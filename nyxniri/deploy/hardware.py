"""Hardware self-adaptation layer — NVIDIA env patching in niri config.kdl.

Kept as a SEPARATE layer from the preset system on purpose (§6): hardware
adaptation is auto-detected and user-invisible; presets are an explicit,
user-visible choice — different concepts, different mechanism. The patch
stays here until hardware variants exceed ~3 (then overlay presets; §11).
"""

import os
import re
import subprocess
from typing import Optional

from nyxniri.constants import MAIN_WM
from nyxniri.core import get_env, log_msg
from nyxniri.i18n import msg

# "primary" | "hybrid" | "none" — process-local, reset by TempEnv.
_NVIDIA_ROLE: Optional[str] = None

_NVIDIA_ENV_SPECS = (
    'GBM_BACKEND "nvidia-drm"',
    '__GLX_VENDOR_LIBRARY_NAME "nvidia"',
    'LIBVA_DRIVER_NAME "nvidia"',
)


def _classify_nvidia_role(lspci_text: str) -> str:
    """Return compositor role from `lspci` text (LC_ALL=C).

    primary — NVIDIA owns a VGA/Display device, or is the only GPU.
    hybrid  — NVIDIA is only a 3D controller beside an AMD/Intel display GPU.
    none    — no NVIDIA GPU.

    Presence of the word "nvidia" is not enough. Hybrid laptops typically
    composite on the iGPU; forcing nvidia-drm / nvidia VA-API makes Chromium
    decode on NVIDIA and present on AMD/Intel, which corrupts video frames.
    """
    nvidia_display = False
    nvidia_present = False
    other_display = False
    for raw in lspci_text.splitlines():
        line = raw.lower()
        is_vga = "vga compatible controller" in line
        is_display = "display controller" in line
        is_3d = "3d controller" in line
        if not (is_vga or is_display or is_3d):
            continue
        if "nvidia" in line:
            nvidia_present = True
            if is_vga or is_display:
                nvidia_display = True
        elif is_vga or is_display:
            other_display = True
    if nvidia_display or (nvidia_present and not other_display):
        return "primary"
    if nvidia_present:
        return "hybrid"
    return "none"


def _nvidia_role() -> str:
    global _NVIDIA_ROLE
    if _NVIDIA_ROLE is not None:
        return _NVIDIA_ROLE
    try:
        res = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        _NVIDIA_ROLE = _classify_nvidia_role(res.stdout)
    except Exception:
        _NVIDIA_ROLE = "none"
    return _NVIDIA_ROLE


def _apply_nvidia_env(content: str, enabled: bool) -> str:
    """Comment or uncomment the three NVIDIA env lines. Idempotent."""
    for spec in _NVIDIA_ENV_SPECS:
        escaped = re.escape(spec)
        if enabled:
            content = re.sub(
                rf'^(\s*)//\s*({escaped})',
                r'\1\2',
                content,
                flags=re.MULTILINE,
            )
        else:
            content = re.sub(
                rf'^(\s*)({escaped})',
                r'\1// \2',
                content,
                flags=re.MULTILINE,
            )
    return content


def _phase_hardware_patches() -> None:
    env = get_env()
    niri_conf = env.config_dir / MAIN_WM / "config.kdl"
    if not niri_conf.is_file():
        return

    role = _nvidia_role()
    if role == "primary":
        print(msg("log_nvidia_gpu_detected"))
        log_msg("INFO", "NVIDIA is the display GPU. Enabling NVIDIA envs in config.kdl")
        enabled = True
    elif role == "hybrid":
        print(msg("log_nvidia_gpu_hybrid"))
        log_msg(
            "INFO",
            "NVIDIA dGPU found but display GPU is not NVIDIA. Keeping NVIDIA envs disabled.",
        )
        enabled = False
    else:
        print(msg("log_nvidia_gpu_not_detected"))
        log_msg("INFO", "Non-NVIDIA GPU detected. NVIDIA envs kept disabled.")
        enabled = False

    content = niri_conf.read_text(encoding="utf-8")
    patched = _apply_nvidia_env(content, enabled)
    if patched != content:
        niri_conf.write_text(patched, encoding="utf-8")
