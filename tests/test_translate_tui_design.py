from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import curses
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orbit_translate.theme import Palette
from orbit_translate.tui import (
    _confirm,
    _Completion,
    _prompt,
    _render,
    _run_screen,
    _show_help,
    _select_protocol,
    display_width,
)
from orbit_translate.tui_style import load_terminal_style
from tests.test_translate_tui import FakeDocument


class RecordingScreen:
    def __init__(self, keys: list[object], *, rows: int = 18, columns: int = 90):
        self.keys = list(keys)
        self.rows = rows
        self.columns = columns
        self.history: list[str] = []
        self.output: list[str] = []
        self.writes: list[tuple[int, int, str]] = []
        self.refreshes = 0

    def getmaxyx(self) -> tuple[int, int]:
        return self.rows, self.columns

    def keypad(self, _enabled: bool) -> None:
        pass

    def timeout(self, _milliseconds: int) -> None:
        pass

    def erase(self) -> None:
        self.output.clear()

    def addstr(self, row: int, column: int, value: str) -> None:
        self.history.append(value)
        self.output.append(value)
        self.writes.append((row, column, value))

    def move(self, _row: int, _column: int) -> None:
        pass

    def refresh(self) -> None:
        self.refreshes += 1

    def get_wch(self) -> object:
        if not self.keys:
            raise AssertionError("unexpected extra screen read")
        return self.keys.pop(0)


class DesignScreenTests(unittest.TestCase):
    def test_small_header_keeps_unsaved_state_and_list_omits_protocol_noise(self) -> None:
        document = FakeDocument()
        document.dirty = True
        for width in (25, 40, 90):
            with self.subTest(width=width):
                screen = RecordingScreen([], rows=18, columns=width)
                _render(screen, document, 0, "", "", False, 0)
                self.assertIn("未保存", "".join(value for row, _col, value in screen.writes if row == 0))
                self.assertTrue(all("mymemory" not in value for row, _col, value in screen.writes if row == 4))

    def test_truncated_confirmation_cannot_accept_until_resized(self) -> None:
        screen = RecordingScreen(["y", "\n", "\x1b"], rows=8, columns=35)
        self.assertFalse(_confirm(screen, "不可撤销的钥匙串写入风险说明" * 12))
        self.assertIn("请放大窗口", "".join(screen.history))

    def test_protocol_choice_cannot_accept_invisible_options(self) -> None:
        screen = RecordingScreen(["5", "\n", "\x1b"], rows=8, columns=35)
        self.assertIsNone(_select_protocol(screen))
        self.assertIn("请放大窗口", "".join(screen.history))

    def test_url_with_explicit_port_is_visible_and_unaltered(self) -> None:
        value = "http://127.0.0.1:11434/api"
        screen = RecordingScreen(["\n"])
        self.assertEqual(_prompt(screen, "Base URL", default=value), value)
        self.assertIn(value, "".join(screen.history))

    def test_focusable_action_strip_and_help_dialog(self) -> None:
        screen = RecordingScreen(["\t", curses.KEY_RIGHT, "\n", "\x1b", "?", "x", "q"])
        self.assertEqual(_run_screen(screen, FakeDocument()), 0)
        output = "".join(screen.history)
        self.assertIn("‹[e] 编辑›", output)
        self.assertIn("设置 · Name", output)
        self.assertIn("Orbit Translate 帮助", output)
        self.assertIn("立即写入系统钥匙串", output)

    def test_shift_tab_can_focus_and_activate_quit_action(self) -> None:
        screen = RecordingScreen([getattr(curses, "KEY_BTAB", -2), "\n"])
        self.assertEqual(_run_screen(screen, FakeDocument()), 0)
        self.assertIn("‹[q] 退出›", "".join(screen.history))

    def test_main_timeout_does_not_redraw_an_unchanged_frame(self) -> None:
        class TimeoutOnce(RecordingScreen):
            def __init__(self):
                super().__init__(["q"])
                self.timeout_once = True

            def get_wch(self) -> object:
                if self.timeout_once:
                    self.timeout_once = False
                    raise curses.error("input timeout")
                return super().get_wch()

        screen = TimeoutOnce()
        self.assertEqual(_run_screen(screen, FakeDocument()), 0)
        self.assertEqual(screen.refreshes, 1)

    def test_probe_preview_is_cleared_or_suppressed_when_selection_changes(self) -> None:
        class DelayedWorker:
            def __init__(self, _document):
                self.busy = False
                self.kind = None
                self.poll_count = 0
                self.completion = None

            def submit(self, kind, *values):
                self.busy = True
                self.kind = kind
                self.completion = _Completion(
                    "probe", True, SimpleNamespace(ok=True, text="译文预览"), values[0]
                )
                return True

            def poll(self):
                self.poll_count += 1
                if self.completion is not None and self.poll_count >= completion_poll:
                    self.busy = False
                    self.kind = None
                    completion, self.completion = self.completion, None
                    return completion
                return None

            def stop(self):
                pass

        for completion_poll in (2, 3, 4):
            with self.subTest(completion_poll=completion_poll):
                document = FakeDocument(
                    [
                        {"id": "first", "name": "First", "type": "mymemory", "enabled": True},
                        {"id": "second", "name": "Second", "type": "google", "enabled": True},
                    ]
                )
                screen = RecordingScreen(["t", "\n", "\n", "\n", "j", "x", "q"])
                with patch("orbit_translate.tui._OperationWorker", DelayedWorker):
                    self.assertEqual(_run_screen(screen, document), 0)
                output = "".join(screen.output)
                self.assertNotIn("测试可达", output)
                self.assertNotIn("译文预览", output)
                if completion_poll == 3:
                    self.assertIn("当前选择不同，未显示结果", output)
                if completion_poll == 4:
                    self.assertIn("测试仍在后台进行", "".join(screen.history))

    def test_narrow_layout_wraps_by_cells_and_never_renders_private_url_parts(self) -> None:
        document = FakeDocument(
            [
                {
                    "id": "fixture",
                    "name": "翻译渠道",
                    "type": "openai_responses",
                    "enabled": True,
                    "base_url": "https://url-user:secret@example.test/v1?token=private#fragment",
                    "model": "fixture-model",
                    "api_key_secret": "secret-service:private-reference",
                    "api_key_env": "PRIVATE_ENV_NAME",
                }
            ]
        )
        screen = RecordingScreen([], rows=18, columns=40)
        _render(screen, document, 0, "删除确认需要完整换行显示", "", False, 0)
        output = "".join(screen.history)
        self.assertIn("渠道详情", output)
        self.assertIn("example.test/v1", output)
        for private in ("url-user", "secret", "private", "fragment", "private-reference", "PRIVATE_ENV_NAME"):
            self.assertNotIn(private, output)
        self.assertTrue(all(display_width(value) <= screen.columns - column - 1 for _row, column, value in screen.writes))

    def test_centered_confirmation_keeps_enter_default_and_y_n_cancel(self) -> None:
        self.assertTrue(_confirm(RecordingScreen(["\n"]), "长删除说明 " * 20, default=True))
        self.assertFalse(_confirm(RecordingScreen(["\n"]), "保存配置？", default=False))
        self.assertTrue(_confirm(RecordingScreen(["y", "\n"]), "确认删除？"))
        self.assertFalse(_confirm(RecordingScreen(["n", "\n"]), "确认删除？", default=True))
        self.assertFalse(_confirm(RecordingScreen(["\x1b"]), "确认删除？", default=True))

    def test_long_input_viewport_shows_end_and_ctrl_u_clears(self) -> None:
        value = "这是一个很长的地址段" * 5
        screen = RecordingScreen(["\x15", *value, "\n"], rows=12, columns=38)
        self.assertEqual(_prompt(screen, "Model ID", limit=200), value)
        self.assertIn("…", "".join(screen.history))
        self.assertIn(value[-5:], "".join(screen.history))

    def test_url_input_never_echoes_userinfo_query_or_fragment(self) -> None:
        value = "https://url-user:secret@example.test/v1?token=private#fragment"
        screen = RecordingScreen([*value, "\n"], rows=14, columns=48)
        self.assertEqual(_prompt(screen, "Base URL", limit=200), value)
        output = "".join(screen.history)
        self.assertIn("https://example.test/v1", output)
        for private in ("url-user", "secret", "token", "private", "fragment"):
            self.assertNotIn(private, output)


class TerminalStyleTests(unittest.TestCase):
    def test_no_color_forces_monochrome_without_touching_terminal_palette(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": ""}, clear=True), \
             patch("orbit_translate.tui_style.load_palette", return_value=Palette()), \
             patch("orbit_translate.tui_style.curses.init_color") as init_color, \
             patch("orbit_translate.tui_style.curses.init_pair") as init_pair:
            style = load_terminal_style()
        self.assertFalse(style.enabled)
        init_color.assert_not_called()
        init_pair.assert_not_called()

    def test_eight_color_mode_uses_default_background_and_shared_palette(self) -> None:
        with patch.dict(os.environ, {}, clear=True), \
             patch("orbit_translate.tui_style.load_palette", return_value=Palette(primary="#f0a050")), \
             patch("orbit_translate.tui_style.curses.has_colors", return_value=True), \
             patch("orbit_translate.tui_style.curses.start_color"), \
             patch("orbit_translate.tui_style.curses.use_default_colors"), \
             patch("orbit_translate.tui_style.curses.color_content", side_effect=[(0, 0, 0)] * 8), \
             patch("orbit_translate.tui_style.curses.COLORS", 8, create=True), \
             patch("orbit_translate.tui_style.curses.COLOR_PAIRS", 64, create=True), \
             patch("orbit_translate.tui_style.curses.init_pair") as init_pair, \
             patch("orbit_translate.tui_style.curses.color_pair", side_effect=lambda pair: pair):
            style = load_terminal_style()
        self.assertTrue(style.enabled)
        self.assertEqual(init_pair.call_count, 8)
        self.assertTrue(all(call.args[2] == -1 for call in init_pair.call_args_list))

    def test_monochrome_terminal_falls_back_cleanly(self) -> None:
        with patch.dict(os.environ, {}, clear=True), \
             patch("orbit_translate.tui_style.load_palette", return_value=Palette()), \
             patch("orbit_translate.tui_style.curses.has_colors", return_value=False):
            style = load_terminal_style()
        self.assertFalse(style.enabled)
        self.assertEqual(style.title, 0)


if __name__ == "__main__":
    unittest.main()
