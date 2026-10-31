"""PluginLedger — the state domain's single entry (plugin-model.md §2).

The only kernel module that reads or writes ``state.json``. Generic
key/value selections (active shell, migration level) and plugin records
share one atomic write path: flock, merge, tmp file, ``os.replace``.

Plugin records live under the top-level ``plugins`` key, keyed by plugin id.
Each record carries exactly five frozen fields (plugin-model.md §3):
``state`` / ``form`` / ``files`` / ``vault`` / ``updated``. Kernel code must
not invent a sixth. ``form`` is the plugin's whole-config axis choice; slot
axis choices live under the top-level ``forms`` key (``{plugin: {slot:
value}}``).
"""

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nyxuri.core import get_env

PLUGIN_STATES = ("enabled", "disabled")

# Top-level key holding plugin records.
PLUGINS_KEY = "plugins"

# Top-level key holding slot-axis choices: {plugin: {slot: value}}.
FORMS_KEY = "forms"
_FORM_FIELD = "form"

# --- generic ledger primitives -------------------------------------------


def ledger_path() -> Path:
    return get_env().state_dir / "state.json"


def _read_raw() -> dict[str, Any]:
    try:
        data = json.loads(ledger_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


@contextmanager
def _ledger_lock(path: Path):
    """Hold the advisory flock; degrades to no-op when unopenable."""
    lock_handle = None
    try:
        lock_handle = open(path.with_name(f".{path.name}.lock"), "a+")
        fcntl.flock(lock_handle, fcntl.LOCK_EX)
    except OSError:
        if lock_handle is not None:
            lock_handle.close()
        lock_handle = None
    try:
        yield
    finally:
        if lock_handle is not None:
            lock_handle.close()


def _write_locked(path: Path, data: dict[str, Any]) -> None:
    """Tmp file + ``os.replace``; caller must already hold the flock."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_ledger() -> dict[str, Any]:
    """Read state.json (single-truth ledger)."""
    return _read_raw()


def update_ledger(**changes: Any) -> dict[str, Any]:
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _ledger_lock(path):
        data = _read_raw()
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
        _write_locked(path, data)
    return data


# --- shell selection ------------------------------------------------------


def active_shell(default: str = "noctalia") -> str:
    value = read_ledger().get("active_shell", default)
    if not isinstance(value, str):
        return default
    if value in {"nyxuri-shell", "nyxuri", "custom"}:
        return "nyxuri-shell"
    if value == "noctalia":
        return "noctalia"
    return default


def custom_shell_bin() -> str:
    ledger = read_ledger()
    val = ledger.get("custom_shell_bin") or ledger.get("nyxuri_shell_bin", "")
    return str(val) if isinstance(val, str) else ""


def nyxuri_shell_bin() -> str:
    return custom_shell_bin()


def set_shell(shell_name: str, bin_path: str | None = None) -> dict[str, Any]:
    s = str(shell_name).strip().lower()
    if s in {"nyxuri-shell", "nyxuri", "custom"}:
        canonical = "nyxuri-shell"
    elif s == "noctalia":
        canonical = "noctalia"
    else:
        raise ValueError(f"Invalid shell: {shell_name} (must be 'noctalia' or 'nyxuri-shell')")
    changes: dict[str, Any] = {"active_shell": canonical}
    if bin_path is not None:
        changes["custom_shell_bin"] = bin_path
    return update_ledger(**changes)


# --- plugin records (KM0 frozen five-field shape) ---------------------------


def all_plugins() -> dict[str, dict[str, Any]]:
    """Every plugin record in the ledger, keyed by plugin id."""
    plugins = read_ledger().get(PLUGINS_KEY)
    if not isinstance(plugins, dict):
        return {}
    return {uid: dict(rec) for uid, rec in plugins.items() if isinstance(rec, dict)}


def get_plugin(plugin_id: str) -> dict[str, Any] | None:
    """One plugin record, or None when the plugin was never switched."""
    return all_plugins().get(plugin_id)


def set_plugin(
    plugin_id: str,
    *,
    state: str,
    form: str = "default",
    files: dict[str, str] | None = None,
    vault: str | None = None,
    updated: str | None = None,
) -> dict[str, Any]:
    """Upsert one plugin record, enforcing the frozen five-field shape.

    ``state``: ``enabled`` / ``disabled`` (the only switch axis).
    ``form``: whole-config axis choice. ``files``: ``{relpath: sha256}``
    snapshot of managed files. ``vault``: archive location of the user's
    custom files (null is honest when nothing was ever archived — a
    ``use``-only record). ``updated``: ISO timestamp, defaulted to now (UTC).
    """
    if state not in PLUGIN_STATES:
        raise ValueError(f"invalid plugin state '{state}' (must be 'enabled' or 'disabled')")
    if not isinstance(form, str) or not form:
        raise ValueError("form must be a non-empty string")
    if files is None:
        files = {}
    if not isinstance(files, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in files.items()
    ):
        raise ValueError("files must map relative paths to hash strings")
    if vault is not None and not isinstance(vault, str):
        raise ValueError("vault must be an archive path string or None")
    if updated is None:
        updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record: dict[str, Any] = {
        "state": state,
        "form": form,
        "files": dict(files),
        "vault": vault,
        "updated": updated,
    }
    data = update_ledger(**{PLUGINS_KEY: {plugin_id: record}})
    return dict(data[PLUGINS_KEY][plugin_id])


# --- slot-axis choices (R0-2 杀词并轨) ---------------------------------------


def get_form_slots(plugin_id: str) -> dict[str, str]:
    """The plugin's recorded slot-axis choices, ``{slot: value}``."""
    forms = read_ledger().get(FORMS_KEY)
    if not isinstance(forms, dict):
        return {}
    slot_map = forms.get(plugin_id)
    if not isinstance(slot_map, dict):
        return {}
    return {k: v for k, v in slot_map.items() if isinstance(k, str) and isinstance(v, str)}


def set_form_slot(plugin_id: str, slot: str, value: str) -> None:
    """Record one slot-axis choice under the top-level ``forms`` key."""
    if not slot or not isinstance(slot, str):
        raise ValueError("slot must be a non-empty string")
    if not value or not isinstance(value, str):
        raise ValueError("value must be a non-empty string")
    slot_map = get_form_slots(plugin_id)
    slot_map[slot] = value
    update_ledger(**{FORMS_KEY: {plugin_id: slot_map}})
