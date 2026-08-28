"""
NyxNiri Wallpaper Picker — Material 3 layer-shell UI.

Wayland overlay dialog assembled from M3 components: top app bar, search bar,
filter chips, image cards and a FAB. All styling is compiled from theme.py
tokens. Thumbnails stream in as CSS background-images on demand, so
off-screen cards hold no decoded pixbufs and scrolling away releases them.
"""

import os
import sys
import random
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

# ── Layout on the M3 grid (24dp dialog padding, 16dp gutters, 12dp rows).
# Card width keeps a 14px reserve so the grid never overflows when the
# vertical scrollbar claims its width. ──
DIALOG_W = 1080
DIALOG_H = 640
GRID_COLS = 3
GRID_GAP = 16
DIALOG_PAD = 24
GAP_V = 12
CARD_W = (DIALOG_W - 2 * DIALOG_PAD - (GRID_COLS - 1) * GRID_GAP - 14) // GRID_COLS
THUMB_H = CARD_W * 9 // 16
GRID_VIEWPORT_H = DIALOG_H - 2 * DIALOG_PAD - 64 - 56 - 32 - 3 * GAP_V


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


class WallpaperPickerWindow(Gtk.Window):
    """Material 3 wallpaper picker on the Wayland layer shell."""

    def __init__(self, lock_fd=None, pid_path=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("NyxNiriWallpaperPicker")

        self.lock_fd = lock_fd
        self.pid_path = pid_path
        self.tokens = theme.build_tokens()

        # View state must exist before scanner.scan() pre-warms cached thumbs
        # (its callback fires synchronously during scan).
        self.search_query = ""
        self.active_cat_idx = 0
        self.is_dismissing = False
        self._dismiss_timer = None
        self.thumb_widgets = {}
        self._applied_thumbs = set()
        self.flowbox = None
        self.chip_buttons = []
        self.chip_checks = []

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
                theme.build_css(self.tokens, {"card_w": CARD_W, "thumb_h": THUMB_H}).encode()
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
        for btn, check in zip(self.chip_buttons, self.chip_checks):
            if check is not None:
                check.set_visible(btn.get_active())
        self.search_entry.grab_focus()
        self.scanner.load_thumbnails_async()
        self.scroll.get_vadjustment().connect("value-changed", self._on_scroll)

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)

        # Overlay hosts the dialog plus the FAB, which floats above content
        # per the M3 scaffold pattern.
        self.overlay = Gtk.Overlay()
        dialog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=GAP_V)
        dialog.set_size_request(DIALOG_W, DIALOG_H)
        dialog.get_style_context().add_class("picker-dialog")
        self.dialog = dialog

        dialog.pack_start(self._build_appbar(), False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search wallpapers...")
        self.search_entry.set_size_request(-1, 56)
        self.search_entry.set_hexpand(True)
        self.search_entry.get_style_context().add_class("search")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("stop-search", self.on_stop_search)
        self.search_entry.connect("key-press-event", self.on_search_key_press)
        self.search_entry.connect("activate", self.on_search_activate)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.get_style_context().add_class("grid-scroll")
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(GRID_VIEWPORT_H)

        if self.scanner.items:
            dialog.pack_start(self.search_entry, False, False, 0)
            dialog.pack_start(self._build_chips(), False, False, 0)
            dialog.pack_start(self._build_grid(), True, True, 0)
        else:
            dialog.pack_start(self._build_empty_state(), True, True, 0)

        self.overlay.add(dialog)
        self.overlay.add_overlay(self._build_fab())
        outer.add(self.overlay)
        self.add(outer)

    def _build_appbar(self):
        appbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        appbar.set_size_request(-1, 64)

        title = Gtk.Label(label="Wallpapers")
        title.set_valign(Gtk.Align.CENTER)
        title.get_style_context().add_class("appbar-title")

        self.count_label = Gtk.Label(label="0")
        self.count_label.set_valign(Gtk.Align.CENTER)
        self.count_label.get_style_context().add_class("appbar-count")

        spacer = Gtk.Box()
        spacer.set_hexpand(True)

        close = Gtk.Button()
        close.set_valign(Gtk.Align.CENTER)
        close.set_focus_on_click(False)
        close.get_style_context().add_class("icon-btn")
        icon = _symbolic_icon("window-close-symbolic", 24)
        if icon is not None:
            close.add(icon)
        else:
            close.set_label("\u00d7")
        close.connect("clicked", lambda b: self.dismiss_window())

        appbar.pack_start(title, False, False, 0)
        appbar.pack_start(self.count_label, False, False, 0)
        appbar.pack_start(spacer, True, True, 0)
        appbar.pack_end(close, False, False, 0)
        return appbar

    def _build_chips(self):
        chips = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.chip_buttons = []
        self.chip_checks = []
        for idx, cat in enumerate(self.scanner.categories):
            btn = Gtk.ToggleButton()
            btn.set_focus_on_click(False)
            btn.get_style_context().add_class("chip")

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            check = _symbolic_icon("object-select-symbolic", 18)
            if check is not None:
                check.set_no_show_all(True)
                row.pack_start(check, False, False, 0)
            row.pack_start(Gtk.Label(label=cat), False, False, 0)
            btn.add(row)

            btn.set_active(idx == 0)
            btn.connect("toggled", self.on_chip_toggled, idx)
            chips.pack_start(btn, False, False, 0)
            self.chip_buttons.append(btn)
            self.chip_checks.append(check)
        return chips

    def _build_grid(self):
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_min_children_per_line(GRID_COLS)
        self.flowbox.set_max_children_per_line(GRID_COLS)
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
        if is_current:
            child.get_style_context().add_class("current")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner.get_style_context().add_class("card-inner")

        thumb = Gtk.Box()
        thumb.get_style_context().add_class("thumb")
        self.thumb_widgets[item.hash_id] = thumb

        thumb_host = Gtk.Overlay()
        thumb_host.add(thumb)
        if is_current:
            badge = Gtk.Label(label="\u2713")
            badge.set_xalign(0.5)
            badge.set_halign(Gtk.Align.END)
            badge.set_valign(Gtk.Align.START)
            badge.set_margin_end(8)
            badge.set_margin_top(8)
            badge.get_style_context().add_class("badge")
            thumb_host.add_overlay(badge)
        inner.pack_start(thumb_host, False, False, 0)

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

    def _build_fab(self):
        fab = Gtk.Button()
        fab.set_halign(Gtk.Align.END)
        fab.set_valign(Gtk.Align.END)
        fab.set_margin_end(16)
        fab.set_margin_bottom(16)
        fab.set_focus_on_click(False)
        fab.set_can_focus(False)
        fab.set_tooltip_text("Random wallpaper (Ctrl+R)")
        icon = _symbolic_icon("media-playlist-shuffle-symbolic", 24)
        if icon is not None:
            fab.add(icon)
        else:
            fab.set_label("Shuffle")
            fab.get_style_context().add_class("fab-extended")
        fab.get_style_context().add_class("fab")
        fab.connect("clicked", lambda b: self._apply_random())
        return fab

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

    # ── Filtering ────────────────────────────────────────────────────────────
    def _filter_func(self, child):
        item = child.item
        q = self.search_query.strip().lower()
        if q:
            return q in item.title.lower() or q in item.filename.lower()
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

    def _refresh_count(self):
        if self.flowbox is None:
            self.count_label.set_text("0")
            return
        self.count_label.set_text(str(len(self._visible_children())))

    # ── Signal handlers ──────────────────────────────────────────────────────
    def on_search_changed(self, entry):
        self.search_query = entry.get_text()
        self.flowbox.invalidate_filter()
        self._refresh_count()
        self.scanner.load_visible_thumbnails(
            [c.item for c in self._visible_children()]
        )

    def on_stop_search(self, entry):
        # SearchEntry emits stop-search on Esc-with-empty-text
        if not self.search_query:
            self.dismiss_window()

    def on_search_key_press(self, entry, event):
        if event.keyval == Gdk.KEY_Down:
            children = self._visible_children()
            if children:
                self.flowbox.grab_focus()
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
        for b, check in zip(self.chip_buttons, self.chip_checks):
            if check is not None:
                check.set_visible(b.get_active())
        self.flowbox.invalidate_filter()
        self._refresh_count()
        self.search_entry.grab_focus()
        cat = self.scanner.categories[idx]
        if cat != "All":
            self.scanner.load_category_thumbnails(cat)

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
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)

        # Ctrl+R → apply a random wallpaper from the visible set
        if ctrl and keyval in (Gdk.KEY_r, Gdk.KEY_R):
            self._apply_random()
            return True

        # Esc outside the search bar → clear search, or dismiss if already empty
        if keyval == Gdk.KEY_Escape:
            if self.search_query:
                self.search_entry.set_text("")
                self.search_entry.grab_focus()
            else:
                self.dismiss_window()
            return True

        return False

    # ── Apply ────────────────────────────────────────────────────────────────
    def select_and_apply(self, item):
        self.dismiss_window()
        threading.Thread(target=apply_wallpaper, args=(item,), daemon=False).start()

    def _apply_random(self):
        if self.flowbox is None:
            return
        items = [c.item for c in self._visible_children()]
        if items:
            self.select_and_apply(random.choice(items))

    # ── Thumbnail callback & lazy loading ─────────────────────────────────────
    def _on_scroll(self, adj):
        if self.is_dismissing:
            return
        if self.scanner._lazy_loaded:
            return
        val = adj.get_value()
        page = adj.get_page_size()
        if val >= (adj.get_upper() - page) * 0.6:
            self.scanner._lazy_loaded = True
            self.scanner.load_visible_thumbnails(self.scanner.items[24:])

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
        self.dialog.get_style_context().add_class("dismissing")
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
