"""Plugin manifests (``manifest.toml``) — the plugin model's self-description.

A ``configs/<plugin>/`` directory is Nyxuri's first-class plugin. By convention
it is self-describing: the directory name drives every default. A sibling
``manifest.toml`` overrides defaults only when the plugin is exceptional (niri
preserves ``monitor.kdl``; missioncenter's package is ``mission-center``).
**No manifest file = full defaults** (plugin-model.md §4: 只写例外).

A *present* manifest must be new-form (S0-2 protocol): it declares
``schemaVersion`` and speaks the closed vocabulary below. Retired keys and
missing ``schemaVersion`` fail loudly — no compat window, no read-only shim.
This parser and the shell PluginRegistry read the same file and enforce the
same checks (manifest-schema.md is the field authority).

Schema (``schemaVersion = 1``)::

    schemaVersion = 1              # required, exactly 1
    id = "kitty"                   # required, == <root prefix><directory name>
    kinds = ["config"]             # required: config | <ui kinds> | service
    label = "XDG Portals"     # default = <id> (menu display name)
    order = 20                     # ui stacking order, bottom -> top (default 0)
    morphology = "atomic"    # config plugins only: atomic | merge | hook-only.
                                   # default = hook-only without payload/target,
                                   # otherwise atomic. Ui kinds carry no
                                   # morphology — their form is the ledger form.
    target = "starship.toml"   # single-file plugin: lands at ~/.config/<target>
    target = "xdg:PICTURES/Wallpapers"  # shared living area (morphology = merge)
    packages        = ["mangowm"]       # default = [<plugin name>] (config kinds)
    packages_aur    = []                # default = []  (AUR helper installs)
    packages_flatpak = []               # default = []  (Flathub app IDs)
    preserve        = ["monitor.kdl"]   # default = []  (files kept across deploys)
    preserve_values = {}                # default = {}  (kept keys inside value files)
    chmod           = ["scripts/*.sh"]  # default = []  (globs, relative to plugin dir)
    category        = "browser"         # default = ""  (plugin detail grouping key)
    optional        = true              # default = false (optdepends, not hard dep)
    post_install    = "setup-rime"      # default = "" (hook script: configs/<plugin>/hooks/<name>)
    post_remove     = "clean-skin"      # default = "" (off-side hook, same shape)
    dependencies    = []                # default = []  (other Nyxuri plugins)

    [entryPoints]       # one entry per ui kind: path inside the plugin dir
    "edge" = "Bar.qml"

    [[settings]]        # settings routes & search anchors (settings schema)
    [[actions]]         # searchable fixed actions (search = include set)

    [privilege]         # declared root-level side effects (gate: 边界必须声明)
    [forms]             # form axes: inherit / allow / standalone / include /
                        # exclude / reload; [forms.<slot>] slot axes

A ``target`` plugin ships exactly one file (``plugins/<plugin>/<target>``) that
lands at ``~/.config/<target>``; form axes are directory affordances and do
not apply to it. A ``~/``-prefixed ``target`` declares a shared
living area outside ``~/.config``; an ``xdg:<KIND>/<rest>`` target resolves
``<KIND>`` through the XDG user dirs (``xdg-user-dir``), so a localised
Pictures dir lands wallpapers where the desktop looks for them.

This module is pure stdlib (``tomllib``, 3.11+). No hardcoded project plugin names.
"""

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nyxuri.core import get_env, log_msg

_MANIFEST_NAME = "manifest.toml"
_METADATA_NAMES = frozenset({"__pycache__"})

SCHEMA_VERSION = 1

MORPHOLOGY_RUNTIME = "runtime"
MORPHOLOGY_MERGE = "merge"
MORPHOLOGY_HOOK_ONLY = "hook-only"
MORPHOLOGY_ATOMIC = "atomic"
MORPHOLOGIES = (
    MORPHOLOGY_RUNTIME,
    MORPHOLOGY_MERGE,
    MORPHOLOGY_HOOK_ONLY,
    MORPHOLOGY_ATOMIC,
)
# Morphology is expressible in the manifest only for config plugins; the ui
# kinds carry their form in the kinds themselves (ledger-only existence).
_MORPHOLOGY_KEYS = (MORPHOLOGY_MERGE, MORPHOLOGY_HOOK_ONLY, MORPHOLOGY_ATOMIC)

KIND_CONFIG = "config"
KINDS = (
    KIND_CONFIG,
    "edge",
    "island",
    "overlay",
    "drawer",
    "surface:desktop",
    "popup:notification",
    "service",  # reserved: headless service plugins (no consumer yet)
)
UI_KINDS = tuple(kind for kind in KINDS if kind != KIND_CONFIG)

# Closed vocabulary (manifest-schema.md). An undeclared key is a parse error:
# the word table only shrinks or moves through a deliberate schema change.
_TOP_KEYS = frozenset({
    "schemaVersion", "id", "kinds", "label", "order", "morphology",
    "target", "packages", "packages_aur", "packages_flatpak",
    "preserve", "preserve_values", "chmod", "category", "optional",
    "post_install", "post_remove", "dependencies",
    "privilege", "forms", "entryPoints", "settings", "actions",
})
_RETIRED_KEYS = {
    "deploy": "retired and must be removed (executed with the optional-apps supply surface)",
    "detect": "retired and must be removed (executed with the optional-apps supply surface)",
    "runtime": "retired: the form is now declared by kinds (ui kinds = ledger form)",
    "merge": "retired: use morphology = \"merge\"",
}

_ID_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9.:-]*")
_ENTRY_KEYS = {"id", "title", "context", "icon", "source", "controls", "description",
               "aliases", "group", "order", "route"}
_ACTION_KEYS = {"id", "target", "method", "args", "confirmation",
                "availability", "search"}
_ACTION_SEARCH_KEYS = {"title", "description", "context", "icon", "aliases"}

# Settings schema value controls (S0-3b): a route declares `controls`
# instead of `source` and the host renders it from the atoms — Omarchy's
# schema form (boolean/enum/integer/string), TOML carrier, own vocabulary.
_SETTING_CONTROL_TYPES = ("switch", "select", "slider", "spin", "text")
_SETTING_CONTROL_KEYS = {"key", "type", "title", "description", "icon", "default",
                         "options", "min", "max", "step"}
_SETTING_CONTROL_OPTION_KEYS = {"value", "label", "icon"}
_CONFIRMATIONS = ("none", "power-menu")
AVAILABILITY = ("always", "awww", "nyxuri-wallpaper", "wallpaper-idle",
                "keystone", "keyboard-lock", "dock-previews")


@dataclass(frozen=True)
class ModuleManifest:
    """Resolved manifest for one plugin. Every field has a real value (defaults applied)."""

    id: str
    kinds: List[str]
    packages_repo: List[str]
    packages_aur: List[str]
    packages_flatpak: List[str]
    preserve: List[str]
    preserve_values: Dict[str, List[str]]
    chmod: List[str]
    label: str
    category: str
    dependencies: List[str]  # other Nyxuri plugins this plugin depends on
    is_deployable: bool
    entry_points: Dict[str, str] = field(default_factory=dict)  # ui kind -> QML entry
    order: int = 0               # ui stacking order, bottom -> top
    settings: List[dict] = field(default_factory=list)  # [[settings]] declarations
    actions: List[dict] = field(default_factory=list)   # [[actions]] declarations
    is_optional: bool = False  # True iff declared optional (optdepends, not hard dep)
    post_install: str = ""     # on-side hook: executable at configs/<plugin>/hooks/<spec>
    post_remove: str = ""      # off-side hook: same shape, run after the wipe
    requires_root: bool = False  # declared privilege escalation ([privilege])
    system_paths: List[str] = field(default_factory=list)  # declared /etc etc. touchpoints
    target: str = ""           # Single-file plugin: deployed file name under ~/.config
    merge: bool = False        # Shared living area: no-clobber deploy, snapshot = laid files
    runtime: bool = False      # Ledger-only plugin (shell.*): no living area, the
                               # running host reacts to the plugin-changed event
    morphology: str = MORPHOLOGY_ATOMIC
    form_inherit: bool = False
    form_allow: List[str] = field(default_factory=list)
    form_standalone: List[str] = field(default_factory=list)
    form_include: List[str] = field(default_factory=list)
    form_exclude: List[str] = field(default_factory=list)
    form_reload: List[str] = field(default_factory=list)
    forms: Dict[str, dict] = field(default_factory=dict)

    @property
    def is_runtime(self) -> bool:
        return self.morphology == MORPHOLOGY_RUNTIME

    @property
    def is_merge(self) -> bool:
        return self.morphology == MORPHOLOGY_MERGE

    @property
    def is_hook_only(self) -> bool:
        return self.morphology == MORPHOLOGY_HOOK_ONLY

    @property
    def is_atomic(self) -> bool:
        return self.morphology == MORPHOLOGY_ATOMIC


def _is_deployable(app_src: Path) -> bool:
    """A plugin is deployable iff it ships real config (more than just a manifest).

    ``hooks/`` is plugin-owned lifecycle behavior (KM3 contract) — it never
    counts as deployable config and never ships to the living area.
    """
    try:
        for entry in app_src.iterdir():
            if entry.name in _METADATA_NAMES or entry.name in (_MANIFEST_NAME, "hooks"):
                continue
            return True
    except OSError:
        pass
    return False


def _as_str_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    return []


def _as_forms_dict(value) -> Dict[str, dict]:
    """Slot-axis declarations under ``[forms]``: every dict-valued entry."""
    if not isinstance(value, dict):
        return {}
    return {key: cfg for key, cfg in value.items() if isinstance(cfg, dict)}


def _as_str_map(value) -> Dict[str, List[str]]:
    if not isinstance(value, dict):
        return {}
    result: Dict[str, List[str]] = {}
    for key, keys in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(keys, str):
            result[key] = [keys]
            continue
        if isinstance(keys, (list, tuple)):
            names = [name for name in keys if isinstance(name, str)]
            if names:
                result[key] = names
    return result


# ``xdg:`` target vocabulary. Only categories with a real resolver are
# accepted here; an unknown one is rejected rather than guessed (issue #144).
def _require_str(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or invalid '{field}'")
    return value


def _require_stable_id(value, field: str) -> str:
    text = _require_str(value, field)
    if not _ID_RE.fullmatch(text):
        raise ValueError(f"invalid stable id '{text}' ({field})")
    return text


def _safe_rel_parts(value: str, field: str) -> List[str]:
    """Relative path safety: inside the plugin dir, no escape, no absolute."""
    from nyxuri.core import is_safe_leaf_name

    parts = [part for part in value.replace("\\", "/").split("/") if part]
    if not parts or value.startswith("/") or not all(is_safe_leaf_name(p) for p in parts):
        raise ValueError(f"unsafe relative path in manifest: '{value}' ({field})")
    return parts


def _validate_kinds(raw) -> List[str]:
    kinds = _as_str_list(raw)
    if not kinds:
        raise ValueError("manifest key 'kinds' must be a non-empty array")
    if len(set(kinds)) != len(kinds):
        raise ValueError(f"duplicate kinds: {kinds}")
    for kind in kinds:
        if kind not in KINDS:
            raise ValueError(f"unknown kind '{kind}' (must be one of {KINDS})")
    return kinds


def _validate_entry_points(raw, ui_kinds: List[str], app_src: Path) -> Dict[str, str]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("entryPoints must be a table of kind = \"path\" entries")
    if set(raw) != set(ui_kinds):
        raise ValueError(
            f"entryPoints must declare exactly the ui kinds {sorted(ui_kinds)}, got {sorted(raw)}"
        )
    out: Dict[str, str] = {}
    for kind, value in raw.items():
        if not isinstance(value, str):
            raise ValueError(f"entryPoint '{kind}' must be a path string")
        parts = _safe_rel_parts(value, f"entryPoints.{kind}")
        if not (app_src / Path(*parts)).is_file():
            raise ValueError(f"entryPoint '{kind}' does not exist: '{value}'")
        out[kind] = value
    return out


def _require_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    return value


def _validate_setting_controls(settings_id: str, raw) -> List[dict]:
    """``controls`` — value-control schema rendered by the host (S0-3b)."""
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"settings '{settings_id}' controls must be a non-empty array")
    out: List[dict] = []
    seen_keys: set = set()
    for control in raw:
        if not isinstance(control, dict):
            raise ValueError(f"settings '{settings_id}' controls entries must be tables")
        unknown = sorted(set(control) - _SETTING_CONTROL_KEYS)
        if unknown:
            raise ValueError(
                f"settings '{settings_id}' control key '{unknown[0]}' is not in the vocabulary")
        key = _require_stable_id(control.get("key"), f"settings '{settings_id}' control.key")
        if "." in key or ":" in key:
            raise ValueError(
                f"settings '{settings_id}' control key '{key}' must be a leaf name "
                "(the storage namespace is plugin.key)")
        if key in seen_keys:
            raise ValueError(f"settings '{settings_id}' duplicate control key '{key}'")
        seen_keys.add(key)
        ctype = control.get("type")
        if ctype not in _SETTING_CONTROL_TYPES:
            raise ValueError(
                f"settings '{settings_id}' control '{key}' type must be one of "
                f"{'/'.join(_SETTING_CONTROL_TYPES)}")
        normalized = {
            "key": key,
            "type": ctype,
            "title": _require_str(control.get("title"), f"control '{key}' title"),
        }
        if control.get("description") is not None:
            normalized["description"] = _require_str(
                control.get("description"), f"control '{key}' description")
        if control.get("icon") is not None:
            normalized["icon"] = _require_str(control.get("icon"), f"control '{key}' icon")
        default_provided = "default" in control
        if ctype == "select":
            options = control.get("options")
            if not isinstance(options, list) or not options:
                raise ValueError(f"control '{key}' (select) needs a non-empty options array")
            values: list = []
            for option in options:
                if not isinstance(option, dict):
                    raise ValueError(f"control '{key}' options entries must be tables")
                unknown_option = sorted(set(option) - _SETTING_CONTROL_OPTION_KEYS)
                if unknown_option:
                    raise ValueError(
                        f"control '{key}' option key '{unknown_option[0]}' is not in the vocabulary")
                value = _require_str(option.get("value"), f"control '{key}' option value")
                if value in values:
                    raise ValueError(f"control '{key}' duplicate option value '{value}'")
                values.append(value)
            normalized["options"] = [{
                "value": option["value"],
                "label": _require_str(option.get("label"), f"control '{key}' option label"),
                **({"icon": option["icon"]} if "icon" in option else {}),
            } for option in options]
            if default_provided:
                default = _require_str(control["default"], f"control '{key}' default")
                if default not in values:
                    raise ValueError(f"control '{key}' default '{default}' is not an option value")
                normalized["default"] = default
        elif ctype in ("slider", "spin"):
            low = _require_number(control.get("min"), f"control '{key}' min")
            high = _require_number(control.get("max"), f"control '{key}' max")
            if not low < high:
                raise ValueError(f"control '{key}' min must be below max")
            step = 0.0 if ctype == "slider" else 1.0
            if "step" in control:
                step = _require_number(control["step"], f"control '{key}' step")
                if step < 0:
                    raise ValueError(f"control '{key}' step must not be negative")
            normalized.update({"min": low, "max": high, "step": step})
            if default_provided:
                default = _require_number(control["default"], f"control '{key}' default")
                if not low <= default <= high:
                    raise ValueError(f"control '{key}' default is outside [min, max]")
                normalized["default"] = default
        elif default_provided:
            if ctype == "switch":
                if not isinstance(control["default"], bool):
                    raise ValueError(f"control '{key}' default must be a boolean")
                normalized["default"] = control["default"]
            else:
                normalized["default"] = _require_str(control["default"], f"control '{key}' default")
        out.append(normalized)
    return out


def _validate_settings(raw, app_src: Path) -> List[dict]:
    """``[[settings]]`` — settings routes (source or controls) and search anchors."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("settings must be an array of tables")
    out: List[dict] = []
    seen_ids: set = set()
    route_ids: set = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("each [[settings]] entry must be a table")
        unknown = sorted(set(entry) - _ENTRY_KEYS)
        if unknown:
            raise ValueError(f"unknown [[settings]] key '{unknown[0]}'")
        entry_id = _require_stable_id(entry.get("id"), "settings.id")
        if entry_id in seen_ids:
            raise ValueError(f"duplicate settings id: '{entry_id}'")
        seen_ids.add(entry_id)
        forms = [name for name in ("source", "controls", "route") if name in entry]
        if len(forms) != 1:
            raise ValueError(
                f"settings '{entry_id}' must declare exactly one of "
                "source (panel page), controls (schema page) or route (anchor)"
            )
        out.append({
            "id": entry_id,
            "title": _require_str(entry.get("title"), f"settings '{entry_id}' title"),
            "context": _require_str(entry.get("context"), f"settings '{entry_id}' context"),
            "icon": _require_str(entry.get("icon"), f"settings '{entry_id}' icon"),
            "aliases": _as_str_list(entry.get("aliases")),
        })
        if forms[0] in ("source", "controls"):
            if forms[0] == "source":
                source = entry["source"]
                if not isinstance(source, str) or not source.endswith(".qml"):
                    raise ValueError(f"settings '{entry_id}' source must be a local QML filename")
                parts = _safe_rel_parts(source, f"settings '{entry_id}' source")
                if not (app_src / Path(*parts)).is_file():
                    raise ValueError(f"settings '{entry_id}' source does not exist: '{source}'")
                out[-1]["source"] = source
            else:
                out[-1]["controls"] = _validate_setting_controls(entry_id, entry["controls"])
            order = entry.get("order", 0)
            if isinstance(order, bool) or not isinstance(order, int):
                raise ValueError(f"settings '{entry_id}' order must be an integer")
            out[-1].update({
                "description": _require_str(entry.get("description"), f"settings '{entry_id}' description"),
                "group": _require_str(entry.get("group"), f"settings '{entry_id}' group"),
                "order": order,
            })
            route_ids.add(entry_id)
    # Anchors point at routes of the same manifest; nesting stays one deep.
    for entry, normalized in zip(raw, out):
        if "source" in entry or "controls" in entry:
            path = entry["id"].split(".")
            if len(path) > 2:
                raise ValueError(f"settings '{entry['id']}' nests deeper than one level")
            if len(path) == 2 and path[0] not in route_ids:
                raise ValueError(f"settings '{entry['id']}' has no parent route '{path[0]}'")
        else:
            route = _require_str(entry.get("route"), f"settings '{entry['id']}' route")
            if route not in route_ids:
                raise ValueError(f"settings '{entry['id']}' points at unknown route '{route}'")
            normalized["route"] = route
    return out


def _validate_actions(raw) -> List[dict]:
    """``[[actions]]`` — the search-visible fixed actions (search = include)."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("actions must be an array of tables")
    out: List[dict] = []
    seen_ids: set = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("each [[actions]] entry must be a table")
        unknown = sorted(set(entry) - _ACTION_KEYS)
        if unknown:
            raise ValueError(f"unknown [[actions]] key '{unknown[0]}'")
        action_id = _require_stable_id(entry.get("id"), "actions.id")
        if action_id in seen_ids:
            raise ValueError(f"duplicate action id: '{action_id}'")
        seen_ids.add(action_id)
        target = _require_str(entry.get("target"), f"action '{action_id}' target")
        method = _require_str(entry.get("method"), f"action '{action_id}' method")
        confirmation = entry.get("confirmation", "none")
        if confirmation not in _CONFIRMATIONS:
            raise ValueError(f"invalid confirmation: '{action_id}'")
        if target == "power-menu" and confirmation != "power-menu":
            raise ValueError(f"power actions must open the existing confirmation UI: '{action_id}'")
        availability = entry.get("availability", "always")
        if availability not in AVAILABILITY:
            raise ValueError(f"unknown availability: '{action_id}'")
        search = entry.get("search")
        if not isinstance(search, dict):
            raise ValueError(f"action '{action_id}' must declare a search table")
        unknown = sorted(set(search) - _ACTION_SEARCH_KEYS)
        if unknown:
            raise ValueError(f"unknown action search key '{unknown[0]}': '{action_id}'")
        out.append({
            "id": action_id,
            "target": target,
            "method": method,
            "args": _as_str_list(entry.get("args")),
            "confirmation": confirmation,
            "availability": availability,
            "search": {
                "title": _require_str(search.get("title"), f"action '{action_id}' title"),
                "description": _require_str(search.get("description"), f"action '{action_id}' description"),
                "context": _require_str(search.get("context"), f"action '{action_id}' context"),
                "icon": _require_str(search.get("icon"), f"action '{action_id}' icon"),
                "aliases": _as_str_list(search.get("aliases")),
            },
        })
    return out


_XDG_PREFIX = "xdg:"


def _resolve_xdg_target(target: str) -> Path:
    """Resolve ``xdg:<KIND>/<rest>`` against the XDG user dirs."""
    from nyxuri.core import get_pics_dir, get_xdg_user_dir, is_safe_leaf_name, assert_contained

    kind, _, rest = target[len(_XDG_PREFIX):].partition("/")
    kind = kind.upper()
    if not rest:
        raise ValueError(f"unsupported xdg: target '{target}'")
    parts = [p for p in rest.replace("\\", "/").split("/") if p]
    if not parts or not all(is_safe_leaf_name(p) for p in parts):
        raise ValueError(f"unsafe xdg: target path '{target}'")
    base = get_pics_dir() if kind == "PICTURES" else get_xdg_user_dir(kind)
    candidate = base.joinpath(*parts)
    return assert_contained(candidate, base)


def living_path(m: ModuleManifest, config_dir: Path) -> Path:
    """A plugin's living-area path (plugin-model.md §4 target exception).

    A ``~/``-prefixed (or absolute) ``target`` declares a shared living area
    outside ``~/.config`` — expanded against ``$HOME``. An ``xdg:<KIND>/<rest>``
    target resolves through the XDG user dirs (R0-4 generalises the map).
    A bare ``target`` is the single-file exception under ``~/.config``; no
    target means ``~/.config/<plugin>``.
    """
    if m.target.startswith(_XDG_PREFIX):
        return _resolve_xdg_target(m.target)
    if m.target.startswith(("~", "/")):
        return Path(os.path.expanduser(m.target))
    raw = m.target or m.id
    parts = [p for p in raw.replace("\\", "/").split("/") if p]
    from nyxuri.core import is_safe_leaf_name, assert_contained
    if not parts or not all(is_safe_leaf_name(p) for p in parts):
        raise ValueError(f"unsafe plugin target '{raw}'")
    candidate = config_dir.joinpath(*parts)
    return assert_contained(candidate, config_dir)


def load_manifest(app_src: Path, *, namespace: str = "") -> ModuleManifest:
    """Load a manifest for a plugin directory; defaults derived from the id.

    A present manifest must be new-form (closed vocabulary, ``schemaVersion``
    1, ``id`` == ``<namespace><directory>``); a missing manifest is the full
    default: ``kinds = ["config"]`` and every other default applies.
    """
    expected_id = namespace + app_src.name
    mpath = app_src / _MANIFEST_NAME
    data = {}
    if mpath.is_file():
        with open(mpath, "rb") as f:
            data = tomllib.load(f)
        # Closed vocabulary: an undeclared key is a parse error, and retired
        # words fail loudly instead of being silently ignored (KM1 doctrine:
        # 删除不寄生于新增). ``deploy``/``detect`` were the optional-apps supply
        # surface (R0-2); ``runtime``/``merge`` collapsed into kinds/morphology.
        for key in data:
            if key in _RETIRED_KEYS:
                raise ValueError(f"manifest key '{key}' is {_RETIRED_KEYS[key]}")
            if key not in _TOP_KEYS:
                raise ValueError(
                    f"unknown manifest key '{key}' (the schema is a closed vocabulary)"
                )
        if data.get("schemaVersion") != SCHEMA_VERSION:
            raise ValueError(
                f"manifest must declare schemaVersion = {SCHEMA_VERSION} (new-form only)"
            )
        if data.get("id") != expected_id:
            raise ValueError(
                f"manifest id '{data.get('id')}' does not match the registry id "
                f"'{expected_id}' (ids derive from the blueprint root and directory name)"
            )
        kinds = _validate_kinds(data.get("kinds"))
    else:
        kinds = [KIND_CONFIG]
    ui_kinds = [kind for kind in kinds if kind != KIND_CONFIG]

    forms = data.get("forms", {}) or {}
    privilege = data.get("privilege", {}) or {}
    # Absent packages -> [<plugin name>] for config kinds (the package the
    # plugin ships config for); ui kinds default to no packages. An explicit
    # empty list stays empty (flatpak/AUR-only plugins must keep their name
    # out of pacman).
    raw_repo = data.get("packages")
    if raw_repo is not None:
        pkg_repo = _as_str_list(raw_repo)
    else:
        pkg_repo = [app_src.name] if KIND_CONFIG in kinds else []

    manifest_preserve = _as_str_list(data.get("preserve"))
    manifest_forms = _as_forms_dict(data.get("forms"))
    for slot_cfg in manifest_forms.values():
        if isinstance(slot_cfg, dict):
            target = slot_cfg.get("target")
            if target and target not in manifest_preserve:
                manifest_preserve.append(target)

    from nyxuri.core import is_safe_leaf_name

    for p in manifest_preserve:
        parts = [part for part in p.replace("\\", "/").split("/") if part]
        if not parts or not all(is_safe_leaf_name(part) for part in parts) or Path(p).is_absolute():
            raise ValueError(f"unsafe preserve path in manifest: '{p}'")

    raw_preserve_values = _as_str_map(data.get("preserve_values"))
    for k in raw_preserve_values:
        parts = [part for part in k.replace("\\", "/").split("/") if part]
        if not parts or not all(is_safe_leaf_name(part) for part in parts) or Path(k).is_absolute():
            raise ValueError(f"unsafe preserve_values key in manifest: '{k}'")

    post_install_str = str(data.get("post_install", ""))
    if post_install_str and not is_safe_leaf_name(post_install_str):
        raise ValueError(f"unsafe post_install hook in manifest: '{post_install_str}'")

    post_remove_str = str(data.get("post_remove", ""))
    if post_remove_str and not is_safe_leaf_name(post_remove_str):
        raise ValueError(f"unsafe post_remove hook in manifest: '{post_remove_str}'")

    deployable = ("config" in kinds) and _is_deployable(app_src)
    target_str = str(data.get("target", ""))
    if target_str and not target_str.startswith(_XDG_PREFIX) and not target_str.startswith(("~", "/")):
        parts = [part for part in target_str.replace("\\", "/").split("/") if part]
        if not parts or not all(is_safe_leaf_name(part) for part in parts):
            raise ValueError(f"unsafe target path in manifest: '{target_str}'")

    order = data.get("order", 0)
    if isinstance(order, bool) or not isinstance(order, int):
        raise ValueError("manifest key 'order' must be an integer")

    raw_morphology = data.get("morphology")
    if KIND_CONFIG not in kinds:
        if raw_morphology is not None:
            raise ValueError(
                "morphology is declared but kinds carry no 'config' — "
                "ui kinds are ledger-form by definition"
            )
        morphology = MORPHOLOGY_RUNTIME
    elif raw_morphology is not None:
        if raw_morphology not in _MORPHOLOGY_KEYS:
            raise ValueError(
                f"unsupported morphology: '{raw_morphology}' (must be one of {_MORPHOLOGY_KEYS})"
            )
        morphology = raw_morphology
    elif not deployable and not target_str:
        morphology = MORPHOLOGY_HOOK_ONLY
    else:
        morphology = MORPHOLOGY_ATOMIC

    label = data.get("label", expected_id)
    if not isinstance(label, str) or not label.strip():
        raise ValueError("manifest key 'label' must be a non-empty string")

    return ModuleManifest(
        id=expected_id,
        kinds=kinds,
        entry_points=_validate_entry_points(data.get("entryPoints"), ui_kinds, app_src),
        order=order,
        settings=_validate_settings(data.get("settings"), app_src),
        actions=_validate_actions(data.get("actions")),
        packages_repo=pkg_repo,
        packages_aur=_as_str_list(data.get("packages_aur")),
        packages_flatpak=_as_str_list(data.get("packages_flatpak")),
        preserve=manifest_preserve,
        preserve_values=_as_str_map(data.get("preserve_values")),
        chmod=_as_str_list(data.get("chmod")),
        label=label,
        category=data.get("category", ""),
        dependencies=_as_str_list(data.get("dependencies")),
        is_deployable=deployable,
        is_optional=bool(data.get("optional", False)),
        post_install=str(data.get("post_install", "")),
        post_remove=str(data.get("post_remove", "")),
        requires_root=bool(privilege.get("requires_root", False)),
        system_paths=_as_str_list(privilege.get("system_paths")),
        target=target_str,
        merge=(morphology == MORPHOLOGY_MERGE),
        runtime=(morphology == MORPHOLOGY_RUNTIME),
        morphology=morphology,
        form_inherit=bool(forms.get("inherit")),
        form_allow=_as_str_list(forms.get("allow")),
        form_standalone=_as_str_list(forms.get("standalone")),
        form_include=_as_str_list(forms.get("include")),
        form_exclude=_as_str_list(forms.get("exclude")),
        form_reload=_as_str_list(forms.get("reload")),
        forms=manifest_forms,
    )


def _app_src(app_name: str) -> Path:
    """Resolve the on-disk source path for a plugin name under configs/."""
    return get_env().plugins_src / app_name


def load_manifest_for(app_name: str) -> ModuleManifest:
    """Convenience: load manifest by plugin name (resolves configs/<name> path)."""
    return load_manifest(_app_src(app_name))


_MANIFEST_CACHE: Optional[List[Tuple[str, "ModuleManifest"]]] = None

def discover_manifest_apps() -> List[Tuple[str, ModuleManifest]]:
    """Scan every plugin directory under configs/.

    Every subdirectory is a plugin shipping real config (or a runtime
    ledger-only unit). Sorted by name for deterministic output. Result is
    cached per process (manifest files cannot change under a running engine).
    """
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    env = get_env()
    if not env.plugins_src.is_dir():
        return []

    apps: List[Tuple[str, ModuleManifest]] = []
    for p in sorted(env.plugins_src.iterdir(), key=lambda x: x.name):
        if not p.is_dir() or p.is_symlink() or p.name in _METADATA_NAMES:
            continue
        try:
            m = load_manifest(p)
        except Exception as exc:
            # A malformed manifest must not break discovery of other plugins.
            log_msg("WARN", f"Skipping plugin '{p.name}': malformed manifest ({exc})")
            continue
        apps.append((p.name, m))

    _MANIFEST_CACHE = apps
    return apps


def discover_deployable_apps() -> List[str]:
    """Names of plugins that ship real config AND go through the atomic swap.

    Merge plugins (declared shared living areas) deploy only through the
    transaction's no-clobber path — they never join the atomic batch,
    where a swap would clobber user content.
    """
    return [name for name, m in discover_manifest_apps() if m.is_deployable and not m.merge]


def discover_optional_apps() -> List[str]:
    """Names of plugins declared optional (optdepends axis)."""
    return [name for name, m in discover_manifest_apps() if m.is_optional]
