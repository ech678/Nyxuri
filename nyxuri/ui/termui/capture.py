from __future__ import annotations

import pathlib
from typing import List

import pyte
from PIL import Image, ImageDraw, ImageFont

from .theme import strip_ansi, visible_width

NAMED = {
    "black": "000000",
    "red": "d70000",
    "green": "00af00",
    "brown": "af5f00",
    "yellow": "af5f00",
    "blue": "005fd7",
    "magenta": "af00af",
    "cyan": "00afaf",
    "white": "ffffff",
    "default": "d8dee9",
}

BACKGROUND = (11, 13, 16)
CANVAS_PAD = 26
CELL_W = 9
CELL_H = 19
FONT_SIZE = 15
FONT_REGULAR = "/usr/share/fonts/gnu-free/FreeMono.otf"
FONT_BOLD = "/usr/share/fonts/gnu-free/FreeMonoBold.otf"


def _resolve(color: str, fallback: str) -> str:
    if not color:
        return fallback
    if len(color) == 6:
        try:
            int(color, 16)
            return color
        except ValueError:
            return fallback
    return NAMED.get(color, fallback)


def _rgb(hex_color: str) -> tuple:
    return tuple(int(hex_color[index:index + 2], 16) for index in (0, 2, 4))


def _screen_size(frame: str) -> tuple:
    lines = frame.split("\n")
    cols = max((visible_width(line) for line in lines), default=1)
    return cols, len(lines)


def frame_to_screen(frame: str) -> pyte.Screen:
    cols, rows = _screen_size(frame)
    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)
    stream.feed("\r\n".join(frame.split("\n")))
    return screen


def _glyph_mask(char: str, font: ImageFont.FreeTypeFont, cache: dict) -> Image.Image:
    key = (char, font.path, font.size)
    if key in cache:
        return cache[key]
    tile = Image.new("L", (CELL_W + 1, CELL_H + 2), 0)
    pen = ImageDraw.Draw(tile)
    pen.text((0, 0), char, font=font, fill=255)
    tile = tile.point(lambda value: 255 if value >= 128 else 0)
    cache[key] = tile
    return tile


def screen_to_png(screen: pyte.Screen, path: pathlib.Path) -> pathlib.Path:
    font = ImageFont.truetype(FONT_REGULAR, FONT_SIZE)
    bold_font = ImageFont.truetype(FONT_BOLD, FONT_SIZE)
    cache: dict = {}
    cols = screen.columns
    rows = screen.lines
    width = cols * CELL_W + CANVAS_PAD * 2
    height = rows * CELL_H + CANVAS_PAD * 2
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for row in range(rows):
        for col in range(cols):
            cell = screen.buffer[row][col]
            char = cell.data or " "
            foreground = _resolve(cell.fg, "d8dee9")
            if cell.bg and cell.bg != "default":
                box = (
                    CANVAS_PAD + col * CELL_W - 1,
                    CANVAS_PAD + row * CELL_H,
                    CANVAS_PAD + (col + 1) * CELL_W,
                    CANVAS_PAD + (row + 1) * CELL_H,
                )
                draw.rectangle(box, fill=_rgb(_resolve(cell.bg, "151a22")))
            if char == " ":
                continue
            mask = _glyph_mask(char, bold_font if cell.bold else font, cache)
            image.paste(
                _rgb(foreground),
                (CANVAS_PAD + col * CELL_W, CANVAS_PAD + row * CELL_H),
                mask,
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def frame_to_png(frame: str, path: pathlib.Path) -> pathlib.Path:
    return screen_to_png(frame_to_screen(frame), path)


def png_report(path: pathlib.Path) -> str:
    with Image.open(path) as image:
        colors = image.getcolors(maxcolors=1 << 20) or []
    return f"{path.name}: {image.size[0]}x{image.size[1]} colors={len(colors)}"
