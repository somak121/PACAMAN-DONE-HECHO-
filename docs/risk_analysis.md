# PAC-MAN — Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A-Maze-ing API changes during peer review (re-installed) | Medium | High | `maze_adapter.py` isolates all API calls — only one file to fix ✅ |
| "42" center pattern blocks player/ghost spawn | Medium | High | `get_center()` / `get_corners()` use BFS to find nearest walkable cell ✅ |
| Ghost BFS too slow on large mazes (29×29) | Low | Medium | BFS is O(n) per ghost per frame; cache paths if needed ✅ |
| PyInstaller packaging fails on macOS (Gatekeeper) | Medium | Medium | Test early; use `--onedir` mode; document how to allow app in System Preferences ✅ |
| Itch.io upload rejected or broken | Low | Low | Test with a minimal build first; keep source zip as backup ✅ |
| flake8/mypy strict errors cause late rework | Medium | Medium | Enable linting from day 1 — run `make lint` before every commit ✅ |
| Peer evaluator doesn't know cheat mode exists | Low | Medium | Cheat codes listed in Instructions screen AND in README ✅ |
| Config file modified during evaluation breaks game | Low | High | All config errors clamped/defaulted — game never crashes on bad config ✅ |
