"""Persistent highscore system for Pac-Man.

Stores the top 10 scores (name + score) in a JSON file.
Robust to missing files, corruption, and invalid entries.
"""

import json
import logging
import os
import re
from typing import List, TypedDict

logger = logging.getLogger(__name__)

MAX_ENTRIES: int = 10
MAX_NAME_LEN: int = 10
NAME_PATTERN = re.compile(r"^[A-Za-z0-9 ]+$")


class Entry(TypedDict):
    name: str
    score: int


class HighscoreManager:
    """Manages loading, saving, and querying the highscore list.

    The highscore file is a JSON array of objects:
        [{"name": "SOFIA", "score": 9420}, ...]

    The list is always sorted descending by score and capped at 10 entries.

    Args:
        filepath: Path to the highscore JSON file.
    """

    def __init__(self, filepath: str = "highscores.json") -> None:
        """Initialize and load existing highscores from disk."""
        self._filepath = filepath
        self._entries: List[Entry] = []
        self.load()

    def load(self) -> None:
        """Load highscores from the JSON file.

        On missing file: starts with an empty list (not an error).
        On corrupted file: resets to empty list and logs a warning.
        """
        if not os.path.isfile(self._filepath):
            logger.info(
                "Highscore file '%s' not found — starting fresh",
                self._filepath,
            )
            self._entries = []
            return

        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                raw: object = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "Highscore file '%s' could not be read (%s) — resetting",
                self._filepath,
                e,
            )
            self._entries = []
            return

        self._entries = self._validate_entries(raw)
        self._sort_and_trim()

    def save(self) -> None:
        """Atomically save highscores to disk.

        Writes to a temp file first, then renames to prevent corruption.
        Logs a warning if saving fails (non-fatal).
        """
        tmp_path = self._filepath + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._filepath)
            logger.info("Highscores saved to '%s'", self._filepath)
        except OSError as e:
            logger.warning("Failed to save highscores: %s", e)
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def add_entry(self, name: str, score: int) -> bool:
        """Add a new highscore entry if it qualifies for the top 10.

        Args:
            name: Player name (1–10 chars, alphanumeric + spaces, auto-truncated).
            score: Final score (non-negative integer).

        Returns:
            True if the entry was added, False if it didn't make the top 10.
        """
        clean_name = self._sanitize_name(name)
        if score < 0:
            logger.warning("Ignoring negative score: %d", score)
            return False

        self._entries.append({"name": clean_name, "score": score})
        self._sort_and_trim()

        # Check if the entry survived trimming
        added = any(
            e["name"] == clean_name and e["score"] == score for e in self._entries
        )
        return added

    def get_top_10(self) -> List[Entry]:
        """Return a copy of the top 10 highscore entries.

        Returns:
            List of up to 10 dicts with 'name' and 'score' keys,
            sorted descending by score.
        """
        return list(self._entries)

    def qualifies(self, score: int) -> bool:
        """Check if a score would make the top 10.

        Args:
            score: Score to check.

        Returns:
            True if the score would appear in the top 10 list.
        """
        if len(self._entries) < MAX_ENTRIES:
            return True
        return score > self._entries[-1]["score"]

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    def _sanitize_name(self, name: str) -> str:
        """Clean and validate a player name.

        Args:
            name: Raw name input.

        Returns:
            Sanitized name string (uppercase, 1–10 chars, alphanumeric + space).
        """
        cleaned = name.strip().upper()
        # Keep only valid characters
        cleaned = "".join(c for c in cleaned if c.isalnum() or c == " ")
        cleaned = cleaned[:MAX_NAME_LEN]
        return cleaned if cleaned else "PLAYER"

    def _sort_and_trim(self) -> None:
        """Sort entries descending by score and keep only top 10."""
        self._entries.sort(key=lambda e: e["score"], reverse=True)
        self._entries = self._entries[:MAX_ENTRIES]

    def _validate_entries(self, raw: object) -> List[Entry]:
        """Validate raw data loaded from JSON.

        Args:
            raw: Object loaded from JSON (expected list of dicts).

        Returns:
            Cleaned list of valid entry dicts.
        """
        if not isinstance(raw, list):
            logger.warning("Highscore file has unexpected format — resetting")
            return []

        valid: List[Entry] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            score = item.get("score", -1)
            if not isinstance(name, str) or not isinstance(score, (int, float)):
                continue
            if score < 0:
                continue
            valid.append(
                {
                    "name": self._sanitize_name(name),
                    "score": int(score),
                }
            )
        return valid
