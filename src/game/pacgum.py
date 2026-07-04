"""Pacgum and SuperPacgum entities for Pac-Man."""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Pacgum:
    """A small dot placed in maze corridors.

    Eating a pacgum awards points and counts toward level completion.

    Args:
        pos: Grid cell (x, y) where the pacgum is located.
        points: Points awarded when eaten.
        eaten: Whether this pacgum has been consumed.
    """

    pos: Tuple[int, int]
    points: int = 10
    eaten: bool = field(default=False, init=False)

    def eat(self) -> None:
        """Mark this pacgum as eaten."""
        self.eaten = True


@dataclass
class SuperPacgum:
    """A large power pellet placed in maze corners.

    Eating a super-pacgum awards points and triggers ghost frightened mode.

    Args:
        pos: Grid cell (x, y) where the super-pacgum is located.
        points: Points awarded when eaten.
        frightened_duration: How long ghosts remain frightened in seconds.
        eaten: Whether this super-pacgum has been consumed.
    """

    pos: Tuple[int, int]
    points: int = 50
    frightened_duration: float = 7.0
    eaten: bool = field(default=False, init=False)

    def eat(self) -> None:
        """Mark this super-pacgum as eaten."""
        self.eaten = True
