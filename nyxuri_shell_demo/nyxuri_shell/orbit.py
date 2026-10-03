import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nyxuri_shell.motion import Spring

BASE_RADIUS = 168.0
DEADZONE_RADIUS = 48.0
HYSTERESIS_DEG = 6.0
CAPSULE_IDLE_H = 48.0
CAPSULE_ACTIVE_H = 54.0

DEFAULT_ITEMS: List[dict] = [
    {"id": "kitty", "name": "Kitty", "desc": "Terminal", "icon": "\u2328", "cmd": "kitty"},
    {"id": "tools", "name": "System Tools", "desc": "Folder \u00b7 3 Tools", "icon": "\u2699",
     "children": [
         {"id": "missioncenter", "name": "Mission Center", "desc": "System Monitor", "icon": "\u25a3",
          "cmd": "missioncenter"},
         {"id": "eyecare", "name": "Eye Care", "desc": "Toggle Warmth", "icon": "\u25d0",
          "cmd": "~/.config/niri/scripts/toggle-eyecare.sh"},
         {"id": "cache", "name": "Clean Cache", "desc": "Free Disk Space", "icon": "\u2662",
          "cmd": "nyxuri clean"},
     ]},
    {"id": "websites", "name": "Websites", "desc": "Folder \u00b7 3 Sites", "icon": "\u25c9",
     "children": [
         {"id": "zhihu", "name": "Zhihu", "desc": "\u77e5\u4e4e", "icon": "\u25c9",
          "url": "https://www.zhihu.com"},
         {"id": "bilibili", "name": "Bilibili", "desc": "\u54d4\u54e9\u54d4\u54e9", "icon": "\u25b6",
          "url": "https://www.bilibili.com"},
         {"id": "github", "name": "GitHub", "desc": "Code Repository", "icon": "\u25c8",
          "url": "https://github.com"},
     ]},
    {"id": "wallpaper", "name": "Wallpapers", "desc": "Static & Live", "icon": "\u25a6",
     "cmd": "nyxuri-shell --action wallpaper-picker"},
]

DEFAULT_ENGINES: List[dict] = [
    {"id": "bing", "name": "Bing", "url": "https://www.bing.com/search?q={query}"},
    {"id": "google", "name": "Google", "url": "https://www.google.com/search?q={query}"},
    {"id": "deepseek", "name": "DeepSeek", "url": "https://chat.deepseek.com/?q={query}"},
    {"id": "chatgpt", "name": "ChatGPT", "url": "https://chatgpt.com/?hints=search&q={query}"},
]

DEFAULT_SEARCH = {"default_engine": "bing", "placeholder": "Search or ask..."}


def config_paths() -> List[Path]:
    home = Path(os.environ.get("HOME", str(Path.home())))
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return [
        config_home / "nyxuri-shell" / "orbit-items.toml",
        config_home / "noctalia" / "tools" / "orbit-items__custom__.toml",
        config_home / "niri" / "scratchpad-items__custom__.toml",
    ]


def _load_toml(path: Path) -> Optional[dict]:
    try:
        import tomllib

        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, ValueError, ImportError):
        return None


def load_items() -> List[dict]:
    for path in config_paths():
        if not path.is_file():
            continue
        data = _load_toml(path)
        if not isinstance(data, dict):
            continue
        items = data.get("items")
        if isinstance(items, list) and items:
            return items
    return DEFAULT_ITEMS


def load_engines() -> Tuple[List[dict], dict]:
    for path in config_paths():
        if not path.is_file():
            continue
        data = _load_toml(path)
        if not isinstance(data, dict):
            continue
        engines = data.get("search_engines")
        meta = data.get("search") if isinstance(data.get("search"), dict) else {}
        if isinstance(engines, list) and engines:
            return engines, {**DEFAULT_SEARCH, **meta}
    return DEFAULT_ENGINES, dict(DEFAULT_SEARCH)


@dataclass
class Item:
    id: str
    name: str
    desc: str = ""
    icon: str = ""
    cmd: str = ""
    url: str = ""
    shortcut: str = ""
    children: List["Item"] = field(default_factory=list)

    @property
    def is_folder(self) -> bool:
        return bool(self.children)


def build_tree(raw: List[dict]) -> List[Item]:
    out: List[Item] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        children = entry.get("children")
        out.append(Item(
            id=str(entry.get("id") or entry.get("name") or ""),
            name=str(entry.get("name") or ""),
            desc=str(entry.get("desc") or ""),
            icon=str(entry.get("icon") or ""),
            cmd=str(entry.get("cmd") or ""),
            url=str(entry.get("url") or ""),
            shortcut=str(entry.get("shortcut") or ""),
            children=build_tree(children) if isinstance(children, list) else [],
        ))
    return out


def angle_of(dx: float, dy: float) -> float:
    return math.degrees(math.atan2(dy, dx)) % 360.0


def radius_of(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def sector_of(angle: float, count: int) -> int:
    if count <= 0:
        return -1
    return int(round(angle / (360.0 / count))) % count


def angle_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def hit_test(dx: float, dy: float, count: int, current: Optional[int] = None,
             deadzone: float = DEADZONE_RADIUS,
             hysteresis: float = HYSTERESIS_DEG) -> Optional[int]:
    if count <= 0:
        return None
    if radius_of(dx, dy) < deadzone:
        return None
    angle = angle_of(dx, dy)
    candidate = sector_of(angle, count)
    if current is None or current == candidate:
        return candidate
    step = 360.0 / count
    boundary = (current + 0.5) * step
    if angle_diff(angle, boundary) < hysteresis:
        return current
    return candidate


def folder_labels(items: List[Item]) -> List[str]:
    return [f"{i.name} ({len(i.children)})" if i.is_folder else i.name for i in items]


def digit_index(keyval: int, digits: Tuple[int, ...] = ()) -> Optional[int]:
    if not digits:
        digits = tuple(range(0x31, 0x3A))
    try:
        pos = digits.index(keyval)
    except ValueError:
        return None
    return pos


def rotate(current: Optional[int], count: int, delta: int) -> Optional[int]:
    if count <= 0:
        return None
    if current is None:
        return 0 if delta >= 0 else count - 1
    return (current + delta) % count


def mnemonic_index(items: List[Item], char: str) -> Optional[int]:
    if not char:
        return None
    needle = char.lower()
    for index, item in enumerate(items):
        if item.name.lower().startswith(needle):
            return index
    return None


def digit_map(items: List[Item], limit: int = 9) -> Dict[str, int]:
    out: Dict[str, int] = {}
    used: set = set()
    for index, item in enumerate(items[:limit]):
        explicit = getattr(item, "shortcut", "")
        if explicit and explicit.isdigit() and explicit not in used:
            out[explicit] = index
            used.add(explicit)
    nxt = 1
    for index in range(len(items[:limit])):
        if index in out.values():
            continue
        while str(nxt) in used:
            nxt += 1
        if nxt > limit:
            break
        out[str(nxt)] = index
        used.add(str(nxt))
        nxt += 1
    return out


def search_url(query: str, engines: List[dict], engine_id: str = "") -> str:
    chosen = None
    for engine in engines:
        if engine.get("id") == engine_id:
            chosen = engine
            break
    if chosen is None and engines:
        chosen = engines[0]
    if chosen is None:
        return ""
    template = str(chosen.get("url") or "")
    from urllib.parse import quote_plus

    return template.replace("{query}", quote_plus(query))


def resolve_target(item: Item) -> List[str]:
    import shlex
    import shutil

    if item.url:
        for opener in ("xdg-open", "gio"):
            if shutil.which(opener):
                return [opener, item.url]
        return []
    if not item.cmd:
        return []
    expanded = os.path.expanduser(item.cmd)
    try:
        return shlex.split(expanded)
    except ValueError:
        return []


@dataclass
class OrbitState:
    depth: int = 0
    stack: List[int] = field(default_factory=list)
    hover: Optional[int] = None
    query: str = ""

    def enter(self, index: int, item: Item) -> bool:
        if not item.is_folder:
            return False
        self.stack.append(index)
        self.depth += 1
        self.hover = None
        self.query = ""
        return True

    def back(self) -> bool:
        if not self.stack:
            return False
        self.stack.pop()
        self.depth -= 1
        self.hover = None
        return True

    def current_items(self, root: List[Item]) -> List[Item]:
        node = root
        for index in self.stack:
            if 0 <= index < len(node):
                node = node[index].children
            else:
                return []
        return node

    def current_item(self, root: List[Item]) -> Optional[Item]:
        items = self.current_items(root)
        if self.hover is None or not (0 <= self.hover < len(items)):
            return None
        return items[self.hover]


class Animator:

    def __init__(self) -> None:
        self.bloom = Spring(value=0.0, target=0.0, damping=0.70, stiffness=196.0, epsilon=2e-4)
        self.subring = Spring(value=1.0, target=1.0, damping=0.80, stiffness=225.0, epsilon=2e-4)
        self.hover = Spring(value=0.0, target=0.0, damping=1.00, stiffness=324.0, epsilon=2e-4)
        self._hover_index: Optional[int] = None
        self._open = False

    @property
    def open(self) -> bool:
        return self._open

    def show(self) -> None:
        self._open = True
        self.bloom.set(1.0)
        self.subring.set(1.0, immediate=True)
        self.hover.set(0.0, immediate=True)
        self._hover_index = None

    def hide(self) -> None:
        self._open = False
        self.bloom.set(0.0)

    def enter_subring(self) -> None:
        self.subring.value = 0.0
        self.subring.velocity = 0.0
        self.subring.set(1.0)
        self.hover.set(0.0, immediate=True)
        self._hover_index = None

    def leave_subring(self) -> None:
        self.subring.value = 0.0
        self.subring.velocity = 0.0
        self.subring.set(1.0)
        self.hover.set(0.0, immediate=True)
        self._hover_index = None

    def set_hover(self, index: Optional[int]) -> None:
        if index == self._hover_index:
            return
        self._hover_index = index
        self.hover.set(1.0 if index is not None else 0.0)

    @property
    def active(self) -> bool:
        return not (self.bloom.settled and self.subring.settled and self.hover.settled)

    def step(self, dt: float) -> None:
        self.bloom.step(dt)
        self.subring.step(dt)
        self.hover.step(dt)

    def reset(self) -> None:
        self.bloom.set(0.0, immediate=True)
        self.subring.set(1.0, immediate=True)
        self.hover.set(0.0, immediate=True)
        self._hover_index = None
        self._open = False


@dataclass
class Flick:

    aiming: bool = False
    armed: bool = False
    button_held: bool = False

    def begin(self) -> None:
        self.aiming = True
        self.armed = True

    def end(self) -> None:
        self.aiming = False
        self.armed = False

    def press(self) -> None:
        self.button_held = True

    def release(self) -> bool:
        was = self.armed and self.button_held
        self.button_held = False
        self.armed = False
        self.aiming = False
        return was

    @property
    def active(self) -> bool:
        return self.armed or self.aiming


def _self_check() -> List[str]:
    problems: List[str] = []

    if sector_of(0.0, 4) != 0:
        problems.append("sector_of(0) wrong")
    if sector_of(90.0, 4) != 1:
        problems.append("sector_of(90) wrong")
    if sector_of(359.0, 4) != 0:
        problems.append("sector_of(359) wrong")

    if hit_test(0.0, 0.0, 4) is not None:
        problems.append("deadzone not honored")
    if hit_test(200.0, 0.0, 4) != 0:
        problems.append("hit_test right failed")

    near_boundary = 45.0 - HYSTERESIS_DEG / 2
    dx = math.cos(math.radians(near_boundary)) * 200
    dy = math.sin(math.radians(near_boundary)) * 200
    if hit_test(dx, dy, 4, current=0) != 0:
        problems.append("hysteresis not honored")

    far_past = 45.0 + HYSTERESIS_DEG * 2
    dx = math.cos(math.radians(far_past)) * 200
    dy = math.sin(math.radians(far_past)) * 200
    if hit_test(dx, dy, 4, current=0) != 1:
        problems.append("hysteresis blocks real movement")

    if abs(angle_diff(10.0, 350.0) - 20.0) > 1e-6:
        problems.append("angle_diff wrap wrong")

    tree = build_tree(DEFAULT_ITEMS)
    if len(tree) != len(DEFAULT_ITEMS):
        problems.append("build_tree dropped items")
    if not any(i.is_folder for i in tree):
        problems.append("no folder detected")

    state = OrbitState()
    if state.enter(0, tree[0]):
        problems.append("entered non-folder")
    folder_index = next(i for i, it in enumerate(tree) if it.is_folder)
    if not state.enter(folder_index, tree[folder_index]):
        problems.append("could not enter folder")
    if state.depth != 1:
        problems.append("depth not incremented")
    if not state.current_items(tree):
        problems.append("folder has no children")
    if not state.back():
        problems.append("back failed")
    if state.depth != 0:
        problems.append("depth not decremented")
    if state.back():
        problems.append("back from root should fail")

    engines, _meta = load_engines()
    url = search_url("hello world", engines, "bing")
    if "hello+world" not in url and "hello%20world" not in url:
        problems.append(f"search url not encoded: {url}")

    for fn in (load_items, load_engines, config_paths):
        try:
            fn()
        except Exception as exc:
            problems.append(f"{fn.__name__} raised {type(exc).__name__}")

    anim = Animator()
    if anim.active:
        problems.append("fresh animator should be settled")
    anim.show()
    if not anim.active:
        problems.append("show() should start motion")
    steps = 0
    while anim.active and steps < 600:
        anim.step(1.0 / 60.0)
        steps += 1
    if anim.active:
        problems.append("bloom never settled")
    if abs(anim.bloom.value - 1.0) > 1e-3:
        problems.append(f"bloom settled at {anim.bloom.value}")
    if steps > 200:
        problems.append(f"bloom too slow: {steps} frames")

    anim.enter_subring()
    if not anim.active:
        problems.append("enter_subring should animate")
    for _ in range(600):
        if not anim.active:
            break
        anim.step(1.0 / 60.0)
    if abs(anim.subring.value - 1.0) > 1e-3:
        problems.append(f"subring did not re-bloom: {anim.subring.value}")

    anim.leave_subring()
    for _ in range(600):
        if not anim.active:
            break
        anim.step(1.0 / 60.0)
    if abs(anim.subring.value - 1.0) > 1e-3:
        problems.append("leave_subring did not settle at 1.0")

    anim.set_hover(2)
    if not anim.active:
        problems.append("hover should animate")
    anim.set_hover(2)
    if anim.hover.target != 1.0:
        problems.append("hover target wrong")
    anim.reset()
    if anim.active or anim.open:
        problems.append("reset did not settle")

    if digit_index(0x31) != 0 or digit_index(0x39) != 8:
        problems.append("digit_index mapping wrong")
    if digit_index(0x41) is not None:
        problems.append("digit_index accepted a letter")

    if rotate(None, 4, 1) != 0:
        problems.append("rotate from empty forward")
    if rotate(None, 4, -1) != 3:
        problems.append("rotate from empty backward")
    if rotate(3, 4, 1) != 0:
        problems.append("rotate did not wrap")
    if rotate(0, 4, -1) != 3:
        problems.append("rotate negative wrap")
    if rotate(0, 0, 1) is not None:
        problems.append("rotate on empty ring")

    tree = build_tree(DEFAULT_ITEMS)
    if mnemonic_index(tree, "k") != 0:
        problems.append("mnemonic lookup wrong")
    if mnemonic_index(tree, "z") is not None:
        problems.append("mnemonic matched nothing")
    if mnemonic_index(tree, "") is not None:
        problems.append("empty mnemonic accepted")

    mapping = digit_map(tree)
    if len(mapping) != len(tree):
        problems.append(f"digit_map size {len(mapping)} vs {len(tree)}")
    if sorted(int(k) for k in mapping) != list(range(1, len(tree) + 1)):
        problems.append("digit_map keys not 1..n")
    explicit = build_tree([{"id": "a", "name": "A", "shortcut": "3"},
                           {"id": "b", "name": "B"}])
    emap = digit_map(explicit)
    if emap.get("3") != 0:
        problems.append("explicit shortcut ignored")
    if emap.get("1") != 1:
        problems.append("auto shortcut did not fill remaining")

    flick = Flick()
    if flick.active or flick.release():
        problems.append("flick armed by default")
    flick.begin()
    if not flick.active:
        problems.append("flick.begin did not arm")
    if flick.release():
        problems.append("release without button press committed")
    flick.begin()
    flick.press()
    if not flick.release():
        problems.append("armed release did not commit")
    if flick.release():
        problems.append("second release committed twice")
    if flick.active:
        problems.append("flick still active after release")

    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)

    tree = build_tree(load_items())
    print(f"items: {len(tree)}")
    for item in tree:
        kind = "folder" if item.is_folder else "app"
        print(f"  [{kind:6s}] {item.name:20s} {item.desc}")
    print("ok")
