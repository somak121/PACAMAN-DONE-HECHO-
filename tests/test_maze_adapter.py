"""Tests for MazeAdapter (requires mazegenerator to be installed)."""

import pytest
from src.maze.maze_adapter import MazeAdapter, Direction, SOLID


@pytest.fixture(scope="module")
def maze() -> MazeAdapter:
    """Create a 21x21 maze with fixed seed for deterministic tests."""
    return MazeAdapter(width=21, height=21, seed=42, perfect=False)


class TestMazeAdapter:
    """Test suite for MazeAdapter."""

    def test_correct_dimensions(self, maze: MazeAdapter) -> None:
        """Generated maze should have the requested dimensions."""
        assert maze.width == 21
        assert maze.height == 21

    def test_grid_shape(self, maze: MazeAdapter) -> None:
        """Raw grid should have height rows and width columns."""
        grid = maze.raw_grid
        assert len(grid) == maze.height
        assert all(len(row) == maze.width for row in grid)

    def test_has_walkable_cells(self, maze: MazeAdapter) -> None:
        """Maze should have at least some walkable (non-solid) cells."""
        corridors = maze.get_corridors()
        assert len(corridors) > 0

    def test_not_all_solid(self, maze: MazeAdapter) -> None:
        """Not every cell should be fully solid."""
        solid_count = sum(
            1
            for y in range(maze.height)
            for x in range(maze.width)
            if maze.raw_grid[y][x] == SOLID
        )
        assert solid_count < maze.width * maze.height

    def test_can_move_respects_walls(self, maze: MazeAdapter) -> None:
        """can_move should return False when a wall blocks that direction."""
        for y in range(maze.height):
            for x in range(maze.width):
                cell = maze.raw_grid[y][x]
                if cell == SOLID:
                    continue
                for d in Direction:
                    has_wall = (cell & d.value) != 0
                    can = maze.can_move(x, y, d)
                    assert can != has_wall, (
                        f"Mismatch at ({x},{y}) direction {d}: "
                        f"cell={cell}, can_move={can}"
                    )

    def test_out_of_bounds_not_walkable(self, maze: MazeAdapter) -> None:
        """Cells outside maze bounds should not be walkable."""
        assert not maze.is_walkable(-1, 0)
        assert not maze.is_walkable(0, -1)
        assert not maze.is_walkable(maze.width, 0)
        assert not maze.is_walkable(0, maze.height)

    def test_out_of_bounds_cannot_move(self, maze: MazeAdapter) -> None:
        """Moving out of bounds should return False."""
        assert not maze.can_move(-1, 0, Direction.NORTH)
        assert not maze.can_move(0, maze.height, Direction.SOUTH)

    def test_get_corners_returns_four(self, maze: MazeAdapter) -> None:
        """get_corners should return exactly 4 walkable cells."""
        corners = maze.get_corners()
        assert len(corners) == 4
        for c in corners:
            assert maze.is_walkable(c[0], c[1])

    def test_get_center_is_walkable(self, maze: MazeAdapter) -> None:
        """get_center should return a walkable cell."""
        center = maze.get_center()
        assert maze.is_walkable(center[0], center[1])

    def test_imperfect_maze_has_loops(self) -> None:
        """PERFECT=False should produce a maze with multiple paths (loops)."""
        # Run multiple regenerations and check that not all cells are dead-ends
        m = MazeAdapter(width=21, height=21, seed=1, perfect=False)
        corridors = m.get_corridors()
        # Count cells with 3+ openings (junction = loop evidence)
        junctions = [
            c
            for c in corridors
            if sum(1 for d in Direction if m.can_move(c[0], c[1], d)) >= 3
        ]
        assert len(junctions) > 0, "Expected some junctions (loops) with PERFECT=False"

    def test_fixed_seed_reproducible(self) -> None:
        """Same seed should produce identical mazes."""
        m1 = MazeAdapter(width=21, height=21, seed=42)
        m2 = MazeAdapter(width=21, height=21, seed=42)
        assert m1.raw_grid == m2.raw_grid

    def test_different_seeds_differ(self) -> None:
        """Different seeds should usually produce different mazes."""
        m1 = MazeAdapter(width=21, height=21, seed=1)
        m2 = MazeAdapter(width=21, height=21, seed=999)
        assert m1.raw_grid != m2.raw_grid
