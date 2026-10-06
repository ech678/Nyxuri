"""Desktop theme synchronization without a shell-script dependency.

Propagation order: Noctalia IPC (when its daemon answers), then the Nyxuri
Shell ``theme`` IPC (when a running instance is resolvable), then system-level
sync only. Every child call captures stderr so a dead daemon can never leak a
raw ``error:`` line into interactive output; the final summary line states the
channel that received the change.
"""

import configparser
import fcntl
import os
import shutil
import sys
import time
from pathlib import Path

from nyxuri.constants import get_compat_env
from nyxuri.core import get_env, timed_run


def _mode_from_system() -> str:
    if shutil.which("noctalia"):
        res = timed_run(["noctalia", "msg", "theme-mode-get"], 3, capture_output=True, text=True, check=False)
        if res is not None and res.returncode == 0:
            val = res.stdout.strip()
            if val in ("dark", "light"):
                return val
    if shutil.which("gsettings"):
        res = timed_run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"], 5, capture_output=True, text=True, check=False)
        if res is not None and res.returncode == 0:
            return "light" if "prefer-light" in res.stdout or "default" in res.stdout else "dark"
    return get_compat_env("DEFAULT_MODE", "dark")


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


def _noctalia_available() -> bool:
    """True only when the Noctalia daemon answers, not merely installed."""
    if not shutil.which("noctalia"):
        return False
    res = timed_run(["noctalia", "msg", "status"], 3, capture_output=True, text=True, check=False)
    return res is not None and res.returncode == 0


def _nyxuri_shell_dir() -> Path | None:
    """Resolve the running Nyxuri Shell tree from its recorded binary."""
    try:
        from nyxuri.shell_switcher import resolve_custom_bin
    except Exception:
        return None
    try:
        resolved = resolve_custom_bin()
    except Exception:
        return None
    if not resolved:
        return None
    binary = Path(resolved).resolve()
    for candidate in (binary.parent, binary.parent.parent):
        if (candidate / "shell.qml").is_file():
            return candidate
    return None


def _nyxuri_shell_ipc(args: "list[str]", timeout: float = 3.0) -> "str | None":
    """Call the Nyxuri Shell IPC; None when qs, the binary, or IPC is absent."""
    if not shutil.which("qs"):
        return None
    shell_dir = _nyxuri_shell_dir()
    if shell_dir is None:
        return None
    res = timed_run(["qs", "-p", str(shell_dir), "ipc", "call", *args], timeout,
                    capture_output=True, text=True, check=False)
    if res is not None and res.returncode == 0:
        return res.stdout.strip()
    return None


def _propagate(mode: str, toggle: bool) -> str:
    """Hand the mode change to the shell that owns the runtime theme.

    Returns the channel name for feedback: "noctalia", "nyxuri-shell" or
    "none". Toggle callers may read back the resulting mode afterwards.
    """
    if toggle:
        if _noctalia_available():
            timed_run(["noctalia", "msg", "theme-mode-toggle"], 3, capture_output=True, text=True, check=False)
            time.sleep(0.3)
            return "noctalia"
        if _nyxuri_shell_ipc(["theme", "toggle"]) is not None:
            time.sleep(0.2)
            return "nyxuri-shell"
        return "none"
    if _noctalia_available():
        timed_run(["noctalia", "msg", "theme-mode-set", mode], 3, capture_output=True, text=True, check=False)
        return "noctalia"
    if _nyxuri_shell_ipc(["theme", "set", mode]) is not None:
        return "nyxuri-shell"
    return "none"


def _sync_glow_layout(current: str) -> None:
    """Swap the fixed-glow niri layout for the active mode, then reload niri.

    Mirrors theme-sync.sh: only runs when the glow preset is active and the
    per-mode layout file exists; identical bytes are a no-op.
    """
    env = get_env()
    active = env.presets_dir / "niri.active"
    for legacy in (env.config_dir / "nyxniri" / "presets" / "niri.active",
                   env.config_dir / "NyxNiri" / "presets" / "niri.active"):
        if not active.is_file() and legacy.is_file():
            active = legacy
    if not active.is_file():
        return
    if active.read_text(encoding="utf-8").strip() != "glow":
        return
    niri_dir = env.config_dir / "niri"
    source = niri_dir / f"layout-{current}.kdl"
    dest = niri_dir / "layout.kdl"
    if not source.is_file():
        return
    if dest.is_file() and dest.read_bytes() == source.read_bytes():
        return
    tmp = dest.with_name(f".layout.kdl.{os.getpid()}.tmp")
    tmp.write_bytes(source.read_bytes())
    os.replace(tmp, dest)
    if shutil.which("niri"):
        timed_run(["niri", "msg", "action", "load-config-file"], 3, capture_output=True, text=True, check=False)


def status() -> int:
    scheme = "unknown"
    if shutil.which("gsettings"):
        res = timed_run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"], 5, capture_output=True, text=True, check=False)
        if res is not None and res.returncode == 0:
            scheme = res.stdout.strip().strip("'") or "unknown"
    noctalia_mode = "unknown"
    if shutil.which("noctalia"):
        res = timed_run(["noctalia", "msg", "theme-mode-get"], 5, capture_output=True, text=True, check=False)
        if res is not None and res.returncode == 0:
            noctalia_mode = res.stdout.strip() or "unknown"
    print(f"Current Scheme: {scheme} | Noctalia Mode: {noctalia_mode}")
    return 0


def sync(mode: str = "sync") -> int:
    env = get_env()
    lock = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"nyxuri-{os.getuid()}-theme-sync.lock"
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

        channel = "none"
        current: str
        if mode == "toggle":
            channel = _propagate("", True)
            if channel == "noctalia":
                current = _mode_from_system()
            elif channel == "nyxuri-shell":
                readback = _nyxuri_shell_ipc(["theme", "status"])
                current = readback if readback in ("dark", "light") else _mode_from_system()
            else:
                current = _mode_from_system()
            current = "light" if current == "dark" else "dark"
        elif mode in ("dark", "light"):
            current = mode
            channel = _propagate(mode, False)
        else:
            current = _mode_from_system()
        current = "light" if current == "light" else "dark"
        dark = current == "dark"
        scheme_val = "prefer-dark" if dark else "prefer-light"
        gtk = get_compat_env("GTK_THEME_DARK" if dark else "GTK_THEME_LIGHT", "adw-gtk3-dark" if dark else "adw-gtk3")
        if shutil.which("gsettings"):
            timed_run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme_val], 5, check=False)
            timed_run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", gtk], 5, check=False)
        for version in ("gtk-3.0", "gtk-4.0"):
            path = env.config_dir / version / "settings.ini"
            _write_ini(path, "gtk-application-prefer-dark-theme", "true" if dark else "false")
            _write_ini(path, "gtk-theme-name", gtk)

        # Qt/Kvantum applications follow only when the theme is installed.
        kvantum = get_compat_env("KVANTUM_DARK" if dark else "KVANTUM_LIGHT",
                                 "KvLibadwaitaDark" if dark else "KvLibadwaita")
        kvantum_config = env.config_dir / "Kvantum" / "kvantum.kvconfig"
        if kvantum and ((Path("/usr/share/Kvantum") / kvantum).is_dir() or (env.config_dir / "Kvantum" / kvantum).is_dir()):
            _write_ini(kvantum_config, "theme", kvantum)

        _sync_glow_layout(current)

        # Notify Kitty terminal
        if shutil.which("pkill"):
            timed_run(["pkill", "-SIGUSR1", "-x", "kitty"], 2, check=False)

        if sys.stdout.isatty() and mode != "sync":
            channel_label = {"noctalia": "shell: noctalia",
                             "nyxuri-shell": "shell: nyxuri",
                             "none": "shell: none running"}.get(channel, channel)
            print(f"Theme synced to: {current} (Scheme: {scheme_val}, GTK: {gtk}, {channel_label})")
        return 0
