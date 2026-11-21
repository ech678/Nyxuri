"""Compositor definitions and driver surface: niri, mango."""

from __future__ import annotations

import os
from dataclasses import dataclass

MAIN_WM = "niri"


@dataclass(frozen=True)
class Compositor:
    """Static facts about one supported compositor."""

    id: str
    display_name: str
    reload_argv: tuple[str, ...]
    portal_conf: str
    config_relpath: str | None = None
    scripts_subpath: str | None = None
    has_glow_support: bool = False
    doctor_outputs_cmd: tuple[str, ...] | None = None
    essential_scripts: tuple[str, ...] = ()


COMPOSITORS: dict[str, Compositor] = {
    "niri": Compositor(
        id="niri",
        display_name="Niri",
        reload_argv=("niri", "msg", "action", "load-config-file"),
        portal_conf="niri-portals.conf",
        config_relpath="niri/config.kdl",
        scripts_subpath="niri/scripts",
        has_glow_support=True,
        doctor_outputs_cmd=("niri", "msg", "outputs"),
        essential_scripts=(
            "session-shell.sh",
            "shell-action.sh",
            "toggle-eyecare.sh",
            "niri-scratch-toggle.sh",
            "niri-scratch-menu.py",
            "niri-brightness.sh",
        ),
    ),
    "mango": Compositor(
        id="mango",
        display_name="Mango WM",
        reload_argv=("mmsg", "dispatch", "reload_config"),
        portal_conf="mango-portals.conf",
        config_relpath="mango/config.conf",
        scripts_subpath="mango/scripts",
        has_glow_support=False,
        doctor_outputs_cmd=None,
        essential_scripts=(
            "session-shell.sh",
            "shell-action.sh",
            "mango-brightness.sh",
            "hotkey-helper.py",
        ),
    ),
}


def detect_preferred_wm() -> str:
    """Detect the running compositor from the session; MAIN_WM fallback."""
    xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    for wm in COMPOSITORS:
        if wm == xdg or wm in xdg:
            return wm
    return MAIN_WM


def session_wm(xdg_lower: str) -> str:
    """Map a lowercase XDG_CURRENT_DESKTOP onto a known compositor id."""
    return xdg_lower if xdg_lower in COMPOSITORS else MAIN_WM


def portal_conf_name(xdg_lower: str) -> str:
    """Portal routing file for a session's compositor (unknown -> main)."""
    return COMPOSITORS[session_wm(xdg_lower)].portal_conf


def get_compositor(wm_id: str | None = None) -> Compositor:
    """Get Compositor record by ID or fallback to detected/main WM."""
    if wm_id and wm_id in COMPOSITORS:
        return COMPOSITORS[wm_id]
    return COMPOSITORS.get(detect_preferred_wm(), COMPOSITORS[MAIN_WM])


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
