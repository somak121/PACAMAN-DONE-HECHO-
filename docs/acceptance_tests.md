# PAC-MAN — Acceptance Test Plan

## Feature Tests

| # | Feature | Test Method | Expected | Status |
|---|---|---|---|---|
| 1 | Launch with valid config | `python3 pac-man.py config.json` | Game window opens | ✅ |
| 2 | Launch without args | `python3 pac-man.py` | Clean usage error, no traceback | ✅ |
| 3 | Launch with missing file | `python3 pac-man.py missing.json` | Clean file-not-found error | ✅ |
| 4 | Launch with invalid JSON | Feed broken JSON file | Clean parse error, no traceback | ✅ |
| 5 | Config bad values | Set `lives=-5` | Warning logged, game uses default (3) | ✅ |
| 6 | Config unknown keys | Add `"foo": "bar"` | Key silently ignored, game starts | ✅ |
| 7 | Main menu navigation | Arrow keys | Selection moves, Enter triggers action | ✅ |
| 8 | Start game | Select "START GAME" | Level 1 loads, player in center | ✅ |
| 9 | Player movement | Arrow keys / WASD | Player moves through corridors only | ✅ |
| 10 | Wall collision | Move into wall | Player stops at wall | ✅ |
| 11 | Eat pacgum | Move over pacgum | Score increases, dot disappears | ✅ |
| 12 | Eat super-pacgum | Move over corner pellet | Score increases, ghosts turn blue | ✅ |
| 13 | Ghost frightened | After super-pacgum | Ghosts flee player for N seconds | ✅ |
| 14 | Eat frightened ghost | Collide with blue ghost | Ghost eaten, score increases (combo) | ✅ |
| 15 | Ghost returns | After being eaten | Ghost respawns in corner after delay | ✅ |
| 16 | Ghost kills player | Collide with chasing ghost | Life lost, player respawns at center | ✅ |
| 17 | Lose all lives | Die 3 times | Game Over screen shown | ✅ |
| 18 | Win level | Eat all pacgums | Level complete splash, next level loads | ✅ |
| 19 | Level progression | Beat level 1 | Level 2 loads with different maze | ✅ |
| 20 | Score persists across levels | Beat level 1 with 500 pts | Level 2 starts with score = 500 | ✅ |
| 21 | Lives persist across levels | Beat level 1 with 2 lives | Level 2 starts with 2 lives | ✅ |
| 22 | Win all levels | Beat all 10 levels | Victory screen shown | ✅ |
| 23 | Timer counts down | Watch HUD | Timer bar decreases, turns red < 15s | ✅ |
| 24 | Timeout game over | Wait 90s | Game Over screen (default behavior) | ✅ |
| 25 | Pause / Resume | Press P | Game freezes, press P again to resume | ✅ |
| 26 | Name entry | Game over → type name | Input shown, max 10 chars enforced | ✅ |
| 27 | Highscore saved | Enter name after game | Score appears in highscore list | ✅ |
| 28 | Highscore persists | Restart game | Previous score still in list | ✅ |
| 29 | View highscores | Main menu | Top 10 shown with names and scores | ✅ |
| 30 | Cheat overlay | Press C in game | Overlay appears with key reference | ✅ |
| 31 | Cheat: Invincibility | Press I | Ghosts walk through player without killing | ✅ |
| 32 | Cheat: Level skip | Press N | Level completes immediately | ✅ |
| 33 | Cheat: Ghost freeze | Press F | All ghosts stop moving | ✅ |
| 34 | Cheat: Extra life | Press L | Lives counter increases by 1 | ✅ |
| 35 | Cheat: Speed boost | Press S | Player visibly moves faster | ✅ |
| 36 | Cheat: Scare ghosts | Press G | All ghosts turn blue | ✅ |
| 37 | `make lint` passes | Run `make lint` | 0 flake8 errors, 0 mypy errors | ✅ |
| 38 | `make test` passes | Run `make test` | 45/45 tests green | ✅ |
| 39 | Packaged build runs | Run PyInstaller build | Executable launches without Python | ✅ |
| 40 | Itch.io accessible | Visit Itch.io page | Game download works, build is functional | ✅ |
