"""Tests for ConfigLoader."""

import os
import json
import tempfile
import pytest
from src.config.config_loader import ConfigLoader, GameConfig


def _write_config(data: str, suffix: str = ".json") -> str:
    """Write data to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    f.write(data)
    f.close()
    return f.name


class TestConfigLoader:
    """Test suite for ConfigLoader."""

    def test_valid_config_loads(self) -> None:
        """Valid JSON config should load without errors."""
        cfg_text = json.dumps(
            {
                "lives": 5,
                "points_per_pacgum": 15,
                "levels": [{"width": 21, "height": 21, "seed": 42}] * 10,
            }
        )
        path = _write_config(cfg_text)
        try:
            cfg = ConfigLoader.load(path)
            assert cfg.lives == 5
            assert cfg.points_per_pacgum == 15
        finally:
            os.unlink(path)

    def test_comments_are_stripped(self) -> None:
        """Lines starting with # should be ignored."""
        cfg_text = (
            "# This is a comment\n"
            '{"lives": 3, "levels": [{"width": 21, "height": 21, "seed": 42}]}\n'
        )
        # Pad to 10 levels with repeated entries
        data = {
            "lives": 3,
            "levels": [{"width": 21, "height": 21, "seed": 42}] * 10,
        }
        cfg_text = "# comment\n" + json.dumps(data)
        path = _write_config(cfg_text)
        try:
            cfg = ConfigLoader.load(path)
            assert cfg.lives == 3
        finally:
            os.unlink(path)

    def test_missing_keys_use_defaults(self) -> None:
        """Missing keys should fall back to safe defaults."""
        path = _write_config("{}")
        try:
            cfg = ConfigLoader.load(path)
            assert cfg.lives == 3
            assert cfg.points_per_pacgum == 10
            assert cfg.level_max_time == 90
            assert len(cfg.levels) == 10
        finally:
            os.unlink(path)

    def test_invalid_lives_clamped(self) -> None:
        """Negative lives should be clamped to 1."""
        data = {"lives": -5}
        path = _write_config(json.dumps(data))
        try:
            cfg = ConfigLoader.load(path)
            assert cfg.lives >= 1
        finally:
            os.unlink(path)

    def test_unknown_keys_ignored(self) -> None:
        """Unknown config keys should be silently ignored."""
        data = {"unknown_key_xyz": "value", "another_unknown": 999}
        path = _write_config(json.dumps(data))
        try:
            cfg = ConfigLoader.load(path)
            assert isinstance(cfg, GameConfig)
        finally:
            os.unlink(path)

    def test_missing_file_raises(self) -> None:
        """Missing file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load("/nonexistent/path/config.json")

    def test_invalid_json_raises(self) -> None:
        """Invalid JSON should raise ValueError."""
        path = _write_config("{ not valid json }")
        try:
            with pytest.raises(ValueError):
                ConfigLoader.load(path)
        finally:
            os.unlink(path)

    def test_non_json_extension_accepted(self) -> None:
        """ConfigLoader itself doesn't check extension — that's pac-man.py's job."""
        data = {
            "lives": 2,
            "levels": [{"width": 21, "height": 21, "seed": 0}] * 10,
        }
        path = _write_config(json.dumps(data), suffix=".txt")
        try:
            cfg = ConfigLoader.load(path)
            assert cfg.lives == 2
        finally:
            os.unlink(path)

    def test_levels_padded_to_10(self) -> None:
        """Fewer than 10 levels should be padded with defaults."""
        data = {"levels": [{"width": 21, "height": 21, "seed": 42}]}
        path = _write_config(json.dumps(data))
        try:
            cfg = ConfigLoader.load(path)
            assert len(cfg.levels) == 10
        finally:
            os.unlink(path)

    def test_even_dimensions_made_odd(self) -> None:
        """Even maze dimensions should be incremented to odd."""
        data = {"levels": [{"width": 20, "height": 22, "seed": 0}] * 10}
        path = _write_config(json.dumps(data))
        try:
            cfg = ConfigLoader.load(path)
            assert cfg.levels[0].width % 2 == 1
            assert cfg.levels[0].height % 2 == 1
        finally:
            os.unlink(path)

    def test_timeout_behavior_default(self) -> None:
        """Invalid timeout_behavior should default to 'game_over'."""
        data = {"timeout_behavior": "invalid_value"}
        path = _write_config(json.dumps(data))
        try:
            cfg = ConfigLoader.load(path)
            assert cfg.timeout_behavior == "game_over"
        finally:
            os.unlink(path)
