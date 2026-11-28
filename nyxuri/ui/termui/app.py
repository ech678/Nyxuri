from __future__ import annotations

import pathlib
import sys
from typing import Dict, List

import pytermgui as ptg

from . import data, screens

VERSION = "v4.0.0-alpha.2"
NAMES = [key for _label, key in screens.PAGES]
CURSOR_LIMITS = {"plugins": "plugins", "snapshots": "snapshots"}


def collect() -> Dict:
    state = data.snapshot_state()
    state["doctor"] = data.doctor_rows()
    return state


def build_window(lines: List[str]) -> ptg.Window:
    labels = [ptg.Label(line, parent_align=ptg.HorizontalAlignment.LEFT) for line in lines]
    window = ptg.Window(
        *labels,
        box=ptg.boxes.EMPTY,
        parent_align=ptg.HorizontalAlignment.LEFT,
    )
    window.width = screens.WIDTH + 2
    window.height = screens.HEIGHT + 2
    return window


def render(name: str, state: Dict, cursor: int) -> str:
    lines = screens.build(name, state, cursor, VERSION)
    window = build_window(lines)
    return "\n".join(window.get_lines())


def clamp(name: str, cursor: int, state: Dict) -> int:
    key = CURSOR_LIMITS.get(name)
    if key is None:
        return 0
    total = len(state.get(key, []))
    if total <= 0:
        return 0
    return max(0, min(cursor, total - 1))


def draw(name: str, state: Dict, cursor: int) -> None:
    frame = render(name, state, cursor)
    sys.stdout.write("\x1b[H\x1b[2J")
    sys.stdout.write(frame)
    sys.stdout.write("\n")
    sys.stdout.flush()


def interactive(start: str = "overview") -> int:
    state = collect()
    name = start if start in NAMES else "overview"
    cursor = 0
    message = ""
    draw(name, state, cursor)
    while True:
        key = ptg.getch()
        if key is None:
            continue
        if key in ("q", "Q", "\x03", "\x1b"):
            sys.stdout.write("\x1b[H\x1b[2J")
            sys.stdout.flush()
            return 0
        if key in ("\x1b[C", "\t"):
            index = (NAMES.index(name) + 1) % len(NAMES)
            name = NAMES[index]
            cursor = 0
        elif key in ("\x1b[D",):
            index = (NAMES.index(name) - 1) % len(NAMES)
            name = NAMES[index]
            cursor = 0
        elif key in [str(number) for number in range(1, 7)]:
            name = NAMES[int(key) - 1]
            cursor = 0
        elif key in ("\x1b[B", "j"):
            cursor = clamp(name, cursor + 1, state)
        elif key in ("\x1b[A", "k"):
            cursor = clamp(name, cursor - 1, state)
        elif key in ("\r", "\n"):
            message = f"{name} · {cursor + 1} selected"
        elif key == "/":
            message = "search is not wired in this preview"
        else:
            message = ""
        draw(name, state, cursor)


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
