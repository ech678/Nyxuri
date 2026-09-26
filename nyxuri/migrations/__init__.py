"""Linear, idempotent cleanup migrations for managed user state."""

import json
from pathlib import Path

from nyxuri.core import get_env

MIGRATION_LEVEL = 2
# Deprecated paths cleaned during linear migration.
TOMBSTONES: tuple[str, ...] = (
    ".config/fish/completions/nyxniri.fish",
    ".config/fish/conf.d/nyxniri-path.fish",
    ".config/noctalia/templates/nyxniri-palette.toml",
)

def _ledger_path() -> Path:
    return get_env().state_dir / "state.json"

def _read() -> dict:
    try:
        value = json.loads(_ledger_path().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}

def run() -> bool:
    env = get_env()
    ledger = _read()
    if int(ledger.get("migration_level", 0) or 0) >= MIGRATION_LEVEL:
        return True
    for relative in TOMBSTONES:
        target = env.home / relative
        try:
            target.resolve().relative_to(env.home.resolve())
        except ValueError:
            return False
        try:
            if target.is_symlink() or target.is_file():
                target.unlink()
        except OSError:
            return False
    ledger["migration_level"] = MIGRATION_LEVEL
    path = _ledger_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True
