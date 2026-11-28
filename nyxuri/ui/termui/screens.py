from __future__ import annotations

import pathlib
from typing import Dict, List

from . import theme as t

WIDTH = 98
HEIGHT = 28
MARGIN = 4
EDGE = WIDTH - MARGIN
LABEL = 22
BODY_TOP = 6
BODY_ROWS = 18

PAGES = [
    ("Overview", "overview"),
    ("Plugins", "plugins"),
    ("Doctor", "doctor"),
    ("Config", "config"),
    ("Shell", "shell"),
    ("Snapshots", "snapshots"),
]

STATUS = {
    "ok": t.fg(t.OK, "•"),
    "warn": t.fg(t.WARN, "•"),
    "bad": t.fg(t.BAD, "•"),
}


def _blank() -> str:
    return " " * WIDTH


def _section(title: str) -> str:
    return t.columns((MARGIN, t.fg(t.DIM, title.upper())), total=WIDTH)


def _plain_section(title: str) -> str:
    return t.fg(t.DIM, title.upper())


def _plain_field(label: str, value: str, value_color: str = t.TEXT) -> str:
    return t.fg(t.MUTED, t.pad(label, LABEL)) + t.fg(value_color, value)


def _field(label: str, value: str, value_color: str = t.TEXT) -> str:
    return t.columns(
        (MARGIN, t.fg(t.MUTED, t.pad(label, LABEL))),
        (MARGIN + LABEL, t.fg(value_color, value)),
        total=WIDTH,
    )


def _body(rows: List[str]) -> List[str]:
    lines = list(rows[:BODY_ROWS])
    while len(lines) < BODY_ROWS:
        lines.append(_blank())
    return lines


def header(version: str, mode: str) -> str:
    brand = t.bold(t.fg(t.TEXT, "nyxuri"))
    meta = t.fg(t.DIM, version) + t.fg(t.FAINT, "   ·   ") + t.fg(t.MUTED, mode)
    return t.columns((MARGIN, brand), (EDGE - t.visible_width(meta), meta), total=WIDTH)


def navigation(active: str) -> str:
    segments = []
    position = MARGIN
    for label, key in PAGES:
        styled = t.bold(t.fg(t.ACCENT, label)) if key == active else t.fg(t.MUTED, label)
        segments.append((position, styled))
        position += len(label) + 3
    return t.columns(*segments, total=WIDTH)


def hairline() -> str:
    return t.columns((MARGIN, t.fg(t.FAINT, "─" * (EDGE - MARGIN))), total=WIDTH)


def footer(active: str) -> str:
    keys = [("1-6", "pages"), ("tab", "next"), ("jk", "move"), ("q", "quit")]
    segments = []
    position = MARGIN
    for key, label in keys:
        segments.append((position, t.fg(t.MUTED, key) + t.fg(t.FAINT, " ") + t.fg(t.DIM, label)))
        position += len(key) + len(label) + 4
    index = [key for _label, key in PAGES].index(active) + 1
    page = t.fg(t.DIM, f"{index:02d} / {len(PAGES):02d}")
    segments.append((EDGE - t.visible_width(page), page))
    return t.columns(*segments, total=WIDTH)


def overview(state: Dict) -> List[str]:
    shell = state["shell"]
    config = state["config"]
    plugins = state["plugins"]
    activity = state["activity"]
    enabled = sum(1 for row in plugins if row["state"] == "enabled")
    compositor = shell.get("compositor") or {}
    running = compositor.get("running", "")
    installed = compositor.get("installed", [])
    if running:
        compositor_text = running
    elif installed:
        compositor_text = installed[0] + " installed"
    else:
        compositor_text = "not detected"
    home = str(pathlib.Path.home())
    folder = str(config["wallpaper"] or "unset")
    if home and folder.startswith(home):
        folder = "~" + folder[len(home):]

    def recent(index: int) -> str:
        if index >= len(activity):
            return ""
        item = activity[index]
        return t.fg(t.DIM, item["stamp"]) + t.fg(t.FAINT, "   ") + t.fg(t.MUTED, item["detail"])

    left = [
        _plain_section("session"),
        _plain_field("Compositor", compositor_text),
        _plain_field("Shell", shell["active"], t.ACCENT),
        _plain_field("Instances", ", ".join(shell["running"]) if shell["running"] else "not running"),
    ]
    right = [_plain_section("recent")] + [recent(index) for index in range(3)]

    rows: List[str] = []
    for index in range(max(len(left), len(right))):
        left_text = left[index] if index < len(left) else ""
        right_text = right[index] if index < len(right) else ""
        segments = []
        if left_text:
            segments.append((MARGIN, left_text))
        if right_text:
            segments.append((54, right_text))
        rows.append(t.columns(*segments, total=WIDTH))
    rows.extend([
        _blank(),
        _section("units"),
        _field("Enabled", f"{enabled} of {len(plugins)}"),
        _field("Disabled", str(len(plugins) - enabled)),
        _blank(),
        _section("preferences"),
        _field("Theme", config["theme"]),
        _field("Language", config["language"]),
        _field("Schema", f"{config['schema']} · {config['size']} bytes"),
        _field("Wallpapers", folder, t.MUTED),
    ])
    return _body(rows)


def plugins(state: Dict, cursor: int) -> List[str]:
    entries = state["plugins"]
    enabled = sum(1 for entry in entries if entry["state"] == "enabled")
    header_row = t.columns(
        (MARGIN + 2, t.fg(t.DIM, t.pad("unit", 21))),
        (MARGIN + 24, t.fg(t.DIM, t.pad("kind", 13))),
        (MARGIN + 39, t.fg(t.DIM, t.pad("state", 11))),
        (MARGIN + 52, t.fg(t.DIM, "target")),
        total=WIDTH,
    )
    rows: List[str] = [header_row]
    for index in range(14):
        if index >= len(entries):
            rows.append(_blank())
            continue
        entry = entries[index]
        selected = index == cursor
        bar = t.fg(t.ACCENT, "▌") if selected else " "
        name = t.fg(t.TEXT, t.pad(entry["id"], 21)) if selected else t.fg(t.MUTED, t.pad(entry["id"], 21))
        raw_kind = entry["kinds"] or "-"
        kind_label = raw_kind.split(":")[0]
        kind = t.fg(t.MUTED if selected else t.DIM, t.pad(kind_label, 13))
        state_word = t.fg(t.OK, t.pad("enabled", 11)) if entry["state"] == "enabled" else t.fg(t.DIM, t.pad("disabled", 11))
        target = t.fg(t.DIM, "~/.config/" + entry["id"])
        rows.append(t.columns((MARGIN, bar), (MARGIN + 2, name), (MARGIN + 24, kind),
                              (MARGIN + 39, state_word), (MARGIN + 52, target), total=WIDTH))
    rows.append(_blank())
    rows.append(t.columns((MARGIN, t.fg(t.DIM, f"{enabled} of {len(entries)} enabled")), total=WIDTH))
    return _body(rows)


def doctor(state: Dict) -> List[str]:
    checks = state["doctor"]
    counts = {"ok": 0, "warn": 0, "bad": 0}
    for check in checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1
    summary = (
        t.fg(t.OK, f"{counts['ok']} ok")
        + t.fg(t.FAINT, "   ·   ")
        + t.fg(t.WARN, f"{counts['warn']} warn")
        + t.fg(t.FAINT, "   ·   ")
        + t.fg(t.BAD, f"{counts['bad']} bad")
    )
    rows: List[str] = [
        t.columns((MARGIN, summary), total=WIDTH),
        _blank(),
        t.columns(
            (MARGIN + 2, t.fg(t.DIM, t.pad("area", 14))),
            (MARGIN + 16, t.fg(t.DIM, t.pad("check", 20))),
            (MARGIN + 36, t.fg(t.DIM, "detail")),
            total=WIDTH,
        ),
    ]
    for check in checks:
        rows.append(t.columns(
            (MARGIN, STATUS.get(check["status"], "•")),
            (MARGIN + 2, t.fg(t.MUTED, t.pad(check["category"], 14))),
            (MARGIN + 16, t.fg(t.TEXT, t.pad(check["name"], 20))),
            (MARGIN + 36, t.fg(t.DIM, check["detail"])),
            total=WIDTH,
        ))
    return _body(rows)


def config(state: Dict) -> List[str]:
    conf = state["config"]
    home = str(pathlib.Path.home())
    folder = str(conf["wallpaper"] or "unset")
    if home and folder.startswith(home):
        folder = "~" + folder[len(home):]
    rows: List[str] = [
        _section("file"),
        _field("Path", str(conf["path"]).replace(home, "~")),
        _field("Schema", str(conf["schema"])),
        _field("Size", f"{conf['size']} bytes"),
        _blank(),
        _section("appearance"),
        _field("Theme", conf["theme"], t.ACCENT),
        _field("Language", conf["language"]),
        _blank(),
        _section("wallpapers"),
        _field("Folder", folder, t.MUTED),
        _field("Files", str(conf["wallpapers"])),
    ]
    return _body(rows)


def shell(state: Dict) -> List[str]:
    info = state["shell"]
    rows: List[str] = [
        _section("runtime"),
        _field("Active", info["active"], t.ACCENT),
        _field("Instances", ", ".join(info["running"]) if info["running"] else "not running"),
        _blank(),
        _section("targets"),
    ]
    targets = [
        ("nyxuri-shell", info["binary_exists"], info["binary"] or "not resolvable"),
        ("noctalia", False, "not installed"),
    ]
    for name, ready, detail in targets:
        rows.append(t.columns(
            (MARGIN, STATUS["ok"] if ready else t.fg(t.DIM, "•")),
            (MARGIN + 2, t.fg(t.TEXT if ready else t.MUTED, t.pad(name, 18))),
            (MARGIN + 20, t.fg(t.OK if ready else t.DIM, t.pad("ready" if ready else "unavailable", 13))),
            (MARGIN + 34, t.fg(t.DIM, detail)),
            total=WIDTH,
        ))
    rows.append(_blank())
    rows.append(_section("events"))
    for name, detail in (("unit reload", "ledger changes reach the running shell"),
                         ("theme sync", "mode changes follow the shell"),
                         ("readiness", "bounded probe with cold-start budget")):
        rows.append(t.columns(
            (MARGIN + 2, t.fg(t.MUTED, t.pad(name, 14))),
            (MARGIN + 18, t.fg(t.DIM, detail)),
            total=WIDTH,
        ))
    return _body(rows)


def snapshots(state: Dict, cursor: int) -> List[str]:
    entries = state["snapshots"]
    if not entries:
        return _body([
            t.columns((MARGIN, t.fg(t.MUTED, "no snapshots yet")), total=WIDTH),
            t.columns((MARGIN, t.fg(t.DIM, "press s to save the current configuration")), total=WIDTH),
            _blank(),
            t.columns((MARGIN, t.fg(t.DIM, "backups live in ~/.config/nyxuri/backups")), total=WIDTH),
        ])
    rows: List[str] = [
        t.columns(
            (MARGIN + 2, t.fg(t.DIM, t.pad("snapshot", 24))),
            (MARGIN + 26, t.fg(t.DIM, t.pad("note", 20))),
            (MARGIN + 48, t.fg(t.DIM, "files")),
            total=WIDTH,
        )
    ]
    for index in range(14):
        if index >= len(entries):
            rows.append(_blank())
            continue
        entry = entries[index]
        selected = index == cursor
        bar = t.fg(t.ACCENT, "▌") if selected else " "
        name = t.fg(t.TEXT, t.pad(entry["name"], 24)) if selected else t.fg(t.MUTED, t.pad(entry["name"], 24))
        rows.append(t.columns(
            (MARGIN, bar),
            (MARGIN + 2, name),
            (MARGIN + 26, t.fg(t.DIM, t.pad(entry["note"], 20))),
            (MARGIN + 48, t.fg(t.MUTED, entry["files"])),
            total=WIDTH,
        ))
    return _body(rows)


def build(name: str, state: Dict, cursor: int, version: str) -> List[str]:
    root = pathlib.Path(__file__).resolve().parents[3]
    mode = "local" if root.joinpath("nyxuri").is_dir() else "installed"
    bodies = {
        "overview": lambda: overview(state),
        "plugins": lambda: plugins(state, cursor),
        "doctor": lambda: doctor(state),
        "config": lambda: config(state),
        "shell": lambda: shell(state),
        "snapshots": lambda: snapshots(state, cursor),
    }
    lines: List[str] = [
        _blank(),
        header(version, mode),
        _blank(),
        navigation(name),
        _blank(),
    ]
    lines.extend(bodies.get(name, lambda: overview(state))())
    while len(lines) < HEIGHT - 2:
        lines.append(_blank())
    lines.append(hairline())
    lines.append(footer(name))
    return [t.pad(line, WIDTH) for line in lines[:HEIGHT]]
