#!/usr/bin/env python3
"""
NyxNiri M3E Wallpaper Picker
Zero-Daemon Stateless Wayland Layer-Shell Wallpaper Selector & Live Video Wallpaper Manager.
"""

import sys
import os
import signal
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk

# Add current scripts directory to sys.path to load local wallpaper_picker package
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from wallpaper_picker.lock import acquire_instance_lock, release_instance_lock
from wallpaper_picker.window import WallpaperPickerWindow

RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/nyxniri-{os.getuid()}"
os.makedirs(RUNTIME_DIR, exist_ok=True)
LOCK_FILE_PATH = os.path.join(RUNTIME_DIR, "nyxniri-wallpaper-picker.lock")
PID_FILE_PATH = os.path.join(RUNTIME_DIR, "nyxniri-wallpaper-picker.pid")


def main():
    lock_fd = acquire_instance_lock(LOCK_FILE_PATH, PID_FILE_PATH)
    state = {"win": None, "quit": False}

    def handle_signal(signum, frame):
        # Absorb SIGTERM/SIGINT at any stage: toggle-close from a rapid
        # re-launch can arrive while the window is still constructing.
        if state["win"] is not None:
            state["win"].dismiss_window()
        else:
            state["quit"] = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    win = WallpaperPickerWindow(lock_fd=lock_fd, pid_path=PID_FILE_PATH)
    state["win"] = win

    try:
        if state["quit"]:
            win.dismiss_window()
        Gtk.main()
    finally:
        release_instance_lock(lock_fd, PID_FILE_PATH)


if __name__ == "__main__":
    main()
