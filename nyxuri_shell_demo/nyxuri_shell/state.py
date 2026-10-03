import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from nyxuri_shell.color import generate_scheme, hex_of, rgb_of

APP = "nyxuri-shell"
CONFIG_NAME = "shell.toml"


def _home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home())))


def xdg_config_home() -> Path:
    raw = os.environ.get("XDG_CONFIG_HOME")
    return Path(raw) if raw else _home() / ".config"


def xdg_cache_home() -> Path:
    raw = os.environ.get("XDG_CACHE_HOME")
    return Path(raw) if raw else _home() / ".cache"


def xdg_pictures() -> Path:
    return _home() / "Pictures"


def state_path() -> Path:
    return xdg_cache_home() / "nyxuri" / "shell-state.json"


def palette_path() -> Path:
    return xdg_cache_home() / "nyxuri" / "palette.toml"


def config_path() -> Path:
    return xdg_config_home() / APP / CONFIG_NAME


def wallpapers_dir() -> Path:
    return xdg_pictures() / "Wallpapers"


def video_wallpapers_dir() -> Path:
    return wallpapers_dir() / "video"


def thumb_cache_dir() -> Path:
    return xdg_cache_home() / "nyxuri" / "thumbs"


@dataclass
class Appearance:
    mode: str = "dark"
    scheme: str = "tonal_spot"
    source_color: str = "#6750a4"
    wallpaper: str = ""
    live_wallpaper: bool = False
    blur: bool = True
    opacity: float = 0.90

    def mode_effective(self) -> str:
        if self.mode == "auto":
            return "dark"
        return self.mode if self.mode in ("dark", "light") else "dark"

    def scheme_colors(self) -> Dict[str, Dict[str, str]]:
        return generate_scheme(rgb_of(self.source_color))


@dataclass
class Layout:
    bar_position: str = "top"
    bar_height: int = 36
    bar_margin: int = 10
    capsule: bool = True
    capsule_radius: int = 80
    scale: float = 1.10
    dock_enabled: bool = True
    dock_auto_hide: bool = True


@dataclass
class Osd:
    enabled: bool = True
    position: str = "bottom_center"
    timeout_ms: int = 2000
    scale: float = 0.90


@dataclass
class Idle:
    lock_timeout: int = 300
    screen_off_timeout: int = 360
    suspend_timeout: int = 900

    def behaviors(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if self.lock_timeout > 0:
            out.append({"action": "lock", "timeout": float(self.lock_timeout), "enabled": True})
        if self.screen_off_timeout > 0:
            out.append({"action": "screen_off", "timeout": float(self.screen_off_timeout), "enabled": True})
        if self.suspend_timeout > 0:
            out.append({"action": "lock_and_suspend", "timeout": float(self.suspend_timeout), "enabled": True})
        out.sort(key=lambda b: b["timeout"])
        return out


@dataclass
class ShellState:
    appearance: Appearance = field(default_factory=Appearance)
    layout: Layout = field(default_factory=Layout)
    osd: Osd = field(default_factory=Osd)
    idle: Idle = field(default_factory=Idle)
    active_shell: str = "custom"
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_shell": self.active_shell,
            "appearance": asdict(self.appearance),
            "layout": asdict(self.layout),
            "osd": asdict(self.osd),
            "idle": asdict(self.idle),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShellState":
        def sub(klass, key):
            raw = data.get(key)
            if not isinstance(raw, dict):
                raw = {}
            known = {f for f in klass.__dataclass_fields__}
            return klass(**{k: v for k, v in raw.items() if k in known})

        return cls(
            appearance=sub(Appearance, "appearance"),
            layout=sub(Layout, "layout"),
            osd=sub(Osd, "osd"),
            idle=sub(Idle, "idle"),
            active_shell=str(data.get("active_shell", "custom")),
            schema_version=int(data.get("schema_version", 1) or 1),
        )


def load_state() -> ShellState:
    path = state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ShellState()
    if not isinstance(data, dict):
        return ShellState()
    try:
        return ShellState.from_dict(data)
    except TypeError:
        return ShellState()


def save_state(state: ShellState) -> bool:
    path = state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".state.", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(name).replace(path)
        return True
    except OSError:
        return False


def write_palette(state: ShellState) -> bool:
    from nyxuri_shell.color import render_palette_toml

    scheme = state.appearance.scheme_colors()
    mode = state.appearance.mode_effective()
    body = render_palette_toml(
        scheme,
        mode=mode,
        source_hex=state.appearance.source_color,
        wallpaper=state.appearance.wallpaper,
    )
    path = palette_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".palette.", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        Path(name).replace(path)
        return True
    except OSError:
        return False


def apply_source_color(state: ShellState, rgb) -> ShellState:
    state.appearance.source_color = hex_of(rgb)
    return state


def _self_check() -> List[str]:
    problems: List[str] = []
    state = ShellState()
    data = state.to_dict()
    if data["appearance"]["mode"] != "dark":
        problems.append("default mode not dark")

    roundtrip = ShellState.from_dict(data)
    if roundtrip.to_dict() != data:
        problems.append("state roundtrip mismatch")

    legacy = {"appearance": {"mode": "light", "bogus_key": 1}, "unknown": True}
    parsed = ShellState.from_dict(legacy)
    if parsed.appearance.mode != "light":
        problems.append("tolerant parse failed")
    if hasattr(parsed.appearance, "bogus_key"):
        problems.append("unknown key leaked into dataclass")

    broken = ShellState.from_dict({"idle": "not-a-dict"})
    if not isinstance(broken.idle, Idle):
        problems.append("bad idle payload not coerced")

    scheme = state.appearance.scheme_colors()
    if not scheme["dark"].get("primary"):
        problems.append("scheme missing primary")

    behaviors = state.idle.behaviors()
    if [b["timeout"] for b in behaviors] != sorted(b["timeout"] for b in behaviors):
        problems.append("idle behaviors not sorted")

    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)
    print("ok")
