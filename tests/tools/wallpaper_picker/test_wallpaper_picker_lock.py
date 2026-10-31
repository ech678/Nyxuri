"""Contract tests for the wallpaper picker lock.py — PID-file toggle-close must
only signal a verifiable picker process (same uid + known entry script), never
an arbitrary PID planted in the runtime dir. _is_picker_process is validated
against REAL subprocess /proc cmdline, not a mock of itself.
"""

import importlib.util
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import call, patch

_LOCK = (
    Path(__file__).resolve().parents[3]
    / "plugins" / "noctalia" / "tools" / "wallpaper_picker" / "lock.py"
)


def _load_lock():
    spec = importlib.util.spec_from_file_location("picker_lock_under_test", _LOCK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _ProcCase(unittest.TestCase):
    def setUp(self):
        self.lock = _load_lock()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.pid_file = self.tmp / "picker-test.pid"
        self._procs = []

    def tearDown(self):
        for proc in self._procs:
            proc.kill()
            proc.wait()
        self._tmp.cleanup()

    def _spawn_and_wait(self, argv, needle):
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

    def _spawn_picker_sleeper(self, name):
        script = self.tmp / name
        script.write_text("import time; time.sleep(30)\n")
        return self._spawn_and_wait([sys.executable, str(script)], str(script))

    def _held_lock(self):
        lock_file = self.tmp / "picker-test.lock"
        lock_file.write_text("")
        return str(lock_file)


class TestIsPickerProcess(_ProcCase):

    def test_rejects_non_positive_pid(self):
        self.assertFalse(self.lock._is_picker_process(0))
        self.assertFalse(self.lock._is_picker_process(1))
        self.assertFalse(self.lock._is_picker_process(-5))

    def test_rejects_missing_process(self):
        self.assertFalse(self.lock._is_picker_process(10 ** 9))

    def test_accepts_picker_entry_shape(self):
        proc = self._spawn_picker_sleeper("wallpaper-picker.py")
        self.assertTrue(self.lock._is_picker_process(proc.pid))

    def test_rejects_unrelated_python_process(self):
        proc = self._spawn_and_wait(
            [sys.executable, "-c", "import time; time.sleep(30)"], "time.sleep(30)"
        )
        self.assertFalse(self.lock._is_picker_process(proc.pid))


class TestToggleCloseGuard(_ProcCase):

    def test_garbage_pid_file_never_signals(self):
        self.pid_file.write_text("rm -rf /")
        with patch.object(self.lock.os, "kill") as mock_kill, \
             patch.object(self.lock.sys, "exit") as mock_exit, \
             patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
            self.lock.acquire_instance_lock(self._held_lock(), str(self.pid_file))
        mock_kill.assert_not_called()
        mock_exit.assert_called_once_with(0)

    def test_unrelated_pid_never_signals(self):
        proc = self._spawn_and_wait(
            [sys.executable, "-c", "import time; time.sleep(30)"], "time.sleep(30)"
        )
        self.pid_file.write_text(str(proc.pid))
        with patch.object(self.lock.os, "kill") as mock_kill, \
             patch.object(self.lock.sys, "exit") as mock_exit, \
             patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
            self.lock.acquire_instance_lock(self._held_lock(), str(self.pid_file))
        mock_kill.assert_not_called()
        mock_exit.assert_called_once_with(0)

    def test_verified_picker_pid_gets_sigterm(self):
        proc = self._spawn_picker_sleeper("wallpaper-picker.py")
        self.pid_file.write_text(str(proc.pid))
        with patch.object(self.lock.os, "kill") as mock_kill, \
             patch.object(self.lock.sys, "exit") as mock_exit, \
             patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
            self.lock.acquire_instance_lock(self._held_lock(), str(self.pid_file))
        self.assertEqual(mock_kill.call_args_list[0], call(proc.pid, self.lock.signal.SIGTERM))
        mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
