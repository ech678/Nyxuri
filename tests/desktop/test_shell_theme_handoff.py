"""Tests for theme and wallpaper state handoff during dual shell transitions.

Verifies:
1. State capture from active shell (Noctalia / Nyxuri Shell / fallback)
2. State restoration/handoff into target shell (IPC / daemon commands)
3. Routing priority according to active_shell in nyxuri.system.theme
4. Gsettings 'default' does not incorrectly clobber dark mode
5. Strict test sandbox isolation (no host mutation)
"""

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv
from nyxuri.state.store import set_shell, active_shell


class TestShellThemeHandoff(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__()

    def test_capture_from_noctalia(self):
        from nyxuri.system.shell import capture_active_theme_state

        wp_path = str(self.ctx.home / "Pictures" / "wall.png")
        Path(wp_path).touch()

        def fake_run(cmd, timeout=None, capture_output=False, text=False, check=False):
            if cmd == ["noctalia", "msg", "theme-mode-get"]:
                return subprocess.CompletedProcess(cmd, 0, "light\n", "")
            if cmd == ["noctalia", "msg", "wallpaper-get"]:
                return subprocess.CompletedProcess(cmd, 0, f"{wp_path}\n", "")
            return subprocess.CompletedProcess(cmd, 1, "", "")

        with patch("nyxuri.system.shell.shutil.which", return_value="/usr/bin/noctalia"), \
             patch("nyxuri.system.shell.subprocess.run", side_effect=fake_run):
            mode, wallpaper = capture_active_theme_state("noctalia")

        self.assertEqual(mode, "light")
        self.assertEqual(wallpaper, wp_path)

    def test_capture_from_nyxuri_shell_via_ipc(self):
        from nyxuri.system.shell import capture_active_theme_state

        def fake_ipc(args, timeout=1.0):
            if args == ["theme", "status"]:
                return "light"
            return None

        with patch("nyxuri.system.theme._nyxuri_shell_ipc", side_effect=fake_ipc):
            mode, _ = capture_active_theme_state("nyxuri-shell")

        self.assertEqual(mode, "light")

    def test_capture_from_nyxuri_shell_via_config_toml(self):
        from nyxuri.system.shell import capture_active_theme_state

        wp_dark = str(self.ctx.home / "Pictures" / "dark.png")
        Path(wp_dark).touch()

        nyx_cfg = self.ctx.home / ".config" / "nyxuri" / "config.toml"
        nyx_cfg.parent.mkdir(parents=True, exist_ok=True)
        nyx_cfg.write_text(f'[theme]\nmode = "dark"\n\n[wallpaper]\npathDark = "{wp_dark}"\n')

        with patch("nyxuri.system.theme._nyxuri_shell_ipc", return_value=None):
            mode, wallpaper = capture_active_theme_state("nyxuri-shell")

        self.assertEqual(mode, "dark")
        self.assertEqual(wallpaper, wp_dark)

    def test_capture_from_nyxuri_shell_via_config_json(self):
        from nyxuri.system.shell import capture_active_theme_state

        wp_dark = str(self.ctx.home / "Pictures" / "dark.png")
        Path(wp_dark).touch()

        nyx_cfg = self.ctx.home / ".config" / "nyxuri" / "config.json"
        nyx_cfg.parent.mkdir(parents=True, exist_ok=True)
        nyx_cfg.write_text(json.dumps({
            "theme": {"mode": "dark"},
            "wallpaper": {"pathDark": wp_dark}
        }))

        with patch("nyxuri.system.theme._nyxuri_shell_ipc", return_value=None):
            mode, wallpaper = capture_active_theme_state("nyxuri-shell")

        self.assertEqual(mode, "dark")
        self.assertEqual(wallpaper, wp_dark)

    def test_handoff_to_nyxuri_shell(self):
        from nyxuri.system.shell import handoff_theme_state

        wp_path = str(self.ctx.home / "Pictures" / "wp.png")
        Path(wp_path).touch()
        ipc_calls = []

        def fake_ipc(args, timeout=2.0):
            ipc_calls.append(list(args))
            return "OK"

        with patch("nyxuri.system.theme._nyxuri_shell_ipc", side_effect=fake_ipc), \
             patch("nyxuri.system.theme.sync") as mock_sync:
            handoff_theme_state("nyxuri-shell", "light", wp_path)

        self.assertIn(["theme", "set", "light"], ipc_calls)
        self.assertIn(["wallpaper", "set", wp_path], ipc_calls)
        mock_sync.assert_called_once_with("light")

    def test_handoff_to_noctalia(self):
        from nyxuri.system.shell import handoff_theme_state

        wp_path = str(self.ctx.home / "Pictures" / "wp.png")
        Path(wp_path).touch()
        run_calls = []

        def fake_run(cmd, timeout=None, capture_output=False, check=False):
            run_calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch("nyxuri.system.shell.shutil.which", return_value="/usr/bin/noctalia"), \
             patch("nyxuri.system.shell.subprocess.run", side_effect=fake_run), \
             patch("nyxuri.system.theme.sync") as mock_sync:
            handoff_theme_state("noctalia", "dark", wp_path)

        self.assertIn(["noctalia", "msg", "theme-mode-set", "dark"], run_calls)
        self.assertIn(["noctalia", "msg", "wallpaper-set", wp_path], run_calls)
        mock_sync.assert_called_once_with("dark")

    def test_mode_from_system_prioritizes_active_nyxuri_shell(self):
        from nyxuri.system.theme import _mode_from_system

        set_shell("nyxuri-shell")
        with patch("nyxuri.system.theme._nyxuri_shell_ipc", return_value="light"):
            self.assertEqual(_mode_from_system(), "light")

    def test_mode_from_system_ignores_gsettings_default(self):
        """gsettings 'default' must NOT be interpreted as light mode."""
        from nyxuri.system.theme import _mode_from_system

        set_shell("noctalia")
        with patch("nyxuri.system.theme.shutil.which", side_effect=lambda name: "/usr/bin/" + name if name == "gsettings" else None), \
             patch("nyxuri.system.theme.timed_run", return_value=subprocess.CompletedProcess([], 0, "'default'\n", "")):
            # Should fall back to DEFAULT_MODE (dark) rather than mapping 'default' to 'light'
            self.assertEqual(_mode_from_system(), "dark")

    def test_propagate_routes_to_active_shell(self):
        from nyxuri.system.theme import _propagate

        set_shell("nyxuri-shell")
        with patch("nyxuri.system.theme._nyxuri_shell_ipc", return_value="OK") as mock_ipc, \
             patch("nyxuri.system.theme._noctalia_available", return_value=True):
            channel = _propagate("dark", False)
            self.assertEqual(channel, "nyxuri-shell")
            mock_ipc.assert_called_once_with(["theme", "set", "dark"])

        set_shell("noctalia")
        with patch("nyxuri.system.theme._nyxuri_shell_ipc", return_value="OK"), \
             patch("nyxuri.system.theme._noctalia_available", return_value=True), \
             patch("nyxuri.system.theme.timed_run", return_value=subprocess.CompletedProcess([], 0, "", "")):
            channel = _propagate("dark", False)
            self.assertEqual(channel, "noctalia")


if __name__ == "__main__":
    unittest.main()
