"""Small XDG path helper used by source-tree utility scripts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClavisPaths:
    home: Path
    config_home: Path
    data_home: Path
    state_home: Path
    cache_home: Path
    runtime_home: Path

    @classmethod
    def from_environment(cls) -> "ClavisPaths":
        home = Path(os.environ.get("HOME", str(Path.home())))
        config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        data = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
        state = Path(os.environ.get("XDG_STATE_HOME", home / ".local/state"))
        cache = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR", cache / "clavis/runtime"))
        return cls(
            home=home,
            config_home=Path(os.environ.get("CLAVIS_CONFIG_HOME", config / "clavis")),
            data_home=Path(os.environ.get("CLAVIS_DATA_HOME", data / "clavis")),
            state_home=Path(os.environ.get("CLAVIS_STATE_HOME", state / "clavis")),
            cache_home=Path(os.environ.get("CLAVIS_CACHE_HOME", cache / "clavis")),
            runtime_home=Path(os.environ.get("CLAVIS_RUNTIME_HOME", runtime / "clavis")),
        )


__all__ = ["ClavisPaths"]
