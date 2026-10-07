"""Shared harness for the Orbit Translate tool tests.

The tool ships as deployed files under configs/noctalia/tools (entry
orbit-translate.py + package orbit_translate/), not as a nyxuri subpackage, so
its directory goes on sys.path like test_wallpaper_scanner does. Test modules
re-export setUpModule/tearDownModule from here: each module runs inside one
TempEnv, so XDG config/cache lookups never reach the real ~/.config or ~/.cache.
"""

import sys
from pathlib import Path

from tests.utils import TempEnv

TOOLS = Path(__file__).resolve().parent.parent / "configs" / "noctalia" / "tools"
ENTRY = TOOLS / "orbit-translate.py"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

_env = None


def setUpModule():
    global _env
    _env = TempEnv()
    _env.__enter__()


def tearDownModule():
    global _env
    if _env is not None:
        _env.__exit__()
        _env = None
