"""The record: what already happened, written as plain terminal text.

Pure standard library. Runs between two inline Textual runs, so sudo,
pacman and $EDITOR can own the terminal in the gaps. The column math here
must stay identical to nyxuri.tcss (Screen padding 0 1, #column width 72).
"""

import shutil
import sys
from typing import Optional

from nyxuri.ui.tui import truncate_display

COLUMN = 72

DIM = "\033[90m"
RESET = "\033[0m"
MARKS = {
    "ok": "\033[32m✓\033[0m",
    "fail": "\033[31m✗\033[0m",
    "warn": "\033[33m!\033[0m",
}


def column(width: int) -> tuple:
    """(left margin, span) for a terminal width — Textual's centering, by hand."""
    inner = max(1, width - 2)
    span = min(COLUMN, inner)
    return 1 + (inner - span) // 2, span


class Record:
    def __init__(self, stream=None):
        self.stream = stream or sys.stdout

    def _size(self):
        return shutil.get_terminal_size((80, 24))

    def line(self, text: str = "") -> None:
        left, span = column(self._size().columns)
        body = truncate_display(text, span) if text else ""
        self.stream.write((" " * left + body).rstrip(" ") + "\n" if body else "\n")
        self.stream.flush()

    def step(self, title: str) -> None:
        self.line()
        self.line(f"● {title}")

    def result(self, kind: Optional[str], text: str) -> None:
        if kind == "skip":
            self.line(f"  └ {DIM}{text}{RESET}")
            return
        mark = MARKS.get(kind or "")
        self.line(f"  └ {mark} {text}" if mark else f"  └ {text}")
