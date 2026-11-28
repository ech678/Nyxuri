from __future__ import annotations

BG = "#0b0d10"
TEXT = "#e6e8ec"
MUTED = "#9096a0"
DIM = "#5a616c"
FAINT = "#262b33"
SURFACE = "#171b21"
ACCENT = "#79a6f2"
OK = "#8fb996"
WARN = "#d3ab73"
BAD = "#cc8888"

RESET = "\x1b[0m"


def fg(hex_color: str, text: str) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"


def bg(hex_color: str, text: str) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"\x1b[48;2;{r};{g};{b}m{text}\x1b[0m"


def bold(text: str) -> str:
    return f"\x1b[1m{text}\x1b[0m"


def strip_ansi(text: str) -> str:
    out = []
    index = 0
    length = len(text)
    while index < length:
        if text[index] == "\x1b":
            end = text.find("m", index)
            if end == -1:
                break
            index = end + 1
            continue
        out.append(text[index])
        index += 1
    return "".join(out)


def visible_width(text: str) -> int:
    return len(strip_ansi(text))


def pad(text: str, width: int) -> str:
    visible = visible_width(text)
    if visible > width:
        return truncate(text, width)
    return text + " " * (width - visible)


def truncate(text: str, width: int) -> str:
    if visible_width(text) <= width:
        return text
    plain = strip_ansi(text)
    if width <= 1:
        return plain[:width]
    return plain[: width - 1] + "…"


def columns(*segments, total: int = 0) -> str:
    parts = []
    position = 0
    for column, text in segments:
        if column > position:
            parts.append(" " * (column - position))
            position = column
        parts.append(text)
        position += visible_width(text)
    if total and total > position:
        parts.append(" " * (total - position))
    return "".join(parts)
