"""Self-describing app manifests (.module.toml + .optional-apps.toml).

A ``configs/<app>/`` directory is NyxNiri's first-class unit. By convention it
is self-describing: the directory name drives every default. A sibling
``.module.toml`` overrides defaults only when the app is exceptional (niri
preserves ``monitor.kdl``; missioncenter's package is ``mission-center``).
**No manifest file = full defaults.**

Schema (all fields live under one ``[packages]`` table; all optional)::

    [packages]
    repo     = ["kitty"]            # default = [<app name>]
    aur      = []                    # default = []
    flatpak  = []                    # default = []  (Flathub app IDs)
    preserve = ["monitor.kdl"]       # default = []  (files kept across deploys)
    chmod    = ["scripts/*.sh"]      # default = []  (globs, relative to app dir)
    label    = "XDG Portals"         # default = <app name> (menu display name)
    category = "browser"             # default = ""  (apps menu grouping key)
    detect   = "mission-center"      # default = <app name> (pkg/binary to detect)

File-type apps (``starship.toml``) use a sidecar manifest named
``<file>.module.toml`` next to the file — the only degenerate case today.

Two INDEPENDENT axes (§2 design, decoupled on purpose):
  - **has config**  = a ``configs/<app>/`` dir exists → deployed by install
  - **is optional** = listed in ``.optional-apps.toml`` → offered in the deps
    menu, packages land in AUR ``optdepends``. Stays optional EVEN IF a config
    dir is later added (optional + config coexist — the user may add configs to
    an optional app on a whim without graduating it to "required").

This module is pure stdlib (``tomllib``, 3.11+). No hardcoded project app names.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nyxniri.core import get_env

_MANIFEST_NAME = ".module.toml"
_OPTIONAL_APPS_NAME = ".optional-apps.toml"


@dataclass(frozen=True)
class ModuleManifest:
    """Resolved manifest for one app. Every field has a real value (defaults applied)."""

    name: str
    packages_repo: List[str]
    packages_aur: List[str]
    packages_flatpak: List[str]
    preserve: List[str]
    chmod: List[str]
    label: str
    category: str
    detect: str
    is_deployable: bool
    is_optional: bool = False  # True iff listed in .optional-apps.toml (§2 axis B)


def _manifest_path(app_src: Path) -> Path:
    """Locate the manifest file for a dir-type or file-type app source."""
    if app_src.is_dir():
        return app_src / _MANIFEST_NAME
    # File-type app (e.g. starship.toml): sidecar "<file>.module.toml"
    return app_src.parent / (app_src.name + ".module.toml")


def _is_deployable(app_src: Path) -> bool:
    """An app is deployable iff it ships real config (more than just a manifest)."""
    if app_src.is_file():
        return True
    try:
        for entry in app_src.iterdir():
            if entry.name == "__pycache__" or entry.name == _MANIFEST_NAME:
                continue
            return True
    except OSError:
        pass
    return False


def load_manifest(app_src: Path, is_optional: bool = False) -> ModuleManifest:
    """Load a manifest for an app source (dir or file); defaults derived from name.

    ``is_optional`` is an axis-B flag (§2): whether the app is listed in
    ``.optional-apps.toml``. It is orthogonal to deployability (axis A): an app
    can be optional AND ship config, or optional with no config, or required
    with config. The caller resolves axis B; this function handles axis A
    (deployability) from the on-disk source.
    """
    name = app_src.name
    mpath = _manifest_path(app_src)
    data = {}
    if mpath.is_file():
        with open(mpath, "rb") as f:
            data = tomllib.load(f)

    packages = data.get("packages", {}) or {}
    pkg_repo = packages.get("repo")
    if pkg_repo is None:
        pkg_repo = [name]

    return ModuleManifest(
        name=name,
        packages_repo=list(pkg_repo),
        packages_aur=list(packages.get("aur", [])),
        packages_flatpak=list(packages.get("flatpak", [])),
        preserve=list(packages.get("preserve", [])),
        chmod=list(packages.get("chmod", [])),
        label=packages.get("label", name),
        category=packages.get("category", ""),
        detect=packages.get("detect", name),
        is_deployable=_is_deployable(app_src),
        is_optional=is_optional,
    )


def _optional_toml_path() -> Path:
    return get_env().configs_src / _OPTIONAL_APPS_NAME


def load_optional_apps() -> Dict[str, dict]:
    """Return {name: entry-dict} from ``.optional-apps.toml`` (axis B source).

    Each ``[[app]]`` block: name (required), repo/aur/label/detect (optional,
    defaulting the same as .module.toml). An empty file or missing file → {}.
    """
    path = _optional_toml_path()
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    result: Dict[str, dict] = {}
    for entry in data.get("app", []) or []:
        name = entry.get("name")
        if name:
            result[name] = entry
    return result


def _manifest_from_optional(name: str, entry: dict) -> ModuleManifest:
    """Build a manifest for a toml-only optional app (no config dir)."""
    return ModuleManifest(
        name=name,
        packages_repo=list(entry.get("repo", [name])),
        packages_aur=list(entry.get("aur", [])),
        packages_flatpak=list(entry.get("flatpak", [])),
        preserve=[],
        chmod=[],
        label=entry.get("label", name),
        category=entry.get("category", ""),
        detect=entry.get("detect", name),
        is_deployable=False,
        is_optional=True,
    )


def _merge_optional_entry(m: ModuleManifest, entry: dict) -> ModuleManifest:
    """Overlay the axis-B toml entry onto a dual app (config dir + optional).

    Division of labor: .optional-apps.toml owns the optional axis (packages,
    label, category, detect); the .module.toml keeps config-axis fields
    (preserve, chmod) untouched.
    """
    return ModuleManifest(
        name=m.name,
        packages_repo=list(entry.get("repo", m.packages_repo)),
        packages_aur=list(entry.get("aur", m.packages_aur)),
        packages_flatpak=list(entry.get("flatpak", m.packages_flatpak)),
        preserve=m.preserve,
        chmod=m.chmod,
        label=entry.get("label", m.label),
        category=entry.get("category", m.category),
        detect=entry.get("detect", m.detect),
        is_deployable=m.is_deployable,
        is_optional=True,
    )


def _app_src(app_name: str) -> Path:
    """Resolve the on-disk source path for an app name under configs/."""
    return get_env().configs_src / app_name


def load_manifest_for(app_name: str) -> ModuleManifest:
    """Convenience: load manifest by app name (resolves configs/<name> path).

    Only valid for apps that have a config dir/file; toml-only optional apps
    (no dir) are not resolvable here — use the manifest from
    ``discover_manifest_apps()`` instead.
    """
    return load_manifest(_app_src(app_name))


def _is_configs_metadata(name: str) -> bool:
    """True for files that are NyxNiri metadata, not an app (skip in discovery)."""
    return (
        name == "__pycache__"
        or name == _OPTIONAL_APPS_NAME
        or name.endswith(".module.toml")
    )


_MANIFEST_CACHE: Optional[List[Tuple[str, "ModuleManifest"]]] = None

def discover_manifest_apps() -> List[Tuple[str, ModuleManifest]]:
    """Scan all apps under configs/ + read .optional-apps.toml; merge.

    Returns ``(name, manifest)`` for every app — both deployable (has a config
    dir) and optional (in the toml). An app in BOTH appears once with
    ``is_deployable=True`` AND ``is_optional=True``; its optional-axis fields
    (packages/label/category/detect) come from the toml. Sorted by name for
    deterministic output. Result is cached per process (manifest files cannot
    change under a running engine).
    """
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    env = get_env()
    if not env.configs_src.is_dir():
        return []

    optional = load_optional_apps()
    apps: List[Tuple[str, ModuleManifest]] = []
    seen: set = set()

    # Axis A: dir-scan for apps that ship config (deployable or manifest-only-dir)
    for p in sorted(env.configs_src.iterdir(), key=lambda x: x.name):
        if _is_configs_metadata(p.name):
            continue
        try:
            m = load_manifest(p, is_optional=(p.name in optional))
            if p.name in optional:
                m = _merge_optional_entry(m, optional[p.name])
        except Exception:
            # A malformed manifest must not break discovery of other apps.
            continue
        apps.append((p.name, m))
        seen.add(p.name)

    # Axis B: toml-only optional apps (no config dir)
    for name, entry in optional.items():
        if name in seen:
            continue  # dir exists → already covered, is_optional set there
        apps.append((name, _manifest_from_optional(name, entry)))

    apps.sort(key=lambda x: x[0])
    _MANIFEST_CACHE = apps
    return apps


def discover_deployable_apps() -> List[str]:
    """Names of apps that ship real config (have a configs/<app>/ dir)."""
    return [name for name, m in discover_manifest_apps() if m.is_deployable]


def discover_optional_apps() -> List[str]:
    """Names of apps listed in .optional-apps.toml (axis B, regardless of config dir)."""
    return [name for name, m in discover_manifest_apps() if m.is_optional]
