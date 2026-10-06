"""Behavior checks for the source launcher, tooling scope and presentation owners."""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import unittest

from tests.utils import TempEnv

SHELL = Path(__file__).resolve().parents[1] / "shell"


class ShellLauncherTests(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.root = self.ctx.home / "source tree"
        self.shell = self.root / "shell"
        self.shell.mkdir(parents=True)
        self.runner = self.shell / "nyxuri-shell"
        shutil.copy2(SHELL / "nyxuri-shell", self.runner)
        bin_dir = self.ctx.home / "bin"
        bin_dir.mkdir()
        qs = bin_dir / "qs"
        qs.write_text(
            "#!/usr/bin/env python3\nimport json, os, sys\n"
            "print(json.dumps({'argv': sys.argv[1:], "
            "'qml': os.getenv('QML_IMPORT_PATH', ''), "
            "'qml2': os.getenv('QML2_IMPORT_PATH', '')}))\n"
        )
        qs.chmod(0o755)
        self.environment = {
            key: value for key, value in os.environ.items()
            if key not in {"CLAVIS_BUILD_DIR", "CLAVIS_QML_BUILD_DIR", "NYXURI_BUILD_DIR", "NYXURI_QML_BUILD_DIR", "QML_IMPORT_PATH", "QML2_IMPORT_PATH"}
        }
        self.environment["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]

    def tearDown(self):
        self.ctx.__exit__()

    def invoke(self, *args, **environment):
        return subprocess.run(
            [str(self.runner), *args], env={**self.environment, **environment},
            capture_output=True, text=True, timeout=5,
        )

    def test_pure_qml_launcher_argument_shape(self):
        result = self.invoke("-v")
        self.assertEqual(result.returncode, 0, result.stderr)
        call = json.loads(result.stdout)
        self.assertEqual(call["argv"], ["-p", str(self.shell), "--no-duplicate", "-v"])

    def test_pure_qml_launcher_preserves_environment_import_paths(self):
        result = self.invoke("-v", QML_IMPORT_PATH="/user/qt6", QML2_IMPORT_PATH="/user/legacy")
        self.assertEqual(result.returncode, 0, result.stderr)
        call = json.loads(result.stdout)
        self.assertEqual(call["qml"], "/user/qt6")
        self.assertEqual(call["qml2"], "/user/legacy")

    def test_pure_qml_launcher_mounts_fallback_path(self):
        fallback = self.shell / "fallback"
        fallback.mkdir()
        result = self.invoke("-v", QML_IMPORT_PATH="/user/qt6", QML2_IMPORT_PATH="/user/legacy")
        self.assertEqual(result.returncode, 0, result.stderr)
        call = json.loads(result.stdout)
        self.assertEqual(call["qml"], f"/user/qt6:{fallback}")
        self.assertEqual(call["qml2"], f"/user/legacy:{fallback}")

    def test_action_shape_and_missing_argument(self):
        for action, target, method, trailing in [
            ("launcher", "spotlight", "toggle", []),
            ("session", "power-menu", "toggle", []),
            ("settings", "control-center", "toggle", [""]),
            ("clipboard", "spotlight", "openMode", ["clipboard"]),
            ("lock", "lock", "open", []),
            ("wallpaper-random", "wallpaper", "random", []),
            ("wallpaper-picker", "control-center", "toggle", ["wallpaper"]),
        ]:
            with self.subTest(action=action):
                result = self.invoke("--action", action)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["argv"],
                                 ["-p", str(self.shell), "ipc", "call", target, method, *trailing])
        result = self.invoke("--action")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing action", result.stderr)

    def test_action_invoked_via_symlink(self):
        symlink_bin = self.ctx.home / "bin" / "nyxuri-shell-link"
        symlink_bin.parent.mkdir(parents=True, exist_ok=True)
        symlink_bin.symlink_to(self.runner)
        result = subprocess.run(
            [str(symlink_bin), "--action", "launcher"],
            cwd=self.shell,
            capture_output=True,
            text=True,
            env=self.environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["argv"],
            ["-p", str(self.shell), "ipc", "call", "spotlight", "toggle"],
        )

    def test_changed_scope_is_relative_and_excludes_host_changes(self):
        repo = self.ctx.home / "git fixture"
        shell = repo / "shell"
        shell.mkdir(parents=True)
        (shell / "changed.qml").write_text("old")
        (shell / "deleted.qml").write_text("old")
        (repo / "host.py").write_text("old")
        for argv in [
            ["git", "init", "-q", str(repo)],
            ["git", "-C", str(repo), "add", "."],
            ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"],
        ]:
            subprocess.run(argv, check=True, capture_output=True, env=self.environment)
        (shell / "changed.qml").write_text("new")
        (shell / "deleted.qml").unlink()
        (shell / "untracked.qml").write_text("new")
        (repo / "host.py").write_text("new")
        result = subprocess.run(
            ["bash", "-c", 'source "$1"; clavis_files changed', "test", str(SHELL / "scripts/dev/files.sh")],
            cwd=shell, capture_output=True, check=True, env=self.environment,
        )
        self.assertEqual(set(result.stdout.rstrip(b"\0").split(b"\0")),
                         {b"changed.qml", b"deleted.qml", b"untracked.qml"})


class ShellPresentationTests(unittest.TestCase):
    """Run real QML owners under a private HOME, D-Bus and headless Wayland."""

    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)
        self.qs = shutil.which("qs")
        dbus = shutil.which("dbus-run-session")
        weston = shutil.which("weston")
        if not self.qs or not dbus or not weston:
            self.skipTest("Quickshell, Weston, and private D-Bus required for presentation tests")
        self.shell = self.ctx.home / "preview"
        shutil.copytree(SHELL, self.shell, ignore=shutil.ignore_patterns(
            "native", "build", "wiki", "tests", ".qmlls.ini", "__pycache__"))
        runtime = self.ctx.home / "runtime"
        runtime.mkdir(mode=0o700)
        fallback = str(SHELL / "fallback")
        self.environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("CLAVIS_", "QS_", "NYXURI_"))
            and key not in {"NIRI_SOCKET", "WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"}
        }
        self.environment.update(
            QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="", QT_QUICK_BACKEND="software",
            XDG_RUNTIME_DIR=str(runtime), XDG_DATA_HOME=str(self.ctx.home / "data"),
            XDG_CURRENT_DESKTOP="", XDG_SESSION_DESKTOP="", WAYLAND_DISPLAY="presentation-wayland",
            QML_IMPORT_PATH=fallback, QML2_IMPORT_PATH=fallback,
        )
        compositor_log = open(self.ctx.home / "compositor.log", "w+")
        self.addCleanup(compositor_log.close)
        compositor = subprocess.Popen(
            [weston, "--backend=headless", "--renderer=pixman", "--no-config",
             "--socket=presentation-wayland", "--idle-time=0"],
            env=self.environment, stdout=compositor_log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, compositor)
        deadline = time.monotonic() + 10
        while not (runtime / "presentation-wayland").exists():
            if compositor.poll() is not None or time.monotonic() >= deadline:
                compositor_log.seek(0)
                self.fail("Private compositor did not start:\n" + compositor_log.read())
            time.sleep(0.05)
        self.palette = self.ctx.home / "data/nyxuri/profiles/default/generated/clavis/colors.json"
        self.palette.parent.mkdir(parents=True)
        if self._testMethodName != "test_missing_palette_uses_defaults_then_watches_creation":
            self.palette.write_text('{"primary":"#123456"}')
        (self.shell / "shell.qml").write_text(self._harness_qml())
        self.output = open(self.ctx.home / "preview.log", "w+")
        self.addCleanup(self.output.close)
        self.process = subprocess.Popen(
            [dbus, "--", self.qs, "-p", str(self.shell), "--no-duplicate"],
            env=self.environment, stdout=self.output, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, self.process)
        initial_color = "#88d0ec" if not self.palette.exists() else "#123456"
        if self._testMethodName.startswith("test_r11_"):
            self.wait_for("parseRss", "2048")
        else:
            self.wait_for("palette", initial_color)

    def _harness_qml(self):
        if self._testMethodName.startswith("test_r11_"):
            return '''import QtQuick
import Quickshell
import Quickshell.Io
import qs.app.services
import qs.modules.settings
import "modules/settings/ShellDiagnostics.js" as ShellDiagnostics
import "modules/settings/ShellSamplerMath.js" as SamplerMath

ShellRoot {
    IpcHandler {
        target: "presentation-test"

        function parseRss(): string {
            return String(SamplerMath.parseVmRssKb("Name:\\tqs\\nVmRSS:\\t  2048 kB\\nVmPeak:\\t 4096 kB"));
        }

        function samplingPref(on: bool): string {
            UiPreferences.setControlPlaneResourceSampling(on);
            return "OK";
        }

        function samplingMount(mounted: bool): string {
            ShellControlService.setPageMounted(mounted);
            return "OK";
        }

        function samplingState(): string {
            return JSON.stringify({
                "active": ShellControlService.samplingActive,
                "cpu": ShellControlService.cpuPercent,
                "rss": ShellControlService.rssKb,
                "last": ShellControlService.lastSampleMs,
                "pref": UiPreferences.controlPlaneResourceSampling,
                "mounted": ShellControlService.pageMounted
            });
        }

        function diagSanitizeProbe(): string {
            const poisoned = ShellDiagnostics.buildDiagnostics({
                "homePath": "/home/nyxuser",
                "generatedAtMs": 12,
                "stage": "READY",
                "uptimeMs": 3,
                "firstFrameMs": 1,
                "readyMs": 2,
                "ipcReadyMs": 3,
                "compositorPresent": true,
                "compositorConnected": false,
                "compositorReconnecting": true,
                "samplingEnabled": false,
                "samplingIntervalMs": 5000,
                "samplingCpuPercent": -1,
                "samplingRssKb": -1,
                "samplingLastSampleMs": 0,
                "modules": [{"id": "dock\\nsecret=1", "enabled": true, "state": "/home/nyxuser/x"}],
                "dependencies": [{"id": "wl-copy", "available": true, "probed": true}],
                "errors": [{"source": "test", "message": "boom at /home/nyxuser/secret.txt\\ttabbed\\nlines "
                           + "x".repeat(2000)}],
                "paths": {"config": "/home/nyxuser/.config/nyxuri", "data": "/tmp/data"}
            });
            return JSON.stringify(poisoned);
        }

        function diagJson(): string {
            return ShellControlService.diagnosticsJson();
        }

        function diagExport(): string {
            return ShellControlService.exportDiagnostics() ? "OK" : "BUSY";
        }

        function diagExportState(): string {
            return JSON.stringify({
                "path": ShellControlService.lastExportPath,
                "error": ShellControlService.lastExportError
            });
        }
    }
}
'''
        return '''import QtQuick
import Quickshell
import Quickshell.Io
import qs.app.services
import qs.shared.theme
import qs.shared.controls
import qs.modules.settings
import qs.modules.dock
import qs.modules.wallpaper

ShellRoot {
    Component.onCompleted: {
        ThemeService.reloadColors();
        FontService.refresh();
    }
    IpcHandler {
        target: "presentation-test"
        function palette(): string { return Appearance.m3colors.m3primary.toString(); }
        function error(): string { return ThemeService.paletteError; }
        function opacity(): string { return String(Appearance.backgroundOpacity); }
        function anchors(): string {
            const anchor = anchorFactory.createObject(scroll.contentItem);
            if (SettingsBackend.searchAnchors["test.anchor"] !== anchor)
                return "anchor not registered";
            if (!anchor.reveal(1) || scroll.contentY <= 0)
                return "anchor did not reveal target";
            anchor.destroy();
            return "OK";
        }
        function anchorRemoved(): string {
            return SettingsBackend.searchAnchors["test.anchor"] ? "registered" : "OK";
        }
        function refreshIcons(): string {
            const transient = iconFactory.createObject(scroll);
            Resources.iconThemeRevision += 1;
            transient.destroy();
            return steadyIcon.refreshing ? "OK" : "icon did not refresh";
        }
        function iconsReady(): string {
            return !steadyIcon.refreshing && steadyIcon.source === steadyIcon.iconSource ? "OK" : "pending";
        }
        function check(): string {
            const original = Appearance.m3colors.m3primary.toString();
            try {
                ThemeService.applyGeneratedColors('{"primary":"#abcdef","secondary":"bad color"}');
                return "invalid palette accepted";
            } catch (error) {}
            if (Appearance.m3colors.m3primary.toString() !== original)
                return "partial palette applied";
            FontService.setConfiguredFamily("ui", "NyxuriMissingFont123");
            if (Fonts.ui === "NyxuriMissingFont123" || !Fonts.mono)
                return "font fallback failed";
            if (!Resources.iconsRoot.endsWith("/assets/icons/"))
                return "resource injection failed";
            PersonalizationConfig.shellBackgroundOpacity = 0.37;
            return "OK";
        }
    }
    Item {
        ThemeIcon {
            id: steadyIcon
            iconSource: "image://icon/application-x-executable"
        }
        HotCornerExclusionRegion { surfaceWidth: 100; surfaceHeight: 100 }
        MaterialDialog { visible: false }
        MediaSourceIcon {}
        NotificationVisual {}
        FileThemeIcon { resolvedSources: [] }
        AccountProfileHeader {
            width: 600
            wallpaperComponent: ProfileWallpaper {}
        }
        DockWindowCard { windowData: ({id: 1, title: "Test"}) }

    }
    Flickable {
        id: scroll
        width: 300
        height: 100
        contentHeight: 1000
        Rectangle { id: section; y: 400; width: 200; height: 50 }
    }
    Component {
        id: anchorFactory
        SettingsSearchAnchor {
            target: section
            declaration: '{"id":"test.anchor"}'
        }
    }
    Component {
        id: iconFactory
        ThemeIcon { iconSource: "image://icon/application-x-executable" }
    }
}
'''
        self.output = open(self.ctx.home / "preview.log", "w+")
        self.addCleanup(self.output.close)
        self.process = subprocess.Popen(
            [dbus, "--", self.qs, "-p", str(self.shell), "--no-duplicate"],
            env=self.environment, stdout=self.output, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, self.process)
        initial_color = "#88d0ec" if not self.palette.exists() else "#123456"
        self.wait_for("palette", initial_color)

    def stop_process(self, process):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)

    def call(self, method, *args):
        return subprocess.run(
            [self.qs, "-p", str(self.shell), "ipc", "call", "presentation-test", method, *args],
            env=self.environment, capture_output=True, text=True, timeout=5,
        )

    def wait_for(self, method, expected):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and self.process.poll() is None:
            result = self.call(method)
            if result.returncode == 0 and result.stdout.strip() == expected:
                return
            time.sleep(0.05)
        self.output.flush()
        self.output.seek(0)
        self.fail(f"IPC {method} did not return {expected!r}:\n{self.output.read()}")

    def test_palette_watch_fallback_and_presentation_injection(self):
        self.wait_for("check", "OK")
        self.wait_for("opacity", "0.37")
        self.wait_for("anchors", "OK")
        self.wait_for("anchorRemoved", "OK")
        self.wait_for("refreshIcons", "OK")
        self.wait_for("iconsReady", "OK")
        replacement = self.palette.with_suffix(".tmp")
        replacement.write_text('{"primary":"#abcdef"}')
        replacement.replace(self.palette)
        self.wait_for("palette", "#abcdef")
        replacement.write_text("invalid JSON")
        replacement.replace(self.palette)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.call("error").stdout.strip():
                break
            time.sleep(0.05)
        else:
            self.fail("Invalid palette did not report an error")
        self.wait_for("palette", "#abcdef")
        replacement.write_text('{"primary":"#654321"}')
        replacement.replace(self.palette)
        self.wait_for("palette", "#654321")
        self.wait_for("error", "")
        self.output.flush()
        self.output.seek(0)
        log = self.output.read()
        for diagnostic in ("ReferenceError", "TypeError", "Binding loop", "Unable to assign", "Failed to load configuration"):
            self.assertNotIn(diagnostic, log)

    def test_missing_palette_uses_defaults_then_watches_creation(self):
        self.wait_for("error", "")
        self.palette.write_text('{"primary":"#456789"}')
        self.wait_for("palette", "#456789")
        self.palette.unlink()
        self.wait_for("palette", "#456789")
        self.palette.write_text('{"primary":"#987654"}')
        self.wait_for("palette", "#987654")

    def _sampling_state(self):
        result = self.call("samplingState")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip())

    def _wait_sampling(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        state = {}
        while time.monotonic() < deadline and self.process.poll() is None:
            state = self._sampling_state()
            if predicate(state):
                return state
            time.sleep(0.1)
        self.output.flush()
        self.output.seek(0)
        self.fail(f"sampling state never matched: {state}\n{self.output.read()}")

    def test_r11_sampling_gate_lifecycle(self):
        """R11 behavior: the sampler only exists behind both gates, and a
        closed page or a flipped switch stops it and clears every number."""
        # Mounted but not opted in: the persisted default keeps everything off.
        self.assertEqual(self.call("samplingMount", "true").stdout.strip(), "OK")
        state = self._sampling_state()
        self.assertTrue(state["mounted"])
        self.assertFalse(state["pref"])
        self.assertFalse(state["active"])
        self.assertEqual(state["last"], 0)
        self.assertEqual(state["rss"], -1)

        # Opting in while mounted starts real sampling: RSS comes straight
        # from /proc/self, CPU% arrives after the second sample builds the
        # jiffies baseline.
        self.assertEqual(self.call("samplingPref", "true").stdout.strip(), "OK")
        state = self._wait_sampling(lambda s: s["active"] and s["last"] > 0 and s["rss"] > 0)
        self.assertGreater(state["rss"], 0)
        state = self._wait_sampling(lambda s: s["cpu"] >= 0, timeout=12)
        self.assertGreater(state["cpu"], 0)

        # Unmounting clears the numbers even though the switch stays on.
        self.assertEqual(self.call("samplingMount", "false").stdout.strip(), "OK")
        state = self._wait_sampling(lambda s: not s["active"] and s["last"] == 0 and s["rss"] == -1
                                    and s["cpu"] == -1)
        self.assertTrue(state["pref"])
        time.sleep(0.5)
        self.assertEqual(self._sampling_state()["last"], 0)

        # Flipping the switch off while unmounted keeps everything idle.
        self.assertEqual(self.call("samplingPref", "false").stdout.strip(), "OK")
        self.assertFalse(self._sampling_state()["active"])

    def test_r11_diagnostics_sanitized_and_exported(self):
        """R11 behavior: diagnostics are allowlist-built, home-masked,
        truncated, and the exported file carries the same guarantees."""
        # 1. Pure sanitizer against a poisoned payload (assertions here, not
        # in the harness, so the test owns the expectations).
        probe = json.loads(self.call("diagSanitizeProbe").stdout.strip())
        self.assertEqual(probe["schemaVersion"], 1)
        self.assertEqual(probe["generatedAtMs"], 12)
        message = probe["errors"][0]["message"]
        self.assertNotIn("/home/nyxuser", message)
        self.assertNotIn("\n", message)
        self.assertNotIn("\t", message)
        self.assertLessEqual(len(message), 512)
        module = probe["modules"][0]
        self.assertEqual(module["id"], "dock secret=1")
        self.assertEqual(module["state"], "~/x")
        self.assertEqual(probe["paths"]["config"], "~/.config/nyxuri")
        self.assertEqual(probe["paths"]["data"], "/tmp/data")

        # 2. End-to-end payload from the live singletons: schema keys are
        # exactly the allowlist, no raw home path and no environment leaks.
        raw = self.call("diagJson").stdout
        payload = json.loads(raw.strip())
        self.assertEqual(set(payload.keys()), {
            "schemaVersion", "generatedAtMs", "shell", "compositor", "modules",
            "dependencies", "errors", "sampling", "paths"
        })
        self.assertNotIn(str(self.ctx.home), raw)
        self.assertNotIn("NIRI_SOCKET", raw)
        self.assertIn("dock", {entry["id"] for entry in payload["modules"]})
        self.assertIn("wl-copy", {entry["id"] for entry in payload["dependencies"]})

        # 3. The export writes the same sanitized document into the cache.
        self.assertEqual(self.call("diagExport").stdout.strip(), "OK")
        deadline = time.monotonic() + 8
        state = {"path": "", "error": ""}
        while time.monotonic() < deadline:
            result = self.call("diagExportState")
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(result.stdout.strip())
            if state["path"] or state["error"]:
                break
            time.sleep(0.05)
        self.assertEqual(state["error"], "", state)
        self.assertTrue(state["path"], state)
        exported = Path(state["path"])
        self.assertTrue(exported.is_file(), state)
        content = exported.read_text(encoding="utf-8")
        self.assertNotIn(str(self.ctx.home), content)
        self.assertEqual(json.loads(content)["schemaVersion"], 1)


if __name__ == "__main__":
    unittest.main()
