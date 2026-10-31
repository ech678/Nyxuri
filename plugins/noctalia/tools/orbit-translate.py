#!/usr/bin/env python3
"""Capture the current Wayland selection and show the Orbit translation panel."""

from __future__ import annotations

import argparse
import shutil
import sys

from orbit_translate.capture import CaptureError, capture_primary
from orbit_translate.config import ConfigError, default_config, load_config


def check_dependencies() -> int:
    """Check the runtime pieces without opening a GTK window."""

    missing = [command for command in ("wl-paste", "niri") if shutil.which(command) is None]
    if missing:
        print("缺少运行依赖: " + ", ".join(missing), file=sys.stderr)
        return 1

    try:
        import gi

        gi.require_version("Gdk", "3.0")
        gi.require_version("Gtk", "3.0")
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import Gdk, Gtk, GtkLayerShell  # noqa: F401
    except ImportError:
        print("缺少 Python GTK 绑定: gi / PyGObject", file=sys.stderr)
        return 1
    except (ValueError, gi.RepositoryError):
        print("缺少 GTK3 / GtkLayerShell 运行时", file=sys.stderr)
        return 1

    print("依赖检查通过")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orbit-translate.py",
        description="Capture and translate the current Wayland selection.",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--settings",
        action="store_true",
        help="open the terminal channel settings before capture or GTK starts",
    )
    modes.add_argument(
        "--check-deps",
        action="store_true",
        help="check runtime dependencies without opening a window",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="settings configuration file (only valid with --settings)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.config and not args.settings:
        parser.error("--config is only valid with --settings")

    if args.check_deps:
        return check_dependencies()

    if args.settings:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print("--settings requires an interactive terminal (TTY).", file=sys.stderr)
            return 2
        from orbit_translate.tui import run_settings_tui

        return run_settings_tui(args.config)

    try:
        config = load_config()
    except ConfigError as exc:
        from orbit_translate.ui import show_message

        show_message(default_config(), f"配置错误\n{exc}")
        return 1

    if not config.capture_primary:
        from orbit_translate.ui import show_message

        show_message(config, "已关闭 Primary Selection 捕获")
        return 1

    try:
        selected_text = capture_primary(
            timeout_ms=config.capture_timeout_ms,
            max_chars=config.max_chars,
        )
    except CaptureError as exc:
        from orbit_translate.ui import show_message

        show_message(config, str(exc))
        return 1

    # Network requests do not need GTK: start them before importing it and
    # building the window, and buffer results until the window attaches.
    prestarted = None
    if any(provider.enabled for provider in config.providers):
        from orbit_translate.engine import ProviderEngine, ResultRelay

        relay = ResultRelay()
        engine = ProviderEngine(
            tuple(provider for provider in config.providers if provider.enabled),
            selected_text,
            config.source,
            config.target,
            config.request_timeout_ms,
            config.max_parallel,
            relay,
        ).start()
        prestarted = (engine, relay)

    from orbit_translate.ui import TranslationWindow

    window = TranslationWindow(config, selected_text, prestarted=prestarted)
    window.start()

    from gi.repository import Gtk

    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
