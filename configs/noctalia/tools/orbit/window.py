"""
Orbit Launcher GtkLayerShell Window & Interaction Controller
100% Stateless & On-Demand event-driven Wayland Layer Shell overlay window.
"""

import sys
import os
import math
import subprocess
import urllib.parse
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

from .physics import Spring
from .palette import load_material_palette, hex_to_rgb
from .lock import release_instance_lock
from .config import (
    BASE_ORBIT_RADIUS, DEADZONE_RADIUS, HYSTERESIS_DEG, FLOAT_SPRING,
    DEFAULT_MENU_TREE, load_menu_tree, load_search_config
)
from .renderer import (
    draw_scrim, draw_star_ring, draw_tethers, draw_submenu_return_core,
    draw_idle_center_dot, draw_search_hub, draw_capsules
)


def is_modifier_or_nav_key(keyval: int) -> bool:
    """Check if keyval is a modifier or special system key that should never trigger search."""
    if 0xffe1 <= keyval <= 0xffee:
        return True
    if 0xfe00 <= keyval <= 0xfeff:
        return True
    if Gdk.KEY_F1 <= keyval <= Gdk.KEY_F35:
        return True
    if keyval in (
        Gdk.KEY_Insert, Gdk.KEY_Delete, Gdk.KEY_Home, Gdk.KEY_End,
        Gdk.KEY_Page_Up, Gdk.KEY_Page_Down, Gdk.KEY_Pause, Gdk.KEY_Print,
        Gdk.KEY_Menu, Gdk.KEY_Num_Lock, Gdk.KEY_Scroll_Lock, Gdk.KEY_VoidSymbol
    ):
        return True
    return False


class OrbitLauncher(Gtk.Window):
    """Orbit Launcher Main GtkLayerShell Window."""

    def __init__(self, lock_fd: int = None, pid_path: str = None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.lock_fd = lock_fd
        self.pid_path = pid_path
        self.palette = load_material_palette()
        self.root_items = load_menu_tree()
        self.menu_stack = []
        self.apps = self.root_items
        self.num_items = len(self.apps)

        # Search Config & Engine Suite
        self.search_engines, self.search_meta = load_search_config()
        self.default_engine_id = self.search_meta.get("default_engine", "bing")
        self.placeholder_text = self.search_meta.get("placeholder", "Search or ask...")
        self.current_engine_idx = 0
        for idx, eng in enumerate(self.search_engines):
            if eng.get("id") == self.default_engine_id:
                self.current_engine_idx = idx
                break

        self.search_query = ""
        self.search_active = False
        self.cursor_time = 0.0

        # Pre-cache Pango Back Icon
        self.layout_back = self.create_pango_layout("󰌍")
        self.layout_back.set_font_description(Pango.FontDescription("JetBrainsMono Nerd Font Bold 16"))
        self.back_ink_rect, _ = self.layout_back.get_pixel_extents()

        self.hovered_index = None
        self.keyboard_selected = None
        self.keyboard_nav_pos = None
        self.press_pos = None
        self.center_x = None
        self.center_y = None
        self.origin_locked = False
        self.is_dismissing = False
        self.last_mouse_pos = None

        # Physics Springs Matrix
        self.entry_spring = Spring(0.0, omega=14.0, zeta=0.70)
        self.trans_spring = Spring(1.0, omega=15.0, zeta=0.80)
        self.core_spring_x = Spring(0.0, omega=18.0, zeta=1.00)
        self.core_spring_y = Spring(0.0, omega=18.0, zeta=1.00)
        self.search_spring = Spring(0.0, omega=18.0, zeta=0.75)
        self.engine_switch_spring = Spring(1.0, omega=22.0, zeta=0.78)
        self.node_springs = []

        # Native Wayland CJK IME Context (Fcitx5 / IBus)
        self.im_context = Gtk.IMMulticontext()
        self.im_context.set_use_preedit(True)
        self.im_context.connect("commit", self.on_im_commit)
        self.im_context.connect("preedit-changed", self.on_im_preedit_changed)

        self.setup_current_tier()

        # GdkFrameClock VBLANK synchronization callback
        self.tick_callback_id = None
        self.last_frame_time = 0

        # Layer Shell Setup
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)

        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
            | Gdk.EventMask.KEY_RELEASE_MASK
            | Gdk.EventMask.STRUCTURE_MASK
        )

        self.connect("realize", self.on_realize)
        self.connect("draw", self.on_draw)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("enter-notify-event", self.on_enter_notify)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("scroll-event", self.on_scroll)
        self.connect("key-press-event", self.on_key_press)
        self.connect("key-release-event", self.on_key_release)
        self.connect("delete-event", lambda w, e: (self.dismiss_menu(), True)[1])
        self.connect("destroy", lambda w: Gtk.main_quit())

        self.open_menu()

    def on_realize(self, widget):
        gdk_window = self.get_window()
        if gdk_window:
            self.im_context.set_client_window(gdk_window)

    def update_im_cursor_location(self, cursor_x: float, cursor_y: float):
        rect = Gdk.Rectangle()
        rect.x = int(cursor_x)
        rect.y = int(cursor_y)
        rect.width = 2
        rect.height = 26
        self.im_context.set_cursor_location(rect)

    def setup_current_tier(self):
        if not self.apps or not isinstance(self.apps, list):
            self.apps = DEFAULT_MENU_TREE
        self.num_items = len(self.apps)
        if self.num_items == 0:
            return
        self.node_springs = [Spring(0.0, omega=12.0, zeta=0.65) for _ in range(self.num_items)]
        self.init_geometry()
        self.init_cached_layouts()

    def init_geometry(self):
        if self.num_items == 0:
            return
        start_angle = -90.0
        step = 360.0 / self.num_items
        for i, app in enumerate(self.apps):
            angle = (start_angle + i * step) % 360.0
            if angle > 180.0:
                angle -= 360.0
            app["center_angle"] = angle
            color_key = str(app.get("color_key", "secondary"))
            if color_key.startswith("#"):
                app["color"] = hex_to_rgb(color_key, default=(0.38, 0.85, 0.65))
            else:
                app["color"] = self.palette.get(color_key, (0.38, 0.85, 0.65))

    def init_cached_layouts(self):
        font_title = Pango.FontDescription("Noto Sans CJK SC, Inter, sans-serif SemiBold 11.5")
        font_desc = Pango.FontDescription("Noto Sans CJK SC, Inter, sans-serif Regular 8.5")
        font_icon = Pango.FontDescription("JetBrainsMono Nerd Font 14")
        font_badge = Pango.FontDescription("JetBrains Mono Bold 9")

        for app in self.apps:
            app_name = str(app.get("name") or app.get("id") or "App")
            lt = self.create_pango_layout(app_name)
            lt.set_font_description(font_title)
            tw, th = lt.get_pixel_size()
            app["layout_title"] = lt
            app["title_w"], app["title_h"] = tw, th

            desc_text = str(app.get("desc") or "")
            if not desc_text:
                if "children" in app and isinstance(app["children"], list):
                    desc_text = f"Folder · {len(app['children'])} Items"
                elif "url" in app:
                    desc_text = "Web Link"
            ld = self.create_pango_layout(desc_text)
            ld.set_font_description(font_desc)
            dw, dh = ld.get_pixel_size()
            app["layout_desc"] = ld
            app["desc_w"], app["desc_h"] = dw, dh

            li = self.create_pango_layout(str(app.get("icon", "󰣆")))
            li.set_font_description(font_icon)
            ink_rect, log_rect = li.get_pixel_extents()
            app["layout_icon"] = li
            app["icon_ink_rect"] = ink_rect
            app["icon_w"], app["icon_h"] = log_rect.width, log_rect.height

            lk = self.create_pango_layout(str(app.get("shortcut", "")))
            lk.set_font_description(font_badge)
            kw, kh = lk.get_pixel_size()
            app["layout_badge"] = lk
            app["badge_w"], app["badge_h"] = kw, kh

            needed_w = 14.0 + 32.0 + 8.0 + max(tw, dw) + 8.0 + (kw + 8.0) + 14.0
            app["idle_w"] = max(156.0, needed_w)
            app["active_w"] = app["idle_w"] + 24.0

        # Pre-cache search engine layouts
        font_engine_icon = Pango.FontDescription("JetBrainsMono Nerd Font Bold 16")
        font_placeholder = Pango.FontDescription("Noto Sans CJK SC, Inter Bold 13")
        for eng in self.search_engines:
            icon_text = str(eng.get("icon", "󰍉"))
            le = self.create_pango_layout(icon_text)
            le.set_font_description(font_engine_icon)
            ink_rect, log_rect = le.get_pixel_extents()
            eng["layout"] = le
            eng["icon_ink"] = ink_rect
            eng["layout_w"] = log_rect.width
            eng["layout_h"] = log_rect.height

        self.layout_placeholder = self.create_pango_layout(self.placeholder_text)
        self.layout_placeholder.set_font_description(font_placeholder)
        self.placeholder_w, self.placeholder_h = self.layout_placeholder.get_pixel_size()

    def open_menu(self):
        self.palette = load_material_palette()
        self.hovered_index = None
        self.keyboard_selected = None
        self.keyboard_nav_pos = None
        self.press_pos = None
        self.is_dismissing = False
        self.last_mouse_pos = None

        self.search_query = ""
        self.search_active = False
        self.cursor_time = 0.0

        self.entry_spring.current = 0.0
        self.entry_spring.target = 1.0
        self.entry_spring.velocity = 0.0

        self.trans_spring.current = 1.0
        self.trans_spring.target = 1.0
        self.trans_spring.velocity = 0.0

        self.core_spring_x.current = 0.0
        self.core_spring_x.target = 0.0
        self.core_spring_x.velocity = 0.0
        self.core_spring_y.current = 0.0
        self.core_spring_y.target = 0.0
        self.core_spring_y.velocity = 0.0

        self.search_spring.current = 0.0
        self.search_spring.target = 0.0
        self.search_spring.velocity = 0.0

        self.engine_switch_spring.current = 1.0
        self.engine_switch_spring.target = 1.0
        self.engine_switch_spring.velocity = 0.0

        self.show_all()
        self.present()
        self.im_context.focus_in()
        self._request_frame()

    def dismiss_menu(self):
        if self.is_dismissing:
            return
        self.is_dismissing = True
        self.im_context.focus_out()
        self.entry_spring.target = 0.0
        self._request_frame()

    def _finish_dismiss(self):
        release_instance_lock(self.lock_fd, self.pid_path)
        self.lock_fd = None
        self.hide()
        Gtk.main_quit()

    def drill_down(self, child_items: list):
        if not child_items or not isinstance(child_items, list):
            return
        self.menu_stack.append((self.apps, self.hovered_index))
        self.apps = child_items
        self.setup_current_tier()
        self.hovered_index = None
        self.keyboard_selected = None
        if self.last_mouse_pos is not None:
            self.update_hover(self.last_mouse_pos[0], self.last_mouse_pos[1])

        self.trans_spring.omega = 15.0
        self.trans_spring.zeta = 0.80
        self.trans_spring.current = 0.75
        self.trans_spring.target = 1.0
        self.trans_spring.velocity = 0.0
        self._request_frame()

    def return_to_parent(self):
        if not self.menu_stack:
            self.dismiss_menu()
            return

        parent_items, _ = self.menu_stack.pop()
        self.apps = parent_items
        self.setup_current_tier()
        self.hovered_index = None
        self.keyboard_selected = None
        if self.last_mouse_pos is not None:
            self.update_hover(self.last_mouse_pos[0], self.last_mouse_pos[1])

        self.trans_spring.omega = 16.0
        self.trans_spring.zeta = 0.90
        self.trans_spring.current = 1.15
        self.trans_spring.target = 1.0
        self.trans_spring.velocity = 0.0
        self._request_frame()

    def trigger_app(self, item: dict):
        # 1. Folder drill-down
        if "children" in item and len(item["children"]) > 0:
            self.drill_down(item["children"])
            return

        # 2. Web URL direct launching via xdg-open
        url = item.get("url", "")
        cmd = item.get("cmd") or item.get("id") or item.get("name", "").lower()
        target_url = url if url else (cmd if cmd.startswith(("http://", "https://", "www.")) else "")

        if target_url:
            if target_url.startswith("www."):
                target_url = "https://" + target_url
            try:
                subprocess.Popen(["xdg-open", target_url])
            except Exception as e:
                print(f"Error opening URL: {e}", file=sys.stderr)
            self.dismiss_menu()
            return

        # 3. Local Scratchpad / App Command
        script_path = os.path.expanduser("~/.config/niri/scripts/niri-scratch-toggle.sh")
        if not os.path.isfile(script_path):
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "niri-scratch-toggle.sh")
        try:
            subprocess.Popen(["/bin/bash", script_path, cmd])
        except Exception as e:
            print(f"Error launching scratchpad: {e}", file=sys.stderr)
        self.dismiss_menu()

    def trigger_search(self):
        query = self.search_query.strip()
        if not query or not self.search_engines:
            return
        engine = self.search_engines[self.current_engine_idx % len(self.search_engines)]
        encoded_query = urllib.parse.quote_plus(query)
        target_url = engine.get("url", "https://www.bing.com/search?q={query}").replace("{query}", encoded_query)
        try:
            subprocess.Popen(["xdg-open", target_url])
        except Exception as e:
            print(f"Error launching web search: {e}", file=sys.stderr)
        self.dismiss_menu()

    def set_anchor_center(self, cursor_x: float, cursor_y: float):
        w = self.get_allocated_width() or 1920
        h = self.get_allocated_height() or 1080
        pad_x, pad_y = 250.0, 210.0
        self.center_x = max(pad_x, min(w - pad_x, cursor_x))
        self.center_y = max(pad_y, min(h - pad_y, cursor_y))
        self.origin_locked = True

    def _request_frame(self):
        if self.tick_callback_id is None:
            self.last_frame_time = 0
            self.tick_callback_id = self.add_tick_callback(self.on_frame_tick)

    def on_frame_tick(self, widget, frame_clock):
        frame_time = frame_clock.get_frame_time()
        dt = 0.016 if self.last_frame_time == 0 else (frame_time - self.last_frame_time) / 1_000_000.0
        self.last_frame_time = frame_time
        self.cursor_time += dt

        still_animating = False

        if self.entry_spring.update(dt):
            still_animating = True

        if self.is_dismissing and self.entry_spring.current <= 0.02:
            self._finish_dismiss()
            self.tick_callback_id = None
            return GLib.SOURCE_REMOVE

        if self.trans_spring.update(dt):
            still_animating = True

        if self.search_spring.update(dt):
            still_animating = True

        if self.engine_switch_spring.update(dt):
            still_animating = True

        # Keep smooth animation for breathing neon cursor while search is active
        if self.search_spring.current > 0.01 and not self.is_dismissing and len(self.menu_stack) == 0:
            still_animating = True

        active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index
        for i in range(self.num_items):
            if i < len(self.node_springs):
                self.node_springs[i].target = 1.0 if (active_idx == i and not self.is_dismissing) else 0.0
                if self.node_springs[i].update(dt):
                    still_animating = True

        if active_idx is not None and not self.is_dismissing and active_idx < self.num_items and self.search_spring.current <= 0.01:
            ang_rad = math.radians(self.apps[active_idx]["center_angle"])
            self.core_spring_x.target = math.cos(ang_rad) * 10.0
            self.core_spring_y.target = math.sin(ang_rad) * 10.0
        else:
            self.core_spring_x.target = 0.0
            self.core_spring_y.target = 0.0

        if self.core_spring_x.update(dt) or self.core_spring_y.update(dt):
            still_animating = True

        self.queue_draw()

        if not still_animating:
            self.tick_callback_id = None
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE

    def update_hover(self, mx: float, my: float):
        if not self.origin_locked:
            self.set_anchor_center(mx, my)

        if self.keyboard_selected is not None:
            if self.keyboard_nav_pos and math.hypot(mx - self.keyboard_nav_pos[0], my - self.keyboard_nav_pos[1]) > 15.0:
                self.keyboard_selected = None
                self.keyboard_nav_pos = None
            else:
                self.last_mouse_pos = (mx, my)
                return

        self.last_mouse_pos = (mx, my)
        dx = mx - self.center_x
        dy = my - self.center_y
        dist = math.hypot(dx, dy)

        if dist < DEADZONE_RADIUS:
            new_hover = None
        else:
            angle_deg = math.degrees(math.atan2(dy, dx))
            best_idx = None
            min_diff = 999.0

            for i, app in enumerate(self.apps):
                c_ang = app["center_angle"]
                diff = abs((angle_deg - c_ang + 180.0) % 360.0 - 180.0)
                if self.hovered_index == i:
                    diff -= HYSTERESIS_DEG
                if diff < min_diff:
                    min_diff = diff
                    best_idx = i

            new_hover = best_idx

        if new_hover != self.hovered_index:
            self.hovered_index = new_hover
            self._request_frame()

    def on_enter_notify(self, widget, event):
        if not self.origin_locked:
            self.set_anchor_center(event.x, event.y)
        return True

    def on_motion_notify(self, widget, event):
        if not self.is_dismissing:
            self.update_hover(event.x, event.y)
        return True

    def on_button_press(self, widget, event):
        if self.is_dismissing:
            return True
        if not self.origin_locked:
            self.set_anchor_center(event.x, event.y)
        if event.button == 1:
            self.press_pos = (event.x, event.y)

        is_search_mode = (self.search_spring.current > 0.05 or bool(self.search_query)) and len(self.menu_stack) == 0

        # Right-click (button 3) or Middle-click (button 2)
        if event.button in (2, 3):
            if is_search_mode:
                self.search_query = ""
                self.search_active = False
                self.search_spring.target = 0.0
                self._request_frame()
            elif len(self.menu_stack) > 0:
                self.return_to_parent()
            else:
                self.dismiss_menu()
            return True

        # Left-click (button 1)
        if event.button == 1:
            cx, cy = (self.center_x or 960.0), (self.center_y or 540.0)
            dx = event.x - cx
            dy = event.y - cy
            dist = math.hypot(dx, dy)

            # Check search mode click handling
            if len(self.menu_stack) == 0:
                search_prog = max(0.0, min(1.0, self.search_spring.current))
                if search_prog > 0.05:
                    sw = 36.0 + (390.0 - 36.0) * search_prog
                    sh = 36.0 + (64.0 - 36.0) * search_prog
                    if abs(dx) <= sw / 2.0 and abs(dy) <= sh / 2.0:
                        # Clicked inside left circular engine avatar -> cycle engine
                        if dx < -sw / 4.0 and len(self.search_engines) > 0:
                            self.current_engine_idx = (self.current_engine_idx + 1) % len(self.search_engines)
                            self.engine_switch_spring.current = 0.85
                            self.engine_switch_spring.target = 1.0
                        self.search_active = True
                        self.search_spring.target = 1.0
                        self.keyboard_selected = None
                        self._request_frame()
                        return True
                    else:
                        # Clicked outside search pill -> collapse back to star-ring
                        self.search_query = ""
                        self.search_active = False
                        self.search_spring.target = 0.0
                        self._request_frame()
                        return True
                elif dist <= DEADZONE_RADIUS:
                    # Clicked idle center dot -> wake search
                    self.search_active = True
                    self.search_spring.target = 1.0
                    self.keyboard_selected = None
                    self._request_frame()
                    return True

            active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index
            if active_idx is not None and active_idx < self.num_items and self.search_spring.current <= 0.05:
                self.trigger_app(self.apps[active_idx])
            elif len(self.menu_stack) > 0:
                self.return_to_parent()
            else:
                self.dismiss_menu()
            return True

        return False

    def on_button_release(self, widget, event):
        if self.is_dismissing or event.button not in (1, 8, 9):
            return False
        # Mouse flick release (LMB, Side button): releasing over an active capsule triggers it
        if not self.search_active and self.search_spring.current <= 0.05 and len(self.menu_stack) == 0:
            if self.hovered_index is not None and self.hovered_index < self.num_items:
                self.trigger_app(self.apps[self.hovered_index])
                return True
        return False

    def on_scroll(self, widget, event):
        if self.is_dismissing:
            return False

        step = 1 if event.direction == Gdk.ScrollDirection.DOWN else (-1 if event.direction == Gdk.ScrollDirection.UP else 0)
        if step == 0:
            return False

        # Search mode: mouse wheel cycles through search engines
        if (self.search_spring.current > 0.05 or self.search_active) and self.search_engines:
            self.current_engine_idx = (self.current_engine_idx + step) % len(self.search_engines)
            self.engine_switch_spring.current = 0.85
            self.engine_switch_spring.target = 1.0
            self._request_frame()
            return True

        # Star-ring mode: mouse wheel cycles highlighted item
        cur = self.keyboard_selected if self.keyboard_selected is not None else (self.hovered_index or 0)
        self.keyboard_selected = (cur + step) % self.num_items
        self.keyboard_nav_pos = self.last_mouse_pos
        self._request_frame()
        return True

    def on_im_commit(self, im_context, text):
        if len(self.menu_stack) == 0:
            self.search_active = True
            self.search_query += text
            self.search_spring.target = 1.0
            self.keyboard_selected = None
            self._request_frame()

    def on_im_preedit_changed(self, im_context):
        self._request_frame()

    def on_key_release(self, widget, event):
        if self.search_active and len(self.menu_stack) == 0 and self.im_context.filter_keypress(event):
            return True

        if self.is_dismissing:
            return False

        # Hotkey flick release: releasing Super / A / S while hovering over a capsule
        keyval = event.keyval
        if keyval in (
            Gdk.KEY_Super_L, Gdk.KEY_Super_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R,
            Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_a, Gdk.KEY_A, Gdk.KEY_s, Gdk.KEY_S
        ):
            if not self.search_active and self.search_spring.current <= 0.05 and len(self.menu_stack) == 0:
                if self.hovered_index is not None and self.hovered_index < self.num_items:
                    self.trigger_app(self.apps[self.hovered_index])
                    return True

        return False

    def on_key_press(self, widget, event):
        if self.is_dismissing:
            return True

        keyval = event.keyval
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)

        if self.center_x is None:
            w = self.get_allocated_width() or 1920
            h = self.get_allocated_height() or 1080
            self.center_x = w / 2.0
            self.center_y = h / 2.0
            self.origin_locked = True

        is_search = (self.search_spring.current > 0.05 or bool(self.search_query)) and len(self.menu_stack) == 0

        # ── 1. SEARCH ACTIVE MODE ─────────────────────────────────────────
        if is_search:
            # Let Wayland CJK IME consume keystrokes first
            if self.im_context.filter_keypress(event):
                return True

            # Ctrl shortcuts for desktop editing
            if ctrl:
                if keyval in (Gdk.KEY_v, Gdk.KEY_V):
                    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                    text = clip.wait_for_text()
                    if text:
                        self.search_query += text.strip()
                        self._request_frame()
                    return True
                elif keyval in (Gdk.KEY_c, Gdk.KEY_C):
                    if self.search_query:
                        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.search_query, -1)
                    return True
                elif keyval in (Gdk.KEY_u, Gdk.KEY_U):
                    self.search_query = ""
                    self.search_active = False
                    self.search_spring.target = 0.0
                    self._request_frame()
                    return True
                elif keyval in (Gdk.KEY_BackSpace, Gdk.KEY_w, Gdk.KEY_W):
                    words = self.search_query.rstrip().rsplit(None, 1)
                    self.search_query = words[0] if len(words) > 1 else ""
                    if not self.search_query:
                        self.search_active = False
                        self.search_spring.target = 0.0
                    self._request_frame()
                    return True

            # Escape -> collapse search back to star-ring
            if keyval == Gdk.KEY_Escape:
                self.search_query = ""
                self.search_active = False
                self.search_spring.target = 0.0
                self._request_frame()
                return True

            # Backspace -> delete character (collapse when empty)
            if keyval == Gdk.KEY_BackSpace:
                self.search_query = self.search_query[:-1]
                if not self.search_query:
                    self.search_active = False
                    self.search_spring.target = 0.0
                self._request_frame()
                return True

            # Tab / Shift+Tab / Up / Down -> cycle search engines
            if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Up, Gdk.KEY_Down):
                if self.search_engines:
                    is_back = bool(event.state & Gdk.ModifierType.SHIFT_MASK) or keyval in (Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Up)
                    step = -1 if is_back else 1
                    self.current_engine_idx = (self.current_engine_idx + step) % len(self.search_engines)
                    self.engine_switch_spring.current = 0.85
                    self.engine_switch_spring.target = 1.0
                    self._request_frame()
                    return True

            # Return / Enter -> execute web search
            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                if self.search_query.strip():
                    self.trigger_search()
                return True

            # Character input (ASCII / Unicode)
            char = chr(keyval) if (32 <= keyval <= 126 and not ctrl) else ""
            if char:
                self.search_query += char
                self._request_frame()
                return True

            return False

        # ── 2. IDLE / ROOT / SUBMENU MODE ─────────────────────────────────
        # Ignore modifier keys (Shift, Ctrl, Alt, Super, F-keys, etc.)
        if is_modifier_or_nav_key(keyval):
            return False

        # (A) Number keys 1..9 -> direct instant launch
        if Gdk.KEY_1 <= keyval <= Gdk.KEY_9 and not ctrl:
            num = keyval - Gdk.KEY_1
            if num < self.num_items:
                self.trigger_app(self.apps[num])
                return True

        # (B) Escape / Backspace -> close menu or return to parent
        if keyval in (Gdk.KEY_Escape, Gdk.KEY_BackSpace):
            if len(self.menu_stack) > 0:
                self.return_to_parent()
            else:
                self.dismiss_menu()
            return True

        # (C) Tab / Shift+Tab -> wake up search in root; cycle items in submenu
        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            if len(self.menu_stack) == 0:
                if self.search_engines:
                    is_back = bool(event.state & Gdk.ModifierType.SHIFT_MASK) or keyval == Gdk.KEY_ISO_Left_Tab
                    step = -1 if is_back else 1
                    self.current_engine_idx = (self.current_engine_idx + step) % len(self.search_engines)
                    self.search_active = True
                    self.search_spring.target = 1.0
                    self.engine_switch_spring.current = 0.85
                    self.engine_switch_spring.target = 1.0
                    self._request_frame()
                    return True
            else:
                is_back = bool(event.state & Gdk.ModifierType.SHIFT_MASK) or keyval == Gdk.KEY_ISO_Left_Tab
                cur = self.keyboard_selected if self.keyboard_selected is not None else (self.hovered_index or 0)
                step = -1 if is_back else 1
                self.keyboard_selected = (cur + step) % self.num_items
                self.keyboard_nav_pos = self.last_mouse_pos
                self._request_frame()
                return True

        # (D) Return / Enter / Space -> trigger active item or wake search
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index
            if active_idx is not None and active_idx < self.num_items:
                self.trigger_app(self.apps[active_idx])
            elif len(self.menu_stack) == 0:
                self.search_active = True
                self.search_spring.target = 1.0
                self.keyboard_selected = None
                self._request_frame()
            else:
                self.return_to_parent()
            return True

        # (E) Standard spatial arrow keys (Left, Right, Down, Up)
        dir_map = {
            Gdk.KEY_Left: 180.0,
            Gdk.KEY_Right: 0.0,
            Gdk.KEY_Down: 90.0,
            Gdk.KEY_Up: -90.0,
        }
        if keyval in dir_map:
            target_angle = dir_map[keyval]
            best_idx = None
            min_diff = 999.0
            for i, app in enumerate(self.apps):
                diff = abs((target_angle - app["center_angle"] + 180.0) % 360.0 - 180.0)
                if diff < min_diff:
                    min_diff = diff
                    best_idx = i
            if best_idx is not None:
                self.keyboard_selected = best_idx
                self.keyboard_nav_pos = self.last_mouse_pos
                self._request_frame()
                return True

        # (F) All letter keys & IME input directly activate search
        if len(self.menu_stack) == 0:
            if self.im_context.filter_keypress(event):
                self.search_active = True
                self.search_spring.target = 1.0
                self.keyboard_selected = None
                return True
            char = chr(keyval) if (32 <= keyval <= 126 and not ctrl) else ""
            if char:
                self.search_active = True
                self.search_spring.target = 1.0
                self.keyboard_selected = None
                self.search_query += char
                self._request_frame()
                return True

        return False

    def on_draw(self, widget, cr):
        entry_val = max(0.0, min(1.0, self.entry_spring.current))
        if entry_val <= 0.001:
            return False

        trans_val = max(0.2, self.trans_spring.current)
        search_prog = max(0.0, min(1.0, self.search_spring.current))
        cx, cy = (self.center_x or 960.0), (self.center_y or 540.0)
        p = self.palette
        active_idx = self.keyboard_selected if self.keyboard_selected is not None else self.hovered_index
        is_submenu = len(self.menu_stack) > 0

        # Outer component alpha: Fades to 0.0 during search (100% focused)
        outer_alpha = max(0.0, 1.0 - search_prog * 1.05) * entry_val if not is_submenu else entry_val

        # 1. Atmospheric Scrim
        draw_scrim(cr, entry_val, p["is_dark"], p["surface_dim"])

        # Scale & Alpha Transform
        cr.save()
        scale = (0.76 + 0.24 * entry_val) * trans_val
        cr.translate(cx, cy)
        cr.scale(scale, scale)
        cr.translate(-cx, -cy)

        core_x = cx + self.core_spring_x.current
        core_y = cy + self.core_spring_y.current

        search_disp = search_prog * 20.0 if not is_submenu else 0.0
        orbit_r = max(BASE_ORBIT_RADIUS, 120.0 + self.num_items * 12.0) + search_disp

        # 2. Celestial Star-Ring
        if outer_alpha > 0.01:
            draw_star_ring(cr, cx, cy, orbit_r, self.num_items, self.apps, self.node_springs,
                           active_idx, outer_alpha, p["outline"])

        # 3. Dynamic Tethers
        if search_prog <= 0.01:
            draw_tethers(cr, cx, cy, core_x, core_y, orbit_r, self.apps, self.node_springs,
                         outer_alpha, p["outline"])

        # 4. Center Core: Smooth Morphing
        if is_submenu:
            draw_submenu_return_core(cr, core_x, core_y, entry_val, p, self.layout_back, self.back_ink_rect)
        else:
            if search_prog <= 0.01:
                draw_idle_center_dot(cr, core_x, core_y, entry_val, active_idx, self.apps, self.num_items, p)
            else:
                placeholder_size = (self.placeholder_w, self.placeholder_h)
                draw_search_hub(cr, cx, cy, search_prog, entry_val, self.search_engines,
                                self.current_engine_idx, self.engine_switch_spring, self.search_query,
                                self.cursor_time, self.layout_placeholder, placeholder_size, p,
                                self.create_pango_layout, self.update_im_cursor_location)

        # 5. M3E Content-Aware Adaptive Streamline Capsules
        if outer_alpha > 0.01:
            draw_capsules(cr, cx, cy, orbit_r, self.apps, self.node_springs, outer_alpha, p)

        cr.restore()
        return False
