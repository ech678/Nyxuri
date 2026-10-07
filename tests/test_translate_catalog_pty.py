"""Catalog terminal acceptance using public-shaped fixtures, never HTTP/keys."""

from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import os
from pathlib import Path
import tempfile
import time
import tomllib
import unittest

from tests.test_translate_tui_pty import TerminalApp, _ENTRY, _FIXTURE


def _command(config: Path, *, cold: bool = False) -> list[str]:
    # Patch inside the child before the settings module creates its lazy store.
    # A real cache, wallet and network are deliberately outside this acceptance.
    launcher = f"""
import runpy, sys, threading, time
sys.path.insert(0, {str(_ENTRY.parent)!r})
from unittest.mock import patch
from orbit_translate.catalog import CatalogModel, CatalogProvider, CatalogSnapshot
snapshot = CatalogSnapshot((
    CatalogProvider('openrouter', 'OpenRouter fixture', ('FIXTURE_API_KEY',), (
        CatalogModel('fixture/jk-text', 'Fixture JK text', 'fixture', 'openai_compatible', 'https://example.test/api/v1'),
    )),
), time.time())
class FixtureStore:
    def load_cached(self):
        return None if {cold!r} else snapshot
    def refresh(self):
        if not {cold!r}:
            raise AssertionError('Fresh fixture must not access HTTP')
        threading.Event().wait(5)
        return snapshot
sys.argv = [str({str(_ENTRY)!r}), '--settings', '--config', {str(config)!r}]
with patch('orbit_translate.catalog.CatalogStore', FixtureStore):
    runpy.run_path({str(_ENTRY)!r}, run_name='__main__')
"""
    return ["/usr/bin/python3", "-c", launcher]


@unittest.skipUnless(os.name == "posix" and Path("/usr/bin/python3").exists(), "requires POSIX ncurses")
class CatalogTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="orbit-catalog-pty-")
        self.config = Path(self.temporary.name) / "example.toml"
        self.config.write_text(_FIXTURE, encoding="utf-8")
        self.addCleanup(self.temporary.cleanup)

    def launch(self, *, cold: bool = False) -> TerminalApp:
        app = TerminalApp(self.config, command=_command(self.config, cold=cold))
        self.addCleanup(app.close)
        app.wait_for("Fixture channel")
        return app

    def test_loading_can_be_cancelled_and_quit_without_waiting_for_http(self) -> None:
        app = self.launch(cold=True)
        app.send("m")
        app.wait_for("models.dev")
        started = time.monotonic()
        app.send("\x1b")
        app.wait_for("已取消")
        app.send("q")
        self.assertEqual(app.process.wait(timeout=2), 0)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(self.config.read_text(encoding="utf-8"), _FIXTURE)

    def test_provider_picker_cancel_after_resize_does_not_save(self) -> None:
        app = self.launch()
        app.send("m")
        app.wait_for("OpenRouter fixture")
        app.resize(8, 35)
        app.send("\x1b")
        time.sleep(0.05)
        app.resize(24, 100)
        app.wait_for("已取消")
        app.send("q")
        self.assertEqual(app.process.wait(timeout=2), 0)
        self.assertEqual(self.config.read_text(encoding="utf-8"), _FIXTURE)

    def test_fuzzy_selection_editable_preset_and_explicit_save(self) -> None:
        app = self.launch()
        app.send("m")
        app.wait_for("OpenRouter fixture")
        app.send("opr\n")
        app.wait_for("Fixture JK text")
        # j/k are search characters in this picker, unlike the channel list.
        app.send("jk\n")
        app.wait_for("渠道名称")
        app.send("\x7f" * len("OpenRouter fixture") + "Fixture selected\n")
        app.wait_for("Enter 保留当前")
        app.send("\n")
        app.wait_for("兼容服务 Base URL")
        app.send("\x7f" * len("https://example.test/api/v1") + "https://gateway.example.test/v1\n")
        app.wait_for("Model ID")
        app.send("\n")
        app.wait_for("已新增停用渠道")
        self.assertEqual(self.config.read_text(encoding="utf-8"), _FIXTURE)
        app.send("s")
        app.wait_for("保存当前配置")
        app.send("y\n")
        app.wait_for("配置已保存并创建备份")
        app.send("q")
        self.assertEqual(app.process.wait(timeout=2), 0)
        saved = tomllib.loads(self.config.read_text(encoding="utf-8"))
        original = tomllib.loads(_FIXTURE)
        self.assertEqual(saved["providers"][0], original["providers"][0])
        provider = saved["providers"][-1]
        self.assertEqual(provider["name"], "Fixture selected")
        self.assertEqual(provider["type"], "openai_compatible")
        self.assertEqual(provider["model"], "fixture/jk-text")
        self.assertEqual(provider["base_url"], "https://gateway.example.test/v1")
        self.assertFalse(provider["enabled"])
        self.assertNotIn("api_key", provider)
        self.assertNotIn("api_key_env", provider)
        self.assertNotIn("api_key_secret", provider)

    def test_model_and_review_cancellation_leave_config_unchanged(self) -> None:
        app = self.launch()
        app.send("m")
        app.wait_for("OpenRouter fixture")
        app.send("\n")
        app.wait_for("Fixture JK text")
        app.send("\x1b")
        app.wait_for("已取消模型选择")
        app.send("m\n\n")
        app.wait_for("渠道名称")
        app.send("\x1b")
        app.wait_for("已取消预设确认")
        app.send("q")
        self.assertEqual(app.process.wait(timeout=2), 0)
        self.assertEqual(self.config.read_text(encoding="utf-8"), _FIXTURE)
