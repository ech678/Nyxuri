"""Small atomic JSON ledger for runtime selections and module state."""

import json
import os
from pathlib import Path
from typing import Any

from nyxuri.core import get_env


def ledger_path() -> Path:
    return get_env().state_dir / "state.json"


def read_ledger() -> dict[str, Any]:
    try:
        data = json.loads(ledger_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def update_ledger(**changes: Any) -> dict[str, Any]:
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = read_ledger()
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return data


def active_shell(default: str = "noctalia") -> str:
    value = read_ledger().get("active_shell", default)
    return value if value in {"noctalia", "custom"} else default


def custom_shell_bin() -> str:
    val = read_ledger().get("custom_shell_bin", "")
    return str(val) if isinstance(val, str) else ""


def set_shell(shell_name: str, bin_path: str | None = None) -> dict[str, Any]:
    if shell_name not in {"noctalia", "custom"}:
        raise ValueError(f"Invalid shell: {shell_name} (must be 'noctalia' or 'custom')")
    changes: dict[str, Any] = {"active_shell": shell_name}
    if bin_path is not None:
        changes["custom_shell_bin"] = bin_path
    return update_ledger(**changes)
