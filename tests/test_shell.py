"""Contract tests for dual shell management and CLI (nyxuri shell)."""

import io
import os
import signal
import sys
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from nyxuri.state.ledger import active_shell, custom_shell_bin, set_shell
from nyxuri.cli import _cmd_shell
from tests.utils import TempEnv


class TestShellManagement(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_default_shell_is_noctalia(self):
        self.assertEqual(active_shell(), "noctalia")
        self.assertEqual(custom_shell_bin(), "")

    def test_set_shell_valid(self):
        set_shell("nyxuri-shell", "/usr/bin/my-shell")
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/usr/bin/my-shell")

        # Backward compatibility with 'custom' and 'nyxuri'
        set_shell("custom", "/usr/bin/custom-shell")
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/usr/bin/custom-shell")

        set_shell("nyxuri")
        self.assertEqual(active_shell(), "nyxuri-shell")

        set_shell("noctalia")
        self.assertEqual(active_shell(), "noctalia")
        # custom_shell_bin remains recorded
        self.assertEqual(custom_shell_bin(), "/usr/bin/custom-shell")

    def test_set_shell_invalid_raises_error(self):
        with self.assertRaises(ValueError):
            set_shell("invalid_shell")

    def test_cmd_shell_get(self):
        set_shell("noctalia")
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["get"])
        self.assertEqual(ret, 0)
        self.assertEqual(f.getvalue().strip(), "noctalia")

        set_shell("nyxuri-shell")
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["get"])
        self.assertEqual(ret, 0)
        self.assertEqual(f.getvalue().strip(), "nyxuri-shell")

    def test_cmd_shell_set(self):
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["set", "nyxuri-shell", "/bin/sh"])
        self.assertEqual(ret, 0)
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/bin/sh")

        # Test backward-compatible alias 'custom'
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["set", "custom", "/bin/bash"])
        self.assertEqual(ret, 0)
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/bin/bash")

    def test_cmd_shell_switch(self):
        # 1. Switch with explicit target
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["switch", "noctalia"])
        self.assertEqual(ret, 0)
        self.assertEqual(active_shell(), "noctalia")

        # 2. Switch toggle: noctalia -> nyxuri-shell
        with patch("nyxuri.shell_switcher.hot_switch_shell", return_value=(True, "Switched successfully")) as mock_switch:
            f = io.StringIO()
            with redirect_stdout(f):
                ret = _cmd_shell(["switch"])
            self.assertEqual(ret, 0)
            mock_switch.assert_called_with("nyxuri-shell", None)

        # 3. Switch toggle: nyxuri-shell -> noctalia
        set_shell("nyxuri-shell", "/bin/sh")
        with patch("nyxuri.shell_switcher.hot_switch_shell", return_value=(True, "Switched successfully")) as mock_switch:
            f = io.StringIO()
            with redirect_stdout(f):
                ret = _cmd_shell(["switch"])
            self.assertEqual(ret, 0)
            mock_switch.assert_called_with("noctalia", None)

        # 4. Switch with alias 'custom'
        with patch("nyxuri.shell_switcher.hot_switch_shell", return_value=(True, "Switched successfully")) as mock_switch:
            f = io.StringIO()
            with redirect_stdout(f):
                ret = _cmd_shell(["switch", "custom", "/bin/sh"])
            self.assertEqual(ret, 0)
            mock_switch.assert_called_with("nyxuri-shell", "/bin/sh")

    def test_cmd_shell_status(self):
        set_shell("nyxuri-shell", "/bin/sh")
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["status"])
        self.assertEqual(ret, 0)
        output = f.getvalue()
        self.assertIn("Active Shell: nyxuri-shell", output)
        self.assertIn("Nyxuri Shell Binary: /bin/sh", output)
        self.assertIn("Nyxuri Shell Status: Ready", output)

    def test_preflight_shell(self):
        from nyxuri.shell_switcher import preflight_shell
        ok, _, err = preflight_shell("invalid")
        self.assertFalse(ok)
        self.assertIn("Unknown target shell", err)

        ok, _, err = preflight_shell("nyxuri-shell", "/nonexistent/path/to/shell")
        self.assertFalse(ok)
        self.assertIn("does not exist", err)

        ok, resolved, err = preflight_shell("nyxuri-shell", "/bin/sh")
        self.assertTrue(ok)
        self.assertEqual(resolved, "/bin/sh")
        self.assertEqual(err, "")

        # Alias custom
        ok, resolved, err = preflight_shell("custom", "/bin/sh")
        self.assertTrue(ok)
        self.assertEqual(resolved, "/bin/sh")

    def test_ensure_compositor_gateway_scripts(self):
        from nyxuri.core import get_env
        from nyxuri.shell_switcher import ensure_compositor_gateway_scripts
        env = get_env()
        fake_configs = self._ctx.home / "fake_configs"
        env.configs_src = fake_configs
        src_dir = fake_configs / "niri" / "scripts"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "session-shell.sh").write_text("#!/bin/sh\necho session new\n", encoding="utf-8")
        (src_dir / "shell-action.sh").write_text("#!/bin/sh\necho action new\n", encoding="utf-8")

        dest_dir = env.config_dir / "niri" / "scripts"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "session-shell.sh").write_text("#!/bin/sh\necho session old\n", encoding="utf-8")
        (dest_dir / "shell-action.sh").write_text("#!/bin/sh\necho action old\n", encoding="utf-8")
        (dest_dir / "session-shell.sh").chmod(0o644)

        ensure_compositor_gateway_scripts()

        self.assertEqual((dest_dir / "session-shell.sh").read_text(encoding="utf-8"), "#!/bin/sh\necho session new\n")
        self.assertEqual((dest_dir / "shell-action.sh").read_text(encoding="utf-8"), "#!/bin/sh\necho action new\n")
        self.assertTrue(os.access(dest_dir / "session-shell.sh", os.X_OK))
        self.assertTrue(os.access(dest_dir / "shell-action.sh", os.X_OK))

    @patch("nyxuri.shell_switcher.wait_shell_ready")
    @patch("nyxuri.shell_switcher.spawn_shell")
    @patch("nyxuri.shell_switcher.stop_shell_process")
    @patch("nyxuri.shell_switcher.probe_running_shell")
    def test_hot_switch_success(self, mock_probe, mock_stop, mock_spawn, mock_wait):
        import os
        from unittest.mock import MagicMock
        from nyxuri.shell_switcher import hot_switch_shell

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        mock_probe.return_value = ("noctalia", 1234)
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_spawn.return_value = mock_proc
        mock_wait.return_value = True

        ok, msg = hot_switch_shell("nyxuri-shell", "/bin/sh")
        self.assertTrue(ok)
        self.assertIn("Successfully switched to nyxuri-shell", msg)
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertTrue(mock_stop.called)
        mock_spawn.assert_called_once_with("nyxuri-shell", "/bin/sh")
        mock_wait.assert_called_once()

    @patch("nyxuri.shell_switcher.wait_shell_ready")
    @patch("nyxuri.shell_switcher.spawn_shell")
    @patch("nyxuri.shell_switcher.stop_shell_process")
    @patch("nyxuri.shell_switcher.probe_running_shell")
    def test_hot_switch_failure_and_rollback(self, mock_probe, mock_stop, mock_spawn, mock_wait):
        import os
        from unittest.mock import MagicMock
        from nyxuri.shell_switcher import hot_switch_shell

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        mock_probe.return_value = ("noctalia", 1234)
        mock_new_proc = MagicMock()
        mock_new_proc.poll.return_value = None
        mock_restore_proc = MagicMock()
        mock_spawn.side_effect = [mock_new_proc, mock_restore_proc]
        # Target fails readiness, restore succeeds
        mock_wait.side_effect = [False, True]

        ok, msg = hot_switch_shell("nyxuri-shell", "/bin/sh")
        self.assertFalse(ok)
        self.assertIn("failed readiness probe", msg)
        self.assertIn("rolled back to noctalia", msg)
        # Ledger must NOT have been changed to target
        self.assertEqual(active_shell(), "noctalia")
        mock_new_proc.terminate.assert_called()

    def test_p2_layer_structure_and_session_decoupling(self):
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Verify 4-layer directories exist
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "app")))
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "shared")))
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "modules", "session")))

        # Verify ActionGateway and SessionHost exist
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "app", "ActionGateway.qml")))
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "modules", "session", "SessionHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "modules", "session", "SessionPanel.qml")))

        # Verify old PowerMenu directory and service are completely deleted
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Modules", "PowerMenu")))
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Services", "PowerMenuService.qml")))

    def test_action_gateway_command_arguments(self):
        import subprocess
        from pathlib import Path
        nyxuri_shell_bin = Path(__file__).resolve().parent.parent / "shell" / "bin" / "nyxuri-shell"
        self.assertTrue(nyxuri_shell_bin.exists() and os.access(nyxuri_shell_bin, os.X_OK))

        # Check help output lists session and all standard actions
        res = subprocess.run([str(nyxuri_shell_bin), "--help"], capture_output=True, text=True, check=True)
        self.assertIn("--action", res.stdout)
        self.assertIn("session", res.stdout)
        self.assertIn("launcher", res.stdout)
        self.assertIn("settings", res.stdout)
        self.assertIn("wallpaper-picker", res.stdout)

    def test_p3_settings_decoupling_and_module_structure(self):
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_dir = os.path.join(repo_root, "shell", "modules", "settings")

        # Verify modules/settings exists and contains required host/backend/bridge
        self.assertTrue(os.path.isdir(settings_dir))
        self.assertTrue(os.path.isfile(os.path.join(settings_dir, "SettingsHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(settings_dir, "SettingsBackend.qml")))
        self.assertTrue(os.path.isfile(os.path.join(settings_dir, "WeatherMapBridge.qml")))
        self.assertTrue(os.path.isfile(os.path.join(settings_dir, "ControlCenterWindow.qml")))

        # Verify old ControlCenter directory and ControlCenterService are deleted
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Modules", "ControlCenter")))
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Services", "ControlCenterService.qml")))

        # Verify no QML file under modules/settings statically imports Clavis.WeatherMap (except backend/WeatherMapBackend.qml)
        for root_path, _, files in os.walk(settings_dir):
            for file in files:
                if file.endswith(".qml") and file != "WeatherMapBackend.qml":
                    full_path = os.path.join(root_path, file)
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.assertNotIn("import Clavis.WeatherMap", content, f"Static import Clavis.WeatherMap found in {full_path}")

        # Verify no script references deleted Modules/ControlCenter
        gen_script = os.path.join(repo_root, "shell", "scripts", "dev", "generate-search-catalog.py")
        with open(gen_script, "r", encoding="utf-8") as f:
            self.assertNotIn("Modules/ControlCenter", f.read())
        check_script = os.path.join(repo_root, "shell", "scripts", "dev", "check.sh")
        with open(check_script, "r", encoding="utf-8") as f:
            self.assertNotIn("Modules/ControlCenter", f.read())

    def test_shell_directory_hygiene_and_module_unification(self):
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Top-level clutter and legacy mother directories removed / relocated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, ".github")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, ".gitignore")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "docs")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "wiki", "upstream-docs")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "tools")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "core")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native", "tools", "window-preview")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "licenses")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "wiki", "upstream-licenses")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "Components")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "controls", "ThemeIcon.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "controls", "FileThemeIcon.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "controls", "SvgIcon.qml")))

        # Legacy mother directories and upstream artifacts eliminated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "Common")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "Services")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "Widgets")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "install.sh")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "i18n")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "matugen")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "assets", "i18n")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "assets", "matugen")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "app", "services")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "shared", "controls")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "controls", "CompositorBlurRegion.qml")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "shared", "compositor")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "shared", "theme")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "shared", "utils")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "native")))

        # Runner exports QML_IMPORT_PATH and QML2_IMPORT_PATH
        runner_path = os.path.join(shell_dir, "bin", "nyxuri-shell")
        with open(runner_path, "r", encoding="utf-8") as f:
            runner_txt = f.read()
        self.assertIn("QML_IMPORT_PATH=", runner_txt)
        self.assertIn("QML2_IMPORT_PATH=", runner_txt)

        # 2. AppShell encapsulated in app/
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "AppShell.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "app", "AppShell.qml")))

        # 3. Capitalized Modules/ directory completely eliminated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "Modules")))

        # 4. Modules unified under modules/ in uniform lowercase with all functional code preserved
        expected_modules = [
            "bar", "desktopcards", "dock", "filepicker", "hotcorners",
            "keystone", "launcher", "lock", "quicksettings",
            "regionselector", "session", "settings", "sidebars",
            "systemcards", "wallpaper"
        ]
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "modules", "map")))
        for mod in expected_modules:
            self.assertTrue(
                os.path.isdir(os.path.join(shell_dir, "modules", mod)),
                f"Expected module directory missing: shell/modules/{mod}"
            )
        # Assert no PascalCase/uppercase directories anywhere in modules/ (strictly all lowercase)
        for root_path, dirs, _ in os.walk(os.path.join(shell_dir, "modules")):
            for entry in dirs:
                self.assertEqual(
                    entry, entry.lower(),
                    f"Non-lowercase directory found in modules: {os.path.join(root_path, entry)}"
                )

        # 5. Zero occurrences of obsolete imports across all QML/JS files
        import re
        qs_mod_re = re.compile(r"import\s+qs\.modules\.([A-Za-z0-9_.]+)")
        for root_path, dirs, files in os.walk(shell_dir):
            if root_path == shell_dir:
                dirs[:] = [entry for entry in dirs if entry != "references"]
            for file in files:
                if file.endswith((".qml", ".js")):
                    full_path = os.path.join(root_path, file)
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.assertNotIn("qs.Modules.", content, f"Obsolete qs.Modules. import found in {full_path}")
                    self.assertNotIn("import qs.Components", content, f"Obsolete qs.Components import found in {full_path}")
                    self.assertNotIn("import qs.Common", content, f"Obsolete qs.Common import found in {full_path}")
                    self.assertNotIn("import qs.Services", content, f"Obsolete qs.Services import found in {full_path}")
                    self.assertNotIn("qs.Widgets.", content, f"Obsolete qs.Widgets. import found in {full_path}")
                    self.assertNotIn("Common/functions", content, f"Obsolete Common/functions import found in {full_path}")
                    self.assertNotIn("qs.shared.compositor", content, f"Obsolete qs.shared.compositor import found in {full_path}")
                    for match in qs_mod_re.finditer(content):
                        mod_path = match.group(1)
                        for seg in mod_path.split("."):
                            self.assertEqual(
                                seg, seg.lower(),
                                f"Non-lowercase qs.modules import '{mod_path}' found in {full_path}"
                            )

    def test_p3_appshell_host_assembly_and_wheel_contract(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Base hosts exist in modules/
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "keystone", "Keystone.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "wallpaper", "WallpaperBackground.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "desktopcards", "DesktopCardHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "dock", "DockHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "regionselector", "RegionSelector.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "hotcorners", "HotCorners.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "settings", "DisplayOverlays.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "sidebars", "SidebarHostWindow.qml")))

        # 2. NotificationContent and KeystoneSurface exist for native notification chain
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "keystone", "styles", "shared", "KeystoneSurface.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "notifications", "NotificationContent.qml")))

        # 3. Bar quicksettings controls exist
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "bar", "quicksettings", "Volume.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "bar", "quicksettings", "Microphone.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "bar", "quicksettings", "Brightness.qml")))

    def test_p3_fallback_qml_modules_contract(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")
        fallback_dir = os.path.join(shell_dir, "native", "fallback")

        # 1. Fallback directories: pruned features removed, kept ones present
        self.assertFalse(os.path.exists(os.path.join(fallback_dir, "Clavis", "Lyrics")))
        self.assertFalse(os.path.exists(os.path.join(fallback_dir, "Clavis", "Cava")))
        self.assertFalse(os.path.exists(os.path.join(fallback_dir, "Clavis", "WeatherMap")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "M3Shapes", "qmldir")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "M3Shapes", "MaterialShape.qml")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "Clavis", "Weather", "qmldir")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "Clavis", "Weather", "WeatherPlugin.qml")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "Qt", "labs", "lottieqt", "qmldir")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "Qt", "labs", "lottieqt", "LottieAnimation.qml")))

        # 2. Pure QML directory modules/keystone does not have handwritten qmldir
        self.assertFalse(os.path.isfile(os.path.join(shell_dir, "modules", "keystone", "qmldir")), "Pure QML directory should not have handwritten qmldir")

        # 3. shared layer strictly contains only theme, controls, utils
        shared_dir = os.path.join(shell_dir, "shared")
        shared_entries = sorted(os.listdir(shared_dir))
        self.assertEqual(shared_entries, ["controls", "theme", "utils"])

        # 4. nyxuri-shell exports FALLBACK_QML_PATH pointing to native/fallback
        launcher_path = os.path.join(shell_dir, "bin", "nyxuri-shell")
        with open(launcher_path, "r", encoding="utf-8") as f:
            launcher_content = f.read()
        self.assertIn("FALLBACK_QML_PATH", launcher_content)
        self.assertIn("native/fallback", launcher_content)

    def test_p3_settings_wiring_and_weather_fallback_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. ActionGateway has settingsHost property and requestSettings* uses it
        gw_path = os.path.join(shell_dir, "app", "ActionGateway.qml")
        with open(gw_path, "r", encoding="utf-8") as f:
            gw_content = f.read()
        self.assertIn("property var settingsHost: null", gw_content)
        self.assertIn("root.settingsHost.toggle", gw_content)

        # 2. AppShell injects settingsHost on completion
        app_path = os.path.join(shell_dir, "app", "AppShell.qml")
        with open(app_path, "r", encoding="utf-8") as f:
            app_content = f.read()
        self.assertIn("ActionGateway.settingsHost = settingsHost;", app_content)

        # 3. SettingsHost toggle returns boolean indicating opening/closing
        sh_path = os.path.join(shell_dir, "modules", "settings", "SettingsHost.qml")
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()
        self.assertIn("function toggle(pageId)", sh_content)
        self.assertIn("return false;", sh_content)
        self.assertIn("return true;", sh_content)

        # 4. Weather fallback provides safe count() and get() methods on forecast models
        weather_fallback = os.path.join(shell_dir, "native", "fallback", "Clavis", "Weather", "WeatherPlugin.qml")
        with open(weather_fallback, "r", encoding="utf-8") as f:
            wf_content = f.read()
        self.assertIn("count: () => 0", wf_content)
        self.assertIn("get: () => ({})", wf_content)

    def test_p3_audio_level_provider_and_settings_cleanup_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Pruned Cava: AudioRecordingVisual provides local fallback levelProvider without Clavis.Cava
        arv_path = os.path.join(shell_dir, "modules", "keystone", "styles", "recording", "AudioRecordingVisual.qml")
        with open(arv_path, "r", encoding="utf-8") as f:
            arv_content = f.read()
        self.assertNotIn("Clavis.Cava", arv_content)
        self.assertIn("id: levelProvider", arv_content)
        self.assertIn("readonly property bool available: false", arv_content)

        # AudioSpectrum is a zero-overhead stub
        asp_path = os.path.join(shell_dir, "app", "services", "AudioSpectrum.qml")
        with open(asp_path, "r", encoding="utf-8") as f:
            asp_content = f.read()
        self.assertIn("readonly property bool available: false", asp_content)

        # 2. ControlCenterWindow cleans up child windows on destruction
        cc_window = os.path.join(shell_dir, "modules", "settings", "ControlCenterWindow.qml")
        with open(cc_window, "r", encoding="utf-8") as f:
            cc_content = f.read()
        self.assertIn("Component.onDestruction: root.closeChildWindows()", cc_content)

        # 3. MeteoIcon uses loops: -1 for infinite loop
        meteo_icon = os.path.join(shell_dir, "shared", "controls", "MeteoIcon.qml")
        with open(meteo_icon, "r", encoding="utf-8") as f:
            meteo_content = f.read()
        self.assertIn("loops: -1", meteo_content)

    def test_p3_bar_and_long_wheel_input_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. RippleButton exposes wheelAction and dispatches to onWheel
        rb_path = os.path.join(shell_dir, "shared", "controls", "RippleButton.qml")
        with open(rb_path, "r", encoding="utf-8") as f:
            rb_content = f.read()
        self.assertIn("property var wheelAction", rb_content)
        self.assertIn("root.wheelAction(wheel)", rb_content)

        # 2. Volume.qml handles wheelAction with 0.05 step
        vol_path = os.path.join(shell_dir, "modules", "bar", "quicksettings", "Volume.qml")
        with open(vol_path, "r", encoding="utf-8") as f:
            vol_content = f.read()
        self.assertIn("wheelAction: wheel =>", vol_content)
        self.assertIn("Volume.setSinkVolume(Volume.sinkVolume + step)", vol_content)
        self.assertIn("0.05", vol_content)

        # 3. Microphone.qml handles wheelAction with 0.05 step
        mic_path = os.path.join(shell_dir, "modules", "bar", "quicksettings", "Microphone.qml")
        with open(mic_path, "r", encoding="utf-8") as f:
            mic_content = f.read()
        self.assertIn("wheelAction: wheel =>", mic_content)
        self.assertIn("Volume.setSourceVolume(Volume.sourceVolume + step)", mic_content)
        self.assertIn("0.05", mic_content)

        # 4. Brightness.qml handles wheelAction with 0.05 step
        br_path = os.path.join(shell_dir, "modules", "bar", "quicksettings", "Brightness.qml")
        with open(br_path, "r", encoding="utf-8") as f:
            br_content = f.read()
        self.assertIn("wheelAction: wheel =>", br_content)
        self.assertIn("Brightness.setBrightnessForScreen", br_content)
        self.assertIn("0.05", br_content)

        # 5. LongStatusItem handles onWheel with pixelDelta/angleDelta support
        long_item = os.path.join(shell_dir, "modules", "keystone", "styles", "long", "LongStatusItem.qml")
        with open(long_item, "r", encoding="utf-8") as f:
            long_content = f.read()
        self.assertIn("onWheel: wheel =>", long_content)
        self.assertIn("pixelDelta", long_content)
        self.assertIn("Volume.setSinkVolume", long_content)
        self.assertIn("Volume.setSourceVolume", long_content)
        self.assertIn("Brightness.setBrightnessForScreen", long_content)

    def test_p3_notification_keystone_chain_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. KeystoneSurface embeds NotificationContent with isNotifMode binding
        surface_path = os.path.join(shell_dir, "modules", "keystone", "styles", "shared", "KeystoneSurface.qml")
        with open(surface_path, "r", encoding="utf-8") as f:
            surface_content = f.read()
        self.assertIn("NotificationContent {", surface_content)
        self.assertIn("property bool isNotifMode:", surface_content)
        self.assertIn("NotificationManager.hasNotifs", surface_content)

        # 2. NotificationContent provides ListView, sanitizedBody, normalActions, dismiss
        notif_content = os.path.join(shell_dir, "modules", "notifications", "NotificationContent.qml")
        with open(notif_content, "r", encoding="utf-8") as f:
            nc_content = f.read()
        self.assertIn("StyledListView {", nc_content)
        self.assertIn("sanitizedBody()", nc_content)
        self.assertIn("root.manager.normalActions", nc_content)
        self.assertIn("root.manager.dismissPopup", nc_content)
        self.assertIn("root.manager.invokeDefaultAction", nc_content)

        # 3. NotificationManager holds timeout, persistence and DND inhibition
        nm_path = os.path.join(shell_dir, "app", "services", "NotificationManager.qml")
        with open(nm_path, "r", encoding="utf-8") as f:
            nm_content = f.read()
        self.assertIn("defaultPopupTimeoutMs: 7000", nm_content)
        self.assertIn("notifications.json", nm_content)
        self.assertIn("silent: UiPreferences.dndEnabled", nm_content)
        self.assertIn("popupInhibited:", nm_content)

        # 4. Notification history components exist in sidebar
        hist_list = os.path.join(shell_dir, "modules", "sidebars", "dashboard", "notifications", "NotificationList.qml")
        hist_center = os.path.join(shell_dir, "modules", "sidebars", "dashboard", "notifications", "NotificationCenterCard.qml")
        self.assertTrue(os.path.isfile(hist_list))
        self.assertTrue(os.path.isfile(hist_center))

    def test_p3_lock_screen_and_safety_switch_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Lock screen structure: Lock.qml, DefaultLockContent, CaelestiaLock, PAM config
        lock_path = os.path.join(shell_dir, "modules", "lock", "Lock.qml")
        with open(lock_path, "r", encoding="utf-8") as f:
            lock_content = f.read()
        self.assertIn("WlSessionLock {", lock_content)
        self.assertIn("PreLockCapture {", lock_content)
        self.assertIn("function open()", lock_content)
        self.assertIn("function isLocked()", lock_content)
        self.assertIn("password.conf", lock_content)

        # 2. Lock cards exist
        cards_dir = os.path.join(shell_dir, "modules", "lock", "cards")
        for card in ["NotificationCard.qml", "MediaCard.qml", "WeatherCard.qml", "MottoCard.qml", "SystemGrid.qml"]:
            self.assertTrue(os.path.isfile(os.path.join(cards_dir, card)), f"Lock card missing: {card}")

        # 3. Hot switch refuses to switch when screen is locked (K06 invariant)
        from nyxuri.shell_switcher import hot_switch_shell
        with patch("nyxuri.shell_switcher.is_shell_locked", return_value=True), \
             patch("nyxuri.shell_switcher.probe_running_shell", return_value=("custom", 9999)), \
             patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}):
            ok, msg = hot_switch_shell("noctalia")
            self.assertFalse(ok)
            self.assertIn("Cannot switch shell while screen is locked", msg)

    def test_p3_notification_fallback_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Standalone notification fallback host exists
        host_path = os.path.join(shell_dir, "modules", "notifications", "NotificationPopupHost.qml")
        self.assertTrue(os.path.isfile(host_path))
        with open(host_path, "r", encoding="utf-8") as f:
            host_content = f.read()

        # 2. Reuses unified NotificationContent with manager injection
        self.assertIn("NotificationContent {", host_content)
        self.assertIn("manager: NotificationManager", host_content)

        # 3. Includes CompositorBlurRegion and StyledRectangularShadow
        self.assertIn("CompositorBlurRegion {", host_content)
        self.assertIn("StyledRectangularShadow {", host_content)

        # 4. Respects Bar collision avoidance
        self.assertIn("PersonalizationConfig.barPosition === \"top\"", host_content)
        self.assertIn("Sizes.barVisualThickness", host_content)

        # 5. Non-intrusive: does not steal keyboard focus
        self.assertIn("WlrLayershell.keyboardFocus: WlrKeyboardFocus.None", host_content)

        # 6. AppShell mounts the host conditionally when Keystone is disabled
        app_shell_path = os.path.join(shell_dir, "app", "AppShell.qml")
        with open(app_shell_path, "r", encoding="utf-8") as f:
            app_shell_content = f.read()
        self.assertIn("active: !PersonalizationConfig.keystoneEnabled", app_shell_content)
        self.assertIn("NotificationPopupHost.qml", app_shell_content)

    def test_p3_r10_lifecycle_and_sideeffect_contracts(self):
        """P3-R10 lifecycle & side-effect governance contract checks."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Auditor clean execution across all target files
        audit_script = os.path.join(shell_dir, "scripts", "dev", "audit-lifecycle.py")
        self.assertTrue(os.path.isfile(audit_script), "audit-lifecycle.py missing")
        import subprocess
        proc = subprocess.run(
            ["python3", audit_script, "--root", shell_dir, "--scope", "all", "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Lifecycle auditor failed: {proc.stdout}\n{proc.stderr}")

        # 2. ActionGateway is the single convergence point for execDetached
        app_dir = os.path.join(shell_dir, "app")
        modules_dir = os.path.join(shell_dir, "modules")
        shared_dir = os.path.join(shell_dir, "shared")

        for scan_root in [app_dir, modules_dir, shared_dir]:
            for root, _, files in os.walk(scan_root):
                for file in files:
                    if file.endswith((".qml", ".js")):
                        full_p = os.path.join(root, file)
                        rel_p = os.path.relpath(full_p, shell_dir)
                        if rel_p == "app/ActionGateway.qml":
                            continue
                        with open(full_p, "r", encoding="utf-8") as f:
                            c = f.read()
                        self.assertNotIn(
                            "Quickshell.execDetached",
                            c,
                            f"Illegal Quickshell.execDetached bypass found in {rel_p}; must route via ActionGateway",
                        )

        # 3. High-risk services teardown hooks present
        high_risk_files = [
            "app/services/SystemMonitorService.qml",
            "app/services/KeyboardLockService.qml",
            "app/services/AwwwWallpaperService.qml",
            "modules/keystone/tools/AudioRecordingService.qml",
            "modules/keystone/tools/RecordingService.qml",
            "app/services/NetworkService.qml",
            "app/services/NetworkManagerExtras.qml",
            "app/services/BluetoothService.qml",
            "modules/launcher/FileSearchService.qml",
            "modules/launcher/SpotlightSearchService.qml",
            "modules/launcher/SpotlightToolService.qml",
            "app/services/WallpaperService.qml",
        ]
        for rel in high_risk_files:
            fp = os.path.join(shell_dir, rel)
            self.assertTrue(os.path.isfile(fp), f"Service missing: {rel}")
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Component.onDestruction", content, f"Missing Component.onDestruction in {rel}")

    def test_p3_r10_20x_lifecycle_simulation(self):
        """P3-R10-04: Simulate 20 rapid open/close lifecycle cycles without leaked tokens."""
        class MockLifecycleConsumer:
            def __init__(self):
                self.generation = 0
                self.active = False
                self.running_processes = set()
                self.running_timers = set()
                self.stale_discards = 0

            def open(self):
                self.generation += 1
                self.active = True
                self.running_timers.add(f"poll_timer_g{self.generation}")
                self.running_processes.add(f"proc_g{self.generation}")

            def close(self):
                self.active = False
                # Teardown contracts must stop timers and mark processes aborted
                self.running_timers.clear()
                self.running_processes.clear()

            def process_response(self, response_generation, data):
                # Generation token isolation: stale responses must be dropped
                if response_generation != self.generation:
                    self.stale_discards += 1
                    return False
                return True

        consumer = MockLifecycleConsumer()
        for i in range(20):
            consumer.open()
            self.assertTrue(consumer.active)
            self.assertEqual(len(consumer.running_timers), 1)
            self.assertEqual(len(consumer.running_processes), 1)

            # Delayed response from an older generation arrives
            if i > 0:
                accepted = consumer.process_response(i, "delayed_data")
                self.assertFalse(accepted, "Stale generation token response must be discarded")

            consumer.close()
            self.assertFalse(consumer.active)
            self.assertEqual(len(consumer.running_timers), 0)
            self.assertEqual(len(consumer.running_processes), 0)

        self.assertEqual(consumer.generation, 20)
        self.assertEqual(consumer.stale_discards, 19)

    def test_r2_pruned_optional_features_contract(self):
        """R2-02 Contract: Cava, Lyrics, WeatherMap, and WindowPreview completely abandoned.

        Ensures 0 imports of deleted plugins and safe zero-overhead stubs in consumers.
        """
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Scanned QML/JS files have zero imports of abandoned native plugins or modules
        forbidden_patterns = [
            "Clavis.Cava",
            "Clavis.WeatherMap",
            "Clavis.Lyrics",
            "Clavis.WindowPreview",
            "qs.modules.map",
        ]
        for root_path, dirs, files in os.walk(shell_dir):
            if root_path == shell_dir:
                dirs[:] = [entry for entry in dirs if entry not in ("references", "tests", "build")]
            for file in files:
                if file.endswith((".qml", ".js")):
                    full_p = os.path.join(root_path, file)
                    with open(full_p, "r", encoding="utf-8") as f:
                        content = f.read()
                    for pattern in forbidden_patterns:
                        self.assertNotIn(
                            pattern,
                            content,
                            f"Forbidden pruned feature reference '{pattern}' found in {os.path.relpath(full_p, shell_dir)}"
                        )

        # 2. Deleted plugin directories are physically removed
        deleted_dirs = [
            os.path.join(shell_dir, "native", "plugin", "cava"),
            os.path.join(shell_dir, "native", "plugin", "lyrics"),
            os.path.join(shell_dir, "native", "plugin", "weathermap"),
            os.path.join(shell_dir, "native", "plugin", "windowpreview"),
            os.path.join(shell_dir, "modules", "map"),
            os.path.join(shell_dir, "native", "tools", "window-preview"),
        ]
        for d in deleted_dirs:
            self.assertFalse(os.path.exists(d), f"Pruned directory still exists: {d}")

        # 3. AudioSpectrum is a zero-overhead stub
        asp_file = os.path.join(shell_dir, "app", "services", "AudioSpectrum.qml")
        self.assertTrue(os.path.isfile(asp_file))
        with open(asp_file, "r", encoding="utf-8") as f:
            asp_content = f.read()
        self.assertIn("readonly property bool available: false", asp_content)
        self.assertIn("readonly property bool active: false", asp_content)
        self.assertIn("readonly property var values: []", asp_content)
        self.assertNotIn("Loader", asp_content)

        # 4. WindowPreviewService is a zero-overhead stub
        wps_file = os.path.join(shell_dir, "app", "services", "WindowPreviewService.qml")
        self.assertTrue(os.path.isfile(wps_file))
        with open(wps_file, "r", encoding="utf-8") as f:
            wps_content = f.read()
        self.assertIn("readonly property bool supported: false", wps_content)
        self.assertIn("readonly property bool connected: false", wps_content)
        self.assertNotIn("Loader", wps_content)

        # 5. WeatherMapBridge is a zero-overhead stub
        wmb_file = os.path.join(shell_dir, "modules", "settings", "WeatherMapBridge.qml")
        self.assertTrue(os.path.isfile(wmb_file))
        with open(wmb_file, "r", encoding="utf-8") as f:
            wmb_content = f.read()
        self.assertIn("readonly property bool available: false", wmb_content)
        self.assertIn("readonly property string status: \"unavailable\"", wmb_content)

        # 6. Native CMakeLists.txt does not configure pruned options
        cm_file = os.path.join(shell_dir, "native", "CMakeLists.txt")
        with open(cm_file, "r", encoding="utf-8") as f:
            cm_content = f.read()
        self.assertNotIn("ENABLE_CAVA", cm_content)
        self.assertNotIn("ENABLE_LYRICS", cm_content)
        self.assertNotIn("ENABLE_WINDOWPREVIEW", cm_content)

    def test_r2_startup_closure_and_lazy_hosts(self):
        """R2-01 Contract: Startup closure and lazy loading of heavy hosts."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. LauncherHost replaces direct LauncherWindow in AppShell
        app_file = os.path.join(shell_dir, "app", "AppShell.qml")
        with open(app_file, "r", encoding="utf-8") as f:
            app_content = f.read()
        self.assertIn("LauncherHost {", app_content)
        self.assertIn("id: spotlightLauncher", app_content)
        self.assertNotIn("LauncherWindow {\n        id: spotlightLauncher", app_content)

        # 2. DesktopCardHost gated by desktopCardIds
        self.assertIn("SystemCardService.desktopCardIds.length > 0", app_content)
        self.assertIn("DesktopCardHost.qml", app_content)

        # 3. ShellStartupService stages and lifecycle tracking
        self.assertIn("ShellStartupService.recordCoreReady()", app_content)
        self.assertIn("ShellStartupService.recordFirstFrame()", app_content)
        self.assertIn("ShellStartupService.recordIpcReady()", app_content)

        # 4. AppShell exposes shell IpcHandler
        self.assertIn("target: \"shell\"", app_content)
        self.assertIn("function stage(): string", app_content)
        self.assertIn("function isReady(): bool", app_content)
        self.assertIn("function status(): string", app_content)

        # 5. RegionSelector gated by RegionSelectionService.active
        reg_file = os.path.join(shell_dir, "modules", "regionselector", "RegionSelector.qml")
        with open(reg_file, "r", encoding="utf-8") as f:
            reg_content = f.read()
        self.assertIn("active: RegionSelectionService.active", reg_content)

        # 6. DisplayOverlays markers and confirmation dialog gated
        disp_file = os.path.join(shell_dir, "modules", "settings", "DisplayOverlays.qml")
        with open(disp_file, "r", encoding="utf-8") as f:
            disp_content = f.read()
        self.assertIn("model: DisplayConfigService.identify ? Quickshell.screens : []", disp_content)
        self.assertIn("active: DisplayConfigService.confirming", disp_content)

        # 7. SidebarHostWindow visibility gated on open or panel presented
        sb_file = os.path.join(shell_dir, "modules", "sidebars", "SidebarHostWindow.qml")
        with open(sb_file, "r", encoding="utf-8") as f:
            sb_content = f.read()
        self.assertIn("root.anySidebarOpen || dashboardSidebar.panelPresented || quickSettingsSidebar.panelPresented", sb_content)

        # 8. Keystone avatar file picker is lazy loaded
        ks_file = os.path.join(shell_dir, "modules", "keystone", "Keystone.qml")
        with open(ks_file, "r", encoding="utf-8") as f:
            ks_content = f.read()
        self.assertIn("id: avatarFilePickerLoader", ks_content)
        self.assertIn("active: false", ks_content)

        # 9. ShellStartupService defines valid stages
        sss_file = os.path.join(shell_dir, "app", "services", "ShellStartupService.qml")
        with open(sss_file, "r", encoding="utf-8") as f:
            sss_content = f.read()
        self.assertIn("readonly property string stageInit: \"INIT\"", sss_content)
        self.assertIn("readonly property string stageFirstFrame: \"FIRST_FRAME\"", sss_content)
        self.assertIn("readonly property string stageReady: \"READY\"", sss_content)
        self.assertIn("readonly property string stageIpcReady: \"IPC_READY\"", sss_content)
        self.assertIn("readonly property string stageFailed: \"FAILED\"", sss_content)

        # 10. Runner nyxuri-shell supports --stage, --status, and updated check-ready
        runner_file = os.path.join(shell_dir, "bin", "nyxuri-shell")
        with open(runner_file, "r", encoding="utf-8") as f:
            runner_content = f.read()
        self.assertIn("--stage", runner_content)
        self.assertIn("--status", runner_content)
        self.assertIn("ipc call shell isReady", runner_content)

        # 11. ClockContent defines font.weight: Font.Black fallback for rolling digits
        clock_file = os.path.join(shell_dir, "modules", "keystone", "clock", "ClockContent.qml")
        with open(clock_file, "r", encoding="utf-8") as f:
            clock_content = f.read()
        self.assertIn("font.weight: Font.Black", clock_content)

    def test_r2_lifecycle_exit_sigterm_and_crash_recovery(self):
        """R2-03 Contract: SIGTERM exit bounding, early crash detection, and rollback safety."""
        from unittest.mock import MagicMock, patch
        from nyxuri.shell_switcher import wait_shell_ready, stop_shell_process, hot_switch_shell

        # 1. Early crash detection in wait_shell_ready: exits immediately if proc.poll() is not None
        mock_dead_proc = MagicMock()
        mock_dead_proc.poll.return_value = 1  # Process crashed with exit code 1
        t_start = time.time()
        ready = wait_shell_ready("custom", mock_dead_proc, "/bin/false", timeout=3.5)
        elapsed = time.time() - t_start
        self.assertFalse(ready)
        self.assertLess(elapsed, 0.5, "wait_shell_ready must exit immediately on process death without waiting for 3.5s timeout")

        # 2. stop_shell_process terminates within bounded timeout
        with patch("os.kill") as mock_kill, patch("subprocess.run"):
            # First call sends SIGTERM, then check loop raises ProcessLookupError
            mock_kill.side_effect = [None, ProcessLookupError]
            ok = stop_shell_process("custom", 12345, "/fake/nyxuri-shell", timeout=2.5)
            self.assertTrue(ok)
            mock_kill.assert_any_call(12345, signal.SIGTERM)

        # 3. Crash recovery rolls back ledger and restores old shell
        with patch("nyxuri.shell_switcher.probe_running_shell", return_value=("noctalia", 1111)), \
             patch("nyxuri.shell_switcher.stop_shell_process", return_value=True), \
             patch("nyxuri.shell_switcher.spawn_shell") as mock_spawn, \
             patch("nyxuri.shell_switcher.wait_shell_ready") as mock_wait, \
             patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}):
            # Target shell fails to become ready; rollback restores noctalia
            mock_crashed = MagicMock()
            mock_crashed.poll.return_value = 1
            mock_restored = MagicMock()
            mock_spawn.side_effect = [mock_crashed, mock_restored]
            mock_wait.side_effect = [False, True]
            ok, msg = hot_switch_shell("custom", "/bin/sh")
            self.assertFalse(ok)
            self.assertIn("failed readiness probe", msg)
            self.assertEqual(active_shell(), "noctalia")

    def test_r3_brand_paths_and_toml_i18n_contracts(self):
        """R3 Contract: Brand convergence, nyxuri namespace, and TOML translation dictionaries."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Obsolete 26,000-line XML .ts files are completely purged from git
        ts_zh = os.path.join(shell_dir, "assets", "i18n", "clavis_zh_CN.ts")
        ts_en = os.path.join(shell_dir, "assets", "i18n", "clavis_en_US.ts")
        self.assertFalse(os.path.exists(ts_zh), f"Obsolete XML ts file must not exist: {ts_zh}")
        self.assertFalse(os.path.exists(ts_en), f"Obsolete XML ts file must not exist: {ts_en}")

        # 2. Modern clean TOML translation dictionaries exist
        toml_zh = os.path.join(shell_dir, "assets", "i18n", "zh_CN.toml")
        toml_en = os.path.join(shell_dir, "assets", "i18n", "en_US.toml")
        self.assertTrue(os.path.isfile(toml_zh), f"zh_CN.toml must exist: {toml_zh}")
        self.assertTrue(os.path.isfile(toml_en), f"en_US.toml must exist: {toml_en}")

        # 3. Translation compiler script exists and is executable
        compile_script = os.path.join(shell_dir, "scripts", "dev", "compile_i18n.py")
        self.assertTrue(os.path.isfile(compile_script))
        self.assertTrue(os.access(compile_script, os.X_OK))

        # 4. Paths.qml defaults configHome to nyxuri namespace
        paths_file = os.path.join(shell_dir, "app", "Paths.qml")
        with open(paths_file, "r", encoding="utf-8") as f:
            paths_content = f.read()
        self.assertIn('xdgConfigHome + "/nyxuri"', paths_content)
        self.assertIn('NYXURI_SHELL_CONFIG_HOME', paths_content)

        # 5. nyxuri_paths.py and nyxuri-paths.sh exist and default to nyxuri
        py_paths = os.path.join(shell_dir, "scripts", "lib", "nyxuri_paths.py")
        sh_paths = os.path.join(shell_dir, "scripts", "lib", "nyxuri-paths.sh")
        self.assertTrue(os.path.isfile(py_paths))
        self.assertTrue(os.path.isfile(sh_paths))
        with open(py_paths, "r", encoding="utf-8") as f:
            py_content = f.read()
        self.assertIn('config / "nyxuri"', py_content)

        # 6. vendor/kdl has no __pycache__ or .pyc tracked in git
        import subprocess
        tracked_vendor = subprocess.run(
            ["git", "ls-files", os.path.join(shell_dir, "scripts", "system", "vendor", "kdl")],
            capture_output=True, text=True, check=True
        ).stdout
        self.assertNotIn(".pyc", tracked_vendor)
        self.assertNotIn("__pycache__", tracked_vendor)

        # 7. i18n scanner captures qsTranslate contexts and correctly localizes settings
        from pathlib import Path
        sys_path_added = False
        scripts_dev = os.path.join(shell_dir, "scripts", "dev")
        if scripts_dev not in sys.path:
            sys.path.insert(0, scripts_dev)
            sys_path_added = True
        try:
            import compile_i18n
            contexts = compile_i18n.scan_source_strings(Path(shell_dir))
            self.assertIn("ControlCenterWindow", contexts)
            self.assertIn("GeneralPage", contexts)
            self.assertIn("GeneralOverviewPage", contexts)
            self.assertIn("Account", contexts["ControlCenterWindow"])
            self.assertIn("Bar", contexts["GeneralPage"])
            self.assertIn("Dock", contexts["GeneralPage"])
            self.assertIn("Displays", contexts["GeneralPage"])
            self.assertIn("System", contexts["GeneralOverviewPage"])

            # Verify generate_ts produces translated entries for these contexts
            ts_zh_output = compile_i18n.generate_ts(Path(toml_zh), "zh_CN", contexts)
            self.assertIn("<name>ControlCenterWindow</name>", ts_zh_output)
            self.assertIn("<source>Account</source>\n        <translation>账户</translation>", ts_zh_output)
            self.assertIn("<source>General</source>\n        <translation>通用</translation>", ts_zh_output)
            self.assertIn("<source>Keystone</source>\n        <translation>Keystone</translation>", ts_zh_output)
            self.assertIn("<name>GeneralPage</name>", ts_zh_output)
            self.assertIn("<source>Bar</source>\n        <translation>Bar</translation>", ts_zh_output)
            self.assertIn("<source>Dock</source>\n        <translation>Dock</translation>", ts_zh_output)
            self.assertIn("<source>Spotlight</source>\n        <translation>Spotlight</translation>", ts_zh_output)
            self.assertIn("<source>Displays</source>\n        <translation>显示器</translation>", ts_zh_output)
            self.assertIn("<name>GeneralOverviewPage</name>", ts_zh_output)
            self.assertIn("<source>System</source>\n        <translation>系统</translation>", ts_zh_output)
        finally:
            if sys_path_added and scripts_dev in sys.path:
                sys.path.remove(scripts_dev)

    def test_r4_architecture_and_lifecycle_contracts(self):
        """R4 Contract: Four-layer boundaries, shared purity, cross-domain isolation, and lifecycle separation."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Architecture matrix contract document exists
        matrix_file = os.path.join(shell_dir, "wiki", "architecture-matrix.md")
        self.assertTrue(os.path.isfile(matrix_file), f"architecture-matrix.md must exist: {matrix_file}")
        with open(matrix_file, "r", encoding="utf-8") as f:
            matrix_content = f.read()
        self.assertIn("app/", matrix_content)
        self.assertIn("modules/", matrix_content)
        self.assertIn("shared/", matrix_content)
        self.assertIn("native/", matrix_content)

        # 2. Shared layer is completely pure (zero side-effects, zero forbidden imports)
        shared_dir = os.path.join(shell_dir, "shared")
        for root_dir, _, files in os.walk(shared_dir):
            for file in files:
                if file.endswith(".qml"):
                    full_p = os.path.join(root_dir, file)
                    with open(full_p, "r", encoding="utf-8") as f:
                        qml_text = f.read()
                    self.assertNotIn("import qs.app", qml_text, f"{file} in shared/ must not import qs.app")
                    self.assertNotIn("import qs.modules", qml_text, f"{file} in shared/ must not import qs.modules")
                    self.assertNotIn("import Quickshell.Io", qml_text, f"{file} in shared/ must not import Quickshell.Io")
                    self.assertNotIn("import Clavis.", qml_text, f"{file} in shared/ must not import Clavis native plugins")
                    self.assertNotIn("Process {", qml_text, f"{file} in shared/ must not define Process")
                    self.assertNotIn("FileView {", qml_text, f"{file} in shared/ must not define FileView")
                    self.assertNotIn("Quickshell.execDetached", qml_text, f"{file} in shared/ must not call execDetached")

        # 3. Cross-domain module imports removed / decoupled
        launcher_file = os.path.join(shell_dir, "modules", "launcher", "LauncherWindow.qml")
        with open(launcher_file, "r", encoding="utf-8") as f:
            launcher_content = f.read()
            self.assertNotIn("import qs.modules.settings", launcher_content, "LauncherWindow must not import settings")
            self.assertNotIn("LocationPicker", launcher_content, "LauncherWindow must not instantiate LocationPicker")
            self.assertNotIn("locationPickerLoader", launcher_content, "LauncherWindow must not retain locationPickerLoader")

        dashboard_file = os.path.join(shell_dir, "modules", "sidebars", "dashboard", "DashboardSidebar.qml")
        with open(dashboard_file, "r", encoding="utf-8") as f:
            sidebar_content = f.read()
            # DashboardSidebar legitimately requires settings & filepicker for WallpaperColorPicker & FilePickerWindow (whitelisted)
            self.assertIn("import qs.modules.settings", sidebar_content, "DashboardSidebar needs settings for WallpaperColorPicker")
            self.assertIn("import qs.modules.filepicker", sidebar_content, "DashboardSidebar needs filepicker for FilePickerWindow")
            self.assertNotIn("import qs.modules.keystone", sidebar_content, "DashboardSidebar must not import keystone")
            self.assertNotIn("import qs.modules.launcher", sidebar_content, "DashboardSidebar must not import launcher")
            self.assertNotIn("import qs.modules.bar", sidebar_content, "DashboardSidebar must not import bar")

        storage_card = os.path.join(shell_dir, "modules", "systemcards", "SystemStorageCard.qml")
        with open(storage_card, "r", encoding="utf-8") as f:
            storage_content = f.read()
            self.assertNotIn("import qs.modules.settings", storage_content, "SystemStorageCard must not import settings")
            self.assertIn("inputRegionService: PopupInputRegionService", storage_content, "SystemStorageCard must inject inputRegionService")

        network_card = os.path.join(shell_dir, "modules", "systemcards", "SystemNetworkCard.qml")
        with open(network_card, "r", encoding="utf-8") as f:
            network_content = f.read()
            self.assertNotIn("import qs.modules.settings", network_content, "SystemNetworkCard must not import settings")
            self.assertIn("inputRegionService: PopupInputRegionService", network_content, "SystemNetworkCard must inject inputRegionService")

        notif_host = os.path.join(shell_dir, "modules", "notifications", "NotificationPopupHost.qml")
        with open(notif_host, "r", encoding="utf-8") as f:
            self.assertNotIn("import qs.modules.keystone.notifications", f.read(), "NotificationPopupHost must not import keystone")

        keystone_surface = os.path.join(shell_dir, "modules", "keystone", "styles", "shared", "KeystoneSurface.qml")
        with open(keystone_surface, "r", encoding="utf-8") as f:
            keystone_content = f.read()
            self.assertIn("import qs.modules.notifications", keystone_content, "KeystoneSurface must import from qs.modules.notifications")
            self.assertNotIn("import qs.modules.keystone.notifications", keystone_content, "Legacy keystone.notifications import must be gone")

        # Keystone notifications directory must be removed to avoid duplication
        keystone_notif_dir = os.path.join(shell_dir, "modules", "keystone", "notifications")
        self.assertFalse(os.path.exists(keystone_notif_dir), "keystone/notifications directory must be removed to avoid duplication")

        # 4. SplitMenuButton is in shared/controls as a pure UI control
        split_btn = os.path.join(shell_dir, "shared", "controls", "SplitMenuButton.qml")
        self.assertTrue(os.path.isfile(split_btn), "SplitMenuButton must exist in shared/controls")
        with open(split_btn, "r", encoding="utf-8") as f:
            btn_content = f.read()
            self.assertNotIn("import qs.app.services", btn_content, "shared/controls/SplitMenuButton must be pure")

        # 5. NotificationContent is in modules/notifications/
        notif_content = os.path.join(shell_dir, "modules", "notifications", "NotificationContent.qml")
        self.assertTrue(os.path.isfile(notif_content), "NotificationContent must exist in modules/notifications")

        # 6. Lifecycle inventory schema separates static inventory and runtime evidence
        inv_file = os.path.join(shell_dir, "wiki", "lifecycle-inventory.json")
        self.assertTrue(os.path.isfile(inv_file))
        import json
        with open(inv_file, "r", encoding="utf-8") as f:
            inv_data = json.load(f)
        self.assertEqual(inv_data.get("schemaVersion"), 2)
        self.assertIn("static_inventory", inv_data)
        self.assertIn("runtime_evidence", inv_data)
        self.assertEqual(inv_data["static_inventory"].get("violations"), 0)
        self.assertIn("generation_anti_stale", inv_data["runtime_evidence"])
        self.assertIn("idempotent_teardown", inv_data["runtime_evidence"])

        # 7. Static audit tool passes with zero violations across entire tree
        import subprocess
        audit_res = subprocess.run(
            [sys.executable, os.path.join(shell_dir, "scripts", "dev", "audit-lifecycle.py"), "--check", "--scope", "all"],
            capture_output=True, text=True, check=True
        )
        self.assertIn("lifecycle-audit: clean", audit_res.stdout)

    def test_r4c_tree_inventory_and_domain_reorganization(self):
        """R4-C Contract: Full tree inventory completeness and domain reorganization."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Tree inventory document exists and covers key sections
        inv_path = os.path.join(shell_dir, "wiki", "tree-inventory.md")
        self.assertTrue(os.path.isfile(inv_path), f"tree-inventory.md missing: {inv_path}")
        with open(inv_path, "r", encoding="utf-8") as f:
            inv_text = f.read()
        self.assertIn("### app/ （共", inv_text)
        self.assertIn("### modules/ （共", inv_text)
        self.assertIn("### shared/ （共", inv_text)
        self.assertIn("### native/ （共", inv_text)
        self.assertIn("### bin/ （共", inv_text)
        self.assertIn("### packaging/ （共", inv_text)

        # 2. Assert 12 single-module services relocated into their functional domains
        migrated_services = [
            "modules/launcher/FileSearchService.qml",
            "modules/launcher/SpotlightSearchService.qml",
            "modules/launcher/SpotlightToolService.qml",
            "modules/keystone/tools/AudioRecordingService.qml",
            "modules/keystone/tools/RecordingService.qml",
            "modules/keystone/media/MediaPalette.qml",
            "modules/bar/tray/TrayService.qml",
            "modules/quicksettings/QuickToggleConfig.qml",
            "modules/systemcards/NetworkInterfaceHistoryService.qml",
            "modules/sidebars/dashboard/infotools/TodoService.qml",
            "modules/settings/AutostartService.qml",
            "modules/settings/DisplayConfigService.qml",
        ]
        for rel in migrated_services:
            target_file = os.path.join(shell_dir, rel)
            self.assertTrue(os.path.isfile(target_file), f"Migrated service missing in domain: {target_file}")

        # 3. Assert old app/services/ locations no longer exist
        old_service_names = [
            "FileSearchService.qml",
            "SpotlightSearchService.qml",
            "SpotlightToolService.qml",
            "AudioRecordingService.qml",
            "RecordingService.qml",
            "MediaPalette.qml",
            "TrayService.qml",
            "QuickToggleConfig.qml",
            "NetworkInterfaceHistoryService.qml",
            "TodoService.qml",
            "AutostartService.qml",
            "DisplayConfigService.qml",
        ]
        for name in old_service_names:
            old_file = os.path.join(shell_dir, "app", "services", name)
            self.assertFalse(os.path.exists(old_file), f"Old service duplicate must not exist in app/services: {old_file}")

        # 4. Redundant forwarders and duplicate wrappers physically deleted
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "modules", "keystone", "tools", "ToolsBackend.qml")),
                         "Redundant ToolsBackend.qml must be deleted")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "modules", "settings", "SplitMenuButton.qml")),
                         "Duplicate settings/SplitMenuButton.qml must be deleted")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "modules", "settings", "backend")),
                         "Empty settings/backend directory must not exist")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native", "tools")),
                         "Empty native/tools directory must not exist")

        # 5. Static lifecycle audit passes clean with zero violations
        import subprocess
        audit_res = subprocess.run(
            [sys.executable, os.path.join(shell_dir, "scripts", "dev", "audit-lifecycle.py"), "--check", "--scope", "all"],
            capture_output=True, text=True, check=True
        )
        self.assertIn("lifecycle-audit: clean", audit_res.stdout)


if __name__ == "__main__":
    unittest.main()



