"""TUI component and terminal presentation engine (Native ANSI + Standard Library)."""

import atexit
import os
import re
import select
import shutil
import signal
import sys
import termios
import time
import tty
import unicodedata
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from nyxniri.constants import Colors
from nyxniri.core import Environment, get_env
from nyxniri.i18n import msg

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class TerminalGuard:
    """Fail-safe guard that guarantees terminal attributes and cursor visibility are restored."""
    _orig_attr: Optional[List[Any]] = None
    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        if cls._initialized:
            return
        if sys.stdin.isatty():
            try:
                cls._orig_attr = termios.tcgetattr(sys.stdin.fileno())
            except Exception:
                cls._orig_attr = None
            atexit.register(cls.restore)
            signal.signal(signal.SIGINT, cls._sig_handler)
            signal.signal(signal.SIGTERM, cls._sig_handler)
        cls._initialized = True

    @classmethod
    def restore(cls) -> None:
        if cls._orig_attr and sys.stdin.isatty():
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, cls._orig_attr)
            except Exception:
                pass
        # Belt-and-suspenders: if a signal crashed a mouse-enabled loop before
        # interactive_screen's finally ran, disable tracking + show cursor so
        # the terminal isn't left in a quirked state.
        sys.stdout.write("\033[?1006l\033[?1002l")
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()

    @classmethod
    def _sig_handler(cls, signum: int, frame: Any) -> None:
        cls.restore()
        sys.stdout.write("\n")
        sys.exit(130)


TerminalGuard.init()


# --- Geometric Column Alignment ---
def display_width(text: str) -> int:
    """Calculate the real physical terminal column width of a string (CJK = 2 cols)."""
    clean_text = ANSI_ESCAPE_RE.sub("", text)
    return sum(
        0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        for ch in clean_text
    )


def pad_display(text: str, width: int) -> str:
    """Pad string with trailing spaces to achieve exact visual column alignment."""
    curr = display_width(text)
    if curr < width:
        return text + (" " * (width - curr))
    return text


def truncate_display(text: str, width: int, suffix: str = "…") -> str:
    """Clip ANSI-styled text to a physical terminal width without splitting CJK glyphs."""
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text

    suffix_width = display_width(suffix)
    content_width = max(0, width - suffix_width)
    output: List[str] = []
    used = 0
    pos = 0
    while pos < len(text):
        match = ANSI_ESCAPE_RE.match(text, pos)
        if match:
            output.append(match.group(0))
            pos = match.end()
            continue
        char = text[pos]
        char_width = 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if used + char_width > content_width:
            break
        output.append(char)
        used += char_width
        pos += 1
    reset = Colors.RESET if ANSI_ESCAPE_RE.search(text) else ""
    return "".join(output) + suffix + reset


def responsive_hint(key: str) -> str:
    """Use compact control hints when the terminal cannot hold the full legend."""
    if shutil.get_terminal_size((80, 24)).columns >= 72:
        return msg(key)
    short_keys = {
        "menu_hint": "menu_hint_short",
        "submenu_hint": "submenu_hint_short",
        "selective_hint": "checklist_hint_short",
        "delete_snapshot_hint": "checklist_hint_short",
        "dep_menu_hint": "checklist_hint_short",
        "opt_apps_menu_hint": "checklist_hint_short",
        "summary_action_hint": "summary_action_hint_short",
        "preset_switcher_hint": "preset_switcher_hint_short",
    }
    return msg(short_keys.get(key, key))


# --- Single Key Event Listener ---
@dataclass
class MouseEvent:
    """A decoded SGR mouse report (``\\x1b[<btn;col;row(M|m)``).

    Only emitted when the caller enabled mouse tracking via
    ``interactive_screen(mouse=True)``; otherwise no such sequence reaches
    read_key(). ``kind`` is one of PRESS / WHEEL_UP / WHEEL_DOWN. col/row are
    1-based terminal coordinates matching cursor-position addressing.
    """
    kind: str
    col: int
    row: int


_MOUSE_RE = re.compile(rb"\x1b\[<(\d+);(\d+);(\d+)([Mm])")


def read_key() -> Any:
    """Listen for a single keyboard event using raw unbuffered OS file descriptor reads.

    Returns a ``str`` for keyboard events, or a ``MouseEvent`` when the caller
    has enabled SGR mouse tracking. Mouse tracking is off by default, so for
    every component but PresetSwitcher(mouse=True) no mouse sequence ever
    arrives and the mouse branch is inert.
    """
    if not sys.stdin.isatty():
        return "ENTER"

    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        raw_bytes = os.read(fd, 1)
        if not raw_bytes:
            return "EOF"
        if raw_bytes == b"\x1b":
            ready, _, _ = select.select([fd], [], [], 0.05)
            if ready:
                raw_bytes += os.read(fd, 31)

        # 1. Standalone ESC
        if raw_bytes == b"\x1b":
            return "ESC"

        # 2. SGR mouse report (\x1b[<btn;col;row(M|m)) — only when caller enabled tracking
        m = _MOUSE_RE.match(raw_bytes)
        if m:
            btn = int(m.group(1))
            col = int(m.group(2))
            row = int(m.group(3))
            release = m.group(4) == b"m"
            if release:
                return "MOUSE_RELEASE"
            # SGR button encoding: low bits = button, +8 = wheel, +64 = motion
            if btn & 64:
                kind = "WHEEL_DOWN" if (btn & 1) else "WHEEL_UP"
            else:
                kind = "PRESS"
            return MouseEvent(kind=kind, col=col, row=row)

        # 3. Arrow keys (CSI: \x1b[ and SS3: \x1bO)
        if raw_bytes in (b"\x1b[A", b"\x1bOA"):
            return "UP"
        if raw_bytes in (b"\x1b[B", b"\x1bOB"):
            return "DOWN"
        if raw_bytes in (b"\x1b[C", b"\x1bOC"):
            return "RIGHT"
        if raw_bytes in (b"\x1b[D", b"\x1bOD"):
            return "LEFT"

        # 4. CSI Extended keys (Home, End, PageUp, PageDown)
        if raw_bytes.startswith(b"\x1b["):
            code = raw_bytes[2:]
            if code in (b"H", b"1~"):
                return "HOME"
            if code in (b"F", b"4~"):
                return "END"
            if code == b"5~":
                return "PAGEUP"
            if code == b"6~":
                return "PAGEDOWN"
            return "ESC"

        # 5. Standard control keys
        if raw_bytes in (b"\r", b"\n"):
            return "ENTER"
        if raw_bytes == b" ":
            return "SPACE"
        if raw_bytes in (b"\x03", b"\x04"):  # Ctrl+C / Ctrl+D — both exit
            return "EXIT"

        # 6. Normal UTF-8 single character
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)

# --- Loop-scoped raw input (kills the cooked-echo window between keys) ---
def _swallow_repeat(fd: int, quiet: float = 0.05, cap: float = 2.0) -> None:
    """Keep draining bytes until `quiet` seconds pass with no new input.

    Absorbs an OS auto-repeat burst (held key) until the user releases, so the
    repeated bytes don't feed the next read_key() and cascade. The quiet window
    (~50ms) reliably exceeds a standard ~33ms auto-repeat interval, so silence
    means release. Hard-capped so a runaway stream can't pin the loop.
    """
    end = time.time() + cap
    while time.time() < end:
        ready, _, _ = select.select([fd], [], [], quiet)
        if not ready:
            return  # quiet window elapsed → key released
        try:
            if os.read(fd, 64) == b"":
                return
        except OSError:
            return


def _drain_pending(fd: int, debounce: bool = False) -> None:
    """Discard pending input; optionally debounce-swallow the auto-repeat tail.

    Two modes:
    - ``debounce=False`` (component *entry*): one non-blocking sweep of bytes
      already queued from the previous component. No wait if empty → zero
      latency on a clean transition.
    - ``debounce=True`` (after an *action* key, e.g. the Enter that confirms):
      sweep, then keep swallowing until a quiet window — the OS auto-repeat
      stream arrives ~30ms *after* the legitimate key, so a snapshot sweep
      runs in the gap and misses it; only a timed quiet-wait catches the tail.
      Called in each loop's ``finally`` so every exit (the action that caused it)
      drains its own repeat burst before the next component reads.

    A held Enter otherwise cascades: repeat bytes feed the next read_key().
    """
    found = False
    while True:
        ready, _, _ = select.select([fd], [], [], 0)
        if not ready:
            break
        try:
            if os.read(fd, 64) == b"":
                return
        except OSError:
            return
        found = True
    if debounce or found:
        _swallow_repeat(fd)


@contextmanager
def raw_input_mode(fd: int):
    """Hold stdin in echo-off raw mode for an interactive loop's duration.

    read_key() toggles raw↔cooked per call; the cooked echo window between calls
    echoed held/auto-repeated Enter as newlines and let the buffered bytes
    cascade into the next prompt. Holding raw for the whole loop removes that
    window. OPOST is re-enabled so the loop's ``\\n`` renders still become
    ``\\r\\n`` (no staircase); ISIG stays off so Ctrl+C arrives as ``\\x03``
    (handled as EXIT, same as the per-call read_key path).

    No-op when stdin is not a real tty: tests patch isatty + read_key, the real
    fd isn't a tty, tcgetattr raises and we skip — the loop then reads the patch.
    """
    old = None
    try:
        if sys.stdin.isatty():
            old = termios.tcgetattr(fd)
            tty.setraw(fd)
            new = termios.tcgetattr(fd)
            new[1] |= termios.OPOST  # keep \n -> \r\n translation on output
            termios.tcsetattr(fd, termios.TCSANOW, new)
    except Exception:
        old = None
    try:
        yield
    finally:
        if old is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except Exception:
                pass


def drain_stdin() -> None:
    """Drain pending input for cooked-line callers (snapshot note / rollback index).

    A brief raw pass that reliably discards leftover bytes (canonical mode's
    select+read is unreliable for partial lines), then restores cooked for readline.
    """
    if not sys.stdin.isatty():
        return
    with raw_input_mode(sys.stdin.fileno()):
        _drain_pending(sys.stdin.fileno())

# --- Rendering Primitives & Screen Cleaners ---
def clear_screen() -> None:
    """Clear the visible terminal without destroying scrollback history."""
    if sys.stdin.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

def write_cleared(text: str) -> None:
    """Write text, ensuring each line has \\033[K before \\n to wipe right-side ghost chars."""
    if not text:
        return
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            sys.stdout.write(line)
        else:
            sys.stdout.write(f"{line}\033[K\n")


# --- Loop scaffold (shared by Menu / CheckboxList / PresetSwitcher / select_language) ---
RESERVED_ROWS = 18  # per-frame vertical budget: logo + title + hint


@contextmanager
def interactive_screen(clear_first: bool = True, mouse: bool = False):
    """Shared scaffolding for a full-screen interactive loop.

    Clears once on entry (unless ``clear_first=False``), enters echo-off raw
    mode, hides the cursor, and drains stale input; yields the stdin fd. On
    exit (return, exception, or SystemExit) it drains the auto-repeat burst,
    restores cooked mode, disables mouse tracking if it was enabled, and
    re-shows the cursor — the body only owns the per-frame redraw
    (``\\033[H`` + show_logo + rows + hint) and key dispatch.

    ``mouse=True`` enables SGR mouse tracking (1002 + 1006) for the loop's
    lifetime; read_key() then yields MouseEvent for clicks/wheel. Off by
    default so non-mouse components see no mouse sequence at all.
    """
    fd = sys.stdin.fileno()
    if clear_first:
        clear_screen()
    sys.stdout.write(Colors.CURSOR_HIDE)
    if mouse:
        # 1002 = button-event tracking, 1006 = SGR coordinate encoding
        sys.stdout.write("\033[?1002h\033[?1006h")
    stack = ExitStack()
    stack.enter_context(raw_input_mode(fd))
    try:
        _drain_pending(fd)
        yield fd
    finally:
        _drain_pending(fd, debounce=True)
        stack.close()
        if mouse:
            sys.stdout.write("\033[?1006l\033[?1002l")
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()


def show_logo(env: Optional[Environment] = None) -> int:
    """Render the official NyxNiri ASCII brand header.

    Returns the number of terminal rows written, so callers that track absolute
    row positions (e.g. PresetSwitcher mouse hit-mapping) can account for the
    header height without re-deriving the layout branches here.
    """
    if env is None:
        env = get_env()

    terminal = shutil.get_terminal_size((80, 24))
    if terminal.columns < 66 or terminal.lines < 20:
        mode_line = truncate_display(f"Mode: {env.mode_label} ({env.repo_dir})", max(12, terminal.columns - 4))
        logo = (
            f"{Colors.BOLD_PURPLE}\n  NYX NIRI{Colors.RESET}  "
            f"{Colors.BOLD_WHITE}{env.version}{Colors.RESET}\n"
            f"  {Colors.DARK_GRAY}{mode_line}{Colors.RESET}\n\n"
        )
        write_cleared(logo)
        return logo.count("\n")

    mode_line = truncate_display(
        f"Mode: {env.mode_label} ({env.repo_dir})",
        max(12, terminal.columns - 4),
    )
    logo = (
        f"{Colors.BOLD_PURPLE}\n"
        " ███╗   ██╗██╗   ██╗██╗  ██╗    ███╗   ██╗██╗██████╗ ██╗\n"
        " ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝    ████╗  ██║██║██╔══██╗██║\n"
        " ██╔██╗ ██║ ╚████╔╝  ╚███╔╝     ██╔██╗ ██║██║██████╔╝██║\n"
        " ██║╚██╗██║  ╚██╔╝   ██╔██╗     ██║╚██╗██║██║██╔══██╗██║\n"
        " ██║ ╚████║   ██║   ██╔╝ ██╗    ██║ ╚████║██║██║  ██║██║\n"
        " ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝╚═╝\n"
        f"{Colors.RESET}\n"
        f"  {Colors.BOLD_CYAN}Noctalia V5 & Niri Desktop Environment Setup{Colors.RESET} {Colors.DARK_GRAY}|{Colors.RESET} {Colors.BOLD_WHITE}{env.version}{Colors.RESET}\n"
        f"  {Colors.DARK_GRAY}{mode_line}{Colors.RESET}\n\n"
    )
    write_cleared(logo)
    return logo.count("\n")

def render_menu_item(idx: int, label: str, focus: int, style: str = "normal", cols: Optional[int] = None) -> None:
    """Render a single interactive menu row with line-level erase."""
    if cols is None:
        cols = shutil.get_terminal_size((80, 24)).columns
    if idx == focus:
        prefix = f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}"
        if style == "warn":
            color = Colors.BOLD_RED
        elif style == "subtle":
            color = Colors.DARK_GRAY
        else:
            color = Colors.BOLD_WHITE
    else:
        prefix = "    "
        if style == "warn":
            color = Colors.RED
        elif style == "subtle":
            color = Colors.DARK_GRAY
        else:
            color = ""
    available = max(1, cols - display_width(prefix) - 1)
    clipped_label = truncate_display(label, available)
    sys.stdout.write(f"{prefix}{color}{clipped_label}{Colors.RESET}\033[K\n")

def render_check_row(is_focus: bool, check_str: str, label: str, cols: Optional[int] = None) -> None:
    """Render a single checkbox item row with line-level erase."""
    if cols is None:
        cols = shutil.get_terminal_size((80, 24)).columns
    prefix = f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}" if is_focus else "    "
    available = max(1, cols - display_width(prefix) - display_width(check_str) - 2)
    clipped_label = truncate_display(label, available)
    if is_focus:
        sys.stdout.write(
            f"  {Colors.BOLD_CYAN}❯ {Colors.RESET}{check_str} "
            f"{Colors.BOLD_WHITE}{clipped_label}{Colors.RESET}\033[K\n"
        )
    else:
        sys.stdout.write(f"    {check_str} {clipped_label}\033[K\n")

def press_any_key() -> None:
    """Prompt to press any key to continue."""
    if sys.stdin.isatty():
        fd = sys.stdin.fileno()
        sys.stdout.write(msg("press_any_key"))
        sys.stdout.flush()
        with raw_input_mode(fd):
            _drain_pending(fd)
            read_key()
            _drain_pending(fd, debounce=True)
        sys.stdout.write("\n")

def prompt_confirm(prompt_key: str, default: str = "y", destructive: bool = False) -> bool:
    """Bilingual prompt confirmation (True for Yes, False for No).

    Single-key raw read (y/n/Enter=default/Esc/Ctrl+C=No). Only the first char
    ever mattered under the old readline path (``line.lower().startswith('y')``),
    so raw single-key is equivalent — and it can't echo a stale buffered Enter.

    Destructive prompts (purge/snapshot delete/dirty-tree reset) always ask,
    even under NYXNIRI_AUTO_YES: express mode speeds things up, it must not
    consent to data loss on the user's behalf.
    """
    if os.environ.get("NYXNIRI_AUTO_YES", "0") == "1" and not destructive:
        return True

    sys.stdout.write(msg(prompt_key))
    sys.stdout.flush()
    if not sys.stdin.isatty():
        return default.lower().startswith("y")

    fd = sys.stdin.fileno()
    with raw_input_mode(fd):
        _drain_pending(fd)
        key = read_key()
        _drain_pending(fd, debounce=True)
    sys.stdout.write("\n")
    if key in ("y", "Y"):
        return True
    if key == "ENTER":
        return default.lower().startswith("y")
    return False  # n/N/Esc/Ctrl+C/any other → No (safe cancel)

# --- Component: Interactive Menu ---
@dataclass
class MenuItem:
    label: str
    action: Any = None
    style: str = "normal"
    group_header: Optional[str] = None


class Menu:
    def __init__(self, title_key: str, items: List[MenuItem], hint_key: str = "menu_hint", compact: bool = False):
        self.title_key = title_key
        self.items = items
        self.hint_key = hint_key
        self.compact = compact

    def run(self, initial_focus: int = 0) -> int:
        """Run interactive menu loop and return the selected item index."""
        if not sys.stdin.isatty():
            return len(self.items) - 1

        focus = initial_focus
        max_idx = len(self.items) - 1
        env = get_env()

        with interactive_screen(mouse=True):
            while True:
                cols, terminal_lines = shutil.get_terminal_size((80, 24))
                sys.stdout.write("\033[?25l\033[H")
                if self.compact:
                    show_header(msg(self.title_key).strip("\n"), env)
                else:
                    show_logo(env)
                    title = msg(self.title_key).strip("\n")
                    write_cleared(f"{title}\n\n")

                reserved = 6 if self.compact else RESERVED_ROWS
                visible_count = max(3, terminal_lines - reserved)
                start = max(0, min(focus - visible_count // 2, len(self.items) - visible_count))
                end = min(len(self.items), start + visible_count)
                if start > 0:
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                for curr_idx in range(start, end):
                    item = self.items[curr_idx]
                    if item.group_header:
                        if curr_idx > 0:
                            write_cleared("\n")
                        header = truncate_display(item.group_header, max(1, cols - 1))
                        write_cleared(f"{header}\n")
                    render_menu_item(curr_idx, item.label, focus, item.style, cols)
                if end < len(self.items):
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")

                hint = responsive_hint(self.hint_key).strip("\n")
                write_cleared(f"\n{hint}\n")
                sys.stdout.write("\033[J")
                sys.stdout.flush()

                key = read_key()
                if isinstance(key, MouseEvent):
                    if key.kind == "WHEEL_UP":
                        focus = max_idx if focus <= 0 else focus - 1
                    elif key.kind == "WHEEL_DOWN":
                        focus = 0 if focus >= max_idx else focus + 1
                    continue

                if key in ("UP", "k", "K", "LEFT", "h", "H"):
                    focus = max_idx if focus <= 0 else focus - 1
                elif key in ("DOWN", "j", "J", "RIGHT", "l", "L"):
                    focus = 0 if focus >= max_idx else focus + 1
                elif key in ("PAGEUP",):
                    focus = max(0, focus - visible_count)
                elif key in ("PAGEDOWN",):
                    focus = min(max_idx, focus + visible_count)
                elif key in ("HOME", "g"):
                    focus = 0
                elif key in ("END", "G"):
                    focus = max_idx
                elif key in ("ENTER", "SPACE"):
                    return focus
                elif key.isdigit() and 1 <= int(key) <= len(self.items):
                    return int(key) - 1
                elif key in ("0", "q", "Q"):
                    return max_idx
                elif key in ("ESC", "EXIT"):
                    return max_idx

# --- Component: Checkbox Checklist ---
@dataclass
class CheckboxEntry:
    key: str
    label: str
    checked: bool = False
    is_separator: bool = False


class CheckboxList:
    def __init__(self, title_key: str, entries: List[CheckboxEntry], hint_key: str = "selective_hint", compact: bool = False):
        self.title_key = title_key
        self.entries = entries
        self.hint_key = hint_key
        self.compact = compact

    def run(self, accept_defaults: bool = False) -> Optional[List[str]]:
        """Run checkbox selection loop. Returns list of selected keys, or None if cancelled."""
        if not any(not entry.is_separator for entry in self.entries):
            return []
        if not sys.stdin.isatty():
            if accept_defaults:
                return [e.key for e in self.entries if not e.is_separator and e.checked]
            return None

        selectable = [idx for idx, entry in enumerate(self.entries) if not entry.is_separator]
        focus_pos = 0
        env = get_env()

        with interactive_screen(mouse=True):
            while True:
                cols, terminal_lines = shutil.get_terminal_size((80, 24))
                sys.stdout.write("\033[?25l\033[H")
                if self.compact:
                    show_header(msg(self.title_key).strip("\n"), env)
                else:
                    show_logo(env)
                    title = msg(self.title_key).strip("\n")
                    write_cleared(f"{title}\n\n")

                focus = selectable[focus_pos]
                reserved = 6 if self.compact else RESERVED_ROWS
                visible_count = max(4, terminal_lines - reserved)
                start = max(
                    0,
                    min(focus - visible_count // 2, len(self.entries) - visible_count),
                )
                end = min(len(self.entries), start + visible_count)
                if start > 0:
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                for idx in range(start, end):
                    entry = self.entries[idx]
                    if entry.is_separator:
                        write_cleared(f"{entry.label}\n")
                        continue

                    check_str = (
                        f"{Colors.BOLD_GREEN}[✓]{Colors.RESET}"
                        if entry.checked
                        else f"{Colors.DARK_GRAY}[ ]{Colors.RESET}"
                    )
                    render_check_row(idx == focus, check_str, entry.label, cols)
                if end < len(self.entries):
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")

                hint = responsive_hint(self.hint_key).strip("\n")
                write_cleared(f"\n{hint}\n")
                sys.stdout.write("\033[J")
                sys.stdout.flush()

                key = read_key()
                if isinstance(key, MouseEvent):
                    if key.kind == "WHEEL_UP":
                        focus_pos = (focus_pos - 1) % len(selectable)
                    elif key.kind == "WHEEL_DOWN":
                        focus_pos = (focus_pos + 1) % len(selectable)
                    continue

                if key in ("UP", "k", "K", "LEFT", "h", "H"):
                    focus_pos = (focus_pos - 1) % len(selectable)
                elif key in ("DOWN", "j", "J", "RIGHT", "l", "L"):
                    focus_pos = (focus_pos + 1) % len(selectable)
                elif key in ("PAGEUP",):
                    focus_pos = max(0, focus_pos - visible_count)
                elif key in ("PAGEDOWN",):
                    focus_pos = min(len(selectable) - 1, focus_pos + visible_count)
                elif key in ("HOME", "g"):
                    focus_pos = 0
                elif key in ("END", "G"):
                    focus_pos = len(selectable) - 1
                elif key == "SPACE":
                    self.entries[focus].checked = not self.entries[focus].checked
                elif key in ("a", "A"):
                    for e in self.entries:
                        if not e.is_separator:
                            e.checked = True
                elif key in ("n", "N"):
                    for e in self.entries:
                        if not e.is_separator:
                            e.checked = False
                elif key in ("0", "q", "Q", "ESC", "EXIT"):
                    return None
                elif key.isdigit():
                    num = int(key) - 1
                    if 0 <= num < len(selectable):
                        focus_pos = num
                        entry_idx = selectable[focus_pos]
                        self.entries[entry_idx].checked = not self.entries[entry_idx].checked
                elif key == "ENTER":
                    return [e.key for e in self.entries if not e.is_separator and e.checked]

# --- Component: Category Accordion Checklist ---
@dataclass
class CategoryAppEntry:
    """One selectable app row inside a CategoryCheckboxList group."""
    key: str
    label: str
    checked: bool = False
    installed: bool = False
    source_tag: str = ""


@dataclass
class CategoryGroup:
    """A collapsible category branch for CategoryCheckboxList."""
    key: str
    label: str
    entries: List[CategoryAppEntry]


class CategoryCheckboxList:
    """Accordion checklist — PresetSwitcher's tree applied to multi-select.

    Category rows collapse/expand (`▸`/`▾`) with a picked/total counter;
    app rows underneath carry `[✓]/[ ]` checkboxes plus right-aligned
    status/source tags. Space toggles whatever the cursor sits on (branch or
    checkbox), Enter confirms the selection from anywhere, ←/→ fold/unfold.

    Actions:
      [↑/↓/j/k] Move   [←/→] Fold/Unfold   [Space] Toggle
      [a] All  [n] None  [Enter] Confirm  [0/q/Esc] Back
    """

    def __init__(self, title_key: str, groups: List[CategoryGroup], hint_key: str = "opt_apps_menu_hint", compact: bool = False):
        self.title_key = title_key
        self.groups = groups
        self.hint_key = hint_key
        self.compact = compact

    def _selected_keys(self) -> List[str]:
        return [e.key for g in self.groups for e in g.entries if e.checked]

    def run(self, accept_defaults: bool = False) -> Optional[List[str]]:
        """Run accordion selection loop. Returns selected keys, or None if cancelled."""
        if not any(g.entries for g in self.groups):
            return []
        if not sys.stdin.isatty():
            if accept_defaults:
                return self._selected_keys()
            return None

        expanded: Set[str] = {g.key for g in self.groups}
        focus = 0
        env = get_env()

        def build_flat_list() -> List[Dict[str, Any]]:
            items: List[Dict[str, Any]] = []
            for g in self.groups:
                is_exp = g.key in expanded
                items.append({"type": "cat", "group": g, "is_expanded": is_exp})
                if is_exp:
                    for e in g.entries:
                        items.append({"type": "app", "group": g, "entry": e})
            return items

        flat_items = build_flat_list()

        with interactive_screen(mouse=True):
            while True:
                cols, terminal_lines = shutil.get_terminal_size((80, 24))
                sys.stdout.write("\033[?25l\033[H")
                if self.compact:
                    cur_row = show_header(msg(self.title_key).strip("\n"), env) + 1
                else:
                    logo_rows = show_logo(env)
                    write_cleared(f"{msg(self.title_key).strip(chr(10))}\n\n")
                    cur_row = logo_rows + 3

                focus = max(0, min(focus, len(flat_items) - 1))
                reserved = 6 if self.compact else RESERVED_ROWS
                visible = max(4, terminal_lines - reserved)
                start = max(0, min(focus - visible // 2, len(flat_items) - visible))
                end = min(len(flat_items), start + visible)

                hit_map: List[Tuple[int, int]] = []
                if start > 0:
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    cur_row += 1

                for i in range(start, end):
                    item = flat_items[i]
                    if item["type"] == "cat":
                        g = item["group"]
                        arrow = "▾" if item["is_expanded"] else "▸"
                        total = len(g.entries)
                        picked = sum(1 for e in g.entries if e.checked)
                        count_tag = f"  {Colors.DARK_GRAY}{picked}/{total}{Colors.RESET}"
                        if i == focus:
                            prefix = f"  {Colors.BOLD_CYAN}❯ {arrow}{Colors.RESET} "
                            label_display = f"{Colors.BOLD_WHITE}{pad_display(g.label, 26)}{Colors.RESET}"
                        else:
                            prefix = f"    {Colors.DARK_GRAY}{arrow}{Colors.RESET} "
                            label_display = f"{Colors.WHITE}{pad_display(g.label, 26)}{Colors.RESET}"
                        line = f"{prefix}{label_display}{count_tag}"
                    else:
                        e = item["entry"]
                        check_str = (
                            f"{Colors.BOLD_GREEN}[✓]{Colors.RESET}"
                            if e.checked
                            else f"{Colors.DARK_GRAY}[ ]{Colors.RESET}"
                        )
                        status = msg("installed") if e.installed else msg("missing")
                        status_color = Colors.DARK_GRAY if e.installed else Colors.RESET
                        tags = f"{status_color}{status}{Colors.RESET}"
                        if e.source_tag:
                            tags += f"  {Colors.DARK_GRAY}{e.source_tag}{Colors.RESET}"
                        if i == focus:
                            prefix = f"      {Colors.BOLD_CYAN}❯{Colors.RESET} {check_str} "
                            label_display = f"{Colors.BOLD_WHITE}{pad_display(e.label, 28)}{Colors.RESET}"
                        else:
                            prefix = f"        {check_str} "
                            label_display = f"{Colors.WHITE}{pad_display(e.label, 28)}{Colors.RESET}"
                        line = f"{prefix}{label_display}  {tags}"

                    write_cleared(f"{line}\033[K\n")
                    hit_map.append((cur_row, i))
                    cur_row += 1

                if end < len(flat_items):
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    cur_row += 1

                hint = responsive_hint(self.hint_key).strip("\n")
                write_cleared(f"\n{hint}\033[K\n")
                sys.stdout.write("\033[J")
                sys.stdout.flush()

                key = read_key()

                if isinstance(key, MouseEvent):
                    if key.kind in ("WHEEL_UP", "WHEEL_DOWN"):
                        delta = -1 if key.kind == "WHEEL_UP" else 1
                        focus = (focus + delta) % len(flat_items)
                    elif key.kind == "PRESS":
                        hit_i = next((i for (r, i) in hit_map if r == key.row), None)
                        if hit_i is not None and 0 <= hit_i < len(flat_items):
                            focus = hit_i
                            hit_item = flat_items[hit_i]
                            if hit_item["type"] == "cat":
                                g_key = hit_item["group"].key
                                if g_key in expanded:
                                    expanded.remove(g_key)
                                else:
                                    expanded.add(g_key)
                                flat_items = build_flat_list()
                            else:
                                hit_item["entry"].checked = not hit_item["entry"].checked
                    continue

                curr_item = flat_items[focus] if flat_items else None

                if key in ("UP", "k", "K"):
                    focus = (focus - 1) % len(flat_items)
                elif key in ("DOWN", "j", "J"):
                    focus = (focus + 1) % len(flat_items)
                elif key in ("PAGEUP",):
                    focus = max(0, focus - visible)
                elif key in ("PAGEDOWN",):
                    focus = min(len(flat_items) - 1, focus + visible)
                elif key in ("HOME", "g"):
                    focus = 0
                elif key in ("END", "G"):
                    focus = len(flat_items) - 1
                elif key in ("RIGHT", "l", "L"):
                    if curr_item and curr_item["type"] == "cat":
                        g_key = curr_item["group"].key
                        if g_key not in expanded:
                            expanded.add(g_key)
                            flat_items = build_flat_list()
                        target = None
                        for i_f, it in enumerate(flat_items):
                            if it["type"] == "app" and it["group"].key == g_key:
                                target = i_f
                                break
                        if target is not None:
                            focus = target
                elif key in ("LEFT", "h", "H"):
                    if curr_item:
                        if curr_item["type"] == "app":
                            for i_f, it in enumerate(flat_items):
                                if it["type"] == "cat" and it["group"].key == curr_item["group"].key:
                                    focus = i_f
                                    break
                        elif curr_item["group"].key in expanded:
                            expanded.remove(curr_item["group"].key)
                            flat_items = build_flat_list()
                elif key == "SPACE" and curr_item:
                    if curr_item["type"] == "cat":
                        g_key = curr_item["group"].key
                        if g_key in expanded:
                            expanded.remove(g_key)
                        else:
                            expanded.add(g_key)
                        flat_items = build_flat_list()
                    else:
                        curr_item["entry"].checked = not curr_item["entry"].checked
                elif key in ("a", "A"):
                    for g in self.groups:
                        for e in g.entries:
                            e.checked = True
                elif key in ("n", "N"):
                    for g in self.groups:
                        for e in g.entries:
                            e.checked = False
                elif key == "ENTER":
                    return self._selected_keys()
                elif key in ("0", "q", "Q", "ESC", "EXIT"):
                    return None

# --- Component: Dual-Pane Preset Switcher (§9) ---
def show_header(title: str, env: Optional[Environment] = None) -> int:
    """Render a clean, modern subpage header with subtle brand tagline."""
    if env is None:
        env = get_env()
    header_text = (
        f"\n  {Colors.BOLD_PURPLE}NYX NIRI{Colors.RESET}  "
        f"{Colors.BOLD_WHITE}{env.version}{Colors.RESET}  "
        f"{Colors.DARK_GRAY}·{Colors.RESET}  "
        f"{Colors.BOLD_WHITE}{title}{Colors.RESET}\n\n"
    )
    write_cleared(header_text)
    return 3

# --- Component: Dual-Pane Preset Switcher (§9) ---
class PresetSwitcher:
    """Accordion Tree Preset Studio: flat list with expandable/collapsible app branches.

    - All apps displayed in a single unified list, collapsed by default (`▸`).
    - Pressing Enter / Space / → (or mouse click) on an App expands its presets (`▾`).
    - Presets indented underneath with single `❯` cursor navigation.
    - Active preset marked with pure minimal green dot `●`.
    - Zero vertical box-drawing lines, zero cross-character misalignments.

    Actions:
      [Enter] Expand App / Apply Preset
      [s]     Save current config to a user preset (in-place prompt)
      [e]     Open user preset in $EDITOR
      [d]     Delete user preset (in-place confirmation)
      [q/Esc] Exit
    """

    def __init__(
        self,
        apps: List[str],
        presets_for: Callable[[str], List[Any]],
        info_for: Optional[Callable[[str, str], Any]] = None,
        on_action: Optional[Callable[[str, str, str], Optional[str]]] = None,
        title_key: str = "preset_switcher_title",
        hint_key: str = "preset_switcher_hint",
    ):
        self.apps = apps
        self.presets_for = presets_for
        self.info_for = info_for
        self.on_action = on_action
        self.title_key = title_key
        self.hint_key = hint_key

    def _normalize_presets(self, raw_list: List[Any]) -> List[Tuple[str, str, bool]]:
        """Normalize (name, is_active) or (name, source, is_active) entries."""
        norm: List[Tuple[str, str, bool]] = []
        for item in raw_list:
            if len(item) == 2:
                name, is_active = item
                source = "official" if name == "default" else "user"
                norm.append((name, source, is_active))
            elif len(item) >= 3:
                name, source, is_active = item[0], item[1], item[2]
                norm.append((name, source, is_active))
        return norm

    def run(self) -> Optional[Tuple[str, str]]:
        if not self.apps or not sys.stdin.isatty():
            return None
        env = get_env()
        expanded: Set[str] = set()
        right_cache: Dict[str, List[Tuple[str, str, bool]]] = {}
        focus = 0
        toast_msg: Optional[str] = None

        def presets_for_app(app: str) -> List[Tuple[str, str, bool]]:
            if app not in right_cache:
                right_cache[app] = self._normalize_presets(self.presets_for(app))
            return right_cache[app]

        def build_flat_list() -> List[Dict[str, Any]]:
            items: List[Dict[str, Any]] = []
            for a in self.apps:
                p_list = presets_for_app(a)
                act_name = "default"
                for p_n, _, is_act in p_list:
                    if is_act:
                        act_name = p_n
                        break
                is_exp = a in expanded
                items.append({
                    "type": "app",
                    "app": a,
                    "active": act_name,
                    "count": len(p_list),
                    "is_expanded": is_exp,
                })
                if is_exp:
                    for p_n, src, is_act in p_list:
                        items.append({
                            "type": "preset",
                            "app": a,
                            "name": p_n,
                            "source": src,
                            "is_active": is_act,
                        })
            return items

        flat_items = build_flat_list()

        expand_details = False
        with interactive_screen(clear_first=False, mouse=True):
            while True:
                cols, terminal_lines = shutil.get_terminal_size((80, 24))
                sys.stdout.write("\033[?25l\033[H")
                logo_rows = show_logo(env)
                title = msg(self.title_key).strip("\n")
                write_cleared(f"  {Colors.BOLD_WHITE}{title}{Colors.RESET}\n\n")

                if not flat_items:
                    flat_items = build_flat_list()
                focus = max(0, min(focus, len(flat_items) - 1))

                visible = max(3, terminal_lines - (24 if expand_details else 18))
                start = max(0, min(focus - visible // 2, len(flat_items) - visible))
                end = min(len(flat_items), start + visible)

                hit_map: List[Tuple[int, int]] = []
                hit_actions: Dict[int, str] = {}
                cur_row = logo_rows + 3
                if start > 0:
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    cur_row += 1

                for i in range(start, end):
                    item = flat_items[i]
                    if item["type"] == "app":
                        arrow = "▾" if item["is_expanded"] else "▸"
                        count_tag = f" ({item['count']})" if item["count"] > 1 else ""
                        if i == focus:
                            prefix = f"  {Colors.BOLD_CYAN}❯ {arrow}{Colors.RESET} "
                            app_display = f"{Colors.BOLD_WHITE}{pad_display(item['app'], 28)}{Colors.RESET}"
                        else:
                            prefix = f"    {Colors.DARK_GRAY}{arrow}{Colors.RESET} "
                            app_display = f"{Colors.WHITE}{pad_display(item['app'], 28)}{Colors.RESET}"
                        status_str = f"{Colors.DARK_GRAY}{item['active']}{count_tag}{Colors.RESET}"
                        line = f"{prefix}{app_display}  {status_str}"
                    else:
                        active_badge = f"  {msg('preset_status_active')}" if item["is_active"] else ""
                        if i == focus:
                            prefix = f"      {Colors.BOLD_CYAN}❯{Colors.RESET}   "
                            name_display = f"{Colors.BOLD_WHITE}{pad_display(item['name'], 24)}{Colors.RESET}"
                        else:
                            prefix = "          "
                            name_display = f"{Colors.WHITE}{pad_display(item['name'], 24)}{Colors.RESET}"
                        line = f"{prefix}{name_display}{active_badge}"

                    write_cleared(f"{line}\033[K\n")
                    hit_map.append((cur_row, i))
                    cur_row += 1

                if end < len(flat_items):
                    write_cleared(f"    {Colors.DARK_GRAY}...{Colors.RESET}\n")
                    cur_row += 1

                # Divider with vertical breathing room
                divider_w = min(56, max(20, cols - 4))
                write_cleared(f"\n  {Colors.DARK_GRAY}{'─' * divider_w}{Colors.RESET}\n\n")
                cur_row += 3

                # Inspector section (Details)
                curr_item = flat_items[focus] if flat_items else None
                if curr_item and self.info_for:
                    cur_app = curr_item["app"]
                    cur_preset = curr_item["name"] if curr_item["type"] == "preset" else curr_item["active"]
                    info = self.info_for(cur_app, cur_preset)
                    if info:
                        write_cleared(f"  {Colors.DARK_GRAY}{msg('preset_info_source')}:{Colors.RESET} {info.path}\033[K\n\n")
                        cur_row += 2

                        # Included Files (independent line, collapsible)
                        f_cnt = len(info.files)
                        f_arrow = "▾" if expand_details else "▸"
                        write_cleared(f"  {Colors.WHITE}{f_arrow} {msg('preset_info_files')} ({f_cnt}){Colors.RESET}\033[K\n")
                        hit_actions[cur_row] = "toggle_details"
                        cur_row += 1

                        if expand_details:
                            if info.files:
                                for f_name in info.files:
                                    write_cleared(f"      {Colors.DARK_GRAY}·{Colors.RESET} {Colors.WHITE}{f_name}{Colors.RESET}\033[K\n")
                                    cur_row += 1
                            else:
                                write_cleared(f"      {Colors.DARK_GRAY}· {msg('preset_info_none')}{Colors.RESET}\033[K\n")
                                cur_row += 1
                            write_cleared("\n")
                            cur_row += 1

                        # Preserved Files (independent line, collapsible)
                        p_cnt = len(info.preserve)
                        p_arrow = "▾" if expand_details else "▸"
                        write_cleared(f"  {Colors.WHITE}{p_arrow} {msg('preset_info_preserve')} ({p_cnt}){Colors.RESET}\033[K\n")
                        hit_actions[cur_row] = "toggle_details"
                        cur_row += 1

                        if expand_details:
                            if info.preserve:
                                for p_name in info.preserve:
                                    write_cleared(f"      {Colors.DARK_GRAY}·{Colors.RESET} {Colors.YELLOW}{p_name}{Colors.RESET}\033[K\n")
                                    cur_row += 1
                            else:
                                write_cleared(f"      {Colors.DARK_GRAY}· {msg('preset_info_none')}{Colors.RESET}\033[K\n")
                                cur_row += 1
                    else:
                        write_cleared("\n\n\n")
                else:
                    write_cleared("\n\n\n")

                # Action Bar / Toast feedback
                if toast_msg:
                    write_cleared(f"\n  {toast_msg}\033[K\n")
                else:
                    hint = responsive_hint(self.hint_key).strip("\n")
                    write_cleared(f"\n{hint}\033[K\n")

                sys.stdout.write("\033[J")
                sys.stdout.flush()

                key = read_key()

                # Mouse handling
                if isinstance(key, MouseEvent):
                    if key.kind in ("WHEEL_UP", "WHEEL_DOWN"):
                        delta = -1 if key.kind == "WHEEL_UP" else 1
                        focus = (focus + delta) % len(flat_items)
                        toast_msg = None
                    elif key.kind == "PRESS":
                        if key.row in hit_actions:
                            if hit_actions[key.row] == "toggle_details":
                                expand_details = not expand_details
                                continue
                        hit_i = next((i for (r, i) in hit_map if r == key.row), None)
                        if hit_i is not None and 0 <= hit_i < len(flat_items):
                            focus = hit_i
                            hit_item = flat_items[hit_i]
                            if hit_item["type"] == "app":
                                a = hit_item["app"]
                                if not self.on_action:
                                    return (a, hit_item["active"])
                                if a in expanded:
                                    expanded.remove(a)
                                else:
                                    expanded.add(a)
                                flat_items = build_flat_list()
                            elif hit_item["type"] == "preset":
                                a = hit_item["app"]
                                p_n = hit_item["name"]
                                if self.on_action:
                                    toast_msg = self.on_action("apply", a, p_n)
                                    if a in right_cache:
                                        del right_cache[a]
                                    flat_items = build_flat_list()
                                else:
                                    return (a, p_n)
                    continue

                # Keyboard handling
                if key in ("TAB", "\t", "i", "I"):
                    expand_details = not expand_details
                    toast_msg = None
                elif key in ("UP", "k", "K"):
                    focus = (focus - 1) % len(flat_items)
                    toast_msg = None
                elif key in ("DOWN", "j", "J"):
                    focus = (focus + 1) % len(flat_items)
                    toast_msg = None
                elif key in ("PAGEUP",):
                    focus = max(0, focus - visible)
                    toast_msg = None
                elif key in ("PAGEDOWN",):
                    focus = min(len(flat_items) - 1, focus + visible)
                    toast_msg = None
                elif key in ("HOME", "g"):
                    focus = 0
                    toast_msg = None
                elif key in ("END", "G"):
                    focus = len(flat_items) - 1
                    toast_msg = None
                elif key in ("RIGHT", "l", "L"):
                    toast_msg = None
                    if curr_item and curr_item["type"] == "app":
                        a = curr_item["app"]
                        if a not in expanded:
                            expanded.add(a)
                            flat_items = build_flat_list()
                        target_focus = None
                        for i_f, it in enumerate(flat_items):
                            if it["type"] == "preset" and it["app"] == a:
                                if target_focus is None:
                                    target_focus = i_f
                                if it["is_active"]:
                                    target_focus = i_f
                                    break
                        if target_focus is not None:
                            focus = target_focus
                elif key in ("LEFT", "h", "H"):
                    toast_msg = None
                    if curr_item:
                        if curr_item["type"] == "preset":
                            for i_f, it in enumerate(flat_items):
                                if it["type"] == "app" and it["app"] == curr_item["app"]:
                                    focus = i_f
                                    break
                        elif curr_item["type"] == "app" and curr_item["app"] in expanded:
                            expanded.remove(curr_item["app"])
                            flat_items = build_flat_list()
                elif key in ("ENTER", "SPACE"):
                    if not curr_item:
                        continue
                    if curr_item["type"] == "app":
                        a = curr_item["app"]
                        if not self.on_action:
                            return (a, curr_item["active"])
                        if a in expanded:
                            expanded.remove(a)
                            flat_items = build_flat_list()
                        else:
                            expanded.add(a)
                            flat_items = build_flat_list()
                            target_focus = None
                            for i_f, it in enumerate(flat_items):
                                if it["type"] == "preset" and it["app"] == a:
                                    if target_focus is None:
                                        target_focus = i_f
                                    if it["is_active"]:
                                        target_focus = i_f
                                        break
                            if target_focus is not None:
                                focus = target_focus
                    elif curr_item["type"] == "preset":
                        a = curr_item["app"]
                        p_n = curr_item["name"]
                        if self.on_action:
                            toast_msg = self.on_action("apply", a, p_n)
                            if a in right_cache:
                                del right_cache[a]
                            flat_items = build_flat_list()
                        else:
                            return (a, p_n)
                elif key in ("s", "S"):
                    if not curr_item:
                        continue
                    cur_app = curr_item["app"]
                    prompt = f"  {Colors.BOLD_CYAN}{msg('preset_prompt_save_name')}{Colors.RESET}"
                    save_name = self._read_line_raw(prompt)
                    if save_name:
                        if self.on_action:
                            toast_msg = self.on_action("save", cur_app, save_name)
                            if cur_app in right_cache:
                                del right_cache[cur_app]
                            expanded.add(cur_app)
                            flat_items = build_flat_list()
                            for i_f, it in enumerate(flat_items):
                                if it["type"] == "preset" and it["app"] == cur_app and it["name"] == save_name:
                                    focus = i_f
                                    break
                elif key in ("e", "E"):
                    if not curr_item:
                        continue
                    if curr_item["type"] == "preset":
                        cur_app = curr_item["app"]
                        cur_preset = curr_item["name"]
                        if self.info_for:
                            info = self.info_for(cur_app, cur_preset)
                            if info and not info.is_editable:
                                toast_msg = msg("preset_edit_official_denied", cur_preset)
                                continue
                        if self.on_action:
                            toast_msg = self.on_action("edit", cur_app, cur_preset)
                            if cur_app in right_cache:
                                del right_cache[cur_app]
                            flat_items = build_flat_list()
                    else:
                        toast_msg = msg("preset_edit_official_denied", curr_item["active"])
                elif key in ("d", "D"):
                    if not curr_item:
                        continue
                    if curr_item["type"] == "preset":
                        cur_app = curr_item["app"]
                        cur_preset = curr_item["name"]
                        if self.info_for:
                            info = self.info_for(cur_app, cur_preset)
                            if info and not info.is_deletable:
                                toast_msg = msg("preset_delete_official_denied", cur_preset)
                                continue
                        prompt = f"  {Colors.BOLD_YELLOW}{msg('preset_prompt_delete_confirm', cur_preset)}{Colors.RESET}"
                        sys.stdout.write(f"\r\033[K{prompt}")
                        sys.stdout.flush()
                        confirm_key = read_key()
                        if confirm_key in ("y", "Y"):
                            if self.on_action:
                                toast_msg = self.on_action("delete", cur_app, cur_preset)
                                if cur_app in right_cache:
                                    del right_cache[cur_app]
                                flat_items = build_flat_list()
                                focus = min(focus, max(0, len(flat_items) - 1))
                        else:
                            toast_msg = msg("delete_cancelled")
                    else:
                        toast_msg = msg("preset_delete_official_denied", curr_item["active"])
                elif key in ("0", "q", "Q", "ESC", "EXIT"):
                    return None

    def _read_line_raw(self, prompt_str: str) -> Optional[str]:
        """Read a line of text in raw mode with backspace support."""
        sys.stdout.write(f"\r\033[K{prompt_str}")
        sys.stdout.flush()
        chars: List[str] = []
        while True:
            k = read_key()
            if k in ("ENTER", "\n", "\r"):
                return "".join(chars).strip()
            elif k in ("ESC", "EXIT"):
                return None
            elif k in ("BACKSPACE", "\x7f", "\x08"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif len(k) == 1 and k.isprintable():
                chars.append(k)
                sys.stdout.write(k)
                sys.stdout.flush()

# --- Component: Language Selection ---
def select_language() -> str:
    """Prompt user to select language mode with smooth arrow keys."""
    if not sys.stdin.isatty():
        from nyxniri.i18n import get_lang
        return get_lang()

    from nyxniri.i18n import set_lang
    env = get_env()
    focus = 1  # Default to Simplified Chinese

    with interactive_screen():
        while True:
            sys.stdout.write("\033[?25l\033[H")
            show_logo(env)
            write_cleared(f"  {Colors.BOLD_CYAN}── 请选择语言 / Select Language ──{Colors.RESET}\n\n")

            if focus == 0:
                sys.stdout.write(f"  {Colors.BOLD_CYAN}❯ {Colors.BOLD_WHITE}English{Colors.RESET}\033[K\n")
                sys.stdout.write(f"    {Colors.DARK_GRAY}简体中文 (Simplified Chinese){Colors.RESET}\033[K\n")
            else:
                sys.stdout.write(f"    {Colors.DARK_GRAY}English{Colors.RESET}\033[K\n")
                sys.stdout.write(f"  {Colors.BOLD_CYAN}❯ {Colors.BOLD_WHITE}简体中文 (Simplified Chinese){Colors.RESET}\033[K\n")

            hint = "[↑/↓] Move  [Enter] Select"
            write_cleared(f"\n  {Colors.DARK_GRAY}{hint}{Colors.RESET}\n")
            sys.stdout.write("\033[J")
            sys.stdout.flush()

            key = read_key()
            if key in ("UP", "k", "K", "LEFT", "h", "H", "1"):
                focus = 0
            elif key in ("DOWN", "j", "J", "RIGHT", "l", "L", "2"):
                focus = 1
            elif key in ("ENTER", "SPACE"):
                chosen = "en" if focus == 0 else "zh"
                set_lang(chosen)
                clear_screen()
                return chosen
            elif key in ("ESC", "EXIT"):
                sys.exit(130)
