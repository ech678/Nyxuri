import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SKIP_CATEGORIES = ("Settings", "System", "ConsoleOnly")
ICON_SIZES = (256, 128, 96, 64, 48, 32)

_ENTRY_RE = re.compile(r"^\[([^\]]+)\]\s*$")
_KEY_RE = re.compile(r"^([A-Za-z0-9-]+)\s*=\s*(.*)$")
_FIELD_CODES = re.compile(r"%[fFuUdDnNickvm]")


def _home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home())))


def data_dirs() -> List[Path]:
    raw = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    dirs = [Path(p) for p in raw.split(":") if p]
    dirs.insert(0, _home() / ".local/share")
    return dirs


def applications_dirs() -> List[Path]:
    return [d / "applications" for d in data_dirs()]


def icon_dirs() -> List[Path]:
    dirs = [_home() / ".local/share/icons", _home() / ".icons"]
    for base in data_dirs():
        dirs.append(base / "icons")
        dirs.append(base / "pixmaps")
    return dirs


@dataclass
class AppEntry:
    id: str
    name: str
    exec_line: str
    icon: str = ""
    terminal: bool = False
    nodisplay: bool = False
    categories: Tuple[str, ...] = ()

    @property
    def command(self) -> List[str]:
        line = _FIELD_CODES.sub("", self.exec_line).strip()
        line = line.replace("%%", "%")
        try:
            parts = shlex_split(line)
        except ValueError:
            return []
        if not parts:
            return []
        if self.terminal:
            term = _terminal_command()
            if term:
                return [*term, *parts]
        return parts

    def matches(self, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        return q in self.name.lower() or q in self.id.lower()


def shlex_split(line: str) -> List[str]:
    import shlex

    try:
        return shlex.split(line)
    except ValueError:
        return line.split()


def _terminal_command() -> List[str]:
    for term in ("kitty", "foot", "alacritty", "wezterm", "gnome-terminal", "xterm"):
        if shutil.which(term):
            return [term]
    return []


def parse_desktop(path: Path) -> Optional[AppEntry]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    in_entry = False
    values: Dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        header = _ENTRY_RE.match(stripped)
        if header:
            if in_entry:
                break
            in_entry = header.group(1) == "Desktop Entry"
            continue
        if not in_entry:
            continue
        match = _KEY_RE.match(stripped)
        if match:
            key, value = match.group(1), match.group(2)
            if key not in values:
                values[key] = value

    if not values:
        return None
    if values.get("Type", "Application") != "Application":
        return None
    if values.get("NoDisplay", "").lower() == "true":
        return None
    if values.get("Hidden", "").lower() == "true":
        return None

    name = values.get("Name", "").strip()
    exec_line = values.get("Exec", "").strip()
    if not name or not exec_line:
        return None

    cats = tuple(c for c in values.get("Categories", "").split(";") if c)
    if all(c in SKIP_CATEGORIES for c in cats) and cats:
        return None

    return AppEntry(
        id=path.stem,
        name=name,
        exec_line=exec_line,
        icon=values.get("Icon", "").strip(),
        terminal=values.get("Terminal", "").lower() == "true",
        categories=cats,
    )


_APP_CACHE: Optional[List["AppEntry"]] = None
_APP_STAMP: Optional[Tuple[Tuple[str, float], ...]] = None
_SEARCH_CACHE: Dict[Tuple[str, int], List["AppEntry"]] = {}


def _dir_stamp() -> Tuple[Tuple[str, float], ...]:
    stamps: List[Tuple[str, float]] = []
    for directory in applications_dirs():
        try:
            stamps.append((str(directory), directory.stat().st_mtime))
        except OSError:
            stamps.append((str(directory), 0.0))
    return tuple(stamps)


def load_apps(force: bool = False) -> List[AppEntry]:
    global _APP_CACHE, _APP_STAMP
    stamp = _dir_stamp()
    if not force and _APP_CACHE is not None and stamp == _APP_STAMP:
        return _APP_CACHE

    seen: Dict[str, AppEntry] = {}
    for directory in applications_dirs():
        if not directory.is_dir():
            continue
        try:
            entries = sorted(directory.glob("*.desktop"))
        except OSError:
            continue
        for path in entries:
            if path.stem in seen:
                continue
            parsed = parse_desktop(path)
            if parsed is not None:
                seen[parsed.id] = parsed
    _APP_CACHE = sorted(seen.values(), key=lambda a: a.name.lower())
    _APP_STAMP = stamp
    _SEARCH_CACHE.clear()
    return _APP_CACHE


def search(query: str, limit: int = 8) -> List[AppEntry]:
    key = (query, limit)
    cached = _SEARCH_CACHE.get(key)
    if cached is not None:
        return cached
    all_apps = load_apps()
    if not query:
        result = all_apps[:limit]
    else:
        q = query.lower()
        hits = [a for a in all_apps if a.matches(query)]
        hits.sort(key=lambda a: (0 if a.name.lower().startswith(q) else 1, a.name.lower()))
        result = hits[:limit]
    if len(_SEARCH_CACHE) > 64:
        _SEARCH_CACHE.clear()
    _SEARCH_CACHE[key] = result
    return result


_ICON_CACHE: Dict[str, Optional[str]] = {}


def resolve_icon(name: str) -> Optional[str]:
    if not name:
        return None
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]
    result = _resolve_icon_uncached(name)
    if len(_ICON_CACHE) > 256:
        _ICON_CACHE.clear()
    _ICON_CACHE[name] = result
    return result


def _resolve_icon_uncached(name: str) -> Optional[str]:
    if os.path.isabs(name) and Path(name).is_file():
        return name
    for base in icon_dirs():
        for size in ICON_SIZES:
            for ext in ("png", "svg", "xpm"):
                candidate = base / "hicolor" / f"{size}x{size}" / "apps" / f"{name}.{ext}"
                if candidate.is_file():
                    return str(candidate)
    for base in icon_dirs():
        if not base.is_dir():
            continue
        try:
            for hit in base.rglob(f"{name}.svg"):
                return str(hit)
        except OSError:
            continue
        try:
            for hit in base.rglob(f"{name}.png"):
                return str(hit)
        except OSError:
            continue
    return None


def _self_check() -> List[str]:
    problems: List[str] = []

    for fn in (load_apps, applications_dirs, icon_dirs, data_dirs):
        try:
            fn()
        except Exception as exc:
            problems.append(f"{fn.__name__} raised {type(exc).__name__}: {exc}")

    sample = "[Desktop Entry]\nName=Foo Bar\nExec=foo --flag %U\nIcon=foo\nTerminal=false\n"
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    try:
        path = tmp / "foo.desktop"
        path.write_text(sample, encoding="utf-8")
        entry = parse_desktop(path)
        if entry is None:
            problems.append("valid desktop entry rejected")
        else:
            if entry.name != "Foo Bar":
                problems.append(f"name parsed as {entry.name}")
            if entry.command != ["foo", "--flag"]:
                problems.append(f"command parsed as {entry.command}")

        hidden = tmp / "hidden.desktop"
        hidden.write_text(sample.replace("Terminal=false", "NoDisplay=true"), encoding="utf-8")
        if parse_desktop(hidden) is not None:
            problems.append("NoDisplay entry not rejected")

        wrong = tmp / "wrong.desktop"
        wrong.write_text(sample.replace("Desktop Entry", "Desktop Action x"), encoding="utf-8")
        if parse_desktop(wrong) is not None:
            problems.append("non-Desktop-Entry accepted")

        empty = tmp / "empty.desktop"
        empty.write_text("[Desktop Entry]\nType=Link\n", encoding="utf-8")
        if parse_desktop(empty) is not None:
            problems.append("Link type accepted")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if search("", limit=3) and len(search("", limit=3)) > 3:
        problems.append("search limit ignored")

    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)

    found = load_apps()
    print(f"apps: {len(found)}")
    for app in found[:8]:
        print(f"  {app.name:32s} -> {' '.join(app.command)[:44]}")
    print("ok")
