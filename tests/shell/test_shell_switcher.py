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


class TestShellSwitcherClassification(unittest.TestCase):

    def test_third_party_quickshell_is_not_nyxuri_shell(self):
        from nyxuri.system import shell as shell_switcher
        with TempEnv():
            cmdline = b"quickshell\x00-p\x00/home/u/.config/quickshell\x00"
            real_read = Path.read_bytes
            with patch.object(shell_switcher, "find_pids",
                              side_effect=lambda pat: [4242] if pat in ("qs", "quickshell") else []), \
                 patch.object(Path, "read_bytes",
                              lambda self: cmdline if str(self) == "/proc/4242/cmdline" else real_read(self)):
                self.assertEqual(shell_switcher.probe_running_shells(), [])

    def test_already_active_keeps_the_running_bin(self):
        from nyxuri.system import shell as shell_switcher
        from nyxuri.state.store import custom_shell_bin, set_shell
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
        from nyxuri.system import shell as shell_switcher
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
        from nyxuri.system import shell as shell_switcher
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
                "from nyxuri.system import shell as shell_switcher\n"
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
