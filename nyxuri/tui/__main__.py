"""M1 trial entry: `python3 -m nyxuri.tui` until the CLI hands off to it (M3)."""

import os
import sys


def _main() -> int:
    from nyxuri.system.env import acquire_lock, get_env, init_logger
    from nyxuri.system.i18n import msg

    if os.geteuid() == 0:
        print(msg("err_root_denied"), file=sys.stderr)
        return 1
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(msg("tui_needs_tty"), file=sys.stderr)
        return 2
    try:
        import textual  # noqa: F401
    except ImportError as exc:
        print(msg("tui_textual_missing", exc), file=sys.stderr)
        return 1
    acquire_lock()
    init_logger()
    get_env()
    from nyxuri.system import shell as bridge
    bridge.wire()
    from nyxuri.tui import main
    return main()


if __name__ == "__main__":
    sys.exit(_main())
