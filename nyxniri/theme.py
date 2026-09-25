"""Desktop theme synchronization without a shell-script dependency."""

import configparser
import fcntl
import os
import shutil
import subprocess
from pathlib import Path

from nyxniri.core import get_env


def _mode_from_system() -> str:
    if shutil.which("gsettings"):
        try:
            value = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"], capture_output=True, text=True, timeout=5, check=False).stdout
            return "light" if "prefer-light" in value or "default" in value else "dark"
        except (OSError, subprocess.SubprocessError):
            pass
    return os.environ.get("NYXNIRI_DEFAULT_MODE", "dark")


def _write_ini(path: Path, key: str, value: str) -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if path.is_file():
        parser.read(path, encoding="utf-8")
    if not parser.has_section("Settings"):
        parser.add_section("Settings")
    parser.set("Settings", key, value)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    os.replace(tmp, path)


def sync(mode: str = "sync") -> int:
    env = get_env()
    lock = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"nyxniri-{os.getuid()}-theme-sync.lock"
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = lock.open("w")
    except OSError:
        lock = env.state_dir / "theme-sync.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = lock.open("w")
    with lock_handle as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        current = _mode_from_system() if mode in ("toggle", "sync") else mode
        if mode == "toggle":
            current = "light" if current == "dark" else "dark"
        current = "light" if current == "light" else "dark"
        dark = current == "dark"
        gtk = os.environ.get("NYXNIRI_GTK_THEME_DARK" if dark else "NYXNIRI_GTK_THEME_LIGHT", "adw-gtk3-dark" if dark else "adw-gtk3")
        if shutil.which("gsettings"):
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark" if dark else "prefer-light"], check=False, timeout=5)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", gtk], check=False, timeout=5)
        for version in ("gtk-3.0", "gtk-4.0"):
            path = env.config_dir / version / "settings.ini"
            _write_ini(path, "gtk-application-prefer-dark-theme", "true" if dark else "false")
            _write_ini(path, "gtk-theme-name", gtk)
        return 0
