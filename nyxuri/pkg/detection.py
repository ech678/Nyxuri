"""Dependency probes scoped to one inspection, never cached across installs."""

import os
import re
import shutil
import sys
from functools import cached_property
from pathlib import Path

from nyxuri.core import timed_run
from nyxuri.pkg.platform import current_platform, normalize_dpkg_package_names


class DependencyProbe:
    def _query(self, executable, args, timeout):
        if not shutil.which(executable):
            return ""
        result = timed_run([executable, *args], timeout, capture_output=True, text=True,
                           check=False, env={**os.environ, "LC_ALL": "C"})
        return result.stdout if result is not None and result.returncode == 0 else ""

    @cached_property
    def packages(self):
        if current_platform() == "ubuntu":
            output = self._query(
                "dpkg-query", ["-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n"], 30,
            )
            return normalize_dpkg_package_names(output)
        if current_platform() == "arch":
            return set(self._query("pacman", ["-Qq"], 30).split())
        return set()

    @cached_property
    def fonts(self):
        return self._query("fc-list", [":", "family"], 15).lower()

    @cached_property
    def font_families(self):
        """将 Fontconfig 实际列出的字族和别名拆成集合，用于指定字族的精确检测。"""
        # fc-list 每行可能同时列出多个逗号分隔的字族别名；不使用 fc-match，
        # 因为缺失目标字体时它仍会返回其他字体，不能作为安装成功的证据。
        return {family.strip() for line in self.fonts.splitlines()
                for family in line.split(",") if family.strip()}

    @cached_property
    def flatpaks(self):
        return set(self._query("flatpak", ["list", "--system", "--app", "--columns=application"], 15).split())

    def installed(self, name: str) -> bool:
        if name in self.packages:
            return True
        if name == "inotify-tools":
            return shutil.which("inotifywait") is not None
        runtime_imports = {
            "python-gobject": "import gi",
            "python3-gi": "import gi",
            "gtk-layer-shell": "import gi; gi.require_version('GtkLayerShell', '0.1')",
            "gir1.2-gtklayershell-0.1": "import gi; gi.require_version('GtkLayerShell', '0.1')",
            "python3-cairo": "import cairo",
        }
        if name in runtime_imports:
            code = runtime_imports[name]
            result = timed_run([sys.executable, "-c", code], 10, capture_output=True, check=False)
            return result is not None and result.returncode == 0
        if name in ("rime-ice", "jetbrains-mono-nerd-font",
                    "material-symbols-rounded-font", "material-symbols-outlined-font"):
            return self.manual_installed(name)
        patterns = {
            "ttf-jetbrains-mono": "jetbrains mono",
            "ttf-jetbrains-mono-nerd": r"jetbrains.*nerd",
            "jetbrains-mono-nerd-font": r"jetbrains.*nerd",
            "noto-fonts-cjk": r"noto.*cjk",
        }
        if name in patterns:
            return bool(re.search(patterns[name], self.fonts))
        return shutil.which(name) is not None

    def manual_installed(self, name: str) -> bool:
        """检查需要人工提供的字体或 Rime 方案文件，不安装或修改它们。"""
        if name == "mpvpaper":
            return shutil.which("mpvpaper") is not None
        if name == "jetbrains-mono-nerd-font":
            return bool(re.search(r"jetbrains.*nerd", self.fonts))
        symbol_families = {
            "material-symbols-rounded-font": "material symbols rounded",
            "material-symbols-outlined-font": "material symbols outlined",
        }
        if name in symbol_families:
            return symbol_families[name] in self.font_families
        if name == "rime-ice":
            roots = (
                Path("/usr/share/rime-data"),
                Path.home() / ".local/share/fcitx5/rime",
                Path.home() / ".config/fcitx/rime",
                Path.home() / ".config/ibus/rime",
            )
            # 只认 Rime Ice 的正式 schema 名，避免把 office 等无关文件当成已安装方案。
            return any((root / "rime_ice.schema.yaml").is_file() for root in roots)
        return False
