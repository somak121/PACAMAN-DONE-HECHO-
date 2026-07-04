"""Maze adapter — wraps the external MazeGenerator package.

This is the ONLY file that imports or calls MazeGenerator directly.
All game code must use MazeAdapter instead.

Wall encoding per cell (4 low bits):
    Bit 0 (value 1) = North wall — blocks movement UP
    Bit 1 (value 2) = East wall  — blocks movement RIGHT
    Bit 2 (value 4) = South wall — blocks movement DOWN
    Bit 3 (value 8) = West wall  — blocks movement LEFT
    Value 15        = fully solid cell (all 4 walls) — not walkable
"""

import logging
from enum import Enum
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class Direction(Enum):
    """Cardinal directions for movement and wall checks.

    Each direction has an associated bit mask matching MazeGenerator's encoding.
    """

    NORTH = 1  # bit 0
    EAST = 2  # bit 1
    SOUTH = 4  # bit 2
    WEST = 8  # bit 3

    @property
    def dx(self) -> int:
        """Horizontal delta for this direction."""
        return {
            Direction.NORTH: 0,
            Direction.EAST: 1,
            Direction.SOUTH: 0,
            Direction.WEST: -1,
        }[self]

    @property
    def dy(self) -> int:
        """Vertical delta for this direction."""
        return {
            Direction.NORTH: -1,
            Direction.EAST: 0,
            Direction.SOUTH: 1,
            Direction.WEST: 0,
        }[self]

    def opposite(self) -> "Direction":
        """Return the opposite direction."""
        return {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }[self]


SOLID: int = 15  # cell value for a fully walled (unpassable) block


class MazeAdapter:
    """Wraps MazeGenerator to expose a Pac-Man-friendly interface.

    This adapter isolates all dependency on the external MazeGenerator package.
    If the package API changes, only this file needs to be updated.

    Args:
        width: Maze width in cells.
        height: Maze height in cells.
        seed: Seed for reproducibility. 0 = random. 42 = fixed (level 1).
        perfect: Must be False for Pac-Man (produces loops).

    Example:
        maze = MazeAdapter(width=21, height=21, seed=42)
        if maze.can_move(5, 3, Direction.EAST):
            player.move_east()
    """

    def __init__(
        self,
        width: int,
        height: int,
        seed: int = 0,
        perfect: bool = False,
    ) -> None:
        """Initialize and generate the maze."""
        self._width = width
        self._height = height
        self._seed = seed
        self._perfect = perfect
        self._grid: List[List[int]] = []
        self._generate()

    def _generate(self) -> None:
        """Call MazeGenerator and store the resulting grid.

        Raises:
            RuntimeError: If MazeGenerator fails or produces an invalid grid.
        """
        try:
            from mazegenerator import MazeGenerator

            mg = MazeGenerator(
                size=(self._width, self._height),
                perfect=self._perfect,
                seed=self._seed,
            )
            self._grid = mg.maze
            self._entry: Tuple[int, int] = mg.maze_entry
            self._exit: Tuple[int, int] = mg.maze_exit
        except ImportError as e:
            raise RuntimeError(
                "MazeGenerator package not installed. Run: make install"
            ) from e
        except Exception as e:
            raise RuntimeError(f"MazeGenerator failed to generate maze: {e}") from e

        if not self._grid or len(self._grid) != self._height:
            raise RuntimeError(
                f"MazeGenerator returned unexpected grid shape: "
                f"{len(self._grid)} rows, expected {self._height}"
            )

    def regenerate(self, seed: int = 0) -> None:
        """Regenerate the maze with an optional new seed.

        Args:
            seed: New seed. 0 = random.
        """
        self._seed = seed
        self._generate()

    # ------------------------------------------------------------------ #
    #  Movement helpers
    # ------------------------------------------------------------------ #

    def can_move(self, x: int, y: int, direction: Direction) -> bool:
        """Check if movement from cell (x, y) in direction is unblocked.

        Args:
            x: Column index.
            y: Row index.
            direction: Direction to move.

        Returns:
            True if movement is allowed (no wall on that side).
        """
        if not self._in_bounds(x, y):
            return False
        cell = self._grid[y][x]
        if cell == SOLID:
            return False
        return (cell & direction.value) == 0

    def is_walkable(self, x: int, y: int) -> bool:
        """Check whether cell (x, y) can be entered at all.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            True if the cell is not fully solid.
        """
        if not self._in_bounds(x, y):
            return False
        return self._grid[y][x] != SOLID

    # ------------------------------------------------------------------ #
    #  Spatial helpers
    # ------------------------------------------------------------------ #

    def get_corridors(self) -> List[Tuple[int, int]]:
        """Return all walkable cell coordinates.

        Returns:
            List of (x, y) tuples for every non-solid cell.
        """
        return [
            (x, y)
            for y in range(self._height)
            for x in range(self._width)
            if self.is_walkable(x, y)
        ]

    def get_corners(self) -> List[Tuple[int, int]]:
        """Return the nearest walkable cell to each of the 4 maze corners.

        Used for placing super-pacgums and ghost spawn points.

        Returns:
            List of 4 (x, y) tuples, one per corner (TL, TR, BL, BR).
        """
        candidates = [
            (0, 0),
            (self._width - 1, 0),
            (0, self._height - 1),
            (self._width - 1, self._height - 1),
        ]
        corners: List[Tuple[int, int]] = []
        for cx, cy in candidates:
            nearest = self._nearest_walkable(cx, cy)
            if nearest is not None:
                corners.append(nearest)
        return corners

    def get_center(self) -> Tuple[int, int]:
        """Return the nearest walkable cell to the maze center.

        Used for placing the player spawn point.

        Returns:
            (x, y) of the nearest walkable cell to center.
        """
        cx = self._width // 2
        cy = self._height // 2
        result = self._nearest_walkable(cx, cy)
        if result is None:
            # Fallback: first walkable cell
            corridors = self.get_corridors()
            if corridors:
                return corridors[0]
            raise RuntimeError("Maze has no walkable cells")
        return result

    def _nearest_walkable(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        """BFS from (x, y) to find the nearest walkable cell.

        Args:
            x: Starting column.
            y: Starting row.

        Returns:
            Nearest walkable (x, y), or None if maze is entirely solid.
        """
        from collections import deque

        if self.is_walkable(x, y):
            return (x, y)
        visited = [[False] * self._width for _ in range(self._height)]
        queue: deque[Tuple[int, int]] = deque([(x, y)])
        visited[y][x] = True
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if self._in_bounds(nx, ny) and not visited[ny][nx]:
                    visited[ny][nx] = True
                    if self.is_walkable(nx, ny):
                        return (nx, ny)
                    queue.append((nx, ny))
        return None

    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if (x, y) is within the maze grid.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            True if within bounds.
        """
        return 0 <= x < self._width and 0 <= y < self._height

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #

    @property
    def width(self) -> int:
        """Maze width in cells."""
        return self._width

    @property
    def height(self) -> int:
        """Maze height in cells."""
        return self._height

    @property
    def raw_grid(self) -> List[List[int]]:
        """The raw 2D grid from MazeGenerator (read-only view).

        Returns:
            2D list where each int encodes walls via bit flags.
        """
        return self._grid

    @property
    def entry(self) -> Tuple[int, int]:
        """Maze entry cell coordinates (x, y)."""
        return self._entry

    @property
    def exit(self) -> Tuple[int, int]:
        """Maze exit cell coordinates (x, y)."""
        return self._exit
