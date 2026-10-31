"""PluginTransaction — the kernel's only side-effect orchestration layer.

The star layering (plugin-model.md §2) freezes this module as the ONLY one
that composes registry + resolver + ledger with the deploy machinery, the
Vault and the ``plugin-changed`` event port. Every interface (CLI verb, TUI,
Shell settings) must route switch flips through :func:`plugin_on` /
:func:`plugin_off` — they are the single transaction path that lands
``state.json``.

Transaction shape (plugin-model.md §3)::

    resolve (resolver) → preflight (declared packages) → vault restore
    → atomic swap (deploy) → ledger five-field record → one event

Disable reverses it: reverse-dependency guard → vault archive → managed
wipe to a white living area → ledger record → event. Package management is
asymmetric (§7.1): ``off`` only reports the packages it leaves behind.

Runtime plugins (KM4, §6) are the third shape: ``runtime = true`` in the
manifest declares a payload-less existence — no living area, no vault
in/out, no wipe, empty ``files`` snapshot. The ledger record plus one
``plugin-changed`` event IS the whole transaction; the running host (the
Shell) reacts by unloading or loading the domain.

The event sink is injected via :func:`set_event_sink`; the kernel never
imports or subprocesses a delivery — naming and wiring it is the outer
layer's job. Without a subscriber events are no-ops.
"""

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from nyxuri.kernel import ledger, registry
from nyxuri.core import get_env, log_msg, remove_path
from nyxuri.deploy.atomic import CarryPolicy
from nyxuri.deploy.deploy import _phase_atomic_deployment, merge_deploy_plugin
from nyxuri.deploy.manifest import ModuleManifest, living_path
from nyxuri.deploy.forms import write_active_form
from nyxuri.kernel.resolver import resolve_order

STATE_SYNCED = "Synced"
STATE_DRIFTED = "Drifted"
STATE_GHOST = "Ghost"

EventSink = Callable[[str, str], None]
_event_sink: Optional[EventSink] = None


@dataclass(frozen=True)
class Step:
    """One plugin's transaction outcome; KM3 CLI turns these into prose."""

    plugin: str
    ok: bool
    detail: str = ""


# --- plugin-changed event port ----------------------------------------------


def set_event_sink(sink: Optional[EventSink]) -> None:
    """Inject the plugin-changed delivery (outer layer's job, e.g. Shell IPC)."""
    global _event_sink
    _event_sink = sink


def _emit(plugin_id: str, state: str) -> None:
    """Deliver one plugin-changed event; a failing sink never fails the plugin."""
    if _event_sink is None:
        return
    try:
        _event_sink(plugin_id, state)
    except Exception as exc:
        log_msg("WARN", f"plugin-changed sink failed for {plugin_id}: {exc}")


# --- shared helpers ---------------------------------------------------------


def vault_dir(plugin_id: str) -> Path:
    """Flat file-mirror archive root for one plugin (plugin-model.md §7.3)."""
    return get_env().state_dir / "vault" / plugin_id


def _plugin_dest(plugin_id: str, manifest: ModuleManifest) -> Path:
    return living_path(manifest, get_env().config_dir)


def _is_runtime(manifest: ModuleManifest) -> bool:
    """A payload-less plugin (manifest ``runtime = true``, plugin-model.md §6).

    Its existence is the ledger record plus the running host's reaction to
    the plugin-changed event — never files under ~/.config. The declaration
    is explicit: no scan of blueprint contents may silently turn a runtime
    plugin into a deployable one (or vice versa).
    """
    return manifest.runtime


def _is_packages_only(manifest: ModuleManifest) -> bool:
    """A plugin that only declares system packages, ships no living area.

    R0-2 catalog 并轨产物：根 catalog.toml 的「装但不部署」声明升格为
    manifest-only 插件目录。``on`` = 装包 + 落账（无生活区、无 Vault 进出），
    与 runtime 插件同形——区别仅在它有真实的包世界投影（deps 菜单/安装器）。
    """
    return (
        not manifest.runtime
        and not manifest.target
        and not manifest.merge
        and not manifest.is_deployable
    )


def _blueprint_rels(manifest: ModuleManifest) -> List[str]:
    """The plugin's payload file names (manifest.toml and hooks/ excluded).

    For merge plugins these names ARE ownership: whatever matches them in the
    shared living area is ours to withdraw, nothing else.
    """
    root = registry.plugin_dir(manifest.name)
    if root is None:
        return []
    out: List[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(root)
        if path.name == "manifest.toml" or "hooks" in rel.parts:
            continue
        out.append(rel.as_posix())
    return out


def _merge_managed_view(dest: Path, manifest: ModuleManifest) -> Dict[str, str]:
    """Hashes of blueprint-named files present in a merge plugin's shared area."""
    view: Dict[str, str] = {}
    if not dest.is_dir() or dest.is_symlink():
        return view
    for rel in _blueprint_rels(manifest):
        p = dest / rel
        if p.is_file() and not p.is_symlink():
            view[rel] = _hash_file(p)
    return view


def _enabled_set() -> set:
    return {uid for uid, rec in ledger.all_plugins().items() if rec.get("state") == "enabled"}


def _is_user_owned(rel: str, manifest: ModuleManifest) -> bool:
    """Dunder-protocol and manifest-preserve files belong to the user.

    A preserve entry may name a DIRECTORY (#139 field report): the whole
    tree is runtime-managed (e.g. fish/functions — Fisher's territory), so
    every path under it is user-owned by prefix.
    """
    if "__custom__" in rel:
        return True
    for entry in manifest.preserve:
        if rel == entry or rel.startswith(entry + "/"):
            return True
    return False


def carry_baselines(plugin_ids: List[str]) -> Dict[str, Optional[Dict[str, str]]]:
    """Ledger ``files`` maps for enabled plugins among ``plugin_ids`` (#139).

    The baseline is what the engine last laid: a dest file hashing equal to
    its baseline entry is untouched and follows the new template; anything
    else is the user's and is carried. Plugins without an enabled record map
    to None (Ghost — provenance unknown).
    """
    out: Dict[str, Optional[Dict[str, str]]] = {}
    for uid in plugin_ids:
        rec = ledger.get_plugin(uid)
        files = (rec or {}).get("files")
        out[uid] = dict(files) if rec and rec.get("state") == "enabled" and isinstance(files, dict) else None
    return out


def resnapshot_plugins(plugin_ids: List[str],
                     carried: Optional[Dict[str, Dict[str, str]]] = None) -> None:
    """Re-baseline ledger snapshots after an out-of-band deploy (update path).

    The ledger means "hashes of what the engine last laid". After an update
    the laid truth changed under the enabled records, so every deployed
    enabled plugin is re-recorded from its living area — minus the files the
    swap carried as user-owned. A carried file must never enter the
    snapshot: it would read as engine-laid and be clobbered by the next
    template change. Ownership only ever grows through ``on`` (adoption),
    never through an update.
    """
    carried = carried or {}
    for uid in plugin_ids:
        rec = ledger.get_plugin(uid)
        if not rec or rec.get("state") != "enabled":
            continue
        try:
            manifest = registry.load_plugin(uid)
        except KeyError:
            continue
        if _is_runtime(manifest) or manifest.merge:
            continue
        dest = _plugin_dest(uid, manifest)
        if not (dest.exists() or dest.is_symlink()):
            continue
        files = snapshot_files(dest, manifest)
        for rel in carried.get(uid, {}):
            files.pop(rel, None)
        ledger.set_plugin(
            uid,
            state="enabled",
            form=(rec.get("form") or "default"),
            files=files,
            vault=None,
        )


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_files(dest: Path, manifest: ModuleManifest) -> Dict[str, str]:
    """``{rel path: sha256}`` of managed files under dest (user-owned excluded).

    Symlinks are recorded as ``link:<target>`` — their identity is the link
    itself (e.g. a slot axis whose target encodes the active variant), not
    the linked content. The result feeds both the ledger ``files`` snapshot
    and the ``Drifted`` half of :func:`audit_plugins`.
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


def _active_form_name(plugin_id: str) -> str:
    from nyxuri.deploy.forms import read_active_form

    try:
        return read_active_form(plugin_id)
    except Exception:
        return "default"


# --- dependency plans (pure composition of registry + resolver) -------------


def _enable_closure(plugin_id: str) -> List[str]:
    """The plugin plus its transitive dependencies, dependency-first order."""
    graph = registry.dependency_graph()
    if plugin_id not in graph:
        raise KeyError(f"unknown plugin: {plugin_id}")
    wanted = set()
    stack = [plugin_id]
    while stack:
        cur = stack.pop()
        if cur in wanted:
            continue
        wanted.add(cur)
        stack.extend(graph.get(cur, ()))
    sub = {u: [d for d in graph[u] if d in wanted] for u in wanted}
    return resolve_order(sub)


def _disable_plan(plugin_id: str) -> List[str]:
    """The plugin plus its ENABLED transitive dependents, dependents-first.

    The target always comes last: flipping it off is only safe once
    everything that declares it as a dependency has been switched off.
    """
    graph = registry.dependency_graph()
    if plugin_id not in graph:
        raise KeyError(f"unknown plugin: {plugin_id}")
    reverse: Dict[str, set] = {}
    for u, deps in graph.items():
        for d in deps:
            reverse.setdefault(d, set()).add(u)
    enabled = _enabled_set()
    wanted = set()
    stack = [plugin_id]
    while stack:
        cur = stack.pop()
        if cur in wanted:
            continue
        wanted.add(cur)
        stack.extend(reverse.get(cur, ()))
    nodes = {plugin_id} | {u for u in wanted if u in enabled}
    sub = {u: [d for d in graph.get(u, ()) if d in nodes] for u in nodes}
    return list(reversed(resolve_order(sub)))


# --- read-only plans (disclosure only — writes go through the verbs) --------


def replay_enabled_hooks() -> List[Step]:
    """Re-run the on-side hooks of every ledger-enabled plugin.

    Deploy pipelines use this after a base deploy: hook products inside a
    living area re-enter that plugin's snapshot when the plugin is next switched,
    and side-domain effects (skins, renders) are replayed idempotently.
    Fresh machines with an empty ledger get a no-op — activation belongs to
    an explicit ``on``.
    """
    results: List[Step] = []
    for uid in sorted(_enabled_set()):
        try:
            manifest = registry.load_plugin(uid)
        except KeyError:
            continue
        if not manifest.post_install:
            continue
        ok = _run_plugin_hook(uid, manifest, manifest.post_install)
        results.append(Step(uid, ok, "hook-replayed" if ok else f"hook-failed: {manifest.post_install}"))
    return results


def plan_on(plugin_id: str) -> List[str]:
    """The enable closure (plugin plus dependencies, dependency-first).

    Disclosure input for the outer layers ("what would this switch turn on");
    computing it touches nothing and writes nothing.
    """
    return _enable_closure(plugin_id)


def plan_off(plugin_id: str) -> List[str]:
    """The disable plan: the plugin plus its ENABLED dependents (they first).

    Every member besides ``plugin_id`` is a dependent that would block the
    transaction unless the caller opts into ``cascade``.
    """
    return _disable_plan(plugin_id)


# --- vault in/out ------------------------------------------------------------


def _move_into_vault(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        remove_path(dst)
    shutil.move(str(src), str(dst))


def _vault_archive(plugin_id: str, dest: Path, manifest: ModuleManifest) -> List[str]:
    """Move user-owned files (Dunder + manifest preserve) into the Vault.

    The vault stays a flat directory mirror of the plugin's living area —
    no database, no compression (plugin-model.md §7.3). Returns archived
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
                _move_into_vault(src, vault_dir(plugin_id) / rel)
                moved.append(rel + "/")
            else:
                keep.append(name)
        dirs[:] = keep
        for name in sorted(files):
            if "__custom__" in name:
                src = Path(root) / name
                rel = src.relative_to(dest).as_posix()
                _move_into_vault(src, vault_dir(plugin_id) / rel)
                moved.append(rel)
    for rel in manifest.preserve:
        if not rel or os.path.isabs(rel):
            continue
        src = dest / rel
        if src.exists() or src.is_symlink():
            _move_into_vault(src, vault_dir(plugin_id) / rel)
            moved.append(rel)
    return moved


def _vault_restore(plugin_id: str, dest: Path) -> int:
    """Move archived user files back into the living area (Vault Out).

    Entries land in ``dest`` BEFORE the atomic swap so the Dunder walk and
    the manifest-preserve injection treat them like any living file. The
    archive is consumed (moved, not copied): a file the user deleted from
    the living area must not resurrect on the next enable.
    """
    vault = vault_dir(plugin_id)
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


def _wipe_plugin(plugin_id: str, dest: Path, rec: Optional[dict],
               manifest: ModuleManifest) -> List[str]:
    """Remove the plugin's managed files; return foreign survivors, if any.

    White-paper rule (plugin-model.md §1.2): a disabled plugin leaves nothing
    managed behind. Foreign files the user dropped in are never eaten —
    they survive and are reported (doctor flags the plugin Ghost).

    Merge plugins (shared living areas) never remove the directory itself:
    ownership = exactly the files the transaction laid (the ledger
    snapshot). Without a snapshot, ownership falls back to blueprint names:
    engine payload files are withdrawn, everything else survives and is
    reported — a pre-ledger (v3-era) dest never loses personal files to an
    ``off`` (#139).
    """
    if not (dest.exists() or dest.is_symlink()):
        return []
    if dest.is_file() or dest.is_symlink():
        # Single-file plugin (target=): the file is the whole living area.
        # A file outside the managed snapshot is user-owned (carried at
        # deploy, or dropped in) — never eaten (#139).
        if dest.name not in set((rec or {}).get("files") or {}):
            return [dest.name]
        remove_path(dest)
        return []
    if manifest.merge:
        managed = set((rec or {}).get("files") or {})
        for rel in sorted(managed):
            p = dest / rel
            if p.is_symlink() or p.is_file():
                p.unlink(missing_ok=True)
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
        _prune_empty_dirs(dest)
        if not any(dest.iterdir()):
            remove_path(dest)  # ours was the only content: dissolve the shell
        remaining = {
            p.relative_to(dest).as_posix()
            for p in dest.rglob("*")
            if p.is_file() or p.is_symlink()
        }
        return sorted(remaining - managed)
    if rec is None or not (rec.get("files") or {}):
        # No managed snapshot (never switched through the transaction, or
        # already-off): ownership falls back to blueprint names — engine-laid
        # payload files are withdrawn, anything else is the user's and
        # survives, reported as foreign (#139: a v3-era dest must not lose
        # personal files to an `off`).
        blueprint = set(_blueprint_rels(manifest))
        withdrawn: set = set()
        for p in list(dest.rglob("*")):
            if not (p.is_file() or p.is_symlink()):
                continue
            rel = p.relative_to(dest).as_posix()
            if rel in blueprint:
                p.unlink(missing_ok=True)
                withdrawn.add(rel)
        _prune_empty_dirs(dest)
        remaining: set = set()
        if dest.is_dir():
            if not any(dest.iterdir()):
                remove_path(dest)
            else:
                remaining = {
                    p.relative_to(dest).as_posix()
                    for p in dest.rglob("*")
                    if p.is_file() or p.is_symlink()
                }
        return sorted(remaining - withdrawn)
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


# --- plugin lifecycle hooks (declared side effects, plugin-owned) -----------------


def _hook_script(plugin_id: str, spec: str):
    """Resolve ``<blueprint>/<plugin>/hooks/<spec>``; None when absent/malformed."""
    if not spec or "/" in spec or spec.startswith("."):
        return None
    root = registry.plugin_dir(plugin_id)
    if root is None:
        return None
    script = root / "hooks" / spec
    return script if script.is_file() else None


def _run_plugin_hook(plugin_id: str, manifest: ModuleManifest, spec: str) -> bool:
    """Execute a declared plugin hook: ``<plugin>/hooks/<spec>`` in its blueprint.

    Hooks are the plugin's own behavior (KM3 contract, plugin-model.md §4) —
    executable files living in the blueprint, never kernel business code.
    The transaction injects identity context (``NYXURI_UNIT`` / ``_SRC`` /
    ``_DEST``) and never interprets the hook's internals; a failing hook
    degrades to WARN and the caller surfaces it in the step detail.
    """
    script = _hook_script(plugin_id, spec)
    if script is None:
        log_msg("WARN", f"plugin '{plugin_id}' declares a missing hook: {spec}")
        return False
    if not os.access(script, os.X_OK):
        log_msg("WARN", f"hook for '{plugin_id}' is not executable: {script}")
        return False
    import subprocess

    plugin_src = registry.plugin_dir(plugin_id)
    hook_env = {
        **os.environ,
        # Blueprint is source-absolute read-only: hooks importing engine code
        # must never drop __pycache__ into the source tree (P0 invariant).
        "PYTHONDONTWRITEBYTECODE": "1",
        "NYXURI_UNIT": plugin_id,
        "NYXURI_UNIT_SRC": str(plugin_src or ""),
        "NYXURI_UNIT_DEST": "" if _is_runtime(manifest) else str(_plugin_dest(plugin_id, manifest)),
    }
    root = Path(__import__("nyxuri").__file__).resolve().parent.parent
    hook_env["PYTHONPATH"] = str(root) + (
        os.pathsep + hook_env["PYTHONPATH"] if hook_env.get("PYTHONPATH") else ""
    )
    try:
        # Hooks own their runtime (network fetches, schema compilers) — no
        # timeout here; the hook itself is the declared plugin boundary.
        result = subprocess.run(
            [str(script)], env=hook_env, cwd=str(script.parent.parent), check=False
        )
        return result.returncode == 0
    except Exception as exc:
        log_msg("WARN", f"hook '{spec}' failed for '{plugin_id}': {exc}")
        return False


# --- the two verbs of the transaction path -----------------------------------


def plugin_on(
    plugin_id: str,
    *,
    form: Optional[str] = None,
    install_packages: Optional[Callable[[str, List[str]], bool]] = None,
) -> List[Step]:
    """Enable a plugin: resolve → preflight → vault out → swap → ledger → event.

    The dependency closure is enabled in resolver order; a plugin missing
    declared packages aborts the transaction with the missing list disclosed
    (nothing has been touched beyond earlier closure members). Installation
    itself is injected as ``installer(plugin_id, missing)`` — the outer layer
    owns the package-manager call (it also owns the manifest context needed
    to split repo / AUR / Flatpak names); the kernel never shells out.
    """
    plan = _enable_closure(plugin_id)
    enabled = _enabled_set()
    if plugin_id in enabled and form is None:
        return [Step(plugin_id, True, "already-enabled")]
    results: List[Step] = []
    for uid in plan:
        if uid in enabled and uid != plugin_id:
            continue
        manifest = registry.load_plugin(uid)
        missing = missing_packages(manifest)
        if missing:
            installed = False
            if install_packages is not None:
                try:
                    installed = bool(install_packages(uid, list(missing)))
                except Exception as exc:
                    log_msg("WARN", f"package installer failed for {uid}: {exc}")
            if not installed or missing_packages(manifest):
                results.append(Step(uid, False, "missing-packages: " + ", ".join(missing)))
                return results
        dest = _plugin_dest(uid, manifest)
        runtime = _is_runtime(manifest)
        packages_only = _is_packages_only(manifest)
        files: Dict[str, str] = {}
        carried_rels: List[str] = []
        if runtime or packages_only:
            # Runtime (§6) and packages-only (R0-2) plugins: no living area,
            # no vault, no deploy. The ledger record plus the event below is
            # the whole transaction.
            pass
        else:
            if not manifest.target and not manifest.merge:
                # Vault in/out is a directory-plugin affordance; a single-file
                # plugin's living area is one blueprint-managed file with no
                # user-owned layer to archive or restore, and a merge plugin's
                # shared area preserves user content in place (no-clobber).
                _vault_restore(uid, dest)
            if form is not None and uid == plugin_id and not manifest.merge and not packages_only:
                write_active_form(uid, form)
            if manifest.merge:
                laid = merge_deploy_plugin(uid, manifest)
                if laid is None:
                    results.append(Step(uid, False, "deploy-failed"))
                    return results
                files = {rel: _hash_file(dest / rel) for rel in laid}
            else:
                # `on` is adoption: the engine claims its payload names
                # (carry_unknown=False), user-placed extras are carried and
                # stay user-owned (#139). A previously-enabled record acts as
                # the drift baseline so a form switch never eats edits.
                rec = ledger.get_plugin(uid)
                baseline = None
                if rec and rec.get("state") == "enabled" and isinstance(rec.get("files"), dict):
                    baseline = dict(rec["files"])
                policy = CarryPolicy(
                    baselines={uid: baseline}, unknown=False, carried={uid: {}}
                )
                if uid in _phase_atomic_deployment([uid], carry_policy=policy):
                    results.append(Step(uid, False, "deploy-failed"))
                    return results
                files = snapshot_files(dest, manifest)
                # Carried files stay user-owned: they must never enter the
                # snapshot, or the next deploy would mistake them for
                # engine-laid content and clobber them. (Re-applied after the
                # hook below, which may lay further engine-owned products.)
                carried_rels = list(policy.carried.get(uid, {}))
        hook_note = ""
        if manifest.post_install:
            # Runs BEFORE the ledger snapshot: a hook that lands files inside
            # the plugin's own living area makes them transaction-managed, so
            # ``off`` wipes them through the normal white-paper path (KM3).
            if not _run_plugin_hook(uid, manifest, manifest.post_install):
                hook_note = f"; hook-failed: {manifest.post_install}"
        if not runtime and not packages_only and not manifest.merge:
            # Post-hook snapshot (hook products are engine-laid), minus the
            # files the swap carried as user-owned (#139).
            files = snapshot_files(dest, manifest)
            for rel in carried_rels:
                files.pop(rel, None)
        ledger.set_plugin(
            uid,
            state="enabled",
            form=_active_form_name(uid),
            # Merge plugins snapshot at deploy time (laid files only — the
            # shared area's other content is never ours); atomic plugins use
            # the post-hook snapshot minus carried user files (#139); runtime
            # and packages-only plugins keep the empty map (nothing on disk
            # is theirs).
            files=files,
            vault=None,
        )
        _emit(uid, "enabled")
        results.append(Step(uid, True, "enabled" + hook_note))
    return results


def plugin_off(plugin_id: str, *, cascade: bool = False) -> List[Step]:
    """Disable a plugin: guard → vault in → managed wipe → post_remove → ledger.

    Enabled dependents block the transaction unless ``cascade`` is set, in
    which case they are switched off first (dependents-first order). The
    report keeps the package asymmetry honest: declared packages stay on
    the machine, only the plugin's config presence is withdrawn. A declared
    ``post_remove`` hook cleans effects that live outside the living area
    (running after the wipe, before the ledger lands).
    """
    plan = _disable_plan(plugin_id)
    dependents = [uid for uid in plan if uid != plugin_id]
    if dependents and not cascade:
        return [
            Step(plugin_id, False, "blocked-by-enabled-dependents: " + ", ".join(dependents))
        ]
    results: List[Step] = []
    for uid in plan:
        rec = ledger.get_plugin(uid)
        manifest = registry.load_plugin(uid)
        dest = _plugin_dest(uid, manifest)
        runtime = _is_runtime(manifest)
        packages_only = _is_packages_only(manifest)
        if uid not in _enabled_set() and not (dest.exists() or dest.is_symlink()):
            results.append(Step(uid, True, "already-disabled"))
            continue
        # Runtime and packages-only plugins have no living area: nothing to
        # archive, nothing to wipe — disabling is landing the ledger record
        # and firing the event the running host reacts to (§6 / R0-2).
        archived = [] if (manifest.merge or runtime or packages_only) else _vault_archive(uid, dest, manifest)
        foreign = [] if (runtime or packages_only) else _wipe_plugin(uid, dest, rec, manifest)
        detail = "disabled"
        if manifest.post_remove and not _run_plugin_hook(uid, manifest, manifest.post_remove):
            detail += f"; hook-failed: {manifest.post_remove}"
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
        ledger.set_plugin(
            uid,
            state="disabled",
            form=(rec or {}).get("form") or "default",
            files={},
            # the archive path is named only when something was actually
            # archived (R0-2 amended rule: no phantom vault pointers)
            vault=str(vault_dir(uid)) if archived else None,
        )
        _emit(uid, "disabled")
        results.append(Step(uid, True, detail))
    return results


# --- doctor reconciliation (read-only) ---------------------------------------


def audit_plugins(plugin_id: Optional[str] = None) -> Dict[str, str]:
    """Reconcile declarations vs the living machine: ``Synced`` / ``Drifted``
    / ``Ghost`` per plugin (plugin-model.md §3). Read-only, never writes.

    Only plugins with something to reconcile are reported: a ledger record or
    living files. Never-switched white plugins are absent from the report.
    """
    known = registry.plugin_ids()
    if plugin_id is not None:
        if plugin_id not in known and plugin_id not in ledger.all_plugins():
            raise KeyError(f"unknown plugin: {plugin_id}")
        candidates = [plugin_id]
    else:
        candidates = sorted(set(known) | set(ledger.all_plugins()))
    report: Dict[str, str] = {}
    for uid in candidates:
        manifest = registry.load_plugin(uid)
        rec = ledger.get_plugin(uid)
        if _is_runtime(manifest) or _is_packages_only(manifest):
            # Nothing on disk belongs to a runtime or packages-only plugin —
            # the ledger record is the whole existence, so there is nothing
            # to drift or ghost.
            if rec is not None:
                report[uid] = STATE_SYNCED
            continue
        dest = _plugin_dest(uid, manifest)
        if rec is not None and rec.get("state") == "enabled":
            if manifest.merge:
                synced = _merge_managed_view(dest, manifest) == (rec.get("files") or {})
            else:
                # Per-record verdict (#139): a managed entry counts as synced
                # only when dest still hashes to it. Entries are judged one by
                # one so carried user files (deliberately outside the
                # snapshot) never masquerade as drift — a missing or tampered
                # managed file still does.
                snap = {} if dest.is_symlink() else snapshot_files(dest, manifest)
                synced = all(snap.get(rel) == h for rel, h in (rec.get("files") or {}).items())
            report[uid] = STATE_SYNCED if synced else STATE_DRIFTED
        elif manifest.merge:
            # Shared living area: the directory existing is the user's own
            # content, not residue. Only blueprint-named leftovers are Ghost.
            if _merge_managed_view(dest, manifest):
                report[uid] = STATE_GHOST
            elif rec is not None:
                report[uid] = STATE_SYNCED
        elif dest.exists() or dest.is_symlink():
            report[uid] = STATE_GHOST
        elif rec is not None:
            report[uid] = STATE_SYNCED
    return report


# (contract self-checks live in tests/test_transaction.py — the kernel
#  carries no test helpers of its own)
