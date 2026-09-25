"""
NyxNiri Wallpaper Picker Single-Instance & True-Toggle Locking Engine
Ensures atomic single-instance execution. If another instance is running, sends SIGTERM to toggle-close it.
"""

import os
import sys
import time
import signal
import fcntl


def acquire_instance_lock(lock_path: str, pid_path: str) -> int:
    """Acquire single-instance file lock. Toggle-close existing instance if detected."""
    lock_fd = None
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except Exception:
                pass
        if os.path.isfile(pid_path):
            try:
                with open(pid_path, "r") as pf:
                    old_pid = int(pf.read().strip())
                os.kill(old_pid, signal.SIGTERM)
                # Poll to wait for old instance to clean up and exit (up to 500ms)
                for _ in range(50):
                    time.sleep(0.01)
                    try:
                        os.kill(old_pid, 0)
                    except OSError:
                        break
            except Exception:
                pass
        sys.exit(0)

    try:
        with open(pid_path, "w") as pf:
            pf.write(str(os.getpid()))
    except Exception:
        pass

    return lock_fd


def release_instance_lock(lock_fd: int, pid_path: str):
    """Release file lock and clean up PID file."""
    try:
        if os.path.isfile(pid_path):
            os.remove(pid_path)
    except Exception:
        pass
    try:
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except Exception:
        pass
