"""Contract tests for Mango WM adaptation in Nyxuri."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nyxuri.core import get_env
from nyxuri.deploy.manifest import discover_deployable_apps, discover_optional_apps, load_manifest
from nyxuri.deploy.templates import _phase_render_templates
from tests.utils import TempEnv

_REPO = Path(__file__).resolve().parent.parent


class TestMangoAdaptation(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.mango_src = _REPO / "configs" / "mango"

    def tearDown(self):
        self.ctx.__exit__()

    def test_mango_config_syntax_valid(self):
        """Validate config.conf syntax with mango -p if mango binary is available."""
        if not shutil.which("mango"):
            self.skipTest("mango binary not installed")
        conf_path = self.mango_src / "config.conf"
        self.assertTrue(conf_path.is_file())
        res = subprocess.run(["mango", "-c", str(conf_path), "-p"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"mango -p failed: {res.stderr}")

    def test_mango_manifest_contract(self):
        """Verify .module.toml parameters for mango."""
        m = load_manifest(self.mango_src, is_optional=True)
        self.assertEqual(m.name, "mango")
        self.assertEqual(m.detect, "mango")
        self.assertEqual(m.label, "Mango WM")
        self.assertIn("monitors.conf", m.preserve)
        self.assertIn("noctalia.conf", m.preserve)
        self.assertIn("scripts/*.sh", m.chmod)
        self.assertEqual(m.preset_reload, ["mmsg", "dispatch", "reload_config"])
        self.assertTrue(m.is_deployable)
        self.assertTrue(m.is_optional)

    def test_mango_dual_axis_discovery(self):
        """Mango must be both deployable (axis A) and optional (axis B)."""
        deployable = discover_deployable_apps()
        self.assertIn("mango", deployable)

        optional = discover_optional_apps()
        self.assertIn("mango", optional)

    def test_mango_portals_conf_exists_and_routes_wlr(self):
        """Verify mango-portals.conf configures wlr screencast/screenshot."""
        portal_conf = _REPO / "configs" / "xdg-desktop-portal" / "mango-portals.conf"
        self.assertTrue(portal_conf.is_file())
        content = portal_conf.read_text(encoding="utf-8")
        self.assertIn("org.freedesktop.impl.portal.ScreenCast=wlr;", content)
        self.assertIn("org.freedesktop.impl.portal.Screenshot=wlr;", content)

    def test_mango_template_rendering(self):
        """Verify /home/user is replaced with target $HOME in config.conf."""
        env = get_env()
        dest_mango = env.config_dir / "mango"
        dest_mango.mkdir(parents=True, exist_ok=True)
        (dest_mango / "config.conf").write_text(
            "exec=/home/user/.config/mango/scripts/session-shell.sh\n",
            encoding="utf-8",
        )
        _phase_render_templates(only_app="mango")
        rendered = (dest_mango / "config.conf").read_text(encoding="utf-8")
        self.assertNotIn("/home/user", rendered)
        self.assertIn(str(env.home), rendered)

    def test_theme_sync_calls_mmsg_reload(self):
        """Theme sync should dispatch mmsg reload_config when mmsg is available."""
        from nyxuri.theme import sync

        calls = []

        def fake_timed_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0)

        def fake_which(cmd):
            if cmd == "mmsg":
                return "/usr/bin/mmsg"
            return None

        with patch("nyxuri.theme.timed_run", side_effect=fake_timed_run), \
             patch("nyxuri.theme.shutil.which", side_effect=fake_which):
            sync("dark")

        self.assertIn(["mmsg", "dispatch", "reload_config"], calls)

    def test_doctor_detects_running_mango(self):
        """Doctor should report mango as OK when XDG_CURRENT_DESKTOP is mango."""
        from io import StringIO
        import contextlib
        import os
        from nyxuri.doctor import _check_compositor

        buf = StringIO()
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "mango"}), \
             contextlib.redirect_stdout(buf):
            _check_compositor(self.ctx.env)

        out = buf.getvalue()
        self.assertIn("mango", out)
        self.assertIn("正在运行", out)

    def test_detect_preferred_wm(self):
        """detect_preferred_wm returns running desktop or fallback."""
        import os
        from nyxuri.constants import detect_preferred_wm

        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "mango"}):
            self.assertEqual(detect_preferred_wm(), "mango")

        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "niri"}):
            self.assertEqual(detect_preferred_wm(), "niri")

    def test_checkbox_list_radio_group_mutual_exclusion(self):
        """CheckboxList with radio_group enforces single selection."""
        from io import StringIO
        from nyxuri.tui import CheckboxEntry, CheckboxList

        entries = [
            CheckboxEntry(key="wm_niri", label="Niri", checked=True, radio_group="wm"),
            CheckboxEntry(key="wm_mango", label="Mango", checked=True, radio_group="wm"),
            CheckboxEntry(key="app_waybar", label="Waybar", checked=True),
        ]
        chk = CheckboxList("title", entries)

        # In non-interactive mode with accept_defaults, at most one per radio_group is kept
        with patch("sys.stdin.isatty", return_value=False):
            res = chk.run(accept_defaults=True)
        self.assertIsNotNone(res)
        wm_selected = [k for k in res if k.startswith("wm_")]
        self.assertEqual(len(wm_selected), 1)
        self.assertEqual(wm_selected[0], "wm_niri")
        self.assertIn("app_waybar", res)

        # In interactive mode: pressing SPACE on mango deselects niri and selects mango
        entries2 = [
            CheckboxEntry(key="wm_niri", label="Niri", checked=True, radio_group="wm"),
            CheckboxEntry(key="wm_mango", label="Mango", checked=False, radio_group="wm"),
            CheckboxEntry(key="app_waybar", label="Waybar", checked=False),
        ]
        chk2 = CheckboxList("title", entries2)
        # DOWN (moves focus to mango) -> SPACE (toggles mango on, niri off) -> ENTER
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxuri.tui.read_key", side_effect=["DOWN", "SPACE", "ENTER"]), \
             patch("sys.stdout", new_callable=StringIO):
            res2 = chk2.run()

        self.assertEqual(res2, ["wm_mango"])

    def test_run_master_component_menu_uses_radio_for_wms(self):
        """Master component menu creates radio entries for all supported WMs."""
        from nyxuri.menus import run_master_component_menu
        from nyxuri.tui import CheckboxList
        import os

        captured_entries = []

        def fake_chk_run(self, accept_defaults=False):
            captured_entries.extend(self.entries)
            # return default checked items
            return [e.key for e in self.entries if not e.is_separator and e.checked]

        with patch.object(CheckboxList, "run", fake_chk_run), \
             patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "mango"}):
            res = run_master_component_menu()

        self.assertIsNotNone(res)
        wm_entries = [e for e in captured_entries if e.key in ("config_niri", "config_mango")]
        self.assertEqual(len(wm_entries), 2)
        for e in wm_entries:
            self.assertEqual(e.radio_group, "wm")

        # Because XDG_CURRENT_DESKTOP=mango, config_mango should be checked and config_niri unchecked
        mango_entry = next(e for e in wm_entries if e.key == "config_mango")
        niri_entry = next(e for e in wm_entries if e.key == "config_niri")
        self.assertTrue(mango_entry.checked)
        self.assertFalse(niri_entry.checked)

        # In returned configs dict, only mango should be present, not niri
        self.assertIn("mango", res["configs"])
        self.assertNotIn("niri", res["configs"])


if __name__ == "__main__":
    unittest.main()

