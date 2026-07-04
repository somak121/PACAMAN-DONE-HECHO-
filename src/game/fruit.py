"""Fruit entities for Pac-Man."""

from enum import Enum, auto
from typing import Tuple


class FruitType(Enum):
    """Types of fruits available in the game."""

    CHERRY = auto()
    STRAWBERRY = auto()


class Fruit:
    """Represents a fruit item on the maze.

    Args:
        pos: Grid cell coordinates (x, y).
        fruit_type: Type of fruit (Cherry, Strawberry, etc.).
        points: Base points awarded when eaten.
    """

    def __init__(
        self, pos: Tuple[int, int], fruit_type: FruitType, points: int
    ) -> None:
        self.pos: Tuple[int, int] = pos
        self.type: FruitType = fruit_type
        self.points: int = points
        self.eaten: bool = False

    def eat(self) -> None:
        """Mark the fruit as eaten."""
        self.eaten = True
