"""Behavior contracts for fcitx: partial template registration detection (OR logic)."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, mock_open

from tests.utils import TempEnv


class TestFcitxTemplateDetection(unittest.TestCase):
    """fcitx_templates_registered must use OR logic (any one template = registered)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_all_three_registered_returns_true(self):
        """All 3 templates present → True."""
        from nyxniri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = (
            f"[theme.templates.user.{FCITX_THEME}_theme]\n"
            f"[theme.templates.user.{FCITX_THEME}_panel]\n"
            f"[theme.templates.user.{FCITX_THEME}_highlight]\n"
        )
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertTrue(fcitx_templates_registered())

    def test_only_one_registered_returns_true(self):
        """Only 1 of 3 templates present → True (OR logic)."""
        from nyxniri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = f"[theme.templates.user.{FCITX_THEME}_theme]\n"
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertTrue(fcitx_templates_registered(),
                                    "Partial registration (1/3) should return True with OR logic")

    def test_none_registered_returns_false(self):
        """No templates present → False."""
        from nyxniri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = "[some.other.template]\n"
        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertFalse(fcitx_templates_registered())

    def test_no_config_file_returns_false(self):
        """No config file → False."""
        from nyxniri.modules.fcitx import fcitx_templates_registered

        with patch("nyxniri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=False):
                self.assertFalse(fcitx_templates_registered())


class TestFcitxStartup(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_niri_starts_fcitx_when_installed(self):
        config = (self.env.configs_src / "niri" / "config.kdl").read_text(encoding="utf-8")
        self.assertIn(
            'spawn-at-startup "sh" "-c" "command -v fcitx5 >/dev/null 2>&1 && exec fcitx5 -d"',
            config,
        )

    def test_reload_does_not_start_or_kill_daemon(self):
        from nyxniri.modules.fcitx import fcitx_reload

        with patch("nyxniri.modules.fcitx.shutil.which", return_value="/usr/bin/fcitx5-remote"), \
             patch("nyxniri.modules.fcitx.timed_run", return_value=SimpleNamespace(returncode=1)) as run, \
             patch("nyxniri.modules.fcitx.subprocess.Popen") as popen:
            fcitx_reload()

        run.assert_called_once_with(
            ["fcitx5-remote", "--check", "-r"], 5, capture_output=True, check=False,
        )
        popen.assert_not_called()

    def test_theme_edit_preserves_other_sections_and_comments(self):
        from nyxniri.modules.fcitx import fcitx_set_theme_conf
        path = self.env.config_dir / "fcitx5/conf/classicui.conf"
        path.parent.mkdir(parents=True)
        path.write_text("# personal\n[Other]\nTheme=keep\n[ClassicUI]\nTheme=old\nFont=custom\n")
        path.chmod(0o600)
        fcitx_set_theme_conf()
        self.assertEqual(path.read_text(), "# personal\n[Other]\nTheme=keep\n[ClassicUI]\nTheme=nyxmellow\nFont=custom\nDarkTheme=nyxmellow\n")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_uninstall_keeps_user_changes_and_private_theme_files(self):
        from nyxniri.modules.fcitx import fcitx_set_theme_conf, fcitx_uninstall
        path = self.env.config_dir / "fcitx5/conf/classicui.conf"
        path.parent.mkdir(parents=True)
        path.write_text("[ClassicUI]\nTheme=old\nDarkTheme=old-dark\n")
        fcitx_set_theme_conf()
        path.write_text(path.read_text().replace("Theme=nyxmellow\n", "Theme=my-new-theme\n", 1))
        private = self.env.home / ".local/share/fcitx5/themes/nyxmellow/custom.txt"
        private.parent.mkdir(parents=True)
        private.write_text("mine")
        with patch("nyxniri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_uninstall())
        self.assertIn("Theme=my-new-theme\n", path.read_text())
        self.assertIn("DarkTheme=old-dark\n", path.read_text())
        self.assertEqual(private.read_text(), "mine")

    def test_install_preserves_shortcuts_and_is_repeatable(self):
        from nyxniri.modules.fcitx import fcitx_install
        config = self.env.config_dir / "fcitx5/config"
        config.parent.mkdir(parents=True)
        config.write_text("[Hotkey/TriggerKeys]\n0=Alt+space\n")
        quickphrase = config.parent / "conf/quickphrase.conf"
        quickphrase.parent.mkdir()
        quickphrase.write_text("[Hotkey]\nTriggerKey=Super+space\n")
        shell = self.env.config_dir / "noctalia/noctalia-config.toml"
        shell.parent.mkdir()
        shell.write_text('[theme]\nmode = "dark"\n')
        with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.fcitx.fcitx_trigger_render"), \
             patch("nyxniri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_install())
            first = shell.read_text()
            self.assertTrue(fcitx_install())
            self.assertEqual(shell.read_text(), first)
        self.assertEqual(config.read_text(), "[Hotkey/TriggerKeys]\n0=Alt+space\n")
        self.assertEqual(quickphrase.read_text(), "[Hotkey]\nTriggerKey=Super+space\n")

    def test_template_registration_and_removal_leave_other_templates(self):
        from nyxniri.modules.fcitx import fcitx_register_templates, fcitx_uninstall
        path = self.env.config_dir / "noctalia/noctalia-config.toml"
        path.parent.mkdir()
        personal = '[theme.templates.user.nyxmellow_personal]\ninput_path = "mine"\n'
        owned = '[theme.templates.user.nyxmellow_theme]\nindex = 9\n'
        path.write_text(personal + owned)
        self.assertTrue(fcitx_register_templates())
        self.assertIn(personal, path.read_text())
        self.assertIn(owned, path.read_text())
        with patch("nyxniri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_uninstall())
        self.assertIn(personal, path.read_text())
        self.assertNotIn("nyxmellow_theme]", path.read_text())

    def test_failed_template_write_does_not_enable_module(self):
        from nyxniri.modules.fcitx import fcitx_install, fcitx_enabled
        with patch("nyxniri.modules.fcitx.atomic_replace_item", return_value=False):
            self.assertFalse(fcitx_install())
        self.assertFalse(fcitx_enabled())


if __name__ == "__main__":
    unittest.main()
