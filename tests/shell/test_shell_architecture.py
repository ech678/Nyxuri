"""Shell ROADMAP milestone architecture contracts (P2..R11).

Split from the former TestShellManagement ledger: these tests assert the
milestone architecture frozen in shell/ROADMAP.md, not runtime switching.
"""


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

from nyxuri.kernel.ledger import active_shell, custom_shell_bin, set_shell
from nyxuri.cli import _cmd_shell
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import subprocess
from pathlib import Path





class TestShellManagement(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_p2_layer_structure_and_session_decoupling(self):
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Verify 4-layer directories exist
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "app")))
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "shared")))
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "units", "session")))

        # Verify ActionGateway and SessionHost exist
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "app", "ActionGateway.qml")))
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "units", "session", "SessionHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "units", "session", "SessionPanel.qml")))

        # Verify old PowerMenu directory and service are completely deleted
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Modules", "PowerMenu")))
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Services", "PowerMenuService.qml")))

    def test_action_gateway_command_arguments(self):
        import subprocess
        from pathlib import Path
        nyxuri_shell_bin = Path(__file__).resolve().parents[2] / "shell" / "nyxuri-shell"
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
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        settings_dir = os.path.join(repo_root, "shell", "units", "settings")

        # Verify units/settings exists and contains required host/backend
        self.assertTrue(os.path.isdir(settings_dir))
        self.assertTrue(os.path.isfile(os.path.join(settings_dir, "SettingsHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(settings_dir, "SettingsBackend.qml")))
        self.assertTrue(os.path.isfile(os.path.join(settings_dir, "ControlCenterWindow.qml")))

        # R10: the zero-consumer WeatherMapBridge stub is deleted
        self.assertFalse(os.path.exists(os.path.join(settings_dir, "WeatherMapBridge.qml")))

        # Verify old ControlCenter directory and ControlCenterService are deleted
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Modules", "ControlCenter")))
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Services", "ControlCenterService.qml")))

        # Verify no QML file under units/settings statically imports Clavis.WeatherMap (except backend/WeatherMapBackend.qml)
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
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Top-level clutter and legacy mother directories removed / relocated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, ".github")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, ".gitignore")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "docs")))
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "llms-wiki", "upstream", "clavis-docs")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "tools")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "core")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native", "tools", "window-preview")))
        # KM4.6: assets/ dissolved; third-party provenance lives in the LICENSE
        # third-party appendix (verbatim texts preserved).
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "assets")),
                         "shell/assets/ must stay dissolved (KM4.6)")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "licenses")))
        license_text = open(os.path.join(shell_dir, "LICENSE"), encoding="utf-8").read()
        self.assertIn("APPENDIX: THIRD-PARTY LICENSES AND PROVENANCE", license_text)
        self.assertIn("VERBATIM LICENSE TEXT: M3Shapes-Apache-2.0.txt", license_text)
        self.assertIn("VERBATIM LICENSE TEXT: ZenBrowser-MPL-2.0.txt", license_text)
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
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "assets", "matugen")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "app", "i18n")))
        self.assertTrue(os.path.isdir(os.path.join(shell_dir, "app", "templates")))
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
        self.assertNotIn("FALLBACK_QML_PATH", runner_txt)
        self.assertIn("${SHELL_DIR}/shared/controls/shapes", runner_txt)

        # 2. AppShell encapsulated in app/
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "AppShell.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "app", "AppShell.qml")))

        # 3. Capitalized Modules/ directory completely eliminated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "Modules")))

        # 4. Units unified under units/ in uniform lowercase with all functional code preserved
        # KM4.5: units/<domain>/ = manifest.toml + code (one domain, one directory).
        expected_units = [
            "bar", "desktopcards", "dock", "keystone", "launcher", "lock",
            "notifications", "regionselector", "session", "settings",
            "sidebars", "wallpaper"
        ]
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "units", "map")))
        # Support modules demolished at KM4.5: no fourth tree beside the units.
        for demolished in ("filepicker", "hotcorners", "quicksettings", "systemcards"):
            self.assertFalse(
                os.path.exists(os.path.join(shell_dir, "units", demolished)),
                f"Demolished support module must not exist under units/: {demolished}"
            )
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "modules")),
                         "shell/modules/ must be gone after KM4.5 (renamed to units/)")
        for mod in expected_units:
            self.assertTrue(
                os.path.isdir(os.path.join(shell_dir, "units", mod)),
                f"Expected unit directory missing: shell/units/{mod}"
            )
        for mod in expected_units:
            self.assertTrue(
                os.path.isfile(os.path.join(shell_dir, "units", mod, "manifest.toml")),
                f"Unit blueprint missing manifest.toml: shell/units/{mod}"
            )
        # Assert no PascalCase/uppercase directories anywhere in units/ (strictly all lowercase)
        for root_path, dirs, _ in os.walk(os.path.join(shell_dir, "units")):
            for entry in dirs:
                self.assertEqual(
                    entry, entry.lower(),
                    f"Non-lowercase directory found in units: {os.path.join(root_path, entry)}"
                )

        # 5. Zero occurrences of obsolete imports across all QML/JS files
        import re
        qs_mod_re = re.compile(r"import\s+qs\.units\.([A-Za-z0-9_.]+)")
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
                    self.assertNotIn("qs.modules.", content, f"Obsolete qs.modules. import found in {full_path} (KM4.5 renamed to qs.units.)")
                    for match in qs_mod_re.finditer(content):
                        mod_path = match.group(1)
                        for seg in mod_path.split("."):
                            self.assertEqual(
                                seg, seg.lower(),
                                f"Non-lowercase qs.units import '{mod_path}' found in {full_path}"
                            )

    def test_p3_appshell_host_assembly_and_wheel_contract(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Base hosts exist in units/
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "keystone", "Keystone.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "wallpaper", "WallpaperBackground.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "desktopcards", "DesktopCardHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "dock", "DockHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "regionselector", "RegionSelector.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "app", "services", "HotCorners.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "settings", "DisplayOverlays.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "sidebars", "SidebarHostWindow.qml")))

        # 2. NotificationContent and KeystoneSurface exist for native notification chain
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "keystone", "styles", "shared", "KeystoneSurface.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "notifications", "NotificationContent.qml")))

        # 3. Bar quicksettings controls exist
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "bar", "quickpanel", "Volume.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "bar", "quickpanel", "Microphone.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "bar", "quickpanel", "BrightnessButton.qml")))

    def test_r4c_c05_cpp_toolchain_elimination(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Native C++ source, CMake build system and native targets are completely eliminated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native")), "shell/native must be eliminated")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "CMakeLists.txt")), "shell/CMakeLists.txt must be eliminated")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "build")), "shell/build must not exist")

        # 2. Pure QML directories carry no handwritten qmldir — pragma Singleton
        #    resolves in qs synthetic pools (app/services precedent), so any
        #    surviving qmldir outside the named M3Shapes module is drift.
        self.assertFalse(os.path.isfile(os.path.join(shell_dir, "units", "keystone", "qmldir")), "Pure QML directory should not have handwritten qmldir")
        self.assertFalse(os.path.isfile(os.path.join(shell_dir, "units", "settings", "dashwindow", "qmldir")), "dashwindow qmldir is redundant; delete it")
        self.assertFalse(os.path.isfile(os.path.join(shell_dir, "units", "bar", "clock", "qmldir")), "bar/clock qmldir is redundant; delete it")

        # 3. shared layer strictly contains only cards, controls, i18n, theme, utils
        # (KM4.5: cards/ holds the pure presentational system cards)
        shared_dir = os.path.join(shell_dir, "shared")
        shared_entries = sorted(os.listdir(shared_dir))
        self.assertEqual(shared_entries, ["cards", "controls", "i18n", "theme", "utils"])

        # 4. KM4.6: fallback/ executed. The M3Shapes named-module shim (pure-QML
        # stand-in for the retired external plugin) lives beside the vendored
        # shape math in shared/controls/shapes; the dead lottieqt stub is gone.
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "fallback")),
                         "shell/fallback/ must stay executed (KM4.6)")
        shapes_dir = os.path.join(shell_dir, "shared", "controls", "shapes")
        self.assertTrue(os.path.isfile(os.path.join(shapes_dir, "M3Shapes", "qmldir")))
        self.assertTrue(os.path.isfile(os.path.join(shapes_dir, "M3Shapes", "MaterialShape.qml")))
        self.assertFalse(os.path.exists(os.path.join(shapes_dir, "Qt")),
                         "the dead lottieqt stub must not be resurrected")

        # 5. nyxuri-shell launcher mounts pure fallback but does not reference native plugins
        launcher_path = os.path.join(shell_dir, "nyxuri-shell")
        with open(launcher_path, "r", encoding="utf-8") as f:
            launcher_content = f.read()
        self.assertIn("SHAPES_QML_PATH", launcher_content)
        self.assertIn("${SHELL_DIR}/shared/controls/shapes", launcher_content)
        self.assertNotIn("NATIVE_PLUGIN_PATH", launcher_content)
        self.assertNotIn("native/fallback", launcher_content)

        # 6. KM4.6: the shell's standalone release/packaging pipeline is executed —
        # the shell ships via repo mode; gen-deps owns the repo-root packaging/ only.
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "packaging")),
                         "shell/packaging/ must stay executed (KM4.6)")

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
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. ActionGateway has settingsHost property and requestSettings* uses it
        gw_path = os.path.join(shell_dir, "app", "ActionGateway.qml")
        with open(gw_path, "r", encoding="utf-8") as f:
            gw_content = f.read()
        self.assertIn("property var settingsHost: null", gw_content)
        self.assertIn("root.settingsHost.toggle", gw_content)

        # 2. SettingsHost self-registers on the gateway (unit-model.md §6):
        # the host reference exists exactly while the unit is loaded, and
        # AppShell no longer wires it by id.
        sh_path = os.path.join(shell_dir, "units", "settings", "SettingsHost.qml")
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()
        self.assertIn("ActionGateway.settingsHost = root", sh_content)
        self.assertIn("ActionGateway.settingsHost = null", sh_content)
        app_path = os.path.join(shell_dir, "app", "AppShell.qml")
        with open(app_path, "r", encoding="utf-8") as f:
            app_content = f.read()
        self.assertNotIn("settingsHost =", app_content)
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
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Pruned Cava: AudioRecordingVisual provides local fallback levelProvider without Clavis.Cava
        arv_path = os.path.join(shell_dir, "units", "keystone", "styles", "recording", "AudioRecordingVisual.qml")
        with open(arv_path, "r", encoding="utf-8") as f:
            arv_content = f.read()
        self.assertNotIn("Clavis.Cava", arv_content)
        self.assertIn("id: levelProvider", arv_content)
        self.assertIn("readonly property bool available: false", arv_content)

        # AudioSpectrum is physically deleted (R4-C-02)
        asp_path = os.path.join(shell_dir, "app", "services", "AudioSpectrum.qml")
        self.assertFalse(os.path.exists(asp_path))

        # 2. ControlCenterWindow cleans up child windows on destruction
        cc_window = os.path.join(shell_dir, "units", "settings", "ControlCenterWindow.qml")
        with open(cc_window, "r", encoding="utf-8") as f:
            cc_content = f.read()
        self.assertIn("Component.onDestruction: root.closeChildWindows()", cc_content)

        # 3. MeteoIcon uses native font symbols (R6-01: pure subtraction, no lottie)
        meteo_icon = os.path.join(shell_dir, "shared", "controls", "MeteoIcon.qml")
        with open(meteo_icon, "r", encoding="utf-8") as f:
            meteo_content = f.read()
        self.assertIn("Fonts.materialSymbolsOutlined", meteo_content)

    def test_p3_bar_and_long_wheel_input_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. RippleButton exposes wheelAction and dispatches to onWheel
        rb_path = os.path.join(shell_dir, "shared", "controls", "RippleButton.qml")
        with open(rb_path, "r", encoding="utf-8") as f:
            rb_content = f.read()
        self.assertIn("property var wheelAction", rb_content)
        self.assertIn("root.wheelAction(wheel)", rb_content)

        # 2. Volume.qml handles wheelAction with 0.05 step
        vol_path = os.path.join(shell_dir, "units", "bar", "quickpanel", "Volume.qml")
        with open(vol_path, "r", encoding="utf-8") as f:
            vol_content = f.read()
        self.assertIn("wheelAction: wheel =>", vol_content)
        self.assertIn("VolumeService.setSinkVolume(VolumeService.sinkVolume + step)", vol_content)
        self.assertIn("0.05", vol_content)

        # 3. Microphone.qml handles wheelAction with 0.05 step
        mic_path = os.path.join(shell_dir, "units", "bar", "quickpanel", "Microphone.qml")
        with open(mic_path, "r", encoding="utf-8") as f:
            mic_content = f.read()
        self.assertIn("wheelAction: wheel =>", mic_content)
        self.assertIn("VolumeService.setSourceVolume(VolumeService.sourceVolume + step)", mic_content)
        self.assertIn("0.05", mic_content)

        # 4. BrightnessButton.qml handles wheelAction with 0.05 step
        br_path = os.path.join(shell_dir, "units", "bar", "quickpanel", "BrightnessButton.qml")
        with open(br_path, "r", encoding="utf-8") as f:
            br_content = f.read()
        self.assertIn("wheelAction: wheel =>", br_content)
        self.assertIn("BrightnessService.setBrightnessForScreen", br_content)
        self.assertIn("0.05", br_content)

        # 5. LongStatusItem handles onWheel with pixelDelta/angleDelta support
        long_item = os.path.join(shell_dir, "units", "keystone", "styles", "long", "LongStatusItem.qml")
        with open(long_item, "r", encoding="utf-8") as f:
            long_content = f.read()
        self.assertIn("onWheel: wheel =>", long_content)
        self.assertIn("pixelDelta", long_content)
        self.assertIn("VolumeService.setSinkVolume", long_content)
        self.assertIn("VolumeService.setSourceVolume", long_content)
        self.assertIn("BrightnessService.setBrightnessForScreen", long_content)

    def test_bar_layout_two_way_synchronization_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. PersonalizationConfig maintains bidirectional sync between 2-zone and 3-lane
        pc_path = os.path.join(shell_dir, "app", "services", "PersonalizationConfig.qml")
        with open(pc_path, "r", encoding="utf-8") as f:
            pc_content = f.read()

        self.assertIn('"information"', pc_content)
        self.assertIn("root.barLayoutLeft = root.normalizedBarLayoutIds(leading)", pc_content)
        self.assertIn("root.barLayoutRight = root.normalizedBarLayoutIds(trailing)", pc_content)
        self.assertIn("root.barLeadingComponents = nextLeft.slice()", pc_content)
        self.assertIn("root.barTrailingComponents = combinedTrailing", pc_content)
        self.assertIn("!root.arraysEqual(root.barLeadingComponents, root.barLayoutLeft)", pc_content)

        # 2. BarContent delegates 3 lanes to Repeaters with BarComponentLoader
        bc_path = os.path.join(shell_dir, "units", "bar", "BarContent.qml")
        with open(bc_path, "r", encoding="utf-8") as f:
            bc_content = f.read()
        self.assertIn("model: PersonalizationConfig.barLayoutLeft", bc_content)
        self.assertIn("model: PersonalizationConfig.barLayoutMiddle", bc_content)
        self.assertIn("model: PersonalizationConfig.barLayoutRight", bc_content)
        self.assertIn("delegate: BarComponentLoader {", bc_content)

    def test_p3_notification_keystone_chain_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. KeystoneSurface embeds NotificationContent with isNotifMode binding
        surface_path = os.path.join(shell_dir, "units", "keystone", "styles", "shared", "KeystoneSurface.qml")
        with open(surface_path, "r", encoding="utf-8") as f:
            surface_content = f.read()
        self.assertIn("NotificationContent {", surface_content)
        self.assertIn("property bool isNotifMode:", surface_content)
        self.assertIn("NotificationService.hasNotifs", surface_content)

        # 2. NotificationContent provides ListView, sanitizedBody, normalActions, dismiss
        notif_content = os.path.join(shell_dir, "units", "notifications", "NotificationContent.qml")
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
        hist_list = os.path.join(shell_dir, "units", "sidebars", "dashboard", "notifications", "NotificationList.qml")
        self.assertTrue(os.path.isfile(hist_list))

    def test_keystone_audio_osd_startup_suppression_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")
        surface_path = os.path.join(shell_dir, "units", "keystone", "styles", "shared", "KeystoneSurface.qml")
        with open(surface_path, "r", encoding="utf-8") as f:
            surface_content = f.read()

        # 1. State properties exist for baseline tracking
        self.assertIn("readonly property var sinkNode: Pipewire.defaultAudioSink", surface_content)
        self.assertIn("readonly property var sourceNode: Pipewire.defaultAudioSource", surface_content)
        self.assertIn("property bool sinkInitialized:", surface_content)
        self.assertIn("property bool sourceInitialized:", surface_content)

        # 2. Handlers guard against unready state and verify value delta before triggering OSD
        self.assertIn("function syncSinkState()", surface_content)
        self.assertIn("function handleSinkVolumeChanged()", surface_content)
        self.assertIn("function handleSinkMutedChanged()", surface_content)
        self.assertIn("function syncSourceState()", surface_content)
        self.assertIn("function handleSourceVolumeChanged()", surface_content)
        self.assertIn("function handleSourceMutedChanged()", surface_content)

        self.assertIn("!sinkNode || !sinkNode.ready || !audioNode", surface_content)
        self.assertIn("Math.abs(currentVol - lastSinkVolume) > 0.0001", surface_content)
        self.assertIn("currentMuted !== lastSinkMuted", surface_content)

        # 3. Component.onCompleted initializes baseline state
        self.assertIn("root.syncSinkState();", surface_content)
        self.assertIn("root.syncSourceState();", surface_content)

        # 4. Raw unshielded calls are replaced
        self.assertNotIn('function onVolumeChanged() {\n                        root.triggerSliderOSD("volume");', surface_content)
        self.assertNotIn('function onVolumeChanged() {\n                        root.triggerSliderOSD("mic");', surface_content)

    def test_p3_lock_screen_and_safety_switch_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Lock screen structure: Lock.qml, DefaultLockContent, CaelestiaLock, PAM config
        lock_path = os.path.join(shell_dir, "units", "lock", "Lock.qml")
        with open(lock_path, "r", encoding="utf-8") as f:
            lock_content = f.read()
        self.assertIn("WlSessionLock {", lock_content)
        self.assertIn("PreLockCapture {", lock_content)
        self.assertIn("function open()", lock_content)
        self.assertIn("function isLocked()", lock_content)
        self.assertIn("password.conf", lock_content)

        # 2. Lock cards exist
        cards_dir = os.path.join(shell_dir, "units", "lock", "cards")
        for card in ["NotificationCard.qml", "MediaCard.qml", "WeatherCard.qml", "SystemGrid.qml"]:
            self.assertTrue(os.path.isfile(os.path.join(cards_dir, card)), f"Lock card missing: {card}")

        # 3. Hot switch refuses to switch when screen is locked (K06 invariant)
        from nyxuri.desktop.shell_switcher import hot_switch_shell, is_shell_locked
        with patch("nyxuri.desktop.shell_switcher.is_shell_locked", return_value=True), \
             patch("nyxuri.desktop.shell_switcher.probe_running_shells", return_value=[("nyxuri-shell", 9999)]), \
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

    def test_p3_lock_screen_ime_free_password_and_recovery_contracts(self):
        """Lock screen password input bypasses the input method entirely, and a
        shell that died while locked is taken over again on restart."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")
        lock_dir = os.path.join(shell_dir, "units", "lock")

        # 1. The lock module must not instantiate text-input controls anywhere:
        # with QT_IM_MODULE=fcitx a focused TextInput lets fcitx5-qt raise a
        # parentless xdg_popup from the session-lock surface, which niri rejects
        # with a fatal protocol error (red dead-locker screen afterwards).
        lock_qml_files = glob.glob(os.path.join(lock_dir, "**", "*.qml"), recursive=True)
        self.assertTrue(lock_qml_files)
        for qml_path in lock_qml_files:
            with open(qml_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("TextInput {", content, f"IME-capable control in {qml_path}")
            self.assertNotIn("TextField {", content, f"IME-capable control in {qml_path}")
            self.assertNotIn("inputMethodHints", content, f"IME hints in {qml_path}")

        # 2. PasswordCapture accumulates key events without any text-input control.
        capture_path = os.path.join(lock_dir, "PasswordCapture.qml")
        self.assertTrue(os.path.isfile(capture_path))
        with open(capture_path, "r", encoding="utf-8") as f:
            capture_content = f.read()
        self.assertIn("FocusScope {", capture_content)
        self.assertIn("Keys.onPressed", capture_content)
        self.assertIn("currentText", capture_content)

        # 3. Both lock styles drive the shared capture component.
        with open(os.path.join(lock_dir, "DefaultLockContent.qml"), "r", encoding="utf-8") as f:
            default_content = f.read()
        with open(os.path.join(lock_dir, "cards", "AuthCard.qml"), "r", encoding="utf-8") as f:
            auth_content = f.read()
        self.assertIn("PasswordCapture {", default_content)
        self.assertIn("PasswordCapture {", auth_content)

        # 4. The dead legacy context is gone (its failure path lacked unlockFailed).
        self.assertFalse(os.path.isfile(os.path.join(lock_dir, "LockContext.qml")))

        # 5. Failure state clears as soon as the user types again.
        lock_path = os.path.join(lock_dir, "Lock.qml")
        with open(lock_path, "r", encoding="utf-8") as f:
            lock_content = f.read()
        self.assertIn("onCurrentTextChanged: showFailure = false", lock_content)

        # 6. Crash recovery: the lock writes a session-scoped marker and a fresh
        # instance takes the session lock over when the marker is fresh.
        self.assertIn('lockMarkerPath: Paths.runtimeHome + "/lock-active"', lock_content)
        self.assertIn("XDG_SESSION_ID", lock_content)
        self.assertIn("previousInstanceDiedLocked", lock_content)
        self.assertIn("sessionLock.locked = true", lock_content)
        self.assertIn("writeLockMarker()", lock_content)
        self.assertIn("clearLockMarker()", lock_content)
        self.assertIn("FileView {", lock_content)

    def test_p3_notification_fallback_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Standalone notification fallback host exists
        host_path = os.path.join(shell_dir, "units", "notifications", "NotificationPopupHost.qml")
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

        # 6. The popup:notification slot arbitrates keystone vs the standalone
        # popup host in the slot host (unit-model.md §6, host-owned rule) —
        # not a private config conditional in AppShell.
        slot_path = os.path.join(shell_dir, "app", "SlotHost.qml")
        with open(slot_path, "r", encoding="utf-8") as f:
            slot_content = f.read()
        self.assertIn('unit.id === "notifications"', slot_content)
        self.assertIn('StateProjection.isEnabled("keystone")', slot_content)

    def test_p3_r10_lifecycle_and_sideeffect_contracts(self):
        """P3-R10 lifecycle & side-effect governance contract checks."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        modules_dir = os.path.join(shell_dir, "units")
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
            "units/keystone/tools/AudioRecordingService.qml",
            "units/keystone/tools/RecordingService.qml",
            "app/services/NetworkService.qml",
            "app/services/NetworkManagerExtras.qml",
            "app/services/BluetoothService.qml",
            "units/launcher/FileSearchService.qml",
            "units/launcher/SpotlightSearchService.qml",
            "units/launcher/SpotlightToolService.qml",
            "units/wallpaper/WallpaperService.qml",
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
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Scanned QML/JS files have zero imports of abandoned native plugins or modules
        forbidden_patterns = [
            "Clavis.Cava",
            "Clavis.WeatherMap",
            "Clavis.Lyrics",
            "Clavis.WindowPreview",
            "qs.units.map",
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
            os.path.join(shell_dir, "units", "map"),
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

        # 5. WeatherMapBridge is physically deleted (R10): zero consumers, the
        # "not supported" stub answered no real call site
        wmb_file = os.path.join(shell_dir, "units", "settings", "WeatherMapBridge.qml")
        self.assertFalse(os.path.exists(wmb_file))

        # 6. Native directory and build files are completely eliminated
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "native")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "CMakeLists.txt")))

    def test_r2_startup_closure_and_lazy_hosts(self):
        """R2-01 Contract: Startup closure and lazy loading of heavy hosts.

        KM4: lazy loading is slot-driven — AppShell instantiates zero units
        by name; SlotHost owns one Loader per UnitCatalog row keyed by
        StateProjection (unit-model.md §6).
        """
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. AppShell is the microkernel host: no unit instantiated by name.
        app_file = os.path.join(shell_dir, "app", "AppShell.qml")
        with open(app_file, "r", encoding="utf-8") as f:
            app_content = f.read()
        for unit_component in ("LauncherHost {", "Lock {", "SessionHost {", "SettingsHost {",
                               "Keystone {", "RegionSelector {", "SidebarHostWindow {",
                               "WallpaperBackground {", "NotificationPopupHost {",
                               "DesktopCardHost {", "Bar {", "DockHost {"):
            self.assertNotIn(unit_component, app_content,
                             f"unit must not be instantiated by name in AppShell: {unit_component}")
        self.assertIn("SlotHost {", app_content)

        # 2. SlotHost: data-driven Loaders over the catalog, gated by the
        # ledger projection.
        slot_file = os.path.join(shell_dir, "app", "SlotHost.qml")
        with open(slot_file, "r", encoding="utf-8") as f:
            slot_content = f.read()
        self.assertIn("Repeater", slot_content)
        self.assertIn("Loader", slot_content)
        self.assertIn("StateProjection.isEnabled", slot_content)
        self.assertIn("UnitCatalog.units", slot_content)

        # 2b. DesktopCardHost gates its own windows on configured cards;
        # slot loading stays pure existence.
        dch_file = os.path.join(shell_dir, "units", "desktopcards", "DesktopCardHost.qml")
        with open(dch_file, "r", encoding="utf-8") as f:
            dch_content = f.read()
        self.assertIn("SystemCardService.desktopCardIds.length > 0", dch_content)

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
        reg_file = os.path.join(shell_dir, "units", "regionselector", "RegionSelector.qml")
        with open(reg_file, "r", encoding="utf-8") as f:
            reg_content = f.read()
        self.assertIn("active: RegionSelectionService.active", reg_content)

        # 6. DisplayOverlays markers and confirmation dialog gated
        disp_file = os.path.join(shell_dir, "units", "settings", "DisplayOverlays.qml")
        with open(disp_file, "r", encoding="utf-8") as f:
            disp_content = f.read()
        self.assertIn("model: DisplayConfigService.identify ? Quickshell.screens : []", disp_content)
        self.assertIn("active: DisplayConfigService.confirming", disp_content)

        # 7. SidebarHostWindow visibility gated on open or panel presented
        sb_file = os.path.join(shell_dir, "units", "sidebars", "SidebarHostWindow.qml")
        with open(sb_file, "r", encoding="utf-8") as f:
            sb_content = f.read()
        self.assertIn("root.anySidebarOpen || dashboardSidebar.panelPresented || quickSettingsSidebar.panelPresented", sb_content)

        # 8. Keystone avatar file picker is lazy loaded
        ks_file = os.path.join(shell_dir, "units", "keystone", "Keystone.qml")
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
        clock_file = os.path.join(shell_dir, "units", "keystone", "clock", "ClockContent.qml")
        with open(clock_file, "r", encoding="utf-8") as f:
            clock_content = f.read()
        self.assertIn("font.weight: Font.Black", clock_content)

    def test_r2_lifecycle_exit_sigterm_and_crash_recovery(self):
        """R2-03 Contract: SIGTERM exit bounding, early crash detection, and rollback safety."""
        from unittest.mock import MagicMock, patch
        from nyxuri.desktop.shell_switcher import wait_shell_ready, stop_shell_process, hot_switch_shell

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
        with patch("nyxuri.desktop.shell_switcher.probe_running_shells", return_value=[("noctalia", 1111)]), \
             patch("nyxuri.desktop.shell_switcher.stop_all_shell_instances", return_value=True), \
             patch("nyxuri.desktop.shell_switcher.stop_shell_process", return_value=True), \
             patch("nyxuri.desktop.shell_switcher.spawn_shell") as mock_spawn, \
             patch("nyxuri.desktop.shell_switcher.wait_shell_ready") as mock_wait, \
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
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Obsolete 26,000-line XML .ts files are completely purged from git
        ts_zh = os.path.join(shell_dir, "app", "i18n", "clavis_zh_CN.ts")
        ts_en = os.path.join(shell_dir, "app", "i18n", "clavis_en_US.ts")
        self.assertFalse(os.path.exists(ts_zh), f"Obsolete XML ts file must not exist: {ts_zh}")
        self.assertFalse(os.path.exists(ts_en), f"Obsolete XML ts file must not exist: {ts_en}")

        # 2. Modern clean TOML translation dictionaries exist
        toml_zh = os.path.join(shell_dir, "app", "i18n", "zh_CN.toml")
        toml_en = os.path.join(shell_dir, "app", "i18n", "en_US.toml")
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
        self.assertIn("Account", contexts["ControlCenterWindow"])
        self.assertIn("Bar", contexts["ControlCenterWindow"])
        self.assertIn("Dock", contexts["ControlCenterWindow"])
        self.assertIn("Displays", contexts["ControlCenterWindow"])

        # Verify generate_ts produces translated entries for these contexts
        ts_zh_output = compile_i18n.generate_ts(Path(toml_zh), "zh_CN", contexts)
        self.assertIn("<name>ControlCenterWindow</name>", ts_zh_output)
        self.assertIn("<source>Account</source>\n        <translation>账户</translation>", ts_zh_output)
        self.assertIn("<source>Keystone</source>\n        <translation>Keystone</translation>", ts_zh_output)
        self.assertIn("<source>Bar</source>\n        <translation>Bar</translation>", ts_zh_output)
        self.assertIn("<source>Dock</source>\n        <translation>Dock</translation>", ts_zh_output)
        self.assertIn("<source>Spotlight</source>\n        <translation>Spotlight</translation>", ts_zh_output)
        self.assertIn("<source>Displays</source>\n        <translation>显示器</translation>", ts_zh_output)

    def test_r4_architecture_and_lifecycle_contracts(self):
        """R4 Contract: Four-layer boundaries, shared purity, cross-domain isolation, and lifecycle separation."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Architecture matrix contract document exists
        matrix_file = os.path.join(repo_root, "llms-wiki", "shell", "architecture-matrix.md")
        self.assertTrue(os.path.isfile(matrix_file), f"architecture-matrix.md must exist: {matrix_file}")
        with open(matrix_file, "r", encoding="utf-8") as f:
            matrix_content = f.read()
        self.assertIn("app/", matrix_content)
        self.assertIn("units/", matrix_content)
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
        launcher_file = os.path.join(shell_dir, "units", "launcher", "LauncherWindow.qml")
        with open(launcher_file, "r", encoding="utf-8") as f:
            launcher_content = f.read()
            self.assertNotIn("import qs.units.settings", launcher_content, "LauncherWindow must not import settings")
            self.assertNotIn("LocationPicker", launcher_content, "LauncherWindow must not instantiate LocationPicker")
            self.assertNotIn("locationPickerLoader", launcher_content, "LauncherWindow must not retain locationPickerLoader")

        dashboard_file = os.path.join(shell_dir, "units", "sidebars", "dashboard", "DashboardSidebar.qml")
        with open(dashboard_file, "r", encoding="utf-8") as f:
            sidebar_content = f.read()
            # DashboardSidebar legitimately requires settings & the app services pool
            # for WallpaperColorPicker & FilePickerWindow (KM4.5: picker lives in app/services)
            self.assertIn("import qs.units.settings", sidebar_content, "DashboardSidebar needs settings for WallpaperColorPicker")
            self.assertIn("import qs.app.services", sidebar_content, "DashboardSidebar needs app services for FilePickerWindow")
            self.assertNotIn("import qs.units.keystone", sidebar_content, "DashboardSidebar must not import keystone")
            self.assertNotIn("import qs.units.launcher", sidebar_content, "DashboardSidebar must not import launcher")
            self.assertNotIn("import qs.units.bar", sidebar_content, "DashboardSidebar must not import bar")

        storage_card = os.path.join(shell_dir, "shared", "cards", "SystemStorageCard.qml")
        with open(storage_card, "r", encoding="utf-8") as f:
            storage_content = f.read()
            self.assertNotIn("import qs.units.settings", storage_content, "SystemStorageCard must not import settings")
            self.assertIn("inputRegionService: PopupInputRegionService", storage_content, "SystemStorageCard must inject inputRegionService")

        network_card = os.path.join(shell_dir, "shared", "cards", "SystemNetworkCard.qml")
        with open(network_card, "r", encoding="utf-8") as f:
            network_content = f.read()
            self.assertNotIn("import qs.units.settings", network_content, "SystemNetworkCard must not import settings")
            self.assertIn("inputRegionService: PopupInputRegionService", network_content, "SystemNetworkCard must inject inputRegionService")

        notif_host = os.path.join(shell_dir, "units", "notifications", "NotificationPopupHost.qml")
        with open(notif_host, "r", encoding="utf-8") as f:
            self.assertNotIn("import qs.units.keystone.notifications", f.read(), "NotificationPopupHost must not import keystone")

        keystone_surface = os.path.join(shell_dir, "units", "keystone", "styles", "shared", "KeystoneSurface.qml")
        with open(keystone_surface, "r", encoding="utf-8") as f:
            keystone_content = f.read()
            self.assertIn("import qs.units.notifications", keystone_content, "KeystoneSurface must import from qs.units.notifications")
            self.assertNotIn("import qs.units.keystone.notifications", keystone_content, "Legacy keystone.notifications import must be gone")

        # Keystone notifications directory must be removed to avoid duplication
        keystone_notif_dir = os.path.join(shell_dir, "units", "keystone", "notifications")
        self.assertFalse(os.path.exists(keystone_notif_dir), "keystone/notifications directory must be removed to avoid duplication")

        # 4. SplitMenuButton is in shared/controls as a pure UI control
        split_btn = os.path.join(shell_dir, "shared", "controls", "SplitMenuButton.qml")
        self.assertTrue(os.path.isfile(split_btn), "SplitMenuButton must exist in shared/controls")
        with open(split_btn, "r", encoding="utf-8") as f:
            btn_content = f.read()
            self.assertNotIn("import qs.app.services", btn_content, "shared/controls/SplitMenuButton must be pure")

        # 5. NotificationContent is in units/notifications/
        notif_content = os.path.join(shell_dir, "units", "notifications", "NotificationContent.qml")
        self.assertTrue(os.path.isfile(notif_content), "NotificationContent must exist in units/notifications")

        # 6. Static audit tool passes with zero violations across entire tree
        import subprocess
        audit_res = subprocess.run(
            [sys.executable, os.path.join(shell_dir, "scripts", "dev", "audit-lifecycle.py"), "--check", "--scope", "all"],
            capture_output=True, text=True, check=True
        )
        self.assertIn("lifecycle-audit: clean", audit_res.stdout)

    def test_r4c_domain_reorganization_contract(self):
        """R4-C Contract: Domain reorganization — services live in their functional domains."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. The hand-frozen tree-inventory snapshot is retired; the tree is answered by git + architecture-matrix.
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "wiki")), "shell/wiki must stay dissolved")
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "scripts", "dev", "generate-tree-inventory.py")))

        # 2. Assert 12 single-module services relocated into their functional domains
        migrated_services = [
            "units/launcher/FileSearchService.qml",
            "units/launcher/SpotlightSearchService.qml",
            "units/launcher/SpotlightToolService.qml",
            "units/keystone/tools/AudioRecordingService.qml",
            "units/keystone/tools/RecordingService.qml",
            "units/keystone/media/MediaPalette.qml",
            "units/bar/tray/TrayService.qml",
            "units/sidebars/quicksettings/QuickToggleConfig.qml",
            "units/sidebars/dashboard/infotools/TodoService.qml",
            "units/settings/AutostartService.qml",
            "units/settings/DisplayConfigService.qml",
        ]
        for rel in migrated_services:
            target_file = os.path.join(shell_dir, rel)
            self.assertTrue(os.path.isfile(target_file), f"Migrated service missing in domain: {target_file}")

        # KM4.5: systemcards demolished — its stateful network history singleton is a
        # genuine app-layer service and lives in app/services (not a duplicate).
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "app", "services", "NetworkInterfaceHistoryService.qml")),
                        "NetworkInterfaceHistoryService must live in app/services after KM4.5")

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
            "TodoService.qml",
            "AutostartService.qml",
            "DisplayConfigService.qml",
        ]
        for name in old_service_names:
            old_file = os.path.join(shell_dir, "app", "services", name)
            self.assertFalse(os.path.exists(old_file), f"Old service duplicate must not exist in app/services: {old_file}")

        # 4. Redundant forwarders and duplicate wrappers physically deleted
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "units", "keystone", "tools", "ToolsBackend.qml")),
                         "Redundant ToolsBackend.qml must be deleted")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "units", "settings", "SplitMenuButton.qml")),
                         "Duplicate settings/SplitMenuButton.qml must be deleted")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "units", "settings", "backend")),
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
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Keystone lyrics directory and files physically deleted
        lyrics_dir = os.path.join(shell_dir, "units", "keystone", "lyrics")
        self.assertFalse(os.path.exists(lyrics_dir), "Keystone lyrics directory must be deleted")

        # 2. Dock preview fake capture image physically deleted
        dock_preview_dir = os.path.join(shell_dir, "units", "dock", "preview")
        self.assertFalse(os.path.exists(dock_preview_dir), "Dock preview directory must be deleted")

        # 3. Deprecated Cava template stays deleted; the Tera asset tree is
        # fully replaced by the Noctalia-syntax builtin registry (P4).
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "assets", "matugen")),
                         "the retired matugen Tera asset tree must stay deleted")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "app", "templates", "cava-colors.ini")),
                         "cava-colors.ini template must stay deleted")
        with open(os.path.join(shell_dir, "app", "templates", "config.toml"), "r", encoding="utf-8") as f:
            registry_content = f.read()
        self.assertNotIn("cava", registry_content)
        self.assertNotIn("yazi", registry_content)

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
        bar_qs_dir = os.path.join(shell_dir, "units", "bar", "quickpanel")
        self.assertTrue(os.path.isfile(os.path.join(bar_qs_dir, "BrightnessButton.qml")))
        self.assertFalse(os.path.exists(os.path.join(bar_qs_dir, "Brightness.qml")))

        # 7. JS tools 100% PascalCase.js
        calendar_layout = os.path.join(shell_dir, "units", "sidebars", "dashboard", "infotools", "CalendarLayout.js")
        self.assertTrue(os.path.isfile(calendar_layout))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "units", "sidebars", "dashboard", "infotools", "calendar_layout.js")))

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
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "lock", "lock-snapshot.sh")))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "scripts", "capture", "lock_snapshot.sh")))

        theme_scripts = [
            "generate-matugen-colors.sh",
            "generate-matugen-previews.sh",
            "list-cursor-icon-themes.sh",
            "manage-matugen-templates.sh",
            "write-niri-cursor-config.sh",
            "matugen-registry.jq",
        ]
        for s in theme_scripts:
            self.assertTrue(os.path.isfile(os.path.join(shell_dir, "scripts", "theme", s)), f"{s} must exist")
            old_s = s.replace("-", "_")
            self.assertFalse(os.path.exists(os.path.join(shell_dir, "scripts", "theme", old_s)), f"Old {old_s} must not exist")
        # P4: the shell-side system writer is liquidated; nyxuri theme is the
        # single system-level writer.
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "scripts", "theme", "set-system-color-scheme.sh")))

    def test_r4c_app_global_boundary_convergence(self):
        """R4-C-02a Contract: app/ global boundary convergence and domain state containment."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")
        services_dir = os.path.join(shell_dir, "app", "services")

        # 1. Assert 9 domain-specific files migrated into functional domains
        migrated_services = [
            "units/wallpaper/WallpaperService.qml",
            "units/wallpaper/WallpaperSceneService.qml",
            "units/wallpaper/WallpaperPaletteSession.qml",
            "units/desktopcards/DesktopPresentationService.qml",
            "units/desktopcards/SystemCardDragSession.qml",
            "units/desktopcards/SystemCardDragState.js",
            "units/sidebars/dashboard/infotools/TimerService.qml",
            "units/sidebars/dashboard/infotools/InfoDrawerState.qml",
        ]
        for rel in migrated_services:
            target_file = os.path.join(shell_dir, rel)
            self.assertTrue(os.path.isfile(target_file), f"Migrated service missing in domain: {target_file}")
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "units", "wallpaper", "AwwwWallpaperService.qml")),
                         "AwwwWallpaperService.qml must be deleted")

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

        # 3. Assert app/ file count strictly converged: 56 files total
        # (7 app root + services/*; KM4 adds SlotHost/UnitCatalog/
        # StateProjection/UnitControlService/LogService — the microkernel
        # assembly, catalog, ledger projection, unit verb and log surfaces.
        # KM4.5 absorbs the demolished support modules' service-facing edge:
        # HotCorners, FilePickerWindow, SystemCardContent, SystemWeatherCard,
        # SystemBatteryTank, SystemClockCard, SidebarCookieClock,
        # NetworkInterfaceHistoryService)
        app_files = []
        for root_dir, _, files in os.walk(os.path.join(shell_dir, "app")):
            for f in files:
                if f.endswith((".qml", ".js")):
                    app_files.append(os.path.join(root_dir, f))
        self.assertEqual(len(app_files), 56, f"app/ must strictly contain 56 files, found {len(app_files)}: {app_files}")

        # 5. Static lifecycle audit passes clean with zero violations
        import subprocess
        audit_res = subprocess.run(
            [sys.executable, os.path.join(shell_dir, "scripts", "dev", "audit-lifecycle.py"), "--check", "--scope", "all"],
            capture_output=True, text=True, check=True
        )
        self.assertIn("lifecycle-audit: clean", audit_res.stdout)

    def test_r4c_niri_single_runtime_entry(self):
        """R4-C-02: Assert NiriService is the sole runtime IPC entry point and no Clavis.Niri imports remain in QML."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

        # 2. Assert zero imports of Clavis.Niri in app/, units/, shared/
        violating_files = []
        for scope_dir in ["app", "units", "shared"]:
            target_path = os.path.join(shell_dir, scope_dir)
            for root_dir, _, files in os.walk(target_path):
                for f in files:
                    if f.endswith(".qml"):
                        full_path = os.path.join(root_dir, f)
                        with open(full_path, "r", encoding="utf-8") as qml_f:
                            content = qml_f.read()
                            if "import Clavis.Niri" in content:
                                violating_files.append(os.path.relpath(full_path, shell_dir))

        self.assertEqual(violating_files, [], f"No QML file in app/, units/, shared/ may import Clavis.Niri: {violating_files}")

        # 3. Assert former consumers reference NiriService
        consumer_samples = [
            ("app/AppShell.qml", "NiriService"),
            ("app/services/DockService.qml", "NiriService"),
            ("units/bar/workspaces/Workspaces.qml", "NiriService"),
            ("units/bar/activewindow/ActiveWindow.qml", "NiriService"),
            ("units/dock/DockSurface.qml", "NiriService"),
            ("app/services/HotCorners.qml", "NiriService"),
            ("units/settings/DisplayConfigService.qml", "NiriService"),
            ("units/wallpaper/WallpaperSceneService.qml", "NiriService"),
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
        self.assertIn("| R4-C | 结构收敛与全面去 C++ | 已完成 |", roadmap_content)

    def test_r4c_i18n_service_and_catalog_contracts(self):
        """Assert I18nService is pure QML with zero C++ imports, preserves full public API, and catalogs are valid."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        zh_toml = os.path.join(shell_dir, "app", "i18n", "zh_CN.toml")
        self.assertTrue(os.path.isfile(zh_toml))
        with open(zh_toml, "r", encoding="utf-8") as f:
            toml_text = f.read()
        self.assertIn('"Desktop" = "桌面"', toml_text)
        self.assertIn('"Weather" = "天气"', toml_text)

        # 4. Pure shared i18n module, Toml.js utility, and Translations.js exist with zero C++ requirement
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "i18n", "I18n.qml")))
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "i18n", "Translations.js")))
        self.assertFalse(os.path.isfile(os.path.join(shell_dir, "shared", "i18n", "qmldir")),
                         "pragma Singleton resolves in qs synthetic pools; handwritten qmldir is redundant")
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "shared", "utils", "Toml.js")))

        # 5. Cleanliness: zh_CN.json and root toml.js do not exist (pure TOML single source)
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "app", "i18n", "zh_CN.json")))
        self.assertFalse(os.path.exists(os.path.join(repo_root, "toml.js")))

        # 6. SystemCardCatalog.js has no .import and preserves raw static names for Qt.include stability
        catalog_path = os.path.join(shell_dir, "shared", "cards", "SystemCardCatalog.js")
        with open(catalog_path, "r", encoding="utf-8") as f:
            cat_code = f.read()
        self.assertNotIn(".import", cat_code)
        self.assertNotIn("I18n.tr", cat_code)
        self.assertIn('"Clock"', cat_code)

    def test_r4c_c06_domain_closure_and_single_state_source(self):
        """R4-C-06 Contract: Domain closure, single Niri state entry, pure shared tier, and roadmap completion."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

        # 2. Units tier self-containment: expected domains exist (KM4.5: 12 units)
        units_dir = os.path.join(shell_dir, "units")
        expected_domains = [
            "bar", "desktopcards", "dock", "keystone", "launcher", "lock",
            "notifications", "regionselector", "session", "settings",
            "sidebars", "wallpaper"
        ]
        for domain in expected_domains:
            self.assertTrue(os.path.isdir(os.path.join(units_dir, domain)), f"Domain {domain} must exist in units/")

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
        self.assertIn("| R4-C | 结构收敛与全面去 C++ | 已完成 |", roadmap_content)
        self.assertIn("| R4 | 架构、生命周期与结构收敛 | 已完成 |", roadmap_content)

    def test_r5_resource_doc_and_test_closure(self):
        """R5 Contract: Resource integrity, documentation hygiene, and categorized test runner."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Shader QSB integrity & ZenPaletteRenderer fix
        zen_qsb = os.path.join(shell_dir, "units", "wallpaper", "shaders", "qsb", "zen-palette.frag.qsb")
        self.assertTrue(os.path.isfile(zen_qsb), "zen-palette.frag.qsb must be precompiled")
        self.assertGreater(os.path.getsize(zen_qsb), 0)

        zen_renderer = os.path.join(shell_dir, "units", "wallpaper", "ZenPaletteRenderer.qml")
        with open(zen_renderer, "r", encoding="utf-8") as f:
            zr_code = f.read()
        self.assertNotIn("qrc:/", zr_code, "ZenPaletteRenderer must not use deleted qrc: paths")
        # KM4.6: the precompiled qsb is unit-owned and loaded as a real file URL —
        # a unit-relative Qt.resolvedUrl resolves to file: just like Paths.fileUrl;
        # a bare relative string (compiler-dependent) would not.
        self.assertIn('Qt.resolvedUrl("shaders/qsb/zen-palette.frag.qsb")', zr_code)
        self.assertIn("zen-palette.frag.qsb", zr_code)

        # 2. Dead icons and orphaned SvgIcon.qml eliminated
        for dead_icon in ["play.svg", "pause.svg", "previous.svg", "next.svg"]:
            self.assertFalse(os.path.exists(os.path.join(shell_dir, "app", "icons", dead_icon)))
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "shared", "controls", "SvgIcon.qml")))

        # 3. Conflicting upstream docs removed
        for doc in ["development.md", "installation.md", "releasing.md"]:
            self.assertFalse(os.path.exists(os.path.join(repo_root, "llms-wiki", "upstream", "clavis-docs", doc)))

        # 4. P3 recovery matrix archived
        archive_dir = os.path.join(repo_root, "llms-wiki", "archive")
        self.assertTrue(os.path.isdir(archive_dir))
        for archived in ["recovery.md", "recovery-matrix.md", "recovery-inputs.md"]:
            self.assertTrue(os.path.isfile(os.path.join(archive_dir, archived)))

        # 5. References documentation and modern development guide
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "llms-wiki", "shell", "references.md")))
        dev_guide = os.path.join(repo_root, "llms-wiki", "shell", "development.md")
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
        self.assertIn("| R5 | 资源、文档与测试收口 | 已完成 |", roadmap_content)
        self.assertIn("| R7 | 多套设置 UI 与 PR #120 前置审查 | 已完成 |", roadmap_content)

    def test_r6_performance_and_event_loop_governance(self):
        """R6 Contract: Weather icon subtraction, MPRIS DBus mitigation, and timer zero-interval prohibition."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Weather Icon Subtraction (R6-01): 48.5MB meteocons bloat eliminated
        meteocons_dir = os.path.join(shell_dir, "app", "icons", "weather", "meteocons")
        self.assertFalse(os.path.exists(meteocons_dir), "meteocons directory must be physically eliminated")

        # KM4.6: packaging/ executed — meteocons subtraction contract is pinned by
        # the shared MeteoIcon implementation instead of a release manifest.
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "packaging", "dependencies.json")),
                         "packaging/dependencies.json must stay executed (KM4.6)")

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

        media_content_path = os.path.join(shell_dir, "units", "keystone", "media", "MediaContent.qml")
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
        timer_service_path = os.path.join(shell_dir, "units", "sidebars", "dashboard", "infotools", "TimerService.qml")
        with open(timer_service_path, "r", encoding="utf-8") as f:
            ts_code = f.read()
        self.assertIn("interval: 50", ts_code)
        self.assertNotIn("interval: 10", ts_code)

        # ClockContent clockTimer.running is bound to root.visible
        clock_content_path = os.path.join(shell_dir, "units", "keystone", "clock", "ClockContent.qml")
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
        self.assertIn("| R6 | 能耗基线、事件循环与稳态治理 | 已完成 |", roadmap_content)
        self.assertIn("| R8 | 设置导航扁平化与 M3 信息架构 | 已完成 |", roadmap_content)

    def test_r9_feature_toggles_and_real_lifecycle(self):
        """R9 Contract: Feature toggles control physical existence, layer-shell surfaces unmount, services guard lifecycles."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. Slot-driven existence: unit gates live in SlotHost keyed by the
        # ledger projection; AppShell holds no per-unit conditionals and no
        # private config switches (unit-model.md §6).
        app_path = os.path.join(shell_dir, "app", "AppShell.qml")
        with open(app_path, "r", encoding="utf-8") as f:
            app_code = f.read()
        self.assertIn("active: DisplayConfigService.identify || DisplayConfigService.confirming", app_code)
        self.assertNotIn("PersonalizationConfig.barEnabled", app_code)
        self.assertNotIn("DockService.enabled", app_code)
        self.assertNotIn("keystoneEnabled", app_code)
        slot_path = os.path.join(shell_dir, "app", "SlotHost.qml")
        with open(slot_path, "r", encoding="utf-8") as f:
            slot_code = f.read()
        self.assertIn("StateProjection.isEnabled(unit.id)", slot_code)
        self.assertIn("active: root.slotActive(modelData)", slot_code)

        # 2. Layer-shell surfaces physically unmount when disabled or inactive
        ov_path = os.path.join(shell_dir, "units", "wallpaper", "OverviewWallpaper.qml")
        with open(ov_path, "r", encoding="utf-8") as f:
            ov_code = f.read()
        self.assertIn("model: PersonalizationConfig.overviewEnabled ? Quickshell.screens : []", ov_code)

        dw_path = os.path.join(shell_dir, "units", "wallpaper", "DesktopWallpaper.qml")
        with open(dw_path, "r", encoding="utf-8") as f:
            dw_code = f.read()
        self.assertIn("model: Quickshell.screens", dw_code)
        self.assertNotIn("AwwwWallpaperService", dw_code)

        hc_path = os.path.join(shell_dir, "app", "services", "HotCorners.qml")
        with open(hc_path, "r", encoding="utf-8") as f:
            hc_code = f.read()
        # Whitespace-stripped: qmlformat may re-wrap long expressions.
        hc_compact = "".join(hc_code.split())
        self.assertIn('model:PersonalizationConfig.hotCornerIds.filter(id=>(PersonalizationConfig.hotCornerActions[id]||"disabled")!=="disabled")', hc_compact)

        rs_path = os.path.join(shell_dir, "units", "regionselector", "RegionSelector.qml")
        with open(rs_path, "r", encoding="utf-8") as f:
            rs_code = f.read()
        self.assertIn("model: RegionSelectionService.active ? Quickshell.screens : []", rs_code)

        # 3. DockService guards work and connections when disabled
        dock_path = os.path.join(shell_dir, "app", "services", "DockService.qml")
        with open(dock_path, "r", encoding="utf-8") as f:
            dock_code = f.read()
        self.assertIn("if (!root.enabled) {", dock_code)
        self.assertIn("entries.clear();", dock_code)
        self.assertIn("launchTimeout.stop();", dock_code)
        self.assertIn("target: root.enabled ? NiriService : null", dock_code)
        self.assertIn("target: root.enabled ? ApplicationService : null", dock_code)
        self.assertIn("target: root.enabled ? SpotlightAppUsage : null", dock_code)

        # 4. Service lifecycle teardown hooks
        ws_path = os.path.join(shell_dir, "units", "wallpaper", "WallpaperSceneService.qml")
        with open(ws_path, "r", encoding="utf-8") as f:
            ws_code = f.read()
        self.assertIn("function pruneScenes()", ws_code)
        self.assertIn("target: Quickshell", ws_code)
        self.assertIn("Component.onDestruction:", ws_code)

        disp_path = os.path.join(shell_dir, "units", "settings", "DisplayConfigService.qml")
        with open(disp_path, "r", encoding="utf-8") as f:
            disp_code = f.read()
        self.assertIn("function cancelPreview()", disp_code)
        self.assertIn("identifyTimer.stop();", disp_code)

        auto_path = os.path.join(shell_dir, "units", "settings", "AutostartService.qml")
        with open(auto_path, "r", encoding="utf-8") as f:
            auto_code = f.read()
        self.assertIn("property var deleteProcess: null", auto_code)
        self.assertIn("deleteProcess.running = false;", auto_code)

        sb_path = os.path.join(shell_dir, "units", "settings", "SettingsBackend.qml")
        with open(sb_path, "r", encoding="utf-8") as f:
            sb_code = f.read()
        self.assertIn("Component.onDestruction:", sb_code)
        self.assertIn("root.cancelSearch();", sb_code)

        # 5. Roadmap reflects R9 completion
        roadmap_path = os.path.join(shell_dir, "ROADMAP.md")
        with open(roadmap_path, "r", encoding="utf-8") as f:
            roadmap_code = f.read()
        self.assertIn("| R9 | 功能开关与真实生命周期 | 已完成 |", roadmap_code)

    def test_r10_action_gateway_and_module_autonomy(self):
        """R10 Contract: unified action boundary, domain autonomy, UI free of direct I/O.

        - ActionGateway is the sole execDetached site and documents result semantics
        - dead actionDispatched feedback signal removed
        - AppShell keeps assembly/cross-module wiring/public IPC, no domain business
        - LIFE008 registered: views carry no FileView/Process
        - theme IPC target closes the CLI->shell propagation loop
        - optional color picker degrades explicitly via its domain service
        - generated palettes live under nyxuri/ with legacy clavis read fallback
        """
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        def read(rel):
            with open(os.path.join(shell_dir, rel), "r", encoding="utf-8") as f:
                return f.read()

        # 1. ActionGateway: result semantics documented, dead signal removed,
        # argument shape validation in place.
        gw = read("app/ActionGateway.qml")
        self.assertNotIn("actionDispatched", gw)
        self.assertIn("dispatch accepted", gw)
        self.assertIn("Array.isArray(args)", gw)
        self.assertIn("pendingSecurePowerAction", gw)

        # 2. AppShell: microkernel assembly + generic IPC only. Unit-owned
        # targets (lock / spotlight / power-menu / control-center / settings)
        # moved into their unit roots; the kernel's unit-changed event lands
        # on the host's `unit` target. Gateway-owned search intents delegate
        # to ActionGateway.executeIntent.
        app = read("app/AppShell.qml")
        self.assertNotIn("pendingCycleAction", app)
        self.assertIn("WallpaperService.runCatalogAction(action.method)", app)
        self.assertIn("ActionGateway.executeIntent(action)", app)
        self.assertIn("ActionGateway.requestSidebarOpenOnScreen", app)
        self.assertNotIn('target: "lock"', app)
        self.assertNotIn('target: "spotlight"', app)
        self.assertNotIn('target: "power-menu"', app)
        self.assertNotIn('target: "control-center"', app)
        self.assertIn('target: "unit"', app)
        self.assertIn('target: "theme"', app)
        self.assertIn("ThemeService.setThemeMode(mode)", app)
        self.assertIn("ThemeService.toggleThemeMode()", app)
        self.assertIn("PersonalizationConfig.themeMode;", app)

        # 2b. Unit-owned IPC surfaces live in the unit roots.
        self.assertIn('target: "lock"', read("units/lock/Lock.qml"))
        self.assertIn('target: "spotlight"', read("units/launcher/LauncherHost.qml"))
        self.assertIn('target: "power-menu"', read("units/session/SessionHost.qml"))
        self.assertIn('target: "control-center"', read("units/settings/SettingsHost.qml"))

        # 3. WallpaperService owns its catalog action surface.
        self.assertIn("function runCatalogAction", read("units/wallpaper/WallpaperService.qml"))

        # 4. Theme truth closure: system scheme changes reach themeMode; the
        # generated palette lives in nyxuri/ with no legacy fallback.
        theme_svc = read("app/services/ThemeService.qml")
        self.assertIn("function toggleThemeMode", theme_svc)
        self.assertIn("onSystemThemeModeObserved", theme_svc)
        self.assertIn('"/nyxuri/colors.json"', theme_svc)
        self.assertNotIn("clavis", theme_svc)
        self.assertIn("--generated-home", theme_svc)
        self.assertNotIn("--templates", theme_svc)
        self.assertIn("systemThemeModeObserved", read("app/services/UiPreferences.qml"))
        template_svc = read("app/services/TemplateService.qml")
        self.assertIn('"/nyxuri/scheme-previews.json"', template_svc)
        self.assertNotIn("clavis", template_svc)
        self.assertIn('"/nyxuri/palette-modes.json"', template_svc)

        # The previews FileView left the page: UI files carry no file I/O.
        themes_page = read("units/settings/dashwindow/DashboardThemesPage.qml")
        self.assertNotIn("FileView", themes_page)
        self.assertNotIn("Quickshell.Io", themes_page)
        self.assertIn("TemplateService.schemePreviews", themes_page)

        # 5. The generation script assembles palettes from matugen --json;
        # the Tera render path is retired.
        previews_script = read("scripts/theme/generate-matugen-previews.sh")
        self.assertIn("$generated_home/nyxuri/scheme-previews.json", previews_script)
        self.assertNotIn("$generated_home/clavis/", previews_script)
        generator = read("scripts/theme/generate-matugen-colors.sh")
        self.assertIn("--json hex", generator)
        self.assertIn("palette-modes.json", generator)
        self.assertNotIn("templates.", generator)

        # 6. LIFE008 registered with allowlist; auditor stays green.
        audit_src = read("scripts/dev/audit-lifecycle.py")
        self.assertIn("LIFE008", audit_src)
        for allowlisted in ("units/lock/Lock.qml", "units/lock/PreLockCapture.qml",
                            "units/keystone/media/MediaPalette.qml"):
            self.assertIn(allowlisted, audit_src)

        # 7. Dock force-quit is a gateway action, not a popup-owned Process.
        popup = read("units/dock/DockPreviewPopup.qml")
        self.assertNotIn("Process {", popup)
        self.assertNotIn("property Process", popup)
        self.assertIn('"dock:force-quit"', popup)

        # 8. Color picker degrades explicitly through its domain service.
        tools = read("units/keystone/tools/ToolsContent.qml")
        self.assertNotIn("hyprpicker", tools)
        self.assertIn("ColorPickerService.launch()", tools)
        picker = read("units/keystone/tools/ColorPickerService.qml")
        self.assertIn('"keystone:color-picker"', picker)
        self.assertIn("hyprpicker is missing", picker)
        probe_script = os.path.join(shell_dir, "scripts", "theme", "probe-tool.sh")
        self.assertTrue(os.path.isfile(probe_script) and os.access(probe_script, os.X_OK),
                        "probe-tool.sh missing or not executable")

        # 9. The deleted map stub stays deleted.
        self.assertFalse(os.path.exists(os.path.join(shell_dir, "units", "settings", "WeatherMapBridge.qml")))

    def test_r11_shell_control_plane_and_transparency(self):
        """R11 Contract: on-demand shell control page, gated self sampling,
        allowlisted sanitized diagnostics.

        - the control plane is a real settings route, auto-listed in the nav
        - the page is a pure view: no FileView/Process/Timer of its own
        - sampling lives in the domain service behind a double gate
          (page mounted AND persisted opt-in switch, default off)
        - diagnostics are built by allowlist in pure JS, masked and truncated
        - IPC diagnostics() is a one-line delegation, no inline business
        """
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        def read(rel):
            with open(os.path.join(shell_dir, rel), "r", encoding="utf-8") as f:
                return f.read()

        # 1. Route registration: top-level entry, nav auto-derives from it.
        with open(os.path.join(shell_dir, "units", "settings", "settings-routes.json"),
                  "r", encoding="utf-8") as f:
            routes = json.load(f)
        shell_routes = [r for r in routes["routes"] if r["id"] == "shell"]
        self.assertEqual(len(shell_routes), 1)
        self.assertEqual(shell_routes[0]["path"], ["shell"])
        self.assertEqual(shell_routes[0]["source"], "ShellPage.qml")
        self.assertIn("control-plane", shell_routes[0]["aliases"])
        self.assertTrue(os.path.isfile(os.path.join(shell_dir, "units", "settings", "ShellPage.qml")))

        # 2. The page is a pure view: mounting arms the sampler, unmounting
        # disarms it; no I/O primitives in the view (LIFE008 spirit).
        page = read("units/settings/ShellPage.qml")
        self.assertIn("Component.onCompleted: ShellControlService.setPageMounted(true)", page)
        self.assertIn("Component.onDestruction: ShellControlService.setPageMounted(false)", page)
        self.assertNotIn("FileView", page)
        self.assertNotIn("Process {", page)
        self.assertNotIn("Quickshell.Io", page)
        self.assertNotIn("Timer {", page)

        # 3. The service owns the only sampler and the only export writer.
        service = read("units/settings/ShellControlService.qml")
        self.assertIn("import \"ShellDiagnostics.js\" as ShellDiagnostics", service)
        self.assertIn("import \"ShellSamplerMath.js\" as SamplerMath", service)
        self.assertIn("readonly property bool samplingActive: pageMounted && UiPreferences.controlPlaneResourceSampling",
                      service)
        self.assertIn("interval: root.sampleIntervalMs", service)
        self.assertIn('path: "/proc/self/status"', service)
        self.assertIn('path: "/proc/self/stat"', service)
        self.assertIn("atomicWrites: true", service)
        self.assertIn("Component.onDestruction:", service)
        # External command only through the argv-array Process, never a shell
        # string and never execDetached outside the gateway.
        self.assertIn('["mkdir", "-p", root.diagnosticsDir]', service)
        self.assertNotIn("execDetached", service)
        self.assertNotIn('"sh"', service)
        self.assertNotIn('"bash"', service)

        # 4. Sampling math and diagnostics sanitization are pure JS seams.
        sampler_math = read("units/settings/ShellSamplerMath.js")
        self.assertIn(".pragma library", sampler_math)
        self.assertNotIn("Quickshell", sampler_math)
        self.assertNotIn("XMLHttpRequest", sampler_math)
        diagnostics_js = read("units/settings/ShellDiagnostics.js")
        self.assertIn(".pragma library", diagnostics_js)
        self.assertNotIn("Quickshell", diagnostics_js)
        self.assertNotIn("XMLHttpRequest", diagnostics_js)
        self.assertIn("function sanitizeText(", diagnostics_js)
        self.assertIn("function maskHome(", diagnostics_js)
        self.assertIn('split(home).join("~")', diagnostics_js)
        self.assertIn("/home/", diagnostics_js)

        # 5. The opt-in switch is persisted and defaults to off.
        prefs = read("app/services/UiPreferences.qml")
        self.assertIn("property bool controlPlaneResourceSampling: false", prefs)
        self.assertIn("function setControlPlaneResourceSampling(", prefs)
        self.assertIn('"controlPlaneResourceSampling": root.controlPlaneResourceSampling', prefs)
        self.assertIn("root.controlPlaneResourceSampling = parsed.controlPlaneResourceSampling === true;",
                      prefs)

        # 6. Compositor reconnection is publicly visible and recoverable.
        niri = read("app/services/NiriService.qml")
        self.assertIn("readonly property bool reconnecting: reconnectTimer.running", niri)
        self.assertIn("function reconnect()", niri)

        # 7. IPC diagnostics() delegates; the AppShell stays a thin assembler.
        app = read("app/AppShell.qml")
        self.assertIn("function diagnostics(): string", app)
        self.assertIn("return ShellControlService.diagnosticsJson();", app)
        self.assertNotIn("JSON.stringify(ShellControlService.buildDiagnostics()", app)

        # 8. Dashboard-style routes land somewhere sensible.
        dashboard = read("units/settings/dashwindow/DashboardContent.qml")
        self.assertIn('"shell": "settings"', dashboard)

        # 9. The shipped search catalog carries the new route and sections.
        catalog = read("units/settings/generated/SearchCatalog.js")
        self.assertIn('"shell.section.modules"', catalog)
        self.assertIn('"shell.section.sampling"', catalog)
        self.assertIn('"shell.section.diagnostics"', catalog)

        # 10. Roadmap reflects the R11 delivery state.
        roadmap = read("ROADMAP.md")
        self.assertIn("| R11 | 控制面与透明度 | 已完成 |", roadmap)

    def test_power_menu_and_secure_suspend_contracts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. SessionPanel actions and badges: 5 items (1~5), no hibernate
        panel_path = os.path.join(shell_dir, "units", "session", "SessionPanel.qml")
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
        # Digit shortcuts are derived from the model length, never hard-coded.
        self.assertIn("Qt.Key_1", panel_content)
        self.assertNotIn("Qt.Key_5", panel_content)
        self.assertIn("shortcutIndex >= actionRepeater.count", panel_content)
        self.assertIn("if (selected)", panel_content)
        self.assertNotIn("Qt.Key_L:", panel_content)
        self.assertNotIn("Qt.Key_E:", panel_content)
        self.assertNotIn("Qt.Key_U:", panel_content)
        self.assertNotIn("Qt.Key_S:", panel_content)
        self.assertNotIn("Qt.Key_H:", panel_content)

        # 2. SessionHost closes immediately before triggering action
        host_path = os.path.join(shell_dir, "units", "session", "SessionHost.qml")
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
        # Pending secure power actions expire, so a lost secured() event can
        # never fire an unrelated suspend much later.
        self.assertIn("pendingSecurePowerTimer", gateway_content)
        self.assertIn("interval: 8000", gateway_content)
        self.assertIn("pendingSecurePowerTimer.restart()", gateway_content)
        self.assertIn("pendingSecurePowerTimer.stop()", gateway_content)

        # 3.5 Idle suspend goes through the secure lock pipeline, not a direct
        # loginctl call that would suspend without locking.
        idle_path = os.path.join(shell_dir, "app", "services", "IdleService.qml")
        with open(idle_path, "r", encoding="utf-8") as f:
            idle_content = f.read()
        self.assertNotIn("loginctl", idle_content)
        self.assertNotIn("suspendProcess", idle_content)
        self.assertIn("signal suspendRequested", idle_content)
        self.assertIn("function reportSuspendResult", idle_content)
        app_shell_path = os.path.join(shell_dir, "app", "AppShell.qml")
        with open(app_shell_path, "r", encoding="utf-8") as f:
            app_shell_content = f.read()
        self.assertIn("onSuspendRequested", app_shell_content)
        self.assertIn('ActionGateway.powerAction("suspend", "idle")', app_shell_content)

        # 4. Lock.qml has heartbeat timer, screensChanged listener, and uses PersonalizationConfig.lockScreenStyle
        lock_path = os.path.join(shell_dir, "units", "lock", "Lock.qml")
        with open(lock_path, "r", encoding="utf-8") as f:
            lock_content = f.read()
        self.assertIn("property string sessionStyle: PersonalizationConfig.lockScreenStyle", lock_content)
        self.assertIn("LockSurface {", lock_content)
        self.assertIn("id: lockFocusHeartbeat", lock_content)
        self.assertIn("signal shouldReFocus", lock_content)
        self.assertIn("onScreensChanged", lock_content)

        # 5. LockSurface does NOT gate loader on locked state (unconditional load) and has global focus re-grab
        surface_path = os.path.join(shell_dir, "units", "lock", "LockSurface.qml")
        with open(surface_path, "r", encoding="utf-8") as f:
            surface_content = f.read()
        self.assertNotIn("active: root.lock && root.lock.locked", surface_content)
        self.assertIn("function forceFieldFocus()", surface_content)
        self.assertIn("onShouldReFocus", surface_content)

        # 6. CaelestiaLock & DefaultLock have 500ms safety fallback timer and uninhibited focusAuth
        caelestia_path = os.path.join(shell_dir, "units", "lock", "CaelestiaLock.qml")
        with open(caelestia_path, "r", encoding="utf-8") as f:
            caelestia_content = f.read()
        self.assertIn("layer.enabled: visible && status === Image.Ready && root.backgroundBlur > 0", caelestia_content)
        self.assertIn("id: safetyFallbackTimer", caelestia_content)
        self.assertIn("function focusAuth() {\n        lockContent.forceAuthFocus();", caelestia_content)

        default_lock_path = os.path.join(shell_dir, "units", "lock", "DefaultLock.qml")
        with open(default_lock_path, "r", encoding="utf-8") as f:
            default_lock_content = f.read()
        self.assertIn("id: safetyFallbackTimer", default_lock_content)
        self.assertIn("function forceAuthFocus()", default_lock_content)

        # 7. Niri binds.kdl contains allow-when-locked=true for Mod+L
        binds_path = os.path.join(repo_root, "plugins", "niri", "binds.kdl")
        with open(binds_path, "r", encoding="utf-8") as f:
            binds_content = f.read()
        self.assertIn('Mod+L allow-when-locked=true { spawn "~/.config/niri/scripts/shell-action.sh" "lock"; }', binds_content)


