"""Main menu screen for Pac-Man."""

import math
import pygame
from typing import Optional, List, Any

MENU_BG = (8, 8, 25)
YELLOW = (255, 220, 0)
CYAN = (0, 255, 255)
WHITE = (255, 255, 255)
DIM = (150, 150, 180)
HIGHLIGHT = (255, 255, 100)
RED = (255, 80, 80)
GREEN = (80, 255, 120)
SELECTED_BG = (30, 30, 80)

ITEMS = ["START GAME", "HIGHSCORES", "INSTRUCTIONS", "EXIT"]


class MainMenu:
    """Interactive main menu with keyboard navigation.

    Tracks the currently selected item and emits action strings
    when the user confirms a selection.
    """

    def __init__(self) -> None:
        """Initialize menu with first item selected."""
        self._selected: int = 0

    @property
    def selected(self) -> int:
        """Currently highlighted menu index (0-based)."""
        return self._selected

    def reset(self) -> None:
        """Reset selection back to the first item."""
        self._selected = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Process an input event and return an action string if triggered.

        Supported keys: UP / DOWN to navigate, ENTER or SPACE to confirm.

        Args:
            event: Pygame event.

        Returns:
            One of 'start', 'highscores', 'instructions', 'exit', or None.
        """
        action_map = {
            0: "start",
            1: "highscores",
            2: "instructions",
            3: "exit",
        }
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(ITEMS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return action_map.get(self._selected)
        return None

    @staticmethod
    def draw(
        screen: pygame.Surface,
        font_xl: pygame.font.Font,
        font_lg: pygame.font.Font,
        font_md: pygame.font.Font,
        font_sm: pygame.font.Font,
        highscores: List[Any],
        selected: int = 0,
    ) -> None:
        """Draw the main menu on the given surface.

        Args:
            screen: Target surface.
            font_xl: Extra-large font for title.
            font_lg: Large font for menu items.
            font_md: Medium font for subtitle.
            font_sm: Small font for highscores.
            highscores: Top-10 highscore entries to display on the side.
            selected: Currently highlighted item index.
        """
        w, h = screen.get_size()
        tick = pygame.time.get_ticks() / 1000.0

        # Animated title with colour pulse
        r_val = int(220 + 35 * math.sin(tick * 1.5))
        title_color = (r_val, 210, 0)
        title_surf = font_xl.render("PAC-MAN", True, title_color)
        screen.blit(title_surf, ((w - title_surf.get_width()) // 2, 55))

        subtitle = font_md.render("Waka Waka! — 42 Project", True, DIM)
        screen.blit(subtitle, ((w - subtitle.get_width()) // 2, 125))

        # Menu items
        item_start_y = 200
        item_gap = 75
        for i, item in enumerate(ITEMS):
            item_y = item_start_y + i * item_gap
            item_w = 340
            item_x = (w - item_w) // 2

            if i == selected:
                # Draw selection highlight box
                pygame.draw.rect(
                    screen,
                    SELECTED_BG,
                    (item_x - 10, item_y - 8, item_w + 20, 52),
                    border_radius=8,
                )
                pygame.draw.rect(
                    screen,
                    CYAN,
                    (item_x - 10, item_y - 8, item_w + 20, 52),
                    2,
                    border_radius=8,
                )
                # Animated arrow
                arrow_x = item_x - 30 + int(4 * math.sin(tick * 6))
                arrow = font_lg.render("▶", True, CYAN)
                screen.blit(arrow, (arrow_x, item_y))
                text_color = HIGHLIGHT
            else:
                text_color = WHITE

            surf = font_lg.render(item, True, text_color)
            screen.blit(surf, (item_x, item_y))

        # Highscore sidebar
        hs_x = w - 230
        hs_title = font_sm.render("── TOP SCORES ──", True, CYAN)
        screen.blit(hs_title, (hs_x - hs_title.get_width() // 2 + 90, 210))
        if not highscores:
            no_hs = font_sm.render("No scores yet!", True, DIM)
            screen.blit(no_hs, (hs_x, 248))
        for rank, entry in enumerate(highscores[:5], 1):
            name = str(entry.get("name", "???"))[:10]
            sc = int(entry.get("score", 0))
            color = YELLOW if rank == 1 else DIM
            line = font_sm.render(f"{rank}. {name:<10} {sc:>6,}", True, color)
            screen.blit(line, (hs_x - 10, 230 + rank * 30))

        # Controls hint at the bottom
        hint = font_sm.render("↑ ↓  Navigate     ENTER  Select", True, DIM)
        screen.blit(hint, ((w - hint.get_width()) // 2, h - 38))
