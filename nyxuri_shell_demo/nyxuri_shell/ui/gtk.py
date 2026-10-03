import datetime
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nyxuri_shell import apps, orbit, state as S, sysinfo, wallpaper as W
from nyxuri_shell.color import rgb_of as _rgb_of

PANELS = ("launcher", "session", "settings", "clipboard", "wallpaper")

BAR_LEFT = ("launcher", "workspaces")
BAR_CENTER = ("clock",)
BAR_RIGHT = ("sysmon", "volume", "battery", "notifications", "session")

POLL_MS = 2000
CLOCK_MS = 10000
FRAME_MS = 16
CLIP_LIMIT = 60


def _load_gi():
    try:
        import gi
    except ImportError:
        return None
    return gi


def available() -> bool:
    gi = _load_gi()
    if gi is None:
        return False
    try:
        gi.require_version("Gtk", "4.0")
    except ValueError:
        return False
    try:
        from gi.repository import Gtk
    except (ImportError, ValueError):
        return False
    return True


LAYER_SHELL_NAMESPACES = (("Gtk4LayerShell", "1.0"), ("GtkLayerShell", "0.1"))


def _load_layer_shell():
    gi = _load_gi()
    if gi is None:
        return None
    import importlib

    for namespace, version in LAYER_SHELL_NAMESPACES:
        try:
            gi.require_version(namespace, version)
        except ValueError:
            continue
        try:
            return importlib.import_module(f"gi.repository.{namespace}")
        except (ImportError, ValueError):
            continue
    return None


def layer_shell_available() -> bool:
    return _load_layer_shell() is not None


def layer_shell_library_path() -> Optional[str]:
    import ctypes.util
    import glob

    found = ctypes.util.find_library("gtk4-layer-shell")
    if found:
        return found
    for pattern in (
        "/usr/local/lib/*/libgtk4-layer-shell.so.0",
        "/usr/local/lib/libgtk4-layer-shell.so.0",
        "/usr/lib/*/libgtk4-layer-shell.so.0",
        "/usr/lib/libgtk4-layer-shell.so.0",
    ):
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]
    return None


def ensure_link_order() -> Optional[str]:
    if not available() or _load_layer_shell() is None:
        return None
    path = layer_shell_library_path()
    if path is None:
        return None
    if path in (os.environ.get("LD_PRELOAD", "") or "").split(":"):
        return None
    return path


def reexec_with_preload(path: str) -> None:
    env = dict(os.environ)
    existing = env.get("LD_PRELOAD", "")
    env["LD_PRELOAD"] = f"{path}:{existing}" if existing else path
    env["NYXURI_SHELL_REEXEC"] = "1"
    source_dir = str(Path(__file__).resolve().parent.parent)
    code = (
        "import sys;"
        f"sys.path.insert(0, {source_dir!r});"
        "sys.argv[0] = 'nyxuri-shell';"
        "from nyxuri_shell.daemon import main;"
        "sys.exit(main())"
    )
    os.execve(sys.executable, [sys.executable, "-c", code, *sys.argv[1:]], env)


def clipboard_history(limit: int = CLIP_LIMIT) -> List[str]:
    import shutil

    if not shutil.which("cliphist"):
        return []
    try:
        res = subprocess.run(["cliphist", "list"], capture_output=True, text=True,
                             timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if res.returncode != 0:
        return []
    out: List[str] = []
    for line in res.stdout.splitlines()[:limit]:
        _, _, text = line.partition("\t")
        cleaned = " ".join(text.split())
        if cleaned:
            out.append(cleaned[:120])
    return out


def copy_to_clipboard(text: str) -> bool:
    import shutil

    for tool in ("wl-copy", "xclip"):
        if not shutil.which(tool):
            continue
        cmd = [tool] if tool == "wl-copy" else [tool, "-selection", "clipboard"]
        try:
            subprocess.run(cmd, input=text, text=True, timeout=5, check=False)
            return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False


def notification_count() -> int:
    import shutil

    if not shutil.which("dbus-send"):
        return 0
    try:
        res = subprocess.run(
            ["dbus-send", "--session", "--print-reply",
             "--dest=org.freedesktop.DBus",
             "/org/freedesktop/DBus", "org.freedesktop.DBus.ListNames"],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    if res.returncode != 0:
        return 0
    return sum(1 for line in res.stdout.splitlines() if "org.freedesktop.Notifications" in line)


SESSION_ACTIONS = (
    ("lock", "Lock", "\U0001F512"),
    ("logout", "Log Out", "\u23FB"),
    ("suspend", "Suspend", "\u263E"),
    ("reboot", "Reboot", "\u21BB"),
    ("shutdown", "Shut Down", "\u23FB"),
)


def run_session_action(action: str) -> bool:
    import shutil

    commands = {
        "lock": (["loginctl", "lock-session"], ["swaylock", "-f"], ["gtklock"]),
        "logout": (["loginctl", "terminate-user", os.environ.get("USER", "")],
                   ["niri", "msg", "action", "quit"], ["swaymsg", "exit"]),
        "suspend": (["systemctl", "suspend"],),
        "reboot": (["systemctl", "reboot"],),
        "shutdown": (["systemctl", "poweroff"],),
    }
    for argv in commands.get(action, ()):
        if not argv or not argv[0] or not shutil.which(argv[0]):
            continue
        try:
            subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            return True
        except OSError:
            continue
    return False


class Model:
    def __init__(self, state: S.ShellState):
        self.state = state
        self.panel_visibility: Dict[str, bool] = {p: False for p in PANELS}
        self.tree = orbit.build_tree(orbit.load_items())
        self.orbit = orbit.OrbitState()
        self.anim = orbit.Animator()
        self.flick = orbit.Flick()
        self.engines, self.search_meta = orbit.load_engines()
        self.query = ""
        self.wallpaper_files: List[Path] = []
        self.wallpaper_index = 0
        self.clipboard: List[str] = []
        self._scheme_cache: Optional[Dict[str, str]] = None
        self._scheme_key: Optional[Tuple[str, str, str]] = None
        self._app_cache: List[Any] = []
        self._app_hits: Dict[str, List[Any]] = {}

    def colors(self) -> Dict[str, str]:
        appearance = self.state.appearance
        key = (appearance.source_color, appearance.mode_effective(), appearance.scheme)
        if key != self._scheme_key:
            scheme = appearance.scheme_colors()
            self._scheme_cache = scheme.get(appearance.mode_effective(), {})
            self._scheme_key = key
        return self._scheme_cache or {}

    def invalidate(self) -> None:
        self._scheme_key = None
        self._app_cache = []
        self._app_hits = {}

    def palette(self, role: str, fallback: str = "#000000") -> str:
        return self.colors().get(role, fallback)

    def toggle_panel(self, panel: str) -> bool:
        if panel not in self.panel_visibility:
            panel = "launcher"
        visible = not self.panel_visibility[panel]
        for key in self.panel_visibility:
            self.panel_visibility[key] = (key == panel and visible)
        if visible:
            self.query = ""
            self._prepare_panel(panel)
        return visible

    def _prepare_panel(self, panel: str) -> None:
        if panel == "wallpaper":
            self.wallpaper_files = W.scan_directory(S.wallpapers_dir())
            self.wallpaper_index = 0
        elif panel == "clipboard":
            self.clipboard = clipboard_history()

    def any_panel_visible(self) -> bool:
        return any(self.panel_visibility.values())

    def visible_panel(self) -> Optional[str]:
        for name, shown in self.panel_visibility.items():
            if shown:
                return name
        return None

    def workspace_text(self) -> str:
        marks = []
        for ws in sysinfo.workspaces()[:9]:
            marks.append("\u25CF" if ws.focused else ("\u25CB" if ws.active else "\u00B7"))
        return " ".join(marks)

    def clock_text(self) -> str:
        return datetime.datetime.now().strftime("%m/%d/%y %H:%M")

    def sysmon_text(self) -> str:
        parts = []
        cpu = sysinfo.cpu_percent(blocking=False)
        if cpu is not None:
            parts.append(f"CPU {cpu:.0f}%")
        mem = sysinfo.memory_percent()
        if mem is not None:
            parts.append(f"RAM {mem:.0f}%")
        return "  ".join(parts)

    def volume_text(self) -> str:
        current = sysinfo.volume()
        if current is None:
            return ""
        percent, muted = current
        return "\U0001F507" if muted else f"\U0001F50A {percent}%"

    def battery_text(self) -> str:
        info = sysinfo.battery()
        if info is None:
            return ""
        icon = "\u26A1" if info.charging else "\U0001F50B"
        return f"{icon} {info.percent:.0f}%"

    def text_for(self, name: str) -> str:
        return {
            "launcher": "\u2630",
            "workspaces": self.workspace_text(),
            "clock": self.clock_text(),
            "sysmon": self.sysmon_text(),
            "volume": self.volume_text(),
            "battery": self.battery_text(),
            "notifications": "\U0001F514" if self.notifications_pending() else "\U0001F515",
            "session": "\u23FB",
        }.get(name, name)

    def notifications_pending(self) -> bool:
        return bool(notification_count())

    def click_bar(self, name: str) -> bool:
        if name in ("launcher", "session", "settings", "clipboard"):
            return self.toggle_panel(name)
        if name == "volume":
            sysinfo.toggle_mute()
            return True
        if name == "notifications":
            return self.toggle_panel("clipboard")
        return False

    def launcher_rows(self) -> List[Tuple[str, str, str]]:
        if self.query:
            hits = apps.search(self.query, limit=8)
            return [(a.name, a.id, "") for a in hits]
        items = self.orbit.current_items(self.tree)
        return [(i.name, i.desc, "folder" if i.is_folder else "") for i in items]

    def activate_launcher_row(self, index: int) -> Tuple[str, str]:
        if self.query:
            hits = apps.search(self.query, limit=8)
            if 0 <= index < len(hits):
                return ("app", hits[index].id)
            return ("none", "")
        items = self.orbit.current_items(self.tree)
        if not (0 <= index < len(items)):
            return ("none", "")
        item = items[index]
        if item.is_folder:
            self.orbit.enter(index, item)
            return ("folder", item.id)
        return ("item", item.id)

    def current_item(self) -> Optional[orbit.Item]:
        if self.query:
            return None
        return self.orbit.current_item(self.tree)


def build_css(state: S.ShellState) -> str:
    scheme = state.appearance.scheme_colors()
    colors = scheme.get(state.appearance.mode_effective(), {})

    def c(role: str, fallback: str) -> str:
        return colors.get(role, fallback)

    radius = state.layout.capsule_radius if state.layout.capsule else 12
    opacity = state.appearance.opacity
    scale = state.layout.scale

    return f"""
* {{
    font-family: "JetBrains Mono", "Noto Sans CJK SC", sans-serif;
    font-size: {int(12 * scale)}px;
}}
.nyx-root {{ background: transparent; }}
.nyx-root.panel-root {{
    background: {c('surface_container_low', '#1d1b20')};
}}
.nyx-bar {{
    background: alpha({c('surface_container', '#1c1b1f')}, {opacity:.2f});
    border: 1px solid alpha({c('outline_variant', '#49454f')}, 0.55);
    border-radius: {radius}px;
    color: {c('on_surface', '#e6e1e5')};
    padding: 0 10px;
    min-height: {state.layout.bar_height}px;
}}
.nyx-capsule {{
    background: alpha({c('surface_container_high', '#2b2930')}, 0.79);
    border-radius: {radius}px;
    padding: 2px 10px;
    margin: 3px 4px;
}}
.nyx-capsule:hover {{ background: alpha({c('surface_container_highest', '#36343b')}, 0.90); }}
.nyx-panel {{
    background: alpha({c('surface_container_low', '#1d1b20')}, 0.94);
    border: 1px solid alpha({c('outline_variant', '#49454f')}, 0.50);
    border-radius: 28px;
    padding: 16px;
    color: {c('on_surface', '#e6e1e5')};
    min-width: 540px;
    min-height: 360px;
}}
.nyx-entry {{
    background: alpha({c('surface_container_highest', '#36343b')}, 0.70);
    border-radius: 14px;
    padding: 10px 14px;
    color: {c('on_surface', '#e6e1e5')};
}}
.nyx-entry:focus {{ outline: 2px solid {c('primary', '#d0bcff')}; }}
.nyx-row {{
    background: transparent;
    border-radius: 12px;
    padding: 8px 12px;
    color: {c('on_surface', '#e6e1e5')};
}}
.nyx-row:hover {{ background: alpha({c('surface_container_high', '#2b2930')}, 0.70); }}
.nyx-row.sel {{
    background: alpha({c('primary_container', '#4f378b')}, 0.85);
    color: {c('on_primary_container', '#eaddff')};
}}
.nyx-muted {{ color: {c('on_surface_variant', '#cac4d0')}; }}
.nyx-accent {{ color: {c('primary', '#d0bcff')}; }}
.nyx-osd {{
    background: alpha({c('surface_container_high', '#2b2930')}, 0.90);
    border-radius: 20px;
    padding: 12px 20px;
    color: {c('on_surface', '#e6e1e5')};
}}
.nyx-thumb {{
    border-radius: 12px;
    border: 2px solid transparent;
}}
.nyx-thumb.sel {{ border: 2px solid {c('primary', '#d0bcff')}; }}
"""


def _cairo_rgb(hex_str: str, alpha: float = 1.0) -> Tuple[float, float, float, float]:
    r, g, b = _rgb_of(hex_str)
    return (r / 255.0, g / 255.0, b / 255.0, alpha)


class GtkShell:
    def __init__(self, shell: Any):
        if not available():
            raise RuntimeError("gtk4 unavailable")

        from gi.repository import Gdk, GLib, Gtk

        self._Gtk, self._GLib, self._Gdk = Gtk, GLib, Gdk
        self.shell = shell
        self.state = shell.state
        self.model = Model(self.state)
        self._layer_shell = _load_layer_shell()
        self.layer_shell = self._layer_shell is not None
        self._provider = Gtk.CssProvider()
        self._bar_window = None
        self._panel_window = None
        self._orbit_window = None
        self._osd_window = None
        self._labels: Dict[str, Any] = {}
        self._rows: List[Any] = []
        self._loop = None
        self._loop_running = False
        self._orbit_ticking = False
        self._orbit_last = 0
        self._orbit_source = 0
        self._build()

    def _build(self) -> None:
        Gtk = self._Gtk
        display = self._Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, self._provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._reload_now()

        self._bar_window = self._surface("nyxuri-bar", kind="bar")
        self._bar_window.set_child(self._build_bar())
        self._bar_window.present()

        self._panel_window = self._surface("nyxuri-panel", kind="panel")
        self._panel_window.add_css_class("panel-root")
        self._panel_window.set_default_size(560, 400)
        self._panel_window.set_child(self._build_panel())
        self._panel_window.set_visible(False)

        self._orbit_window = self._surface("nyxuri-orbit", kind="panel")
        self._orbit_window.set_default_size(520, 520)
        self._orbit_window.set_child(self._build_orbit())
        self._orbit_window.set_visible(False)

        self._osd_window = self._surface("nyxuri-osd", kind="osd")
        self._osd_window.set_child(self._build_osd())
        self._osd_window.set_visible(False)

        for win in (self._bar_window, self._panel_window, self._orbit_window):
            self._keybind(win)
        self._centre_surfaces()

    def _surface(self, namespace: str, kind: str):
        Gtk = self._Gtk
        win = Gtk.Window()
        win.set_decorated(False)
        win.set_resizable(False)
        win.add_css_class("nyx-root")
        if self.layer_shell:
            LS = self._layer_shell
            LS.init_for_window(win)
            LS.set_namespace(win, namespace)
            if kind == "bar":
                LS.set_anchor(win, LS.Edge.TOP, True)
                LS.set_anchor(win, LS.Edge.LEFT, True)
                LS.set_anchor(win, LS.Edge.RIGHT, True)
                LS.set_layer(win, LS.Layer.TOP)
                LS.set_exclusive_zone(win, 36)
                LS.set_keyboard_mode(win, LS.KeyboardMode.NONE)
            elif kind == "osd":
                LS.set_anchor(win, LS.Edge.BOTTOM, True)
                LS.set_margin(win, LS.Edge.BOTTOM, 80)
                LS.set_layer(win, LS.Layer.OVERLAY)
                LS.set_keyboard_mode(win, LS.KeyboardMode.NONE)
            else:
                LS.set_anchor(win, LS.Edge.TOP, True)
                LS.set_anchor(win, LS.Edge.LEFT, True)
                LS.set_layer(win, LS.Layer.OVERLAY)
                LS.set_keyboard_mode(win, LS.KeyboardMode.ON_DEMAND)
        else:
            win.set_default_size(1280, 36 if kind == "bar" else 720)
        return win

    def _build_bar(self):
        Gtk = self._Gtk
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bar.add_css_class("nyx-bar")
        for name in BAR_LEFT:
            bar.append(self._capsule(name))
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)
        for name in BAR_CENTER:
            bar.append(self._capsule(name))
        spacer2 = Gtk.Box()
        spacer2.set_hexpand(True)
        bar.append(spacer2)
        for name in BAR_RIGHT:
            bar.append(self._capsule(name))
        return bar

    def _capsule(self, name: str):
        Gtk = self._Gtk
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.add_css_class("nyx-capsule")
        label = Gtk.Label(label=self.model.text_for(name))
        box.append(label)
        self._labels[name] = label
        gesture = Gtk.GestureClick()
        gesture.set_button(1)
        gesture.connect("released", lambda *_a, n=name: self._bar_click(n))
        box.add_controller(gesture)
        if name == "volume":
            scroll = Gtk.EventControllerScroll()
            scroll.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
            scroll.connect("scroll", lambda _c, _dx, dy, _x, _y: self._bar_scroll(name, dy))
            box.add_controller(scroll)
        return box

    def _bar_click(self, name: str) -> None:
        if self.model.click_bar(name):
            self._refresh()

    def _bar_scroll(self, name: str, dy: float) -> bool:
        if name == "volume":
            step = -5 if dy > 0 else 5
            percent = sysinfo.adjust_volume(step)
            if percent is not None:
                self.show_osd(f"Volume {percent}%")
                self._refresh()
            return True
        return False

    def _centre_surfaces(self) -> None:
        if not self.layer_shell:
            return
        LS = self._layer_shell
        monitor = self._Gdk.Display.get_default()
        width, height = 1280, 800
        try:
            monitors = monitor.get_monitors()
            if monitors.get_n_items() > 0:
                geo = monitors.get_item(0).get_geometry()
                width, height = geo.width, geo.height
        except Exception:
            pass
        for win, w, h in ((self._panel_window, 560, 400), (self._orbit_window, 520, 520)):
            if win is None:
                continue
            LS.set_margin(win, LS.Edge.TOP, max(0, (height - h) // 2))
            LS.set_margin(win, LS.Edge.LEFT, max(0, (width - w) // 2))

    def _build_panel(self):
        Gtk = self._Gtk
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.add_css_class("nyx-panel")
        box.set_size_request(560, 400)

        self._panel_title = Gtk.Label(label="")
        self._panel_title.set_xalign(0.0)
        self._panel_title.add_css_class("nyx-accent")
        box.append(self._panel_title)

        self._panel_entry = Gtk.Entry()
        self._panel_entry.add_css_class("nyx-entry")
        self._panel_entry.set_placeholder_text(self.model.search_meta.get("placeholder", ""))
        self._panel_entry.connect("changed", self._on_query_changed)
        self._panel_entry.connect("activate", self._on_entry_activate)
        box.append(self._panel_entry)

        self._panel_scroll = Gtk.ScrolledWindow()
        self._panel_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._panel_scroll.set_vexpand(True)
        self._panel_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._panel_scroll.set_child(self._panel_list)
        box.append(self._panel_scroll)

        return box

    def _build_orbit(self):
        Gtk = self._Gtk
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("nyx-panel")
        self._orbit_area = Gtk.DrawingArea()
        self._orbit_area.set_content_width(520)
        self._orbit_area.set_content_height(520)
        self._orbit_area.set_draw_func(self._draw_orbit)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_orbit_motion)
        motion.connect("leave", lambda *_a: self._orbit_hover(None))
        self._orbit_area.add_controller(motion)

        scroll = Gtk.EventControllerScroll()
        scroll.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self._on_orbit_scroll)
        self._orbit_area.add_controller(scroll)

        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect("released", self._on_orbit_click)
        self._orbit_area.add_controller(click)

        right = Gtk.GestureClick()
        right.set_button(3)
        right.connect("released", self._on_orbit_right_click)
        self._orbit_area.add_controller(right)

        box.append(self._orbit_area)
        return box

    def _on_orbit_click(self, _c, n_press, _x, _y) -> None:
        if n_press != 1:
            return
        if self.model.flick.armed:
            return
        self._orbit_activate()

    def _on_orbit_motion(self, _c, x: float, y: float) -> None:
        width = self._orbit_area.get_width()
        height = self._orbit_area.get_height()
        items = self.model.orbit.current_items(self.model.tree)
        if not items or width <= 0 or height <= 0:
            return
        dx = x - width / 2.0
        dy = y - height / 2.0
        index = orbit.hit_test(dx, dy, len(items), self.model.orbit.hover)
        self._orbit_hover(index)

    def _build_osd(self):
        Gtk = self._Gtk
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add_css_class("nyx-osd")
        self._osd_label = Gtk.Label(label="")
        box.append(self._osd_label)
        return box

    def _draw_orbit(self, area, cr, width, height) -> None:
        model = self.model
        items = model.orbit.current_items(model.tree)
        count = len(items)
        anim = model.anim
        cx, cy = width / 2.0, height / 2.0

        bloom = anim.bloom.value
        sub = anim.subring.value
        if bloom <= 0.001:
            return

        base = min(orbit.BASE_RADIUS, min(width, height) / 2.0 - 80)
        radius = base * (0.55 + 0.45 * bloom) * sub

        surface = _cairo_rgb(model.palette("surface_container_low", "#1d1b20"),
                             0.97 * bloom)
        cr.set_source_rgba(*surface)
        cr.arc(cx, cy, (min(width, height) / 2.0 - 4) * (0.85 + 0.15 * bloom), 0, 6.283185)
        cr.fill()

        if count == 0:
            cr.set_source_rgba(*_cairo_rgb(model.palette("on_surface_variant", "#cac4d0")))
            cr.select_font_face("JetBrains Mono", 0, 0)
            cr.set_font_size(14)
            cr.move_to(cx - 30, cy)
            cr.show_text("empty")
            return

        step = 6.283185307179586 / count
        hover = model.orbit.hover
        hover_t = anim.hover.value
        blind = model.flick.armed
        digits = orbit.digit_map(items)
        digit_of = {v: k for k, v in digits.items()}
        primary = _cairo_rgb(model.palette("primary", "#d0bcff"))
        on_primary = _cairo_rgb(model.palette("on_primary", "#381e72"))
        sec_cont = _cairo_rgb(model.palette("secondary_container", "#4a4458"))
        on_sec_cont = _cairo_rgb(model.palette("on_secondary_container", "#e8def8"))
        pri_cont = _cairo_rgb(model.palette("primary_container", "#4f378b"))
        on_pri_cont = _cairo_rgb(model.palette("on_primary_container", "#eaddff"))
        label_fg = _cairo_rgb(model.palette("on_surface", "#e6e1e5"))
        badge_bg = _cairo_rgb(model.palette("surface_container_highest", "#36343b"), 0.92)

        for index, item in enumerate(items):
            angle = index * step
            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius
            selected = hover == index
            grow = hover_t if selected else 0.0

            if item.is_folder:
                fill, fg = sec_cont, on_sec_cont
            else:
                fill, fg = pri_cont, on_pri_cont
            if selected:
                fill, fg = primary, on_primary

            r = (44.0 + 6.0 * grow) * bloom
            if r < 1.0:
                continue
            if blind and not selected:
                fill = (fill[0], fill[1], fill[2], fill[3] * 0.55)
            cr.set_source_rgba(*fill)
            cr.arc(x, y, r, 0, 6.283185)
            cr.fill()

            if r < 14.0:
                continue
            cr.set_source_rgba(*fg)
            cr.select_font_face("JetBrains Mono", 0, 1)
            cr.set_font_size(22 * bloom)
            glyph = item.icon or item.name[:1]
            ext = cr.text_extents(glyph)
            cr.move_to(x - ext.width / 2 - ext.x_bearing, y - ext.height / 2 - ext.y_bearing)
            cr.show_text(glyph)

            cr.set_source_rgba(*label_fg)
            cr.set_font_size(11)
            label = item.name if len(item.name) <= 12 else item.name[:11] + "\u2026"
            ext = cr.text_extents(label)
            cr.move_to(x - ext.width / 2 - ext.x_bearing, y + r + 16)
            cr.show_text(label)

            badge = digit_of.get(index)
            if badge and r > 20.0:
                bx = x + r * 0.72
                by = y - r * 0.72
                cr.set_source_rgba(*badge_bg)
                cr.arc(bx, by, 10.0, 0, 6.283185)
                cr.fill()
                cr.set_source_rgba(*label_fg)
                cr.set_font_size(11)
                ext = cr.text_extents(badge)
                cr.move_to(bx - ext.width / 2 - ext.x_bearing,
                           by - ext.height / 2 - ext.y_bearing)
                cr.show_text(badge)

        hub_r = orbit.DEADZONE_RADIUS * 0.72 * (0.6 + 0.4 * bloom)
        cr.set_source_rgba(*_cairo_rgb(model.palette("surface_container_highest", "#36343b")))
        cr.arc(cx, cy, hub_r, 0, 6.283185)
        cr.fill()
        cr.set_source_rgba(*label_fg)
        cr.select_font_face("JetBrains Mono", 0, 0)
        cr.set_font_size(12)
        hint = str(model.orbit.depth) if model.orbit.depth else "\u25CF"
        ext = cr.text_extents(hint)
        cr.move_to(cx - ext.width / 2 - ext.x_bearing, cy - ext.height / 2 - ext.y_bearing)
        cr.show_text(hint)

    def _orbit_tick(self) -> bool:
        anim = self.model.anim
        if not anim.active:
            self._orbit_source = 0
            if not anim.open and self._orbit_window is not None:
                self._orbit_window.set_visible(False)
            return False
        now = time.monotonic()
        last = self._orbit_last or now
        self._orbit_last = now
        anim.step(now - last)
        if self._orbit_area is not None:
            self._orbit_area.queue_draw()
        return True

    def _pump_orbit(self) -> None:
        if self._orbit_area is None:
            return
        if self._orbit_source:
            return
        self._orbit_last = 0.0
        self._orbit_source = self._GLib.timeout_add(FRAME_MS, self._orbit_tick)

    def _stop_orbit(self) -> None:
        if self._orbit_source:
            self._GLib.source_remove(self._orbit_source)
            self._orbit_source = 0

    def _keybind(self, win) -> None:
        Gtk = self._Gtk
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key)
        controller.connect("key-released", self._on_key_released)
        win.add_controller(controller)

    def _on_key_released(self, _c, keyval, _code, _mods) -> bool:
        if keyval not in (self._Gdk.KEY_Super_L, self._Gdk.KEY_Super_R,
                          self._Gdk.KEY_Meta_L, self._Gdk.KEY_Meta_R):
            return False
        if not self._orbit_visible():
            self.model.flick.end()
            return False
        if self.model.flick.armed:
            if self.model.flick.button_held:
                self.model.flick.release()
                return True
            self.model.flick.release()
            self._orbit_activate()
            return True
        return False

    def _flick_begin(self) -> None:
        self.model.flick.begin()
        self.show_radial()

    def _on_key(self, _c, keyval, _code, _mods) -> bool:
        if keyval in (self._Gdk.KEY_Super_L, self._Gdk.KEY_Super_R,
                      self._Gdk.KEY_Meta_L, self._Gdk.KEY_Meta_R):
            if not self._orbit_visible():
                self._flick_begin()
            return False

        if keyval == self._Gdk.KEY_Escape:
            if self._orbit_visible() and self.model.orbit.depth > 0:
                if self.model.orbit.back():
                    self.model.anim.leave_subring()
                    self._pump_orbit()
                return True
            self.hide_all()
            return True

        if self._orbit_visible() and not self.model.query:
            if self._orbit_key(keyval, _mods):
                return True

        if keyval in (self._Gdk.KEY_Return, self._Gdk.KEY_KP_Enter):
            self._on_entry_activate(None)
            return True
        return False

    def _orbit_key(self, keyval: int, mods) -> bool:
        model = self.model
        items = model.orbit.current_items(model.tree)
        count = len(items)
        if count == 0:
            return False

        shift = bool(mods & self._Gdk.ModifierType.SHIFT_MASK)
        hover = model.orbit.hover

        if keyval == self._Gdk.KEY_BackSpace:
            if model.orbit.back():
                model.anim.leave_subring()
                self._pump_orbit()
            return True

        if keyval in (self._Gdk.KEY_Return, self._Gdk.KEY_KP_Enter):
            self._orbit_activate()
            return True

        if keyval == self._Gdk.KEY_Tab:
            self._orbit_hover(orbit.rotate(hover, count, -1 if shift else 1))
            return True

        delta = None
        if keyval in (self._Gdk.KEY_Right, self._Gdk.KEY_Down, self._Gdk.KEY_l, self._Gdk.KEY_j):
            delta = 1
        elif keyval in (self._Gdk.KEY_Left, self._Gdk.KEY_Up, self._Gdk.KEY_h, self._Gdk.KEY_k):
            delta = -1
        if delta is not None:
            self._orbit_hover(orbit.rotate(hover, count, delta))
            return True

        index = orbit.digit_index(keyval)
        if index is not None:
            if index < count:
                model.orbit.hover = index
                model.anim.set_hover(index)
                self._orbit_activate()
            return True

        if 0x61 <= keyval <= 0x7A:
            target = orbit.mnemonic_index(items, chr(keyval))
            if target is not None:
                self._orbit_hover(target)
            return True

        return False

    def _on_orbit_scroll(self, _c, _dx, dy, _x, _y) -> bool:
        items = self.model.orbit.current_items(self.model.tree)
        if not items:
            return False
        delta = -1 if dy > 0 else 1
        self._orbit_hover(orbit.rotate(self.model.orbit.hover, len(items), delta))
        return True

    def _on_orbit_right_click(self, _c, n_press, _x, _y) -> None:
        if n_press != 1:
            return
        if self.model.orbit.back():
            self.model.anim.leave_subring()
            self._pump_orbit()
        else:
            self.hide_all()

    def _orbit_activate(self) -> None:
        model = self.model
        item = model.current_item()
        if item is None:
            return
        if item.is_folder:
            index = model.orbit.hover
            if index is not None and model.orbit.enter(index, item):
                model.anim.enter_subring()
                self._pump_orbit()
            return
        target = orbit.resolve_target(item)
        if target:
            subprocess.Popen(target, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        self.hide_all()

    def _orbit_hover(self, index: Optional[int]) -> None:
        self.model.orbit.hover = index
        self.model.anim.set_hover(index)
        self._pump_orbit()

    def _on_query_changed(self, entry) -> None:
        self.model.query = entry.get_text()
        self._refresh_panel()

    def _on_entry_activate(self, _entry) -> None:
        model = self.model
        if model.query:
            url = orbit.search_url(model.query, model.engines,
                                   model.search_meta.get("default_engine", ""))
            if url:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
                self.hide_all()
            return
        kind, ident = model.activate_launcher_row(0)
        if kind == "folder":
            self._refresh_panel()
        elif kind == "app":
            for app in apps.search(model.query, limit=8):
                if app.id == ident:
                    cmd = app.command
                    if cmd:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, start_new_session=True)
                    break
            self.hide_all()

    def _refresh_panel(self) -> None:
        Gtk = self._Gtk
        while True:
            child = self._panel_list.get_first_child()
            if child is None:
                break
            self._panel_list.remove(child)
        self._rows = []

        panel = self.model.visible_panel()
        if panel == "wallpaper":
            self._build_wallpaper_rows()
            return
        if panel == "clipboard":
            self._build_clipboard_rows()
            return
        if panel == "session":
            self._build_session_rows()
            return
        if panel == "settings":
            self._build_settings_rows()
            return

        rows = self.model.launcher_rows()
        self._panel_title.set_text(
            f"{panel}  \u00b7  {self.model.orbit.depth}" if panel == "launcher" else str(panel))
        for index, (name, desc, kind) in enumerate(rows):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.add_css_class("nyx-row")
            if index == 0:
                row.add_css_class("sel")
            label = Gtk.Label(label=name)
            label.set_xalign(0.0)
            label.set_hexpand(True)
            row.append(label)
            if desc:
                sub = Gtk.Label(label=desc)
                sub.add_css_class("nyx-muted")
                row.append(sub)
            if kind == "folder":
                arrow = Gtk.Label(label="\u203A")
                row.append(arrow)
            gesture = Gtk.GestureClick()
            gesture.connect("released", lambda *_a, i=index: self._activate_row(i))
            row.add_controller(gesture)
            self._panel_list.append(row)
            self._rows.append(row)

    def _activate_row(self, index: int) -> None:
        model = self.model
        kind, ident = model.activate_launcher_row(index)
        if kind == "folder":
            if self._orbit_window.get_visible():
                model.anim.enter_subring()
                self._pump_orbit()
            self._refresh_panel()
            return
        if kind == "app":
            for app in apps.search(model.query, limit=8):
                if app.id == ident:
                    if app.command:
                        subprocess.Popen(app.command, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, start_new_session=True)
                    break
            self.hide_all()
            return
        if kind == "item":
            for item in model.orbit.current_items(model.tree):
                if item.id == ident:
                    target = orbit.resolve_target(item)
                    if target:
                        subprocess.Popen(target, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, start_new_session=True)
                    break
            self.hide_all()

    def _build_clipboard_rows(self) -> None:
        Gtk = self._Gtk
        self._panel_title.set_text(f"clipboard  \u00b7  {len(self.model.clipboard)}")
        if not self.model.clipboard:
            empty = Gtk.Label(label="cliphist not available")
            empty.add_css_class("nyx-muted")
            self._panel_list.append(empty)
            return
        for index, text in enumerate(self.model.clipboard[:20]):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            row.add_css_class("nyx-row")
            label = Gtk.Label(label=text)
            label.set_xalign(0.0)
            label.set_ellipsize(3)
            row.append(label)
            gesture = Gtk.GestureClick()
            gesture.connect("released", lambda *_a, t=text: self._copy_text(t))
            row.add_controller(gesture)
            self._panel_list.append(row)

    def _copy_text(self, text: str) -> None:
        if copy_to_clipboard(text):
            self.show_osd("copied")
        self.hide_all()

    def _build_session_rows(self) -> None:
        Gtk = self._Gtk
        self._panel_title.set_text("session")
        for action, label, glyph in SESSION_ACTIONS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.add_css_class("nyx-row")
            icon = Gtk.Label(label=glyph)
            row.append(icon)
            name = Gtk.Label(label=label)
            name.set_xalign(0.0)
            name.set_hexpand(True)
            row.append(name)
            gesture = Gtk.GestureClick()
            gesture.connect("released", lambda *_a, act=action: self._session_action(act))
            row.add_controller(gesture)
            self._panel_list.append(row)

    def _session_action(self, action: str) -> None:
        if action == "lock":
            if self._h_lock_available():
                self.hide_all()
                return
        ok = run_session_action(action)
        self.show_osd(f"{action}: {'ok' if ok else 'unavailable'}")
        if action in ("reboot", "shutdown", "logout", "suspend"):
            self.hide_all()

    def _h_lock_available(self) -> bool:
        import shutil

        for locker in ("swaylock", "gtklock", "hyprlock"):
            if shutil.which(locker):
                subprocess.Popen([locker, "-f"], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
                return True
        return False

    def _build_settings_rows(self) -> None:
        Gtk = self._Gtk
        state = self.model.state
        self._panel_title.set_text("settings")
        rows = [
            ("Dark mode", state.appearance.mode_effective() == "dark",
             lambda: self._toggle_theme()),
            ("Capsules", state.layout.capsule, lambda: self._toggle_layout("capsule")),
            ("Live wallpaper", state.appearance.live_wallpaper, lambda: None),
        ]
        for label, on, cb in rows:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.add_css_class("nyx-row")
            name = Gtk.Label(label=label)
            name.set_xalign(0.0)
            name.set_hexpand(True)
            row.append(name)
            mark = Gtk.Label(label="\u25CF" if on else "\u25CB")
            mark.add_css_class("nyx-accent")
            row.append(mark)
            gesture = Gtk.GestureClick()
            gesture.connect("released", lambda *_a, f=cb: f())
            row.add_controller(gesture)
            self._panel_list.append(row)

    def _toggle_theme(self) -> None:
        mode = self.model.state.appearance.mode_effective()
        new_mode = "light" if mode == "dark" else "dark"
        self.model.state.appearance.mode = new_mode
        S.save_state(self.model.state)
        S.write_palette(self.model.state)
        self.reload()
        self._refresh_panel()
        self.show_osd(f"theme: {new_mode}")

    def _toggle_layout(self, field: str) -> None:
        current = getattr(self.model.state.layout, field)
        setattr(self.model.state.layout, field, not current)
        S.save_state(self.model.state)
        self.reload()
        self._refresh_panel()

    def _build_wallpaper_rows(self) -> None:
        Gtk = self._Gtk
        files = self.model.wallpaper_files
        self._panel_title.set_text(f"wallpaper  \u00b7  {len(files)}")
        if not files:
            empty = Gtk.Label(label="no wallpapers found")
            empty.add_css_class("nyx-muted")
            self._panel_list.append(empty)
            return
        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(4)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        for path in files[:32]:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            image = Gtk.Image.new_from_file(str(path)) if W.is_image(path) else Gtk.Image.new_from_icon_name("video-x-generic")
            image.set_pixel_size(96)
            box.append(image)
            name = Gtk.Label(label=path.stem[:16])
            name.add_css_class("nyx-muted")
            box.append(name)
            gesture = Gtk.GestureClick()
            gesture.connect("released", lambda *_a, p=path: self._set_wallpaper(p))
            box.add_controller(gesture)
            grid.append(box)
        self._panel_list.append(grid)

    def _set_wallpaper(self, path: Path) -> None:
        from nyxuri_shell.actions import set_wallpaper

        ok, info = set_wallpaper(path)
        if ok:
            self.reload()
            self.show_osd(f"wallpaper \u00b7 {info}")
        else:
            self.show_osd(f"failed: {info}")
        self.hide_all()

    def _refresh_orbit(self) -> None:
        if self._orbit_area is not None:
            self._orbit_area.queue_draw()

    def _orbit_visible(self) -> bool:
        return self._orbit_window is not None and self._orbit_window.get_visible()

    def _reload_now(self) -> bool:
        self.state = S.load_state()
        self.model.state = self.state
        self.model.invalidate()
        try:
            self._provider.load_from_data(build_css(self.state).encode("utf-8"))
        except Exception:
            pass
        return False

    def reload(self) -> None:
        self._GLib.idle_add(self._reload_now)

    def idle_add(self, action) -> None:
        self._GLib.idle_add(action)

    def _refresh(self) -> bool:
        for name, label in self._labels.items():
            if name == "clock":
                continue
            try:
                text = self.model.text_for(name)
                if label.get_text() != text:
                    label.set_text(text)
            except Exception:
                pass
        return True

    def _refresh_clock(self) -> bool:
        label = self._labels.get("clock")
        if label is not None:
            try:
                text = self.model.clock_text()
                if label.get_text() != text:
                    label.set_text(text)
            except Exception:
                pass
        return True

    def toggle_panel(self, panel: str) -> bool:
        visible = self.model.toggle_panel(panel)
        self._apply_panel(panel, visible)
        return visible

    def _apply_panel(self, panel: str, visible: bool) -> bool:
        if not visible:
            self._panel_window.set_visible(False)
            return False
        if self._orbit_visible():
            self.close_radial()
        self._refresh_panel()
        self._panel_window.set_visible(True)
        self._panel_window.present()
        if panel not in ("wallpaper", "clipboard", "session", "settings"):
            self._panel_entry.grab_focus()
        return False

    def show_radial(self) -> bool:
        self.model.orbit.hover = None
        self.model.anim.show()
        self._orbit_window.set_visible(True)
        self._orbit_window.present()
        self._pump_orbit()
        return True

    def close_radial(self) -> bool:
        self.model.orbit.hover = None
        self.model.orbit.stack.clear()
        self.model.orbit.depth = 0
        self.model.anim.reset()
        self._stop_orbit()
        if self._orbit_window is not None:
            self._orbit_window.set_visible(False)
        return True

    def toggle_radial(self) -> bool:
        if self._orbit_visible():
            return self.close_radial()
        return self.show_radial()

    def hide_all(self) -> None:
        for name in PANELS:
            self.model.panel_visibility[name] = False
        if self._panel_window is not None:
            self._panel_window.set_visible(False)
        if self._osd_window is not None:
            self._osd_window.set_visible(False)
        self.model.flick.end()
        if self.model.anim.open:
            self.model.anim.hide()
            self._pump_orbit()
        elif self._orbit_window is not None:
            self._orbit_window.set_visible(False)
            self.model.anim.reset()

    def show_osd(self, text: str) -> None:
        self._GLib.idle_add(self._show_osd_now, text)

    def _show_osd_now(self, text: str) -> bool:
        if self._osd_window is None:
            return False
        self._osd_label.set_text(text)
        self._osd_window.set_visible(True)
        self._GLib.timeout_add(self.state.osd.timeout_ms, self._hide_osd)
        return False

    def _hide_osd(self) -> bool:
        if self._osd_window is not None:
            self._osd_window.set_visible(False)
        return False

    def show_wallpaper_picker(self) -> bool:
        self.toggle_panel("wallpaper")
        return True

    def run(self) -> int:
        self._GLib.timeout_add(POLL_MS, self._refresh)
        self._GLib.timeout_add(CLOCK_MS, self._refresh_clock)
        self._loop = self._GLib.MainLoop()
        self._loop_running = True
        try:
            self._loop.run()
        finally:
            self._loop_running = False
        return 0

    def quit(self) -> None:
        self._stop_orbit()
        if self._loop_running and self._loop is not None:
            self._loop.quit()
        for win in (self._panel_window, self._bar_window, self._orbit_window, self._osd_window):
            if win is not None:
                try:
                    win.set_visible(False)
                    win.destroy()
                except Exception:
                    pass


def _self_check() -> List[str]:
    problems: List[str] = []

    state = S.ShellState()
    css = build_css(state)
    for token in (".nyx-bar", ".nyx-panel", ".nyx-row", ".nyx-osd", "alpha("):
        if token not in css:
            problems.append(f"css missing {token}")

    light = S.ShellState()
    light.appearance.mode = "light"
    if build_css(light) == css:
        problems.append("light css identical")

    model = Model(state)
    if model.any_panel_visible():
        problems.append("panel visible by default")
    model.toggle_panel("launcher")
    if model.visible_panel() != "launcher":
        problems.append("launcher did not open")
    model.toggle_panel("wallpaper")
    if model.visible_panel() != "wallpaper":
        problems.append("panels not exclusive")
    model.toggle_panel("wallpaper")
    if model.any_panel_visible():
        problems.append("panel did not close")
    model.toggle_panel("bogus")
    if model.visible_panel() != "launcher":
        problems.append("bogus panel not falling back")

    for name in ("launcher", "workspaces", "clock", "sysmon", "volume", "battery", "session"):
        if not isinstance(model.text_for(name), str):
            problems.append(f"text_for({name}) not str")

    rows = model.launcher_rows()
    if not rows:
        problems.append("launcher has no rows")

    kind, _ident = model.activate_launcher_row(999)
    if kind != "none":
        problems.append("out-of-range row not rejected")

    for name in ("launcher", "workspaces", "clock", "sysmon",
                 "volume", "battery", "notifications", "session"):
        if not isinstance(model.text_for(name), str):
            problems.append(f"text_for({name}) not str")

    if not isinstance(notification_count(), int):
        problems.append("notification_count not int")
    if not isinstance(run_session_action("nonexistent-action"), bool):
        problems.append("run_session_action not bool")

    probe = Model(S.ShellState())
    if not probe.click_bar("launcher"):
        problems.append("bar click on launcher not consumed")
    if probe.visible_panel() != "launcher":
        problems.append("bar click did not open launcher")
    probe.toggle_panel("launcher")
    if probe.any_panel_visible():
        problems.append("bar click left a panel open")
    if probe.click_bar("nope"):
        problems.append("unknown bar capsule consumed click")

    if not isinstance(model.notifications_pending(), bool):
        problems.append("notifications_pending not bool")

    return problems


if __name__ == "__main__":
    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)
    print("ok")
