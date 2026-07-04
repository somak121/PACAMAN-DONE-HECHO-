"""Level module — sets up and manages a single game level."""

import logging
from typing import List, Tuple

from src.config.config_loader import GameConfig, LevelConfig
from src.maze.maze_adapter import MazeAdapter
from src.game.pacgum import Pacgum, SuperPacgum
from src.game.player import Player
from src.game.ghost import Ghost, Blinky, Pinky, Inky, Clyde, GhostState
from src.game.scoring import ScoreTracker
from src.game.fruit import Fruit, FruitType

logger = logging.getLogger(__name__)


class Level:
    """Represents a single Pac-Man level.

    Generates the maze, populates pacgums, super-pacgums, ghosts,
    and places the player at the center. Tracks time and completion.

    Args:
        level_cfg: Level-specific settings (width, height, seed).
        game_cfg: Global game settings (points, time limit, etc.).
        score: The shared score tracker (persists across levels).
        lives: Current player lives carried over from previous level.
        level_number: 1-based level index (for display).
    """

    def __init__(
        self,
        level_cfg: LevelConfig,
        game_cfg: GameConfig,
        score: ScoreTracker,
        lives: int,
        level_number: int,
    ) -> None:
        """Initialize the level: generate maze and place all entities."""
        self.level_number: int = level_number
        self._cfg = game_cfg
        self.score = score
        self.time_remaining: float = float(game_cfg.level_max_time)
        self.complete: bool = False
        self.failed: bool = False

        self.fruits: List[Fruit] = []

        # Generate maze
        try:
            self.maze = MazeAdapter(
                width=level_cfg.width,
                height=level_cfg.height,
                seed=level_cfg.seed,
                perfect=False,
            )
        except RuntimeError as e:
            logger.error("Maze generation failed: %s", e)
            raise

        # Place entities
        corridors = self.maze.get_corridors()
        corners = self.maze.get_corners()
        center = self.maze.get_center()
        # Determine authentic spawn locations
        cx, cy = center

        # Use BFS to find nearest walkable tiles to desired coordinates
        player_start = self.maze._nearest_walkable(cx, cy + 3) or center
        cherry_pos = self.maze._nearest_walkable(cx - 3, cy + 1) or center
        strawberry_pos = self.maze._nearest_walkable(cx + 3, cy + 1) or center

        self.player_start_pos = player_start
        self.fruits = [
            Fruit(cherry_pos, FruitType.CHERRY, 100),
            Fruit(strawberry_pos, FruitType.STRAWBERRY, 300),
        ]

        # Combine all reserved static spawn tiles to avoid placing pacgums on them
        reserved_tiles = (center, player_start, cherry_pos, strawberry_pos)
        self.pacgums: List[Pacgum] = self._place_pacgums(
            corridors, corners, reserved_tiles
        )
        self.super_pacgums: List[SuperPacgum] = self._place_super_pacgums(corners)
        self.player: Player = Player(
            start_pos=player_start,
            lives=lives,
            speed=5.0,
        )
        self.ghosts: List[Ghost] = self._place_ghosts()

        # 2-second delay at start of level
        for ghost in self.ghosts:
            ghost.state = GhostState.RESPAWNING
            ghost._state_timer = 2.0

    # ------------------------------------------------------------------ #
    #  Entity placement
    # ------------------------------------------------------------------ #

    def _place_pacgums(
        self,
        corridors: List[Tuple[int, int]],
        corners: List[Tuple[int, int]],
        reserved_tiles: Tuple[Tuple[int, int], ...],
    ) -> List[Pacgum]:
        """Place pacgums in all corridors except corner cells and reserved tiles."""
        corner_set = set(corners)
        pts = self._cfg.points_per_pacgum
        return [
            Pacgum(pos=cell, points=pts)
            for cell in corridors
            if cell not in corner_set and cell not in reserved_tiles
        ]

    def _place_super_pacgums(
        self,
        corners: List[Tuple[int, int]],
    ) -> List[SuperPacgum]:
        """Place one super-pacgum in each maze corner.

        Args:
            corners: Corner cells from MazeAdapter.

        Returns:
            List of SuperPacgum objects (up to 4).
        """
        pts = self._cfg.points_per_super_pacgum
        dur = self._cfg.frightened_duration
        return [
            SuperPacgum(pos=corner, points=pts, frightened_duration=dur)
            for corner in corners
        ]

    def _place_ghosts(self) -> List[Ghost]:
        """Place all ghosts in the ghost house (center of the maze).

        Returns:
            List of Ghost objects.
        """
        delay = self._cfg.ghost_respawn_delay
        center = self.maze.get_center()
        ghost_classes = [Blinky, Pinky, Inky, Clyde]
        ghosts: List[Ghost] = []
        for cls in ghost_classes:
            ghosts.append(cls(pos=center, respawn_pos=center, respawn_delay=delay))
        return ghosts

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #

    def update(self, dt: float) -> None:
        """Advance level state by dt seconds.

        Handles: timer, player movement, ghost movement, collisions.

        Args:
            dt: Delta time in seconds.
        """
        if self.complete or self.failed:
            return

        # Countdown timer
        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            self._handle_timeout()
            return

        # Update player
        self.player.update(dt, self.maze)

        # Update ghosts
        for ghost in self.ghosts:
            ghost.update(dt, self.player.pos, self.player.direction, self.maze)

        # Check collisions
        self._check_pacgum_collisions()
        self._check_ghost_collisions()
        self._check_fruit_collision()
        self._check_win_condition()

    def _check_fruit_collision(self) -> None:
        """Check if player eats any active fruit."""
        for fruit in self.fruits:
            if not fruit.eaten and self.player.pos == fruit.pos:
                fruit.eat()
                pts = fruit.points
                self.score.add_fruit(pts)
                logger.debug("%s eaten! (+%d)", fruit.type.name, pts)

                # Cherry gives speed boost for 10 seconds
                if fruit.type == FruitType.CHERRY:
                    self.player.activate_fruit_speed_boost(10.0)
                    logger.debug("Speed boost activated for 10s!")

    def _handle_timeout(self) -> None:
        """Handle level time running out."""
        behavior = self._cfg.timeout_behavior
        if behavior == "restart":
            logger.info("Level %d: time out — restarting level", self.level_number)
            self.failed = True  # caller will restart same level
        else:
            logger.info("Level %d: time out — game over", self.level_number)
            self.player.lives = 0
            self.failed = True

    def _check_pacgum_collisions(self) -> None:
        """Check if player is on a pacgum or super-pacgum cell."""
        px, py = self.player.pos

        for pg in self.pacgums:
            if not pg.eaten and pg.pos == (px, py):
                pg.eat()
                pts = self.score.add_pacgum()
                logger.debug("Pacgum eaten at %s (+%d)", pg.pos, pts)

        for spg in self.super_pacgums:
            if not spg.eaten and spg.pos == (px, py):
                spg.eat()
                pts = self.score.add_super_pacgum()
                self.score.reset_ghost_combo()
                logger.debug("Super-pacgum eaten at %s (+%d)", spg.pos, pts)
                for ghost in self.ghosts:
                    ghost.frighten(spg.frightened_duration)

    def _check_ghost_collisions(self) -> None:
        """Check if player collides with any ghost."""
        if not self.player.alive or self.player.is_respawning():
            return
        px, py = self.player.pos
        for ghost in self.ghosts:
            gx = round(ghost.pixel_pos[0])
            gy = round(ghost.pixel_pos[1])
            if (gx, gy) == (px, py) or ghost.pos == (px, py):
                if ghost.is_edible():
                    ghost.eat()
                    pts = self.score.add_ghost()
                    logger.debug("Ghost eaten! (+%d)", pts)
                elif ghost.is_dangerous():
                    game_over = self.player.die()
                    if game_over:
                        self.failed = True
                    else:
                        # Player lost a life, reset all ghosts
                        for g in self.ghosts:
                            g.pos = g._start_pos
                            g._from_pos = g._start_pos
                            g._to_pos = g._start_pos
                            g.state = GhostState.RESPAWNING
                            g._state_timer = 2.0

    def _check_win_condition(self) -> None:
        """Mark level complete when all pacgums are eaten."""
        remaining = sum(1 for pg in self.pacgums if not pg.eaten)
        if remaining == 0:
            self.complete = True
            logger.info("Level %d complete!", self.level_number)

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #

    @property
    def pacgums_remaining(self) -> int:
        """Number of uneaten pacgums."""
        return sum(1 for pg in self.pacgums if not pg.eaten)

    @property
    def total_pacgums(self) -> int:
        """Total number of pacgums in this level."""
        return len(self.pacgums)
