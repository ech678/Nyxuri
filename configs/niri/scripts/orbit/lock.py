"""
Orbit Launcher Single-Instance & True-Toggle Locking Engine
Ensures atomic single-instance execution. If another instance is running, sends SIGTERM to toggle-close it.
"""

import os
import sys
import signal
import fcntl

# A PID file at a predictable path may hold anything; only trust a signal if
# the target process is verifiably one of ours (same uid + known entry script).
_ORBIT_ENTRY_NAMES = {"orbit-launcher.py", "niri-scratch-menu.py"}


def _is_orbit_process(pid: int) -> bool:
    """True only for a live orbit launcher instance owned by this user."""
    if pid <= 1:
        return False
    proc = f"/proc/{pid}"
    try:
        if os.stat(proc).st_uid != os.getuid():
            return False
        with open(f"{proc}/cmdline", "rb") as cf:
            argv = [a.decode("utf-8", "replace") for a in cf.read().split(b"\0") if a]
    except OSError:
        return False
    # argv[0] is the interpreter for shebang-launched scripts; the entry script
    # shows up anywhere in argv (direct spawn, wrapper execv, extra flags).
    return any(os.path.basename(arg) in _ORBIT_ENTRY_NAMES for arg in argv)


def acquire_instance_lock(lock_path: str, pid_path: str) -> int:
    """Acquire single-instance file lock. Toggle-close existing instance if detected."""
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        if os.path.isfile(pid_path):
            try:
                with open(pid_path, "r") as pf:
                    old_pid = int(pf.read().strip())
                if _is_orbit_process(old_pid):
                    os.kill(old_pid, signal.SIGTERM)
            except (ValueError, OSError):
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
