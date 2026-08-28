"""Contract tests for orbit lock.py — PID-file toggle-close must only signal
a verifiable orbit launcher process (same uid + known entry script), never an
arbitrary PID planted in the runtime dir.
"""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

_LOCK = Path(__file__).resolve().parent.parent / "configs" / "niri" / "scripts" / "orbit" / "lock.py"


def _load_lock():
    spec = importlib.util.spec_from_file_location("orbit_lock_under_test", _LOCK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestIsOrbitProcess(unittest.TestCase):

    def setUp(self):
        self.lock = _load_lock()

    def test_rejects_non_positive_pid(self):
        self.assertFalse(self.lock._is_orbit_process(0))
        self.assertFalse(self.lock._is_orbit_process(1))
        self.assertFalse(self.lock._is_orbit_process(-5))

    def test_rejects_missing_process(self):
        self.assertFalse(self.lock._is_orbit_process(10 ** 9))


class TestToggleCloseGuard(unittest.TestCase):

    def setUp(self):
        self.lock = _load_lock()
        self.pid_file = Path(self.lock.os.environ.get("TMPDIR", "/tmp")) / "orbit-test.pid"

    def tearDown(self):
        self.pid_file.unlink(missing_ok=True)

    def _held_lock(self, tmp):
        lock_file = tmp / "orbit-test.lock"
        lock_file.write_text("")
        return str(lock_file)

    def test_garbage_pid_file_never_signals(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            self.pid_file.write_text("rm -rf /")
            with patch.object(self.lock.os, "kill") as mock_kill, \
                 patch.object(self.lock.sys, "exit") as mock_exit, \
                 patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
                self.lock.acquire_instance_lock(self._held_lock(Path(td)), str(self.pid_file))
            mock_kill.assert_not_called()
            mock_exit.assert_called_once_with(0)

    def test_foreign_pid_never_signals(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            self.pid_file.write_text("4242")
            with patch.object(self.lock, "_is_orbit_process", return_value=False), \
                 patch.object(self.lock.os, "kill") as mock_kill, \
                 patch.object(self.lock.sys, "exit") as mock_exit, \
                 patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
                self.lock.acquire_instance_lock(self._held_lock(Path(td)), str(self.pid_file))
            mock_kill.assert_not_called()
            mock_exit.assert_called_once_with(0)

    def test_verified_orbit_pid_gets_sigterm(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            self.pid_file.write_text("4242")
            with patch.object(self.lock, "_is_orbit_process", return_value=True), \
                 patch.object(self.lock.os, "kill") as mock_kill, \
                 patch.object(self.lock.sys, "exit") as mock_exit, \
                 patch.object(self.lock.fcntl, "flock", side_effect=BlockingIOError):
                self.lock.acquire_instance_lock(self._held_lock(Path(td)), str(self.pid_file))
            mock_kill.assert_called_once_with(4242, self.lock.signal.SIGTERM)
            mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
