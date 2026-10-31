"""为 Nyxuri Shell 源码工具解析 XDG 路径与 Shell 专属目录覆盖。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NyxuriPaths:
    home: Path
    config_home: Path
    data_home: Path
    state_home: Path
    cache_home: Path
    runtime_home: Path

    @classmethod
    def from_environment(cls) -> "NyxuriPaths":
        """先解析 XDG 根目录，再应用 Shell 覆盖；空 XDG 值使用默认位置。"""
        home = Path(os.environ.get("HOME", str(Path.home())))
        config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share")
        state = Path(os.environ.get("XDG_STATE_HOME") or home / ".local/state")
        cache = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache")
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or cache / "nyxuri/runtime")
        return cls(
            home=home,
            config_home=Path(os.environ.get("NYXURI_SHELL_CONFIG_HOME", config / "nyxuri")),
            data_home=Path(os.environ.get("NYXURI_SHELL_DATA_HOME", data / "nyxuri")),
            state_home=Path(os.environ.get("NYXURI_SHELL_STATE_HOME", state / "nyxuri")),
            cache_home=Path(os.environ.get("NYXURI_SHELL_CACHE_HOME", cache / "nyxuri")),
            runtime_home=Path(os.environ.get("NYXURI_SHELL_RUNTIME_HOME", runtime / "nyxuri")),
        )


__all__ = ["NyxuriPaths"]
