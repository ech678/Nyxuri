"""Desktop theme synchronization without a shell-script dependency."""

import configparser
import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path

from nyxniri.core import get_env, timed_run


def _mode_from_system() -> str:
    if shutil.which("noctalia"):
        try:
            res = subprocess.run(["noctalia", "msg", "theme-mode-get"], capture_output=True, text=True, timeout=3, check=False)
            val = res.stdout.strip()
            if val in ("dark", "light"):
                return val
        except (OSError, subprocess.SubprocessError):
            pass
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


def status() -> int:
    scheme = "unknown"
    if shutil.which("gsettings"):
        try:
            res = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"], capture_output=True, text=True, timeout=5, check=False)
            scheme = res.stdout.strip().strip("'") or "unknown"
        except (OSError, subprocess.SubprocessError):
            pass
    noctalia_mode = "unknown"
    if shutil.which("noctalia"):
        try:
            res = subprocess.run(["noctalia", "msg", "theme-mode-get"], capture_output=True, text=True, timeout=5, check=False)
            noctalia_mode = res.stdout.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            pass
    print(f"Current Scheme: {scheme} | Noctalia Mode: {noctalia_mode}")
    return 0


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

        # If user explicitly requested toggle or set mode via CLI, propagate to Noctalia
        if mode == "toggle" and shutil.which("noctalia"):
            timed_run(["noctalia", "msg", "theme-mode-toggle"], 3, check=False)
        elif mode in ("dark", "light") and shutil.which("noctalia"):
            timed_run(["noctalia", "msg", "theme-mode-set", mode], 3, check=False)

        current = _mode_from_system() if mode in ("toggle", "sync") else mode
        if mode == "toggle":
            current = "light" if current == "dark" else "dark"
        current = "light" if current == "light" else "dark"
        dark = current == "dark"
        scheme_val = "prefer-dark" if dark else "prefer-light"
        gtk = os.environ.get("NYXNIRI_GTK_THEME_DARK" if dark else "NYXNIRI_GTK_THEME_LIGHT", "adw-gtk3-dark" if dark else "adw-gtk3")
        if shutil.which("gsettings"):
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme_val], check=False, timeout=5)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", gtk], check=False, timeout=5)
        for version in ("gtk-3.0", "gtk-4.0"):
            path = env.config_dir / version / "settings.ini"
            _write_ini(path, "gtk-application-prefer-dark-theme", "true" if dark else "false")
            _write_ini(path, "gtk-theme-name", gtk)

        # Notify Kitty terminal
        if shutil.which("pkill"):
            timed_run(["pkill", "-SIGUSR1", "-x", "kitty"], 2, check=False)

        if sys.stdout.isatty() and mode != "sync":
            print(f"Theme synced to: {current} (Scheme: {scheme_val}, GTK: {gtk})")
        return 0
