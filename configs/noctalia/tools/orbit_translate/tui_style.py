"""Small curses color mapping for the settings interface."""

from __future__ import annotations

import curses
from dataclasses import dataclass
import os

from .theme import Palette, load_palette


@dataclass(frozen=True)
class TerminalStyle:
    """Semantic curses attributes; every role is 0 in monochrome mode."""

    palette: Palette
    enabled: bool = False
    title: int = 0
    text: int = 0
    muted: int = 0
    border: int = 0
    focus: int = 0
    key: int = 0
    strong: int = 0
    subtle: int = 0
    accent: int = 0
    warn: int = 0
    error: int = 0


_PAIR_COUNT = 8


def load_terminal_style() -> TerminalStyle:
    """Load the shared M3 palette and map it to existing terminal colors."""

    palette = load_palette()
    if "NO_COLOR" in os.environ:
        return TerminalStyle(palette)
    try:
        if not curses.has_colors():
            return TerminalStyle(palette)
        curses.start_color()
        curses.use_default_colors()
        colors = min(int(curses.COLORS), 256)
        if colors < 8 or int(curses.COLOR_PAIRS) <= _PAIR_COUNT:
            return TerminalStyle(palette)
        available = [_terminal_rgb(index) for index in range(colors)]
        roles = (
            (1, palette.primary),
            (2, palette.on_surface),
            (3, palette.muted),
            (4, palette.outline_variant),
            (5, palette.outline),
            (6, palette.secondary),
            (7, palette.tertiary),
            (8, palette.error),
        )
        for pair, color in roles:
            curses.init_pair(pair, _nearest_color(color, available), -1)
        bold = getattr(curses, "A_BOLD", 0)
        underline = getattr(curses, "A_UNDERLINE", 0)
        return TerminalStyle(
            palette,
            True,
            title=curses.color_pair(1) | bold,
            text=curses.color_pair(2),
            muted=curses.color_pair(3),
            border=curses.color_pair(4),
            focus=curses.color_pair(1) | bold | underline,
            key=curses.color_pair(1),
            strong=curses.color_pair(2) | bold,
            subtle=curses.color_pair(5),
            accent=curses.color_pair(6) | bold,
            warn=curses.color_pair(7) | bold,
            error=curses.color_pair(8),
        )
    except (AttributeError, curses.error, TypeError, ValueError):
        return TerminalStyle(palette)
def _nearest_color(value: str, available: list[tuple[int, int, int]]) -> int:
    rgb = _parse_rgb(value)
    return min(
        range(len(available)),
        key=lambda index: sum((rgb[channel] - available[index][channel]) ** 2 for channel in range(3)),
    )


def _parse_rgb(value: str) -> tuple[int, int, int]:
    try:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError
        return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
    except (TypeError, ValueError):
        return 128, 136, 152


def _terminal_rgb(index: int) -> tuple[int, int, int]:
    try:
        red, green, blue = curses.color_content(index)
        return round(red * 255 / 1000), round(green * 255 / 1000), round(blue * 255 / 1000)
    except (AttributeError, curses.error, TypeError, ValueError):
        base = (
            (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
            (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
            (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
            (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
        )
        if index < len(base):
            return base[index]
        if index < 232:
            level = (0, 95, 135, 175, 215, 255)
            offset = index - 16
            return level[offset // 36], level[(offset // 6) % 6], level[offset % 6]
        shade = 8 + (index - 232) * 10
        return shade, shade, shade


__all__ = ["TerminalStyle", "load_terminal_style"]
