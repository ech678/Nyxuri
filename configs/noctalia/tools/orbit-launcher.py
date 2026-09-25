#!/usr/bin/env python3
"""
NyxNiri Orbit Launcher (星环启动器)
Zero-Daemon Stateless Radial App Launcher & Gemini Search Hub for Niri / Wayland Layer-Shell.
"""

import sys
import os
import signal
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk

# Add current scripts directory to sys.path to load local orbit package
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from orbit.lock import acquire_instance_lock, release_instance_lock
from orbit.window import OrbitLauncher

RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/nyxniri-{os.getuid()}"
os.makedirs(RUNTIME_DIR, exist_ok=True)
LOCK_FILE_PATH = os.path.join(RUNTIME_DIR, "nyxniri-orbit-launcher.lock")
PID_FILE_PATH = os.path.join(RUNTIME_DIR, "nyxniri-orbit-launcher.pid")


def main():
    lock_fd = acquire_instance_lock(LOCK_FILE_PATH, PID_FILE_PATH)
    win = OrbitLauncher(lock_fd=lock_fd, pid_path=PID_FILE_PATH)

    def handle_signal(signum, frame):
        win.dismiss_menu()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        Gtk.main()
    finally:
        release_instance_lock(lock_fd, PID_FILE_PATH)


if __name__ == "__main__":
    main()
