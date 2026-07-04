"""Ghost entities for Pac-Man — base class and 4 AI variants.

Ghost states:
    CHASE       — actively pursues the player (default)
    FRIGHTENED  — runs away from player after a super-pacgum is eaten
    EATEN       — just eaten, waiting to respawn
    RESPAWNING  — respawn timer counting down, then back to CHASE

The four ghosts and their AI strategies:
    Blinky (Red)    — BFS shortest path directly to player
    Pinky (Pink)    — targets 4 cells ahead of player's direction
    Inky (Cyan)     — random valid corridor movement
    Clyde (Orange)  — chases if distance > 8, wanders randomly if close
"""

import random
import logging
from collections import deque
from enum import Enum, auto
from typing import Tuple, List, Optional
from src.maze.maze_adapter import MazeAdapter, Direction

logger = logging.getLogger(__name__)

GHOST_SPEED: float = 4.0
FRIGHTENED_SPEED: float = 2.0
EATEN_SPEED: float = 8.0
PINKY_LOOKAHEAD: int = 4
CLYDE_CHASE_THRESHOLD: int = 8


class GhostState(Enum):
    """Possible states for a ghost."""

    CHASE = auto()
    FRIGHTENED = auto()
    EATEN = auto()
    RESPAWNING = auto()


class Ghost:
    """Base class for all ghosts.

    Args:
        pos: Starting grid cell (x, y) — typically a maze corner.
        color: RGB tuple identifying this ghost visually.
        respawn_delay: Seconds after being eaten before respawning.
    """

    def __init__(
        self,
        pos: Tuple[int, int],
        color: Tuple[int, int, int],
        respawn_pos: Tuple[int, int],
        respawn_delay: float = 7.0,
    ) -> None:
        """Initialize ghost at the given position."""
        self._start_pos: Tuple[int, int] = pos
        self.respawn_pos: Tuple[int, int] = respawn_pos
        self.pos: Tuple[int, int] = pos
        self.color: Tuple[int, int, int] = color
        self.state: GhostState = GhostState.CHASE
        self._respawn_delay: float = respawn_delay
        self._state_timer: float = 0.0

        self._direction: Optional[Direction] = None
        self._move_progress: float = 0.0
        self._from_pos: Tuple[int, int] = pos
        self._to_pos: Tuple[int, int] = pos

        # Cheat: frozen
        self.frozen: bool = False

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def update(
        self,
        dt: float,
        player_pos: Tuple[int, int],
        player_direction: Optional[Direction],
        maze: MazeAdapter,
    ) -> None:
        """Advance ghost state by dt seconds.

        Args:
            dt: Delta time in seconds.
            player_pos: Current player grid position.
            player_direction: Current player direction (for Pinky targeting).
            maze: Current maze.
        """
        if self.frozen:
            return

        # Handle timed states
        if self.state in (
            GhostState.FRIGHTENED,
            GhostState.RESPAWNING,
        ):
            self._state_timer -= dt
            if self._state_timer <= 0.0:
                if self.state == GhostState.FRIGHTENED:
                    self.state = GhostState.CHASE
                elif self.state == GhostState.RESPAWNING:
                    self.pos = self._start_pos
                    self._from_pos = self._start_pos
                    self._to_pos = self._start_pos
                    self.state = GhostState.CHASE

        if self.state == GhostState.RESPAWNING:
            return

        self._update_movement(dt, player_pos, player_direction, maze)

    def frighten(self, duration: float) -> None:
        """Switch ghost to FRIGHTENED state.

        Args:
            duration: How long the frightened state lasts in seconds.
        """
        if self.state not in (GhostState.EATEN, GhostState.RESPAWNING):
            self.state = GhostState.FRIGHTENED
            self._state_timer = duration
            self._direction = None  # force direction re-evaluation

    def eat(self) -> None:
        """Mark ghost as eaten — returns to base."""
        self.state = GhostState.EATEN
        self._direction = None  # force re-evaluate next frame

    def is_frightened(self) -> bool:
        """Return True if ghost is currently frightened."""
        return self.state == GhostState.FRIGHTENED

    def is_edible(self) -> bool:
        """Return True if ghost can be eaten by the player."""
        return self.state == GhostState.FRIGHTENED

    def is_dangerous(self) -> bool:
        """Return True if the ghost can kill the player."""
        return self.state == GhostState.CHASE

    def frightened_fraction(self) -> float:
        """Return remaining frightened time as a fraction (1.0 → 0.0).

        Used to trigger blinking animation near the end of frightened mode.

        Returns:
            Value from 0.0 to 1.0, or 0.0 if not frightened.
        """
        if self.state != GhostState.FRIGHTENED:
            return 0.0
        # We don't store total duration here; caller can use blink threshold
        return max(0.0, self._state_timer)

    @property
    def pixel_pos(self) -> Tuple[float, float]:
        """Interpolated sub-cell position for smooth rendering."""
        fx = (
            self._from_pos[0]
            + (self._to_pos[0] - self._from_pos[0]) * self._move_progress
        )
        fy = (
            self._from_pos[1]
            + (self._to_pos[1] - self._from_pos[1]) * self._move_progress
        )
        return (fx, fy)

    # ------------------------------------------------------------------ #
    #  Movement
    # ------------------------------------------------------------------ #

    def _update_movement(
        self,
        dt: float,
        player_pos: Tuple[int, int],
        player_direction: Optional[Direction],
        maze: MazeAdapter,
    ) -> None:
        """Move ghost based on current state AI.

        Args:
            dt: Delta time.
            player_pos: Player's current cell.
            player_direction: Player's facing direction.
            maze: Maze for wall checks.
        """
        speed = self._current_speed()
        self._move_progress += speed * dt

        if self._move_progress >= 1.0:
            self._move_progress = 0.0
            self.pos = self._to_pos
            self._from_pos = self.pos

            # If EATEN and reached respawn pos, begin respawn countdown
            if self.state == GhostState.EATEN and self.pos == self.respawn_pos:
                self._begin_respawn()
                return

            # Pick next cell
            if self.state == GhostState.EATEN:
                next_dir = self._bfs_next_direction(self.respawn_pos, maze)
            else:
                next_dir = self._choose_direction(player_pos, player_direction, maze)

            if next_dir:
                self._direction = next_dir
                nx = self.pos[0] + next_dir.dx
                ny = self.pos[1] + next_dir.dy
                self._to_pos = (nx, ny)
            else:
                self._to_pos = self.pos

    def _current_speed(self) -> float:
        """Return movement speed for the current state.

        Returns:
            Speed in cells per second.
        """
        if self.state == GhostState.FRIGHTENED:
            return FRIGHTENED_SPEED
        if self.state == GhostState.EATEN:
            return EATEN_SPEED
        return GHOST_SPEED

    def _choose_direction(
        self,
        player_pos: Tuple[int, int],
        player_direction: Optional[Direction],
        maze: MazeAdapter,
    ) -> Optional[Direction]:
        """Select the next movement direction — overridden by subclasses.

        Default implementation: random valid direction (no reversals).

        Args:
            player_pos: Player's grid cell.
            player_direction: Player's facing direction.
            maze: Maze for wall checks.

        Returns:
            Chosen Direction, or None if no valid move.
        """
        return self._random_direction(maze)

    def _random_direction(
        self,
        maze: MazeAdapter,
        prefer_not: Optional[Direction] = None,
    ) -> Optional[Direction]:
        """Choose a random valid direction, avoiding reversals.

        Args:
            maze: Maze for wall checks.
            prefer_not: Direction to avoid (usually opposite of current).

        Returns:
            A valid Direction or None.
        """
        opposite = self._direction.opposite() if self._direction else None
        options: List[Direction] = []
        for d in Direction:
            if d == opposite:
                continue
            if d == prefer_not:
                continue
            if maze.can_move(self.pos[0], self.pos[1], d):
                options.append(d)
        if not options:
            # Allow reversal as last resort
            if opposite and maze.can_move(self.pos[0], self.pos[1], opposite):
                return opposite
            return None
        return random.choice(options)

    def _bfs_next_direction(
        self,
        target: Tuple[int, int],
        maze: MazeAdapter,
    ) -> Optional[Direction]:
        """BFS to find the first direction toward target.

        Args:
            target: Goal cell (x, y).
            maze: Maze for wall checks.

        Returns:
            Best Direction to move toward target, or None.
        """
        if self.pos == target:
            return self._random_direction(maze)

        visited = set()
        visited.add(self.pos)
        # Queue: (current_pos, first_direction_taken)
        queue: deque[Tuple[Tuple[int, int], Direction]] = deque()

        for d in Direction:
            if maze.can_move(self.pos[0], self.pos[1], d):
                nx = self.pos[0] + d.dx
                ny = self.pos[1] + d.dy
                next_pos = (nx, ny)
                if next_pos not in visited:
                    visited.add(next_pos)
                    queue.append((next_pos, d))

        while queue:
            cur, first_dir = queue.popleft()
            if cur == target:
                return first_dir
            for d in Direction:
                if maze.can_move(cur[0], cur[1], d):
                    nx = cur[0] + d.dx
                    ny = cur[1] + d.dy
                    npos = (nx, ny)
                    if npos not in visited:
                        visited.add(npos)
                        queue.append((npos, first_dir))
        return self._random_direction(maze)

    def _flee_direction(
        self,
        player_pos: Tuple[int, int],
        maze: MazeAdapter,
    ) -> Optional[Direction]:
        """Choose direction that maximizes distance from player.

        Args:
            player_pos: Player cell to flee from.
            maze: Maze for wall checks.

        Returns:
            Best Direction away from player, or random fallback.
        """
        opposite = self._direction.opposite() if self._direction else None
        best_dir: Optional[Direction] = None
        best_dist: float = -1.0

        for d in Direction:
            if d == opposite:
                continue
            if maze.can_move(self.pos[0], self.pos[1], d):
                nx = self.pos[0] + d.dx
                ny = self.pos[1] + d.dy
                dist = (nx - player_pos[0]) ** 2 + (ny - player_pos[1]) ** 2
                if dist > best_dist:
                    best_dist = dist
                    best_dir = d

        return best_dir or self._random_direction(maze)

    def _begin_respawn(self) -> None:
        """Start the respawn delay, teleporting ghost to start position."""
        self.state = GhostState.RESPAWNING
        self._state_timer = 1.5  # brief delay before reactivating


# ------------------------------------------------------------------ #
#  4 Ghost subclasses
# ------------------------------------------------------------------ #


class Blinky(Ghost):
    """Red ghost — chases Pac-Man directly via BFS shortest path."""

    COLOR: Tuple[int, int, int] = (255, 0, 0)

    def __init__(
        self,
        pos: Tuple[int, int],
        respawn_pos: Tuple[int, int],
        respawn_delay: float = 7.0,
    ) -> None:
        """Initialize Blinky."""
        super().__init__(pos, self.COLOR, respawn_pos, respawn_delay)

    def _choose_direction(
        self,
        player_pos: Tuple[int, int],
        player_direction: Optional[Direction],
        maze: MazeAdapter,
    ) -> Optional[Direction]:
        """Chase directly using BFS."""
        if self.state == GhostState.FRIGHTENED:
            return self._flee_direction(player_pos, maze)
        return self._bfs_next_direction(player_pos, maze)


class Pinky(Ghost):
    """Pink ghost — targets 4 cells ahead of Pac-Man's direction."""

    COLOR: Tuple[int, int, int] = (255, 184, 255)

    def __init__(
        self,
        pos: Tuple[int, int],
        respawn_pos: Tuple[int, int],
        respawn_delay: float = 7.0,
    ) -> None:
        """Initialize Pinky."""
        super().__init__(pos, self.COLOR, respawn_pos, respawn_delay)

    def _choose_direction(
        self,
        player_pos: Tuple[int, int],
        player_direction: Optional[Direction],
        maze: MazeAdapter,
    ) -> Optional[Direction]:
        """Target 4 tiles ahead of player; fall back to BFS if no direction."""
        if self.state == GhostState.FRIGHTENED:
            return self._flee_direction(player_pos, maze)

        if player_direction:
            tx = player_pos[0] + player_direction.dx * PINKY_LOOKAHEAD
            ty = player_pos[1] + player_direction.dy * PINKY_LOOKAHEAD
            # Clamp to maze bounds
            tx = max(0, min(tx, maze.width - 1))
            ty = max(0, min(ty, maze.height - 1))
            target = (tx, ty)
            # If target is solid, fall back to player position
            if not maze.is_walkable(tx, ty):
                target = player_pos
            return self._bfs_next_direction(target, maze)

        return self._random_direction(maze)


class Inky(Ghost):
    """Cyan ghost — moves randomly through corridors (unpredictable)."""

    COLOR: Tuple[int, int, int] = (0, 255, 255)

    def __init__(
        self,
        pos: Tuple[int, int],
        respawn_pos: Tuple[int, int],
        respawn_delay: float = 7.0,
    ) -> None:
        """Initialize Inky."""
        super().__init__(pos, self.COLOR, respawn_pos, respawn_delay)

    def _choose_direction(
        self,
        player_pos: Tuple[int, int],
        player_direction: Optional[Direction],
        maze: MazeAdapter,
    ) -> Optional[Direction]:
        """Always move randomly (no reversals)."""
        return self._random_direction(maze)


class Clyde(Ghost):
    """Orange ghost — chases if far, wanders randomly if close."""

    COLOR: Tuple[int, int, int] = (255, 184, 82)

    def __init__(
        self,
        pos: Tuple[int, int],
        respawn_pos: Tuple[int, int],
        respawn_delay: float = 7.0,
    ) -> None:
        """Initialize Clyde."""
        super().__init__(pos, self.COLOR, respawn_pos, respawn_delay)

    def _choose_direction(
        self,
        player_pos: Tuple[int, int],
        player_direction: Optional[Direction],
        maze: MazeAdapter,
    ) -> Optional[Direction]:
        """Chase when far (>8 cells), wander randomly when close."""
        if self.state == GhostState.FRIGHTENED:
            return self._flee_direction(player_pos, maze)

        dx = self.pos[0] - player_pos[0]
        dy = self.pos[1] - player_pos[1]
        dist_sq = dx * dx + dy * dy

        if dist_sq > CLYDE_CHASE_THRESHOLD**2:
            return self._bfs_next_direction(player_pos, maze)
        return self._random_direction(maze)
