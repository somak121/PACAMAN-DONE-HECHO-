"""Tests for HighscoreManager."""

import os
import json
import tempfile
from src.highscore.highscore import HighscoreManager


def _temp_path(content: str = "") -> str:
    """Create a temp .json file with given content."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return f.name


class TestHighscoreManager:
    """Test suite for HighscoreManager."""

    def test_empty_start_when_no_file(self) -> None:
        """Non-existent file should produce empty highscore list."""
        hs = HighscoreManager("/tmp/nonexistent_hs_42.json")
        assert hs.get_top_10() == []

    def test_save_and_load_roundtrip(self) -> None:
        """Saving then loading should preserve all entries."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            hs.add_entry("SOFIA", 5000)
            hs.add_entry("PLAYER", 3000)
            hs.save()

            hs2 = HighscoreManager(path)
            top = hs2.get_top_10()
            assert any(e["name"] == "SOFIA" and e["score"] == 5000 for e in top)
            assert any(e["name"] == "PLAYER" and e["score"] == 3000 for e in top)
        finally:
            os.unlink(path)

    def test_top_10_enforced(self) -> None:
        """Only the top 10 scores should be kept."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            for i in range(15):
                hs.add_entry(f"P{i}", i * 100)
            top = hs.get_top_10()
            assert len(top) == 10
            # Lowest should have been dropped
            assert all(e["score"] >= 500 for e in top)
        finally:
            os.unlink(path)

    def test_sorted_descending(self) -> None:
        """Highscores should always be sorted highest first."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            for score in [100, 500, 200, 800, 300]:
                hs.add_entry("TEST", score)
            scores = [int(e["score"]) for e in hs.get_top_10()]
            assert scores == sorted(scores, reverse=True)
        finally:
            os.unlink(path)

    def test_corrupted_file_resets(self) -> None:
        """Corrupted JSON file should produce empty list without crashing."""
        path = _temp_path("not valid json at all!!!")
        try:
            hs = HighscoreManager(path)
            assert hs.get_top_10() == []
        finally:
            os.unlink(path)

    def test_name_sanitization(self) -> None:
        """Names should be uppercased, max 10 chars, only alphanumeric+space."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            hs.add_entry("sofia!!!", 1000)
            top = hs.get_top_10()
            name = top[0]["name"]
            assert name == "SOFIA"
        finally:
            os.unlink(path)

    def test_name_too_long_truncated(self) -> None:
        """Names longer than 10 chars should be truncated."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            hs.add_entry("VERYLONGNAME123", 500)
            top = hs.get_top_10()
            assert len(str(top[0]["name"])) <= 10
        finally:
            os.unlink(path)

    def test_empty_name_becomes_player(self) -> None:
        """Empty or whitespace-only name should default to 'PLAYER'."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            hs.add_entry("   ", 100)
            top = hs.get_top_10()
            assert top[0]["name"] == "PLAYER"
        finally:
            os.unlink(path)

    def test_negative_score_rejected(self) -> None:
        """Negative scores should not be added."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            added = hs.add_entry("BAD", -100)
            assert added is False
            assert hs.get_top_10() == []
        finally:
            os.unlink(path)

    def test_qualifies_below_top10(self) -> None:
        """A score lower than the worst top-10 entry should not qualify."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            for i in range(10):
                hs.add_entry(f"P{i}", (i + 1) * 1000)
            # Worst score is 1000, so 500 should not qualify
            assert hs.qualifies(500) is False
            assert hs.qualifies(15000) is True
        finally:
            os.unlink(path)

    def test_atomic_save_no_partial_write(self) -> None:
        """Save should not leave corrupted data if interrupted (basic check)."""
        path = _temp_path()
        try:
            hs = HighscoreManager(path)
            hs.add_entry("A", 100)
            hs.save()
            # File should be valid JSON after save
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list)
        finally:
            os.unlink(path)
