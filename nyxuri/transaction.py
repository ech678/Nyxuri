"""UnitTransaction — the kernel's only side-effect orchestration layer.

The star layering (unit-model.md §2) freezes this module as the ONLY one
that composes registry + resolver + ledger with the deploy machinery, the
Vault and the ``unit-changed`` event port. Every interface (CLI verb, TUI,
Shell settings) must route switch flips through :func:`unit_on` /
:func:`unit_off` — they are the single transaction path that lands
``state.json``.

Transaction shape (unit-model.md §3)::

    resolve (resolver) → preflight (declared packages) → vault restore
    → atomic swap (deploy) → ledger five-field record → one event

Disable reverses it: reverse-dependency guard → vault archive → managed
wipe to a white living area → ledger record → event. Package management is
asymmetric (§7.1): ``off`` only reports the packages it leaves behind.

The event sink is injected via :func:`set_event_sink`; the kernel never
imports or subprocesses a delivery — naming and wiring it is the outer
layer's job. Without a subscriber events are no-ops.
"""

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, List, Optional

from nyxuri import ledger, registry
from nyxuri.core import get_env, log_msg, remove_path
from nyxuri.deploy.deploy import _phase_atomic_deployment
from nyxuri.deploy.manifest import ModuleManifest, load_manifest
from nyxuri.deploy.preset import write_active_preset
from nyxuri.resolver import resolve_order

STATE_SYNCED = "Synced"
STATE_DRIFTED = "Drifted"
STATE_GHOST = "Ghost"

EventSink = Callable[[str, str], None]
_event_sink: Optional[EventSink] = None


@dataclass(frozen=True)
class Step:
    """One unit's transaction outcome; KM3 CLI turns these into prose."""

    unit: str
    ok: bool
    detail: str = ""


# --- unit-changed event port ----------------------------------------------


def set_event_sink(sink: Optional[EventSink]) -> None:
    """Inject the unit-changed delivery (outer layer's job, e.g. Shell IPC)."""
    global _event_sink
    _event_sink = sink


def _emit(unit_id: str, state: str) -> None:
    """Deliver one unit-changed event; a failing sink never fails the unit."""
    if _event_sink is None:
        return
    try:
        _event_sink(unit_id, state)
    except Exception as exc:
        log_msg("WARN", f"unit-changed sink failed for {unit_id}: {exc}")


# --- shared helpers ---------------------------------------------------------


def vault_dir(unit_id: str) -> Path:
    """Flat file-mirror archive root for one unit (unit-model.md §7.3)."""
    return get_env().state_dir / "vault" / unit_id


def _unit_dest(unit_id: str, manifest: ModuleManifest) -> Path:
    return get_env().config_dir / (manifest.target or unit_id)


def _enabled_set() -> set:
    return {uid for uid, rec in ledger.all_units().items() if rec.get("state") == "enabled"}


def _is_user_owned(rel: str, manifest: ModuleManifest) -> bool:
    """Dunder-protocol and manifest-preserve files belong to the user."""
    return "__custom__" in rel or rel in set(manifest.preserve)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_files(dest: Path, manifest: ModuleManifest) -> Dict[str, str]:
    """``{rel path: sha256}`` of managed files under dest (user-owned excluded).

    Symlinks are recorded as ``link:<target>`` — their identity is the link
    itself (e.g. a parts slot whose target encodes the active variant), not
    the linked content. The result feeds both the ledger ``files`` snapshot
    and the ``Drifted`` half of :func:`audit_units`.
    """
    if dest.is_symlink():
        return {}
    if dest.is_file():
        if _is_user_owned(dest.name, manifest):
            return {}
        return {dest.name: _hash_file(dest)}
    out: Dict[str, str] = {}
    if not dest.is_dir():
        return out
    for root, dirs, files in os.walk(dest):
        for name in files:
            p = Path(root) / name
            rel = p.relative_to(dest).as_posix()
            if _is_user_owned(rel, manifest):
                continue
            out[rel] = "link:" + os.readlink(p) if p.is_symlink() else _hash_file(p)
    return out


def missing_packages(manifest: ModuleManifest) -> List[str]:
    """Declared system packages absent from the machine (repo+AUR via the
    pacman database, Flatpak via its app list). Empty = preflight green."""
    from nyxuri.pkg.detection import DependencyProbe

    probe = DependencyProbe()
    missing = [
        name
        for name in (*manifest.packages_repo, *manifest.packages_aur)
        if not probe.installed(name)
    ]
    missing.extend(app for app in manifest.packages_flatpak if app not in probe.flatpaks)
    return missing


def _active_preset_name(unit_id: str) -> str:
    from nyxuri.deploy.preset import read_active_preset

    try:
        return read_active_preset(unit_id)
    except Exception:
        return "default"


# --- dependency plans (pure composition of registry + resolver) -------------


def _enable_closure(unit_id: str) -> List[str]:
    """The unit plus its transitive dependencies, dependency-first order."""
    graph = registry.dependency_graph()
    if unit_id not in graph:
        raise KeyError(f"unknown unit: {unit_id}")
    wanted = set()
    stack = [unit_id]
    while stack:
        cur = stack.pop()
        if cur in wanted:
            continue
        wanted.add(cur)
        stack.extend(d for d in graph.get(cur, ()) if d in graph)
    sub = {u: [d for d in graph.get(u, ()) if d in wanted] for u in wanted}
    return resolve_order(sub)


def _disable_plan(unit_id: str) -> List[str]:
    """The unit plus its ENABLED transitive dependents, dependents-first.

    The target always comes last: flipping it off is only safe once
    everything that declares it as a dependency has been switched off.
    """
    graph = registry.dependency_graph()
    if unit_id not in graph:
        raise KeyError(f"unknown unit: {unit_id}")
    reverse: Dict[str, set] = {}
    for u, deps in graph.items():
        for d in deps:
            reverse.setdefault(d, set()).add(u)
    enabled = _enabled_set()
    wanted = set()
    stack = [unit_id]
    while stack:
        cur = stack.pop()
        if cur in wanted:
            continue
        wanted.add(cur)
        stack.extend(reverse.get(cur, ()))
    nodes = {unit_id} | {u for u in wanted if u in enabled}
    sub = {u: [d for d in graph.get(u, ()) if d in nodes] for u in nodes}
    return list(reversed(resolve_order(sub)))


# --- vault in/out ------------------------------------------------------------


def _move_into_vault(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        remove_path(dst)
    shutil.move(str(src), str(dst))


def _vault_archive(unit_id: str, dest: Path, manifest: ModuleManifest) -> List[str]:
    """Move user-owned files (Dunder + manifest preserve) into the Vault.

    The vault stays a flat directory mirror of the unit's living area —
    no database, no compression (unit-model.md §7.3). Returns archived
    relative paths (``/``-suffixed for directories).
    """
    moved: List[str] = []
    if not (dest.is_dir() and not dest.is_symlink()):
        return moved
    for root, dirs, files in os.walk(dest):
        keep = []
        for name in sorted(dirs):
            if "__custom__" in name:
                src = Path(root) / name
                rel = src.relative_to(dest).as_posix()
                _move_into_vault(src, vault_dir(unit_id) / rel)
                moved.append(rel + "/")
            else:
                keep.append(name)
        dirs[:] = keep
        for name in sorted(files):
            if "__custom__" in name:
                src = Path(root) / name
                rel = src.relative_to(dest).as_posix()
                _move_into_vault(src, vault_dir(unit_id) / rel)
                moved.append(rel)
    for rel in manifest.preserve:
        if not rel or os.path.isabs(rel) or ".." in PurePosixPath(rel.replace("\\", "/")).parts:
            continue
        src = dest / rel
        if src.exists() or src.is_symlink():
            _move_into_vault(src, vault_dir(unit_id) / rel)
            moved.append(rel)
    return moved


def _vault_restore(unit_id: str, dest: Path) -> int:
    """Move archived user files back into the living area (Vault Out).

    Entries land in ``dest`` BEFORE the atomic swap so the Dunder walk and
    the manifest-preserve injection treat them like any living file. The
    archive is consumed (moved, not copied): a file the user deleted from
    the living area must not resurrect on the next enable.
    """
    vault = vault_dir(unit_id)
    if not vault.is_dir():
        return 0
    count = 0
    dest.mkdir(parents=True, exist_ok=True)
    for entry in sorted(vault.iterdir()):
        target = dest / entry.name
        if target.exists() or target.is_symlink():
            remove_path(target)
        shutil.move(str(entry), str(target))
        count += 1
    if vault.is_dir() and not any(vault.iterdir()):
        vault.rmdir()
    return count


# --- the living-area wipe ----------------------------------------------------


def _prune_empty_dirs(root: Path) -> None:
    for dirpath, _dirs, _files in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        try:
            p.rmdir()  # succeeds only when empty
        except OSError:
            pass


def _wipe_unit(unit_id: str, dest: Path, rec: Optional[dict]) -> List[str]:
    """Remove the unit's managed files; return foreign survivors, if any.

    White-paper rule (unit-model.md §1.2): a disabled unit leaves nothing
    managed behind. Foreign files the user dropped in are never eaten —
    they survive and are reported (doctor flags the unit Ghost).
    """
    if not (dest.exists() or dest.is_symlink()):
        return []
    if dest.is_file() or dest.is_symlink():
        # Single-file unit (target=): the file is the whole living area.
        remove_path(dest)
        return []
    if rec is None or not (rec.get("files") or {}):
        # No managed snapshot (never switched through the transaction, or
        # already-off): blueprint ownership of the whole target applies.
        remove_path(dest)
        return []
    managed = set(rec["files"])
    remaining = {
        p.relative_to(dest).as_posix()
        for p in dest.rglob("*")
        if p.is_file() or p.is_symlink()
    }
    for rel in sorted(managed):
        p = dest / rel
        if p.is_symlink() or p.is_file():
            p.unlink(missing_ok=True)
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    _prune_empty_dirs(dest)
    if not any(dest.iterdir()):
        remove_path(dest)  # white paper: no empty skeleton left behind
    return sorted(remaining - managed)


# --- the two verbs of the transaction path -----------------------------------


def unit_on(
    unit_id: str,
    *,
    preset: Optional[str] = None,
    install_packages: Optional[Callable[[List[str]], bool]] = None,
) -> List[Step]:
    """Enable a unit: resolve → preflight → vault out → swap → ledger → event.

    The dependency closure is enabled in resolver order; a unit missing
    declared packages aborts the transaction with the missing list disclosed
    (nothing has been touched beyond earlier closure members). Installation
    itself is injected — the kernel never shells out to a package manager.
    """
    plan = _enable_closure(unit_id)
    enabled = _enabled_set()
    if unit_id in enabled and preset is None:
        return [Step(unit_id, True, "already-enabled")]
    results: List[Step] = []
    for uid in plan:
        if uid in enabled and uid != unit_id:
            continue
        manifest = registry.load_unit(uid)
        missing = missing_packages(manifest)
        if missing:
            installed = False
            if install_packages is not None:
                try:
                    installed = bool(install_packages(list(missing)))
                except Exception as exc:
                    log_msg("WARN", f"package installer failed for {uid}: {exc}")
            if not installed or missing_packages(manifest):
                results.append(Step(uid, False, "missing-packages: " + ", ".join(missing)))
                return results
        dest = _unit_dest(uid, manifest)
        if not manifest.target:
            # Vault in/out is a directory-unit affordance; a single-file
            # unit's living area is one blueprint-managed file with no
            # user-owned layer to archive or restore.
            _vault_restore(uid, dest)
        if uid in _phase_atomic_deployment([uid]):
            results.append(Step(uid, False, "deploy-failed"))
            return results
        if preset is not None and uid == unit_id:
            write_active_preset(uid, preset)
        ledger.set_unit(
            uid,
            state="enabled",
            preset=_active_preset_name(uid),
            files=snapshot_files(dest, manifest),
            vault=None,
        )
        _emit(uid, "enabled")
        if manifest.post_install:
            from nyxuri.deps import _run_post_install_hook

            _run_post_install_hook(manifest.post_install)
        results.append(Step(uid, True, "enabled"))
    return results


def unit_off(unit_id: str, *, cascade: bool = False) -> List[Step]:
    """Disable a unit: guard → vault in → managed wipe → ledger → event.

    Enabled dependents block the transaction unless ``cascade`` is set, in
    which case they are switched off first (dependents-first order). The
    report keeps the package asymmetry honest: declared packages stay on
    the machine, only the unit's config presence is withdrawn.
    """
    plan = _disable_plan(unit_id)
    dependents = [uid for uid in plan if uid != unit_id]
    if dependents and not cascade:
        return [
            Step(unit_id, False, "blocked-by-enabled-dependents: " + ", ".join(dependents))
        ]
    results: List[Step] = []
    for uid in plan:
        rec = ledger.get_unit(uid)
        manifest = registry.load_unit(uid)
        dest = _unit_dest(uid, manifest)
        if uid not in _enabled_set() and not (dest.exists() or dest.is_symlink()):
            results.append(Step(uid, True, "already-disabled"))
            continue
        archived = _vault_archive(uid, dest, manifest)
        foreign = _wipe_unit(uid, dest, rec)
        detail = "disabled"
        if archived:
            detail += f"; archived: {len(archived)}"
        if foreign:
            detail += "; foreign-left: " + ", ".join(foreign)
        pkgs = (
            *manifest.packages_repo,
            *manifest.packages_aur,
            *manifest.packages_flatpak,
        )
        if pkgs:
            detail += "; packages-left: " + ", ".join(pkgs)
        ledger.set_unit(
            uid,
            state="disabled",
            preset=(rec or {}).get("preset") or "default",
            files={},
            vault=str(vault_dir(uid)),
        )
        _emit(uid, "disabled")
        results.append(Step(uid, True, detail))
    return results


# --- doctor reconciliation (read-only) ---------------------------------------


def audit_units(unit_id: Optional[str] = None) -> Dict[str, str]:
    """Reconcile declarations vs the living machine: ``Synced`` / ``Drifted``
    / ``Ghost`` per unit (unit-model.md §3). Read-only, never writes.

    Only units with something to reconcile are reported: a ledger record or
    living files. Never-switched white units are absent from the report.
    """
    known = registry.unit_ids()
    if unit_id is not None:
        if unit_id not in known and unit_id not in ledger.all_units():
            raise KeyError(f"unknown unit: {unit_id}")
        candidates = [unit_id]
    else:
        candidates = sorted(set(known) | set(ledger.all_units()))
    report: Dict[str, str] = {}
    for uid in candidates:
        manifest = load_manifest(get_env().configs_src / uid)
        dest = _unit_dest(uid, manifest)
        rec = ledger.get_unit(uid)
        if rec is not None and rec.get("state") == "enabled":
            if not dest.is_symlink() and snapshot_files(dest, manifest) == (rec.get("files") or {}):
                report[uid] = STATE_SYNCED
            else:
                report[uid] = STATE_DRIFTED
        elif dest.exists() or dest.is_symlink():
            report[uid] = STATE_GHOST
        elif rec is not None:
            report[uid] = STATE_SYNCED
    return report


# (contract self-checks live in tests/test_transaction.py — the kernel
#  carries no test helpers of its own)
