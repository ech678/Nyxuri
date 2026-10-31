"""Unit manifests (``manifest.toml``) — the unit model's self-description.

A ``configs/<unit>/`` directory is Nyxuri's first-class unit. By convention
it is self-describing: the directory name drives every default. A sibling
``manifest.toml`` overrides defaults only when the unit is exceptional (niri
preserves ``monitor.kdl``; missioncenter's package is ``mission-center``).
**No manifest file = full defaults** (unit-model.md §4: 只写例外).

Schema (all fields optional, flat at top level)::

    target = "starship.toml"   # single-file unit: lands at ~/.config/<target>
    target = "xdg:PICTURES/Wallpapers"  # shared living area (implies merge use)
    merge = true               # shared living area: no-clobber deploy, off
                               # withdraws only laid files (never rm -rf)
    runtime = true             # ledger-only unit: no living area, no deploy;
                               # the running host reacts to the unit-changed event
    packages        = ["mangowm"]       # default = [<unit name>]
    packages_aur    = []                # default = []  (AUR helper installs)
    packages_flatpak = []               # default = []  (Flathub app IDs)
    preserve        = ["monitor.kdl"]   # default = []  (files kept across deploys)
    preserve_values = {}                # default = {}  (kept keys inside value files)
    chmod           = ["scripts/*.sh"]  # default = []  (globs, relative to unit dir)
    label           = "XDG Portals"     # default = <unit name> (menu display name)
    category        = "browser"         # default = ""  (apps menu grouping key)
    detect          = "mission-center"  # default = <unit name> (pkg/binary to detect)
    optional        = true              # default = false (menu + optdepends, not hard dep)
    post_install    = "setup-rime"      # default = "" (hook script: configs/<unit>/hooks/<name>)
    post_remove     = "clean-skin"      # default = "" (off-side hook, same shape)
    dependencies    = []                # default = []  (other Nyxuri units)

    [privilege]         # declared root-level side effects (gate: 边界必须声明)
    requires_root = true
    system_paths = ["/etc/greetd/config.toml"]

    [presets]           # inherit / allow / standalone / include / exclude / reload
    [parts.<slot>]      # target / source_dir / default

A ``target`` unit ships exactly one file (``plugins/<unit>/<target>``) that
lands at ``~/.config/<target>``; presets and parts are directory affordances
and do not apply to it. A ``~/``-prefixed ``target`` declares a shared
living area outside ``~/.config`` (implies ``merge`` semantics); an
``xdg:<KIND>/<rest>`` target resolves ``<KIND>`` through the XDG user dirs
(``xdg-user-dir``), so a localised Pictures dir lands wallpapers where the
desktop looks for them.

This module is pure stdlib (``tomllib``, 3.11+). No hardcoded project unit names.
"""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nyxuri.core import get_env, log_msg

_MANIFEST_NAME = "manifest.toml"
_METADATA_NAMES = frozenset({"__pycache__"})


@dataclass(frozen=True)
class ModuleManifest:
    """Resolved manifest for one unit. Every field has a real value (defaults applied)."""

    name: str
    packages_repo: List[str]
    packages_aur: List[str]
    packages_flatpak: List[str]
    preserve: List[str]
    preserve_values: Dict[str, List[str]]
    chmod: List[str]
    label: str
    category: str
    detect: str
    dependencies: List[str]  # other Nyxuri units this unit depends on
    is_deployable: bool
    is_optional: bool = False  # True iff declared optional (menu + optdepends)
    post_install: str = ""     # on-side hook: executable at configs/<unit>/hooks/<spec>
    post_remove: str = ""      # off-side hook: same shape, run after the wipe
    requires_root: bool = False  # declared privilege escalation ([privilege])
    system_paths: List[str] = field(default_factory=list)  # declared /etc etc. touchpoints
    target: str = ""           # Single-file unit: deployed file name under ~/.config
    merge: bool = False        # Shared living area: no-clobber deploy, snapshot = laid files
    runtime: bool = False      # Ledger-only unit (shell.*): no living area, the
                               # running host reacts to the unit-changed event
    preset_inherit: bool = False
    preset_allow: List[str] = field(default_factory=list)
    preset_standalone: List[str] = field(default_factory=list)
    preset_include: List[str] = field(default_factory=list)
    preset_exclude: List[str] = field(default_factory=list)
    preset_reload: List[str] = field(default_factory=list)
    parts: Dict[str, dict] = field(default_factory=dict)


def _is_deployable(app_src: Path) -> bool:
    """A unit is deployable iff it ships real config (more than just a manifest).

    ``hooks/`` is unit-owned lifecycle behavior (KM3 contract) — it never
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


def _as_parts_dict(value) -> Dict[str, dict]:
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
_XDG_PREFIX = "xdg:"


def _resolve_xdg_target(target: str) -> Path:
    """Resolve ``xdg:<KIND>/<rest>`` against the XDG user dirs."""
    from nyxuri.core import get_pics_dir

    kind, _, rest = target[len(_XDG_PREFIX):].partition("/")
    kind = kind.upper()
    if kind != "PICTURES" or not rest:
        raise ValueError(f"unsupported xdg: target '{target}'")
    return get_pics_dir() / rest


def living_path(m: ModuleManifest, config_dir: Path) -> Path:
    """A unit's living-area path (unit-model.md §4 target exception).

    A ``~/``-prefixed (or absolute) ``target`` declares a shared living area
    outside ``~/.config`` — expanded against ``$HOME``. An ``xdg:<KIND>/<rest>``
    target resolves through the XDG user dirs (R0-4 generalises the map).
    A bare ``target`` is the single-file exception under ``~/.config``; no
    target means ``~/.config/<unit>``.
    """
    if m.target.startswith(_XDG_PREFIX):
        return _resolve_xdg_target(m.target)
    if m.target.startswith(("~", "/")):
        return Path(os.path.expanduser(m.target))
    return config_dir / (m.target or m.name)


def load_manifest(app_src: Path) -> ModuleManifest:
    """Load a manifest for a unit directory; defaults derived from the name."""
    name = app_src.name
    mpath = app_src / _MANIFEST_NAME
    data = {}
    if mpath.is_file():
        with open(mpath, "rb") as f:
            data = tomllib.load(f)

    presets = data.get("presets", {}) or {}
    privilege = data.get("privilege", {}) or {}
    # Absent packages → [<unit name>]; an explicit empty list stays empty
    # (flatpak/AUR-only units must keep their name out of pacman).
    raw_repo = data.get("packages")
    pkg_repo = _as_str_list(raw_repo) if raw_repo is not None else [name]

    manifest_preserve = _as_str_list(data.get("preserve"))
    manifest_parts = _as_parts_dict(data.get("parts"))
    for slot_cfg in manifest_parts.values():
        if isinstance(slot_cfg, dict):
            target = slot_cfg.get("target")
            if target and target not in manifest_preserve:
                manifest_preserve.append(target)

    return ModuleManifest(
        name=name,
        packages_repo=pkg_repo,
        packages_aur=_as_str_list(data.get("packages_aur")),
        packages_flatpak=_as_str_list(data.get("packages_flatpak")),
        preserve=manifest_preserve,
        preserve_values=_as_str_map(data.get("preserve_values")),
        chmod=_as_str_list(data.get("chmod")),
        label=data.get("label", name),
        category=data.get("category", ""),
        detect=data.get("detect", name),
        dependencies=_as_str_list(data.get("dependencies")),
        is_deployable=_is_deployable(app_src),
        is_optional=bool(data.get("optional", False)),
        post_install=str(data.get("post_install", "")),
        post_remove=str(data.get("post_remove", "")),
        requires_root=bool(privilege.get("requires_root", False)),
        system_paths=_as_str_list(privilege.get("system_paths")),
        target=str(data.get("target", "")),
        merge=bool(data.get("merge", False)),
        runtime=bool(data.get("runtime", False)),
        preset_inherit=bool(presets.get("inherit")),
        preset_allow=_as_str_list(presets.get("allow")),
        preset_standalone=_as_str_list(presets.get("standalone")),
        preset_include=_as_str_list(presets.get("include")),
        preset_exclude=_as_str_list(presets.get("exclude")),
        preset_reload=_as_str_list(presets.get("reload")),
        parts=manifest_parts,
    )


def _app_src(app_name: str) -> Path:
    """Resolve the on-disk source path for a unit name under configs/."""
    return get_env().units_src / app_name


def load_manifest_for(app_name: str) -> ModuleManifest:
    """Convenience: load manifest by unit name (resolves configs/<name> path)."""
    return load_manifest(_app_src(app_name))


_MANIFEST_CACHE: Optional[List[Tuple[str, "ModuleManifest"]]] = None

def discover_manifest_apps() -> List[Tuple[str, ModuleManifest]]:
    """Scan every unit directory under configs/.

    Every subdirectory is a unit: deployable (ships config) or
    optional-only (manifest declares packages, nothing to deploy). Sorted
    by name for deterministic output. Result is cached per process
    (manifest files cannot change under a running engine).
    """
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    env = get_env()
    if not env.units_src.is_dir():
        return []

    apps: List[Tuple[str, ModuleManifest]] = []
    for p in sorted(env.units_src.iterdir(), key=lambda x: x.name):
        if not p.is_dir() or p.is_symlink() or p.name in _METADATA_NAMES:
            continue
        try:
            m = load_manifest(p)
        except Exception as exc:
            # A malformed manifest must not break discovery of other units.
            log_msg("WARN", f"Skipping unit '{p.name}': malformed manifest ({exc})")
            continue
        apps.append((p.name, m))

    _MANIFEST_CACHE = apps
    return apps


def discover_deployable_apps() -> List[str]:
    """Names of units that ship real config AND go through the atomic swap.

    Merge units (declared shared living areas) deploy only through the
    transaction's no-clobber path — they never join the atomic batch,
    where a swap would clobber user content.
    """
    return [name for name, m in discover_manifest_apps() if m.is_deployable and not m.merge]


def discover_optional_apps() -> List[str]:
    """Names of units declared optional (menu + optdepends axis)."""
    return [name for name, m in discover_manifest_apps() if m.is_optional]
