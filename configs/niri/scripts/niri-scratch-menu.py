#!/usr/bin/env python3
"""
NyxNiri Orbit Launcher (Legacy Compatibility Wrapper)
Forwards execution to the Noctalia companion tool.
"""

import sys
import os

CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
TARGET_SCRIPT = os.path.join(CONFIG_HOME, "noctalia", "tools", "orbit-launcher.py")

if __name__ == "__main__":
    if not os.path.isfile(TARGET_SCRIPT):
        raise SystemExit(f"Orbit tool is not deployed: {TARGET_SCRIPT}")
    os.execv(sys.executable, [sys.executable, TARGET_SCRIPT] + sys.argv[1:])
