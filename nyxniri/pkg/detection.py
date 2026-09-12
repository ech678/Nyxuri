"""Dependency probes scoped to one inspection, never cached across installs."""

import os
import re
import shutil
import sys
from functools import cached_property

from nyxniri.core import timed_run


class DependencyProbe:
    def _query(self, executable, args, timeout):
        if not shutil.which(executable):
            return ""
        result = timed_run([executable, *args], timeout, capture_output=True, text=True,
                           check=False, env={**os.environ, "LC_ALL": "C"})
        return result.stdout if result is not None and result.returncode == 0 else ""

    @cached_property
    def packages(self):
        return set(self._query("pacman", ["-Qq"], 30).split())

    @cached_property
    def fonts(self):
        return self._query("fc-list", [":", "family"], 15).lower()

    @cached_property
    def flatpaks(self):
        return set(self._query("flatpak", ["list", "--system", "--app", "--columns=application"], 15).split())

    def installed(self, name: str) -> bool:
        if name in self.packages:
            return True
        if name == "inotify-tools":
            return shutil.which("inotifywait") is not None
        if name in ("python-gobject", "gtk-layer-shell"):
            code = "import gi" if name == "python-gobject" else "import gi; gi.require_version('GtkLayerShell', '0.1')"
            result = timed_run([sys.executable, "-c", code], 10, capture_output=True, check=False)
            return result is not None and result.returncode == 0
        patterns = {"ttf-jetbrains-mono": "jetbrains mono", "ttf-jetbrains-mono-nerd": r"jetbrains.*nerd",
                    "noto-fonts-cjk": r"noto.*cjk"}
        if name in patterns:
            return bool(re.search(patterns[name], self.fonts))
        return shutil.which(name) is not None
