*This project has been created as part of the 42 curriculum by smikhail, evieito-.*

# PAC-MAN

> Recreating the classic 1980 arcade game in Python — with modern architecture, AI-powered ghosts, and a polished UI.

---

## Description

This project is a faithful recreation of **Namco's Pac-Man (1980)**, implemented entirely in Python 3.10+ using **pygame** for graphics. The game features:

- **10+ procedurally generated levels** via the external `mazegenerator` package
- **4 ghost AI variants** (Blinky, Pinky, Inky, Clyde) with chase/frightened/eaten states
- **Persistent highscore system** (top 10, stored as JSON)
- **JSON configuration file** with `#` comment support
- **Cheat mode** for peer review testing
- **Full UI**: main menu, in-game HUD, pause, game over, and victory screens
- **Deployment**: Play the standalone build on [Itch.io](https://smikhail.itch.io/pac-man-42)

---

## Instructions

### Requirements
- Python 3.10 or later
- pip

### Installation

```bash
# Clone the repository and enter the project
cd pac-man/

# Install all dependencies (pygame, flake8, mypy, pytest)
# and the mazegenerator package
make install
```

### Running

```bash
make run
# Equivalent to: python3 pac-man.py config.json
```

### Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move Pac-Man |
| P / Escape | Pause / Resume |
| C | Toggle cheat overlay |

### Debug mode

```bash
make debug   # launches python3 -m pdb pac-man.py config.json
```

### Linting

```bash
make lint         # flake8 + mypy (standard flags)
make lint-strict  # flake8 + mypy --strict
```

### Tests

```bash
make test    # runs pytest tests/
```

---

## Configuration

The game is configured via a JSON file passed as a command-line argument:

```bash
python3 pac-man.py config.json
```

Lines starting with `#` are treated as comments and ignored.

### Config Key Reference

| Key | Type | Default | Description |
|---|---|---|---|
| `highscore_filename` | `str` | `"highscores.json"` | Path to highscore file |
| `lives` | `int` | `3` | Starting lives (1–99) |
| `points_per_pacgum` | `int` | `10` | Score per pacgum eaten |
| `points_per_super_pacgum` | `int` | `50` | Score per super-pacgum |
| `points_per_ghost` | `int` | `200` | Base score per ghost eaten |
| `frightened_duration` | `float` | `7.0` | Seconds ghosts stay frightened |
| `ghost_respawn_delay` | `float` | `7.0` | Seconds before eaten ghost respawns |
| `level_max_time` | `int` | `90` | Time limit per level (seconds) |
| `timeout_behavior` | `str` | `"game_over"` | What happens on timeout: `"game_over"` or `"restart"` |
| `levels` | `list` | 10 default levels | Array of level configs (see below) |

### Level Config Keys

```json
{
  "levels": [
    {"width": 21, "height": 21, "seed": 42},
    {"width": 23, "height": 23, "seed": 0}
  ]
}
```

| Key | Default | Description |
|---|---|---|
| `width` | `21` | Maze width in cells (odd recommended) |
| `height` | `21` | Maze height in cells (odd recommended) |
| `seed` | `0` | RNG seed. `42` = fixed (level 1). `0` = random |

**Error handling:** Missing keys use defaults. Invalid values are clamped to safe ranges with a warning message. Unknown keys are silently ignored. No tracebacks are ever shown to the user.

---

## Highscore

### How it works

Highscores are stored in a JSON file (default: `highscores.json`) in the project directory. The file contains an array of up to **10 entries**, each with a `name` and `score` field.

### Format

```json
[
  {"name": "SOFIA", "score": 9420},
  {"name": "PLAYER1", "score": 3100}
]
```

### Rules
- **Top 10 only**: lower scores are discarded
- **Player names**: max 10 characters, uppercase alphanumeric + spaces only
- **Scores**: non-negative integers only
- **Persistence**: loaded at game start, saved atomically on game end (temp file + rename to prevent corruption)
- **Corruption recovery**: if the file is missing or corrupt, the game starts with an empty list and overwrites on save

### Why this implementation?

We chose a plain JSON file for simplicity, portability, and debuggability. It requires no database, no network, and is human-readable. The atomic save (write to `.tmp` + `os.replace()`) prevents partial writes from corrupting the file.

---

## Maze Generation

The game uses the external **`mazegenerator`** package (provided as a `.whl` file) to generate mazes. We do not write our own maze generator.

### Integration

Our adapter (`src/maze/maze_adapter.py`) is the **only file** that imports `MazeGenerator` directly. All game code uses `MazeAdapter`, which exposes a Pac-Man-friendly interface.

### Key parameters

```python
from mazegenerator import MazeGenerator
mg = MazeGenerator(size=(width, height), perfect=False, seed=seed)
```

- `perfect=False` — generates imperfect mazes with **loops**, required for Pac-Man gameplay
- `seed=42` — fixed seed for level 1 (reproducible)
- `seed=0` — random seed for levels 2+ (different maze each playthrough)

### Wall encoding

Each cell in `mg.maze` encodes its walls as a 4-bit integer:

| Bit | Value | Meaning |
|---|---|---|
| 0 | `1` | North wall (blocks UP) |
| 1 | `2` | East wall (blocks RIGHT) |
| 2 | `4` | South wall (blocks DOWN) |
| 3 | `8` | West wall (blocks LEFT) |
| all | `15` | Solid block — includes the "42" logo at center |

The `42` pattern embedded by the generator (cells = `15`) is treated as a decorative wall cluster. The player and ghosts spawn at the nearest walkable cells to the center and corners respectively.

---

## Implementation

### Game Loop

The game runs at a fixed **60 FPS** target using `pygame.time.Clock`. Delta time (`dt`) is capped at 50ms to prevent physics tunneling during lag spikes.

### Entity movement

Player and ghosts use **sub-cell interpolation**: they store both their current grid cell and a progress value (0.0–1.0) toward the next cell. The renderer uses the interpolated position for smooth movement. Player direction input is **buffered** — the next requested direction is applied automatically as soon as the current cell is reached.

### Ghost AI

| Ghost | Strategy |
|---|---|
| Blinky (Red) | BFS shortest path to player |
| Pinky (Pink) | Targets 4 cells ahead of player's facing direction |
| Inky (Cyan) | Fully random (no reversals) |
| Clyde (Orange) | BFS if distance > 8 cells, random if closer |

Ghost combo scoring: eating multiple ghosts in one frightened phase awards `base × 2^n` points (capped at 8×).

### State machine

```
MAIN_MENU → PLAYING ⇄ PAUSED → LEVEL_TRANSITION → PLAYING
                             ↘ GAME_OVER → ENTER_NAME → MAIN_MENU
                             ↘ VICTORY  → ENTER_NAME → MAIN_MENU
```

---

## General Software Architecture

```
pac-man.py                   # Entry point — arg parsing + error handling
├── src/config/              # JSON config loading + validation
│   └── config_loader.py     # ConfigLoader → GameConfig dataclass
├── src/maze/                # MazeGenerator adapter (single isolation layer)
│   └── maze_adapter.py      # MazeAdapter + Direction enum
├── src/game/                # Core game logic
│   ├── game.py              # Game state machine + main loop
│   ├── level.py             # Level setup + update + collision detection
│   ├── player.py            # Pac-Man entity + movement
│   ├── ghost.py             # Ghost base + Blinky/Pinky/Inky/Clyde AI
│   ├── pacgum.py            # Pacgum + SuperPacgum entities
│   └── scoring.py           # Score tracker + ghost combo
├── src/highscore/           # Persistent highscore system
│   └── highscore.py         # HighscoreManager — load/save/validate
├── src/ui/                  # All rendering and screen logic
│   ├── renderer.py          # Renderer — draws everything to pygame surface
│   └── screens/
│       └── main_menu.py     # Main menu screen
└── src/cheat/               # Cheat mode for peer review
    └── cheat_mode.py        # CheatMode — 6 cheats
```

**Key design decisions:**
- `maze_adapter.py` is the only file touching `MazeGenerator` — one place to update if the API changes
- `renderer.py` is the only file touching `pygame` display surfaces — keeps game logic pure
- All game config flows through the immutable `GameConfig` dataclass
- No global state — every component receives what it needs via constructor injection

---

## Cheat Mode

Activate by pressing **`C`** during gameplay. A reference panel appears in the top-right corner.

| Key | Cheat | Effect |
|---|---|---|
| `I` | Invincibility | Ghosts cannot kill the player (toggle) |
| `N` | Level skip | Win the current level immediately |
| `F` | Ghost freeze | All ghosts stop moving (toggle) |
| `L` | Extra life | Add +1 life |
| `S` | Speed boost | Player moves at 2× speed (toggle) |
| `G` | Scare ghosts | Trigger frightened mode on all ghosts |

---

## Project Management

See the [`docs/`](docs/) directory for:
- [`gantt.md`](docs/gantt.md) — Project timeline
- [`kanban.md`](docs/kanban.md) — Task tracking board
- [`risk_analysis.md`](docs/risk_analysis.md) — Risk register
- [`acceptance_tests.md`](docs/acceptance_tests.md) — Feature acceptance test plan

---

## Resources

### References
- [Pac-Man Dossier](https://www.gamedeveloper.com/design/the-pac-man-dossier) — Definitive analysis of original ghost AI
- [pygame documentation](https://www.pygame.org/docs/)
- [Python `typing` module docs](https://docs.python.org/3/library/typing.html)
- [flake8 docs](https://flake8.pycqa.org/)
- [mypy docs](https://mypy.readthedocs.io/)
- [PEP 257 — Docstring conventions](https://peps.python.org/pep-0257/)

### AI Usage
AI (Antigravity / Claude) was used for:
- **Development plan creation**: translating the subject PDF requirements into a structured 11-phase implementation plan
- **Boilerplate generation**: initial file structures, `__init__.py` files, `Makefile` targets
- **Test scaffolding**: generating pytest test cases for config, highscore, maze, and scoring modules

All AI-generated code was reviewed, understood, and validated by the team before inclusion. The core game logic (ghost AI strategies, collision detection, state machine transitions) was designed and written by smikhail and evieito-.
