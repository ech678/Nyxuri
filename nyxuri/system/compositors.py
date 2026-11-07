"""Compositor definitions and driver surface: niri, mango."""

from __future__ import annotations

import os
from dataclasses import dataclass

MAIN_WM = "niri"


@dataclass(frozen=True)
class Compositor:
    """Static facts about one supported compositor."""

    id: str
    reload_argv: tuple[str, ...]
    portal_conf: str


COMPOSITORS: dict[str, Compositor] = {
    "niri": Compositor(
        id="niri",
        reload_argv=("niri", "msg", "action", "load-config-file"),
        portal_conf="niri-portals.conf",
    ),
    "mango": Compositor(
        id="mango",
        reload_argv=("mmsg", "dispatch", "reload_config"),
        portal_conf="mango-portals.conf",
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
