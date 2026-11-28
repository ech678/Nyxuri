from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List

__all__ = ["snapshot_state", "plugin_rows", "doctor_rows", "shell_state", "config_state", "snapshot_rows", "activity_rows", "compositor_state"]


def _home() -> pathlib.Path:
    return pathlib.Path.home()


def _load_toml(path: pathlib.Path) -> Dict[str, Any]:
    try:
        import tomllib

        with path.open("rb") as handle:
            return tomllib.load(handle)
    except Exception:
        return {}


def _load_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _ledger() -> Dict[str, Any]:
    data = _load_json(_home() / ".local" / "state" / "nyxuri" / "state.json")
    return data if isinstance(data, dict) else {}


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def config_state() -> Dict[str, Any]:
    path = _home() / ".config" / "nyxuri" / "config.toml"
    size = path.stat().st_size if path.is_file() else 0
    data = _load_toml(path)
    theme = data.get("theme") if isinstance(data.get("theme"), dict) else {}
    wallpaper = data.get("wallpaper") if isinstance(data.get("wallpaper"), dict) else {}
    folder = pathlib.Path(str(wallpaper.get("folder", "")).replace("~", str(_home())))
    wallpapers = 0
    try:
        if folder.is_dir():
            wallpapers = sum(1 for item in folder.iterdir() if item.is_file())
    except OSError:
        wallpapers = 0
    preferences = data.get("preferences") if isinstance(data.get("preferences"), dict) else {}
    return {
        "path": path,
        "exists": path.is_file(),
        "size": size,
        "schema": data.get("configVersion", data.get("schemaVersion", "?")),
        "theme": str(theme.get("mode", "dark")),
        "wallpaper": str(wallpaper.get("folder", "")),
        "wallpapers": wallpapers,
        "language": str(preferences.get("language", "en_US")),
        "raw": data,
    }


COMPOSITORS = ("niri", "sway", "Hyprland", "hyprland", "mango", "weston")


def _running_process_names() -> List[str]:
    names: List[str] = []
    proc = pathlib.Path("/proc")
    try:
        entries = list(proc.iterdir())
    except OSError:
        return names
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        names.append(comm)
    return names


def compositor_state() -> Dict[str, Any]:
    running = [name for name in _running_process_names() if name in COMPOSITORS]
    installed = [name for name in COMPOSITORS if shutil_which(name)]
    return {
        "running": running[0] if running else "",
        "installed": installed,
    }


def shutil_which(name: str) -> str:
    import shutil

    return shutil.which(name) or ""


def activity_rows(limit: int = 5) -> List[Dict[str, str]]:
    ledger = _ledger()
    plugins = ledger.get("plugins") if isinstance(ledger.get("plugins"), dict) else {}
    entries: List[Dict[str, str]] = []
    for plugin_id, record in plugins.items():
        if not isinstance(record, dict):
            continue
        stamp = str(record.get("updated", ""))
        if not stamp:
            continue
        state = str(record.get("state", ""))
        entries.append({
            "stamp": stamp[11:16] if len(stamp) >= 16 else stamp,
            "action": "unit switch",
            "detail": f"{plugin_id.replace('shell.', '')} → {state}",
        })
    entries.sort(key=lambda item: item["stamp"], reverse=True)
    return entries[:limit]


def shell_state() -> Dict[str, Any]:
    try:
        from nyxuri.state.store import active_shell
    except Exception:
        active_shell = lambda: "unknown"
    try:
        from nyxuri.system.shell import probe_running_shells, resolve_custom_bin
    except Exception:
        probe_running_shells = lambda: []
        resolve_custom_bin = lambda: ""
    try:
        running = probe_running_shells()
    except Exception:
        running = []
    binary = ""
    try:
        binary = resolve_custom_bin()
    except Exception:
        binary = ""
    try:
        active = active_shell()
    except Exception:
        active = "unknown"
    return {
        "active": active or "unknown",
        "running": [name for name, _pid in running],
        "binary": binary,
        "binary_exists": bool(binary) and pathlib.Path(binary).is_file(),
        "compositor": compositor_state(),
    }


def plugin_rows() -> List[Dict[str, str]]:
    from nyxuri.deploy import catalog

    ledger = _ledger().get("plugins", {})
    rows: List[Dict[str, str]] = []
    try:
        ids = sorted(catalog.plugin_ids())
    except Exception:
        ids = []
    for plugin_id in ids:
        try:
            manifest = catalog.load_plugin(plugin_id)
            kinds = ",".join(getattr(manifest, "kinds", []) or [])
            label = getattr(manifest, "label", plugin_id)
        except Exception:
            kinds = "?"
            label = plugin_id
        record = ledger.get(plugin_id) if isinstance(ledger, dict) else {}
        state = "disabled"
        form = "-"
        if isinstance(record, dict):
            state = str(record.get("state", "disabled"))
            form = str(record.get("form", "default"))
        rows.append({
            "id": plugin_id,
            "label": str(label),
            "kinds": kinds,
            "state": state,
            "form": form,
        })
    return rows


def snapshot_rows() -> List[Dict[str, str]]:
    try:
        from nyxuri.state.backup import get_all_backups

        backups = get_all_backups()
    except Exception:
        backups = []
    rows: List[Dict[str, str]] = []
    for index, path in enumerate(backups[:12], 1):
        note = ""
        try:
            note = (path / "note.txt").read_text(encoding="utf-8").strip()
        except Exception:
            note = ""
        files = 0
        try:
            files = sum(1 for item in path.rglob("*") if item.is_file())
        except Exception:
            files = 0
        rows.append({
            "index": str(index),
            "name": path.name,
            "note": note or "no note",
            "files": str(files),
            "path": str(path),
        })
    return rows


def doctor_rows() -> List[Dict[str, str]]:
    checks: List[Dict[str, str]] = []

    def add(category: str, name: str, status: str, detail: str) -> None:
        checks.append({"category": category, "name": name, "status": status, "detail": detail})

    repo = _repo_root()
    shell = shell_state()
    config = config_state()
    ledger = _ledger()

    compositors = ("niri", "sway", "hyprland", "mango", "noctalia")
    found = [name for name in compositors if (pathlib.Path("/usr/bin") / name).is_file()]
    if found:
        add("compositor", "session", "ok", ", ".join(found))
    else:
        add("compositor", "session", "warn", "no supported compositor on PATH")

    if shell["binary"] and shell["binary_exists"]:
        add("runtime", "nyxuri-shell", "ok", shell["binary"])
    else:
        add("runtime", "nyxuri-shell", "bad", "binary not resolvable")

    if shell["running"]:
        add("runtime", "instances", "ok", ", ".join(shell["running"]))
    else:
        add("runtime", "instances", "warn", "shell not running")

    if config["exists"]:
        add("config", "config.toml", "ok", f"{config['size']} bytes, schema {config['schema']}")
    else:
        add("config", "config.toml", "bad", "missing")

    if isinstance(ledger.get("plugins"), dict) and ledger.get("plugins"):
        enabled = sum(1 for record in ledger["plugins"].values() if str(record.get("state")) == "enabled")
        add("config", "ledger", "ok", f"{enabled} units enabled")
    else:
        add("config", "ledger", "warn", "state.json missing")

    notifications = _home() / ".local" / "state" / "nyxuri" / "notifications" / "notifications.json"
    if notifications.is_file() and _load_json(notifications) is not None:
        add("data", "notifications", "ok", "readable")
    else:
        add("data", "notifications", "warn", "not readable")

    wallpapers = _home() / "Pictures" / "Wallpapers"
    if wallpapers.is_dir():
        count = sum(1 for item in wallpapers.iterdir() if item.is_file())
        add("data", "wallpapers", "ok" if count else "warn", f"{count} files")
    else:
        add("data", "wallpapers", "warn", str(wallpapers))

    scripts = repo / "nyxuri" / "data" / "scripts"
    add("assets", "gateway scripts", "ok" if scripts.is_dir() else "bad", str(scripts))

    return checks


def snapshot_state() -> Dict[str, Any]:
    return {
        "config": config_state(),
        "shell": shell_state(),
        "plugins": plugin_rows(),
        "snapshots": snapshot_rows(),
        "activity": activity_rows(),
    }
