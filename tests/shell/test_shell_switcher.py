"""Regression tests for upstream defects fixed during the bug-hunt rounds.

Each test reproduces a concrete failure that shipped in v4.0.0-alpha.1 and
asserts the corrected behavior, so the defect cannot silently return.
"""

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.utils import TempEnv


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class TestShellSwitcherClassification(unittest.TestCase):

    def test_default_shell_comes_from_the_checked_out_source_tree(self):
        """源码仓库的默认入口位于仓库根目录下的 shell/。"""
        from nyxuri.desktop import shell_switcher

        with TempEnv() as ctx:
            repo = ctx.home / "source tree"
            module = repo / "nyxuri" / "desktop" / "shell_switcher.py"
            module.parent.mkdir(parents=True)
            entry = repo / "shell" / "nyxuri-shell"
            entry.parent.mkdir()
            entry.write_text("#!/bin/sh\n", encoding="utf-8")
            entry.chmod(0o755)

            with patch.object(shell_switcher, "__file__", str(module)), \
                 patch.object(shell_switcher.shutil, "which", return_value=None):
                self.assertEqual(shell_switcher.find_default_custom_bin(), str(entry))

    def test_running_shell_from_current_source_tree_is_classified(self):
        """进程探测把当前 checkout 的 Quickshell 实例纳入切换清理范围。"""
        from nyxuri.desktop import shell_switcher

        with TempEnv() as ctx:
            repo = ctx.home / "source tree"
            module = repo / "nyxuri" / "desktop" / "shell_switcher.py"
            shell_dir = repo / "shell"
            module.parent.mkdir(parents=True)
            shell_dir.mkdir()
            cmdline = f"qs\0-p\0{shell_dir}\0".encode()
            real_read_bytes = Path.read_bytes

            def read_bytes(path):
                if str(path) == "/proc/4242/cmdline":
                    return cmdline
                return real_read_bytes(path)

            with patch.object(shell_switcher, "__file__", str(module)), \
                 patch.dict(os.environ, {"NYXURI_CUSTOM_SHELL_BIN": ""}), \
                 patch.object(shell_switcher, "find_pids",
                              side_effect=lambda name: [4242] if name in ("qs", "quickshell") else []), \
                 patch.object(Path, "read_bytes", read_bytes):
                self.assertEqual(shell_switcher.probe_running_shells(), [("nyxuri-shell", 4242)])

    def test_third_party_quickshell_is_not_nyxuri_shell(self):
        from nyxuri.desktop import shell_switcher
        with TempEnv():
            cmdline = b"quickshell\x00-p\x00/home/u/.config/quickshell\x00"
            real_read = Path.read_bytes
            with patch.object(shell_switcher, "find_pids",
                              side_effect=lambda pat: [4242] if pat in ("qs", "quickshell") else []), \
                 patch.object(Path, "read_bytes",
                              lambda self: cmdline if str(self) == "/proc/4242/cmdline" else real_read(self)):
                self.assertEqual(shell_switcher.probe_running_shells(), [])

    def test_already_active_keeps_the_running_bin(self):
        from nyxuri.desktop import shell_switcher
        from nyxuri.kernel.ledger import custom_shell_bin, set_shell
        with TempEnv():
            old_bin = str(Path(tempfile.mkdtemp()) / "old-shell")
            new_bin = str(Path(tempfile.mkdtemp()) / "new-shell")
            Path(old_bin).write_text("#!/bin/sh\n", encoding="utf-8")
            Path(new_bin).write_text("#!/bin/sh\n", encoding="utf-8")
            set_shell("nyxuri-shell", old_bin)
            with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
                 patch.object(shell_switcher, "probe_running_shells", return_value=[("nyxuri-shell", 111)]), \
                 patch.object(shell_switcher, "preflight_shell", return_value=(True, new_bin, "")), \
                 patch.object(shell_switcher, "spawn_shell") as spawn, \
                 patch.object(shell_switcher, "ensure_compositor_gateway_scripts"), \
                 patch.object(shell_switcher, "is_shell_locked", return_value=False):
                ok, _ = shell_switcher.hot_switch_shell("nyxuri-shell", new_bin)
            self.assertTrue(ok)
            self.assertFalse(spawn.called)
            self.assertEqual(custom_shell_bin(), old_bin)

    def test_failed_restore_returns_tuple_instead_of_raising(self):
        from nyxuri.desktop import shell_switcher
        with TempEnv():
            attempts = {"n": 0}

            def flaky(name, bin_path):
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise FileExistsError(17, "File exists")
                raise OSError(13, "Permission denied")

            with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
                 patch.object(shell_switcher, "probe_running_shells", return_value=[("noctalia", 1234)]), \
                 patch.object(shell_switcher, "preflight_shell", return_value=(True, "/bin/sh", "")), \
                 patch.object(shell_switcher, "spawn_shell", side_effect=flaky), \
                 patch.object(shell_switcher, "ensure_compositor_gateway_scripts"), \
                 patch.object(shell_switcher, "stop_shell_process", return_value=True), \
                 patch.object(shell_switcher, "stop_all_shell_instances", return_value=True), \
                 patch.object(shell_switcher, "is_shell_locked", return_value=False), \
                 patch.object(shell_switcher.shutil, "which", return_value="/usr/bin/noctalia"):
                ok, message = shell_switcher.hot_switch_shell("nyxuri-shell", "/bin/sh")
            self.assertFalse(ok)
            self.assertIn("also failed", message)

    def test_probe_sees_parent_shell_dispatching_a_unit_switch(self):
        # Regression (2026-10-17): UnitControlService dispatches `nyxuri
        # on/off shell.X` from inside the RUNNING shell, so this CLI's
        # parent process IS the qs instance the bridge must notify.
        # probe_running_shells() used to exclude getppid(), went blind
        # there, and every shell-originated unit-changed delivery became
        # a silent no-op (toggles landed the ledger, the desktop never
        # re-projected). Reproduces the exact topology: a fake qs process
        # (binary exec, argv preserved verbatim in /proc) → child prober
        # whose getppid() is that qs.
        from nyxuri.desktop import shell_switcher
        repo = Path(shell_switcher.__file__).resolve().parents[2]
        with TempEnv() as ctx:
            fake_wrapper = ctx.home / "nyxuri-shell"
            fake_wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            fake_wrapper.chmod(0o755)
            # resolve_custom_bin() via env pins known_shell_dirs to ctx.home,
            # so the fake instance must target -p ctx.home to classify.
            prober = ctx.home / "prober.py"
            prober.write_text(
                "import json\n"
                "from nyxuri.desktop import shell_switcher\n"
                "print(json.dumps(shell_switcher.probe_running_shells()))\n",
                encoding="utf-8")
            out_path = ctx.home / "probe-out.json"
            err_path = ctx.home / "probe-err.txt"
            # The fake qs is the real python binary (execve keeps argv
            # verbatim: /proc shows "qs -c ... -p ... --no-duplicate").
            # -c must precede -p or CPython's own parser would reject -p.
            # The driver text ships inside the fake cmdline, so it touches
            # no module names (classify() bad-lists several); the prober
            # path travels via env instead.
            driver = (
                "import json, os, subprocess\n"
                "r = subprocess.run([os.environ['PROBE_PY'], os.environ['PROBER']],\n"
                "                   capture_output=True, text=True, timeout=25)\n"
                "with open(os.environ['PROBE_OUT'], 'w', encoding='utf-8') as fh:\n"
                "    fh.write(json.dumps({'out': r.stdout, 'err': r.stderr}))\n"
            )
            env = dict(os.environ,
                       NYXURI_CUSTOM_SHELL_BIN=str(fake_wrapper),
                       PROBE_PY=sys.executable, PROBER=str(prober), PROBE_OUT=str(out_path),
                       PYTHONPATH=str(repo) + os.pathsep + os.environ.get("PYTHONPATH", ""))
            fakeqs = subprocess.Popen(
                ["qs", "-c", driver, "-p", str(ctx.home), "--no-duplicate"],
                executable=sys.executable, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                fakeqs.wait(timeout=30)
            except subprocess.TimeoutExpired:
                fakeqs.kill()
                self.fail("fake qs instance did not exit")
            self.assertTrue(out_path.exists(), "prober driver wrote nothing")
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["out"].strip(),
                            f"prober produced no output; stderr: {payload['err']}")
            result = [tuple(item) for item in json.loads(payload["out"])]
            self.assertIn(("nyxuri-shell", fakeqs.pid), result)

class TestShellLauncherConfigRoot(unittest.TestCase):

    def _launcher(self):
        return Path(__file__).resolve().parents[2] / "shell" / "nyxuri-shell"

    def test_launcher_ignores_a_divergent_xdg_config_home(self):
        self.assertNotIn("XDG_CONFIG_HOME", self._launcher().read_text(encoding="utf-8"))

    def test_radial_launcher_runs_the_deployed_tool_despite_divergent_xdg(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            tool = home / ".config" / "noctalia" / "tools" / "orbit-launcher.py"
            tool.parent.mkdir(parents=True)
            tool.write_text('#!/bin/sh\nprintf "ORBIT-LAUNCHER-STARTED\\n"\n', encoding="utf-8")
            tool.chmod(0o755)
            result = subprocess.run(
                ["bash", str(self._launcher()), "--action", "radial-launcher"],
                capture_output=True, text=True,
                env={"HOME": str(home), "XDG_CONFIG_HOME": str(home / "elsewhere"),
                     "PATH": os.environ.get("PATH", "/usr/bin:/bin")})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ORBIT-LAUNCHER-STARTED", result.stdout)

    def test_translate_runs_the_deployed_tool(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            tool = home / ".config" / "noctalia" / "tools" / "orbit-translate.py"
            tool.parent.mkdir(parents=True)
            tool.write_text('#!/bin/sh\nprintf "ORBIT-TRANSLATE-STARTED\\n"\n', encoding="utf-8")
            tool.chmod(0o755)
            result = subprocess.run(
                ["bash", str(self._launcher()), "--action", "translate"],
                capture_output=True, text=True,
                env={"HOME": str(home), "XDG_CONFIG_HOME": str(home / "elsewhere"),
                     "PATH": os.environ.get("PATH", "/usr/bin:/bin")})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ORBIT-TRANSLATE-STARTED", result.stdout)

class TestRuntimeHomeContract(unittest.TestCase):

    def test_shell_and_python_resolve_the_same_runtime_home(self):
        import shutil
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not available")
        lib = Path(__file__).resolve().parents[2] / "shell" / "scripts" / "lib"
        with tempfile.TemporaryDirectory() as temporary:
            env = {"HOME": temporary, "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
            shell = subprocess.run(
                [bash, "-c", 'source "%s"\nnyxuri_paths_init\nprintf "%%s" "$NYXURI_SHELL_RUNTIME_HOME"'
                 % (lib / "nyxuri-paths.sh")],
                capture_output=True, text=True, env=env)
            self.assertEqual(shell.returncode, 0, shell.stderr)
            python = subprocess.run(
                [sys.executable, "-c",
                 'import sys; sys.path.insert(0, "%s")\n'
                 'from nyxuri_paths import NyxuriPaths\n'
                 'sys.stdout.write(str(NyxuriPaths.from_environment().runtime_home))' % lib],
                capture_output=True, text=True, env=env)
            self.assertEqual(python.returncode, 0, python.stderr)
        self.assertEqual(shell.stdout, python.stdout)
        self.assertTrue(shell.stdout.endswith("/nyxuri/runtime/nyxuri"), shell.stdout)


class TestShellRuntimePreflight(unittest.TestCase):
    """缺运行时、QML或字体时不能停止旧实例；探针只运行自建进程。"""

    def setUp(self):
        self.context = TempEnv()
        self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)
        self.root = self.context.home / "shell"
        self.root.mkdir()
        self.entry = self.root / "nyxuri-shell"
        source = Path(__file__).resolve().parents[2] / "shell/nyxuri-shell"
        self.entry.write_bytes(source.read_bytes())
        self.entry.chmod(0o755)
        (self.root / "shell.qml").write_text("import QtQuick\nimport Quickshell\nShellRoot {}\n")
        (self.root / "app").mkdir()
        (self.root / "app/Required.qml").write_text("import QtQuick.Controls\nItem {}\n")
        self.binaries = self.context.home / "bin"
        self.binaries.mkdir()
        # PATH完全隔离，不能因宿主恰好有qs而让缺运行时场景变成实际启动。
        for command in ("bash", "readlink", "dirname"):
            (self.binaries / command).symlink_to(shutil.which(command))
        self.audit = self.context.home / "probe-audit.json"

    def runtime(self, mode="ready"):
        path = self.binaries / "qs"
        path.write_text(
            "#!" + sys.executable + "\n"
            "import json, os, sys, time\n"
            "from pathlib import Path\n"
            "Path(os.environ['QS_PROBE_AUDIT']).write_text(json.dumps({'argv':sys.argv,'env':dict(os.environ),'qml':Path(sys.argv[2]+'/shell.qml').read_text(),'pid':os.getpid()}))\n"
            + ("Path(os.environ['NYXURI_PREFLIGHT_MARKER']).write_text('NYXURI_RUNTIME_PREFLIGHT_READY')\ntime.sleep(30)\n" if mode == "ready" else
               "print('module QtQuick.Controls is not installed', flush=True)\nsys.exit(1)\n"), encoding="utf-8")
        path.chmod(0o755)
        return path

    def environment(self):
        return patch.dict(os.environ, {"PATH": str(self.binaries),
                                       "QML_DISK_CACHE_PATH": str(self.context.home / ".cache/nyxuri-shell/quickshell/qmlcache"),
                                       "QS_PROBE_AUDIT": str(self.audit), "WAYLAND_DISPLAY": "wayland-test"})

    def test_wrapper_runtime_query_matches_actual_probe_and_keeps_cache(self):
        from nyxuri.desktop.shell_runtime import preflight_runtime
        runtime = self.runtime()
        cache = self.context.home / ".cache/nyxuri-shell/quickshell/qmlcache/sentinel"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"keep cache during preflight")
        with self.environment(), patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"), \
             patch("nyxuri.desktop.shell_runtime.DependencyProbe.installed", return_value=True) as installed:
            self.assertEqual(preflight_runtime(self.entry), "")
        audit = json.loads(self.audit.read_text())
        self.assertEqual(audit["argv"][:2], [str(runtime), "-p"])
        self.assertIn("import QtQuick.Controls", audit["qml"])
        self.assertEqual(audit["env"]["QT_QPA_PLATFORM"], "offscreen")
        self.assertNotIn("WAYLAND_DISPLAY", audit["env"])
        self.assertNotEqual(audit["env"]["HOME"], str(self.context.home))
        self.assertEqual(audit["env"]["QML_DISK_CACHE_PATH"], audit["env"]["HOME"] + "/cache/qmlcache")
        self.assertTrue(audit["env"]["DBUS_SESSION_BUS_ADDRESS"].startswith("unix:path=" + audit["env"]["HOME"]))
        requested = {entry.args[0] for entry in installed.call_args_list}
        self.assertIn("qml6-module-qtquick-controls", requested)
        self.assertIn("material-symbols-rounded-font", requested)
        self.assertIn("material-symbols-outlined-font", requested)
        self.assertEqual(cache.read_bytes(), b"keep cache during preflight")
        with self.assertRaises(ProcessLookupError):
            os.kill(audit["pid"], 0)

    def test_missing_runtime_or_qml_does_not_stop_old_shell(self):
        from nyxuri.desktop import shell_switcher
        from nyxuri.desktop.shell_runtime import preflight_runtime
        for scenario in ("runtime", "qml"):
            with self.subTest(scenario=scenario):
                if scenario == "qml":
                    self.runtime(mode="missing-import")
                with self.environment(), patch("nyxuri.desktop.shell_runtime.DependencyProbe.installed", return_value=True), \
                     patch("nyxuri.desktop.shell_switcher.stop_shell_process") as stop, \
                     patch("nyxuri.desktop.shell_switcher.stop_all_shell_instances") as sweep, \
                     patch("nyxuri.desktop.shell_switcher.spawn_shell") as spawn:
                    ok, message = shell_switcher.hot_switch_shell("nyxuri-shell", str(self.entry))
                self.assertFalse(ok)
                self.assertIn("Preflight failed", message)
                self.assertIn("qs" if scenario == "runtime" else "QtQuick.Controls", message)
                stop.assert_not_called()
                sweep.assert_not_called()
                spawn.assert_not_called()

    def test_probe_timeout_is_bounded_and_reaps_process(self):
        from nyxuri.desktop.shell_runtime import probe_qml_runtime
        runtime = self.runtime(mode="missing-import")
        # 同样经过真正的Popen边界，但不产生ready文件，复现导入卡住而进程仍存活。
        runtime.write_text("#!" + sys.executable + "\nimport os, time\nfrom pathlib import Path\n"
                           "Path(os.environ['QS_PROBE_AUDIT']).write_text(str(os.getpid()))\ntime.sleep(30)\n")
        with self.environment():
            start = time.monotonic()
            error = probe_qml_runtime(runtime, self.root, timeout=0.2)
            elapsed = time.monotonic() - start
        self.assertIn("did not become ready", error)
        self.assertLess(elapsed, 2.0)
        with self.assertRaises(ProcessLookupError):
            os.kill(int(self.audit.read_text()), 0)

    def test_missing_catalog_dependency_or_font_blocks_probe(self):
        from nyxuri.desktop.shell_runtime import preflight_runtime
        self.runtime()
        for missing in ("qml6-module-qtquick-controls", "material-symbols-outlined-font"):
            with self.subTest(missing=missing), self.environment(), \
                 patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"), \
                 patch("nyxuri.desktop.shell_runtime.DependencyProbe.installed", side_effect=lambda name: name != missing), \
                 patch("nyxuri.desktop.shell_runtime.probe_qml_runtime") as probe:
                error = preflight_runtime(self.entry)
                self.assertIn(missing, error)
                probe.assert_not_called()


class _ReadinessClock:
    """让慢启动和超时预算测试按模拟时间推进，不让测试实际等待几十秒。"""

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class TestShellReadinessBudgets(unittest.TestCase):
    def test_noctalia_default_budget_accepts_simulated_dbus_initialization_delay(self):
        from nyxuri.desktop import shell_switcher
        clock = _ReadinessClock()
        process = Mock()
        process.poll.return_value = None
        commands = []

        def ipc(command, *, timeout, **kwargs):
            self.assertEqual(command, ["noctalia", "msg", "theme-mode-get"])
            self.assertLessEqual(timeout, min(1.0, 30.0 - clock.now))
            commands.append(command)
            clock.now += min(timeout, 25.64 - clock.now)
            if clock.now >= 25.64:
                return subprocess.CompletedProcess(command, 0)
            raise subprocess.TimeoutExpired(command, timeout)

        with TempEnv(), patch.object(shell_switcher.time, "monotonic", clock.monotonic), \
             patch.object(shell_switcher.time, "sleep", clock.sleep), \
             patch.object(shell_switcher.subprocess, "run", side_effect=ipc):
            self.assertTrue(shell_switcher.wait_shell_ready("noctalia", process, "/usr/bin/noctalia"))
        self.assertGreater(clock.now, 4.0)
        self.assertLessEqual(clock.now, 30.0)
        self.assertGreater(len(commands), 1)

    def test_ipc_and_poll_sleep_use_only_remaining_total_budget(self):
        from nyxuri.desktop import shell_switcher
        for shell, command, limit in (("noctalia", ["noctalia", "msg", "theme-mode-get"], 1.0),
                                      ("nyxuri-shell", ["/fake/nyxuri-shell", "--check-ready"], 0.5)):
            for budget in (0.2, 0.28, 0.7):
                with self.subTest(shell=shell, budget=budget), TempEnv():
                    clock = _ReadinessClock()
                    process = Mock()
                    process.poll.return_value = None
                    def ipc(argv, *, timeout, **kwargs):
                        self.assertEqual(argv, command)
                        self.assertGreater(timeout, 0)
                        self.assertLessEqual(timeout, min(limit, budget - clock.now))
                        clock.now += min(0.1, timeout)
                        return subprocess.CompletedProcess(argv, 7)
                    with patch.object(shell_switcher.time, "monotonic", clock.monotonic), \
                         patch.object(shell_switcher.time, "sleep", clock.sleep), \
                         patch.object(shell_switcher.subprocess, "run", side_effect=ipc):
                        result = shell_switcher.wait_shell_ready(shell, process, "/fake/nyxuri-shell", timeout=budget)
                    self.assertIs(result, False)
                    self.assertAlmostEqual(clock.now, budget)

    def test_late_success_does_not_turn_expired_budget_into_ready(self):
        from nyxuri.desktop import shell_switcher
        clock = _ReadinessClock()
        process = Mock()
        process.poll.return_value = None
        def delayed_ipc(command, *, timeout, **kwargs):
            self.assertEqual(command, ["noctalia", "msg", "theme-mode-get"])
            self.assertEqual(timeout, 0.2)
            clock.now += timeout + 0.01
            return subprocess.CompletedProcess(command, 0)
        with TempEnv(), patch.object(shell_switcher.time, "monotonic", clock.monotonic), \
             patch.object(shell_switcher.subprocess, "run", side_effect=delayed_ipc), \
             patch.object(shell_switcher.time, "sleep") as sleep:
            self.assertIs(shell_switcher.wait_shell_ready("noctalia", process, "/usr/bin/noctalia", timeout=0.2), False)
        sleep.assert_not_called()

    def test_hot_switch_and_failed_target_rollback_both_allow_slow_noctalia(self):
        from nyxuri.desktop import shell_switcher
        from nyxuri.kernel import ledger
        for target in ("noctalia", "nyxuri-shell"):
            with self.subTest(target=target), TempEnv():
                clock = _ReadinessClock()
                previous = "nyxuri-shell" if target == "noctalia" else "noctalia"
                ledger.set_shell(previous, "/fake/nyxuri-shell" if previous == "nyxuri-shell" else None)
                started = {}
                def spawn(shell, executable):
                    self.assertEqual(executable, "/fake/" + shell)
                    started[shell] = clock.now
                    process = Mock(pid=1234 + len(started))
                    process.poll.return_value = None
                    return process
                def ipc(command, *, timeout, **kwargs):
                    if command == ["noctalia", "msg", "theme-mode-get"]:
                        self.assertLessEqual(timeout, min(1.0, started["noctalia"] + 30.0 - clock.now))
                        remaining_startup = started["noctalia"] + 25.64 - clock.now
                        clock.now += min(timeout, remaining_startup)
                        if clock.now >= started["noctalia"] + 25.64:
                            return subprocess.CompletedProcess(command, 0)
                    else:
                        self.assertEqual(command, ["/fake/nyxuri-shell", "--check-ready"])
                        self.assertLessEqual(timeout, min(0.5, started["nyxuri-shell"] + 4.0 - clock.now))
                        clock.now += timeout
                    raise subprocess.TimeoutExpired(command, timeout)
                with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
                     patch.object(shell_switcher, "preflight_shell", return_value=(True, "/fake/" + target, "")), \
                     patch.object(shell_switcher, "ensure_compositor_gateway_scripts"), \
                     patch.object(shell_switcher, "probe_running_shells", return_value=[(previous, 111)]), \
                     patch.object(shell_switcher, "resolve_shell_bin", return_value="/fake/nyxuri-shell"), \
                     patch.object(shell_switcher.shutil, "which", return_value="/fake/noctalia"), \
                     patch.object(shell_switcher, "is_shell_locked", return_value=False), \
                     patch.object(shell_switcher, "capture_active_theme_state", return_value=("dark", "")), \
                     patch.object(shell_switcher, "handoff_theme_state"), \
                     patch.object(shell_switcher, "stop_shell_process", return_value=True), \
                     patch.object(shell_switcher, "stop_all_shell_instances", return_value=True), \
                     patch.object(shell_switcher, "spawn_shell", side_effect=spawn), \
                     patch.object(shell_switcher.time, "monotonic", clock.monotonic), \
                     patch.object(shell_switcher.time, "sleep", clock.sleep), \
                     patch.object(shell_switcher.subprocess, "run", side_effect=ipc):
                    ok, message = shell_switcher.hot_switch_shell(target)
                self.assertEqual(ok, target == "noctalia", message)
                self.assertEqual(ledger.active_shell(), "noctalia")
                self.assertIn("30.0s", message)
                if target == "nyxuri-shell":
                    self.assertIn("within 4.0s", message)
                    self.assertIn("Successfully recovered", message)
                self.assertAlmostEqual(clock.now - started["noctalia"], 25.64)

    def test_spawn_failure_checks_restored_noctalia_with_its_full_budget(self):
        from nyxuri.desktop import shell_switcher
        restored = Mock()
        with TempEnv(), patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
             patch.object(shell_switcher, "preflight_shell", return_value=(True, "/fake/nyxuri-shell", "")), \
             patch.object(shell_switcher, "ensure_compositor_gateway_scripts"), \
             patch.object(shell_switcher, "probe_running_shells", return_value=[("noctalia", 111)]), \
             patch.object(shell_switcher.shutil, "which", return_value="/fake/noctalia"), \
             patch.object(shell_switcher, "is_shell_locked", return_value=False), \
             patch.object(shell_switcher, "capture_active_theme_state", return_value=("dark", "")), \
             patch.object(shell_switcher, "handoff_theme_state"), \
             patch.object(shell_switcher, "stop_shell_process", return_value=True), \
             patch.object(shell_switcher, "stop_all_shell_instances", return_value=True), \
             patch.object(shell_switcher, "spawn_shell", side_effect=[OSError("spawn failed"), restored]), \
             patch.object(shell_switcher, "wait_shell_ready", return_value=True) as ready:
            ok, message = shell_switcher.hot_switch_shell("nyxuri-shell")
        self.assertFalse(ok)
        ready.assert_called_once_with("noctalia", restored, "/fake/noctalia", timeout=30.0)
        self.assertIn("successfully recovered noctalia", message)
        self.assertIn("30.0s", message)
