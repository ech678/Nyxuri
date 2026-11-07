from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

ARCH = "arch"
FEDORA = "fedora"

ARCH_IDS = frozenset({
    "arch", "archarm", "archlinux", "artix", "cachyos", "endeavouros",
    "garuda", "manjaro", "rebornos",
})
FEDORA_IDS = frozenset({
    "fedora", "nobara", "rhel", "centos", "rocky", "almalinux", "ol",
})

FEDORA_RENAMES = {
    "adw-gtk-theme": "adw-gtk3-theme",
    "ffmpeg": "ffmpeg-free",
    "noto-fonts-cjk": "google-noto-sans-cjk-fonts",
    "python-cairo": "python3-cairo",
    "python-gobject": "python3-gobject",
    "qt6-imageformats": "qt6-qtimageformats",
    "ttf-jetbrains-mono": "jetbrains-mono-fonts",
}

FEDORA_COPRS = {
    "starship": "atim/starship",
}


@lru_cache(maxsize=1)
def os_release() -> dict:
    try:
        text = Path("/etc/os-release").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if not sep or key.lstrip().startswith("#"):
            continue
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def family() -> str:
    override = os.environ.get("NYXURI_PKG_FAMILY", "").strip().lower()
    if override in (ARCH, FEDORA):
        return override
    fields = os_release()
    ids = {fields.get("ID", "").strip().lower()}
    ids.update(fields.get("ID_LIKE", "").strip().lower().split())
    ids.discard("")
    if ids & FEDORA_IDS:
        return FEDORA
    return ARCH


def native_manager() -> str:
    return "dnf" if family() == FEDORA else "pacman"


def supports_aur() -> bool:
    return family() != FEDORA


def needs_superuser_prefix() -> bool:
    return os.geteuid() != 0


def rename(name: str) -> str:
    if family() != FEDORA:
        return name
    return FEDORA_RENAMES.get(name, name)


def copr(name: str):
    if family() != FEDORA:
        return None
    return FEDORA_COPRS.get(name)


def version_argv(names) -> list:
    if family() == FEDORA:
        return ["rpm", "-q", "--qf", "%{NAME} %{VERSION}-%{RELEASE}\n", *names]
    return ["pacman", "-Q", *names]
