"""
NyxNiri Wallpaper Picker — Material 3 layer-shell UI.

Wayland overlay dialog assembled from M3 components: scrim, top app bar,
search bar, filter chips and image cards. All styling is compiled from
theme.py tokens. Thumbnails stream in as CSS background-images on demand;
GTK3 caches each painted bitmap until exit, so memory tracks the thumbs
actually viewed (see scanner.py), not the library size.
"""

import math
import os
import sys
import threading
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

from . import theme
from .lock import release_instance_lock
from .scanner import WallpaperScanner
from .backend import apply_wallpaper

# ── M3 layout constants. The dialog sits centered with a 56dp margin to
# every screen edge (dialog placement rule); its nominal 1080×720 is clamped
# to the actual screen at startup — 720 lets the viewport show exactly two
# card rows. 8dp is the global rhythm: card gutters, dialog section spacing,
# icon-label gaps. Component heights feed both the viewport arithmetic here
# and the compiled CSS — single source. ──
DIALOG_W_MAX = 1080
DIALOG_H_MAX = 720
DIALOG_MIN_W = 360
SCREEN_MARGIN = 56
DIALOG_PAD = 24
GAP_V = 8
GRID_GAP = 8
APPBAR_H = 64
SEARCH_H = 56
# 48dp hit target (the 32dp chip face rides inside it); also the CSS
# min-height via the geometry dict — single source.
CHIP_ROW_H = 48
SCROLLBAR_RESERVE = 14
BORDER_W = 3
# Search input coalescing: keystrokes restart this timer, only the last
# one runs the full filter pass (two O(n) sweeps per apply).
SEARCH_DEBOUNCE_MS = 150


def _symbolic_icon(name, pixel_size):
    """Gtk.Image for a symbolic icon, or None when the icon theme lacks it."""
    try:
        if Gtk.IconTheme.get_default().has_icon(name):
            img = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.MENU)
            img.set_pixel_size(pixel_size)
            return img
    except Exception:
        pass
    return None


class FixedDialog(Gtk.Box):
    """Vertical dialog whose measured size is a constant.

    set_size_request only floors the requisition: dynamic child
    measurements — IME preedit inside the search entry, the entry's
    clear-button icon, the scrollbar appearing — would still push the
    dialog wider or narrower by tens of pixels mid-session. Overriding
    the four preferred-size vfuncs pins the dialog so no content
    re-measure can ever move it.
    """

    def __init__(self, width, height, spacing=0):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        self._fixed_w = width
        self._fixed_h = height

    def do_get_preferred_width(self):
        return self._fixed_w, self._fixed_w

    def do_get_preferred_width_for_height(self, height):
        return self._fixed_w, self._fixed_w

    def do_get_preferred_height(self):
        return self._fixed_h, self._fixed_h

    def do_get_preferred_height_for_width(self, width):
        return self._fixed_h, self._fixed_h


class SmoothScroll(Gtk.ScrolledWindow):
    """ScrolledWindow with critically-damped wheel / touchpad gliding.

    GTK3 jumps a fixed step per wheel notch and never animates pointer
    input. Scroll events here accumulate a target position that a
    frame-clock tick approaches exponentially — no overshoot,
    effects-spring semantics (see theme.py; scroll motion has no
    published M3 tokens, so TAU and the step are design decisions).
    Scrollbar grabs and programmatic resets abort the glide.
    """

    TAU_MS = 70.0
    WHEEL_STEP_PX = 120.0
    SNAP_PX = 0.5

    def __init__(self):
        super().__init__()
        self._target = None
        self._tick_id = None
        self._last_us = 0
        self._self_write = False
        self.get_vadjustment().connect("value-changed", self._on_value_changed)

    def do_scroll_event(self, event):
        adj = self.get_vadjustment()
        if adj is None:
            return False
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            step = event.delta_y * self.WHEEL_STEP_PX
        elif event.direction == Gdk.ScrollDirection.DOWN:
            step = self.WHEEL_STEP_PX
        elif event.direction == Gdk.ScrollDirection.UP:
            step = -self.WHEEL_STEP_PX
        else:
            return False
        if self._target is None:
            self._target = adj.get_value()
        self._target = min(max(self._target + step, adj.get_lower()),
                           adj.get_upper() - adj.get_page_size())
        if self._tick_id is None:
            self._last_us = self.get_frame_clock().get_frame_time()
            self._tick_id = self.add_tick_callback(self._tick)
        return True

    def _tick(self, widget, clock):
        adj = self.get_vadjustment()
        now = clock.get_frame_time()
        dt = max((now - self._last_us) / 1000.0, 1.0)
        self._last_us = now
        bounds = adj.get_upper() - adj.get_page_size()
        target = min(max(self._target, adj.get_lower()), bounds)
        value = adj.get_value()
        value += (target - value) * (1.0 - math.exp(-dt / self.TAU_MS))
        if abs(target - value) <= self.SNAP_PX:
            value = target
            self._stop()
        self._self_write = True
        adj.set_value(value)
        self._self_write = False
        return GLib.SOURCE_CONTINUE if self._tick_id is not None else GLib.SOURCE_REMOVE

    def _on_value_changed(self, adj):
        # A change we did not write — scrollbar drag, programmatic reset —
        # makes the glide target stale; drop it instead of fighting back.
        if not self._self_write:
            self._target = adj.get_value()
            self._stop()

    def _stop(self):
        if self._tick_id is not None:
            self.remove_tick_callback(self._tick_id)
            self._tick_id = None

    def snap_to(self, value):
        """Abort any glide and jump immediately (used on filter resets)."""
        self._stop()
        self._target = None
        self.get_vadjustment().set_value(value)


class WallpaperPickerWindow(Gtk.Window):
    """Material 3 wallpaper picker on the Wayland layer shell."""

    def __init__(self, lock_fd=None, pid_path=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("NyxNiriWallpaperPicker")

        self.lock_fd = lock_fd
        self.pid_path = pid_path
        self.tokens = theme.build_tokens()

        # Runtime dialog geometry: nominal size clamped to the screen minus
        # the 56dp placement margin (M3 dialog placement rule).
        screen = self.get_screen()
        self.dialog_w = max(DIALOG_MIN_W, min(DIALOG_W_MAX, screen.get_width() - 2 * SCREEN_MARGIN))
        self.dialog_h = min(DIALOG_H_MAX, screen.get_height() - 2 * SCREEN_MARGIN)
        self.grid_cols = 3 if self.dialog_w >= 720 else 2
        self.card_w = (self.dialog_w - 2 * DIALOG_PAD - (self.grid_cols - 1) * GRID_GAP
                       - SCROLLBAR_RESERVE) // self.grid_cols
        self.thumb_w = self.card_w - 2 * BORDER_W
        self.thumb_h = self.thumb_w * 9 // 16
        self.grid_viewport_h = (self.dialog_h - 2 * DIALOG_PAD - APPBAR_H
                                - SEARCH_H - CHIP_ROW_H - 3 * GAP_V)

        # View state must exist before scanner.scan() pre-warms cached thumbs
        # (its callback fires synchronously during scan).
        self.search_query = ""
        self.active_cat_idx = 0
        self.is_dismissing = False
        self._dismiss_timer = None
        self._search_debounce_id = None
        self.thumb_widgets = {}
        self._applied_thumbs = set()
        self._fading = []
        self._fade_tick_id = None
        self.flowbox = None
        self.chip_buttons = []
        self.chip_revealers = []

        self.scanner = WallpaperScanner(on_thumb_ready_cb=self.on_thumb_ready)
        self.scanner.scan()
        self.current_wp_path = self.scanner.get_current_wallpaper()

        # Layer-shell overlay: fullscreen, above everything, exclusive keyboard.
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)
        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT,
                     GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(
                theme.build_css(self.tokens, {
                    "card_w": self.card_w, "thumb_w": self.thumb_w,
                    "thumb_h": self.thumb_h, "search_h": SEARCH_H,
                    "chip_h": CHIP_ROW_H,
                }).encode()
            )
            Gtk.StyleContext.add_provider_for_screen(
                self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"CSS load error: {e}", file=sys.stderr)

        self._build_ui()

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-press-event", self.on_key_press)
        self.connect("delete-event", lambda w, e: (self.dismiss_window(), True)[1])
        self.connect("destroy", lambda w: Gtk.main_quit())

        self.show_all()
        self.search_entry.grab_focus()
        self.scanner.set_thumb_queue(self.scanner.items)
        self.scanner.load_next_thumb_batch()
        self.scroll.get_vadjustment().connect("value-changed", self._on_scroll)
        GLib.idle_add(self._reveal)

    def _reveal(self):
        """Fade in dialog + scrim (entry transition, effects spring)."""
        self.scrim.get_style_context().add_class("revealed")
        self.dialog.get_style_context().add_class("revealed")
        return GLib.SOURCE_REMOVE

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)

        # Overlay hosts the dialog. No floating actions: the grid itself is
        # the primary action surface (M3: no FAB when images are the action).
        self.overlay = Gtk.Overlay()
        dialog = FixedDialog(self.dialog_w, self.dialog_h, spacing=GAP_V)
        dialog.get_style_context().add_class("picker-dialog")
        self.dialog = dialog

        dialog.pack_start(self._build_appbar(), False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search wallpapers...")
        self.search_entry.set_size_request(-1, SEARCH_H)
        self.search_entry.set_hexpand(True)
        self.search_entry.get_style_context().add_class("search")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("stop-search", self.on_stop_search)
        self.search_entry.connect("key-press-event", self.on_search_key_press)
        self.search_entry.connect("activate", self.on_search_activate)

        self.scroll = SmoothScroll()
        self.scroll.get_style_context().add_class("grid-scroll")
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(self.grid_viewport_h)

        if self.scanner.items:
            dialog.pack_start(self.search_entry, False, False, 0)
            dialog.pack_start(self._build_chips(), False, False, 0)
            dialog.pack_start(self._build_grid(), True, True, 0)
        else:
            dialog.pack_start(self._build_empty_state(), True, True, 0)

        self.overlay.add(dialog)
        outer.add(self.overlay)

        # Scrim behind the dialog (modal dim layer); clicks bubble up to the
        # window handler, which dismisses when they land outside the dialog.
        self.root_overlay = Gtk.Overlay()
        self.scrim = Gtk.Box()
        self.scrim.get_style_context().add_class("scrim")
        self.root_overlay.add(self.scrim)
        self.root_overlay.add_overlay(outer)
        self.add(self.root_overlay)

    def _build_appbar(self):
        appbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        appbar.set_size_request(-1, APPBAR_H)

        title = Gtk.Label(label="Wallpapers")
        title.set_valign(Gtk.Align.CENTER)
        title.get_style_context().add_class("appbar-title")

        self.count_label = Gtk.Label(label="0")
        self.count_label.set_valign(Gtk.Align.CENTER)
        self.count_label.get_style_context().add_class("count-label")

        spacer = Gtk.Box()
        spacer.set_hexpand(True)

        close = Gtk.Button()
        close.set_valign(Gtk.Align.CENTER)
        close.set_focus_on_click(False)
        close.get_style_context().add_class("icon-btn")
        face = Gtk.Box()
        face.set_halign(Gtk.Align.CENTER)
        face.set_valign(Gtk.Align.CENTER)
        face.get_style_context().add_class("icon-btn-face")
        icon = _symbolic_icon("window-close-symbolic", 24)
        if icon is not None:
            icon.set_halign(Gtk.Align.CENTER)
            icon.set_valign(Gtk.Align.CENTER)
            face.pack_start(icon, True, True, 0)
        else:
            glyph = Gtk.Label(label="\u00d7")
            glyph.set_halign(Gtk.Align.CENTER)
            glyph.set_valign(Gtk.Align.CENTER)
            face.pack_start(glyph, True, True, 0)
        close.add(face)
        close.connect("clicked", lambda b: self.dismiss_window())

        appbar.pack_start(title, False, False, 0)
        appbar.pack_start(self.count_label, False, False, 0)
        appbar.pack_start(spacer, True, True, 0)
        appbar.pack_end(close, False, False, 0)
        return appbar

    def _build_chips(self):
        chips = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.chip_buttons = []
        self.chip_revealers = []
        for idx, cat in enumerate(self.scanner.categories):
            btn = Gtk.ToggleButton()
            btn.set_focus_on_click(False)
            btn.get_style_context().add_class("chip")

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_valign(Gtk.Align.CENTER)
            row.get_style_context().add_class("chip-face")
            rev = None
            check = _symbolic_icon("object-select-symbolic", 18)
            if check is not None:
                # Collapsed revealer leaves the leading padding of the chip
                # face; revealing slides the icon + 8dp gap in — GTK3's
                # closest approximation of the M3E width morph.
                rev = Gtk.Revealer()
                rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
                rev.set_transition_duration(theme.DUR_DEFAULT_MS)
                rev.add(check)
                rev.set_reveal_child(idx == 0)
                row.pack_start(rev, False, False, 0)
            row.pack_start(Gtk.Label(label=cat), False, False, 0)
            btn.add(row)

            btn.set_active(idx == 0)
            btn.connect("toggled", self.on_chip_toggled, idx)
            chips.pack_start(btn, False, False, 0)
            self.chip_buttons.append(btn)
            self.chip_revealers.append(rev)
        return chips

    def _build_grid(self):
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_min_children_per_line(self.grid_cols)
        self.flowbox.set_max_children_per_line(self.grid_cols)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_halign(Gtk.Align.CENTER)
        self.flowbox.set_column_spacing(GRID_GAP)
        self.flowbox.set_row_spacing(GRID_GAP)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_activate_on_single_click(True)
        self.flowbox.get_style_context().add_class("grid")
        self.flowbox.connect("child-activated", self.on_child_activated)
        self.flowbox.connect("key-press-event", self.on_grid_key_press)

        for item in self.scanner.items:
            self.flowbox.add(self._make_card(item))
        self.flowbox.set_filter_func(self._filter_func)
        self._refresh_count()

        self.scroll.add(self.flowbox)
        return self.scroll

    def _make_card(self, item):
        child = Gtk.FlowBoxChild()
        child.get_style_context().add_class("card")
        child.item = item
        is_current = item.path == self.current_wp_path

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner.get_style_context().add_class("card-inner")

        thumb = Gtk.Box()
        thumb.get_style_context().add_class("thumb")
        self.thumb_widgets[item.hash_id] = thumb

        # Enabled/selected state rides the card outline itself
        # (.card.current / .card:selected in theme.py); no corner badge.
        if is_current:
            child.get_style_context().add_class("current")
        inner.pack_start(thumb, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        info.get_style_context().add_class("card-info")
        if item.is_video:
            live = Gtk.Label(label="Live")
            live.get_style_context().add_class("live")
            info.pack_start(live, False, False, 0)
        title = Gtk.Label(label=item.title)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_max_width_chars(30)
        title.get_style_context().add_class("card-title")
        info.pack_start(title, False, False, 0)
        inner.pack_start(info, False, False, 0)

        child.add(inner)
        return child

    def _build_empty_state(self):
        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        empty.set_valign(Gtk.Align.CENTER)
        icon = _symbolic_icon("image-x-generic-symbolic", 48)
        if icon is not None:
            icon.set_halign(Gtk.Align.CENTER)
            empty.pack_start(icon, False, False, 0)
        title = Gtk.Label(label="No wallpapers found")
        title.set_halign(Gtk.Align.CENTER)
        title.get_style_context().add_class("empty-title")
        hint = Gtk.Label(label="Add images or videos to your wallpaper folders")
        hint.set_halign(Gtk.Align.CENTER)
        hint.get_style_context().add_class("empty-hint")
        empty.pack_start(title, False, False, 0)
        empty.pack_start(hint, False, False, 0)
        return empty

    # ── Thumbnail rendering ──────────────────────────────────────────────────
    def _apply_thumb(self, thumb_box, thumb_path):
        provider = Gtk.CssProvider()
        uri = "file://" + thumb_path.replace('"', "")
        css = (
            f'.thumb {{ background-image: url("{uri}");'
            f' background-size: cover; background-position: center; }}'
        )
        try:
            provider.load_from_data(css.encode())
            thumb_box.get_style_context().add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
            )
        except Exception as e:
            print(f"thumb apply error: {e}", file=sys.stderr)
            return
        self._fade_in(thumb_box)

    def _fade_in(self, widget, total_ms=None):
        """M3 new-content entrance: fade the widget in. GTK3 cannot
        transition background-image, so widget opacity carries the reveal.
        All running fades share one ticker instead of one timer apiece."""
        if not widget.get_visible():
            # Off-screen / filtered-out cards appear instantly when shown
            widget.set_opacity(1.0)
            return
        if total_ms is None:
            total_ms = theme.DUR_FAST_MS
        widget.set_opacity(0.0)
        self._fading.append([widget, 0.0, float(total_ms)])
        if self._fade_tick_id is None:
            self._fade_tick_id = GLib.timeout_add(16, self._fade_tick)

    def _fade_tick(self):
        still = []
        for widget, elapsed, total in self._fading:
            if not widget.get_mapped():
                # Hidden mid-fade (filter/scroll): snap full so it never
                # resurfaces stuck at partial opacity
                widget.set_opacity(1.0)
                continue
            elapsed += 16
            if elapsed >= total:
                widget.set_opacity(1.0)
            else:
                widget.set_opacity(min(1.0, widget.get_opacity() + 16.0 / total))
                still.append([widget, elapsed, total])
        self._fading = still
        if not self._fading:
            self._fade_tick_id = None
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    # ── Filtering ────────────────────────────────────────────────────────────
    def _filter_func(self, child):
        item = child.item
        q = self.search_query.strip().lower()
        if q:
            return q in item.search_key
        if self.active_cat_idx == 0:
            return True
        cat = self.scanner.categories[self.active_cat_idx]
        if cat == "Static":
            return not item.is_video
        if cat == "Live":
            return item.is_video
        return item.category == cat

    def _visible_children(self):
        return [c for c in self.flowbox.get_children() if self._filter_func(c)]

    def _refresh_count(self, visible=None):
        if self.flowbox is None:
            self.count_label.set_text("0")
            return
        if visible is None:
            visible = self._visible_children()
        self.count_label.set_text(str(len(visible)))

    # ── Signal handlers ──────────────────────────────────────────────────────
    def on_search_changed(self, entry):
        self.search_query = entry.get_text()
        if self._search_debounce_id is not None:
            GLib.source_remove(self._search_debounce_id)
        self._search_debounce_id = GLib.timeout_add(SEARCH_DEBOUNCE_MS, self._apply_search_debounced)

    def _apply_search_debounced(self):
        self._search_debounce_id = None
        if self.is_dismissing:
            return GLib.SOURCE_REMOVE
        self._update_filter()
        return GLib.SOURCE_REMOVE

    def on_stop_search(self, entry):
        # SearchEntry emits stop-search on Esc-with-empty-text
        if not self.search_query:
            self.dismiss_window()

    def on_search_key_press(self, entry, event):
        if event.keyval == Gdk.KEY_Down:
            children = self._visible_children()
            if children:
                # Focus the card itself, not the FlowBox container: the
                # child grab is what sets the FlowBox's internal focus
                # anchor, so subsequent arrow keys move from a known place
                # instead of resetting to the first item.
                children[0].grab_focus()
                self.flowbox.select_child(children[0])
            return True
        return False

    def on_search_activate(self, entry):
        children = self._visible_children()
        if children:
            self.select_and_apply(children[0].item)

    def on_chip_toggled(self, btn, idx):
        if not btn.get_active():
            return
        for i, b in enumerate(self.chip_buttons):
            if i != idx and b.get_active():
                b.handler_block_by_func(self.on_chip_toggled)
                b.set_active(False)
                b.handler_unblock_by_func(self.on_chip_toggled)
        self.active_cat_idx = idx
        for b, rev in zip(self.chip_buttons, self.chip_revealers):
            if rev is not None:
                rev.set_reveal_child(b.get_active())
        self._update_filter()
        self.search_entry.grab_focus()

    def _update_filter(self):
        """Apply the active filter and restart incremental thumb loading."""
        visible = self._visible_children()
        self.flowbox.invalidate_filter()
        self._refresh_count(visible)
        self.scroll.snap_to(0)
        self.scanner.set_thumb_queue([c.item for c in visible])
        self.scanner.load_next_thumb_batch()

    def on_child_activated(self, box, child):
        self.select_and_apply(child.item)

    def on_grid_key_press(self, box, event):
        # Up at the top row → hand focus back to the search bar
        if event.keyval == Gdk.KEY_Up:
            sel = self.flowbox.get_selected_children()
            visible = self._visible_children()
            if visible and (not sel or sel[0] == visible[0]):
                self.search_entry.grab_focus()
                return True
        return False

    def on_button_press(self, widget, event):
        if self.is_dismissing:
            return True
        # Right / middle click → clear search, or dismiss if already empty
        if event.button in (2, 3):
            if self.search_query:
                self.search_entry.set_text("")
            else:
                self.dismiss_window()
            return True
        # Left click outside the dialog → dismiss
        if event.button == 1 and self._click_outside_dialog(event.x, event.y):
            self.dismiss_window()
            return True
        return False

    def _click_outside_dialog(self, x, y):
        wa = self.get_allocation()
        da = self.dialog.get_allocation()
        if da.width == 0 or da.height == 0 or wa.width == 0:
            return False
        # dialog is centered in the (fullscreen) window
        dx = (wa.width - da.width) // 2
        dy = (wa.height - da.height) // 2
        return not (dx <= x <= dx + da.width and dy <= y <= dy + da.height)

    def on_key_press(self, widget, event):
        if self.is_dismissing:
            return True
        keyval = event.keyval
        mods = event.state & Gtk.accelerator_get_default_mod_mask()

        # Esc outside the search bar → clear search, or dismiss if already empty
        if keyval == Gdk.KEY_Escape:
            if self.search_query:
                self.search_entry.set_text("")
                self.search_entry.grab_focus()
            else:
                self.dismiss_window()
            return True

        # Ctrl+F → hand focus back to the search bar from anywhere
        if keyval == Gdk.KEY_f and mods & Gdk.ModifierType.CONTROL_MASK:
            self.search_entry.grab_focus()
            return True

        # Alt+1..9 → clear the search and jump straight to the n-th category
        if mods & Gdk.ModifierType.MOD1_MASK and Gdk.KEY_1 <= keyval <= Gdk.KEY_9:
            idx = keyval - Gdk.KEY_1
            if idx < len(self.chip_buttons):
                if self.search_query:
                    self.search_entry.set_text("")
                self.chip_buttons[idx].set_active(True)
            return True

        # ←/→/Home/End while a chip holds focus → move within the chip row
        # only (GTK's default Home/End would jump the whole focus chain)
        if keyval in (Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_Home, Gdk.KEY_End):
            focus = self.get_focus()
            last = len(self.chip_buttons) - 1
            for i, btn in enumerate(self.chip_buttons):
                if focus is btn:
                    if keyval == Gdk.KEY_Left and i > 0:
                        self.chip_buttons[i - 1].grab_focus()
                    elif keyval == Gdk.KEY_Right and i < last:
                        self.chip_buttons[i + 1].grab_focus()
                    elif keyval == Gdk.KEY_Home:
                        self.chip_buttons[0].grab_focus()
                    elif keyval == Gdk.KEY_End:
                        self.chip_buttons[last].grab_focus()
                    else:
                        return True
                    return True

        return False

    # ── Apply ────────────────────────────────────────────────────────────────
    def select_and_apply(self, item):
        self.dismiss_window()
        threading.Thread(target=apply_wallpaper, args=(item,), daemon=False).start()

    # ── Thumbnail callback & lazy loading ─────────────────────────────────────
    def _on_scroll(self, adj):
        if self.is_dismissing:
            return
        if not self.scanner.has_pending_thumbs():
            return
        # Near the bottom → load the next batch from the display-order queue
        if adj.get_value() + adj.get_page_size() >= adj.get_upper() - 400:
            self.scanner.load_next_thumb_batch()

    def on_thumb_ready(self, item):
        if item.hash_id in self._applied_thumbs:
            return
        thumb = self.thumb_widgets.get(item.hash_id)
        if thumb and os.path.isfile(item.thumb_path):
            self._applied_thumbs.add(item.hash_id)
            self._apply_thumb(thumb, item.thumb_path)

    # ── Dismiss (fade out + release lock + quit) ──────────────────────────────
    def dismiss_window(self):
        if self.is_dismissing:
            return
        self.is_dismissing = True
        if self._search_debounce_id is not None:
            GLib.source_remove(self._search_debounce_id)
            self._search_debounce_id = None
        self.dialog.get_style_context().remove_class("revealed")
        self.scrim.get_style_context().remove_class("revealed")
        self._dismiss_timer = GLib.timeout_add(theme.DUR_EXIT_MS, self._finish_dismiss)

    def _finish_dismiss(self):
        if self._dismiss_timer is not None:
            GLib.source_remove(self._dismiss_timer)
            self._dismiss_timer = None
        release_instance_lock(self.lock_fd, self.pid_path)
        self.lock_fd = None
        self.hide()
        Gtk.main_quit()
        return GLib.SOURCE_REMOVE
