from __future__ import annotations

import pathlib
import shutil
from typing import Dict, List, Tuple

from . import theme as t

WIDTH = 98
HEIGHT = 28
BODY_OFFSET = 5

PAGES: List[Tuple[str, str]] = [
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


def terminal_size() -> Tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(WIDTH + 2, HEIGHT + 2))
    width = max(44, min(WIDTH, size.columns - 2))
    height = max(14, min(HEIGHT, size.lines - 2))
    return width, height


class Frame:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.margin = 4 if width >= 64 else 2
        self.body_rows = max(4, height - (BODY_OFFSET + 2))

    def blank(self) -> str:
        return " " * self.width

    def row(self, *segments) -> str:
        return t.columns(*segments, total=self.width)

    def fit(self, text: str) -> str:
        return t.pad(text, self.width)

    def section(self, title: str) -> str:
        return self.row((self.margin, t.fg(t.DIM, title.upper())))

    def field(self, label: str, value: str, value_color: str = t.TEXT,
              label_width: int = 0) -> str:
        width = label_width or self.label_width()
        return self.row((self.margin, t.fg(t.MUTED, t.pad(label, width))),
                        (self.margin + width, t.fg(value_color, value)))

    def label_width(self) -> int:
        return max(12, min(22, self.width // 4))

    def header(self, version: str, mode: str) -> str:
        brand = t.bold(t.fg(t.TEXT, "nyxuri"))
        meta = t.fg(t.DIM, version) + t.fg(t.FAINT, "   ·   ") + t.fg(t.MUTED, mode)
        if t.visible_width(meta) + self.margin * 2 + 12 > self.width:
            meta = t.fg(t.DIM, version)
        right = self.width - self.margin - t.visible_width(meta)
        return self.row((self.margin, brand), (right, meta))

    def navigation(self, active: str) -> str:
        labels = [(label, key) for label, key in PAGES]
        position = self.margin
        segments = []
        for label, key in labels:
            styled = t.bold(t.fg(t.ACCENT, label)) if key == active else t.fg(t.MUTED, label)
            if position + len(label) > self.width - self.margin:
                break
            segments.append((position, styled))
            position += len(label) + 3
        total = t.visible_width("".join(label for label, _key in labels)) + 3 * (len(labels) - 1)
        if total + self.margin * 2 > self.width:
            current = dict((key, label) for label, key in PAGES)[active]
            index = [key for _label, key in PAGES].index(active) + 1
            text = t.bold(t.fg(t.ACCENT, current)) + t.fg(t.FAINT, f"   {index}/{len(PAGES)}")
            return self.row((self.margin, text))
        return self.row(*segments)

    def hairline(self) -> str:
        return self.row((self.margin, t.fg(t.FAINT, "─" * (self.width - self.margin * 2))))

    def footer(self, active: str) -> str:
        keys = [("1-6", "pages"), ("tab", "next"), ("jk", "move"), ("q", "quit")]
        segments = []
        position = self.margin
        for key, label in keys:
            if position + len(key) + len(label) + 4 > self.width - self.margin - 8:
                break
            segments.append((position, t.fg(t.MUTED, key) + t.fg(t.FAINT, " ") + t.fg(t.DIM, label)))
            position += len(key) + len(label) + 4
        index = [key for _label, key in PAGES].index(active) + 1
        page = t.fg(t.DIM, f"{index:02d} / {len(PAGES):02d}")
        segments.append((self.width - self.margin - t.visible_width(page), page))
        return self.row(*segments)


def _recent(state: Dict, index: int) -> str:
    activity = state["activity"]
    if index >= len(activity):
        return ""
    item = activity[index]
    return t.fg(t.DIM, item["stamp"]) + t.fg(t.FAINT, "   ") + t.fg(t.MUTED, item["detail"])


def overview(frame: Frame, state: Dict) -> List[str]:
    shell = state["shell"]
    config = state["config"]
    plugins = state["plugins"]
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

    show_recent = frame.width >= 88
    recent_column = frame.width - frame.margin - 38

    left = [
        frame.section("session"),
        frame.field("Compositor", compositor_text),
        frame.field("Shell", shell["active"], t.ACCENT),
        frame.field("Instances", ", ".join(shell["running"]) if shell["running"] else "not running"),
    ]
    right = [frame.section("recent")] + [_recent(state, index) for index in range(3)]

    rows: List[str] = []
    for index in range(max(len(left), len(right)) if show_recent else len(left)):
        segments = []
        if index < len(left):
            segments.append((frame.margin, left[index][frame.margin:]))
        if show_recent and index < len(right) and right[index]:
            segments.append((recent_column, right[index]))
        rows.append(frame.row(*segments) if segments else frame.blank())
    rows.extend([
        frame.blank(),
        frame.section("units"),
        frame.field("Enabled", f"{enabled} of {len(plugins)}"),
        frame.field("Disabled", str(len(plugins) - enabled)),
        frame.blank(),
        frame.section("preferences"),
        frame.field("Theme", config["theme"]),
        frame.field("Language", config["language"]),
        frame.field("Schema", f"{config['schema']} · {config['size']} bytes"),
        frame.field("Wallpapers", folder, t.MUTED),
    ])
    return rows


def _window(cursor: int, total: int, visible: int) -> Tuple[int, int]:
    if total <= visible:
        return 0, total
    offset = max(0, min(cursor - visible + 1, total - visible))
    return offset, min(total, offset + visible)


def plugins(frame: Frame, state: Dict, cursor: int) -> List[str]:
    entries = state["plugins"]
    total = len(entries)
    enabled = sum(1 for entry in entries if entry["state"] == "enabled")
    show_kind = frame.width >= 76
    show_target = frame.width >= 92
    margin = frame.margin
    name_width = 21 if frame.width >= 76 else 18
    kind_column = margin + 2 + name_width + 2
    state_column = kind_column + (13 + 2 if show_kind else 0)
    target_column = state_column + 13

    visible = max(3, frame.body_rows - 3)
    offset, end = _window(cursor, total, visible)

    header_segments = [(margin + 2, t.fg(t.DIM, t.pad("unit", name_width)))]
    if show_kind:
        header_segments.append((kind_column, t.fg(t.DIM, t.pad("kind", 13))))
    header_segments.append((state_column, t.fg(t.DIM, t.pad("state", 11))))
    if show_target:
        header_segments.append((target_column, t.fg(t.DIM, "target")))
    rows: List[str] = [frame.row(*header_segments)]

    for index in range(offset, end):
        entry = entries[index]
        selected = index == cursor
        bar = t.fg(t.ACCENT, "▌") if selected else " "
        name = t.fg(t.TEXT, t.pad(entry["id"], name_width)) if selected else t.fg(t.MUTED, t.pad(entry["id"], name_width))
        segments = [(margin, bar), (margin + 2, name)]
        if show_kind:
            kind_label = (entry["kinds"] or "-").split(":")[0]
            color = t.MUTED if selected else t.DIM
            segments.append((kind_column, t.fg(color, t.pad(kind_label, 13))))
        state_color = t.OK if entry["state"] == "enabled" else t.DIM
        segments.append((state_column, t.fg(state_color, t.pad(entry["state"], 11))))
        if show_target:
            segments.append((target_column, t.fg(t.DIM, "~/.config/" + entry["id"])))
        rows.append(frame.row(*segments))

    rows.append(frame.blank())
    if total > visible:
        summary = f"{offset + 1}-{end} of {total} · {enabled} enabled"
    else:
        summary = f"{enabled} of {total} enabled"
    rows.append(frame.row((margin, t.fg(t.DIM, summary))))
    return rows


def doctor(frame: Frame, state: Dict) -> List[str]:
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
    margin = frame.margin
    rows: List[str] = [
        frame.row((margin, summary)),
        frame.blank(),
        frame.row(
            (margin + 2, t.fg(t.DIM, t.pad("area", 14))),
            (margin + 16, t.fg(t.DIM, t.pad("check", 20))),
            (margin + 36, t.fg(t.DIM, "detail")),
        ),
    ]
    for check in checks[: max(1, frame.body_rows - 4)]:
        detail = check["detail"]
        rows.append(frame.row(
            (margin, STATUS.get(check["status"], "•")),
            (margin + 2, t.fg(t.MUTED, t.pad(check["category"], 14))),
            (margin + 16, t.fg(t.TEXT, t.pad(check["name"], 20))),
            (margin + 36, t.fg(t.DIM, detail)),
        ))
    return rows


def config(frame: Frame, state: Dict) -> List[str]:
    conf = state["config"]
    home = str(pathlib.Path.home())
    folder = str(conf["wallpaper"] or "unset")
    if home and folder.startswith(home):
        folder = "~" + folder[len(home):]
    return [
        frame.section("file"),
        frame.field("Path", str(conf["path"]).replace(home, "~")),
        frame.field("Schema", str(conf["schema"])),
        frame.field("Size", f"{conf['size']} bytes"),
        frame.blank(),
        frame.section("appearance"),
        frame.field("Theme", conf["theme"], t.ACCENT),
        frame.field("Language", conf["language"]),
        frame.blank(),
        frame.section("wallpapers"),
        frame.field("Folder", folder, t.MUTED),
        frame.field("Files", str(conf["wallpapers"])),
    ]


def shell(frame: Frame, state: Dict) -> List[str]:
    info = state["shell"]
    margin = frame.margin
    rows: List[str] = [
        frame.section("runtime"),
        frame.field("Active", info["active"], t.ACCENT),
        frame.field("Instances", ", ".join(info["running"]) if info["running"] else "not running"),
        frame.blank(),
        frame.section("targets"),
    ]
    targets = [
        ("nyxuri-shell", info["binary_exists"], info["binary"] or "not resolvable"),
        ("noctalia", False, "not installed"),
    ]
    for name, ready, detail in targets:
        rows.append(frame.row(
            (margin, STATUS["ok"] if ready else t.fg(t.DIM, "•")),
            (margin + 2, t.fg(t.TEXT if ready else t.MUTED, t.pad(name, 18))),
            (margin + 20, t.fg(t.OK if ready else t.DIM, t.pad("ready" if ready else "unavailable", 13))),
            (margin + 34, t.fg(t.DIM, detail)),
        ))
    rows.append(frame.blank())
    rows.append(frame.section("events"))
    for name, detail in (("unit reload", "ledger changes reach the running shell"),
                         ("theme sync", "mode changes follow the shell"),
                         ("readiness", "bounded probe with cold-start budget")):
        rows.append(frame.row(
            (margin + 2, t.fg(t.MUTED, t.pad(name, 14))),
            (margin + 18, t.fg(t.DIM, detail)),
        ))
    return rows


def snapshots(frame: Frame, state: Dict, cursor: int) -> List[str]:
    entries = state["snapshots"]
    margin = frame.margin
    if not entries:
        return [
            frame.row((margin, t.fg(t.MUTED, "no snapshots yet"))),
            frame.row((margin, t.fg(t.DIM, "press s to save the current configuration"))),
            frame.blank(),
            frame.row((margin, t.fg(t.DIM, "backups live in ~/.config/nyxuri/backups"))),
        ]
    show_note = frame.width >= 72
    show_files = frame.width >= 88
    name_width = 24 if frame.width >= 72 else 18
    note_column = margin + 2 + name_width
    files_column = note_column + 20

    visible = max(3, frame.body_rows - 2)
    offset, end = _window(cursor, len(entries), visible)

    header_segments = [(margin + 2, t.fg(t.DIM, t.pad("snapshot", name_width)))]
    if show_note:
        header_segments.append((note_column, t.fg(t.DIM, t.pad("note", 20))))
    if show_files:
        header_segments.append((files_column, t.fg(t.DIM, "files")))
    rows: List[str] = [frame.row(*header_segments)]

    for index in range(offset, end):
        entry = entries[index]
        selected = index == cursor
        bar = t.fg(t.ACCENT, "▌") if selected else " "
        name = t.fg(t.TEXT, t.pad(entry["name"], name_width)) if selected else t.fg(t.MUTED, t.pad(entry["name"], name_width))
        segments = [(margin, bar), (margin + 2, name)]
        if show_note:
            segments.append((note_column, t.fg(t.DIM, t.pad(entry["note"], 20))))
        if show_files:
            segments.append((files_column, t.fg(t.MUTED, entry["files"])))
        rows.append(frame.row(*segments))
    if len(entries) > visible:
        rows.append(frame.blank())
        rows.append(frame.row((margin, t.fg(t.DIM, f"{offset + 1}-{end} of {len(entries)}"))))
    return rows


def build(name: str, state: Dict, cursor: int, version: str,
          width: int = WIDTH, height: int = HEIGHT) -> List[str]:
    frame = Frame(width, height)
    root = pathlib.Path(__file__).resolve().parents[3]
    mode = "local" if root.joinpath("nyxuri").is_dir() else "installed"
    bodies = {
        "overview": lambda: overview(frame, state),
        "plugins": lambda: plugins(frame, state, cursor),
        "doctor": lambda: doctor(frame, state),
        "config": lambda: config(frame, state),
        "shell": lambda: shell(frame, state),
        "snapshots": lambda: snapshots(frame, state, cursor),
    }
    body = bodies.get(name, lambda: overview(frame, state))()
    lines: List[str] = [
        frame.blank(),
        frame.header(version, mode),
        frame.blank(),
        frame.navigation(name),
        frame.blank(),
    ]
    lines.extend(body[: frame.body_rows])
    while len(lines) < height - 2:
        lines.append(frame.blank())
    lines.append(frame.hairline())
    lines.append(frame.footer(name))
    return [frame.fit(line) for line in lines[:height]]
