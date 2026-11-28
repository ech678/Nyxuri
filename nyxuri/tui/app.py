"""One inline run: the shared base every activity area is built on."""

from dataclasses import replace
from pathlib import Path
from typing import List, Optional, Sequence

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.content import Content
from textual.theme import BUILTIN_THEMES
from textual.widgets import OptionList, Static

from nyxuri.system.i18n import msg

_BASE = BUILTIN_THEMES["ansi-dark"]
THEME = replace(
    _BASE,
    name="nyxuri",
    primary="ansi_magenta",
    accent="ansi_magenta",
    variables={**_BASE.variables, "nyx-dim": "ansi_bright_black"},
)

CANCEL = "cancel"

WORDMARK = "\n".join((
    "███╗   ██╗██╗   ██╗██╗  ██╗    ██╗   ██╗██████╗ ██╗",
    "████╗  ██║╚██╗ ██╔╝╚██╗██╔╝    ██║   ██║██╔══██╗██║",
    "██╔██╗ ██║ ╚████╔╝  ╚███╔╝     ██║   ██║██████╔╝██║",
    "██║╚██╗██║  ╚██╔╝   ██╔██╗     ██║   ██║██╔══██╗██║",
    "██║ ╚████║   ██║   ██╔╝ ██╗    ╚██████╔╝██║  ██║██║",
    "╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝     ╚═════╝ ╚═╝  ╚═╝╚═╝",
))


def _signature() -> str:
    from nyxuri.system.env import get_env

    env = get_env()
    home, conf = str(env.home), str(env.config_dir)
    where = "~" + conf[len(home):] if conf.startswith(home) else conf
    return f"nyxuri {env.version.removeprefix('v')} · {where}"


class Wordmark(Vertical):
    """Head of a menu screen; part of the activity area, so every redraw keeps it."""

    def compose(self) -> ComposeResult:
        yield Static(WORDMARK, id="wordmark-art", markup=False)
        yield Static(_signature(), id="wordmark-line", markup=False)


class PointerList(OptionList):
    """OptionList whose focused row carries the ❯ pointer."""

    def __init__(self, rows: Sequence[Content], **kwargs):
        self._rows = list(rows)
        super().__init__(*(self._prompt(i, i == 0) for i in range(len(self._rows))), compact=True, **kwargs)

    def _prompt(self, index: int, focused: bool) -> Content:
        return Content.assemble("❯ " if focused else "  ", self._rows[index])

    def set_rows(self, rows: Sequence[Content], focus: int = 0) -> None:
        self._rows = list(rows)
        self.set_options(self._prompt(i, False) for i in range(len(self._rows)))
        self.highlighted = min(focus, len(self._rows) - 1) if self._rows else None

    def watch_highlighted(self, old: Optional[int], new: Optional[int]) -> None:
        for index, focused in ((old, False), (new, True)):
            if index is not None and index < len(self._rows):
                self.replace_option_prompt_at_index(index, self._prompt(index, focused))
        super().watch_highlighted(new)


class InlineApp(App):
    CSS_PATH = Path(__file__).with_name("nyxuri.tcss")
    INLINE_PADDING = 0
    ENABLE_COMMAND_PALETTE = False
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (60, "-wide")]
    VERTICAL_BREAKPOINTS = [(0, "-short"), (20, "-tall")]
    BINDINGS = [
        Binding("ctrl+c", "cancel", show=False, priority=True, system=True),
        Binding("escape,q", "back", show=False),
        Binding("j", "cursor('down')", show=False),
        Binding("k", "cursor('up')", show=False),
    ]

    def __init__(self):
        super().__init__(ansi_color=True)
        self.register_theme(THEME)
        self.theme = THEME.name

    def run_inline(self):
        return self.run(inline=True, mouse=False)

    def action_cancel(self) -> None:
        self.exit(CANCEL)

    def action_back(self) -> None:
        self.exit(None)

    def action_cursor(self, direction: str) -> None:
        getattr(self.query_one(PointerList), f"action_cursor_{direction}")()

    def on_key(self, event) -> None:
        if event.character and event.character in "123456789":
            event.stop()
            self.pick(int(event.character) - 1)

    def pick(self, index: int) -> None:
        options = self.query_one(PointerList)
        if index < options.option_count:
            options.highlighted = index


class Confirm(InlineApp):
    """A boxed question; returns the chosen index, None (esc) or CANCEL."""

    def __init__(self, body: List[str], choices: List[str], default: int = 0):
        super().__init__()
        self.body = body
        self.choices = choices
        self.default = default

    def compose(self) -> ComposeResult:
        with Vertical(id="column"):
            with Vertical(id="box"):
                for line in self.body:
                    yield Static(line, classes="body", markup=False)
                yield PointerList([Content(f"{i + 1}. {c}") for i, c in enumerate(self.choices)])
            yield Static(msg("tui_confirm_hint"), classes="hint", markup=False)

    def on_mount(self) -> None:
        options = self.query_one(PointerList)
        options.highlighted = self.default
        options.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.exit(event.option_index)

    def pick(self, index: int) -> None:
        if index < len(self.choices):
            self.exit(index)
