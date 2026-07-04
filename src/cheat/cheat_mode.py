"""Cheat mode for Pac-Man — for peer review purposes.

Activate the cheat overlay by pressing C during gameplay.
Then use the keys below to trigger individual cheats.

Cheats:
    I — Invincibility (toggle)
    N — Skip current level (win immediately)
    F — Freeze all ghosts (toggle)
    L — Add 1 extra life
    S — Speed boost (toggle)
    G — Scare all ghosts (trigger frightened mode)
"""

import logging
from typing import List
from src.game.player import Player
from src.game.ghost import Ghost

logger = logging.getLogger(__name__)


class CheatMode:
    """Provides cheat functions for peer review testing.

    All cheats are designed to help evaluators quickly reach and test
    any game feature without needing to play through normally.
    """

    def toggle_invincibility(self, player: Player) -> None:
        """Toggle player invincibility on/off.

        When invincible, ghosts cannot kill the player.

        Args:
            player: The player entity.
        """
        player.invincible = not player.invincible
        state = "ON" if player.invincible else "OFF"
        logger.info("[CHEAT] Invincibility %s", state)

    def skip_level(self, level: object) -> None:
        """Immediately win the current level.

        Args:
            level: The current Level instance.
        """
        logger.info("[CHEAT] Level skip triggered")
        if hasattr(level, "complete"):
            level.complete = True

    def toggle_ghost_freeze(self, ghosts: List[Ghost]) -> None:
        """Freeze or unfreeze all ghosts.

        When frozen, ghosts stop moving entirely.

        Args:
            ghosts: List of Ghost instances.
        """
        if not ghosts:
            return
        new_state = not ghosts[0].frozen
        for ghost in ghosts:
            ghost.frozen = new_state
        state = "frozen" if new_state else "unfrozen"
        logger.info("[CHEAT] All ghosts %s", state)

    def add_life(self, player: Player) -> None:
        """Add one extra life to the player.

        Args:
            player: The player entity.
        """
        player.add_life()
        logger.info("[CHEAT] Extra life added (now %d)", player.lives)

    def toggle_speed_boost(self, player: Player) -> None:
        """Toggle player speed boost on/off.

        When boosted, player moves at 2x normal speed.

        Args:
            player: The player entity.
        """
        player.speed_boosted = not player.speed_boosted
        state = "ON" if player.speed_boosted else "OFF"
        logger.info("[CHEAT] Speed boost %s", state)

    def scare_all_ghosts(self, ghosts: List[Ghost], duration: float) -> None:
        """Trigger frightened mode on all active ghosts.

        Args:
            ghosts: List of Ghost instances.
            duration: How long to frighten them (seconds).
        """
        for ghost in ghosts:
            ghost.frighten(duration)
        logger.info("[CHEAT] All ghosts scared for %.1fs", duration)
