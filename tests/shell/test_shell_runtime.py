"""Behavior checks for the source launcher, tooling scope and presentation owners."""

import base64
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import unittest

from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import io
import sys
from unittest.mock import patch


SHELL = Path(__file__).resolve().parents[2] / "shell"

PRESENTATION_TIMEOUT_SCALE = 1.0


def presentation_timeout_scale():
    """Multiplier for presentation budgets, for hardware slower than CI."""
    raw = os.environ.get("NYXURI_PRESENTATION_TIMEOUT_SCALE", "").strip()
    try:
        value = float(raw) if raw else 0.0
    except ValueError:
        value = 0.0
    return value if value >= 1 else PRESENTATION_TIMEOUT_SCALE


def presentation_budget(seconds):
    return seconds * presentation_timeout_scale()


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
            if key not in {"NYXURI_BUILD_DIR", "NYXURI_QML_BUILD_DIR", "QML_IMPORT_PATH", "QML2_IMPORT_PATH"}
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

    def test_pure_qml_launcher_mounts_named_module_path(self):
        module_root = self.shell / "ui" / "shapes"
        module_root.mkdir(parents=True)
        result = self.invoke("-v", QML_IMPORT_PATH="/user/qt6", QML2_IMPORT_PATH="/user/legacy")
        self.assertEqual(result.returncode, 0, result.stderr)
        call = json.loads(result.stdout)
        self.assertEqual(call["qml"], f"/user/qt6:{module_root}")
        self.assertEqual(call["qml2"], f"/user/legacy:{module_root}")

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
            ["bash", "-c", 'source "$1"; nyxuri_files changed', "test", str(SHELL / "scripts/dev/files.sh")],
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
            if not key.startswith(("QS_", "NYXURI_"))
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
        self.palette = self.ctx.home / "data/nyxuri/profiles/default/generated/nyxuri/colors.json"
        self.palette.parent.mkdir(parents=True)
        if self._testMethodName == "test_template_render_queue_writes_outputs_and_hooks":
            # Builtin template hooks run pkill; shim it so a passing test can
            # never signal the developer's session.
            shim_dir = self.ctx.home / "bin"
            shim_dir.mkdir(parents=True, exist_ok=True)
            (shim_dir / "pkill").write_text(
                '#!/bin/sh\nprintf "%%s\\n" "$*" >> "%s/hook-pkill"\n' % self.ctx.home)
            (shim_dir / "pkill").chmod(0o755)
            self.environment["PATH"] = str(shim_dir) + os.pathsep + self.environment["PATH"]
            # Trace hook STARTS separately from the pkill shim: btop-apply and
            # starship-apply never pkill, so their invocations are invisible
            # there and a stalled spawn would be indistinguishable from a
            # stalled render.
            trace = self.ctx.home / "hook-trace"
            for hook in ["kitty-apply.sh", "btop-apply.sh", "starship-apply.sh"]:
                path = self.shell / "app/templates" / hook.split("-")[0] / hook
                path.write_text('printf "%s\\n" "$0" >> "' + str(trace) + '"\n' + path.read_text(
                    encoding="utf-8"))
            # Trace FileView operation internals: a lost saved()/loaded() emit
            # wedges the queue without any QML-level diagnostic.
            self.environment["QT_LOGGING_RULES"] = "quickshell.io.fileview.debug=true"
            self.palette_modes = self.ctx.home / ("data/nyxuri/profiles/default/generated/nyxuri/"
                                                  "palette-modes.json")
            self.palette_modes.parent.mkdir(parents=True, exist_ok=True)
            self.palette_modes.write_text(self._palette_modes_fixture())
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
import qs.services
import qs.plugins.settings
import "plugins/settings/ShellDiagnostics.js" as ShellDiagnostics
import "plugins/settings/ShellSamplerMath.js" as SamplerMath

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
import qs.services
import qs.commons
import qs.ui
import qs.plugins.settings
import qs.plugins.dock
import qs.plugins.wallpaper

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
        function templateState(): string {
            return JSON.stringify({
                "ready": TemplateService.ready,
                "queue": TemplateService.renderQueue.length,
                "rendering": TemplateService.renderingId,
                "renderingOutput": TemplateService.renderingOutput,
                "outputReady": TemplateService.outputReady,
                "pending": TemplateService.pendingRendered.length,
                "hookRunning": TemplateService.hookRunning,
                "errors": TemplateService.renderErrors,
                "activeMode": TemplateService.activeMode
            });
        }
        function rerender(): string {
            TemplateService.renderAll();
            return "OK";
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
            if (!Resources.iconsRoot.endsWith("/app/icons/"))
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
            env=self.environment, capture_output=True, text=True,
            timeout=presentation_budget(5),
        )

    def wait_for(self, method, expected):
        deadline = time.monotonic() + presentation_budget(10)
        while time.monotonic() < deadline and self.process.poll() is None:
            try:
                result = self.call(method)
            except subprocess.TimeoutExpired:
                continue
            if result.returncode == 0 and result.stdout.strip() == expected:
                return
            time.sleep(0.05)
        self.output.flush()
        self.output.seek(0)
        self.fail(f"IPC {method} did not return {expected!r}:\n{self.output.read()}")

    def dump_artifacts(self):
        hook_log = self.ctx.home / "hook-pkill"
        artifacts = {}
        for path in [self.ctx.home / ".config/kitty/themes/nyxuri.conf",
                     self.ctx.home / ".config/btop/themes/nyxuri.theme",
                     self.ctx.home / ".cache/nyxuri/starship-palette.toml", hook_log]:
            artifacts[str(path.relative_to(self.ctx.home))] = (
                path.stat().st_size if path.exists() else None)
        artifacts["hook-pkill lines"] = self.hook_invocation_count()
        return artifacts

    def qslog_dump(self):
        """The preview log names the instance's qslog file; its FileView debug
        trace is the only record of a lost saved()/loaded() emit."""
        match = re.search(r"Saving logs to \"?([^\"]+)\"?", self.output.read())
        self.output.seek(0)
        if not match:
            return "(no qslog path in preview log)"
        result = subprocess.run([self.qs, "log", match.group(1)], capture_output=True,
                                text=True, timeout=10)
        return result.stdout + result.stderr

    def wait_for_queue_idle(self):
        """The render queue must drain: a stuck renderingId swallows every
        later renderAll silently (FileView.setText no-ops on identical
        content, so an onSaved-only completion never fires)."""
        deadline = time.monotonic() + presentation_budget(20)
        while time.monotonic() < deadline and self.process.poll() is None:
            state = json.loads(self.call("templateState").stdout)
            if state["rendering"] == "" and state["queue"] == 0:
                return
            time.sleep(0.05)
        self.output.flush()
        self.output.seek(0)
        state = self.call("templateState").stdout.strip()
        self.fail("render queue never drained:\nstate=%s\nartifacts=%s\nhookTrace=%s\nqslog=%s\n%s"
                  % (state, self.dump_artifacts(), self.hook_trace(), self.qslog_dump(),
                     self.output.read()))

    def hook_invocation_count(self):
        hook_log = self.ctx.home / "hook-pkill"
        if not hook_log.exists():
            return 0
        return len(hook_log.read_text(encoding="utf-8").splitlines())

    def hook_signal_arguments(self):
        hook_log = self.ctx.home / "hook-pkill"
        if not hook_log.exists():
            return []
        return [line.split() for line in hook_log.read_text(encoding="utf-8").splitlines()]

    def hook_trace(self):
        trace = self.ctx.home / "hook-trace"
        if not trace.exists():
            return []
        return trace.read_text(encoding="utf-8").splitlines()

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
        deadline = time.monotonic() + presentation_budget(5)
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

    def _palette_modes_fixture(self):
        """A full 50-token dual-mode palette, as generate-matugen-colors.sh writes."""
        tokens = [
            "background", "error", "error_container", "inverse_on_surface", "inverse_primary",
            "inverse_surface", "on_background", "on_error", "on_error_container", "on_primary",
            "on_primary_container", "on_primary_fixed", "on_primary_fixed_variant", "on_secondary",
            "on_secondary_container", "on_secondary_fixed", "on_secondary_fixed_variant",
            "on_surface", "on_surface_variant", "on_tertiary", "on_tertiary_container",
            "on_tertiary_fixed", "on_tertiary_fixed_variant", "outline", "outline_variant",
            "primary", "primary_container", "primary_fixed", "primary_fixed_dim", "scrim",
            "secondary", "secondary_container", "secondary_fixed", "secondary_fixed_dim",
            "shadow", "source_color", "surface", "surface_bright", "surface_container",
            "surface_container_high", "surface_container_highest", "surface_container_low",
            "surface_container_lowest", "surface_dim", "surface_tint", "surface_variant",
            "tertiary", "tertiary_container", "tertiary_fixed", "tertiary_fixed_dim"
        ]
        dark = {name: "#%06x" % (0x010000 + index * 0x0301) for index, name in enumerate(tokens)}
        light = {name: "#%06x" % (0x800000 + index * 0x0301) for index, name in enumerate(tokens)}
        return json.dumps({
            "schemaVersion": 1, "mode": "dark", "scheme": "scheme-tonal-spot",
            "source_color": dark["primary"], "dark": dark, "light": light
        })

    def _template_outputs(self, generation):
        """Rendered-output assertions for one fixture generation.

        kitty renders color4 from terminal_normal_blue (derived from tertiary
        in dark mode), btop renders main_fg from on_surface; the hook runs
        after the writes (kitty include line). The "switched" generation swaps
        the mode palettes, so dark-mode values come from the light set.
        """
        base = 0x010000 if generation == "first" else 0x800000
        blue = "#%06x" % (base + 46 * 0x0301)      # tertiary -> terminal_normal_blue
        on_surface = "#%06x" % (base + 17 * 0x0301)
        kitty = self.ctx.home / ".config/kitty/themes/nyxuri.conf"
        btop = self.ctx.home / ".config/btop/themes/nyxuri.theme"
        kitty_conf = self.ctx.home / ".config/kitty/kitty.conf"
        return {
            "kitty_color4": (kitty, "color4 " + blue),
            "btop_main_fg": (btop, 'theme[main_fg]="' + on_surface + '"'),
            "kitty_include": (kitty_conf, "include themes/nyxuri.conf"),
        }

    def test_template_render_queue_writes_outputs_and_hooks(self):
        """P4 behavior: palette-modes hot reload renders app templates and runs
        their hooks — the wallpaper-switch path this phase replaced matugen
        with, verified against the real QML owners."""
        expected = self._template_outputs("first")

        def outputs_ready():
            for path, marker in expected.values():
                if not path.is_file() or marker not in path.read_text(encoding="utf-8"):
                    return False
            return True

        deadline = time.monotonic() + presentation_budget(30)
        while time.monotonic() < deadline and self.process.poll() is None:
            if outputs_ready():
                break
            time.sleep(0.1)
        else:
            self.output.flush()
            self.output.seek(0)
            state = self.call("templateState").stdout.strip()
            self.fail("template outputs never rendered:\nstate=%s\n%s" % (state, self.output.read()))
        state = json.loads(self.call("templateState").stdout)
        self.assertEqual(state["errors"], {}, state)
        self.wait_for_queue_idle()
        mirror = self.ctx.home / ".config/noctalia/palettes/nyxuri.json"
        self.assertTrue(mirror.is_file(), "Noctalia palette mirror was not written")
        mirror_body = json.loads(mirror.read_text(encoding="utf-8"))
        self.assertIn("dark", mirror_body)
        self.assertEqual(len(mirror_body["dark"]["terminal"]), 22)

        # Wallpaper-switch equivalent: rewrite the dual-mode palette and watch
        # every output follow, then re-render idempotently.
        replacement = self.ctx.home / "data/nyxuri/profiles/default/generated/nyxuri/palette-modes.new"
        light_generation = json.loads(self._palette_modes_fixture())
        light_generation["mode"] = "light"
        # Swap mode palettes so the rendered dark-mode values change.
        light_generation["dark"], light_generation["light"] = (
            light_generation["light"], light_generation["dark"])
        replacement.write_text(json.dumps(light_generation))
        replacement.replace(self.palette_modes)
        switched = self._template_outputs("switched")

        deadline = time.monotonic() + presentation_budget(20)
        while time.monotonic() < deadline and self.process.poll() is None:
            if all(path.is_file() and marker in path.read_text(encoding="utf-8")
                   for path, marker in switched.values()):
                break
            time.sleep(0.1)
        else:
            self.output.flush()
            self.output.seek(0)
            state = self.call("templateState").stdout.strip()
            self.fail("palette rewrite did not re-render template outputs:\nstate=%s\n%s"
                      % (state, self.output.read()))
        self.assertEqual(json.loads(self.call("templateState").stdout)["errors"], {})
        self.wait_for_queue_idle()

        # Identical re-render: the rendered content already matches what is on
        # disk, which is exactly the boot-time regeneration case (same
        # wallpaper, byte-comparable engine output). FileView.setText no-ops
        # on identical content and never emits onSaved, so this pass must
        # still drain and the hooks must still run — otherwise the queue dies
        # here and every later wallpaper switch silently does nothing.
        hooks_before = self.hook_invocation_count()
        self.assertEqual(self.call("rerender").stdout.strip(), "OK")
        self.wait_for_queue_idle()
        self.assertGreater(self.hook_invocation_count(), hooks_before,
                           "identical re-render did not run the post hooks")
        signals = self.hook_signal_arguments()
        self.assertTrue(signals, "template hooks never signalled the applications")
        for arguments in signals:
            if "kitty" in arguments:
                self.assertIn("-x", arguments,
                              "the kitty reload signal must match the process name exactly")
        for path, marker in switched.values():
            self.assertIn(marker, path.read_text(encoding="utf-8"))

        # ...and a following palette rewrite must still be followed.
        replacement.write_text(self._palette_modes_fixture())
        replacement.replace(self.palette_modes)
        restored = self._template_outputs("first")
        deadline = time.monotonic() + presentation_budget(20)
        while time.monotonic() < deadline and self.process.poll() is None:
            if all(path.is_file() and marker in path.read_text(encoding="utf-8")
                   for path, marker in restored.values()):
                break
            time.sleep(0.1)
        else:
            self.output.flush()
            self.output.seek(0)
            state = self.call("templateState").stdout.strip()
            artifacts = self.dump_artifacts()
            self.fail("identical re-render stalled the queue; later palette rewrite was ignored:\n"
                      "state=%s\nartifacts=%s\n%s" % (state, artifacts, self.output.read()))
        self.wait_for_queue_idle()
        self.assertEqual(json.loads(self.call("templateState").stdout)["errors"], {})
        self.output.flush()
        self.output.seek(0)
        log = self.output.read()
        for diagnostic in ("ReferenceError", "TypeError", "Binding loop", "Unable to assign"):
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
        deadline = time.monotonic() + presentation_budget(timeout)
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
        deadline = time.monotonic() + presentation_budget(8)
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


class ShellConfigStoreTests(unittest.TestCase):
    """A config store that cannot be read must survive, and a first run must create it."""

    CONFIG_RELATIVE = ".config/nyxuri/config.json"

    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)
        self.qs = shutil.which("qs")
        weston = shutil.which("weston")
        if not self.qs or not weston:
            self.skipTest("Quickshell and Weston required for config store tests")
        self.shell = self.ctx.home / "preview"
        shutil.copytree(SHELL, self.shell, ignore=shutil.ignore_patterns(
            "native", "build", "wiki", "tests", ".qmlls.ini", "__pycache__"))
        runtime = self.ctx.home / "runtime"
        runtime.mkdir(mode=0o700)
        fallback = str(SHELL / "fallback")
        self.environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("QS_", "NYXURI_"))
            and key not in {"NIRI_SOCKET", "WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"}
        }
        self.environment.update(
            QT_QPA_PLATFORM="wayland", QT_QUICK_BACKEND="software",
            XDG_RUNTIME_DIR=str(runtime), XDG_DATA_HOME=str(self.ctx.home / "data"),
            WAYLAND_DISPLAY="config-store-wayland",
            QML_IMPORT_PATH=fallback, QML2_IMPORT_PATH=fallback,
        )
        compositor_log = open(self.ctx.home / "compositor.log", "w+")
        self.addCleanup(compositor_log.close)
        compositor = subprocess.Popen(
            [weston, "--backend=headless", "--renderer=pixman", "--no-config",
             "--socket=config-store-wayland", "--idle-time=0"],
            env=self.environment, stdout=compositor_log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, compositor)
        deadline = time.monotonic() + 10
        while not (runtime / "config-store-wayland").exists():
            if compositor.poll() is not None or time.monotonic() >= deadline:
                compositor_log.seek(0)
                self.fail("Private compositor did not start:\n" + compositor_log.read())
            time.sleep(0.05)
        (self.shell / "shell.qml").write_text(self._harness_qml())
        self.output = open(self.ctx.home / "preview.log", "w+")
        self.addCleanup(self.output.close)
        self.process = subprocess.Popen(
            [self.qs, "-p", str(self.shell), "--no-duplicate"],
            env=self.environment, stdout=self.output, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, self.process)

    def _harness_qml(self):
        return '''import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import qs.services
import qs.plugins.bar.tray
import qs.plugins.quicksettings
import qs.plugins.sidebars.dashboard.infotools

ShellRoot {
    IpcHandler {
        target: "configStore"
        function themeMode(): string { return String(PersonalizationConfig.themeMode); }
        function auxiliaryStores(): string {
            return String(IdleService.policyConfigPath) + "|" + String(TrayService.filePath)
                 + "|" + String(QuickToggleConfig.filePath);
        }
        function statefulStores(): string {
            return String(InfoDrawerState.filePath) + "|" + String(TodoService.filePath);
        }
    }
}
'''

    def stop_process(self, process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)

    @property
    def config_path(self):
        return self.ctx.home / self.CONFIG_RELATIVE

    def log_text(self):
        self.output.flush()
        self.output.seek(0)
        return self.output.read()

    def call(self, method):
        done = subprocess.run(
            [self.qs, "-p", str(self.shell), "ipc", "call", "configStore", method],
            env=self.environment, capture_output=True, text=True, timeout=20)
        return done.stdout

    def wait_until_ready(self):
        deadline = time.monotonic() + presentation_budget(300)
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            try:
                done = subprocess.run(
                    [self.qs, "-p", str(self.shell), "ipc", "call", "configStore", "themeMode"],
                    env=self.environment, capture_output=True, text=True, timeout=10)
            except subprocess.TimeoutExpired:
                continue
            if done.returncode == 0 and done.stdout.strip():
                return
            time.sleep(1)
        self.fail("Shell never reported readiness:\n" + self.log_text())

    def test_corrupt_config_is_left_untouched(self):
        """A parse failure must be reported, not repaired by overwriting the user's file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        corrupt = '{"theme":{"mode":"light"},"sidebar":{"keepLoaded":false},"pad":"'
        self.config_path.write_text(corrupt, encoding="utf-8")
        self.wait_until_ready()
        time.sleep(25)
        self.assertEqual(self.config_path.read_text(encoding="utf-8"), corrupt)
        self.assertIn("leaving the existing config untouched", self.log_text())

    def test_missing_config_is_created_with_defaults(self):
        """The first run still has to materialise the store."""
        self.assertFalse(self.config_path.exists())
        self.wait_until_ready()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not self.config_path.exists():
            time.sleep(0.5)
        self.assertTrue(self.config_path.exists(), "the store was never created")
        parsed = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertIn("theme", parsed)
        self.assertIn(parsed["theme"]["mode"], ("dark", "light"))

    def test_corrupt_auxiliary_stores_are_left_untouched(self):
        """The tray, quick toggle and idle stores must survive a parse failure too."""
        corrupt = '{"broken":'
        stores = [self.ctx.home / relative for relative in (
            ".config/nyxuri/idle-policy.json",
            ".config/nyxuri/tray.json",
            ".config/nyxuri/quick-toggles.json",
        )]
        for store in stores:
            store.parent.mkdir(parents=True, exist_ok=True)
            store.write_text(corrupt, encoding="utf-8")
        self.wait_until_ready()
        self.assertTrue(self.call("auxiliaryStores").strip())
        time.sleep(25)
        for store in stores:
            self.assertEqual(store.read_text(encoding="utf-8"), corrupt, store.name)
        log = self.log_text()
        for name in ("IdleService", "TrayService", "QuickToggleConfig"):
            self.assertIn(name + " failed to load", log)
            self.assertIn("leaving the existing", log)

    def test_corrupt_stateful_stores_are_left_untouched(self):
        """The drawer and todo stores schedule a save after loading; a parse failure must skip it."""
        corrupt = '{"broken":'
        stores = [self.ctx.home / relative for relative in (
            ".local/state/nyxuri/nyxuri-info-drawer.json",
            ".local/state/nyxuri/todo.json",
        )]
        for store in stores:
            store.parent.mkdir(parents=True, exist_ok=True)
            store.write_text(corrupt, encoding="utf-8")
        self.wait_until_ready()
        self.assertTrue(self.call("statefulStores").strip())
        time.sleep(25)
        for store in stores:
            self.assertEqual(store.read_text(encoding="utf-8"), corrupt, store.name)
        log = self.log_text()
        for name in ("InfoDrawerState", "TodoService"):
            self.assertIn(name + " failed to load", log)


class ShellFileUrlTests(unittest.TestCase):
    """A file whose name carries URL-significant characters still has to load."""

    SPECIAL_NAMES = (
        "plain.png",
        "has #hash.png",
        "has?question.png",
        "50%percent.png",
        "sp ace.png",
    )
    PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)
        self.qs = shutil.which("qs")
        weston = shutil.which("weston")
        if not self.qs or not weston:
            self.skipTest("Quickshell and Weston required for file URL tests")
        self.shell = self.ctx.home / "preview"
        shutil.copytree(SHELL, self.shell, ignore=shutil.ignore_patterns(
            "native", "build", "wiki", "tests", ".qmlls.ini", "__pycache__"))
        self.pictures = self.ctx.home / "pictures"
        self.pictures.mkdir()
        for name in self.SPECIAL_NAMES:
            (self.pictures / name).write_bytes(self.PNG)
        runtime = self.ctx.home / "runtime"
        runtime.mkdir(mode=0o700)
        fallback = str(SHELL / "fallback")
        self.environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("QS_", "NYXURI_"))
            and key not in {"NIRI_SOCKET", "WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"}
        }
        self.environment.update(
            QT_QPA_PLATFORM="wayland", QT_QUICK_BACKEND="software",
            XDG_RUNTIME_DIR=str(runtime), XDG_DATA_HOME=str(self.ctx.home / "data"),
            WAYLAND_DISPLAY="file-url-wayland",
            QML_IMPORT_PATH=fallback, QML2_IMPORT_PATH=fallback,
        )
        compositor_log = open(self.ctx.home / "compositor.log", "w+")
        self.addCleanup(compositor_log.close)
        compositor = subprocess.Popen(
            [weston, "--backend=headless", "--renderer=pixman", "--no-config",
             "--socket=file-url-wayland", "--idle-time=0"],
            env=self.environment, stdout=compositor_log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, compositor)
        deadline = time.monotonic() + 10
        while not (runtime / "file-url-wayland").exists():
            if compositor.poll() is not None or time.monotonic() >= deadline:
                compositor_log.seek(0)
                self.fail("Private compositor did not start:\n" + compositor_log.read())
            time.sleep(0.05)
        (self.shell / "shell.qml").write_text(self._harness_qml())
        self.output = open(self.ctx.home / "preview.log", "w+")
        self.addCleanup(self.output.close)
        self.process = subprocess.Popen(
            [self.qs, "-p", str(self.shell), "--no-duplicate"],
            env=self.environment, stdout=self.output, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.addCleanup(self.stop_process, self.process)

    def _harness_qml(self):
        images = "\n".join(
            '    Image { id: image%d; source: Paths.fileUrl(base + "/%s") }' % (index, name)
            for index, name in enumerate(self.SPECIAL_NAMES))
        statuses = " + \"|\" + ".join(
            'name%d + "=" + status(image%d)' % (index, index)
            for index in range(len(self.SPECIAL_NAMES)))
        names = "\n".join(
            '    property string name%d: "%s"' % (index, name)
            for index, name in enumerate(self.SPECIAL_NAMES))
        return '''import QtQuick
import Quickshell
import Quickshell.Io
import qs.app

ShellRoot {
    property string base: "%s"
%s
%s

    function status(image): string {
        if (image.status === Image.Ready) return "Ready";
        if (image.status === Image.Error) return "Error";
        if (image.status === Image.Loading) return "Loading";
        return "Null";
    }

    IpcHandler {
        target: "fileUrl"
        function statuses(): string { return %s; }
        function shapes(): string {
            return "hash=" + Paths.fileUrl("/p/has #hash.png")
                 + "|question=" + Paths.fileUrl("/p/has?question.png")
                 + "|space=" + Paths.fileUrl("/p/sp ace.png")
                 + "|percent=" + Paths.fileUrl("/p/50%%percent.png")
                 + "|plain=" + Paths.fileUrl("/p/plain.png")
                 + "|empty=" + Paths.fileUrl("")
                 + "|already=" + Paths.fileUrl("file:///p/already%%20encoded.png");
        }
    }
}
''' % (self.pictures, names, images, statuses)

    def stop_process(self, process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)

    def log_text(self):
        self.output.flush()
        self.output.seek(0)
        return self.output.read()

    def call(self, method):
        done = subprocess.run(
            [self.qs, "-p", str(self.shell), "ipc", "call", "fileUrl", method],
            env=self.environment, capture_output=True, text=True, timeout=20)
        return done.stdout

    def wait_until_ready(self):
        deadline = time.monotonic() + presentation_budget(300)
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            try:
                done = subprocess.run(
                    [self.qs, "-p", str(self.shell), "ipc", "call", "fileUrl", "shapes"],
                    env=self.environment, capture_output=True, text=True, timeout=10)
            except subprocess.TimeoutExpired:
                continue
            if done.returncode == 0 and done.stdout.strip():
                return
            time.sleep(1)
        self.fail("Shell never reported readiness:\n" + self.log_text())

    def test_special_characters_still_load(self):
        """A hash or question mark in the file name used to make the image fail outright."""
        self.wait_until_ready()
        time.sleep(25)
        statuses = self.call("statuses").strip()
        self.assertTrue(statuses)
        for entry in statuses.split("|"):
            self.assertTrue(entry.endswith("=Ready"), entry)

    def test_reserved_characters_are_percent_encoded(self):
        """Every character that URL parsing would otherwise consume has to be escaped."""
        self.wait_until_ready()
        time.sleep(25)
        shapes = self.call("shapes").strip()
        self.assertTrue(shapes)
        self.assertIn("hash=file:///p/has%20%23hash.png", shapes)
        self.assertIn("question=file:///p/has%3Fquestion.png", shapes)
        self.assertIn("space=file:///p/sp%20ace.png", shapes)
        self.assertIn("percent=file:///p/50%25percent.png", shapes)
        self.assertIn("plain=file:///p/plain.png", shapes)
        self.assertIn("empty=", shapes)
        self.assertIn("already=file:///p/already%20encoded.png", shapes)


if __name__ == "__main__":
    unittest.main()


class TestPresentationTimeoutScale(unittest.TestCase):
    """Slow hardware must be able to run the presentation harness at all."""

    def _module(self):
        from tests.shell import test_shell_runtime

        return test_shell_runtime

    def test_default_scale_preserves_the_shipped_budgets(self):
        module = self._module()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NYXURI_PRESENTATION_TIMEOUT_SCALE", None)
            self.assertEqual(module.presentation_timeout_scale(), 1.0)
            for original in (5, 8, 10, 15, 20, 30):
                self.assertEqual(module.presentation_budget(original), float(original))

    def test_scale_multiplies_every_budget(self):
        module = self._module()
        with patch.dict(os.environ, {"NYXURI_PRESENTATION_TIMEOUT_SCALE": "12"}):
            self.assertEqual(module.presentation_budget(10), 120.0)
            self.assertEqual(module.presentation_budget(30), 360.0)

    def test_invalid_values_are_ignored(self):
        module = self._module()
        for value in ("0.1", "0", "-3", "abc", ""):
            with patch.dict(os.environ, {"NYXURI_PRESENTATION_TIMEOUT_SCALE": value}):
                self.assertEqual(module.presentation_timeout_scale(), 1.0, value)
