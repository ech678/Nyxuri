"""Small GTK3 widgets for the translation popup."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GObject, Gtk, Pango


class FitScrolledWindow(Gtk.ScrolledWindow):
    """Vertical scroller whose height follows wrapped content up to a cap.

    GTK3 measures a propagated natural height without the allocated width, so
    wrapping labels would report one character per line. Measure the child for
    the real width instead; ``max_content_height`` remains the cap.
    """

    __gtype_name__ = "OrbitFitScrolledWindow"

    def __init__(self, max_height: int, min_height: int = 0):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_max_content_height(max_height)
        # Own floor instead of min-content-height, which GTK rejects above max.
        self.fit_min_height = min_height

    def do_get_request_mode(self) -> Gtk.SizeRequestMode:
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_get_preferred_height_for_width(self, width: int) -> tuple[int, int]:
        child = self.get_child()
        if child is None or not child.get_visible():
            return 0, 0
        _minimum, natural = child.get_preferred_height_for_width(max(1, width))
        maximum = self.get_max_content_height()
        height = max(0, min(max(natural, self.fit_min_height), maximum))
        return height, height


class LanguageChip(Gtk.Button):
    """Pill button showing the current language; ``LanguageMenu`` opens below it.

    Keeps the ``get_active_id``/``set_active_id``/``changed`` contract of the
    ComboBoxText it replaces.
    """

    __gtype_name__ = "OrbitLanguageChip"
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, options: tuple[tuple[str, str], ...], active_id: str, label_for: Callable[[str], str]):
        super().__init__()
        self.options = tuple(options)
        self._label_for = label_for
        self._active_id = ""
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_valign(Gtk.Align.CENTER)
        self.set_tooltip_text("选择语言")
        self.get_style_context().add_class("translate-language-chip")
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._label = Gtk.Label()
        self._label.set_xalign(0)
        self._label.set_ellipsize(Pango.EllipsizeMode.END)
        content.pack_start(self._label, True, True, 0)
        self._arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.MENU)
        content.pack_end(self._arrow, False, False, 0)
        self.add(content)
        self.set_active_id(active_id)

    def get_active_id(self) -> str:
        return self._active_id

    def set_active_id(self, language: str) -> None:
        if language not in {option for option, _label in self.options}:
            self.options += ((language, self._label_for(language)),)
        self._active_id = language
        self._label.set_text(dict(self.options)[language])
        self.emit("changed")

    def set_open(self, opened: bool) -> None:
        context = self.get_style_context()
        if opened:
            context.add_class("translate-language-chip-open")
        else:
            context.remove_class("translate-language-chip-open")
        self._arrow.set_from_icon_name("pan-up-symbolic" if opened else "pan-down-symbolic", Gtk.IconSize.MENU)


class LanguageMenu(Gtk.Revealer):
    """M3 menu that drops down below a ``LanguageChip``.

    It is an overlay child of the full-surface overlay, placed by margins in
    surface coordinates. It opens downward and flips above the chip only when
    the surface has no room below. GTK3 ComboBox menus instead center the
    active row over the button and cover the panel.
    """

    __gtype_name__ = "OrbitLanguageMenu"
    # M3 exposed dropdown: as wide as its anchor, with a small floor.
    MIN_WIDTH = 140
    MAX_LIST_HEIGHT = 264
    ROW_HEIGHT = 32
    GAP = 4
    # CSS margin around the visible sheet so its shadow is not clipped.
    SHADOW = 8

    def __init__(self, transition_ms: int):
        super().__init__()
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_transition_duration(transition_ms)
        self.set_no_show_all(True)
        self.chip: LanguageChip | None = None
        self._on_select: Callable[[str], None] | None = None
        self._above = False
        sheet = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sheet.get_style_context().add_class("translate-language-menu")
        self._scroll = FitScrolledWindow(self.MAX_LIST_HEIGHT)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.set_activate_on_single_click(True)
        self._list.connect("row-activated", self._on_row_activated)
        self._scroll.add(self._list)
        sheet.pack_start(self._scroll, True, True, 0)
        self.add(sheet)
        self.connect("notify::child-revealed", self._on_child_revealed)

    def is_open(self) -> bool:
        return self.chip is not None

    def open_for(
        self,
        chip: LanguageChip,
        surface_width: int,
        surface_height: int,
        on_select: Callable[[str], None],
        bounds: Gdk.Rectangle | None = None,
    ) -> None:
        """Open below ``chip``; ``bounds`` (the panel) keeps the menu horizontally inside."""
        if self.chip is not None:
            self.chip.set_open(False)
        self.chip = chip
        self._on_select = on_select
        chip.set_open(True)
        self._populate(chip)

        anchor = chip.get_allocation()
        width = max(anchor.width, self.MIN_WIDTH)
        list_height = min(len(chip.options) * self.ROW_HEIGHT + 12, self.MAX_LIST_HEIGHT + 12)
        below = anchor.y + anchor.height + self.GAP
        self._above = below + list_height > surface_height - 8 and anchor.y - self.GAP - list_height >= 8
        right = surface_width - 8 if bounds is None else bounds.x + bounds.width
        left = 8 if bounds is None else bounds.x
        x = max(0, max(left, min(anchor.x, right - width)) - self.SHADOW)
        self.set_size_request(width + 2 * self.SHADOW, -1)
        self.set_margin_start(x)
        if self._above:
            self.set_valign(Gtk.Align.END)
            self.set_margin_top(0)
            self.set_margin_bottom(max(0, surface_height - (anchor.y - self.GAP) - self.SHADOW))
            self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        else:
            self.set_valign(Gtk.Align.START)
            self.set_margin_bottom(0)
            self.set_margin_top(max(0, below - self.SHADOW))
            self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.show()
        self.get_child().show_all()
        self.set_reveal_child(True)
        active = next((row for row in self._list.get_children() if row.language == chip.get_active_id()), None)
        if active is not None:
            active.grab_focus()

    def close(self) -> None:
        chip, self.chip = self.chip, None
        self._on_select = None
        if chip is not None:
            chip.set_open(False)
        self.set_reveal_child(False)

    def contains(self, x: int, y: int, surface_height: int) -> bool:
        if not self.get_visible():
            return False
        width, height = self.get_allocated_width(), self.get_allocated_height()
        left = self.get_margin_start()
        top = surface_height - self.get_margin_bottom() - height if self._above else self.get_margin_top()
        return left <= x <= left + width and top <= y <= top + height

    def _populate(self, chip: LanguageChip) -> None:
        for row in self._list.get_children():
            self._list.remove(row)
        for language, label in chip.options:
            row = Gtk.ListBoxRow()
            row.language = language
            row.get_style_context().add_class("translate-language-option")
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            check = Gtk.Image.new_from_icon_name("object-select-symbolic", Gtk.IconSize.MENU)
            check.set_opacity(1.0 if language == chip.get_active_id() else 0.0)
            content.pack_start(check, False, False, 0)
            text = Gtk.Label(label=label)
            text.set_xalign(0)
            content.pack_start(text, True, True, 0)
            row.add(content)
            if language == chip.get_active_id():
                row.get_style_context().add_class("translate-language-option-active")
            self._list.add(row)

    def _on_row_activated(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        chip, on_select = self.chip, self._on_select
        self.close()
        if chip is not None:
            chip.grab_focus()
        if on_select is not None and row.language != (chip.get_active_id() if chip else None):
            on_select(row.language)

    def _on_child_revealed(self, *_args) -> None:
        if not self.get_reveal_child() and not self.get_child_revealed():
            self.hide()
