"""Package catalog (``catalog.toml``) — declared software that ships no config.

Catalog entries are NOT units (unit-model.md §2 严正排除项): they carry no
deployable files and have no ledger life. The catalog exists so the deps
menu and the AUR ``optdepends`` generator read one declaration of
"installable but not deployable" software.

Bilingual display names live in ``translations.toml`` (``app_*`` keys);
the ``label`` here only feeds optdepends comments. Pure stdlib.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_CATALOG_NAME = "catalog.toml"


@dataclass(frozen=True)
class CatalogEntry:
    """One catalog row: a real-world package bundle with no config to deploy."""

    name: str
    label: str
    category: str = ""
    packages_repo: List[str] = field(default_factory=list)
    packages_aur: List[str] = field(default_factory=list)
    packages_flatpak: List[str] = field(default_factory=list)
    detect: str = ""  # empty at load time → first declared package, else the name
    platforms: dict = field(default_factory=dict)


def catalog_path() -> Path:
    """The repo's catalog.toml (ships next to the engine)."""
    from nyxuri.core import get_env

    return get_env().repo_dir / _CATALOG_NAME


def _as_list(value) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    return []


def _as_platforms_map(value) -> dict:
    """保留平台专属供给表，具体解释集中在包需求解析器。"""
    if not isinstance(value, dict):
        return {}
    return {
        name: details
        for name, details in value.items()
        if isinstance(name, str) and isinstance(details, dict)
    }


def catalog_entries() -> List[CatalogEntry]:
    """Every catalog entry, name-sorted for deterministic output."""
    path = catalog_path()
    if not path.is_file():
        return []
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    entries: List[CatalogEntry] = []
    for name in sorted(data):
        row = data[name]
        if not isinstance(row, dict):
            continue
        repo = _as_list(row.get("packages"))
        aur = _as_list(row.get("packages_aur"))
        detect = str(row.get("detect", ""))
        entries.append(CatalogEntry(
            name=name,
            label=str(row.get("label", name)),
            category=str(row.get("category", "")),
            packages_repo=repo,
            packages_aur=aur,
            packages_flatpak=_as_list(row.get("packages_flatpak")),
            detect=detect or ((repo + aur)[0] if (repo or aur) else name),
            platforms=_as_platforms_map(row.get("platforms")),
        ))
    return entries


def get_entry(name: str) -> Optional[CatalogEntry]:
    """One entry by name, or None."""
    for entry in catalog_entries():
        if entry.name == name:
            return entry
    return None
