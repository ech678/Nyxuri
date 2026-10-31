"""UnitRegistry — the blueprint domain's single entry (unit-model.md §2).

The only kernel module that scans unit blueprints and reads manifests.
Adding a unit = adding a directory (plus an optional ``manifest.toml``) —
zero kernel code change. TOML parsing is delegated to
``nyxuri.deploy.manifest`` (pure stdlib); state.json is never touched
here — that is ledger's monopoly.

Blueprint roots (KM4, unit-model.md §6)::

    plugins/       → bare ids          (kitty, niri, ...)
    shell/units/   → ``shell.`` ids    (shell.bar, shell.dock, ...)

The prefix comes from the ROOT, not from per-id special-casing: the kernel
only ever sees dotted ids and resolves them back through the same table.
Shell units declare ``runtime = true`` — a payload-less existence whose
living area is the running host, never files under ~/.config.
"""

from dataclasses import replace
from pathlib import Path

from nyxuri.core import get_env
from nyxuri.deploy.manifest import ModuleManifest, load_manifest

_METADATA_NAMES = frozenset({"__pycache__"})
SHELL_NAMESPACE = "shell."


def _namespace_roots() -> "list[tuple[Path, str]]":
    """Blueprint roots with their id prefixes; longest prefix wins lookup."""
    env = get_env()
    return [(env.units_src, ""), (env.shell_units_src, SHELL_NAMESPACE)]


def unit_ids() -> list[str]:
    """Sorted ids of every directory unit across all blueprint roots.

    A unit is a directory: ``plugins/<unit>/`` or ``shell/units/<domain>/``.
    Metadata entries are not units; the single-file degenerate
    (``starship.toml`` + sidecar) was physically deleted at KM1 ② and no
    longer exists.
    """
    out: list[str] = []
    for root, prefix in _namespace_roots():
        if not root.is_dir():
            continue
        out.extend(
            prefix + p.name
            for p in root.iterdir()
            if p.is_dir() and p.name not in _METADATA_NAMES
        )
    return sorted(out)


def unit_dir(unit_id: str) -> Path | None:
    """On-disk blueprint directory for a unit, or None if it does not exist.

    Prefixed namespaces are matched first; the bare ``plugins/`` root is the
    fallback. A dotted id under the bare root (``plugins/shell.bar/``) is not
    a unit — namespaces are declared by roots, never by directory names.
    """
    for root, prefix in sorted(_namespace_roots(), key=lambda r: len(r[1]), reverse=True):
        if not unit_id.startswith(prefix):
            continue
        rel = unit_id[len(prefix):]
        if not rel or "/" in rel:
            return None
        src = root / rel
        return src if src.is_dir() else None
    return None


def load_unit(unit_id: str) -> ModuleManifest:
    """Load one unit's resolved manifest; zero-config defaults applied.

    The manifest ``name`` is patched to the full dotted id — every downstream
    consumer (ledger key, vault path, reports) sees exactly the registry id.
    """
    src = unit_dir(unit_id)
    if src is None:
        raise KeyError(f"unknown unit: {unit_id}")
    manifest = load_manifest(src)
    if manifest.name != unit_id:
        manifest = replace(manifest, name=unit_id)
    return manifest


def dependency_graph() -> dict[str, list[str]]:
    """``{unit id: declared unit dependencies}`` for the whole blueprint.

    Feed this straight into ``nyxuri.resolver.resolve_order``; the two
    modules never import each other — the caller composes them.
    """
    return {uid: load_unit(uid).dependencies for uid in unit_ids()}
