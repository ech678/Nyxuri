"""StateStore — single entry point for persistent runtime state (state.json).

Reads and updates ~/.local/state/nyxuri/state.json with atomic flock protection.
Manages enabled plugin records, form slots, active shell choice, and third-party origins.
"""

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nyxuri.system.env import get_env

PLUGIN_STATES = ("enabled", "disabled")

PLUGINS_KEY = "plugins"
FORMS_KEY = "forms"
SOURCES_KEY = "sources"
_FORM_FIELD = "form"


def store_path() -> Path:
    return get_env().state_dir / "state.json"


def _read_raw() -> dict[str, Any]:
    try:
        data = json.loads(store_path().read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        # Clean legacy ghost keys if present
        for legacy_key in ("modules", "shell_package"):
            data.pop(legacy_key, None)
        return data
    except (OSError, ValueError, TypeError):
        return {}


@contextmanager
def _store_lock(path: Path):
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
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_state() -> dict[str, Any]:
    """Read state.json (single truth for runtime state)."""
    return _read_raw()


def update_state(**changes: Any) -> dict[str, Any]:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _store_lock(path):
        data = _read_raw()
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
        _write_locked(path, data)
    return data


# --- Shell Selection ---


def active_shell(default: str = "noctalia") -> str:
    value = read_state().get("active_shell", default)
    if not isinstance(value, str):
        return default
    if value in {"nyxuri-shell", "nyxuri", "custom"}:
        return "nyxuri-shell"
    if value == "noctalia":
        return "noctalia"
    return default


def custom_shell_bin() -> str:
    state = read_state()
    val = state.get("custom_shell_bin") or state.get("nyxuri_shell_bin", "")
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
    return update_state(**changes)


# --- Plugin Records ---


def all_plugins() -> dict[str, dict[str, Any]]:
    """Every plugin record in the store, keyed by plugin id."""
    plugins = read_state().get(PLUGINS_KEY)
    if not isinstance(plugins, dict):
        return {}
    return {uid: dict(rec) for uid, rec in plugins.items() if isinstance(rec, dict)}


def get_plugin(plugin_id: str) -> dict[str, Any] | None:
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
    data = update_state(**{PLUGINS_KEY: {plugin_id: record}})
    return dict(data[PLUGINS_KEY][plugin_id])


# --- Form Slots ---


def get_form_slots(plugin_id: str) -> dict[str, str]:
    forms = read_state().get(FORMS_KEY)
    if not isinstance(forms, dict):
        return {}
    slot_map = forms.get(plugin_id)
    if not isinstance(slot_map, dict):
        return {}
    return {k: v for k, v in slot_map.items() if isinstance(k, str) and isinstance(v, str)}


def set_form_slot(plugin_id: str, slot: str, value: str) -> None:
    if not slot or not isinstance(slot, str):
        raise ValueError("slot must be a non-empty string")
    if not value or not isinstance(value, str):
        raise ValueError("value must be a non-empty string")
    slot_map = get_form_slots(plugin_id)
    slot_map[slot] = value
    update_state(**{FORMS_KEY: {plugin_id: slot_map}})


# --- Third-Party Plugin Sources ---


def get_source(plugin_id: str) -> dict[str, Any] | None:
    sources = read_state().get(SOURCES_KEY)
    if not isinstance(sources, dict):
        return None
    rec = sources.get(plugin_id)
    return dict(rec) if isinstance(rec, dict) else None


def set_source(plugin_id: str, *, url: str, ref: str, commit: str) -> dict[str, Any]:
    if not plugin_id or not isinstance(plugin_id, str):
        raise ValueError("plugin id must be a non-empty string")
    for field, val in (("url", url), ("ref", ref), ("commit", commit)):
        if not isinstance(val, str):
            raise ValueError(f"source {field} must be a string")
    existing = get_source(plugin_id) or {}
    rec = {
        "url": url,
        "ref": ref,
        "commit": commit,
        "added": existing.get("added")
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data = update_state(**{SOURCES_KEY: {plugin_id: rec}})
    return dict(data[SOURCES_KEY][plugin_id])


def forget_plugin(plugin_id: str) -> None:
    """Erase every trace of a third-party plugin from state."""
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _store_lock(path):
        data = _read_raw()
        changed = False
        for key in (PLUGINS_KEY, SOURCES_KEY, FORMS_KEY):
            section = data.get(key)
            if isinstance(section, dict) and plugin_id in section:
                section.pop(plugin_id)
                changed = True
        if changed:
            _write_locked(path, data)
