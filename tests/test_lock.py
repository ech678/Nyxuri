"""Regression tests for the process-wide CLI lock."""

import os
import selectors
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


_LOCK_CHILD = """
import os
from nyxniri.core import acquire_lock

acquire_lock()
ready_fd = os.environ.get("READY_FD")
if ready_fd:
    os.write(int(ready_fd), b"ready\\n")
    os.close(int(ready_fd))
release_fd = os.environ.get("RELEASE_FD")
if release_fd:
    os.read(int(release_fd), 1)
"""


class TestCliLock(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self._repo = Path(__file__).resolve().parent.parent

    def tearDown(self):
        self._ctx.__exit__()

    def _child_env(self, **extra):
        env = os.environ.copy()
        env.update(
            HOME=str(self._ctx.env.home),
            XDG_STATE_HOME=str(self._ctx.env.home / ".local" / "state"),
            PYTHONPATH=str(self._repo),
            **extra,
        )
        return env

    def _start_holder(self):
        ready_r, ready_w = os.pipe()
        release_r, release_w = os.pipe()
        proc = subprocess.Popen(
            [sys.executable, "-c", _LOCK_CHILD],
            cwd=self._repo,
            env=self._child_env(READY_FD=str(ready_w), RELEASE_FD=str(release_r)),
            pass_fds=(ready_w, release_r),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        os.close(ready_w)
        os.close(release_r)
        selector = selectors.DefaultSelector()
        selector.register(ready_r, selectors.EVENT_READ)
        try:
            self.assertTrue(selector.select(timeout=5), "lock holder did not start")
            self.assertEqual(os.read(ready_r, 64), b"ready\n")
        finally:
            selector.close()
            os.close(ready_r)
        self.assertIsNone(proc.poll(), "lock holder exited before synchronization")
        return proc, release_w

    def _try_lock(self):
        return subprocess.run(
            [sys.executable, "-c", _LOCK_CHILD],
            cwd=self._repo,
            env=self._child_env(),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def _stop_holder(self, proc, release_fd):
        try:
            os.write(release_fd, b"x")
        except BrokenPipeError:
            pass
        finally:
            os.close(release_fd)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()

    def test_failed_competitors_do_not_remove_active_lock(self):
        holder, release_w = self._start_holder()
        lock_path = self._ctx.env.state_dir / "nyxniri.lock"
        try:
            self.assertTrue(lock_path.is_file())

            second = self._try_lock()
            self.assertEqual(second.returncode, 1)
            self.assertTrue(lock_path.is_file(), "failed competitor removed lock path")

            third = self._try_lock()
            self.assertEqual(third.returncode, 1)
            self.assertTrue(lock_path.is_file(), "second competitor removed lock path")
        finally:
            self._stop_holder(holder, release_w)
        self.assertEqual(holder.returncode, 0)

        fourth, release_fourth = self._start_holder()
        try:
            self.assertTrue(lock_path.is_file())
        finally:
            self._stop_holder(fourth, release_fourth)
        self.assertEqual(fourth.returncode, 0)
        self.assertTrue(lock_path.is_file(), "normal release must keep lock path")

    def test_release_closes_fd_if_unlock_fails(self):
        import nyxniri.core as core

        core.acquire_lock()
        held_fd = core._LOCK_FD
        with patch("nyxniri.core.fcntl.flock", side_effect=OSError), \
             patch("nyxniri.core.os.close", wraps=os.close) as close:
            core.release_lock()
        close.assert_called_once_with(held_fd)
        self.assertIsNone(core._LOCK_FD)
        self.assertFalse(core._LOCK_ACQUIRED)
        self.assertTrue(self._ctx.env.state_dir.joinpath("nyxniri.lock").is_file())
        self.assertIsNotNone(held_fd)

    def test_failed_acquire_closes_fd_and_clears_state(self):
        import nyxniri.core as core

        with patch("nyxniri.core.os.open", return_value=17), \
             patch("nyxniri.core.fcntl.flock", side_effect=BlockingIOError), \
             patch("nyxniri.core.os.close") as close, \
             patch("nyxniri.core.sys.exit", side_effect=SystemExit(1)):
            with self.assertRaises(SystemExit):
                core.acquire_lock()
        close.assert_called_once_with(17)
        self.assertIsNone(core._LOCK_FD)
        self.assertFalse(core._LOCK_ACQUIRED)


if __name__ == "__main__":
    unittest.main()
