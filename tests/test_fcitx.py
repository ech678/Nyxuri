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
        from nyxuri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = (
            f"[theme.templates.user.{FCITX_THEME}_theme]\n"
            f"[theme.templates.user.{FCITX_THEME}_panel]\n"
            f"[theme.templates.user.{FCITX_THEME}_highlight]\n"
        )
        with patch("nyxuri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertTrue(fcitx_templates_registered())

    def test_only_one_registered_returns_true(self):
        """Only 1 of 3 templates present → True (OR logic)."""
        from nyxuri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = f"[theme.templates.user.{FCITX_THEME}_theme]\n"
        with patch("nyxuri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertTrue(fcitx_templates_registered(),
                                    "Partial registration (1/3) should return True with OR logic")

    def test_none_registered_returns_false(self):
        """No templates present → False."""
        from nyxuri.modules.fcitx import fcitx_templates_registered, FCITX_THEME

        content = "[some.other.template]\n"
        with patch("nyxuri.modules.fcitx._fcitx_paths") as mock_paths:
            mock_paths.return_value = (None, None, None, None, Path("/fake/config.toml"), None, None, None)
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value=content):
                    self.assertFalse(fcitx_templates_registered())

    def test_no_config_file_returns_false(self):
        """No config file → False."""
        from nyxuri.modules.fcitx import fcitx_templates_registered

        with patch("nyxuri.modules.fcitx._fcitx_paths") as mock_paths:
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
        from nyxuri.modules.fcitx import fcitx_reload

        with patch("nyxuri.modules.fcitx.shutil.which", return_value="/usr/bin/busctl"), \
             patch("nyxuri.modules.fcitx.timed_run", return_value=SimpleNamespace(returncode=0)) as run, \
             patch("nyxuri.modules.fcitx.subprocess.Popen") as popen:
            fcitx_reload()

        run.assert_called_once_with(
            ["busctl", "--user", "--auto-start=no", "call", "org.fcitx.Fcitx5", "/controller", "org.fcitx.Fcitx.Controller1", "ReloadAddonConfig", "s", "classicui"],
            5, stdout=-3, stderr=-3, check=False,
        )
        popen.assert_not_called()

    def test_reload_does_not_start_daemon_when_busctl_is_unavailable(self):
        from nyxuri.modules.fcitx import fcitx_reload

        with patch("nyxuri.modules.fcitx.shutil.which", return_value=None), \
             patch("nyxuri.modules.fcitx.subprocess.Popen") as popen:
            fcitx_reload()

        popen.assert_not_called()

    def test_theme_edit_preserves_other_sections_and_comments(self):
        from nyxuri.modules.fcitx import fcitx_set_theme_conf
        path = self.env.config_dir / "fcitx5/conf/classicui.conf"
        path.parent.mkdir(parents=True)
        path.write_text("# personal\n[Other]\nTheme=keep\n[ClassicUI]\nTheme=old\nFont=custom\n")
        path.chmod(0o600)
        fcitx_set_theme_conf()
        self.assertEqual(path.read_text(), "# personal\nTheme=nyxmellow\nFont=custom\nDarkTheme=nyxmellow\n[Other]\nTheme=keep\n")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_theme_edit_uses_fcitx_root_config_format(self):
        from nyxuri.modules.fcitx import fcitx_set_theme_conf
        path = self.env.config_dir / "fcitx5/conf/classicui.conf"
        path.parent.mkdir(parents=True)
        path.write_text("# generated by fcitx5\nTheme=old\nDarkTheme=old-dark\nFont=custom\n")
        fcitx_set_theme_conf()
        self.assertEqual(
            path.read_text(),
            "# generated by fcitx5\nTheme=nyxmellow\nDarkTheme=nyxmellow\nFont=custom\n",
        )

    def test_theme_edit_migrates_legacy_classicui_header(self):
        from nyxuri.modules.fcitx import fcitx_set_theme_conf
        path = self.env.config_dir / "fcitx5/conf/classicui.conf"
        path.parent.mkdir(parents=True)
        path.write_text("[ClassicUI]\nTheme=default\nDarkTheme=default-dark\nFont=Sans 10\n")
        fcitx_set_theme_conf()
        content = path.read_text()
        self.assertNotIn("[ClassicUI]", content)
        self.assertIn("Theme=nyxmellow\n", content)
        self.assertIn("DarkTheme=nyxmellow\n", content)
        self.assertIn("Font=Sans 10\n", content)

    def test_uninstall_keeps_user_changes_and_private_theme_files(self):
        from nyxuri.modules.fcitx import fcitx_set_theme_conf, fcitx_uninstall
        path = self.env.config_dir / "fcitx5/conf/classicui.conf"
        path.parent.mkdir(parents=True)
        path.write_text("[ClassicUI]\nTheme=old\nDarkTheme=old-dark\n")
        fcitx_set_theme_conf()
        path.write_text(path.read_text().replace("Theme=nyxmellow\n", "Theme=my-new-theme\n", 1))
        private = self.env.home / ".local/share/fcitx5/themes/nyxmellow/custom.txt"
        private.parent.mkdir(parents=True)
        private.write_text("mine")
        with patch("nyxuri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_uninstall())
        self.assertIn("Theme=my-new-theme\n", path.read_text())
        self.assertIn("DarkTheme=old-dark\n", path.read_text())
        self.assertEqual(private.read_text(), "mine")

    def test_install_preserves_shortcuts_and_is_repeatable(self):
        from nyxuri.modules.fcitx import fcitx_install
        config = self.env.config_dir / "fcitx5/config"
        config.parent.mkdir(parents=True)
        config.write_text("[Hotkey/TriggerKeys]\n0=Alt+space\n")
        quickphrase = config.parent / "conf/quickphrase.conf"
        quickphrase.parent.mkdir()
        quickphrase.write_text("[Hotkey]\nTriggerKey=Super+space\n")
        shell = self.env.config_dir / "noctalia/noctalia-config.toml"
        shell.parent.mkdir()
        shell.write_text('[theme]\nmode = "dark"\n')
        with patch("nyxuri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxuri.modules.fcitx.fcitx_trigger_render"), \
             patch("nyxuri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_install())
            first = shell.read_text()
            self.assertTrue(fcitx_install())
            self.assertEqual(shell.read_text(), first)
        self.assertEqual(config.read_text(), "[Hotkey/TriggerKeys]\n0=Alt+space\n")
        self.assertEqual(quickphrase.read_text(), "[Hotkey]\nTriggerKey=Super+space\n")

    def test_template_registration_and_removal_leave_other_templates(self):
        from nyxuri.modules.fcitx import fcitx_register_templates, fcitx_uninstall
        path = self.env.config_dir / "noctalia/noctalia-config.toml"
        path.parent.mkdir()
        personal = '[theme.templates.user.nyxmellow_personal]\ninput_path = "mine"\n'
        owned = '[theme.templates.user.nyxmellow_theme]\nindex = 9\n'
        path.write_text(personal + owned)
        self.assertTrue(fcitx_register_templates())
        self.assertIn(personal, path.read_text())
        self.assertIn(owned, path.read_text())
        with patch("nyxuri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_uninstall())
        self.assertIn(personal, path.read_text())
        self.assertNotIn("nyxmellow_theme]", path.read_text())

    def test_template_registration_upgrades_legacy_hooks(self):
        from nyxuri.modules.fcitx import fcitx_register_templates, FCITX_CLASSICUI_RELOAD_HOOK
        path = self.env.config_dir / "noctalia/noctalia-config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        legacy_content = (
            '[theme.templates.user.nyxmellow_highlight]\n'
            'index = 2\n'
            'input_path = "in.svg"\n'
            'output_path = "out.svg"\n'
            'post_hook = "fcitx5-remote --check -r >/dev/null 2>&1 || true"\n'
        )
        path.write_text(legacy_content)
        self.assertTrue(fcitx_register_templates())
        self.assertIn(f'post_hook = "{FCITX_CLASSICUI_RELOAD_HOOK}"', path.read_text())

    def test_failed_template_write_does_not_enable_module(self):
        from nyxuri.modules.fcitx import fcitx_install, fcitx_enabled
        with patch("nyxuri.modules.fcitx.atomic_replace_item", return_value=False):
            self.assertFalse(fcitx_install())
        self.assertFalse(fcitx_enabled())


class TestFcitxDecouplingAndRime(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_deploy_assets_does_not_modify_classicui_or_enable_marker(self):
        """fcitx_deploy_assets only deploys templates and hooks, leaving classicui untouched."""
        from nyxuri.modules.fcitx import fcitx_deploy_assets, fcitx_enabled

        classicui = self.env.config_dir / "fcitx5/conf/classicui.conf"
        noctalia_conf = self.env.config_dir / "noctalia/noctalia-config.toml"
        noctalia_conf.parent.mkdir(parents=True, exist_ok=True)
        noctalia_conf.write_text('[theme]\nmode = "dark"\n')

        with patch("nyxuri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxuri.modules.fcitx.fcitx_deploy_templates", return_value=True), \
             patch("nyxuri.modules.fcitx.fcitx_trigger_render"):
            self.assertTrue(fcitx_deploy_assets())

        self.assertFalse(classicui.exists(), "classicui.conf must NOT be created or modified by deploy_assets")
        self.assertFalse(fcitx_enabled(), "enabled marker must NOT be created by deploy_assets")

    def test_activate_modifies_classicui_and_creates_marker(self):
        """fcitx_activate sets theme in classicui and creates consent marker."""
        from nyxuri.modules.fcitx import fcitx_activate, fcitx_enabled

        classicui = self.env.config_dir / "fcitx5/conf/classicui.conf"
        noctalia_conf = self.env.config_dir / "noctalia/noctalia-config.toml"
        noctalia_conf.parent.mkdir(parents=True, exist_ok=True)
        noctalia_conf.write_text('[theme]\nmode = "dark"\n')

        with patch("nyxuri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxuri.modules.fcitx.fcitx_trigger_render"), \
             patch("nyxuri.modules.fcitx.fcitx_reload"):
            self.assertTrue(fcitx_activate())

        self.assertTrue(classicui.is_file())
        self.assertIn("Theme=nyxmellow", classicui.read_text())
        self.assertTrue(fcitx_enabled())

    def test_preflight_plan_clarity(self):
        """Preflight plan must clearly distinguish deploy-only vs default theme activation."""
        from nyxuri.modules.fcitx import fcitx_preflight_plan

        plan_full = fcitx_preflight_plan(set_default=True)
        plan_deploy = fcitx_preflight_plan(set_default=False)

        full_text = " ".join(plan_full)
        deploy_text = " ".join(plan_deploy)

        self.assertIn("classicui.conf", full_text)
        self.assertIn("templates", full_text)
        self.assertTrue("跳过" in deploy_text or "Skipped" in deploy_text)

    def test_setup_rime_ice_creates_yaml_and_profile(self):
        """setup_rime_ice patches default.custom.yaml and adds rime to profile."""
        from nyxuri.modules.fcitx import setup_rime_ice

        with patch("nyxuri.modules.fcitx.fcitx_reload_all"):
            self.assertTrue(setup_rime_ice())

        custom_yaml = self.env.home / ".local/share/fcitx5/rime/default.custom.yaml"
        profile = self.env.config_dir / "fcitx5/profile"

        self.assertTrue(custom_yaml.is_file(), "default.custom.yaml must be created")
        self.assertIn("rime_ice", custom_yaml.read_text(), "rime_ice schema must be in default.custom.yaml")

        self.assertTrue(profile.is_file(), "fcitx5 profile must be created")
        self.assertIn("Name=rime", profile.read_text(), "rime input method must be in fcitx5 profile")

    def test_setup_rime_ice_preserves_existing_profile_items(self):
        """setup_rime_ice appends to existing profile without overwriting."""
        from nyxuri.modules.fcitx import setup_rime_ice

        profile = self.env.config_dir / "fcitx5/profile"
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.write_text(
            "[Groups/0]\n"
            "Name=默认\n"
            "Default Layout=us\n\n"
            "[Groups/0/Items/0]\n"
            "Name=keyboard-us\n"
            "Layout=\n\n"
            "[GroupOrder]\n"
            "0=默认\n"
        )

        with patch("nyxuri.modules.fcitx.fcitx_reload_all"):
            self.assertTrue(setup_rime_ice())

        content = profile.read_text()
        self.assertIn("Name=keyboard-us", content)
        self.assertIn("Name=rime", content)
        self.assertIn("[Groups/0/Items/1]", content)


if __name__ == "__main__":
    unittest.main()
