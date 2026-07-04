"""Scoring tracker for Pac-Man."""


class ScoreTracker:
    """Tracks the player's score throughout the game.

    The score is strictly non-negative and never decreases.
    Ghosts eaten in sequence during a single frightened phase
    award a doubling bonus (200, 400, 800, 1600).

    Args:
        points_per_pacgum: Points per regular pacgum.
        points_per_super_pacgum: Points per super-pacgum.
        points_per_ghost: Base points per ghost eaten.
    """

    MAX_GHOST_MULTIPLIER: int = 8  # caps at 8x

    def __init__(
        self,
        points_per_pacgum: int = 10,
        points_per_super_pacgum: int = 50,
        points_per_ghost: int = 200,
    ) -> None:
        """Initialize the score tracker."""
        self._score: int = 0
        self._points_per_pacgum = points_per_pacgum
        self._points_per_super_pacgum = points_per_super_pacgum
        self._points_per_ghost = points_per_ghost
        self._ghost_combo: int = 0  # consecutive ghosts in one frightened phase

    def add_pacgum(self) -> int:
        """Award points for eating a pacgum.

        Returns:
            Points awarded.
        """
        pts = self._points_per_pacgum
        self._score += pts
        return pts

    def add_super_pacgum(self) -> int:
        """Award points for eating a super-pacgum and reset ghost combo.

        Returns:
            Points awarded.
        """
        self._ghost_combo = 0
        pts = self._points_per_super_pacgum
        self._score += pts
        return pts

    def add_fruit(self, points: int) -> None:
        """Add points for eating a fruit.

        Args:
            points: Points value of the fruit.
        """
        self._score += points

    def add_ghost(self) -> int:
        """Award points for eating a ghost, with doubling combo bonus.

        Each ghost eaten in the same frightened phase doubles the base award.
        Resets automatically when a new super-pacgum is eaten.

        Returns:
            Points awarded.
        """
        multiplier = min(1 << self._ghost_combo, self.MAX_GHOST_MULTIPLIER)
        pts = self._points_per_ghost * multiplier
        self._score += pts
        self._ghost_combo += 1
        return pts

    def reset_ghost_combo(self) -> None:
        """Reset the ghost combo counter (call when frightened phase ends)."""
        self._ghost_combo = 0

    @property
    def score(self) -> int:
        """Current score (always non-negative)."""
        return self._score

    def reset(self) -> None:
        """Reset score to zero (use at game start only)."""
        self._score = 0
        self._ghost_combo = 0
