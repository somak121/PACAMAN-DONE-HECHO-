"""Main game state machine and loop for Pac-Man.

States:
    MAIN_MENU         — showing the main menu
    PLAYING           — active gameplay
    PAUSED            — game paused (overlay shown)
    LEVEL_TRANSITION  — brief 'Level N Complete' splash
    GAME_OVER         — player lost all lives
    VICTORY           — player beat all levels
    ENTER_NAME        — name entry after game ends
"""

import logging
from enum import Enum, auto
from typing import Optional

import pygame

from src.config.config_loader import GameConfig
from src.game.level import Level
from src.game.scoring import ScoreTracker
from src.highscore.highscore import HighscoreManager
from src.cheat.cheat_mode import CheatMode
from src.maze.maze_adapter import Direction

logger = logging.getLogger(__name__)

FPS: int = 60
WINDOW_TITLE: str = "PAC-MAN — 42 Project"
TRANSITION_DURATION: float = 2.0  # seconds between levels


class GameState(Enum):
    """All possible game states."""

    MAIN_MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    LEVEL_TRANSITION = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    ENTER_NAME = auto()
    INSTRUCTIONS = auto()
    HIGHSCORES = auto()


# Keyboard → Direction mapping
KEY_DIRECTIONS = {
    pygame.K_UP: Direction.NORTH,
    pygame.K_w: Direction.NORTH,
    pygame.K_DOWN: Direction.SOUTH,
    pygame.K_s: Direction.SOUTH,
    pygame.K_LEFT: Direction.WEST,
    pygame.K_a: Direction.WEST,
    pygame.K_RIGHT: Direction.EAST,
    pygame.K_d: Direction.EAST,
}


class Game:
    """Top-level game controller — owns the state machine and main loop.

    Args:
        config: Validated game configuration.
    """

    def __init__(self, config: GameConfig) -> None:
        """Initialize pygame display, highscores, and game state."""
        self._cfg = config
        self._state: GameState = GameState.MAIN_MENU
        self._level_index: int = 0
        self._score = ScoreTracker(
            points_per_pacgum=config.points_per_pacgum,
            points_per_super_pacgum=config.points_per_super_pacgum,
            points_per_ghost=config.points_per_ghost,
        )
        self._lives: int = config.lives
        self._current_level: Optional[Level] = None
        self._transition_timer: float = 0.0
        self._won: bool = False  # True = victory, False = game over
        self._entered_name: str = ""
        self._name_cursor_visible: bool = True
        self._name_cursor_timer: float = 0.0

        # Highscores
        self._highscores = HighscoreManager(config.highscore_filename)

        # Cheat mode
        self._cheat = CheatMode()
        self._cheat_overlay_visible: bool = False

        # Display
        self._cell_size: int = 24  # pixels per cell (adjusted per level)
        self._screen: pygame.Surface = self._create_window()
        self._clock = pygame.time.Clock()

        # Lazy import renderer and screens to keep imports clean
        self._renderer: Optional[object] = None
        self._init_renderer()

        # Main menu — created here so it works from the very first frame
        from src.ui.screens.main_menu import MainMenu

        self._menu: Optional[MainMenu] = MainMenu()

    def _create_window(self) -> pygame.Surface:
        """Create the pygame window.

        Returns:
            Main pygame display surface.
        """
        screen = pygame.display.set_mode((800, 800), pygame.RESIZABLE)
        pygame.display.set_caption(WINDOW_TITLE)
        try:
            icon = pygame.Surface((32, 32))
            icon.fill((255, 255, 0))
            pygame.display.set_icon(icon)
        except Exception:
            pass
        return screen

    def _init_renderer(self) -> None:
        """Lazily initialize the renderer."""
        try:
            from src.ui.renderer import Renderer

            self._renderer = Renderer(self._screen)
        except Exception as e:
            logger.error("Failed to initialize renderer: %s", e)
            raise

    # ------------------------------------------------------------------ #
    #  Main loop
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Run the main game loop until the window is closed."""
        logger.info("Game loop started")
        running = True
        while running:
            dt = self._clock.tick(FPS) / 1000.0  # seconds
            dt = min(dt, 0.05)  # cap dt to prevent spiral of death

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self._handle_event(event)

            self._update(dt)
            self._draw()
            pygame.display.flip()

        self._highscores.save()
        logger.info("Game loop ended")

    # ------------------------------------------------------------------ #
    #  Event handling
    # ------------------------------------------------------------------ #

    def _handle_event(self, event: pygame.event.Event) -> None:
        """Dispatch events based on current game state.

        Args:
            event: The pygame event to handle.
        """
        if self._state == GameState.MAIN_MENU:
            self._handle_menu_event(event)
        elif self._state == GameState.PLAYING:
            self._handle_playing_event(event)
        elif self._state == GameState.PAUSED:
            self._handle_pause_event(event)
        elif self._state == GameState.ENTER_NAME:
            self._handle_name_event(event)
        elif self._state in (GameState.INSTRUCTIONS, GameState.HIGHSCORES):
            self._handle_info_screens_event(event)

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        """Handle keyboard/mouse in the main menu."""
        if self._menu is None:
            return
        action = self._menu.handle_event(event)
        if action == "start":
            self._start_new_game()
        elif action == "highscores":
            self._state = GameState.HIGHSCORES
        elif action == "instructions":
            self._state = GameState.INSTRUCTIONS
        elif action == "exit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _handle_info_screens_event(self, event: pygame.event.Event) -> None:
        """Return to main menu on ESC, ENTER, or SPACE."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self._state = GameState.MAIN_MENU
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._state = GameState.MAIN_MENU

    def _handle_playing_event(self, event: pygame.event.Event) -> None:
        """Handle keyboard in PLAYING state."""
        if event.type != pygame.KEYDOWN:
            return
        key = event.key

        # Pause
        if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_k):
            self._state = GameState.PAUSED
            return

        # Cheat overlay toggle
        if key == pygame.K_h:
            self._cheat_overlay_visible = not self._cheat_overlay_visible
            return

        # Cheat shortcuts (work anytime)
        self._handle_cheat_key(key)

        # Player direction
        if key in KEY_DIRECTIONS and self._current_level:
            self._current_level.player.set_direction(KEY_DIRECTIONS[key])

    def _handle_cheat_key(self, key: int) -> None:
        """Apply cheat mode actions.

        Args:
            key: Pygame key constant.
        """
        if not self._current_level:
            return
        level = self._current_level
        if key == pygame.K_i:
            self._cheat.toggle_invincibility(level.player)
        elif key == pygame.K_n:
            self._cheat.skip_level(level)
        elif key == pygame.K_f:
            self._cheat.toggle_ghost_freeze(level.ghosts)
        elif key == pygame.K_l:
            self._cheat.add_life(level.player)
        elif key == pygame.K_c:
            self._cheat.toggle_speed_boost(level.player)
        elif key == pygame.K_g:
            self._cheat.scare_all_ghosts(level.ghosts, self._cfg.frightened_duration)

    def _handle_pause_event(self, event: pygame.event.Event) -> None:
        """Handle keyboard in PAUSED state."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_k):
            self._state = GameState.PLAYING
        elif event.key == pygame.K_m:
            self._reset_to_menu()

    def _handle_name_event(self, event: pygame.event.Event) -> None:
        """Handle text input for name entry screen.

        Args:
            event: Pygame event.
        """
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_RETURN:
            name = self._entered_name.strip() or "PLAYER"
            self._highscores.add_entry(name, self._score.score)
            self._highscores.save()
            self._reset_to_menu()
        elif key == pygame.K_BACKSPACE:
            self._entered_name = self._entered_name[:-1]
        else:
            char = event.unicode
            if (char.isalnum() or char == " ") and len(self._entered_name) < 10:
                self._entered_name += char.upper()

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #

    def _update(self, dt: float) -> None:
        """Update game logic for the current state.

        Args:
            dt: Delta time in seconds.
        """
        if self._state == GameState.PLAYING:
            self._update_playing(dt)
        elif self._state == GameState.LEVEL_TRANSITION:
            self._update_transition(dt)
        elif self._state == GameState.ENTER_NAME:
            self._update_name_cursor(dt)

    def _update_playing(self, dt: float) -> None:
        """Update the active level and check for state transitions."""
        if not self._current_level:
            return
        level = self._current_level
        level.update(dt)

        if level.complete:
            self._level_index += 1
            if self._level_index >= len(self._cfg.levels):
                # All levels beaten
                self._state = GameState.VICTORY
                self._won = True
                self._entered_name = ""
            else:
                self._state = GameState.LEVEL_TRANSITION
                self._transition_timer = TRANSITION_DURATION
        elif level.failed:
            if level.player.lives <= 0:
                self._state = GameState.GAME_OVER
                self._won = False
                self._entered_name = ""
            else:
                # Timeout with restart behavior — recreate same level
                self._load_level()

    def _update_transition(self, dt: float) -> None:
        """Count down the between-level splash screen."""
        self._transition_timer -= dt
        if self._transition_timer <= 0.0:
            self._load_level()
            self._state = GameState.PLAYING

    def _update_name_cursor(self, dt: float) -> None:
        """Blink the text cursor on the name entry screen."""
        self._name_cursor_timer -= dt
        if self._name_cursor_timer <= 0.0:
            self._name_cursor_visible = not self._name_cursor_visible
            self._name_cursor_timer = 0.5

    # ------------------------------------------------------------------ #
    #  Drawing
    # ------------------------------------------------------------------ #

    def _draw(self) -> None:
        """Dispatch rendering to the appropriate screen."""
        if self._renderer is None:
            return

        from src.ui.renderer import Renderer

        r: Renderer = self._renderer  # type: ignore

        if self._state == GameState.MAIN_MENU:
            selected = self._menu.selected if self._menu else 0
            r.draw_main_menu(self._highscores.get_top_10(), selected)
        elif self._state in (GameState.PLAYING, GameState.PAUSED):
            if self._current_level:
                r.draw_game(
                    self._current_level,
                    self._score.score,
                    paused=(self._state == GameState.PAUSED),
                    cheat_overlay=self._cheat_overlay_visible,
                )
        elif self._state == GameState.LEVEL_TRANSITION:
            if self._current_level:
                r.draw_level_transition(self._level_index)
        elif self._state == GameState.GAME_OVER:
            r.draw_game_over(self._score.score)
            self._state = GameState.ENTER_NAME
        elif self._state == GameState.VICTORY:
            r.draw_victory(self._score.score)
            self._state = GameState.ENTER_NAME
        elif self._state == GameState.ENTER_NAME:
            r.draw_name_entry(
                self._score.score,
                self._entered_name,
                self._name_cursor_visible,
                won=self._won,
            )
        elif self._state == GameState.INSTRUCTIONS:
            r.draw_instructions()
        elif self._state == GameState.HIGHSCORES:
            r.draw_highscore_screen(self._highscores.get_top_10())

    # ------------------------------------------------------------------ #
    #  State helpers
    # ------------------------------------------------------------------ #

    def _start_new_game(self) -> None:
        """Reset everything and start from level 1."""
        self._level_index = 0
        self._lives = self._cfg.lives
        self._score.reset()
        self._load_level()
        self._state = GameState.PLAYING

    def _load_level(self) -> None:
        """Instantiate the current level from config."""
        cfg = self._cfg.levels[self._level_index]
        lives = self._current_level.player.lives if self._current_level else self._lives
        try:
            self._current_level = Level(
                level_cfg=cfg,
                game_cfg=self._cfg,
                score=self._score,
                lives=lives,
                level_number=self._level_index + 1,
            )
        except RuntimeError as e:
            logger.error("Failed to load level %d: %s", self._level_index + 1, e)
            raise

    def _reset_to_menu(self) -> None:
        """Return to main menu and reset menu selection."""
        self._current_level = None
        self._state = GameState.MAIN_MENU
        self._cheat_overlay_visible = False
        if self._menu is not None:
            self._menu.reset()
