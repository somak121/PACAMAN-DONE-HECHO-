"""
pac-man.py — Entry point for the Pac-Man 42 project.

Usage:
    python3 pac-man.py <config.json>

The program takes exactly one argument: a path to a JSON configuration file.
Lines starting with '#' in the JSON file are treated as comments and ignored.
"""

import sys
import os


def main() -> None:
    """Parse CLI args, load config, and launch the game."""
    if len(sys.argv) != 2:
        print("Usage: python3 pac-man.py <config.json>")
        sys.exit(1)

    config_path = sys.argv[1]

    if not config_path.endswith(".json"):
        print(f"Error: config file must be a .json file, got: {config_path}")
        sys.exit(1)

    if not os.path.isfile(config_path):
        print(f"Error: config file not found: {config_path}")
        sys.exit(1)

    try:
        from src.config.config_loader import ConfigLoader
        config = ConfigLoader.load(config_path)
    except Exception as e:
        print(f"Error: failed to load config: {e}")
        sys.exit(1)

    try:
        import pygame
        pygame.init()
    except ImportError:
        print("Error: pygame is not installed. Run: make install")
        sys.exit(1)
    except Exception as e:
        print(f"Error: failed to initialize pygame: {e}")
        sys.exit(1)

    try:
        from src.game.game import Game
        game = Game(config)
        game.run()
    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    except Exception as e:
        print(f"Error: unexpected game error: {e}")
        sys.exit(1)
    finally:
        try:
            import pygame
            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
