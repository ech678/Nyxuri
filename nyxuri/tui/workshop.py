"""Plugin workshop: list + focused detail line, a projection of state.json."""

from typing import Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.content import Content
from textual.widgets import OptionList, Static

from nyxuri.system.i18n import msg
from nyxuri.tui.app import InlineApp, PointerList, Wordmark
from nyxuri.ui.tui import pad_display, truncate_display

ID_WIDTH = 24
FORM_WIDTH = 12


def snapshot() -> Tuple[List[str], Dict[str, dict], Dict[str, str]]:
    from nyxuri.deploy import catalog, engine
    from nyxuri.state import store

    recs = store.all_plugins()
    ids = sorted(set(catalog.plugin_ids()) | set(recs))
    try:
        audit = engine.audit_plugins()
    except Exception:
        audit = {}
    return ids, recs, audit


def row(uid: str, rec: dict, audit: str) -> Content:
    on = rec.get("state") == "enabled"
    parts: list = [("◉ " if on else "◯ ")]
    parts.append(pad_display(truncate_display(uid, ID_WIDTH - 1), ID_WIDTH))
    parts.append(pad_display(rec.get("form") or "—", FORM_WIDTH))
    if audit:
        parts.append((audit.lower(), "$nyx-dim" if audit == "Synced" else ""))
        if audit != "Synced":
            parts.append((" !", "$warning"))
    return Content.assemble(*parts)


def detail(uid: str) -> str:
    from nyxuri.deploy import catalog

    bits = [uid]
    if uid in catalog.plugin_ids():
        m = catalog.load_plugin(uid)
        pkgs = (*m.packages_repo, *m.packages_aur, *m.packages_flatpak)
        if m.label and m.label != uid:
            bits.append(m.label)
        if pkgs:
            bits.append(msg("tui_detail_packages", ", ".join(pkgs)))
        if m.dependencies:
            bits.append(msg("tui_detail_depends", ", ".join(m.dependencies)))
    return " · ".join(bits)


class Workshop(InlineApp):
    """Returns ("on" | "off", uid), None (esc) or CANCEL."""

    BINDINGS = [
        Binding("o", "switch('on')", show=False),
        Binding("f", "switch('off')", show=False),
    ]

    def __init__(self, focus: Optional[str] = None):
        super().__init__()
        self.ids, self.recs, self.audit = snapshot()
        self.start = self.ids.index(focus) if focus in self.ids else 0

    def compose(self) -> ComposeResult:
        rows = [row(u, self.recs.get(u) or {}, self.audit.get(u, "")) for u in self.ids]
        drifted = sum(1 for u in self.ids if self.audit.get(u) not in (None, "", "Synced"))
        with Vertical(id="column"):
            yield Wordmark()
            yield Static(msg("tui_workshop_summary", len(self.ids), drifted), classes="lead", markup=False)
            with Vertical(id="box"):
                yield PointerList(rows)
            yield Static("", id="detail", classes="detail", markup=False)
            yield Static(msg("tui_workshop_hint"), classes="hint", markup=False)

    def on_mount(self) -> None:
        options = self.query_one(PointerList)
        options.highlighted = self.start
        options.focus()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self.query_one("#detail", Static).update(detail(self.ids[event.option_index]))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        uid = self.ids[event.option_index]
        on = (self.recs.get(uid) or {}).get("state") == "enabled"
        self.exit(("off" if on else "on", uid))

    def action_switch(self, verb: str) -> None:
        index = self.query_one(PointerList).highlighted
        if index is not None and self.ids:
            self.exit((verb, self.ids[index]))
