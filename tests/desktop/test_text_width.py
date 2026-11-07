"""Regression tests for terminal text width, clipping, and clean.py helpers."""

import io
import contextlib
import sys
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch

from nyxuri.system.env import Colors
from nyxuri.ui.tui import display_width, render_check_row, render_menu_item, truncate_display


def _reference_width(text: str) -> int:
    total = 0
    for char in text:
        if unicodedata.combining(char) or unicodedata.category(char) in ("Cf", "Mn", "Me"):
            continue
        total += 2 if unicodedata.east_asian_width(char) in ("F", "W") else 1
    return total


class TestDisplayWidth(unittest.TestCase):
    def test_zero_width_characters_do_not_consume_columns(self):
        for text in ("a\u200db", "a\u200bb", "\ufeff", "e\u0301", "\u00ad", "a\u200eb", "\u2060"):
            self.assertEqual(display_width(text), _reference_width(text), repr(text))

    def test_cjk_and_ascii_widths(self):
        self.assertEqual(display_width("中文"), 4)
        self.assertEqual(display_width("abc"), 3)

    def test_ansi_sequences_are_not_counted(self):
        self.assertEqual(display_width(f"{Colors.RED}abc{Colors.RESET}"), 3)


class TestTruncateDisplay(unittest.TestCase):
    def test_never_exceeds_requested_width(self):
        pool = list("abc中文🙂") + ["\u200d", "\u0301", "\ufe0f", "\u200b", Colors.RED, Colors.RESET]
        for suffix in ("…", "...", ""):
            for width in range(0, 12):
                for count in range(0, 8):
                    text = "".join(pool[(i * 3 + count) % len(pool)] for i in range(count))
                    self.assertLessEqual(
                        display_width(truncate_display(text, width, suffix=suffix)),
                        width,
                        f"text={text!r} width={width} suffix={suffix!r}",
                    )

    def test_suffix_larger_than_width_is_clipped(self):
        self.assertLessEqual(display_width(truncate_display("hello", 2, suffix="...")), 2)
        self.assertEqual(truncate_display("hello", 1, suffix="…"), "…")
        self.assertEqual(truncate_display("hello", 0), "")

    def test_text_within_width_is_returned_unchanged(self):
        self.assertEqual(truncate_display("abc", 5), "abc")


class TestRowRendering(unittest.TestCase):
    def _row(self, fn, *args, **kwargs):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            fn(*args, **kwargs)
        return buffer.getvalue().split("\n")[0].replace("\033[K", "")

    def test_rows_never_exceed_terminal_width(self):
        label = "中文🙂\u200d mixed label"
        for cols in (1, 2, 3, 4, 6, 9, 12, 20, 80):
            row = self._row(render_check_row, True, "[✓]", label, cols=cols)
            self.assertLessEqual(display_width(row), cols, f"check row at cols={cols}")
            row = self._row(render_menu_item, 0, label, 0, cols=cols)
            self.assertLessEqual(display_width(row), cols, f"menu row at cols={cols}")


class TestCleanHelpers(unittest.TestCase):
    def test_tilde_only_shortens_paths_actually_below_home(self):
        import nyxuri.system.clean as clean

        with patch.object(clean, "HOME", Path("/home/user")):
            self.assertEqual(clean.tilde("/home/user/.cache"), "~/.cache")
            self.assertEqual(clean.tilde("/home/user"), "~")
            self.assertEqual(clean.tilde("/home/user/.cache/sub"), "~/.cache/sub")
            self.assertEqual(clean.tilde("/home/username/secret"), "/home/username/secret")
            self.assertEqual(clean.tilde("/home/users/data"), "/home/users/data")

    def test_interactive_helpers_survive_stdin_without_fileno(self):
        import nyxuri.system.clean as clean

        class NoFileno:
            def isatty(self):
                return True

            def fileno(self):
                raise io.UnsupportedOperation("redirected stdin is pseudofile")

        tasks = [{"key": "cache", "label": "l", "target": "t", "size": 1}]
        with patch.object(sys, "stdin", NoFileno()):
            # The tui CheckboxList owns key reading now; a non-tty stdin
            # yields no selection instead of a crash.
            self.assertIsNone(clean._checkbox(tasks))


if __name__ == "__main__":
    unittest.main()
