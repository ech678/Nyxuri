"""Regression tests for upstream defects fixed during the bug-hunt rounds.

Each test reproduces a concrete failure that shipped in v4.0.0-alpha.1 and
asserts the corrected behavior, so the defect cannot silently return.
"""

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class TestShellModuleImports(unittest.TestCase):

    def _shell(self):
        return Path(__file__).resolve().parents[2] / "shell"

    def test_files_declaring_desktop_action_import_quickshell(self):
        offenders = []
        for path in sorted(self._shell().rglob("*.qml")):
            source = path.read_text(encoding="utf-8")
            if "property DesktopAction" not in source:
                continue
            if not any(line.startswith("import Quickshell") for line in source.splitlines()):
                offenders.append(str(path.relative_to(self._shell())))
        self.assertEqual(offenders, [])

class TestDisabledOutputDetection(unittest.TestCase):

    def _service(self):
        return (Path(__file__).resolve().parents[2] / "shell" / "services"
                / "NiriService.qml")

    def test_enabled_state_is_derived_from_the_logical_output(self):
        source = self._service().read_text(encoding="utf-8")
        self.assertIn("enabled: !!out.logical,", source)
        self.assertNotIn("out.disabled", source)

class TestDockFolderMenuModelAccess(unittest.TestCase):

    def _shell(self):
        return Path(__file__).resolve().parents[2] / "shell"

    def test_list_view_reads_entries_through_the_folder_model_wrapper(self):
        menu = (self._shell() / "plugins" / "dock" / "DockFolderMenu.qml").read_text(
            encoding="utf-8")
        self.assertIn("root.contents.get(i)", menu)
        self.assertNotIn("root.contents.model.get(", menu)

    def test_the_wrapper_owns_the_model_alias_that_the_menu_must_not_index(self):
        model = (self._shell() / "plugins" / "dock" / "DockFolderModel.qml").read_text(
            encoding="utf-8")
        self.assertIn("function get(index)", model)
        self.assertIn("readonly property alias model: dirModel", model)
        for field in ("name:", "url:", "isDirectory:"):
            self.assertIn(field, model)

class TestFolderListModelRoleNames(unittest.TestCase):

    def _shell(self):
        return Path(__file__).resolve().parents[2] / "shell"

    def _source(self, relative):
        return (self._shell() / relative).read_text(encoding="utf-8")

    def test_the_wrapper_reads_the_role_the_plugin_exposes(self):
        source = self._source("plugins/dock/DockFolderModel.qml")
        self.assertIn('directory.get(index, "fileUrl")', source)
        self.assertNotIn("fileURL", source)
        self.assertNotIn("fileInfo", source)

    def test_the_fan_view_indexes_the_wrapper_instead_of_the_raw_model(self):
        fan = self._source("plugins/dock/DockFolderFan.qml")
        self.assertIn("model: root.count", fan)
        self.assertIn("required property int index", fan)
        self.assertIn("readonly property var fileInfo: root.model ? root.model.get(index) : ({})", fan)
        popup = self._source("plugins/dock/DockFilePopup.qml")
        self.assertIn("model: root.presented && directory.item ? directory.item : null", popup)

    def test_the_deployed_wrapper_returns_real_urls(self):
        runner = Path("/usr/lib/qt6/bin/qml")
        if not runner.exists():
            self.skipTest("qml runtime not available")
        probe = """import QtQuick
import qs.plugins.dock
Item {
    DockFolderModel { id: model; folder: "___FOLDER___" }
    Timer {
        interval: 100; running: true; repeat: true
        onTriggered: {
            if (!model.ready || model.count < 1)
                return;
            running = false;
            for (var i = 0; i < model.count; ++i)
                console.log("PROBE " + model.get(i).name + "=" + JSON.stringify(model.get(i).url));
            Qt.quit();
        }
    }
    Timer {
        interval: 20000; running: true
        onTriggered: Qt.quit()
    }
}
"""
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            shell = self._shell()
            (root / "dir" / "sub").mkdir(parents=True)
            (root / "dir" / "a.txt").write_text("x", encoding="utf-8")
            imports = root / "imports"
            (imports / "qs" / "app").mkdir(parents=True)
            (imports / "qs" / "services").mkdir(parents=True)
            (imports / "qs" / "plugins" / "dock").mkdir(parents=True)
            (imports / "qs" / "qmldir").write_text("module qs\n", encoding="utf-8")
            (imports / "qs" / "app" / "qmldir").write_text("module qs.app\n", encoding="utf-8")
            (imports / "qs" / "plugins" / "qmldir").write_text("module qs.plugins\n", encoding="utf-8")
            (imports / "qs" / "services" / "qmldir").write_text(
                "module qs.services\nsingleton DesktopFiles 1.0 DesktopFiles.qml\n", encoding="utf-8")
            (imports / "qs" / "plugins" / "dock" / "qmldir").write_text(
                "module qs.plugins.dock\nDockFolderModel 1.0 DockFolderModel.qml\n", encoding="utf-8")
            os.symlink(shell / "plugins" / "dock" / "DesktopFiles.qml",
                       imports / "qs" / "services" / "DesktopFiles.qml")
            os.symlink(shell / "plugins" / "dock" / "DockFolderModel.qml",
                       imports / "qs" / "plugins" / "dock" / "DockFolderModel.qml")
            script = root / "probe.qml"
            script.write_text(probe.replace("___FOLDER___", "file://" + str(root / "dir")), encoding="utf-8")
            result = subprocess.run([str(runner), str(script)], capture_output=True, text=True, timeout=120,
                                    cwd=str(root), env={**os.environ, "QT_QPA_PLATFORM": "offscreen",
                                                        "QT_FORCE_STDERR_LOGGING": "1",
                                                        "QML_IMPORT_PATH": str(imports),
                                                        "QML2_IMPORT_PATH": str(imports),
                                                        "LC_ALL": "C.UTF-8"})
        output = result.stdout + result.stderr
        self.assertRegex(output, r'PROBE a\.txt="file://[^"]+/dir/a\.txt"')
        self.assertRegex(output, r'PROBE sub="file://[^"]+/dir/sub"')

class TestDesktopCardHostStructure(unittest.TestCase):

    def _source(self):
        return (Path(__file__).resolve().parents[2] / "shell" / "plugins" / "desktopcards"
                / "DesktopCardHost.qml").read_text(encoding="utf-8")

    def test_no_property_change_signal_is_redeclared(self):
        source = self._source()
        declared = re.findall(r"^\s*property\s+[A-Za-z_][\w.]*\s+(\w+)\s*:", source, re.MULTILINE)
        self.assertTrue(declared)
        for name in sorted(set(declared)):
            self.assertNotIn("signal %sChanged" % name, source, name)

    def test_wallpaper_analyzer_is_not_a_variants_delegate_child(self):
        source = self._source()
        self.assertIn("property QtObject wallpaperAnalyzer", source)
        self.assertNotIn("id: wallpaperAnalyzer", source)

class TestTrayMenuScreenContract(unittest.TestCase):

    def test_tray_menu_does_not_shadow_the_window_screen(self):
        source = (Path(__file__).resolve().parents[2] / "shell" / "plugins" / "bar" / "tray"
                  / "TrayMenu.qml").read_text(encoding="utf-8")
        self.assertNotIn("property var screen", source)
        self.assertIn("screen: root.screen", source)

class TestShellPageSingletonImports(unittest.TestCase):

    def _page(self):
        return (Path(__file__).resolve().parents[2] / "shell" / "plugins" / "settings"
                / "ShellPage.qml").read_text(encoding="utf-8")

    def test_the_control_page_imports_the_singletons_it_binds_to(self):
        source = self._page()
        self.assertIn("Paths.configHome", source)
        self.assertIn("Paths.fileUrl", source)
        self.assertIn("ColorPickerService.probeFinished", source)
        imports = [line.strip() for line in source.splitlines() if line.startswith("import ")]
        self.assertIn("import qs.app", imports)
        self.assertIn("import qs.plugins.keystone.tools", imports)

class TestQmlSingletonImports(unittest.TestCase):
    """Every QML file must import the module that declares a singleton it reads.

    QML resolves identifiers against the importing file's own scope, so a
    singleton from another module is invisible unless that module is imported.
    The read silently yields a ReferenceError at runtime instead of a load
    failure, which is how three pages shipped with blank rows and dead buttons.
    """

    def _shell(self):
        return Path(__file__).resolve().parents[2] / "shell"

    def _singletons(self, shell):
        found = {}
        for path in shell.rglob("*.qml"):
            relative = path.relative_to(shell)
            if "references" in relative.parts or "archive" in relative.parts:
                continue  # gitignored upstream snapshots / frozen history, not shipped QML
            head = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:4]
            if not any("pragma Singleton" in line for line in head):
                continue
            module = "qs" if len(relative.parts) == 1 else "qs." + ".".join(relative.parts[:-1])
            found[path.stem] = (module, relative.parent)
        return found

    def test_files_read_singletons_only_from_modules_they_import(self):
        shell = self._shell()
        singletons = self._singletons(shell)
        self.assertGreater(len(singletons), 50)
        offenders = []
        for path in sorted(shell.rglob("*.qml")):
            relative = path.relative_to(shell)
            if "references" in relative.parts or "archive" in relative.parts:
                continue  # gitignored upstream snapshots / frozen history, not shipped QML
            source = path.read_text(encoding="utf-8", errors="ignore")
            code = "\n".join(line.split("//", 1)[0] for line in source.splitlines())
            imports = set(re.findall(r"^import\s+([\w.]+)", source, re.M))
            for name in sorted(set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\.", code))):
                entry = singletons.get(name)
                if entry is None:
                    continue
                module, parent = entry
                if parent == relative.parent:
                    continue
                if any(module == i or module.startswith(i + ".") or i.startswith(module + ".")
                       for i in imports):
                    continue
                offenders.append("%s reads %s from %s" % (relative, name, module))
        self.assertEqual(offenders, [])

class TestLockMarkerDirectory(unittest.TestCase):

    def test_lock_creates_the_runtime_directory_before_writing_the_marker(self):
        lock = Path(__file__).resolve().parents[2] / "shell" / "plugins" / "lock" / "Lock.qml"
        source = lock.read_text(encoding="utf-8")
        self.assertIn('command: ["mkdir", "-p", Paths.runtimeHome]', source)
        self.assertIn('path: root.markerReady ? root.lockMarkerPath : ""', source)
        self.assertIn("onLoaded: root.restoreLockAfterCrash()", source)
