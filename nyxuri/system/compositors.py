"""Compositor definitions and dynamic blueprint discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

MAIN_WM = "niri"


@dataclass(frozen=True)
class Compositor:
    """Facts about one supported compositor."""

    id: str
    display_name: str
    reload_argv: tuple[str, ...]
    portal_conf: str
    config_relpath: str | None = None
    scripts_subpath: str | None = None
    has_glow_support: bool = False
    doctor_outputs_cmd: tuple[str, ...] | None = None
    essential_scripts: tuple[str, ...] = ()


def discover_compositors() -> dict[str, Compositor]:
    """Dynamically discover compositors from plugins/ blueprints."""
    import tomllib
    from nyxuri.system.env import get_env

    try:
        env = get_env()
        plugins_dir = env.plugins_src
    except Exception:
        plugins_dir = Path(__file__).resolve().parents[2] / "plugins"

    if not plugins_dir.is_dir():
        repo_plugins = Path(__file__).resolve().parents[2] / "plugins"
        if repo_plugins.is_dir():
            plugins_dir = repo_plugins

    compositors: dict[str, Compositor] = {}
    if not plugins_dir.is_dir():
        return compositors

    for entry in sorted(plugins_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        manifest_file = entry / "manifest.toml"
        if not manifest_file.is_file():
            continue

        try:
            with manifest_file.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            continue

        category = data.get("category", "")
        if category != "compositor":
            continue

        cid = data.get("id", entry.name)
        label = data.get("label", cid.capitalize())

        forms_section = data.get("forms", {})
        reload_val = forms_section.get("reload", [])
        if isinstance(reload_val, list):
            reload_argv = tuple(str(x) for x in reload_val)
        else:
            reload_argv = ()

        portal_conf = f"{cid}-portals.conf"

        config_relpath = None
        for candidate in ("config.kdl", "config.conf", f"{cid}.conf"):
            if (entry / candidate).is_file():
                config_relpath = f"{cid}/{candidate}"
                break

        scripts_subpath = None
        essential_scripts: tuple[str, ...] = ()
        scripts_dir = entry / "scripts"
        if scripts_dir.is_dir():
            scripts_subpath = f"{cid}/scripts"
            essential_scripts = tuple(sorted(
                f.name for f in scripts_dir.iterdir()
                if f.is_file() and not f.name.startswith(".")
            ))

        has_glow_support = bool("glow" in forms_section or (entry / "glow").is_dir())

        doctor_outputs_cmd = None
        if cid == "niri":
            doctor_outputs_cmd = ("niri", "msg", "outputs")

        compositors[cid] = Compositor(
            id=cid,
            display_name=label,
            reload_argv=reload_argv,
            portal_conf=portal_conf,
            config_relpath=config_relpath,
            scripts_subpath=scripts_subpath,
            has_glow_support=has_glow_support,
            doctor_outputs_cmd=doctor_outputs_cmd,
            essential_scripts=essential_scripts,
        )

    return compositors


class _CompositorsDict(dict):
    """Dynamic mapping proxy providing backward-compatible dictionary access to discovered compositors."""

    def _refresh(self) -> None:
        self.clear()
        self.update(discover_compositors())

    def __getitem__(self, key: str) -> Compositor:
        self._refresh()
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        self._refresh()
        return super().get(key, default)

    def __contains__(self, key: object) -> bool:
        self._refresh()
        return super().__contains__(key)

    def __iter__(self):
        self._refresh()
        return super().__iter__()

    def __len__(self) -> int:
        self._refresh()
        return super().__len__()

    def keys(self):
        self._refresh()
        return super().keys()

    def values(self):
        self._refresh()
        return super().values()

    def items(self):
        self._refresh()
        return super().items()

    def __repr__(self) -> str:
        self._refresh()
        return super().__repr__()


COMPOSITORS: dict[str, Compositor] = _CompositorsDict()


def get_main_wm() -> str:
    """Dynamically deduce preferred default compositor, falling back to MAIN_WM."""
    comps = discover_compositors()
    if MAIN_WM in comps:
        return MAIN_WM
    if comps:
        return next(iter(comps))
    return MAIN_WM


def detect_preferred_wm() -> str:
    """Detect the running compositor from the session; MAIN_WM fallback."""
    xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    for wm in COMPOSITORS:
        if wm == xdg or wm in xdg:
            return wm
    return get_main_wm()


def session_wm(xdg_lower: str) -> str:
    """Map a lowercase XDG_CURRENT_DESKTOP onto a known compositor id."""
    return xdg_lower if xdg_lower in COMPOSITORS else get_main_wm()


def portal_conf_name(xdg_lower: str) -> str:
    """Portal routing file for a session's compositor (unknown -> main)."""
    return COMPOSITORS[session_wm(xdg_lower)].portal_conf


def get_compositor(wm_id: str | None = None) -> Compositor:
    """Get Compositor record by ID or fallback to detected/main WM."""
    if wm_id and wm_id in COMPOSITORS:
        return COMPOSITORS[wm_id]
    pref = detect_preferred_wm()
    if pref in COMPOSITORS:
        return COMPOSITORS[pref]
    main = get_main_wm()
    if main in COMPOSITORS:
        return COMPOSITORS[main]
    return Compositor(
        id="niri",
        display_name="Niri",
        reload_argv=("niri", "msg", "action", "load-config-file"),
        portal_conf="niri-portals.conf",
        config_relpath="niri/config.kdl",
        scripts_subpath="niri/scripts",
        has_glow_support=True,
    )


def reload_compositor(wm_id: str | None = None) -> bool:
    """Safely execute reload_argv for the specified (or active) compositor."""
    import shutil
    from nyxuri.system.env import timed_run

    comp = get_compositor(wm_id)
    if not comp.reload_argv:
        return False
    bin_name = comp.reload_argv[0]
    if not shutil.which(bin_name):
        return False
    res = timed_run(list(comp.reload_argv), 3, capture_output=True, text=True, check=False)
    return res is not None and res.returncode == 0
