"""New navigation acceptance in real ncurses, with isolated local fixtures."""

from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import os
from pathlib import Path
import tempfile
import tomllib
import unittest

from tests.test_translate_tui_pty import TerminalApp, _FIXTURE


@unittest.skipUnless(os.name == "posix" and Path("/usr/bin/python3").exists(), "requires POSIX ncurses")
class DesignTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="orbit-design-pty-")
        self.config = Path(self.temporary.name) / "example.toml"
        self.config.write_text(_FIXTURE, encoding="utf-8")
        self.app = TerminalApp(self.config)
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(self.app.close)
        self.app.wait_for("Fixture channel")

    def test_help_cancel_and_quit_keeps_configuration(self) -> None:
        self.app.send("?")
        self.app.wait_for("帮助")
        self.app.send("\x1b")
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        self.assertEqual(self.config.read_text(), _FIXTURE)

    def test_focus_toolbar_enter_toggles_then_explicit_save(self) -> None:
        self.app.send("\t")
        # ncurses may repaint only changed cells, not the whole action label.
        self.app.wait_for("‹")
        self.app.send("\n")
        self.app.wait_for("渠道状态已修改")
        self.app.send("s")
        self.app.wait_for("保存当前配置")
        self.app.send("y\n")
        self.app.wait_for("配置已保存并创建备份")
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        saved = tomllib.loads(self.config.read_text())
        self.assertFalse(saved["providers"][0]["enabled"])

    def test_channel_enter_opens_editor_and_cancel_keeps_configuration(self) -> None:
        self.app.send("\n")
        self.app.wait_for("Name")
        self.app.send("\x1b")
        self.app.wait_for("已取消编辑")
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        self.assertEqual(self.config.read_text(), _FIXTURE)

    def test_clear_example_input_and_probe_never_saves(self) -> None:
        self.app.send("t")
        self.app.wait_for("示例文本")
        self.app.send("\x15Good morning\n")
        self.app.wait_for("来源语言")
        self.app.send("\n")
        self.app.wait_for("目标语言")
        self.app.send("\n")
        self.app.wait_for("fixture: Good morning")
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        self.assertEqual(self.config.read_text(), _FIXTURE)


if __name__ == "__main__":
    unittest.main()
