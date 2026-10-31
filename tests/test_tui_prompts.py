"""Regression tests for upstream defects fixed during the bug-hunt rounds.

Each test reproduces a concrete failure that shipped in v4.0.0-alpha.1 and
asserts the corrected behavior, so the defect cannot silently return.
"""

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class TestMultibyteInput(unittest.TestCase):

    def test_read_key_decodes_multibyte_utf8(self):
        import pty
        import threading
        import time
        from nyxuri import tui
        for text in ("中", "é", "😀", "日"):
            master, slave = pty.openpty()
            saved = sys.stdin
            sys.stdin = os.fdopen(os.dup(slave), "r", buffering=1, errors="replace")
            # Type AFTER the TUI goes raw: read_key's tty.setraw uses
            # TCSAFLUSH, which would flush bytes queued before the switch.
            typer = threading.Timer(0.3, os.write, args=(master, text.encode("utf-8")))
            typer.start()
            try:
                self.assertEqual(tui.read_key(), text)
            finally:
                typer.join()
                sys.stdin.close()
                sys.stdin = saved
                os.close(master)
                os.close(slave)

class TestEndOfInputCancelsPrompts(unittest.TestCase):
    """A closed terminal must cancel the prompt instead of spinning the reader.

    read_key() returns "EOF" once os.read() yields nothing, but no caller
    matched it, so every menu looped forever at full CPU after the tty closed.
    """

    def _stub(self, tui):
        calls = {"count": 0}

        def fake_read_key():
            calls["count"] += 1
            if calls["count"] > 50:
                raise AssertionError("read_key() never stopped being polled")
            return "EOF"

        self.enterContext(patch.object(tui, "read_key", fake_read_key))
        self.enterContext(patch.object(tui, "interactive_screen",
                                       lambda **kwargs: contextlib.nullcontext()))
        self.enterContext(patch.object(tui.sys, "stdin",
                                       type("Stdin", (), {"isatty": staticmethod(lambda: True)})()))
        return calls

    def test_menu_run_returns_on_end_of_input(self):
        from nyxuri import tui
        calls = self._stub(tui)
        menu = tui.Menu("rollback_select_title", [tui.MenuItem(label="a"), tui.MenuItem(label="b")],
                        hint_key="rollback_select_hint", compact=True)
        self.assertEqual(menu.run(), len(menu.items) - 1)
        self.assertEqual(calls["count"], 1)

    def test_checkbox_list_run_cancels_on_end_of_input(self):
        from nyxuri import tui
        calls = self._stub(tui)
        checklist = tui.CheckboxList("master_title", [
            tui.CheckboxEntry(key="k1", label="a"),
            tui.CheckboxEntry(key="k2", label="b"),
        ], compact=True)
        self.assertIsNone(checklist.run())
        self.assertEqual(calls["count"], 1)

    def test_raw_line_reader_cancels_on_end_of_input(self):
        from nyxuri import tui
        calls = self._stub(tui)
        switcher = tui.PresetSwitcher.__new__(tui.PresetSwitcher)
        self.assertIsNone(tui.PresetSwitcher._read_line_raw(switcher, "prompt: "))
        self.assertEqual(calls["count"], 1)

    def test_every_prompt_loop_matches_end_of_input(self):
        source = (Path(__file__).resolve().parent.parent / "nyxuri" / "tui.py").read_text(encoding="utf-8")
        for branch in (
            'elif key in ("ESC", "EXIT", "EOF"):',
            'elif key in ("0", "q", "Q", "ESC", "EXIT", "EOF"):',
            'elif key in ("q", "Q", "ESC", "EXIT", "EOF"):',
        ):
            self.assertIn(branch, source)
        self.assertEqual(source.count('elif k in ("ESC", "EXIT", "EOF"):'), 1)

class TestMouseEventsDoNotBreakTextPrompts(unittest.TestCase):
    """read_key() yields MouseEvent rather than str inside a mouse-tracking screen.

    _read_line_raw runs from PresetSwitcher.run(), which enables SGR mouse
    tracking, so a click on the save-name prompt fed a MouseEvent into len(k).
    Every earlier branch compared with ``in``, which tolerates a non-string, so
    only the printable branch could raise, and it raised TypeError.
    """

    def _switcher(self, tui, keys):
        self.enterContext(patch.object(tui, "read_key", side_effect=list(keys)))
        return tui.PresetSwitcher.__new__(tui.PresetSwitcher)

    def test_mouse_events_are_ignored_while_typing(self):
        from nyxuri import tui
        switcher = self._switcher(tui, ["a", tui.MouseEvent("PRESS", 10, 5), "b", "ENTER"])
        self.assertEqual(tui.PresetSwitcher._read_line_raw(switcher, "name> "), "ab")

    def test_wheel_events_are_ignored_while_typing(self):
        from nyxuri import tui
        switcher = self._switcher(tui, [tui.MouseEvent("WHEEL_UP", 3, 3), "c", "ENTER"])
        self.assertEqual(tui.PresetSwitcher._read_line_raw(switcher, "name> "), "c")

    def test_mouse_event_before_escape_still_cancels(self):
        from nyxuri import tui
        switcher = self._switcher(tui, [tui.MouseEvent("PRESS", 1, 1), "ESC"])
        self.assertIsNone(tui.PresetSwitcher._read_line_raw(switcher, "name> "))

    def test_only_string_keys_reach_the_printable_branch(self):
        source = (Path(__file__).resolve().parent.parent / "nyxuri" / "tui.py").read_text(encoding="utf-8")
        self.assertIn("elif isinstance(k, str) and len(k) == 1 and k.isprintable():", source)
        self.assertNotIn("elif len(k) == 1 and k.isprintable():", source)


class TestLifecycleConflictPrompt(unittest.TestCase):
    """已批准的生命周期验收：冲突取消不进入事务，普通确认不等于覆盖。"""

    def test_noninteractive_auto_yes_preserves_conflicts(self):
        from nyxuri import tui
        with TempEnv(), patch("sys.stdin.isatty", return_value=False), \
             patch.dict(os.environ, {"NYXURI_AUTO_YES": "1"}):
            result = _quiet(tui.choose_conflict_policy, ["fish"],
                            conflicts={"fish": ["config.fish"]})
        self.assertIs(result, False)

    def test_scroll_then_eof_cancels_before_unit_transaction(self):
        from nyxuri import tui
        with TempEnv() as temp, patch("sys.stdin.isatty", return_value=True), \
             patch.object(tui, "interactive_screen", side_effect=contextlib.nullcontext), \
             patch.object(tui, "read_key", side_effect=["DOWN", "EOF"]), \
             patch("nyxuri.kernel.transaction.plan_on", return_value=["fish"]), \
             patch("nyxuri.kernel.transaction.plan_conflicts", return_value=[f"file-{i}" for i in range(100)]), \
             patch("nyxuri.kernel.transaction.unit_on") as transact:
            workshop = tui.UnitWorkshop()
            _quiet(workshop._switch, "fish", True)
            transact.assert_not_called()
            self.assertFalse((temp.env.state_dir / "state.json").exists())
            self.assertIsNotNone(workshop._report)

    def test_orphan_enable_reports_without_leaving_workshop(self):
        from nyxuri import tui
        with TempEnv(), patch("nyxuri.kernel.transaction.plan_on", side_effect=KeyError("removed")), \
             patch("nyxuri.kernel.transaction.unit_on") as transact:
            workshop = tui.UnitWorkshop()
            workshop._switch("removed", True)
            self.assertIn("removed", " ".join(workshop._report))
            transact.assert_not_called()
