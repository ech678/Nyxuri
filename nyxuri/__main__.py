"""Entry point for python3 -m nyxuri."""

import os
import sys

_LIGHT_COMMANDS = {
    "pkg": "nyxuri.pkg.cli",
    "clean": "nyxuri.clean",
}


def _run_light(module_name: str, sub_args: list) -> int:
    if os.geteuid() == 0 or os.getuid() == 0:
        from nyxuri.i18n import msg
        print(msg("err_root_denied"), file=sys.stderr)
        return 1
    import importlib
    return importlib.import_module(module_name).main(sub_args)


def _run() -> int:
    args = sys.argv[1:]
    try:
        if args and args[0] in _LIGHT_COMMANDS:
            return _run_light(_LIGHT_COMMANDS[args[0]], args[1:])
        from nyxuri.cli import main
        main()
    except ModuleNotFoundError as e:
        # A missing nyxuri.* module means the engine tree is mixed or partial
        # (typically an update interrupted mid-checkout). Fail with one clear
        # line instead of a traceback; anything else is a real bug — re-raise.
        if not (getattr(e, "name", "") or "").startswith("nyxuri"):
            raise
        try:
            from nyxuri.i18n import msg
            text = msg("err_engine_incomplete")
        except Exception:
            text = ("[✗] 引擎文件不完整或更新中途被打断。重新运行 install.sh 即可恢复。\n"
                    "[✗] Engine files are incomplete or an update was interrupted. Rerun install.sh.")
        print(text, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_run())