"""Configuration loader for Pac-Man.

Handles JSON config files with '#' comment lines, validates all keys,
clamps invalid values to safe defaults, and ignores unknown keys.
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class LevelConfig:
    """Configuration for a single game level.

    Args:
        width: Maze width in cells (odd number recommended).
        height: Maze height in cells (odd number recommended).
        seed: Random seed. 0 = fully random. 42 = fixed for level 1.
    """

    width: int = 21
    height: int = 21
    seed: int = 0


@dataclass
class GameConfig:
    """Full game configuration loaded from a JSON file.

    Args:
        highscore_filename: Path to the highscore JSON file.
        lives: Number of starting lives.
        points_per_pacgum: Score awarded per pacgum eaten.
        points_per_super_pacgum: Score awarded per super-pacgum eaten.
        points_per_ghost: Score awarded per ghost eaten.
        points_per_fruit: Score awarded per fruit eaten.
        frightened_duration: Seconds ghosts stay frightened.
        ghost_respawn_delay: Seconds before eaten ghost respawns.
        level_max_time: Time limit per level in seconds.
        timeout_behavior: 'game_over' or 'restart' when time runs out.
        levels: List of level configurations.
    """

    highscore_filename: str = "highscores.json"
    lives: int = 3
    points_per_pacgum: int = 10
    points_per_super_pacgum: int = 50
    points_per_ghost: int = 200
    points_per_fruit: int = 100
    frightened_duration: float = 7.0
    ghost_respawn_delay: float = 7.0
    level_max_time: int = 90
    timeout_behavior: str = "game_over"
    levels: List[LevelConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Ensure at least 10 default levels exist if none configured."""
        if not self.levels:
            self.levels = _default_levels()


def _default_levels() -> List[LevelConfig]:
    """Return a default list of 10 levels with increasing maze sizes.

    Returns:
        List of 10 LevelConfig objects.
    """
    return [
        LevelConfig(width=21, height=21, seed=42),
        LevelConfig(width=21, height=21, seed=0),
        LevelConfig(width=23, height=23, seed=0),
        LevelConfig(width=23, height=23, seed=0),
        LevelConfig(width=25, height=25, seed=0),
        LevelConfig(width=25, height=25, seed=0),
        LevelConfig(width=27, height=27, seed=0),
        LevelConfig(width=27, height=27, seed=0),
        LevelConfig(width=29, height=29, seed=0),
        LevelConfig(width=29, height=29, seed=0),
    ]


def _strip_comments(text: str) -> str:
    """Remove comment lines starting with '#' from JSON text.

    Also supports C-style // comments at the start of a line.

    Args:
        text: Raw file content.

    Returns:
        Cleaned JSON string with comment lines removed.
    """
    lines = text.splitlines()
    cleaned: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _clamp_int(
    value: object,
    key: str,
    min_val: int,
    max_val: int,
    default: int,
) -> int:
    """Validate and clamp an integer config value.

    Args:
        value: Raw value from config.
        key: Config key name (for logging).
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.
        default: Fallback value if invalid.

    Returns:
        Clamped integer value.
    """
    if not isinstance(value, (int, float)):
        logger.warning(
            "Config '%s' must be a number, got %r — using default %d",
            key,
            value,
            default,
        )
        return default
    clamped = max(min_val, min(int(value), max_val))
    if clamped != int(value):
        logger.warning(
            "Config '%s' value %r clamped to %d (range %d–%d)",
            key,
            value,
            clamped,
            min_val,
            max_val,
        )
    return clamped


def _clamp_float(
    value: object,
    key: str,
    min_val: float,
    max_val: float,
    default: float,
) -> float:
    """Validate and clamp a float config value.

    Args:
        value: Raw value from config.
        key: Config key name (for logging).
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.
        default: Fallback value if invalid.

    Returns:
        Clamped float value.
    """
    if not isinstance(value, (int, float)):
        logger.warning(
            "Config '%s' must be a number, got %r — using default %.1f",
            key,
            value,
            default,
        )
        return default
    clamped = max(min_val, min(float(value), max_val))
    if abs(clamped - float(value)) > 1e-9:
        logger.warning(
            "Config '%s' value %r clamped to %.1f (range %.1f–%.1f)",
            key,
            value,
            clamped,
            min_val,
            max_val,
        )
    return clamped


def _parse_levels(raw: object) -> List[LevelConfig]:
    """Parse the 'levels' array from config.

    Args:
        raw: Raw value from config (expected list of dicts).

    Returns:
        List of LevelConfig. Falls back to defaults on bad input.
    """
    if not isinstance(raw, list) or len(raw) == 0:
        logger.warning("Config 'levels' must be a non-empty list — using defaults")
        return _default_levels()

    levels: List[LevelConfig] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            logger.warning("Level %d is not a dict — skipping", i)
            continue
        width = _clamp_int(item.get("width", 21), f"levels[{i}].width", 5, 99, 21)
        height = _clamp_int(item.get("height", 21), f"levels[{i}].height", 5, 99, 21)
        seed = _clamp_int(item.get("seed", 0), f"levels[{i}].seed", 0, 2**31 - 1, 0)
        # Force odd dimensions for better maze generation
        if width % 2 == 0:
            width += 1
        if height % 2 == 0:
            height += 1
        levels.append(LevelConfig(width=width, height=height, seed=seed))

    if len(levels) < 10:
        logger.warning(
            "Only %d levels configured — padding to 10 with defaults",
            len(levels),
        )
        levels.extend(_default_levels()[len(levels) :])

    return levels


def _validate_timeout_behavior(value: object) -> str:
    """Validate the timeout_behavior string.

    Args:
        value: Raw value from config.

    Returns:
        Validated string, either 'game_over' or 'restart'.
    """
    allowed = {"game_over", "restart"}
    if not isinstance(value, str) or value not in allowed:
        logger.warning(
            "Config 'timeout_behavior' must be one of %s, got %r — using 'game_over'",
            allowed,
            value,
        )
        return "game_over"
    return value


class ConfigLoader:
    """Loads and validates a Pac-Man JSON config file.

    Example:
        config = ConfigLoader.load("config.json")
    """

    @staticmethod
    def load(path: str) -> GameConfig:
        """Load, parse, and validate a JSON config file.

        Lines starting with '#' or '//' are treated as comments and ignored.
        Missing keys use safe defaults. Invalid values are clamped and logged.
        Unknown keys are silently ignored.

        Args:
            path: Path to the JSON config file.

        Returns:
            A validated GameConfig dataclass.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be parsed as JSON after comment stripping.
        """
        logging.basicConfig(
            format="[PAC-MAN] %(levelname)s: %(message)s",
            level=logging.WARNING,
        )

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except OSError as e:
            raise FileNotFoundError(f"Cannot open config file '{path}': {e}") from e

        cleaned = _strip_comments(raw_text)

        try:
            data: object = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Config file '{path}' is not valid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(
                f"Config file '{path}' must be a JSON object at the top level"
            )

        cfg = GameConfig(
            highscore_filename=str(data.get("highscore_filename", "highscores.json")),
            lives=_clamp_int(data.get("lives", 3), "lives", 1, 99, 3),
            points_per_pacgum=_clamp_int(
                data.get("points_per_pacgum", 10),
                "points_per_pacgum",
                0,
                10000,
                10,
            ),
            points_per_super_pacgum=_clamp_int(
                data.get("points_per_super_pacgum", 50),
                "points_per_super_pacgum",
                0,
                10000,
                50,
            ),
            points_per_ghost=_clamp_int(
                data.get("points_per_ghost", 200),
                "points_per_ghost",
                0,
                100000,
                200,
            ),
            frightened_duration=_clamp_float(
                data.get("frightened_duration", 7.0),
                "frightened_duration",
                1.0,
                60.0,
                7.0,
            ),
            ghost_respawn_delay=_clamp_float(
                data.get("ghost_respawn_delay", 7.0),
                "ghost_respawn_delay",
                1.0,
                60.0,
                7.0,
            ),
            level_max_time=_clamp_int(
                data.get("level_max_time", 90), "level_max_time", 10, 600, 90
            ),
            timeout_behavior=_validate_timeout_behavior(
                data.get("timeout_behavior", "game_over")
            ),
            levels=_parse_levels(data.get("levels", [])),
        )

        # Validate highscore_filename is a plausible path
        if not re.match(r"^[\w\-./\\]+\.json$", cfg.highscore_filename):
            logger.warning(
                "Config 'highscore_filename' looks suspicious: %r — using default",
                cfg.highscore_filename,
            )
            cfg.highscore_filename = "highscores.json"

        return cfg
