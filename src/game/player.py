"""Player (Pac-Man) entity."""

import logging
from typing import Tuple, Optional
from src.maze.maze_adapter import MazeAdapter, Direction

logger = logging.getLogger(__name__)

# Pixel speed in cells per second
DEFAULT_SPEED: float = 5.0
FAST_SPEED: float = 10.0

# Respawn delay after dying (seconds)
RESPAWN_DELAY: float = 1.5


class Player:
    """Represents the Pac-Man player.

    The player moves through maze corridors using arrow keys or WASD.
    Movement input is buffered so that the next valid direction is queued
    and applied automatically — making controls feel responsive.

    Args:
        start_pos: Initial grid cell (x, y).
        lives: Starting number of lives.
        speed: Movement speed in cells per second.
    """

    def __init__(
        self,
        start_pos: Tuple[int, int],
        lives: int = 3,
        speed: float = DEFAULT_SPEED,
    ) -> None:
        """Initialize the player at the given position."""
        self._start_pos: Tuple[int, int] = start_pos
        self.pos: Tuple[int, int] = start_pos
        self.direction: Optional[Direction] = None
        self.next_direction: Optional[Direction] = None
        self.lives: int = lives
        self.speed: float = speed
        self.alive: bool = True

        # Sub-cell movement interpolation
        self._move_progress: float = 0.0  # 0.0 → 1.0 between cells
        self._from_pos: Tuple[int, int] = start_pos
        self._to_pos: Tuple[int, int] = start_pos

        # Respawn timer
        self._respawn_timer: float = 0.0
        self._respawning: bool = False

        # Cheat flags
        self.invincible: bool = False
        self.speed_boosted: bool = False  # Permanent cheat toggle

        # Power-up timers
        self._fruit_speed_boost_timer: float = 0.0

        # Animation
        self.mouth_angle: float = 45.0  # degrees open
        self._mouth_direction: float = -1.0  # closing or opening

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #

    def update(self, dt: float, maze: MazeAdapter) -> None:
        """Advance player state by dt seconds.

        Args:
            dt: Delta time in seconds since last frame.
            maze: Current maze for wall collision checks.
        """
        if self._respawning:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0.0:
                self._respawning = False
                self.alive = True
            return

        if not self.alive:
            return

        if self._fruit_speed_boost_timer > 0.0:
            self._fruit_speed_boost_timer -= dt

        self._update_mouth(dt)
        self._update_movement(dt, maze)

    def _update_mouth(self, dt: float) -> None:
        """Animate Pac-Man's mouth opening and closing.

        Args:
            dt: Delta time in seconds.
        """
        MOUTH_SPEED = 200.0  # degrees per second
        self.mouth_angle += self._mouth_direction * MOUTH_SPEED * dt
        if self.mouth_angle <= 0.0:
            self.mouth_angle = 0.0
            self._mouth_direction = 1.0
        elif self.mouth_angle >= 45.0:
            self.mouth_angle = 45.0
            self._mouth_direction = -1.0

    def _update_movement(self, dt: float, maze: MazeAdapter) -> None:
        """Handle sub-cell interpolated movement.

        Args:
            dt: Delta time in seconds.
            maze: Maze for wall checks.
        """
        is_fast = self.speed_boosted or self._fruit_speed_boost_timer > 0.0
        effective_speed = FAST_SPEED if is_fast else self.speed
        self._move_progress += effective_speed * dt

        if self._move_progress >= 1.0:
            # Arrived at destination cell
            self._move_progress = 0.0
            self.pos = self._to_pos
            self._from_pos = self.pos

            # Try to switch to queued direction first
            if self.next_direction and maze.can_move(
                self.pos[0], self.pos[1], self.next_direction
            ):
                self.direction = self.next_direction
                self.next_direction = None

            # Move in current direction if possible
            if self.direction and maze.can_move(
                self.pos[0], self.pos[1], self.direction
            ):
                nx = self.pos[0] + self.direction.dx
                ny = self.pos[1] + self.direction.dy
                self._to_pos = (nx, ny)
            else:
                self._to_pos = self.pos

    def set_direction(self, direction: Direction) -> None:
        """Buffer a direction change request from input.

        If the new direction is directly opposite the current direction,
        apply it instantly to make movement feel more flowy and responsive.

        Args:
            direction: The desired new direction.
        """
        # Instant 180-degree reversal
        if (
            self.direction
            and direction.dx == -self.direction.dx
            and direction.dy == -self.direction.dy
        ):
            self.direction = direction
            self.next_direction = None
            # Swap interpolation endpoints
            self._from_pos, self._to_pos = self._to_pos, self._from_pos
            self._move_progress = 1.0 - self._move_progress
            return

        self.next_direction = direction

    @property
    def pixel_pos(self) -> Tuple[float, float]:
        """Interpolated position between cells for smooth rendering.

        Returns:
            Fractional (x, y) suitable for pixel-level rendering.
        """
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
    #  Life management
    # ------------------------------------------------------------------ #

    def die(self) -> bool:
        """Handle the player being caught by a ghost.

        Returns:
            True if game over (no lives left), False if respawning.
        """
        if self.invincible:
            return False
        self.lives -= 1
        self.alive = False
        if self.lives <= 0:
            return True  # game over
        self._start_respawn()
        return False

    def _start_respawn(self) -> None:
        """Begin the respawn sequence, returning player to start position."""
        self._respawning = True
        self._respawn_timer = RESPAWN_DELAY
        self.pos = self._start_pos
        self._from_pos = self._start_pos
        self._to_pos = self._start_pos
        self._move_progress = 0.0
        self.direction = None
        self.next_direction = None

    def add_life(self) -> None:
        """Add one extra life (cheat mode)."""
        self.lives += 1

    def is_respawning(self) -> bool:
        """Check if the player is in the respawn delay phase."""
        return self._respawning

    def activate_fruit_speed_boost(self, duration: float) -> None:
        """Activate a temporary speed boost (e.g. from eating a Cherry)."""
        self._fruit_speed_boost_timer = duration
