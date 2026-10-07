from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import curses
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import StringIO
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orbit_translate.config import AI_PROVIDER_TYPES
from orbit_translate.providers import ProviderOutcome
from orbit_translate.tui import (
    _Completion,
    _OperationWorker,
    _auth_marker,
    _provider_line,
    _prompt,
    _prompt_secret,
    _result_status,
    _run_screen,
    _select_protocol,
    clip_columns,
    display_width,
    safe_url,
)


class FakeScreen:
    def __init__(self, keys: list[object] | None = None, *, rows: int = 18, columns: int = 90):
        self.keys = list(keys or [])
        self.rows = rows
        self.columns = columns
        self.output: list[str] = []
        self.history: list[str] = []

    def getmaxyx(self) -> tuple[int, int]:
        return self.rows, self.columns

    def keypad(self, _enabled: bool) -> None:
        pass

    def timeout(self, _milliseconds: int) -> None:
        pass

    def erase(self) -> None:
        self.output.clear()

    def clear(self) -> None:
        self.output.clear()

    def addstr(self, _row: int, _column: int, value: str) -> None:
        self.output.append(value)
        self.history.append(value)

    def move(self, _row: int, _column: int) -> None:
        pass

    def clrtoeol(self) -> None:
        pass

    def refresh(self) -> None:
        pass

    def get_wch(self) -> object:
        if not self.keys:
            raise AssertionError("fake input exhausted; unexpected dialog or loop")
        return self.keys.pop(0)


class FakeDocument:
    def __init__(self, providers: list[dict[str, object]] | None = None):
        self.providers = providers or [
            {
                "id": "fixture",
                "name": "Fixture channel",
                "type": "mymemory",
                "enabled": False,
                "extra": "keep me",
            }
        ]
        self.data = {"providers": self.providers}
        self.config = SimpleNamespace(source="en", target="zh-CN", request_timeout_ms=500)
        self.dirty = False
        self.saved = 0
        self.probes: list[tuple[object, ...]] = []
        self.key_written = threading.Event()
        self.key_release: threading.Event | None = None

    def toggle(self, index: int) -> None:
        self.providers[index]["enabled"] = not self.providers[index].get("enabled", False)
        self.dirty = True

    def put_provider(self, index: int | None, values: dict[str, object]) -> None:
        if index is None:
            self.providers.append(dict(values))
        else:
            self.providers[index].update(values)
        self.dirty = True

    def delete_provider(self, index: int) -> None:
        self.providers.pop(index)
        self.dirty = True

    def set_key(self, index: int, value: str) -> None:
        assert index == 0
        assert value == "fixture-secret"
        if self.key_release is not None:
            self.key_release.wait(timeout=1)
        self.providers[index]["api_key_secret"] = "kwallet:fixture"
        self.providers[index]["api_key_env"] = ""
        self.dirty = True
        self.key_written.set()

    def probe(self, *values: object) -> ProviderOutcome:
        self.probes.append(values)
        return ProviderOutcome("fixture", "Fixture", text="译文" * 200)

    def save(self) -> None:
        self.saved += 1
        self.dirty = False
        return None


class TerminalFormattingTests(unittest.TestCase):
    def test_wide_text_clips_on_column_boundaries(self) -> None:
        self.assertEqual(display_width("A你好e\u0301"), 6)
        self.assertEqual(clip_columns("A你好B", 4), "A你")
        self.assertEqual(display_width(clip_columns("A你好B", 4)), 3)

    def test_url_hides_credentials_query_and_fragment(self) -> None:
        self.assertEqual(
            safe_url("https://user:secret@example.test/v1?token=hidden#part"),
            "https://example.test/v1",
        )
        self.assertNotIn("secret", safe_url("https://user:secret@example.test/?key=secret"))

    def test_auth_indicator_is_fixed_and_does_not_reveal_reference_or_env_name(self) -> None:
        provider = {
            "id": "fixture",
            "name": "Fixture",
            "type": "openai_responses",
            "enabled": True,
            "api_key_secret": "secret-service:fixture-ref",
        }
        marker = _auth_marker(provider)
        self.assertEqual(marker, "认证 ********")
        self.assertNotIn(provider["api_key_secret"], _provider_line(provider))
        provider["api_key_env"] = "PRIVATE_KEY_NAME"
        provider["api_key_secret"] = ""
        self.assertEqual(_auth_marker(provider), marker)


class WorkerAndScreenTests(unittest.TestCase):
    def test_masked_prompt_keeps_noecho_for_following_interactions(self) -> None:
        screen = FakeScreen([*"fixture-secret", curses.KEY_BACKSPACE, "\x1b"])
        with patch("orbit_translate.tui.curses.noecho") as noecho, patch("orbit_translate.tui.curses.echo") as echo:
            self.assertIsNone(_prompt_secret(screen, "Key"))
        self.assertGreaterEqual(noecho.call_count, 2)
        echo.assert_not_called()
        self.assertNotIn("fixture-secret", "".join(screen.history))

    def test_prompt_recalculates_dimensions_after_resize(self) -> None:
        class ResizedScreen(FakeScreen):
            def move(self, row, column):
                assert 0 <= row < self.rows and 0 <= column < self.columns

            def get_wch(self):
                key = super().get_wch()
                if key == curses.KEY_RESIZE:
                    self.rows, self.columns = 6, 20
                return key

        screen = ResizedScreen(["你", curses.KEY_RESIZE, "好", "\n"])
        self.assertEqual(_prompt(screen, "Name"), "你好")

    def test_busy_probe_blocks_mutations_and_auto_source_uses_example_english(self) -> None:
        release = threading.Event()
        finished = threading.Event()

        class SlowDocument(FakeDocument):
            def probe(self, *values):
                release.wait(timeout=1)
                result = super().probe(*values)
                finished.set()
                return result

        document = SlowDocument()
        document.config.source = "auto"
        screen = FakeScreen(["t", "\n", "\n", "\n", " ", "d", "s", "q", "y", "\n"])
        try:
            self.assertEqual(_run_screen(screen, document), 0)
            self.assertFalse(document.dirty)
            self.assertEqual(document.saved, 0)
            self.assertEqual(len(document.providers), 1)
            self.assertIn("渠道修改和保存暂不可用", "".join(screen.history))
        finally:
            release.set()
        self.assertTrue(finished.wait(timeout=1))
        self.assertEqual(document.probes[0], (0, "Hello world", "en", "zh-CN"))

    def test_protocol_selector_offers_every_configured_ai_type(self) -> None:
        for index, provider_type in enumerate(AI_PROVIDER_TYPES, start=1):
            with self.subTest(provider_type=provider_type):
                screen = FakeScreen([str(index)])
                self.assertEqual(_select_protocol(screen), provider_type)

    def test_probe_runs_on_daemon_worker_and_screen_can_quit_while_it_waits(self) -> None:
        started = threading.Event()
        release = threading.Event()

        class SlowDocument(FakeDocument):
            finished = threading.Event()

            def probe(self, *values: object) -> ProviderOutcome:
                started.set()
                release.wait(timeout=1)
                result = super().probe(*values)
                self.finished.set()
                return result

        document = SlowDocument()
        screen = FakeScreen(
            [
                ord("t"),
                *([curses.KEY_BACKSPACE] * len("Hello world")),
                *map(ord, "Bonjour"),
                "\n",
                "\n",
                "\n",
                ord("q"),
                "y",
                "\n",
            ],
        )
        began = time.monotonic()
        try:
            self.assertEqual(_run_screen(screen, document), 0)
            self.assertLess(time.monotonic() - began, 0.5)
            self.assertTrue(started.wait(timeout=1))
        finally:
            release.set()
        self.assertTrue(document.finished.wait(timeout=1))
        self.assertEqual(document.probes[0], (0, "Bonjour", "en", "zh-CN"))

    def test_key_prompt_is_fixed_masked_and_writes_off_screen_thread(self) -> None:
        release = threading.Event()
        document = FakeDocument()
        document.key_release = release
        screen = FakeScreen(
            [ord("K"), *map(ord, "fixture-secret"), "\n", ord("q"), "y", "\n"],
        )
        try:
            self.assertEqual(_run_screen(screen, document), 0)
            self.assertFalse(document.key_written.is_set())
            self.assertNotIn("fixture-secret", "".join(screen.history))
            self.assertIn("********", "".join(screen.history))
            self.assertIn("配置引用也会丢弃", "".join(screen.history))
        finally:
            release.set()
        self.assertTrue(document.key_written.wait(timeout=1))

    def test_toggle_save_confirmation_and_exit(self) -> None:
        document = FakeDocument()
        screen = FakeScreen([ord(" "), ord("s"), "y", "\n", ord("q")])
        self.assertEqual(_run_screen(screen, document), 0)
        self.assertTrue(document.providers[0]["enabled"])
        self.assertEqual(document.saved, 1)
        self.assertFalse(document.dirty)

    def test_edit_changes_metadata_and_keeps_other_provider_fields(self) -> None:
        document = FakeDocument()
        screen = FakeScreen(
            [ord("e"), *map(ord, "Updated name"), "\n", "\n", "\n", "\n", ord("q"), "y", "\n"]
        )
        self.assertEqual(_run_screen(screen, document), 0)
        self.assertEqual(document.providers[0]["name"], "Updated name")
        self.assertEqual(document.providers[0]["extra"], "keep me")
        self.assertEqual(document.saved, 0)

    def test_tiny_terminal_and_resize_key_are_handled(self) -> None:
        tiny = FakeScreen([ord("q")], rows=5, columns=20)
        self.assertEqual(_run_screen(tiny, FakeDocument()), 0)
        self.assertIn("终端太小", "".join(tiny.history))

        resized = FakeScreen([curses.KEY_RESIZE, ord("q")])
        self.assertEqual(_run_screen(resized, FakeDocument()), 0)
        self.assertIn("Orbit Translate 设置", "".join(resized.history))

    def test_add_ai_provider_uses_shared_protocol_catalog(self) -> None:
        document = FakeDocument()
        screen = FakeScreen(
            [
                ord("a"),
                "1",
                *map(ord, "My AI"),
                "\n",
                *map(ord, "https://example.test/v1"),
                "\n",
                *map(ord, "fixture-model"),
                "\n",
                "\n",
                ord("q"),
                "n",
                "\n",
                ord("q"),
                "y",
                "\n",
            ],
        )
        self.assertEqual(_run_screen(screen, document), 0)
        added = document.providers[-1]
        self.assertEqual(added["type"], AI_PROVIDER_TYPES[0])
        self.assertEqual(added["name"], "My AI")
        self.assertEqual(added["model"], "fixture-model")
        self.assertFalse(added["enabled"])
        self.assertEqual(document.providers[0]["extra"], "keep me")

    def test_probe_result_is_bounded_and_exception_details_are_hidden(self) -> None:
        outcome = ProviderOutcome("fixture", "Fixture", text="译文" * 1000)
        status, preview = _result_status(_Completion("probe", True, outcome))
        self.assertEqual(status, "测试可达，译文预览：")
        self.assertLessEqual(display_width(preview), 320)
        self.assertEqual(_result_status(_Completion("probe", False))[0], "操作失败；敏感错误详情已隐藏")
        key_status, _ = _result_status(_Completion("set-key", True))
        self.assertIn("不会撤销已轮换的 Key", key_status)


class WorkerUnitTests(unittest.TestCase):
    def test_worker_returns_only_safe_completion_for_key_failure(self) -> None:
        class FailedDocument(FakeDocument):
            def set_key(self, _index: int, _value: str) -> None:
                raise RuntimeError("fixture-secret in subprocess output")

        worker = _OperationWorker(FailedDocument())
        self.assertTrue(worker.submit("set-key", 0, "fixture-secret"))
        deadline = time.monotonic() + 1
        completion = None
        while completion is None and time.monotonic() < deadline:
            completion = worker.poll()
        worker.stop()
        self.assertIsNotNone(completion)
        self.assertFalse(completion.succeeded)
        self.assertIsNone(completion.result)


class EntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        entrypoint = ENTRY
        spec = importlib.util.spec_from_file_location("orbit_translate_entrypoint", entrypoint)
        assert spec and spec.loader
        cls.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.cli)

    def test_config_requires_settings_mode(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            self.cli.main(["--config", "/tmp/fixture.toml"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("only valid with --settings", stderr.getvalue())

    def test_help_describes_all_cli_modes(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as raised:
            self.cli.main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--settings", stdout.getvalue())
        self.assertIn("--check-deps", stdout.getvalue())
        self.assertIn("--config PATH", stdout.getvalue())

    def test_settings_requires_tty_and_emits_no_traceback(self) -> None:
        stderr = StringIO()
        with patch("sys.stderr", stderr), patch("sys.stdin", StringIO()), patch("sys.stdout", StringIO()):
            self.assertEqual(self.cli.main(["--settings", "--config", "/tmp/fixture.toml"]), 2)
        self.assertIn("requires an interactive terminal", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_settings_passes_only_explicit_path_to_tui(self) -> None:
        class TTY:
            def isatty(self) -> bool:
                return True

        with patch("sys.stdin", TTY()), patch("sys.stdout", TTY()), patch(
            "orbit_translate.tui.run_settings_tui", return_value=0
        ) as run_tui:
            self.assertEqual(self.cli.main(["--settings", "--config", "/tmp/fixture.toml"]), 0)
        run_tui.assert_called_once_with("/tmp/fixture.toml")

    def test_check_deps_still_dispatches_to_dependency_check(self) -> None:
        with patch.object(self.cli, "check_dependencies", return_value=0) as check:
            self.assertEqual(self.cli.main(["--check-deps"]), 0)
        check.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
