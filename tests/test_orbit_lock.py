"""Contract tests for orbit lock.py — PID-file toggle-close must only signal
a verifiable orbit launcher process (same uid + known entry script), never an
arbitrary PID planted in the runtime dir. _is_orbit_process is validated
against REAL subprocess /proc cmdline, not a mock of itself.
"""

import importlib.util
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_LOCK = Path(__file__).resolve().parent.parent / "configs" / "niri" / "scripts" / "orbit" / "lock.py"


def _load_lock():
    spec = importlib.util.spec_from_file_location("orbit_lock_under_test", _LOCK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _ProcCase(unittest.TestCase):
    """Base: temp pid/lock files and real subprocesses, killed in tearDown."""

    def setUp(self):
        self.lock = _load_lock()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.pid_file = self.tmp / "orbit-test.pid"
        self._procs = []

    def tearDown(self):
        for proc in self._procs:
            proc.kill()
            proc.wait()
        self._tmp.cleanup()

    def _spawn_and_wait(self, argv, needle):
        """Spawn a real process and wait for the kernel to publish its argv.

        /proc/<pid>/cmdline is often still empty immediately after Popen
        returns; the wait only makes the test deterministic — the real
        toggle-close always inspects processes that are long past spawn.
        """
        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._procs.append(proc)
        needle = needle.encode() if isinstance(needle, str) else needle
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                with open(f"/proc/{proc.pid}/cmdline", "rb") as cf:
                    if needle in cf.read():
                        return proc
            except OSError:
                break
            time.sleep(0.01)
        self.fail(f"/proc/{proc.pid}/cmdline never published {needle!r}")

    def _spawn_orbit_sleeper(self, name):
        # Real orbit runs via shebang/wrapper: argv[0] is the interpreter,
        # the entry script path is argv[1] — spawn matches that exact shape.
        script = self.tmp / name
        script.write_text("import time; time.sleep(30)\n")
        return self._spawn_and_wait([sys.executable, str(script)], str(script))

    def _held_lock(self):
        lock_file = self.tmp / "orbit-test.lock"
        lock_file.write_text("")
        return str(lock_file)


class TestIsOrbitProcess(_ProcCase):

    def test_rejects_non_positive_pid(self):
        self.assertFalse(self.lock._is_orbit_process(0))
        self.assertFalse(self.lock._is_orbit_process(1))
        self.assertFalse(self.lock._is_orbit_process(-5))

    def test_rejects_missing_process(self):
        self.assertFalse(self.lock._is_orbit_process(10 ** 9))

    def test_accepts_orbit_launcher_shape(self):
        proc = self._spawn_orbit_sleeper("orbit-launcher.py")
        self.assertTrue(self.lock._is_orbit_process(proc.pid))

    def test_accepts_scratch_menu_wrapper_shape(self):
        proc = self._spawn_orbit_sleeper("niri-scratch-menu.py")
        self.assertTrue(self.lock._is_orbit_process(proc.pid))

    def test_rejects_unrelated_python_process(self):
        proc = self._spawn_and_wait(
            [sys.executable, "-c", "import time; time.sleep(30)"], "time.sleep(30)"
        )
        self.assertFalse(self.lock._is_orbit_process(proc.pid))


class TestToggleCloseGuard(_ProcCase):

    def test_garbage_pid_file_never_signals(self):
        self.pid_file.write_text("rm -rf /")
        with patch.object(self.lock.os, "kill") as mock_kill, \
             patch.object(self.lock.sys, "exit") as mock_exit, \
             patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
            self.lock.acquire_instance_lock(self._held_lock(), str(self.pid_file))
        mock_kill.assert_not_called()
        mock_exit.assert_called_once_with(0)

    def test_nonexistent_pid_never_signals(self):
        self.pid_file.write_text("4242")
        with patch.object(self.lock.os, "kill") as mock_kill, \
             patch.object(self.lock.sys, "exit") as mock_exit, \
             patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
            self.lock.acquire_instance_lock(self._held_lock(), str(self.pid_file))
        mock_kill.assert_not_called()
        mock_exit.assert_called_once_with(0)

    def test_verified_orbit_pid_gets_sigterm(self):
        # Real process, real /proc lookup — _is_orbit_process stays unpatched.
        proc = self._spawn_orbit_sleeper("orbit-launcher.py")
        self.pid_file.write_text(str(proc.pid))
        with patch.object(self.lock.os, "kill") as mock_kill, \
             patch.object(self.lock.sys, "exit") as mock_exit, \
             patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
            self.lock.acquire_instance_lock(self._held_lock(), str(self.pid_file))
        mock_kill.assert_called_once_with(proc.pid, self.lock.signal.SIGTERM)
        mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
