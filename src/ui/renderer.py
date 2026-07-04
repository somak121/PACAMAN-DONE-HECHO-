"""Central pygame renderer for Pac-Man.

Handles all drawing operations: maze, entities, HUD, and all screens.
All rendering goes through this single class to keep display logic centralized.
"""

import math
import pygame
from typing import TYPE_CHECKING, List, Tuple, Any

if TYPE_CHECKING:
    from src.game.level import Level

# ── Colour palette ────────────────────────────────────────────────────────────
BG_COLOR = (10, 10, 30)  # deep navy background
WALL_COLOR = (30, 80, 220)  # classic arcade blue walls
WALL_BORDER = (60, 130, 255)  # lighter wall border
CORRIDOR_COLOR = (15, 15, 40)  # slightly lighter than background
PACGUM_COLOR = (255, 220, 180)  # warm dot color
SUPER_PACGUM_COLOR = (255, 255, 100)  # bright yellow power pellet
PACMAN_COLOR = (255, 220, 0)  # classic yellow
GHOST_FRIGHTENED = (50, 80, 255)  # blue frightened ghost
GHOST_BLINK = (255, 255, 255)  # white blinking near end of frightened
GHOST_EATEN = (200, 200, 200)  # translucent eyes-only style
TEXT_COLOR = (255, 255, 255)
DIM_TEXT = (180, 180, 200)
FRUIT_COLOR = (255, 100, 100)
YELLOW = (255, 220, 0)
CYAN = (0, 255, 255)
RED = (255, 60, 60)
GREEN = (60, 255, 120)
ORANGE = (255, 160, 40)
MENU_BG = (8, 8, 25)
OVERLAY_BG = (0, 0, 0, 180)  # semi-transparent
TIMER_OK = (60, 200, 80)
TIMER_WARN = (255, 180, 0)
TIMER_CRIT = (255, 50, 50)

HUD_HEIGHT: int = 60  # pixels reserved at top for HUD
MARGIN: int = 8


def _get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Return a system font at the given size.

    Args:
        size: Font size in points.
        bold: Whether to use bold weight.

    Returns:
        A pygame Font object.
    """
    try:
        return pygame.font.SysFont("couriernew,monospace", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


class Renderer:
    """Handles all pygame drawing for Pac-Man.

    Args:
        screen: The main pygame display surface.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize renderer with the given display surface."""
        self._screen = screen
        self._cell_size: int = 24
        self._offset_x: int = 0
        self._offset_y: int = HUD_HEIGHT + MARGIN

        # Fonts
        self._font_xl = _get_font(56, bold=True)
        self._font_lg = _get_font(36, bold=True)
        self._font_md = _get_font(24, bold=False)
        self._font_sm = _get_font(18, bold=False)
        self._font_hud = _get_font(20, bold=True)

        # Animation tick
        self._tick: float = 0.0

    # ------------------------------------------------------------------ #
    #  Public draw methods (called by Game)
    # ------------------------------------------------------------------ #

    def draw_main_menu(self, highscores: List[Any], selected: int = 0) -> None:
        """Draw the main menu screen.

        Args:
            highscores: List of top-10 highscore dicts for display.
            selected: Index of the currently highlighted menu item.
        """
        from src.ui.screens.main_menu import MainMenu

        self._screen.fill(MENU_BG)
        self._draw_starfield()
        MainMenu.draw(
            self._screen,
            self._font_xl,
            self._font_lg,
            self._font_md,
            self._font_sm,
            highscores,
            selected,
        )

    def draw_game(
        self,
        level: "Level",
        score: int,
        paused: bool = False,
        cheat_overlay: bool = False,
    ) -> None:
        """Draw the in-game view: maze, entities, HUD, and overlays.

        Args:
            level: The current Level instance.
            score: Current score.
            paused: Whether to show the pause overlay.
            cheat_overlay: Whether to show cheat key reference.
        """
        self._tick += 0.016
        self._screen.fill(BG_COLOR)

        # Compute cell size and offsets from maze dimensions
        w, h = self._screen.get_size()
        maze_w = level.maze.width
        maze_h = level.maze.height
        available_w = w - 2 * MARGIN
        available_h = h - HUD_HEIGHT - 2 * MARGIN
        self._cell_size = max(8, min(available_w // maze_w, available_h // maze_h))
        grid_px_w = maze_w * self._cell_size
        grid_px_h = maze_h * self._cell_size
        self._offset_x = (w - grid_px_w) // 2
        self._offset_y = HUD_HEIGHT + (h - HUD_HEIGHT - grid_px_h) // 2

        # Draw layers
        self._draw_maze(level.maze)
        self._draw_pacgums(level.pacgums, level.super_pacgums)
        self._draw_ghosts(level.ghosts)
        self._draw_fruits(level.fruits)
        self._draw_player(level.player)
        self._draw_hud(
            score=score,
            lives=level.player.lives,
            level_num=level.level_number,
            time_remaining=level.time_remaining,
            time_max=float(level._cfg.level_max_time),
            total_pacgums=level.total_pacgums,
            remaining_pacgums=level.pacgums_remaining,
        )

        if paused:
            self._draw_pause_overlay()
        if cheat_overlay:
            self._draw_cheat_overlay(level.player)

    def draw_level_transition(self, next_level: int) -> None:
        """Draw the between-level splash screen.

        Args:
            next_level: The 1-based index of the NEXT level.
        """
        self._screen.fill(BG_COLOR)
        self._draw_starfield()
        self._draw_centered_text(
            f"LEVEL {next_level} COMPLETE!", self._font_xl, GREEN, offset_y=-60
        )
        self._draw_centered_text(
            f"GET READY FOR LEVEL {next_level + 1}",
            self._font_md,
            YELLOW,
            offset_y=20,
        )

    def draw_game_over(self, score: int) -> None:
        """Draw the game over screen.

        Args:
            score: Final score.
        """
        self._screen.fill(BG_COLOR)
        self._draw_starfield()
        self._draw_centered_text("GAME OVER", self._font_xl, RED, offset_y=-80)
        self._draw_centered_text(
            f"FINAL SCORE: {score:,}", self._font_lg, YELLOW, offset_y=10
        )

    def draw_victory(self, score: int) -> None:
        """Draw the victory screen.

        Args:
            score: Final score.
        """
        self._screen.fill(BG_COLOR)
        self._draw_starfield()
        self._draw_centered_text(
            "YOU WIN! WAKA-WAKA!", self._font_xl, GREEN, offset_y=-80
        )
        self._draw_centered_text(
            f"FINAL SCORE: {score:,}", self._font_lg, YELLOW, offset_y=10
        )

    def draw_instructions(self) -> None:
        """Draw the instructions and cheat sheet screen."""
        self._screen.fill(MENU_BG)
        self._draw_starfield()
        self._draw_centered_text("INSTRUCTIONS", self._font_xl, CYAN, offset_y=-180)

        lines = [
            ("CONTROLS", YELLOW),
            ("Arrow Keys / WASD : Move Pac-Man", TEXT_COLOR),
            ("P / ESC / K : Pause Game", TEXT_COLOR),
            ("H : Toggle Cheat Menu Overlay", TEXT_COLOR),
            ("", TEXT_COLOR),
            ("CHEAT CODES (Press during gameplay)", YELLOW),
            ("I : Toggle Invincibility", TEXT_COLOR),
            ("N : Skip Level", TEXT_COLOR),
            ("F : Toggle Ghost Freeze", TEXT_COLOR),
            ("L : Add 1 Life", TEXT_COLOR),
            ("C : Toggle Speed Boost", TEXT_COLOR),
            ("G : Scare Ghosts (Frightened Mode)", TEXT_COLOR),
        ]

        y_offset = -80
        for text, color in lines:
            if text:
                self._draw_centered_text(text, self._font_sm, color, offset_y=y_offset)
            y_offset += 25

        self._draw_centered_text(
            "Press ESC to return", self._font_md, DIM_TEXT, offset_y=y_offset + 30
        )

    def draw_highscore_screen(self, highscores: List[Any]) -> None:
        """Draw the highscore leaderboard."""
        self._screen.fill(MENU_BG)
        self._draw_starfield()
        self._draw_centered_text(
            "TOP 10 HIGHSCORES", self._font_xl, YELLOW, offset_y=-180
        )

        y_offset = -80
        for i, entry in enumerate(highscores):
            rank = str(i + 1).rjust(2, " ")
            name = entry["name"].ljust(10, " ")
            score_str = f"{entry['score']:,}".rjust(8, " ")
            text = f"{rank}. {name} - {score_str}"
            self._draw_centered_text(text, self._font_md, TEXT_COLOR, offset_y=y_offset)
            y_offset += 30

        self._draw_centered_text(
            "Press ESC to return", self._font_md, DIM_TEXT, offset_y=y_offset + 30
        )

    def draw_name_entry(
        self,
        score: int,
        name: str,
        cursor_visible: bool,
        won: bool,
    ) -> None:
        """Draw the name entry screen after game ends.

        Args:
            score: Final score.
            name: Current name input.
            cursor_visible: Whether the text cursor should be shown.
            won: True for victory, False for game over.
        """
        self._screen.fill(BG_COLOR)
        self._draw_starfield()
        title = "CONGRATULATIONS!" if won else "GAME OVER"
        color = GREEN if won else RED
        self._draw_centered_text(title, self._font_xl, color, offset_y=-120)
        self._draw_centered_text(
            f"SCORE: {score:,}", self._font_lg, YELLOW, offset_y=-40
        )
        self._draw_centered_text(
            "ENTER YOUR NAME:", self._font_md, TEXT_COLOR, offset_y=40
        )
        cursor = "_" if cursor_visible else " "
        display_name = name + cursor
        self._draw_centered_text(display_name, self._font_lg, CYAN, offset_y=90)
        self._draw_centered_text(
            "Press ENTER to save", self._font_sm, DIM_TEXT, offset_y=160
        )

    # ------------------------------------------------------------------ #
    #  Maze drawing
    # ------------------------------------------------------------------ #

    def _draw_maze(self, maze: object) -> None:
        """Draw the maze walls and corridors using bit-encoded cell data.

        Args:
            maze: MazeAdapter instance.
        """
        from src.maze.maze_adapter import MazeAdapter, SOLID

        m: MazeAdapter = maze  # type: ignore
        cs = self._cell_size
        ox, oy = self._offset_x, self._offset_y
        wall_thickness = max(2, cs // 5)

        for y in range(m.height):
            for x in range(m.width):
                px = ox + x * cs
                py = oy + y * cs
                cell = m.raw_grid[y][x]

                # Draw cell background
                cell_rect = pygame.Rect(px, py, cs, cs)
                if cell == SOLID:
                    pygame.draw.rect(self._screen, WALL_COLOR, cell_rect)
                    pygame.draw.rect(self._screen, WALL_BORDER, cell_rect, 1)
                else:
                    pygame.draw.rect(self._screen, CORRIDOR_COLOR, cell_rect)
                    # Draw individual walls
                    if cell & 1:  # North
                        pygame.draw.rect(
                            self._screen,
                            WALL_COLOR,
                            (px, py, cs, wall_thickness),
                        )
                    if cell & 2:  # East
                        pygame.draw.rect(
                            self._screen,
                            WALL_COLOR,
                            (px + cs - wall_thickness, py, wall_thickness, cs),
                        )
                    if cell & 4:  # South
                        pygame.draw.rect(
                            self._screen,
                            WALL_COLOR,
                            (px, py + cs - wall_thickness, cs, wall_thickness),
                        )
                    if cell & 8:  # West
                        pygame.draw.rect(
                            self._screen,
                            WALL_COLOR,
                            (px, py, wall_thickness, cs),
                        )

    # ------------------------------------------------------------------ #
    #  Entity drawing
    # ------------------------------------------------------------------ #

    def _draw_pacgums(self, pacgums: List[Any], super_pacgums: List[Any]) -> None:
        """Draw all uneaten pacgums and super-pacgums.

        Args:
            pacgums: List of Pacgum objects.
            super_pacgums: List of SuperPacgum objects.
        """
        cs = self._cell_size
        ox, oy = self._offset_x, self._offset_y
        dot_r = max(2, cs // 8)
        pellet_r = max(4, cs // 4)

        for pg in pacgums:
            if not pg.eaten:
                cx = ox + pg.pos[0] * cs + cs // 2
                cy = oy + pg.pos[1] * cs + cs // 2
                pygame.draw.circle(self._screen, PACGUM_COLOR, (cx, cy), dot_r)

        # Super-pacgum pulsing animation
        pulse = abs(math.sin(self._tick * 3.0))
        for spg in super_pacgums:
            if not spg.eaten:
                cx = ox + spg.pos[0] * cs + cs // 2
                cy = oy + spg.pos[1] * cs + cs // 2
                r = int(pellet_r * (0.8 + 0.4 * pulse))
                pygame.draw.circle(self._screen, SUPER_PACGUM_COLOR, (cx, cy), r)
                # Glow ring
                pygame.draw.circle(
                    self._screen, (*SUPER_PACGUM_COLOR, 80), (cx, cy), r + 3, 2
                )

    def _draw_fruits(self, fruits: List[Any]) -> None:
        """Draw all active fruits in the maze.

        Args:
            fruits: List of Fruit objects.
        """
        from src.game.fruit import FruitType

        cs = self._cell_size
        ox, oy = self._offset_x, self._offset_y

        for fruit in fruits:
            if fruit.eaten:
                continue

            fx, fy = fruit.pos
            cx = ox + fx * cs + cs // 2
            cy = oy + fy * cs + cs // 2
            r = max(4, cs // 2 - 2)

            if fruit.type == FruitType.CHERRY:
                # Two red circles with green stems
                pygame.draw.circle(
                    self._screen, FRUIT_COLOR, (cx - r // 3, cy + r // 3), r // 2
                )
                pygame.draw.circle(
                    self._screen, FRUIT_COLOR, (cx + r // 3, cy + r // 3), r // 2
                )
                pygame.draw.line(
                    self._screen, GREEN, (cx - r // 3, cy + r // 3), (cx, cy - r), 2
                )
                pygame.draw.line(
                    self._screen, GREEN, (cx + r // 3, cy + r // 3), (cx, cy - r), 2
                )

            elif fruit.type == FruitType.STRAWBERRY:
                # Red triangle (polygon) with green leaves at top
                points = [
                    (cx, cy + r),  # bottom point
                    (cx - r, cy - r // 3),  # top left
                    (cx + r, cy - r // 3),  # top right
                ]
                pygame.draw.polygon(self._screen, RED, points)
                # Green leaves
                pygame.draw.line(
                    self._screen, GREEN, (cx, cy - r // 3), (cx - r // 2, cy - r), 3
                )
                pygame.draw.line(
                    self._screen, GREEN, (cx, cy - r // 3), (cx + r // 2, cy - r), 3
                )
                pygame.draw.line(
                    self._screen, GREEN, (cx, cy - r // 3), (cx, cy - r - 2), 3
                )

    def _draw_player(self, player: object) -> None:
        """Draw Pac-Man with mouth animation.

        Args:
            player: Player instance.
        """
        from src.game.player import Player

        p: Player = player  # type: ignore
        if not p.alive and not p.is_respawning():
            return

        cs = self._cell_size
        ox, oy = self._offset_x, self._offset_y
        px_f, py_f = p.pixel_pos
        cx = int(ox + px_f * cs + cs // 2)
        cy = int(oy + py_f * cs + cs // 2)
        r = max(4, cs // 2 - 2)

        # Determine facing angle for mouth
        from src.maze.maze_adapter import Direction

        direction_angles = {
            Direction.EAST: 0,
            Direction.NORTH: 270,
            Direction.WEST: 180,
            Direction.SOUTH: 90,
        }
        base_angle = direction_angles.get(p.direction, 0)  # type: ignore
        mouth = p.mouth_angle
        start_angle = math.radians(base_angle + mouth)
        end_angle = math.radians(base_angle + 360 - mouth)

        # Draw filled arc (pygame pie slice)
        if mouth < 2:
            pygame.draw.circle(self._screen, PACMAN_COLOR, (cx, cy), r)
        else:
            points = [(cx, cy)]
            steps = 32
            for i in range(steps + 1):
                angle = start_angle + (end_angle - start_angle) * i / steps
                points.append(
                    (
                        int(cx + r * math.cos(angle)),
                        int(cy - r * math.sin(angle)),
                    )
                )
            if len(points) > 2:
                pygame.draw.polygon(self._screen, PACMAN_COLOR, points)

        # Eye
        eye_x = cx + int(r * 0.3 * math.cos(math.radians(base_angle + 70)))
        eye_y = cy - int(r * 0.3 * math.sin(math.radians(base_angle + 70)))
        pygame.draw.circle(self._screen, BG_COLOR, (eye_x, eye_y), max(2, r // 5))

    def _draw_ghosts(self, ghosts: List[Any]) -> None:
        """Draw all ghosts in their current state.

        Args:
            ghosts: List of Ghost instances.
        """
        from src.game.ghost import GhostState

        cs = self._cell_size
        ox, oy = self._offset_x, self._offset_y

        for ghost in ghosts:
            if ghost.state == GhostState.RESPAWNING:
                continue

            px_f, py_f = ghost.pixel_pos
            gx = int(ox + px_f * cs + cs // 2)
            gy = int(oy + py_f * cs + cs // 2)
            r = max(4, cs // 2 - 2)

            # Choose color
            if ghost.state == GhostState.FRIGHTENED:
                timer = ghost.frightened_fraction()
                if timer < 2.0 and int(self._tick * 5) % 2 == 0:
                    color = GHOST_BLINK
                else:
                    color = GHOST_FRIGHTENED
            elif ghost.state == GhostState.EATEN:
                # Draw only eyes
                self._draw_ghost_eyes(gx, gy, r, ghost.color)
                continue
            else:
                color = ghost.color

            self._draw_ghost_body(gx, gy, r, color)
            self._draw_ghost_eyes(gx, gy, r, ghost.color)

    def _draw_ghost_body(
        self, cx: int, cy: int, r: int, color: Tuple[int, int, int]
    ) -> None:
        """Draw a ghost body (rounded top, wavy bottom).

        Args:
            cx: Center x.
            cy: Center y.
            r: Radius.
            color: Ghost RGB color.
        """
        pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        pygame.draw.circle(self._screen, color, (cx, cy - r // 4), r)
        pygame.draw.rect(
            self._screen,
            color,
            pygame.Rect(cx - r, cy - r // 4, r * 2, r + r // 4),
        )
        # Wavy bottom
        wave_count = 3
        wave_w = (r * 2) // wave_count
        for i in range(wave_count):
            wx = cx - r + i * wave_w
            wy = cy + r - r // 4
            pygame.draw.circle(self._screen, color, (wx + wave_w // 2, wy), wave_w // 2)

    def _draw_ghost_eyes(
        self, cx: int, cy: int, r: int, ghost_color: Tuple[int, int, int]
    ) -> None:
        """Draw ghost eyes (always white with dark pupils).

        Args:
            cx: Ghost center x.
            cy: Ghost center y.
            r: Ghost radius.
            ghost_color: Unused (kept for signature consistency).
        """
        eye_r = max(2, r // 4)
        pupil_r = max(1, r // 7)
        for ex_off in (-r // 3, r // 3):
            ex = cx + ex_off
            ey = cy - r // 4
            pygame.draw.circle(self._screen, (255, 255, 255), (ex, ey), eye_r)
            pygame.draw.circle(self._screen, (0, 0, 80), (ex + 1, ey), pupil_r)

    # ------------------------------------------------------------------ #
    #  HUD
    # ------------------------------------------------------------------ #

    def _draw_hud(
        self,
        score: int,
        lives: int,
        level_num: int,
        time_remaining: float,
        time_max: float,
        total_pacgums: int,
        remaining_pacgums: int,
    ) -> None:
        """Draw the always-visible in-game HUD.

        Args:
            score: Current score.
            lives: Remaining lives.
            level_num: Current level number.
            time_remaining: Seconds remaining.
            time_max: Total seconds for this level.
            total_pacgums: Total pacgums in level.
            remaining_pacgums: Uneaten pacgums.
        """
        w = self._screen.get_width()
        # HUD background
        pygame.draw.rect(self._screen, (5, 5, 20), (0, 0, w, HUD_HEIGHT))
        pygame.draw.line(self._screen, WALL_BORDER, (0, HUD_HEIGHT), (w, HUD_HEIGHT), 2)

        # Score (left)
        score_surf = self._font_hud.render(f"SCORE  {score:,}", True, YELLOW)
        self._screen.blit(score_surf, (12, 12))

        # Level (center)
        level_surf = self._font_hud.render(f"LEVEL {level_num}", True, CYAN)
        self._screen.blit(level_surf, ((w - level_surf.get_width()) // 2, 12))

        # Lives (right — as Pac-Man icons)
        lives_x = w - 14
        for _ in range(min(lives, 10)):
            lives_x -= 22
            pygame.draw.circle(self._screen, PACMAN_COLOR, (lives_x + 8, 20), 8)

        # Timer bar (bottom of HUD)
        bar_w = w - 24
        bar_h = 8
        bar_x = 12
        bar_y = HUD_HEIGHT - bar_h - 4
        fraction = max(0.0, min(1.0, time_remaining / time_max))

        # Color based on urgency
        if fraction > 0.4:
            bar_color = TIMER_OK
        elif fraction > 0.15:
            bar_color = TIMER_WARN
        else:
            bar_color = TIMER_CRIT

        pygame.draw.rect(self._screen, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(
            self._screen,
            bar_color,
            (bar_x, bar_y, int(bar_w * fraction), bar_h),
        )

        # Time label
        time_surf = self._font_sm.render(f"{int(time_remaining)}s", True, bar_color)
        self._screen.blit(time_surf, (w - 40, bar_y - 2))

    # ------------------------------------------------------------------ #
    #  Overlays
    # ------------------------------------------------------------------ #

    def _draw_pause_overlay(self) -> None:
        """Draw a semi-transparent pause screen overlay."""
        overlay = pygame.Surface(self._screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self._screen.blit(overlay, (0, 0))
        self._draw_centered_text("PAUSED", self._font_xl, YELLOW, offset_y=-50)
        self._draw_centered_text(
            "ENTER / P / K — Resume", self._font_md, TEXT_COLOR, offset_y=30
        )
        self._draw_centered_text("M — Main Menu", self._font_md, DIM_TEXT, offset_y=70)

    def _draw_cheat_overlay(self, player: object) -> None:
        """Draw the cheat mode key reference panel.

        Args:
            player: Player instance (to show current cheat states).
        """
        from src.game.player import Player

        p: Player = player  # type: ignore
        w = self._screen.get_width()
        panel_w = 300
        panel_h = 220
        px = w - panel_w - 10
        py = HUD_HEIGHT + 10

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 10, 30, 220))
        self._screen.blit(panel, (px, py))
        pygame.draw.rect(self._screen, CYAN, (px, py, panel_w, panel_h), 2)

        title = self._font_sm.render("⚡ CHEAT MODE", True, CYAN)
        self._screen.blit(title, (px + 10, py + 8))

        cheats = [
            ("I", "Invincibility", p.invincible),
            ("N", "Skip Level", False),
            ("F", "Freeze Ghosts", False),
            ("L", "Add Life", False),
            ("C", "Speed Boost", p.speed_boosted),
            ("G", "Scare Ghosts", False),
        ]
        for i, (key, desc, active) in enumerate(cheats):
            color = GREEN if active else TEXT_COLOR
            label = f"[{key}] {desc}"
            if active:
                label += " ✓"
            surf = self._font_sm.render(label, True, color)
            self._screen.blit(surf, (px + 10, py + 36 + i * 28))

    # ------------------------------------------------------------------ #
    #  Decorative helpers
    # ------------------------------------------------------------------ #

    def _draw_starfield(self) -> None:
        """Draw a simple static starfield background."""
        import random

        rng = random.Random(42)
        w, h = self._screen.get_size()
        for _ in range(80):
            sx = rng.randint(0, w - 1)
            sy = rng.randint(0, h - 1)
            brightness = rng.randint(60, 180)
            r = rng.randint(1, 2)
            pygame.draw.circle(
                self._screen, (brightness, brightness, brightness), (sx, sy), r
            )

    def _draw_centered_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        offset_y: int = 0,
    ) -> None:
        """Render text centered horizontally on the screen.

        Args:
            text: Text to render.
            font: Font to use.
            color: RGB color.
            offset_y: Vertical offset from screen center.
        """
        w, h = self._screen.get_size()
        surf = font.render(text, True, color)
        x = (w - surf.get_width()) // 2
        y = h // 2 + offset_y
        self._screen.blit(surf, (x, y))
