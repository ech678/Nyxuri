from __future__ import annotations

import pathlib
import sys
from typing import Dict, List

import pytermgui as ptg

from . import data, screens

VERSION = "v4.0.0-alpha.2"
NAMES = [key for _label, key in screens.PAGES]
CURSOR_LIMITS = {"plugins": "plugins", "snapshots": "snapshots"}

CSI_KEYS = {
    "A": "up",
    "B": "down",
    "C": "right",
    "D": "left",
    "Z": "backtab",
    "H": "home",
    "F": "end",
}


def collect() -> Dict:
    state = data.snapshot_state()
    state["doctor"] = data.doctor_rows()
    return state


def build_window(lines: List[str], width: int, height: int) -> ptg.Window:
    labels = [ptg.Label(line, parent_align=ptg.HorizontalAlignment.LEFT) for line in lines]
    window = ptg.Window(
        *labels,
        box=ptg.boxes.EMPTY,
        parent_align=ptg.HorizontalAlignment.LEFT,
    )
    window.width = width + 2
    window.height = height + 2
    return window


def render(name: str, state: Dict, cursor: int, width: int = screens.WIDTH,
           height: int = screens.HEIGHT) -> str:
    lines = screens.build(name, state, cursor, VERSION, width=width, height=height)
    window = build_window(lines, width, height)
    return "\n".join(window.get_lines())


def clamp(name: str, cursor: int, state: Dict) -> int:
    key = CURSOR_LIMITS.get(name)
    if key is None:
        return 0
    total = len(state.get(key, []))
    if total <= 0:
        return 0
    return max(0, min(cursor, total - 1))


def parse_keys(chunk: str) -> List[str]:
    keys: List[str] = []
    index = 0
    length = len(chunk)
    while index < length:
        char = chunk[index]
        if char == "\x1b":
            if index + 1 < length and chunk[index + 1] == "[":
                end = index + 2
                while end < length and not ("@" <= chunk[end] <= "~"):
                    end += 1
                if end < length:
                    keys.append(CSI_KEYS.get(chunk[end], "unknown"))
                    index = end + 1
                    continue
                keys.append("esc")
                index = length
                continue
            if index + 1 < length and chunk[index + 1] == "O":
                if index + 2 < length:
                    keys.append(CSI_KEYS.get(chunk[index + 2], "unknown"))
                    index += 3
                    continue
                keys.append("esc")
                index = length
                continue
            keys.append("esc")
            index += 1
            continue
        if char == "\t":
            keys.append("tab")
        elif char == "\x03":
            keys.append("interrupt")
        elif char in "\r\n":
            keys.append("enter")
        else:
            keys.append("char:" + char)
        index += 1
    return keys


def draw(name: str, state: Dict, cursor: int) -> None:
    width, height = screens.terminal_size()
    frame = render(name, state, cursor, width, height)
    lines = frame.split("\n")
    chunks = ["\x1b[H"]
    for index, line in enumerate(lines):
        chunks.append(line + "\x1b[K")
        if index != len(lines) - 1:
            chunks.append("\n")
    chunks.append("\x1b[J")
    sys.stdout.write("".join(chunks))
    sys.stdout.flush()


def interactive(start: str = "overview") -> int:
    state = collect()
    name = start if start in NAMES else "overview"
    cursor = 0
    sys.stdout.write("\x1b[?25l\x1b[H\x1b[2J")
    sys.stdout.flush()
    try:
        draw(name, state, cursor)
        while True:
            chunk = ptg.getch()
            if not chunk:
                continue
            for key in parse_keys(chunk):
                if key in ("esc", "interrupt", "char:q", "char:Q"):
                    return 0
                if key in ("tab", "right"):
                    name = NAMES[(NAMES.index(name) + 1) % len(NAMES)]
                    cursor = 0
                elif key in ("backtab", "left"):
                    name = NAMES[(NAMES.index(name) - 1) % len(NAMES)]
                    cursor = 0
                elif key in ("char:1", "char:2", "char:3", "char:4", "char:5", "char:6"):
                    name = NAMES[int(key[-1]) - 1]
                    cursor = 0
                elif key in ("down", "char:j"):
                    cursor = clamp(name, cursor + 1, state)
                elif key in ("up", "char:k"):
                    cursor = clamp(name, cursor - 1, state)
                elif key in ("home", "char:g"):
                    cursor = 0
                elif key in ("end", "char:G"):
                    total = len(state.get(CURSOR_LIMITS.get(name, ""), []))
                    cursor = max(0, total - 1)
            draw(name, state, cursor)
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[H\x1b[2J")
        sys.stdout.flush()
    return 0


def dump(output_dir: pathlib.Path) -> int:
    from . import capture

    output_dir.mkdir(parents=True, exist_ok=True)
    state = collect()
    for index, name in enumerate(NAMES):
        frame = render(name, state, 0)
        target = output_dir / f"{index + 1:02d}-{name}.png"
        capture.frame_to_png(frame, target)
        print(f"wrote {target}")
    return 0


def main(argv: List[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("--dump", "dump"):
        out = pathlib.Path(args[1]).expanduser() if len(args) > 1 else pathlib.Path.home() / "tui-design"
        return dump(out)
    start = "overview"
    if args and args[0] == "--tab" and len(args) > 1:
        start = args[1]
    if not sys.stdout.isatty():
        state = collect()
        sys.stdout.write(render(start, state, 0) + "\n")
        return 0
    return interactive(start)


if __name__ == "__main__":
    raise SystemExit(main())
