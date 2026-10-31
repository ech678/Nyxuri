"""P4 theme engine contract: matugen extraction slot, self-owned render."""
import glob
import io
import json
import os
import re
import shutil
import signal
import sys
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import subprocess
from pathlib import Path




class TestP4ThemeEngineContract(unittest.TestCase):
    """P4 theme contract: matugen as extraction slot, self-owned render engine.

    - golden master (terminal derivation, 16-role mirror, expression subset)
      runs through qmltestrunner against committed Noctalia reference outputs
    - MD3 reference vectors pin matugen's palette to the engine-agreed values
    - the extraction diff harness pins the known m3-content divergence
    """

    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cls.shell_dir = os.path.join(cls.repo_root, "shell")
        cls.fixtures = os.path.join(cls.shell_dir, "tests", "fixtures", "theme")

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None)

    def _matugen_json(self, image, scheme, mode):
        import subprocess
        res = subprocess.run(
            ["matugen", "--source-color-index", "0", "image", image,
             "--mode", mode, "--type", scheme, "--json", "hex", "-q"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)["colors"]

    def test_qml_golden_master(self):
        runner = shutil.which("qmltestrunner") or "/usr/lib/qt6/bin/qmltestrunner"
        if not os.path.exists(runner):
            self.skipTest("qmltestrunner not available; theme engine golden master not executed")
        env = dict(os.environ)
        env.update({
            "QT_QPA_PLATFORM": "offscreen",
            "QML_XHR_ALLOW_FILE_READ": "1",
            "QT_FORCE_STDERR_LOGGING": "1",
            "QT_ASSUME_STDERR_HAS_CONSOLE": "1",
        })
        import subprocess
        res = subprocess.run(
            [runner, "-input", os.path.join(self.shell_dir, "tests", "qml", "tst_ThemeContract.qml")],
            capture_output=True, text=True, timeout=120, env=env)
        self.assertIn("Totals:", res.stdout + res.stderr, res.stderr[-2000:])
        totals = self._totals_line(res.stdout)
        self.assertRegex(totals, r"Totals: \d+ passed, 0 failed")
        self.assertNotIn("FAIL!", res.stdout + res.stderr,
                         "golden master failures:\n" + (res.stdout + res.stderr)[-4000:])

    @staticmethod
    def _totals_line(output):
        for line in output.splitlines():
            if line.startswith("Totals:"):
                return line
        return ""

    def test_md3_reference_vectors(self):
        """matugen output pinned to the engine-agreed MCU reference values.

        The committed goldens carry Noctalia's deliberate container re-anchoring
        (see test_extraction_diff_matrix); every non-container key is
        byte-identical between the engines and therefore MCU-true.
        """
        if not shutil.which("matugen"):
            self.skipTest("matugen not installed; MD3 reference vectors not executed")
        divergence = {
            ("dark", "scheme-tonal-spot"): set(),
            ("light", "scheme-tonal-spot"): {"on_primary_container", "on_secondary_container",
                                             "on_tertiary_container", "on_error_container"},
            ("dark", "scheme-content"): {"on_primary_container", "on_secondary_container",
                                         "on_tertiary_container"},
            ("light", "scheme-content"): {"on_primary_container", "on_secondary_container",
                                          "on_tertiary_container", "on_error_container"},
        }
        golden = json.load(open(os.path.join(self.fixtures, "golden", "solid-tonal-spot.json"),
                                encoding="utf-8"))
        for (mode, scheme), known in divergence.items():
            if scheme != "scheme-tonal-spot":
                continue
            colors = self._matugen_json(os.path.join(self.fixtures, "images", "solid.png"),
                                        scheme, mode)
            self.assertEqual(len(colors), 50)
            for token, reference in golden[mode].items():
                if token.startswith("terminal") or token in ("hover", "on_hover") or token in known:
                    continue
                self.assertEqual(colors[token]["default"]["color"].lower(),
                                 reference.lower(),
                                 f"MD3 vector drift: {mode}/{token}")

    def test_extraction_diff_matrix(self):
        """matugen vs Noctalia reference: the divergence surface, pinned.

        Noctalia re-anchors on_*_container tones (visible, dE00 ≈ 10) — that
        is the measured cross-engine color diff this phase records. The mirror
        palette + color-scheme-set is the documented alignment for it. A change
        in the surface means the reference engine moved; re-measure.
        """
        if not shutil.which("matugen"):
            self.skipTest("matugen not installed; extraction diff not executed")
        expected = {
            ("dark", "scheme-tonal-spot"): set(),
            ("light", "scheme-tonal-spot"): {"on_primary_container", "on_secondary_container",
                                             "on_tertiary_container", "on_error_container"},
            ("dark", "scheme-content"): {"on_primary_container", "on_secondary_container",
                                         "on_tertiary_container"},
            ("light", "scheme-content"): {"on_primary_container", "on_secondary_container",
                                          "on_tertiary_container", "on_error_container"},
        }
        goldens = {
            "scheme-tonal-spot": json.load(open(
                os.path.join(self.fixtures, "golden", "solid-tonal-spot.json"), encoding="utf-8")),
            "scheme-content": json.load(open(
                os.path.join(self.fixtures, "golden", "solid-content.json"), encoding="utf-8")),
        }
        for (mode, scheme), known in expected.items():
            colors = self._matugen_json(os.path.join(self.fixtures, "images", "solid.png"),
                                        scheme, mode)
            drifted = set()
            for token, reference in goldens[scheme][mode].items():
                if token.startswith("terminal") or token in ("hover", "on_hover"):
                    continue
                if colors[token]["default"]["color"].lower() != reference.lower():
                    drifted.add(token)
            self.assertEqual(drifted, known,
                             f"{scheme}/{mode} divergence surface changed; re-measure")

    def test_theme_contract_files_exist(self):
        for rel in ("commons/ThemeColor.js", "commons/ThemePalette.js",
                    "commons/TemplateExpr.js",
                    "tests/qml/tst_ThemeContract.qml",
                    "tests/fixtures/theme/README.md"):
            self.assertTrue(os.path.isfile(os.path.join(self.shell_dir, rel)), rel)

    def test_builtin_templates_include_fcitx5(self):
        config_path = os.path.join(self.shell_dir, "app", "templates", "config.toml")
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[templates.fcitx5_theme]", content)
        self.assertIn("[templates.fcitx5_panel]", content)
        self.assertIn("[templates.fcitx5_highlight]", content)
        self.assertIn("~/.local/share/fcitx5/themes/nyxmellow/templates/theme.conf", content)
        self.assertIn("~/.local/share/fcitx5/themes/nyxmellow/templates/panel.svg", content)
        self.assertIn("~/.local/share/fcitx5/themes/nyxmellow/templates/highlight.svg", content)
        self.assertIn("ReloadAddonConfig", content)

        dashboard_page = os.path.join(self.shell_dir, "plugins", 'settings', 'dashwindow', "DashboardThemesPage.qml")
        with open(dashboard_page, "r", encoding="utf-8") as f:
            dash_content = f.read()
        self.assertIn('"id": "fcitx5"', dash_content)

    def test_kitty_apply_hook_strips_noctalia_and_orders_before_custom(self):
        import subprocess
        from tests.utils import TempEnv

        with TempEnv() as env:
            kitty_dir = env.home / ".config" / "kitty"
            kitty_dir.mkdir(parents=True, exist_ok=True)
            themes_dir = kitty_dir / "themes"
            themes_dir.mkdir(parents=True, exist_ok=True)
            (themes_dir / "nyxuri.conf").write_text("# nyxuri theme\n", encoding="utf-8")

            # Dirty kitty.conf containing legacy noctalia includes and inverted order
            dirty_conf = (
                "window_padding_width 5\n"
                "# BEGIN_KITTY_THEME\n"
                "# Noctalia\n"
                "include current-theme.conf\n"
                "# END_KITTY_THEME\n\n"
                "# Shortcuts\n"
                "map ctrl+c copy_and_clear_or_interrupt\n\n"
                "# User Custom Configurations\n"
                "include __custom__.conf\n\n"
                "include themes/nyxuri.conf\n"
                "include themes/noctalia.conf\n"
            )
            conf_path = kitty_dir / "kitty.conf"
            conf_path.write_text(dirty_conf, encoding="utf-8")

            hook_script = os.path.join(self.shell_dir, "app", "templates", "kitty", "kitty-apply.sh")
            res = subprocess.run(["bash", hook_script], capture_output=True, text=True,
                                 env=dict(os.environ, XDG_CONFIG_HOME=str(env.home / ".config")))
            self.assertEqual(res.returncode, 0, f"kitty-apply failed: {res.stderr}")

            result = conf_path.read_text(encoding="utf-8")
            self.assertNotIn("themes/noctalia.conf", result)
            self.assertNotIn("current-theme.conf", result)
            self.assertNotIn("BEGIN_KITTY_THEME", result)
            self.assertEqual(result.count("include themes/nyxuri.conf"), 1)

            # Ensure include themes/nyxuri.conf is placed BEFORE include __custom__.conf
            nyxuri_idx = result.find("include themes/nyxuri.conf")
            custom_idx = result.find("include __custom__.conf")
            self.assertGreater(nyxuri_idx, -1)
            self.assertGreater(custom_idx, -1)
            self.assertLess(nyxuri_idx, custom_idx, "nyxuri theme must precede __custom__.conf")

            # Verify idempotency on second run
            res2 = subprocess.run(["bash", hook_script], capture_output=True, text=True,
                                  env=dict(os.environ, XDG_CONFIG_HOME=str(env.home / ".config")))
            self.assertEqual(res2.returncode, 0)
            self.assertEqual(conf_path.read_text(encoding="utf-8"), result)

    def test_kitty_shortcuts_orthodox(self):
        """T0 copy/paste verdict: no Windows-style hijacks; presets ship identical shortcuts."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        confs = [
            os.path.join(repo_root, "plugins", "kitty", "kitty.conf"),
            os.path.join(repo_root, "plugins", "kitty", "__forms__", "transparent", "kitty.conf"),
        ]
        retired = (
            "copy_and_clear_or_interrupt",
            "map ctrl+v paste_from_clipboard",
            "mouse_map right press",
            "map ctrl+a pipe",
        )
        shortcut_blocks = []
        for conf in confs:
            with open(conf, "r", encoding="utf-8") as f:
                content = f.read()
            # Explicit-copy semantics: selecting text must not silently take the clipboard.
            self.assertIn("copy_on_select no", content, conf)
            for hijack in retired:
                self.assertNotIn(hijack, content, f"{conf}: retired hijack must not return: {hijack}")
            shortcut_blocks.append(sorted(
                line.strip() for line in content.splitlines()
                if line.strip().startswith(("map ", "mouse_map "))))
        self.assertEqual(shortcut_blocks[0], shortcut_blocks[1],
                         "kitty.conf and transparent preset must ship identical shortcut blocks")

    def test_template_service_avoids_double_reload_and_fixes_watchdog(self):
        svc_path = os.path.join(self.shell_dir, "services", "TemplateService.qml")
        with open(svc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("hookWatchdog", content)
        self.assertIn("stepWatchdog.stop()", content)
        self.assertIn("templateInput.path === template.inputPath", content)
        self.assertIn("Qt.callLater(root.renderNext)", content)
        self.assertIn('watchStep("Output write")', content)
        self.assertIn('"XDG_CACHE_HOME": Paths.xdgCacheHome', content)
        self.assertIn("hookStderr", content)
        self.assertRegex(content, r"onThemeModeChanged\(\)\s*\{[^}]*root\.renderAll\(\)")

        paths_qml = os.path.join(self.shell_dir, "app", "Paths.qml")
        with open(paths_qml, "r", encoding="utf-8") as f:
            paths_content = f.read()
        self.assertIn("readonly property string xdgCacheHome:", paths_content)

    def test_starship_apply_hook_survives_shell_private_cache_and_updates_palette(self):
        import subprocess
        from tests.utils import TempEnv

        with TempEnv() as env:
            config_dir = env.home / ".config"
            config_dir.mkdir(parents=True, exist_ok=True)
            cache_dir = env.home / ".cache" / "nyxuri"
            cache_dir.mkdir(parents=True, exist_ok=True)
            palette_file = cache_dir / "starship-palette.toml"
            palette_file.write_text(
                '[palettes.nyxuri]\n'
                'blue = "#123456"\n'
                'magenta = "#654321"\n',
                encoding="utf-8"
            )

            # starship.toml with legacy noctalia palette
            starship_conf = config_dir / "starship.toml"
            starship_conf.write_text(
                'palette = "noctalia"\n'
                '# >>> NOCTALIA STARSHIP PALETTE >>>\n'
                '[palettes.noctalia]\n'
                'blue = "#000000"\n'
                '# <<< NOCTALIA STARSHIP PALETTE <<<\n',
                encoding="utf-8"
            )

            hook_script = os.path.join(self.shell_dir, "app", "templates", "starship", "starship-apply.sh")

            # Even if XDG_CACHE_HOME points to private /nyxuri-shell namespace, the hook must succeed
            isolated_cache = env.home / ".cache" / "nyxuri-shell"
            isolated_cache.mkdir(parents=True, exist_ok=True)
            res = subprocess.run(
                ["bash", hook_script],
                capture_output=True,
                text=True,
                env=dict(
                    os.environ,
                    HOME=str(env.home),
                    XDG_CONFIG_HOME=str(config_dir),
                    XDG_CACHE_HOME=str(isolated_cache)
                )
            )
            self.assertEqual(res.returncode, 0, f"starship-apply failed: {res.stderr}")

            result = starship_conf.read_text(encoding="utf-8")
            self.assertIn('palette = "nyxuri"', result)
            self.assertNotIn('palette = "noctalia"', result)
            self.assertNotIn('# >>> NOCTALIA STARSHIP PALETTE >>>', result)
            self.assertIn('# >>> NYXURI STARSHIP PALETTE >>>', result)
            self.assertIn('blue = "#123456"', result)
            self.assertIn('magenta = "#654321"', result)


if __name__ == "__main__":
    unittest.main()
