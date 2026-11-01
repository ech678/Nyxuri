"""Compositor registry — the Python-side compositor driver surface (S0-5).

One declarative entry per supported compositor. The installer's WM
radio special-case, the doctor's session/portal literals and the theme
reload argv all read this single registry instead of scattering
``("mango", "niri")`` tuples. A third compositor means a new entry here,
not a new literal (T5 debt, collected with S0-5).

Pure standard library; imports nothing from the engine.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MAIN_WM = "niri"


@dataclass(frozen=True)
class Compositor:
    """Static facts about one supported compositor."""

    id: str
    # Ask the running compositor to reload its config (theme/layout pushes).
    reload_argv: tuple[str, ...]
    # xdg-desktop-portal routing file this compositor's session expects.
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
