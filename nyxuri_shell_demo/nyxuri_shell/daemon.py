import argparse
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from nyxuri_shell import ipc, state as S
from nyxuri_shell.actions import ACTION_EXIT_OK, set_wallpaper

PID_NAME = "shell.pid"
EXIT_OK = 0
EXIT_ALREADY_RUNNING = 4
EXIT_NO_UI = 5


def pid_path() -> Path:
    return ipc.socket_path(PID_NAME)


def _write_pid() -> bool:
    try:
        pid_path().parent.mkdir(parents=True, exist_ok=True)
        pid_path().write_text(str(os.getpid()), encoding="utf-8")
        return True
    except OSError:
        return False


def _clear_pid() -> None:
    try:
        pid_path().unlink(missing_ok=True)
    except OSError:
        pass


class Shell:
    def __init__(self, state: Optional[S.ShellState] = None):
        self.state = state or S.load_state()
        self.server = ipc.Server()
        self.ui: Any = None
        self.running = False
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.server.register("ping", self._h_ping)
        self.server.register("status", self._h_status)
        self.server.register("reload", self._h_reload)
        self.server.register("theme-toggle", self._h_theme_toggle)
        self.server.register("theme-mode-set", self._h_theme_mode)
        self.server.register("theme-mode-get", self._h_theme_get)
        self.server.register("panel-toggle", self._h_panel_toggle)
        self.server.register("settings-toggle", self._h_settings_toggle)
        self.server.register("session-lock", self._h_lock)
        self.server.register("wallpaper-set", self._h_wallpaper_set)
        self.server.register("wallpaper-get", self._h_wallpaper_get)
        self.server.register("wallpaper-random", self._h_wallpaper_random)
        self.server.register("wallpaper-picker", self._h_wallpaper_picker)
        self.server.register("radial-launcher", self._h_radial)
        self.server.register("sysinfo", self._h_sysinfo)
        self.server.register("volume", self._h_volume)
        self.server.register("brightness", self._h_brightness)
        self.server.register("clipboard-toggle", self._h_clipboard)

    def _h_ping(self, args: Dict[str, Any]) -> ipc.Response:
        return ipc.Response(True, {"pong": True, "pid": os.getpid()})

    def _h_status(self, args: Dict[str, Any]) -> ipc.Response:
        return ipc.Response(True, self.state.to_dict())

    def _h_reload(self, args: Dict[str, Any]) -> ipc.Response:
        self.state = S.load_state()
        S.write_palette(self.state)
        if self.ui is not None and hasattr(self.ui, "reload"):
            self.ui.reload()
        return ipc.Response(True, {"reloaded": True})

    def _h_theme_toggle(self, args: Dict[str, Any]) -> ipc.Response:
        current = self.state.appearance.mode_effective()
        target = "light" if current == "dark" else "dark"
        return self._apply_mode(target)

    def _h_theme_mode(self, args: Dict[str, Any]) -> ipc.Response:
        mode = str(args.get("mode") or "").strip()
        if mode not in ("dark", "light", "auto"):
            return ipc.Response(False, None, "mode must be dark, light or auto")
        return self._apply_mode(mode)

    def _h_theme_get(self, args: Dict[str, Any]) -> ipc.Response:
        return ipc.Response(True, {"mode": self.state.appearance.mode_effective()})

    def _apply_mode(self, mode: str) -> ipc.Response:
        self.state.appearance.mode = mode
        S.save_state(self.state)
        S.write_palette(self.state)
        if self.ui is not None and hasattr(self.ui, "reload"):
            self.ui.reload()
        return ipc.Response(True, {"mode": self.state.appearance.mode_effective()})

    def _h_panel_toggle(self, args: Dict[str, Any]) -> ipc.Response:
        panel = str(args.get("panel") or args.get("action") or "launcher")
        if self.ui is None or not hasattr(self.ui, "toggle_panel"):
            return ipc.Response(False, None, "ui unavailable")
        self._marshal(lambda: self.ui.toggle_panel(panel))
        return ipc.Response(True, {"panel": panel})

    def _h_settings_toggle(self, args: Dict[str, Any]) -> ipc.Response:
        if self.ui is None or not hasattr(self.ui, "toggle_panel"):
            return ipc.Response(False, None, "ui unavailable")
        self._marshal(lambda: self.ui.toggle_panel("settings"))
        return ipc.Response(True, {"panel": "settings", "visible": True})

    def _marshal(self, action) -> None:
        if self.ui is None:
            return
        idle = getattr(self.ui, "idle_add", None)
        if callable(idle):
            idle(action)
            return
        action()

    def _h_lock(self, args: Dict[str, Any]) -> ipc.Response:
        from nyxuri_shell.actions import _spawn

        for locker in ("swaylock", "gtklock", "hyprlock"):
            if _spawn([locker, "-f"]):
                return ipc.Response(True, {"locked": True, "locker": locker})
        return ipc.Response(False, None, "no screen locker available")

    def _h_wallpaper_set(self, args: Dict[str, Any]) -> ipc.Response:
        raw = str(args.get("path") or "")
        if not raw:
            return ipc.Response(False, None, "missing path")
        ok, info = set_wallpaper(Path(raw).expanduser())
        if not ok:
            return ipc.Response(False, None, info)
        self.state = S.load_state()
        if self.ui is not None and hasattr(self.ui, "reload"):
            self.ui.reload()
        return ipc.Response(True, {"source_color": info})

    def _h_wallpaper_get(self, args: Dict[str, Any]) -> ipc.Response:
        return ipc.Response(True, {
            "path": self.state.appearance.wallpaper,
            "live": self.state.appearance.live_wallpaper,
        })

    def _h_wallpaper_random(self, args: Dict[str, Any]) -> ipc.Response:
        from nyxuri_shell.actions import _random_wallpaper

        if _random_wallpaper():
            self.state = S.load_state()
            if self.ui is not None and hasattr(self.ui, "reload"):
                self.ui.reload()
            return ipc.Response(True, {"path": self.state.appearance.wallpaper})
        return ipc.Response(False, None, "no wallpapers available")

    def _h_wallpaper_picker(self, args: Dict[str, Any]) -> ipc.Response:
        if self.ui is not None and hasattr(self.ui, "show_wallpaper_picker"):
            self._marshal(lambda: self.ui.show_wallpaper_picker())
            return ipc.Response(True, {"opened": True})
        from nyxuri_shell.actions import _run_tool

        return ipc.Response(True, {"opened": _run_tool("wallpaper-picker.py")})

    def _h_radial(self, args: Dict[str, Any]) -> ipc.Response:
        if self.ui is not None and hasattr(self.ui, "toggle_radial"):
            self._marshal(self.ui.toggle_radial)
            return ipc.Response(True, {"toggled": True})
        if self.ui is not None and hasattr(self.ui, "show_radial"):
            self._marshal(self.ui.show_radial)
            return ipc.Response(True, {"opened": True})
        from nyxuri_shell.actions import _run_tool

        return ipc.Response(True, {"opened": _run_tool("orbit-launcher.py")})

    def _h_clipboard(self, args: Dict[str, Any]) -> ipc.Response:
        if self.ui is None or not hasattr(self.ui, "toggle_panel"):
            return ipc.Response(False, None, "ui unavailable")
        self._marshal(lambda: self.ui.toggle_panel("clipboard"))
        return ipc.Response(True, {"opened": True})

    def _h_sysinfo(self, args: Dict[str, Any]) -> ipc.Response:
        from nyxuri_shell import sysinfo

        win = sysinfo.focused_window()
        volume = sysinfo.volume()
        battery = sysinfo.battery()
        return ipc.Response(True, {
            "workspaces": [
                {"idx": w.idx, "name": w.name, "focused": w.focused, "active": w.active}
                for w in sysinfo.workspaces()
            ],
            "window": {"title": win.title, "app_id": win.app_id} if win else None,
            "volume": {"percent": volume[0], "muted": volume[1]} if volume else None,
            "battery": {"percent": battery.percent, "charging": battery.charging} if battery else None,
            "backlight": sysinfo.backlight_percent(),
            "memory": sysinfo.memory_percent(),
        })

    def _h_volume(self, args: Dict[str, Any]) -> ipc.Response:
        from nyxuri_shell import sysinfo

        action = str(args.get("action") or "get")
        if action == "get":
            current = sysinfo.volume()
            return ipc.Response(True, {"percent": current[0], "muted": current[1]} if current else None)
        if action == "mute":
            muted = sysinfo.toggle_mute()
            if muted is None:
                return ipc.Response(False, None, "audio unavailable")
            self._osd("Muted" if muted else "Unmuted")
            return ipc.Response(True, {"muted": muted})
        if action in ("up", "down"):
            delta = int(args.get("step") or 5)
            percent = sysinfo.adjust_volume(delta if action == "up" else -delta)
            if percent is None:
                return ipc.Response(False, None, "audio unavailable")
            self._osd(f"Volume {percent}%")
            return ipc.Response(True, {"percent": percent})
        return ipc.Response(False, None, f"unknown volume action: {action}")

    def _h_brightness(self, args: Dict[str, Any]) -> ipc.Response:
        from nyxuri_shell import sysinfo

        action = str(args.get("action") or "get")
        if action == "get":
            return ipc.Response(True, {"percent": sysinfo.backlight_percent()})
        if action in ("up", "down"):
            delta = int(args.get("step") or 5)
            percent = sysinfo.adjust_backlight(delta if action == "up" else -delta)
            if percent is None:
                return ipc.Response(False, None, "backlight unavailable")
            self._osd(f"Brightness {percent}%")
            return ipc.Response(True, {"percent": percent})
        return ipc.Response(False, None, f"unknown brightness action: {action}")

    def _osd(self, text: str) -> None:
        if self.ui is not None and hasattr(self.ui, "show_osd"):
            try:
                self.ui.show_osd(text)
            except Exception:
                pass

    def start(self, with_ui: bool = True) -> bool:
        if with_ui:
            self.ui = _build_ui(self)
        if not self.server.start():
            return False
        _write_pid()
        self.running = True
        return True

    def run(self) -> int:
        if self.ui is None:
            while self.running:
                time.sleep(0.5)
            return EXIT_OK
        return int(self.ui.run() or EXIT_OK)

    def stop(self) -> None:
        self.running = False
        if self.ui is not None and hasattr(self.ui, "quit"):
            try:
                self.ui.quit()
            except Exception:
                pass
        self.server.stop()
        _clear_pid()


def _build_ui(shell: Shell):
    try:
        from nyxuri_shell.ui.gtk import GtkShell
    except Exception as exc:
        log_msg("WARN", f"GTK UI import failed: {type(exc).__name__}: {exc}")
        return None
    try:
        return GtkShell(shell)
    except Exception as exc:
        import traceback

        log_msg("ERROR", f"GTK UI construction failed: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return None


def _install_signal_handlers(shell: Shell) -> None:
    def handler(signum, frame):
        shell.running = False
        try:
            shell.stop()
        finally:
            sys.exit(EXIT_OK)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handler)
        except (ValueError, OSError):
            pass


def _self_check() -> List[str]:
    problems: List[str] = []

    shell = Shell()
    for command in ("ping", "status", "theme-mode-get", "wallpaper-get", "sysinfo",
                    "volume", "brightness"):
        response = shell.server.dispatch(command, {})
        if not response.ok:
            problems.append(f"{command} failed: {response.error}")

    info = shell.server.dispatch("sysinfo", {}).data
    for key in ("workspaces", "window", "volume", "battery", "backlight", "memory"):
        if key not in info:
            problems.append(f"sysinfo missing key {key}")

    if shell.server.dispatch("volume", {"action": "bogus"}).ok:
        problems.append("bogus volume action accepted")
    if shell.server.dispatch("brightness", {"action": "bogus"}).ok:
        problems.append("bogus brightness action accepted")

    bad_mode = shell.server.dispatch("theme-mode-set", {"mode": "chartreuse"})
    if bad_mode.ok:
        problems.append("invalid mode accepted")

    for command in ("panel-toggle", "settings-toggle"):
        response = shell.server.dispatch(command, {})
        if response.ok:
            problems.append(f"{command} should fail without ui")
        elif "ui unavailable" not in response.error:
            problems.append(f"{command} wrong error: {response.error}")

    for command in ("wallpaper-picker", "radial-launcher"):
        response = shell.server.dispatch(command, {})
        if not response.ok:
            problems.append(f"{command} should always succeed: {response.error}")

    got = shell.server.dispatch("theme-mode-get", {})
    if got.data.get("mode") not in ("dark", "light"):
        problems.append("mode not resolved")

    return problems


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="nyxuri-shell", add_help=True)
    parser.add_argument("--no-ui", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--action", "-a", dest="action", default="")
    args, extra = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    if args.self_check:
        issues = _self_check()
        if issues:
            print("self-check failed:")
            for p in issues:
                print("  -", p)
            return 1
        print("ok")
        return EXIT_OK

    from nyxuri_shell.actions import main as action_main

    passthrough = ("--status", "--list", "--set-wallpaper", "--help", "-h")
    if args.action:
        return action_main([args.action, *extra])
    if any(tok in passthrough for tok in extra):
        return action_main([*extra])

    if ipc.is_running():
        print("nyxuri-shell is already running", file=sys.stderr)
        return EXIT_ALREADY_RUNNING

    if not args.no_ui and os.environ.get("NYXURI_SHELL_REEXEC") != "1":
        try:
            from nyxuri_shell.ui import gtk as _gtk

            preload = _gtk.ensure_link_order()
            if preload:
                _gtk.reexec_with_preload(preload)
        except Exception:
            pass

    shell = Shell()
    _install_signal_handlers(shell)
    if not shell.start(with_ui=not args.no_ui):
        print("failed to start nyxuri-shell", file=sys.stderr)
        return 1

    if not args.no_ui and shell.ui is None:
        print("gtk ui unavailable, running headless", file=sys.stderr)

    try:
        return shell.run()
    finally:
        shell.stop()


if __name__ == "__main__":
    sys.exit(main())
