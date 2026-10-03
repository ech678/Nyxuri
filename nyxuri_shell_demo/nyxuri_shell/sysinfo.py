import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

PROBE_TIMEOUT = 3
BACKLIGHT_ROOT = Path("/sys/class/backlight")
POWER_ROOT = Path("/sys/class/power_supply")


def _run(cmd: List[str], timeout: int = PROBE_TIMEOUT) -> Optional[str]:
    if not shutil.which(cmd[0]):
        return None
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if res.returncode != 0:
        return None
    return res.stdout


def _run_json(cmd: List[str], timeout: int = PROBE_TIMEOUT):
    raw = _run(cmd, timeout)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


@dataclass(frozen=True)
class Workspace:
    id: int
    idx: int
    name: str
    active: bool
    urgent: bool
    focused: bool

    @property
    def label(self) -> str:
        return self.name or str(self.idx)


@dataclass(frozen=True)
class Window:
    title: str
    app_id: str

    @property
    def label(self) -> str:
        if self.title and self.app_id:
            return f"{self.app_id}: {self.title}"
        return self.title or self.app_id or ""


def workspaces() -> List[Workspace]:
    data = _run_json(["niri", "msg", "-j", "workspaces"])
    if not isinstance(data, list):
        return []
    out: List[Workspace] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            out.append(Workspace(
                id=int(item.get("id", 0)),
                idx=int(item.get("idx", 0)),
                name=str(item.get("name") or ""),
                active=bool(item.get("is_active")),
                urgent=bool(item.get("is_urgent")),
                focused=bool(item.get("is_focused")),
            ))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda w: w.idx)
    return out


def focused_window() -> Optional[Window]:
    data = _run_json(["niri", "msg", "-j", "windows"])
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict) and item.get("is_focused"):
            return Window(str(item.get("title") or ""), str(item.get("app_id") or ""))
    return None


def focus_workspace(idx: int) -> bool:
    return _run(["niri", "msg", "action", "focus-workspace", str(idx)]) is not None


@dataclass(frozen=True)
class Battery:
    percent: float
    charging: bool
    present: bool


def battery() -> Optional[Battery]:
    if not POWER_ROOT.is_dir():
        return None
    try:
        entries = sorted(POWER_ROOT.iterdir())
    except OSError:
        return None
    for entry in entries:
        try:
            kind = (entry / "type").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if kind != "Battery":
            continue
        try:
            capacity = float((entry / "capacity").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        status = ""
        try:
            status = (entry / "status").read_text(encoding="utf-8").strip()
        except OSError:
            pass
        return Battery(capacity, status.lower() in ("charging", "full"), True)
    return None


def volume() -> Optional[Tuple[int, bool]]:
    raw = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    if not raw:
        return None
    match = re.search(r"Volume:\s*([0-9.]+)", raw)
    if not match:
        return None
    try:
        percent = int(round(float(match.group(1)) * 100))
    except ValueError:
        return None
    return (percent, "[MUTED]" in raw)


def backlight_devices() -> List[Path]:
    if not BACKLIGHT_ROOT.is_dir():
        return []
    try:
        return [p for p in sorted(BACKLIGHT_ROOT.iterdir()) if p.is_dir()]
    except OSError:
        return []


def backlight_percent() -> Optional[int]:
    for dev in backlight_devices():
        try:
            cur = int((dev / "brightness").read_text(encoding="utf-8").strip())
            top = int((dev / "max_brightness").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if top <= 0:
            continue
        return int(round(cur / top * 100))
    return None


def set_backlight(percent: int) -> Optional[int]:
    percent = max(1, min(100, percent))
    for dev in backlight_devices():
        try:
            top = int((dev / "max_brightness").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if top <= 0:
            continue
        target = max(1, int(round(top * percent / 100)))
        try:
            (dev / "brightness").write_text(str(target), encoding="utf-8")
            return percent
        except OSError:
            continue
    if shutil.which("brightnessctl"):
        if _run(["brightnessctl", "set", f"{percent}%"]) is not None:
            return percent
    return None


def adjust_backlight(delta: int) -> Optional[int]:
    current = backlight_percent()
    if current is None:
        current = 50
    return set_backlight(current + delta)


def focused_output_is_internal() -> bool:
    raw = _run(["niri", "msg", "focused-output"])
    if not raw:
        return bool(backlight_devices())
    match = re.search(r"\(([^)]+)\)", raw)
    if not match:
        return bool(backlight_devices())
    return match.group(1).startswith(("eDP", "LVDS", "DSI"))


def adjust_volume(delta: int) -> Optional[int]:
    step = f"{abs(delta)}%{'+' if delta >= 0 else '-'}"
    if _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", step]) is None:
        return None
    current = volume()
    return current[0] if current else None


def toggle_mute() -> Optional[bool]:
    if _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"]) is None:
        return None
    current = volume()
    return None if current is None else current[1]


_CPU_PREV: Optional[Tuple[int, int, float]] = None


def cpu_percent(sample: float = 0.25, blocking: bool = True) -> Optional[float]:
    import time

    def read() -> Optional[Tuple[int, int]]:
        try:
            parts = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()
        except (OSError, IndexError):
            return None
        try:
            values = [int(v) for v in parts[1:]]
        except ValueError:
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return (sum(values), idle)

    global _CPU_PREV
    now = time.monotonic()

    if not blocking:
        current = read()
        if current is None:
            return None
        previous = _CPU_PREV
        _CPU_PREV = (current[0], current[1], now)
        if previous is None:
            return None
        total = current[0] - previous[0]
        idle = current[1] - previous[1]
        if total <= 0:
            return None
        return max(0.0, min(100.0, (1.0 - idle / total) * 100.0))

    first = read()
    if first is None:
        return None
    time.sleep(sample)
    second = read()
    if second is None:
        return None
    total = second[0] - first[0]
    idle = second[1] - first[1]
    if total <= 0:
        return None
    return max(0.0, min(100.0, (1.0 - idle / total) * 100.0))


def memory_percent() -> Optional[float]:
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            info[key.strip()] = rest.strip()
        total = float(info["MemTotal"].split()[0])
        avail = float(info["MemAvailable"].split()[0])
    except (OSError, KeyError, ValueError, IndexError):
        return None
    if total <= 0:
        return None
    return max(0.0, min(100.0, (1.0 - avail / total) * 100.0))


def _self_check() -> List[str]:
    problems: List[str] = []

    for fn in (workspaces, focused_window, battery, volume,
               backlight_percent, cpu_percent, memory_percent):
        try:
            fn()
        except Exception as exc:
            problems.append(f"{fn.__name__} raised {type(exc).__name__}: {exc}")

    try:
        focus_workspace(1)
    except Exception as exc:
        problems.append(f"focus_workspace raised {type(exc).__name__}")

    try:
        set_backlight(50)
    except Exception as exc:
        problems.append(f"set_backlight raised {type(exc).__name__}")

    try:
        adjust_volume(1)
        toggle_mute()
    except Exception as exc:
        problems.append(f"volume control raised {type(exc).__name__}")

    mem = memory_percent()
    if mem is not None and not (0.0 <= mem <= 100.0):
        problems.append(f"memory_percent out of range: {mem}")

    cpu = cpu_percent(sample=0.05)
    if cpu is not None and not (0.0 <= cpu <= 100.0):
        problems.append(f"cpu_percent out of range: {cpu}")

    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)

    print("workspaces   :", [w.label for w in workspaces()] or "(no niri)")
    win = focused_window()
    print("focused      :", win.label if win else "(none)")
    print("battery      :", battery())
    print("volume       :", volume())
    print("backlight    :", backlight_percent())
    print("cpu          :", cpu_percent())
    print("memory       :", memory_percent())
    print("ok")
