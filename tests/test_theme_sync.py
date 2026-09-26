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


if __name__ == "__main__":
    unittest.main()
