"""Real ncurses acceptance with isolated files and no wallet/network access."""

from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import tempfile
import termios
import time
import tomllib
import unittest


_FIXTURE = '''source = "en"
target = "zh-CN"
[[providers]]
id = "fixture"
name = "Fixture channel"
type = "command"
enabled = true
command = ["/usr/bin/printf", "fixture: %s", "{text}"]
'''
_ENTRY = ENTRY


class TerminalApp:
    def __init__(self, config: Path, *, command: list[str] | None = None):
        self.output = bytearray()
        self.master, slave = pty.openpty()
        self.resize(24, 100)
        self.process = subprocess.Popen(
            command or ["/usr/bin/python3", str(_ENTRY), "--settings", "--config", str(config)],
            stdin=slave, stdout=slave, stderr=slave,
            env={**os.environ, "TERM": "xterm-256color", "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
        os.close(slave)

    def resize(self, rows: int, columns: int) -> None:
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        if hasattr(self, "process"):
            self.process.send_signal(signal.SIGWINCH)

    def send(self, value: str) -> None:
        os.write(self.master, value.encode("utf-8"))

    def wait_for(self, value: str) -> None:
        wanted = value.encode("utf-8")
        deadline = time.monotonic() + 4
        while wanted not in self.output and time.monotonic() < deadline:
            if select.select([self.master], [], [], 0.05)[0]:
                try:
                    self.output.extend(os.read(self.master, 65536))
                except OSError:
                    break
        if wanted not in self.output:
            raise AssertionError(f"Terminal did not reach expected fixture state: {value}")

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=2)
        os.close(self.master)


@unittest.skipUnless(os.name == "posix" and Path("/usr/bin/python3").exists(), "requires POSIX ncurses")
class TerminalAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="orbit-tui-test-")
        self.config = Path(self.temporary.name) / "example.toml"
        self.config.write_text(_FIXTURE, encoding="utf-8")
        self.app = TerminalApp(self.config)
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(self.app.close)
        self.app.wait_for("Fixture channel")

    def test_toggle_save_reload_and_clean_exit(self) -> None:
        self.app.send(" s")
        self.app.wait_for("保存当前配置")
        self.app.send("y\n")
        self.app.wait_for("配置已保存并创建备份")
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        saved = tomllib.loads(self.config.read_text(encoding="utf-8"))
        self.assertFalse(saved["providers"][0]["enabled"])
        backups = list(self.config.parent.glob("example.toml.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), _FIXTURE)

    def test_example_probe_does_not_save(self) -> None:
        self.app.send("t")
        self.app.wait_for("示例文本")
        self.app.send("\n")
        self.app.wait_for("来源语言")
        self.app.send("\n")
        self.app.wait_for("zh-CN")
        self.app.send("\n")
        self.app.wait_for("fixture: Hello world")
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        self.assertEqual(self.config.read_text(encoding="utf-8"), _FIXTURE)

    def test_cancelled_masked_input_survives_resize_without_echo(self) -> None:
        self.app.send("K")
        self.app.wait_for("固定掩码")
        marker = "fixture-key-never-store"
        self.app.send(marker)
        self.app.resize(8, 35)
        self.app.send("\x1b")
        time.sleep(0.05)
        self.app.resize(24, 100)
        self.app.wait_for("已取消")
        # ncurses remains in noecho mode after leaving the masked prompt.
        deadline = time.monotonic() + 1
        while termios.tcgetattr(self.app.master)[3] & termios.ECHO and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertFalse(termios.tcgetattr(self.app.master)[3] & termios.ECHO)
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        self.assertNotIn(marker.encode(), self.app.output)
        self.assertEqual(self.config.read_text(encoding="utf-8"), _FIXTURE)

    def test_discard_after_shrinking_terminal_retains_original(self) -> None:
        self.app.send(" ")
        self.app.wait_for("渠道状态已修改")
        self.app.resize(8, 35)
        self.app.wait_for("终端太小")
        self.app.send("q")
        self.app.wait_for("丢弃未保存")
        self.app.send("y\n")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        self.assertEqual(self.config.read_text(encoding="utf-8"), _FIXTURE)

    def test_add_ai_save_and_reload(self) -> None:
        self.app.send("a")
        self.app.wait_for("选择 AI 协议")
        self.app.send("2")
        self.app.wait_for("渠道名称")
        self.app.send("Fixture AI\n")
        self.app.wait_for("Base URL")
        self.app.send("https://example.test/v1\n")
        self.app.wait_for("Model")
        self.app.send("fixture-model\n")
        self.app.wait_for("认证环境变量名")
        self.app.send("\n")
        self.app.wait_for("已新增停用渠道")
        self.app.send(" s")
        self.app.wait_for("保存当前配置")
        self.app.send("y\n")
        self.app.wait_for("配置已保存并创建备份")
        self.app.send("q")
        self.assertEqual(self.app.process.wait(timeout=2), 0)
        saved = tomllib.loads(self.config.read_text(encoding="utf-8"))
        provider = saved["providers"][-1]
        self.assertEqual(provider["type"], "openai_responses")
        self.assertTrue(provider["enabled"])
        self.assertEqual(provider["model"], "fixture-model")
        self.assertNotIn("api_key", provider)
