import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nyxuri_shell import ipc, state as S

ACTION_EXIT_OK = 0
ACTION_EXIT_UNKNOWN = 1
ACTION_EXIT_NO_DAEMON = 2
ACTION_EXIT_FAILED = 3

STANDARD_ACTIONS = (
    "launcher",
    "session",
    "settings",
    "clipboard",
    "lock",
    "wallpaper-random",
    "wallpaper-picker",
    "radial-launcher",
)

DAEMON_ACTIONS = {
    "launcher": "panel-toggle",
    "session": "panel-toggle",
    "settings": "settings-toggle",
    "clipboard": "panel-toggle",
    "lock": "session-lock",
    "wallpaper-random": "wallpaper-random",
    "wallpaper-picker": "wallpaper-picker",
    "radial-launcher": "radial-launcher",
}

EXTERNAL_FALLBACKS: Dict[str, Tuple[str, ...]] = {
    "launcher": ("fuzzel", "wofi", "rofi"),
    "wallpaper-picker": (),
    "radial-launcher": (),
    "clipboard": ("cliphist", "wl-paste"),
}


def _spawn(argv: List[str], detach: bool = True) -> bool:
    if not argv or not shutil.which(argv[0]):
        return False
    try:
        if detach:
            subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            subprocess.run(argv, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return True


def _tools_dir() -> Path:
    raw = os.environ.get("XDG_CONFIG_HOME")
    base = Path(raw) if raw else Path(os.environ.get("HOME", "~")) / ".config"
    return base / "noctalia" / "tools"


def _run_tool(script: str) -> bool:
    path = _tools_dir() / script
    if path.is_file():
        return _spawn([str(path)])
    if shutil.which(script):
        return _spawn([script])
    return False


def _niri_msg(*args: str) -> bool:
    return _spawn(["niri", "msg", *args], detach=False)


def _notify(summary: str, body: str, urgency: str = "normal") -> None:
    _spawn(["notify-send", "-a", "Nyxuri Shell", "-u", urgency, summary, body])


def daemon_command(action: str) -> Optional[str]:
    return DAEMON_ACTIONS.get(action)


def dispatch(action: str) -> int:
    if action not in STANDARD_ACTIONS:
        print(f"unknown shell action: {action}", file=sys.stderr)
        print("usage: shell-action {" + "|".join(STANDARD_ACTIONS) + "}", file=sys.stderr)
        return ACTION_EXIT_UNKNOWN

    command = DAEMON_ACTIONS[action]
    args: Dict[str, Any] = {"action": action}
    if action in ("launcher", "session", "clipboard"):
        args["panel"] = action

    response = ipc.send(command, args, timeout=2.0)
    if response.ok:
        return ACTION_EXIT_OK

    if response.error == "daemon not running":
        if _fallback(action):
            return ACTION_EXIT_OK
        _notify("Nyxuri Shell", f"daemon not running; {action} unavailable", "critical")
        return ACTION_EXIT_NO_DAEMON

    print(f"shell action failed: {action}: {response.error}", file=sys.stderr)
    return ACTION_EXIT_FAILED


def _fallback(action: str) -> bool:
    if action == "wallpaper-picker":
        return _run_tool("wallpaper-picker.py")
    if action == "radial-launcher":
        return _run_tool("orbit-launcher.py")
    for candidate in EXTERNAL_FALLBACKS.get(action, ()):
        if shutil.which(candidate):
            if action == "launcher":
                return _spawn([candidate])
            return _spawn([candidate])
    if action == "lock":
        for locker in ("swaylock", "gtklock", "hyprlock"):
            if shutil.which(locker):
                return _spawn([locker])
    if action == "wallpaper-random":
        return _random_wallpaper()
    return False


def _random_wallpaper() -> bool:
    import random

    from nyxuri_shell import wallpaper as W

    root = S.wallpapers_dir()
    pool = [p for p in W.scan_directory(root) if not W.is_video(p)]
    if not pool:
        return False
    return set_wallpaper(random.choice(pool))[0]


def set_wallpaper(path: Path) -> Tuple[bool, str]:
    if not path.is_file():
        return (False, "file not found")

    from nyxuri_shell import wallpaper as W

    current = S.load_state()
    current.appearance.wallpaper = str(path)
    current.appearance.live_wallpaper = W.is_video(path)

    color = W.pick_from_file(path)
    if color is not None:
        current.appearance.source_color = color.hex

    if not S.save_state(current):
        return (False, "cannot persist state")
    if not S.write_palette(current):
        return (False, "cannot write palette")

    _apply_wallpaper_surface(path, current.appearance.live_wallpaper)
    _notify("Nyxuri Shell", f"wallpaper set: {path.name}")
    return (True, current.appearance.source_color)


def _apply_wallpaper_surface(path: Path, is_live: bool) -> None:
    if is_live:
        if shutil.which("mpvpaper"):
            _kill_pattern("mpvpaper")
            _spawn(["mpvpaper", "-o", "no-audio --loop-file=inf", "*", str(path)])
        return
    _kill_pattern("mpvpaper")
    if shutil.which("swaybg"):
        _kill_pattern("swaybg")
        _spawn(["swaybg", "-i", str(path), "-m", "fill"])
    elif shutil.which("swww"):
        _spawn(["swww", "img", str(path)])


def _kill_pattern(pattern: str) -> None:
    if not shutil.which("pkill"):
        return
    subprocess.run(["pkill", "-x", pattern], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def list_actions() -> str:
    lines = ["standard actions:"]
    for action in STANDARD_ACTIONS:
        lines.append(f"  {action:20s} -> ipc:{DAEMON_ACTIONS[action]}")
    return "\n".join(lines)


def _self_check() -> List[str]:
    problems: List[str] = []

    for action in STANDARD_ACTIONS:
        if action not in DAEMON_ACTIONS:
            problems.append(f"{action} has no daemon command")

    if daemon_command("nope") is not None:
        problems.append("unknown action mapped")

    from nyxuri_shell import state as _S

    if _S.wallpapers_dir().name != "Wallpapers":
        problems.append("wallpapers dir unexpected")

    code = dispatch("definitely-not-an-action")
    if code != ACTION_EXIT_UNKNOWN:
        problems.append(f"unknown action exit code {code}")

    try:
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.');"
             "from nyxuri_shell.actions import dispatch;"
             "sys.exit(dispatch('launcher'))"],
            capture_output=True, text=True, timeout=15, cwd=str(Path.cwd()),
        )
        if out.returncode not in (ACTION_EXIT_OK, ACTION_EXIT_NO_DAEMON, ACTION_EXIT_FAILED):
            problems.append(f"subprocess exit code {out.returncode}: {out.stderr[:200]}")
    except (OSError, subprocess.TimeoutExpired) as exc:
        problems.append(f"subprocess check failed: {exc}")

    return problems


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        print(list_actions())
        return ACTION_EXIT_OK

    if argv[0] in ("--action", "-a"):
        argv = argv[1:]

    if not argv:
        print("missing action", file=sys.stderr)
        return ACTION_EXIT_UNKNOWN

    if argv[0] == "--list":
        print(list_actions())
        return ACTION_EXIT_OK

    if argv[0] == "--set-wallpaper":
        if len(argv) < 2:
            print("missing path", file=sys.stderr)
            return ACTION_EXIT_UNKNOWN
        target = Path(argv[1]).expanduser()
        live = ipc.send("wallpaper-set", {"path": str(target)}, timeout=15.0)
        if live.ok:
            print(str(live.data.get("source_color") or ""))
            return ACTION_EXIT_OK
        if live.error != "daemon not running":
            print(live.error, file=sys.stderr)
            return ACTION_EXIT_FAILED
        ok, info = set_wallpaper(target)
        print(info)
        return ACTION_EXIT_OK if ok else ACTION_EXIT_FAILED

    if argv[0] == "--status":
        current = S.load_state()
        print(json.dumps(current.to_dict(), ensure_ascii=False, indent=2))
        return ACTION_EXIT_OK

    return dispatch(argv[0])


if __name__ == "__main__":
    if os.environ.get("NYXURI_SHELL_SELFCHECK") == "1":
        issues = _self_check()
        if issues:
            print("self-check failed:")
            for p in issues:
                print("  -", p)
            sys.exit(1)
        print("ok")
        sys.exit(0)
    sys.exit(main())
