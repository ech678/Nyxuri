import configparser
import unittest
from unittest.mock import patch

from tests.utils import TempEnv


class TestThemeSync(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__()

    def test_sync_writes_both_gtk_settings_files(self):
        from nyxuri.theme import sync

        with patch("nyxuri.theme.shutil.which", return_value=None):
            self.assertEqual(sync("light"), 0)
        for version in ("gtk-3.0", "gtk-4.0"):
            parser = configparser.ConfigParser()
            parser.read(self.ctx.home / ".config" / version / "settings.ini")
            self.assertEqual(parser["Settings"]["gtk-application-prefer-dark-theme"], "false")
            self.assertEqual(parser["Settings"]["gtk-theme-name"], "adw-gtk3")

    def test_status_returns_zero(self):
        from nyxuri.theme import status

        with patch("nyxuri.theme.shutil.which", return_value=None):
            self.assertEqual(status(), 0)

    def test_sync_respects_nyxuri_gtk_theme_env_precedence(self):
        from nyxuri.theme import sync
        import os

        env_vars = {
            "NYXURI_GTK_THEME_LIGHT": "custom-nyxuri-light",
            "NYXNIRI_GTK_THEME_LIGHT": "custom-nyxniri-light",
        }
        with patch.dict(os.environ, env_vars, clear=False), \
             patch("nyxuri.theme.shutil.which", return_value=None):
            self.assertEqual(sync("light"), 0)
            parser = configparser.ConfigParser()
            parser.read(self.ctx.home / ".config" / "gtk-3.0" / "settings.ini")
            self.assertEqual(parser["Settings"]["gtk-theme-name"], "custom-nyxuri-light")

    def test_sync_propagates_to_nyxuri_shell_ipc(self):
        """R10: explicit mode rides the shell theme IPC when Noctalia is gone."""
        from unittest.mock import MagicMock
        from nyxuri.theme import sync

        calls = []

        def fake_ipc(args, timeout=3.0):
            calls.append(list(args))
            return "OK"

        # Noctalia binary absent; qs + shell tree resolvable.
        def which(name):
            return "/usr/bin/qs" if name == "qs" else None

        shell_dir = self.ctx.home / "shelltree"
        shell_dir.mkdir()
        (shell_dir / "shell.qml").write_text("// fixture\n")
        with patch("nyxuri.theme.shutil.which", side_effect=which), \
             patch("nyxuri.theme._nyxuri_shell_dir", return_value=shell_dir), \
             patch("nyxuri.theme._nyxuri_shell_ipc", side_effect=fake_ipc):
            self.assertEqual(sync("dark"), 0)
        self.assertIn(["theme", "set", "dark"], calls)

    def test_sync_toggle_falls_back_to_system_flip_without_shells(self):
        from nyxuri.theme import sync

        with patch("nyxuri.theme.shutil.which", return_value=None), \
             patch("nyxuri.theme._nyxuri_shell_ipc", return_value=None):
            self.assertEqual(sync("toggle"), 0)
        # DEFAULT_MODE default is dark, so the flip lands on light.
        parser = configparser.ConfigParser()
        parser.read(self.ctx.home / ".config" / "gtk-3.0" / "settings.ini")
        self.assertEqual(parser["Settings"]["gtk-application-prefer-dark-theme"], "false")
        self.assertEqual(parser["Settings"]["gtk-theme-name"], "adw-gtk3")

    def test_sync_writes_kvantum_only_when_theme_installed(self):
        from nyxuri.theme import sync

        kvantum_dir = self.ctx.home / ".config" / "Kvantum" / "KvLibadwaitaDark"
        kvantum_dir.mkdir(parents=True)
        with patch("nyxuri.theme.shutil.which", return_value=None):
            self.assertEqual(sync("dark"), 0)
        parser = configparser.ConfigParser()
        parser.read(self.ctx.home / ".config" / "Kvantum" / "kvantum.kvconfig")
        self.assertEqual(parser["Settings"]["theme"], "KvLibadwaitaDark")

    def test_sync_swaps_glow_layout_and_reload_guards_on_niri(self):
        from nyxuri.theme import sync

        config = self.ctx.home / ".config"
        (config / "nyxuri" / "presets").mkdir(parents=True)
        (config / "nyxuri" / "presets" / "niri.active").write_text("glow\n")
        (config / "niri").mkdir()
        (config / "niri" / "layout-dark.kdl").write_text("// dark layout\n")
        (config / "niri" / "layout.kdl").write_text("// stale light layout\n")
        with patch("nyxuri.theme.shutil.which", return_value=None):
            self.assertEqual(sync("dark"), 0)
        self.assertEqual((config / "niri" / "layout.kdl").read_text(), "// dark layout\n")

        # Identical bytes must be a no-op (mtime-only churn avoided).
        before = (config / "niri" / "layout.kdl").stat().st_mtime_ns
        with patch("nyxuri.theme.shutil.which", return_value=None):
            self.assertEqual(sync("dark"), 0)
        self.assertEqual((config / "niri" / "layout.kdl").stat().st_mtime_ns, before)

    def test_sync_skips_glow_layout_when_preset_inactive(self):
        from nyxuri.theme import sync

        config = self.ctx.home / ".config"
        (config / "nyxuri" / "presets").mkdir(parents=True)
        (config / "nyxuri" / "presets" / "niri.active").write_text("plain\n")
        (config / "niri").mkdir()
        (config / "niri" / "layout-dark.kdl").write_text("// dark layout\n")
        with patch("nyxuri.theme.shutil.which", return_value=None):
            self.assertEqual(sync("dark"), 0)
        self.assertFalse((config / "niri" / "layout.kdl").exists())


if __name__ == "__main__":
    unittest.main()
