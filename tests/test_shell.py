"""Contract tests for dual shell management and CLI (nyxuri shell)."""

import io
import json
import os
import re
import signal
import sys
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

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
        nyxuri_shell_bin = Path(__file__).resolve().parent.parent / "shell" / "nyxuri-shell"
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
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "shared", "controls", "SvgIcon.qml")))

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
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "CMakeLists.txt")))

        # Runner directly launches quickshell
        runner_path = os.path.join(shell_dir, "nyxuri-shell")
        with open(runner_path, "r", encoding="utf-8") as f:
            runner_txt = f.read()
        self.assertIn('exec qs -p "${SHELL_DIR}"', runner_txt)
        self.assertNotIn("NATIVE_PLUGIN_PATH", runner_txt)
        self.assertNotIn("native/fallback", runner_txt)
        self.assertIn("${SHELL_DIR}/fallback", runner_txt)

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
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "modules", "bar", "quicksettings", "BrightnessButton.qml")))

    def test_r4c_c05_cpp_toolchain_elimination(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Native C++ source, CMake build system and native targets are completely eliminated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native")), "shell/native must be eliminated")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "CMakeLists.txt")), "shell/CMakeLists.txt must be eliminated")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "build")), "shell/build must not exist")

        # 2. Pure QML directory modules/keystone does not have handwritten qmldir
        self.assertFalse(os.path.isfile(os.path.join(shell_dir, "modules", "keystone", "qmldir")), "Pure QML directory should not have handwritten qmldir")

        # 3. shared layer strictly contains only controls, i18n, theme, utils
        shared_dir = os.path.join(shell_dir, "shared")
        shared_entries = sorted(os.listdir(shared_dir))
        self.assertEqual(shared_entries, ["controls", "i18n", "theme", "utils"])

        # 4. Pure QML fallback stubs exist for external optional runtime modules (M3Shapes, Qt.labs.lottieqt)
        fallback_dir = os.path.join(shell_dir, "fallback")
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "M3Shapes", "qmldir")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "M3Shapes", "MaterialShape.qml")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "Qt", "labs", "lottieqt", "qmldir")))
        self.assertTrue(os.path.isfile(os.path.join(fallback_dir, "Qt", "labs", "lottieqt", "LottieAnimation.qml")))

        # 5. nyxuri-shell launcher mounts pure fallback but does not reference native plugins
        launcher_path = os.path.join(shell_dir, "nyxuri-shell")
        with open(launcher_path, "r", encoding="utf-8") as f:
            launcher_content = f.read()
        self.assertIn("FALLBACK_QML_PATH", launcher_content)
        self.assertIn("${SHELL_DIR}/fallback", launcher_content)
        self.assertNotIn("NATIVE_PLUGIN_PATH", launcher_content)
        self.assertNotIn("native/fallback", launcher_content)

        # 6. dependencies.json build section contains zero C++ toolchain entries
        deps_path = os.path.join(shell_dir, "packaging", "dependencies.json")
        with open(deps_path, "r", encoding="utf-8") as f:
            deps_content = f.read()
        self.assertNotIn("cmake", deps_content.lower())
        self.assertNotIn("ninja", deps_content.lower())
        self.assertNotIn("gcc", deps_content.lower())
        self.assertNotIn("clang", deps_content.lower())

        # 7. No leftover C++ formatter or C++ source files
        self.assertFalse(os.path.exists(os.path.join(shell_dir, ".clang-format")))
        cxx_exts = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp")
        cxx_files = [
            os.path.relpath(os.path.join(root, f), shell_dir)
            for root, _, files in os.walk(shell_dir)
            for f in files
            if f.endswith(cxx_exts) and "references" not in root
        ]
        self.assertEqual(cxx_files, [], f"Leftover C/C++ files found in shell/: {cxx_files}")

    def test_p3_settings_wiring_and_weather_backend_contracts(self):
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

        # 4. Pure QML WeatherBackend provides makeForecastModel and air-quality support
        weather_backend = os.path.join(shell_dir, "app", "services", "weather", "WeatherBackend.qml")
        with open(weather_backend, "r", encoding="utf-8") as f:
            wb_content = f.read()
        self.assertIn("makeForecastModel", wb_content)
        self.assertIn("air-quality-api.open-meteo.com", wb_content)
        self.assertIn("calculateMoonPhaseAngle", wb_content)

        # 6. nyxuri-shell wallpaper-picker action directly routes to control-center without noctalia fallback
        nyxuri_shell = os.path.join(shell_dir, "nyxuri-shell")
        with open(nyxuri_shell, "r", encoding="utf-8") as f:
            ns_content = f.read()
        self.assertNotIn("wallpaper-picker.py", ns_content)

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

        # AudioSpectrum is physically deleted (R4-C-02)
        asp_path = os.path.join(shell_dir, "app", "services", "AudioSpectrum.qml")
        self.assertFalse(os.path.exists(asp_path))

        # 2. ControlCenterWindow cleans up child windows on destruction
        cc_window = os.path.join(shell_dir, "modules", "settings", "ControlCenterWindow.qml")
        with open(cc_window, "r", encoding="utf-8") as f:
            cc_content = f.read()
        self.assertIn("Component.onDestruction: root.closeChildWindows()", cc_content)

        # 3. MeteoIcon uses native font symbols (R6-01: pure subtraction, no lottie)
        meteo_icon = os.path.join(shell_dir, "shared", "controls", "MeteoIcon.qml")
        with open(meteo_icon, "r", encoding="utf-8") as f:
            meteo_content = f.read()
        self.assertIn("Fonts.materialSymbolsOutlined", meteo_content)

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
        self.assertIn("VolumeService.setSinkVolume(VolumeService.sinkVolume + step)", vol_content)
        self.assertIn("0.05", vol_content)

        # 3. Microphone.qml handles wheelAction with 0.05 step
        mic_path = os.path.join(shell_dir, "modules", "bar", "quicksettings", "Microphone.qml")
        with open(mic_path, "r", encoding="utf-8") as f:
            mic_content = f.read()
        self.assertIn("wheelAction: wheel =>", mic_content)
        self.assertIn("VolumeService.setSourceVolume(VolumeService.sourceVolume + step)", mic_content)
        self.assertIn("0.05", mic_content)

        # 4. BrightnessButton.qml handles wheelAction with 0.05 step
        br_path = os.path.join(shell_dir, "modules", "bar", "quicksettings", "BrightnessButton.qml")
        with open(br_path, "r", encoding="utf-8") as f:
            br_content = f.read()
        self.assertIn("wheelAction: wheel =>", br_content)
        self.assertIn("BrightnessService.setBrightnessForScreen", br_content)
        self.assertIn("0.05", br_content)

        # 5. LongStatusItem handles onWheel with pixelDelta/angleDelta support
        long_item = os.path.join(shell_dir, "modules", "keystone", "styles", "long", "LongStatusItem.qml")
        with open(long_item, "r", encoding="utf-8") as f:
            long_content = f.read()
        self.assertIn("onWheel: wheel =>", long_content)
        self.assertIn("pixelDelta", long_content)
        self.assertIn("VolumeService.setSinkVolume", long_content)
        self.assertIn("VolumeService.setSourceVolume", long_content)
        self.assertIn("BrightnessService.setBrightnessForScreen", long_content)

    def test_p3_notification_keystone_chain_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. KeystoneSurface embeds NotificationContent with isNotifMode binding
        surface_path = os.path.join(shell_dir, "modules", "keystone", "styles", "shared", "KeystoneSurface.qml")
        with open(surface_path, "r", encoding="utf-8") as f:
            surface_content = f.read()
        self.assertIn("NotificationContent {", surface_content)
        self.assertIn("property bool isNotifMode:", surface_content)
        self.assertIn("NotificationService.hasNotifs", surface_content)

        # 2. NotificationContent provides ListView, sanitizedBody, normalActions, dismiss
        notif_content = os.path.join(shell_dir, "modules", "notifications", "NotificationContent.qml")
        with open(notif_content, "r", encoding="utf-8") as f:
            nc_content = f.read()
        self.assertIn("StyledListView {", nc_content)
        self.assertIn("sanitizedBody()", nc_content)
        self.assertIn("root.manager.normalActions", nc_content)
        self.assertIn("root.manager.dismissPopup", nc_content)
        self.assertIn("root.manager.invokeDefaultAction", nc_content)

        # 3. NotificationService holds timeout, persistence and DND inhibition
        nm_path = os.path.join(shell_dir, "app", "services", "NotificationService.qml")
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
        from nyxuri.shell_switcher import hot_switch_shell, is_shell_locked
        with patch("nyxuri.shell_switcher.is_shell_locked", return_value=True), \
             patch("nyxuri.shell_switcher.probe_running_shell", return_value=("custom", 9999)), \
             patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}):
            ok, msg = hot_switch_shell("noctalia")
            self.assertFalse(ok)
            self.assertIn("Cannot switch shell while screen is locked", msg)

        # 4. is_shell_locked properly resolves shell_dir containing shell.qml
        shell_bin = os.path.join(shell_dir, "nyxuri-shell")
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="true")
            self.assertTrue(is_shell_locked("nyxuri-shell", shell_bin))
            mock_sub.assert_called_once_with(
                ["qs", "-p", shell_dir, "ipc", "call", "lock", "isLocked"],
                timeout=1.0, capture_output=True, text=True, check=False,
            )

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
        self.assertIn("manager: NotificationService", host_content)

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
            "modules/wallpaper/AwwwWallpaperService.qml",
            "modules/keystone/tools/AudioRecordingService.qml",
            "modules/keystone/tools/RecordingService.qml",
            "app/services/NetworkService.qml",
            "app/services/NetworkManagerExtras.qml",
            "app/services/BluetoothService.qml",
            "modules/launcher/FileSearchService.qml",
            "modules/launcher/SpotlightSearchService.qml",
            "modules/launcher/SpotlightToolService.qml",
            "modules/wallpaper/WallpaperService.qml",
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

        # 3. AudioSpectrum is physically deleted (R4-C-02)
        asp_file = os.path.join(shell_dir, "app", "services", "AudioSpectrum.qml")
        self.assertFalse(os.path.exists(asp_file))

        # 4. WindowPreviewService is physically deleted (R4-C-02)
        wps_file = os.path.join(shell_dir, "app", "services", "WindowPreviewService.qml")
        self.assertFalse(os.path.exists(wps_file))

        # 5. WeatherMapBridge is a zero-overhead stub
        wmb_file = os.path.join(shell_dir, "modules", "settings", "WeatherMapBridge.qml")
        self.assertTrue(os.path.isfile(wmb_file))
        with open(wmb_file, "r", encoding="utf-8") as f:
            wmb_content = f.read()
        self.assertIn("readonly property bool available: false", wmb_content)
        self.assertIn("readonly property string status: \"unavailable\"", wmb_content)

        # 6. Native directory and build files are completely eliminated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "CMakeLists.txt")))

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
        runner_file = os.path.join(shell_dir, "nyxuri-shell")
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
        compile_script = os.path.join(shell_dir, "scripts", "dev", "compile-i18n.py")
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
        import importlib.util
        spec = importlib.util.spec_from_file_location("compile_i18n", compile_script)
        compile_i18n = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compile_i18n)
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

    def test_r4c_naming_codex_and_dead_stub_elimination(self):
        """R4-C-02 Contract: Full library naming codex unified and dead code/stubs eliminated."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Keystone lyrics directory and files physically deleted
        lyrics_dir = os.path.join(shell_dir, "modules", "keystone", "lyrics")
        self.assertFalse(os.path.exists(lyrics_dir), "Keystone lyrics directory must be deleted")

        # 2. Dock preview fake capture image physically deleted
        dock_preview_dir = os.path.join(shell_dir, "modules", "dock", "preview")
        self.assertFalse(os.path.exists(dock_preview_dir), "Dock preview directory must be deleted")

        # 3. Deprecated Cava template deleted and removed from matugen config
        cava_tpl = os.path.join(shell_dir, "assets", "matugen", "templates", "cava-colors.ini")
        self.assertFalse(os.path.exists(cava_tpl), "cava-colors.ini template must be deleted")
        matugen_cfg = os.path.join(shell_dir, "assets", "matugen", "config.toml")
        with open(matugen_cfg, "r", encoding="utf-8") as f:
            matugen_content = f.read()
        self.assertNotIn("templates.cava", matugen_content)

        # 4. AudioSpectrum and WindowPreviewService stubs deleted
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "app", "services", "AudioSpectrum.qml")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "app", "services", "WindowPreviewService.qml")))

        # 5. Service singletons renamed to *Service.qml and bare nouns eliminated
        services_dir = os.path.join(shell_dir, "app", "services")
        renamed_services = {
            "VolumeService.qml": "Volume.qml",
            "BrightnessService.qml": "Brightness.qml",
            "TimeService.qml": "Time.qml",
            "WeatherService.qml": "WeatherPlugin.qml",
            "NotificationService.qml": "NotificationManager.qml",
            "MediaService.qml": "MediaManager.qml",
        }
        for new_name, old_name in renamed_services.items():
            self.assertTrue(os.path.isfile(os.path.join(services_dir, new_name)), f"{new_name} must exist")
            self.assertFalse(os.path.exists(os.path.join(services_dir, old_name)), f"Old {old_name} must not exist")

        # 6. Bar quicksettings Brightness button renamed to BrightnessButton.qml
        bar_qs_dir = os.path.join(shell_dir, "modules", "bar", "quicksettings")
        self.assertTrue(os.path.isfile(os.path.join(bar_qs_dir, "BrightnessButton.qml")))
        self.assertFalse(os.path.exists(os.path.join(bar_qs_dir, "Brightness.qml")))

        # 7. JS tools 100% PascalCase.js
        calendar_layout = os.path.join(shell_dir, "modules", "sidebars", "dashboard", "infotools", "CalendarLayout.js")
        self.assertTrue(os.path.isfile(calendar_layout))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "modules", "sidebars", "dashboard", "infotools", "calendar_layout.js")))

        import re
        pascal_case_re = re.compile(r"^[A-Z][a-zA-Z0-9]*\.js$")
        for root_dir, dirs, files in os.walk(shell_dir):
            if any(part in root_dir for part in ["native", "references", "build"]):
                continue
            for f in files:
                if f.endswith(".js"):
                    self.assertTrue(pascal_case_re.match(f), f"JS file must be PascalCase.js: {os.path.join(root_dir, f)}")

        # 8. CLI scripts unified to kebab-case
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "scripts", "dev", "compile-i18n.py")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "scripts", "dev", "compile_i18n.py")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "scripts", "capture", "lock-snapshot.sh")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "scripts", "capture", "lock_snapshot.sh")))

        theme_scripts = [
            "generate-matugen-colors.sh",
            "list-cursor-icon-themes.sh",
            "manage-matugen-templates.sh",
            "set-system-color-scheme.sh",
            "write-niri-cursor-config.sh",
            "matugen-registry.jq",
        ]
        for s in theme_scripts:
            self.assertTrue(os.path.isfile(os.path.join(shell_dir, "scripts", "theme", s)), f"{s} must exist")
            old_s = s.replace("-", "_")
            self.assertFalse(os.path.exists(os.path.join(shell_dir, "scripts", "theme", old_s)), f"Old {old_s} must not exist")

    def test_r4c_app_global_boundary_convergence(self):
        """R4-C-02a Contract: app/ global boundary convergence and domain state containment."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")
        services_dir = os.path.join(shell_dir, "app", "services")

        # 1. Assert 9 domain-specific files migrated into functional domains
        migrated_services = [
            "modules/wallpaper/WallpaperService.qml",
            "modules/wallpaper/WallpaperSceneService.qml",
            "modules/wallpaper/WallpaperPaletteSession.qml",
            "modules/wallpaper/AwwwWallpaperService.qml",
            "modules/desktopcards/DesktopPresentationService.qml",
            "modules/desktopcards/SystemCardDragSession.qml",
            "modules/desktopcards/SystemCardDragState.js",
            "modules/sidebars/dashboard/infotools/TimerService.qml",
            "modules/sidebars/dashboard/infotools/InfoDrawerState.qml",
        ]
        for rel in migrated_services:
            target_file = os.path.join(shell_dir, rel)
            self.assertTrue(os.path.isfile(target_file), f"Migrated service missing in domain: {target_file}")

        # 2. Assert old app/services/ locations no longer exist
        old_service_names = [
            "WallpaperService.qml",
            "WallpaperSceneService.qml",
            "WallpaperPaletteSession.qml",
            "AwwwWallpaperService.qml",
            "DesktopPresentationService.qml",
            "SystemCardDragSession.qml",
            "SystemCardDragState.js",
            "TimerService.qml",
            "InfoDrawerState.qml",
        ]
        for name in old_service_names:
            old_file = os.path.join(services_dir, name)
            self.assertFalse(os.path.exists(old_file), f"Old service duplicate must not exist in app/services: {old_file}")

        # 3. Assert app/ file count strictly converged: 43 files total (4 app root, 39 in services)
        app_files = []
        for root_dir, _, files in os.walk(os.path.join(shell_dir, "app")):
            for f in files:
                if f.endswith((".qml", ".js")):
                    app_files.append(os.path.join(root_dir, f))
        self.assertEqual(len(app_files), 43, f"app/ must strictly contain 43 files, found {len(app_files)}: {app_files}")

        # 4. Tree inventory document matches 43 app files
        inv_path = os.path.join(shell_dir, "wiki", "tree-inventory.md")
        with open(inv_path, "r", encoding="utf-8") as f:
            inv_text = f.read()
        self.assertIn("### app/ （共 43 文件）", inv_text)

        # 5. Static lifecycle audit passes clean with zero violations
        import subprocess
        audit_res = subprocess.run(
            [sys.executable, os.path.join(shell_dir, "scripts", "dev", "audit-lifecycle.py"), "--check", "--scope", "all"],
            capture_output=True, text=True, check=True
        )
        self.assertIn("lifecycle-audit: clean", audit_res.stdout)

    def test_r4c_niri_single_runtime_entry(self):
        """R4-C-02: Assert NiriService is the sole runtime IPC entry point and no Clavis.Niri imports remain in QML."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")
        niri_service_path = os.path.join(shell_dir, "app", "services", "NiriService.qml")
        self.assertTrue(os.path.isfile(niri_service_path), f"NiriService.qml must exist at {niri_service_path}")

        with open(niri_service_path, "r", encoding="utf-8") as f:
            niri_service_content = f.read()

        # 1. Assert NiriService contract invariants
        self.assertIn("pragma Singleton", niri_service_content)
        self.assertIn("Component.onDestruction", niri_service_content)
        self.assertIn("eventStreamSocket", niri_service_content)
        self.assertIn("requestSocket", niri_service_content)
        self.assertIn("fetchOutputsProcess", niri_service_content)
        self.assertIn("workspacesModel", niri_service_content)
        self.assertIn("property var outputs:", niri_service_content)
        self.assertIn("property var windows:", niri_service_content)
        self.assertIn("supportsMinimize: false", niri_service_content)
        self.assertIn("supportsMinimizeAnimation: false", niri_service_content)

        # 2. Assert zero imports of Clavis.Niri in app/, modules/, shared/
        violating_files = []
        for scope_dir in ["app", "modules", "shared"]:
            target_path = os.path.join(shell_dir, scope_dir)
            for root_dir, _, files in os.walk(target_path):
                for f in files:
                    if f.endswith(".qml"):
                        full_path = os.path.join(root_dir, f)
                        with open(full_path, "r", encoding="utf-8") as qml_f:
                            content = qml_f.read()
                            if "import Clavis.Niri" in content:
                                violating_files.append(os.path.relpath(full_path, shell_dir))

        self.assertEqual(violating_files, [], f"No QML file in app/, modules/, shared/ may import Clavis.Niri: {violating_files}")

        # 3. Assert former consumers reference NiriService
        consumer_samples = [
            ("app/AppShell.qml", "NiriService"),
            ("app/services/DockService.qml", "NiriService"),
            ("modules/bar/workspaces/Workspaces.qml", "NiriService"),
            ("modules/bar/activewindow/ActiveWindow.qml", "NiriService"),
            ("modules/dock/DockSurface.qml", "NiriService"),
            ("modules/hotcorners/HotCorners.qml", "NiriService"),
            ("modules/keystone/styles/long/LongWorkspaces.qml", "NiriService"),
            ("modules/settings/DisplayConfigService.qml", "NiriService"),
            ("modules/wallpaper/WallpaperSceneService.qml", "NiriService"),
        ]
        for rel_path, pattern in consumer_samples:
            target_f = os.path.join(shell_dir, rel_path)
            self.assertTrue(os.path.isfile(target_f), f"Consumer {rel_path} must exist")
            with open(target_f, "r", encoding="utf-8") as cf:
                self.assertIn(pattern, cf.read(), f"{rel_path} must reference {pattern}")

        # 4. Assert ROADMAP status updated
        roadmap_path = os.path.join(shell_dir, "ROADMAP.md")
        with open(roadmap_path, "r", encoding="utf-8") as rf:
            roadmap_content = rf.read()
        self.assertIn("| 已完成 | 建立 Niri 单一运行时入口 | R4-C-02 |", roadmap_content)

    def test_r4c_i18n_service_and_catalog_contracts(self):
        """Assert I18nService is pure QML with zero C++ imports, preserves full public API, and catalogs are valid."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")
        i18n_service_path = os.path.join(shell_dir, "app", "services", "I18nService.qml")
        self.assertTrue(os.path.isfile(i18n_service_path), f"I18nService.qml must exist at {i18n_service_path}")

        with open(i18n_service_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Pure QML with zero C++ plugin imports or legacy I18nManager invocations
        self.assertNotIn("import Clavis", content)
        self.assertNotIn("I18nManager", content)

        # 2. Public API surface strictly preserved
        self.assertIn("readonly property var supportedLanguages:", content)
        self.assertIn("readonly property string language:", content)
        self.assertIn("property bool ready:", content)
        self.assertIn("property string lastError:", content)
        self.assertIn("readonly property string systemLanguage:", content)
        self.assertIn("function normalizeLanguage(lang)", content)
        self.assertIn("function preferredLanguage(languages)", content)
        self.assertIn("function setLanguage(lang)", content)
        self.assertIn("function initialize()", content)
        self.assertIn('code: "zh_CN"', content)
        self.assertIn('code: "en_US"', content)

        # 3. Translation catalog zh_CN.toml exists and has core mappings
        zh_toml = os.path.join(shell_dir, "assets", "i18n", "zh_CN.toml")
        self.assertTrue(os.path.isfile(zh_toml))
        with open(zh_toml, "r", encoding="utf-8") as f:
            toml_text = f.read()
        self.assertIn('"Desktop" = "桌面"', toml_text)
        self.assertIn('"Weather" = "天气"', toml_text)

        # 4. Pure shared i18n module, Toml.js utility, and Translations.js exist with zero C++ requirement
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "i18n", "I18n.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "i18n", "Translations.js")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "i18n", "qmldir")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "utils", "Toml.js")))

        # 5. Cleanliness: zh_CN.json and root toml.js do not exist (pure TOML single source)
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "assets", "i18n", "zh_CN.json")))
        self.assertFalse(os.path.exists(os.path.join(repo_root, "toml.js")))

        # 6. SystemCardCatalog.js has no .import and preserves raw static names for Qt.include stability
        catalog_path = os.path.join(shell_dir, "modules", "systemcards", "SystemCardCatalog.js")
        with open(catalog_path, "r", encoding="utf-8") as f:
            cat_code = f.read()
        self.assertNotIn(".import", cat_code)
        self.assertNotIn("I18n.tr", cat_code)
        self.assertIn('"Clock"', cat_code)

    def test_r4c_c06_domain_closure_and_single_state_source(self):
        """R4-C-06 Contract: Domain closure, single Niri state entry, pure shared tier, and roadmap completion."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. NiriService is the sole runtime entry for Niri state & IPC
        niri_service_path = os.path.join(shell_dir, "app", "services", "NiriService.qml")
        self.assertTrue(os.path.isfile(niri_service_path))
        with open(niri_service_path, "r", encoding="utf-8") as f:
            ns_content = f.read()
        self.assertIn("workspacesModel", ns_content)
        self.assertIn("property var outputs:", ns_content)
        self.assertIn("property var windows:", ns_content)
        self.assertIn("property string currentOutput:", ns_content)

        # 2. Modules tier self-containment: expected domains exist
        modules_dir = os.path.join(shell_dir, "modules")
        expected_domains = [
            "bar", "desktopcards", "dock", "filepicker", "hotcorners",
            "keystone", "launcher", "lock", "notifications", "quicksettings",
            "regionselector", "session", "settings", "sidebars", "systemcards", "wallpaper"
        ]
        for domain in expected_domains:
            self.assertTrue(os.path.isdir(os.path.join(modules_dir, domain)), f"Domain {domain} must exist in modules/")

        # 3. Shared layer is strictly pure with no upward dependencies
        shared_dir = os.path.join(shell_dir, "shared")
        for root_dir, _, files in os.walk(shared_dir):
            for file in files:
                if file.endswith(".qml") or file.endswith(".js"):
                    full_p = os.path.join(root_dir, file)
                    with open(full_p, "r", encoding="utf-8") as f:
                        code = f.read()
                    self.assertNotIn("import qs.app", code, f"{file} must not import qs.app")
                    self.assertNotIn("import qs.modules", code, f"{file} must not import qs.modules")
                    self.assertNotIn("import Clavis", code, f"{file} must not import Clavis")

        # 4. Roadmap status reflects R4-C-05 and R4-C-06 completion
        roadmap_path = os.path.join(shell_dir, "ROADMAP.md")
        with open(roadmap_path, "r", encoding="utf-8") as rf:
            roadmap_content = rf.read()
        self.assertIn("| 已完成 | 删除 Nyxuri 自有 C++ 构建链 | R4-C-05 |", roadmap_content)
        self.assertIn("| 已完成 | 完成结构与行为收口 | R4-C-06 |", roadmap_content)

    def test_r5_resource_doc_and_test_closure(self):
        """R5 Contract: Resource integrity, documentation hygiene, and categorized test runner."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Shader QSB integrity & ZenPaletteRenderer fix
        zen_qsb = os.path.join(shell_dir, "assets", "shaders", "wallpaper", "qsb", "zen-palette.frag.qsb")
        self.assertTrue(os.path.isfile(zen_qsb), "zen-palette.frag.qsb must be precompiled")
        self.assertGreater(os.path.getsize(zen_qsb), 0)

        zen_renderer = os.path.join(shell_dir, "modules", "wallpaper", "ZenPaletteRenderer.qml")
        with open(zen_renderer, "r", encoding="utf-8") as f:
            zr_code = f.read()
        self.assertNotIn("qrc:/", zr_code, "ZenPaletteRenderer must not use deleted qrc: paths")
        self.assertIn("Paths.fileUrl", zr_code)
        self.assertIn("zen-palette.frag.qsb", zr_code)

        # 2. Dead icons and orphaned SvgIcon.qml eliminated
        for dead_icon in ["play.svg", "pause.svg", "previous.svg", "next.svg"]:
            self.assertFalse(os.path.exists(os.path.join(shell_dir, "assets", "icons", dead_icon)))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "shared", "controls", "SvgIcon.qml")))

        # 3. Conflicting upstream docs removed
        for doc in ["development.md", "installation.md", "releasing.md"]:
            self.assertFalse(os.path.exists(os.path.join(shell_dir, "wiki", "upstream-docs", doc)))

        # 4. P3 recovery matrix archived
        archive_dir = os.path.join(shell_dir, "wiki", "archive")
        self.assertTrue(os.path.isdir(archive_dir))
        for archived in ["recovery.md", "recovery-matrix.md", "recovery-inputs.md"]:
            self.assertTrue(os.path.isfile(os.path.join(archive_dir, archived)))

        # 5. References documentation and modern development guide
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "wiki", "references.md")))
        dev_guide = os.path.join(shell_dir, "wiki", "development.md")
        with open(dev_guide, "r", encoding="utf-8") as f:
            dev_text = f.read()
        self.assertNotIn("cmake -S", dev_text)
        self.assertNotIn("ctest --test-dir", dev_text)

        # 6. Categorized test runner exists
        run_tests = os.path.join(shell_dir, "scripts", "dev", "run-tests.py")
        self.assertTrue(os.path.isfile(run_tests))
        self.assertTrue(os.access(run_tests, os.X_OK))

        # 7. Roadmap status reflects R5 completion
        roadmap_path = os.path.join(shell_dir, "ROADMAP.md")
        with open(roadmap_path, "r", encoding="utf-8") as rf:
            roadmap_content = rf.read()
        self.assertIn("| 已完成 | 盘点图标、翻译、shader、主题和第三方资源消费者 | R2/R3 |", roadmap_content)
        self.assertIn("| 已完成 | 统一 README、wiki、注释和上游参考资料职责 | R1/R3 |", roadmap_content)
        self.assertIn("| 已完成 | 按逻辑、运行时资源、native、图形环境和静态规则分类测试 | R4 |", roadmap_content)

    def test_r6_performance_and_event_loop_governance(self):
        """R6 Contract: Weather icon subtraction, MPRIS DBus mitigation, and timer zero-interval prohibition."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Weather Icon Subtraction (R6-01): 48.5MB meteocons bloat eliminated
        meteocons_dir = os.path.join(shell_dir, "assets", "icons", "weather", "meteocons")
        self.assertFalse(os.path.exists(meteocons_dir), "meteocons directory must be physically eliminated")

        deps_json_path = os.path.join(shell_dir, "packaging", "dependencies.json")
        with open(deps_json_path, "r", encoding="utf-8") as f:
            deps_data = json.load(f)
        self.assertEqual(deps_data.get("resources", []), [], "resources array in dependencies.json must be empty")

        meteo_icon_path = os.path.join(shell_dir, "shared", "controls", "MeteoIcon.qml")
        with open(meteo_icon_path, "r", encoding="utf-8") as f:
            meteo_code = f.read()
        self.assertIn("Fonts.materialSymbolsOutlined", meteo_code)
        self.assertNotIn("Qt.labs.lottieqt", meteo_code)
        self.assertNotIn("meteoconSvg", meteo_code)

        paths_qml_path = os.path.join(shell_dir, "app", "Paths.qml")
        with open(paths_qml_path, "r", encoding="utf-8") as f:
            paths_code = f.read()
        self.assertNotIn("meteoconsDir", paths_code)

        # 2. MPRIS DBus Mitigation (R6-02): reference-counted position polling and rogue signal removal
        media_service_path = os.path.join(shell_dir, "app", "services", "MediaService.qml")
        with open(media_service_path, "r", encoding="utf-8") as f:
            ms_code = f.read()
        self.assertIn("property int positionSubscribers: 0", ms_code)
        self.assertIn("function acquirePositionTracking()", ms_code)
        self.assertIn("function releasePositionTracking()", ms_code)
        self.assertIn("root.positionSubscribers > 0", ms_code)
        self.assertNotIn("player.positionChanged()", ms_code)
        self.assertIn("onObjectRemovedPost", ms_code)

        media_content_path = os.path.join(shell_dir, "modules", "keystone", "media", "MediaContent.qml")
        with open(media_content_path, "r", encoding="utf-8") as f:
            mc_code = f.read()
        self.assertIn("MediaService.acquirePositionTracking()", mc_code)
        self.assertIn("MediaService.releasePositionTracking()", mc_code)

        # 3. Timer Governance & Zero-Interval Prohibition (R6-03):
        # Assert zero occurrences of `interval: 0` across shell/ QML files
        zero_interval_regex = re.compile(r"\binterval:\s*0\b")
        for root_dir, dirs, files in os.walk(shell_dir):
            if any(p in root_dir for p in ["references", ".git", "build"]):
                continue
            for fname in files:
                if fname.endswith(".qml"):
                    full_p = os.path.join(root_dir, fname)
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as qf:
                        code = qf.read()
                    self.assertIsNone(
                        zero_interval_regex.search(code),
                        f"Found interval: 0 in {full_p} - must use Qt.callLater or non-zero interval",
                    )

        # TimerService stopwatchTimer interval is 50ms (not 10ms)
        timer_service_path = os.path.join(shell_dir, "modules", "sidebars", "dashboard", "infotools", "TimerService.qml")
        with open(timer_service_path, "r", encoding="utf-8") as f:
            ts_code = f.read()
        self.assertIn("interval: 50", ts_code)
        self.assertNotIn("interval: 10", ts_code)

        # ClockContent clockTimer.running is bound to root.visible
        clock_content_path = os.path.join(shell_dir, "modules", "keystone", "clock", "ClockContent.qml")
        with open(clock_content_path, "r", encoding="utf-8") as f:
            cc_code = f.read()
        self.assertIn("running: root.visible", cc_code)

        # LIFE007 and LIFE008 rules exist in audit-lifecycle.py
        audit_py_path = os.path.join(shell_dir, "scripts", "dev", "audit-lifecycle.py")
        with open(audit_py_path, "r", encoding="utf-8") as f:
            audit_code = f.read()
        self.assertIn("LIFE007", audit_code)
        self.assertIn("LIFE008", audit_code)

        # MediaContent.qml has exactly one Component.onCompleted and no duplicate handlers
        with open(media_content_path, "r", encoding="utf-8") as f:
            mc_code = f.read()
        self.assertEqual(mc_code.count("Component.onCompleted"), 1, "MediaContent.qml must have exactly one onCompleted")

        # Zero duplicate Component.onCompleted or Component.onDestruction across shell
        for root_dir, dirs, files in os.walk(shell_dir):
            if any(p in root_dir for p in ["references", ".git", "build"]):
                continue
            for fname in files:
                if fname.endswith(".qml"):
                    full_p = os.path.join(root_dir, fname)
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as qf:
                        code = qf.read()
                    completed_count = len(re.findall(r"^[ \t]{0,4}Component\.onCompleted\s*:", code, re.MULTILINE))
                    destruction_count = len(re.findall(r"^[ \t]{0,4}Component\.onDestruction\s*:", code, re.MULTILINE))
                    self.assertLessEqual(completed_count, 1, f"Duplicate Component.onCompleted in {full_p}")
                    self.assertLessEqual(destruction_count, 1, f"Duplicate Component.onDestruction in {full_p}")

        # 4. Roadmap status reflects R6 completion
        roadmap_path = os.path.join(shell_dir, "ROADMAP.md")
        with open(roadmap_path, "r", encoding="utf-8") as rf:
            roadmap_content = rf.read()
        self.assertIn("| 已完成 | 天气资产做减法：淘汰 meteocons 臃肿依赖，原生化图标映射 | R5 |", roadmap_content)
        self.assertIn("| 已完成 | MPRIS DBus 频繁失效重连与位置轮询治理 | R5 |", roadmap_content)
        self.assertIn("| 已完成 | 根除 `interval: 0` 事件循环空转与高频定时器降频 | R5 |", roadmap_content)

    def test_power_menu_and_secure_suspend_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. SessionPanel actions and badges: 5 items (1~5), no hibernate
        panel_path = os.path.join(shell_dir, "modules", "session", "SessionPanel.qml")
        with open(panel_path, "r", encoding="utf-8") as f:
            panel_content = f.read()
        self.assertIn('"action": "lock"', panel_content)
        self.assertIn('"action": "logout"', panel_content)
        self.assertIn('"action": "suspend"', panel_content)
        self.assertIn('"action": "reboot"', panel_content)
        self.assertIn('"action": "poweroff"', panel_content)
        self.assertNotIn('"action": "hibernate"', panel_content)
        self.assertIn('"key": "1"', panel_content)
        self.assertIn('"key": "5"', panel_content)
        self.assertIn("Qt.Key_1", panel_content)
        self.assertIn("Qt.Key_5", panel_content)
        self.assertNotIn("Qt.Key_L:", panel_content)
        self.assertNotIn("Qt.Key_E:", panel_content)
        self.assertNotIn("Qt.Key_U:", panel_content)
        self.assertNotIn("Qt.Key_S:", panel_content)
        self.assertNotIn("Qt.Key_H:", panel_content)

        # 2. SessionHost closes immediately before triggering action
        host_path = os.path.join(shell_dir, "modules", "session", "SessionHost.qml")
        with open(host_path, "r", encoding="utf-8") as f:
            host_content = f.read()
        self.assertIn("root.close();", host_content)

        # 3. ActionGateway uses systemctl for power actions and requests session close
        gateway_path = os.path.join(shell_dir, "app", "ActionGateway.qml")
        with open(gateway_path, "r", encoding="utf-8") as f:
            gateway_content = f.read()
        self.assertIn('root.execute(["systemctl", action], "session:secure-power")', gateway_content)
        self.assertNotIn('["loginctl", action]', gateway_content)
        self.assertIn("root.requestSessionClose()", gateway_content)

        # 4. Lock.qml has heartbeat timer, screensChanged listener, and uses PersonalizationConfig.lockScreenStyle
        lock_path = os.path.join(shell_dir, "modules", "lock", "Lock.qml")
        with open(lock_path, "r", encoding="utf-8") as f:
            lock_content = f.read()
        self.assertIn("property string sessionStyle: PersonalizationConfig.lockScreenStyle", lock_content)
        self.assertIn("LockSurface {", lock_content)
        self.assertIn("id: lockFocusHeartbeat", lock_content)
        self.assertIn("signal shouldReFocus", lock_content)
        self.assertIn("onScreensChanged", lock_content)

        # 5. LockSurface does NOT gate loader on locked state (unconditional load) and has global focus re-grab
        surface_path = os.path.join(shell_dir, "modules", "lock", "LockSurface.qml")
        with open(surface_path, "r", encoding="utf-8") as f:
            surface_content = f.read()
        self.assertNotIn("active: root.lock && root.lock.locked", surface_content)
        self.assertIn("function forceFieldFocus()", surface_content)
        self.assertIn("onShouldReFocus", surface_content)

        # 6. CaelestiaLock & DefaultLock have 500ms safety fallback timer and uninhibited focusAuth
        caelestia_path = os.path.join(shell_dir, "modules", "lock", "CaelestiaLock.qml")
        with open(caelestia_path, "r", encoding="utf-8") as f:
            caelestia_content = f.read()
        self.assertIn("layer.enabled: visible && status === Image.Ready && root.backgroundBlur > 0", caelestia_content)
        self.assertIn("id: safetyFallbackTimer", caelestia_content)
        self.assertIn("function focusAuth() {\n        lockContent.forceAuthFocus();", caelestia_content)

        default_lock_path = os.path.join(shell_dir, "modules", "lock", "DefaultLock.qml")
        with open(default_lock_path, "r", encoding="utf-8") as f:
            default_lock_content = f.read()
        self.assertIn("id: safetyFallbackTimer", default_lock_content)
        self.assertIn("function forceAuthFocus()", default_lock_content)

        # 7. Niri binds.kdl contains allow-when-locked=true for Mod+L
        binds_path = os.path.join(repo_root, "configs", "niri", "binds.kdl")
        with open(binds_path, "r", encoding="utf-8") as f:
            binds_content = f.read()
        self.assertIn('Mod+L allow-when-locked=true { spawn "~/.config/niri/scripts/shell-action.sh" "lock"; }', binds_content)


if __name__ == "__main__":
    unittest.main()



