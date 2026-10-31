"""统一编排单元启用、刷新与撤回，并保存可重试的部署阶段。

持有账本锁后先检查预设、平台和依赖，再备份冲突、逐文件恢复 Vault、提交
配置与部署基线。关键钩子或重载失败保留 pending，不能当作 already-enabled。
停用依据历史目标和最后部署哈希归档修改，仅撤回有归属证据的路径。
目录、单文件、共享目录共用保护规则；runtime 单元只拥有状态与事件。
"""

import hashlib
from functools import wraps
from dataclasses import replace
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from nyxuri.kernel import ledger, registry
from nyxuri.core import get_env, log_msg, remove_path
from nyxuri.deploy.atomic import (CarryPolicy, _path_identity, _deploy_ignore_factory,
                                  _base_deploy_ignore_factory)
from nyxuri.deploy.deploy import _phase_atomic_deployment, merge_deploy_unit
from nyxuri.deploy.manifest import ModuleManifest, living_path
from nyxuri.deploy.preset import write_active_preset
from nyxuri.deploy.templates import _phase_render_templates, prepare_screenshot_directory
from nyxuri.kernel.resolver import resolve_order

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
    status: str = ""
    conflicts: tuple[str, ...] = ()
    backup: str = ""


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
    return living_path(manifest, get_env().config_dir)


def _is_runtime(manifest: ModuleManifest) -> bool:
    """A payload-less unit (manifest ``runtime = true``, unit-model.md §6).

    Its existence is the ledger record plus the running host's reaction to
    the unit-changed event — never files under ~/.config. The declaration
    is explicit: no scan of blueprint contents may silently turn a runtime
    unit into a deployable one (or vice versa).
    """
    return manifest.runtime


def _blueprint_rels(manifest: ModuleManifest) -> List[str]:
    """The unit's payload file names (manifest.toml and hooks/ excluded).

    For merge units these names ARE ownership: whatever matches them in the
    shared living area is ours to withdraw, nothing else.
    """
    root = registry.unit_dir(manifest.name)
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
    """Hashes of blueprint-named files present in a merge unit's shared area."""
    view: Dict[str, str] = {}
    if not dest.is_dir() or dest.is_symlink():
        return view
    for rel in _blueprint_rels(manifest):
        p = dest / rel
        if p.is_file() and not p.is_symlink():
            view[rel] = _hash_file(p)
    return view


def _enabled_set() -> set:
    return {uid for uid, rec in ledger.all_units().items() if rec.get("state") == "enabled"}


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


def carry_baselines(unit_ids: List[str]) -> Dict[str, Optional[Dict[str, str]]]:
    """Ledger ``files`` maps for enabled units among ``unit_ids`` (#139).

    The baseline is what the engine last laid: a dest file hashing equal to
    its baseline entry is untouched and follows the new template; anything
    else is the user's and is carried. Units without an enabled record map
    to None (Ghost — provenance unknown).
    """
    out: Dict[str, Optional[Dict[str, str]]] = {}
    for uid in unit_ids:
        rec = ledger.get_unit(uid)
        files = (rec or {}).get("files")
        out[uid] = dict(files) if rec and rec.get("state") == "enabled" and isinstance(files, dict) else None
    return out


def resnapshot_units(unit_ids: List[str],
                     carried: Optional[Dict[str, Dict[str, str]]] = None) -> None:
    """兼容旧部署入口的基线提交；新入口应直接调用 unit_refresh。

    本次真正写入的路径记录新哈希。carry 中原先已登记的路径继续保存旧哈希，
    外来路径不入账；不能删除历史归属或把个人版本重新解释为引擎输出。
    """
    carried = carried or {}
    for uid in unit_ids:
        rec = ledger.get_unit(uid)
        if not rec or rec.get("state") != "enabled":
            continue
        try:
            manifest = registry.load_unit(uid)
        except KeyError:
            continue
        if _is_runtime(manifest) or manifest.merge:
            continue
        dest = _unit_dest(uid, manifest)
        if not (dest.exists() or dest.is_symlink()):
            continue
        files = snapshot_files(dest, manifest)
        for rel in carried.get(uid, {}):
            if rel in rec["files"]:
                files[rel] = rec["files"][rel]
            else:
                files.pop(rel, None)
        ledger.set_unit(
            uid,
            state="enabled",
            preset=(rec.get("preset") or "default"),
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
    """枚举生活区普通文件身份，Custom 与 preserve 除外。

    软链记录 link:<目标>，不读取链接内容；零件的 preserve 目标由实际零件事务
    单独加入基线，避免将本次没有写入的个人内容误记为受管结果。
    """
    if dest.is_symlink():
        return {}
    return {rel: _path_identity(path) for rel, path in _leaves(dest)
            if not _is_user_owned(rel, manifest)}


def missing_packages(manifest: ModuleManifest) -> List[str]:
    """列出当前平台缺失的包和手动资源，不混入其他发行版包名。

    平台支持状态由 unit_on 单独检查；空缺失列表不能替代支持声明。
    包数据库与实际命令/资源探测共用 DependencyProbe。
    """
    from nyxuri.pkg.detection import DependencyProbe
    from nyxuri.pkg.requirements import resolve_requirements

    requirements = resolve_requirements(manifest)
    probe = DependencyProbe()
    missing = [
        name
        for name in (*requirements.packages_repo, *requirements.packages_aur, *requirements.manual)
        if not probe.installed(name)
    ]
    missing.extend(app for app in requirements.packages_flatpak if app not in probe.flatpaks)
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
        stack.extend(graph.get(cur, ()))
    sub = {u: [d for d in graph[u] if d in wanted] for u in wanted}
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


# --- read-only plans (disclosure only — writes go through the verbs) --------


def replay_enabled_hooks() -> List[Step]:
    """Re-run the on-side hooks of every ledger-enabled unit.

    Deploy pipelines use this after a base deploy: hook products inside a
    living area re-enter that unit's snapshot when the unit is next switched,
    and side-domain effects (skins, renders) are replayed idempotently.
    Fresh machines with an empty ledger get a no-op — activation belongs to
    an explicit ``on``.
    """
    results: List[Step] = []
    for uid in sorted(_enabled_set()):
        try:
            manifest = registry.load_unit(uid)
        except KeyError:
            continue
        if not manifest.post_install:
            continue
        ok = _run_unit_hook(uid, manifest, manifest.post_install)
        results.append(Step(uid, ok, "hook-replayed" if ok else f"hook-failed: {manifest.post_install}"))
    return results


def plan_on(unit_id: str) -> List[str]:
    """The enable closure (unit plus dependencies, dependency-first).

    Disclosure input for the outer layers ("what would this switch turn on");
    computing it touches nothing and writes nothing.
    """
    return _enable_closure(unit_id)


def plan_off(unit_id: str) -> List[str]:
    """The disable plan: the unit plus its ENABLED dependents (they first).

    Every member besides ``unit_id`` is a dependent that would block the
    transaction unless the caller opts into ``cascade``.
    """
    if unit_id not in registry.unit_ids() and ledger.get_unit(unit_id) is not None:
        return [unit_id]
    return _disable_plan(unit_id)


# --- vault in/out ------------------------------------------------------------


def _safe_leaf(root: Path, rel: str, *, single: bool = False) -> Path:
    """仅允许记录中的相对叶节点，拒绝经父目录软链逃逸到其他目录。"""
    if root.is_symlink() and not single:
        raise ValueError(f"Symlink deployment root: {root}")
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError(f"Unsafe managed path: {rel}")
    path = root if single else root / rel
    boundary = root.parent if single else root
    if not path.parent.resolve().is_relative_to(boundary.resolve()):
        raise ValueError(f"Managed path escapes target: {path}")
    return path


def _leaves(root: Path):
    """逐文件枚举，软链作为叶节点处理，不沿软链递归。"""
    if root.is_symlink() or root.is_file():
        yield root.name, root
    elif root.is_dir():
        for base, dirs, files in os.walk(root):
            for name in list(dirs):
                path = Path(base) / name
                if path.is_symlink():
                    dirs.remove(name)
                    yield path.relative_to(root).as_posix(), path
            for name in files:
                path = Path(base) / name
                yield path.relative_to(root).as_posix(), path


def _copy_leaf(src: Path, dst: Path) -> None:
    """复制归档叶节点；已有目标必须由调用方先保全或确认相同。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        dst.symlink_to(os.readlink(src))
    else:
        shutil.copy2(src, dst)


def _vault_archive(unit_id: str, dest: Path, manifest: ModuleManifest,
                   rec: Optional[dict] = None) -> List[str]:
    """只归档有来源记录的保留文件和普通修改，全部复制成功后才撤回原件。

    preserve/Custom 只声明更新时保留，不能证明路径由 Nyxuri 创建。受保护路径
    使用独立来源集合，不计算漂移哈希；既有个人插件等未知内容始终留在生效区。
    """
    baseline = (rec or {}).get("files", {})
    protected = set(ledger.get_deployment(unit_id).get("protected_paths", []))
    selected = [(rel, path) for rel, path in _leaves(dest)
                if (rel in protected or rel in baseline) and _is_user_owned(rel, manifest)
                or (rel in baseline and _path_identity(path) != baseline[rel])]
    vault = vault_dir(unit_id)
    # 冲突版本集中保存在状态域；绝不覆盖保险库里尚未恢复的旧内容。
    for rel, src in selected:
        dst = _safe_leaf(vault, rel)
        if dst.exists() or dst.is_symlink():
            if _path_identity(dst) == _path_identity(src):
                continue
            backup_conflicts(unit_id, [rel])
            raise ValueError(f"Vault conflict: {rel}")
        _copy_leaf(src, dst)
    for _, src in selected:
        src.unlink()
    return [rel for rel, _ in selected]


def _vault_restore(unit_id: str, dest: Path, *, single: bool = False,
                   excluded: Optional[set[str]] = None) -> int:
    """逐文件恢复；现有同级目录保留，冲突双方保全后保留生效区版本。"""
    vault = vault_dir(unit_id)
    if not vault.is_dir():
        return 0
    entries = [(rel, src) for rel, src in _leaves(vault) if rel not in (excluded or set())]
    for rel, src in entries:
        target = _safe_leaf(dest, rel, single=single)
        if target.exists() or target.is_symlink():
            if _path_identity(target) != _path_identity(src):
                backup_conflicts(unit_id, [rel])
                continue
            src.unlink()
        else:
            _copy_leaf(src, target)
            src.unlink()
    _prune_empty_dirs(vault)
    if not any(vault.iterdir()):
        vault.rmdir()
    return len(entries)


def _prune_empty_dirs(root: Path) -> None:
    for dirpath, _dirs, _files in os.walk(root, topdown=False):
        if Path(dirpath) != root:
            try:
                Path(dirpath).rmdir()
            except OSError:
                pass


def _wipe_unit(unit_id: str, dest: Path, rec: Optional[dict],
               manifest: ModuleManifest) -> List[str]:
    """只撤回账本确认的路径；没有归属证据时所有文件保留并报告。"""
    managed = (rec or {}).get("files", {})
    single = bool(manifest.target and not manifest.merge)
    for rel in managed:
        path = _safe_leaf(dest, rel, single=single)
        if path.is_file() or path.is_symlink():
            path.unlink()
    if dest.is_dir() and not dest.is_symlink():
        _prune_empty_dirs(dest)
        if not any(dest.iterdir()):
            dest.rmdir()
    return sorted(rel for rel, _ in _leaves(dest))


# --- unit lifecycle hooks (declared side effects, unit-owned) -----------------


def _hook_script(unit_id: str, spec: str):
    """Resolve ``<blueprint>/<unit>/hooks/<spec>``; None when absent/malformed."""
    if not spec or "/" in spec or spec.startswith("."):
        return None
    root = registry.unit_dir(unit_id)
    if root is None:
        return None
    script = root / "hooks" / spec
    return script if script.is_file() else None


def _run_unit_hook(unit_id: str, manifest: ModuleManifest, spec: str, *, force: bool = False) -> bool:
    """运行单元声明的可执行钩子，返回真实退出状态供事务保留 pending。

    上下文提供单元 ID、源码和目标路径，禁写源码字节码；NYXURI_FORCE 只在
    调用方已经完成强制备份后置为 1。钩子自行负责已声明的外部产物归属。
    """
    script = _hook_script(unit_id, spec)
    if script is None:
        log_msg("WARN", f"unit '{unit_id}' declares a missing hook: {spec}")
        return False
    if not os.access(script, os.X_OK):
        log_msg("WARN", f"hook for '{unit_id}' is not executable: {script}")
        return False
    import subprocess

    unit_src = registry.unit_dir(unit_id)
    hook_env = {
        **os.environ,
        # Blueprint is source-absolute read-only: hooks importing engine code
        # must never drop __pycache__ into the source tree (P0 invariant).
        "PYTHONDONTWRITEBYTECODE": "1",
        "NYXURI_UNIT": unit_id,
        "NYXURI_FORCE": "1" if force else "0",
        "NYXURI_UNIT_SRC": str(unit_src or ""),
        "NYXURI_UNIT_DEST": "" if _is_runtime(manifest) else str(_unit_dest(unit_id, manifest)),
    }
    root = Path(__import__("nyxuri").__file__).resolve().parent.parent
    hook_env["PYTHONPATH"] = str(root) + (
        os.pathsep + hook_env["PYTHONPATH"] if hook_env.get("PYTHONPATH") else ""
    )
    try:
        # Hooks own their runtime (network fetches, schema compilers) — no
        # timeout here; the hook itself is the declared unit boundary.
        result = subprocess.run(
            [str(script)], env=hook_env, cwd=str(script.parent.parent), check=False
        )
        return result.returncode == 0
    except Exception as exc:
        log_msg("WARN", f"hook '{spec}' failed for '{unit_id}': {exc}")
        return False


# --- the two verbs of the transaction path -----------------------------------


def _guarded(operation):
    """所有文件动作共享账本锁；失败留下明确结果供 CLI、TUI 重试。"""
    @wraps(operation)
    def guarded(unit_id, *args, **kwargs):
        try:
            # 显式预设先做纯读取检查，连账本锁文件也不必为无效输入创建。
            if operation.__name__ == "unit_on" and kwargs.get("preset") is not None:
                _source_for(unit_id, registry.load_unit(unit_id), kwargs["preset"])
            with ledger.mutation_lock():
                return operation(unit_id, *args, **kwargs)
        except (ledger.LedgerError, OSError, ValueError, RuntimeError) as exc:
            try:
                pending = ledger.get_deployment(unit_id).get("pending")
            except ledger.LedgerError:
                pending = None
            return [Step(unit_id, False, str(exc), status="partial" if pending else "failed")]
    return guarded


def _metadata(manifest: ModuleManifest, dest: Path) -> dict:
    """保存实际落地点与形状，未来源码删除或 target 改动仍可安全撤回。"""
    return dict(target=str(dest), shape=("runtime" if manifest.runtime else
                "merge" if manifest.merge else "file" if manifest.target else "directory"),
                preserve=list(manifest.preserve), pending=None)


def _historical_manifest(uid: str, rec: Optional[dict]):
    """用历史目标撤回；旧记录仍借助现有蓝图，但不猜测消失单元的路径。"""
    meta = ledger.get_deployment(uid)
    try:
        manifest = registry.load_unit(uid)
    except KeyError:
        if not meta:
            raise ValueError(f"Orphan has no deployment target: {uid}")
        manifest = ModuleManifest(uid, [], [], [], [], {}, [], uid, "", uid, [], False)
    dest = _unit_dest(uid, manifest)
    if not meta and rec and manifest.legacy_targets:
        meta = _legacy_metadata(uid, manifest, rec, {}) or {}
    if meta:
        dest = Path(meta["target"])
        if not dest.is_absolute() or dest == get_env().home or not dest.parent.resolve().is_relative_to(get_env().home.resolve()):
            raise ValueError(f"Unsafe historical target: {dest}")
        shape = meta["shape"]
        manifest = replace(manifest, preserve=meta.get("preserve", []),
                           merge=shape == "merge", runtime=shape == "runtime",
                           target=(str(dest) if shape in ("file", "merge") else ""))
    return manifest, dest


def _legacy_metadata(uid: str, manifest: ModuleManifest, rec: dict, meta: dict) -> Optional[dict]:
    """识别已声明的旧布局；五字段旧账本只使用明确的历史默认值。

    没有账本的旧目录仍是未知用户内容。已保存的动态 Pictures 目标可随用户
    图片目录设置改变而迁移；其他目标或形状变化必须与 legacy_targets 匹配。
    """
    if not rec:
        return None
    current = _metadata(manifest, _unit_dest(uid, manifest))
    if meta and meta.get("target") == current["target"] and meta.get("shape") == current["shape"]:
        return None
    declared = []
    for target, shape in manifest.legacy_targets.items():
        old = replace(manifest, target=target)
        declared.append(dict(target=str(_unit_dest(uid, old)), shape=shape,
                             preserve=list(manifest.preserve), pending=None))
    if meta:
        if any(meta.get("target") == old["target"] and meta.get("shape") == old["shape"] for old in declared):
            return meta
        if manifest.target.startswith("@pictures/") and meta.get("shape") == "merge":
            return meta
        return None
    if len(declared) == 1:
        return declared[0]
    return None


def _migration_entries(uid: str, manifest: ModuleManifest, rec: dict, oldmeta: dict):
    """选择有归属证据及保留协议覆盖的旧文件，并合入尚未恢复的 Vault。"""
    old = Path(oldmeta["target"])
    if old.is_symlink() or not old.parent.resolve().is_relative_to(get_env().home.resolve()):
        raise ValueError(f"Unsafe migration target: {old}")
    baseline = {**oldmeta.get("archived_baselines", {}), **rec.get("files", {})}
    entries = {rel: path for rel, path in _leaves(old)
               if rel in baseline or _is_user_owned(rel, manifest)}
    # 同名 Vault 版本保留在保险库；生效区版本优先，后续恢复会明确报告冲突。
    for rel, path in _leaves(vault_dir(uid)):
        entries.setdefault(rel, path)
    return entries


def _migration_conflicts(uid: str, manifest: ModuleManifest, rec: dict, oldmeta: dict) -> List[str]:
    dest = _unit_dest(uid, manifest)
    conflicts = []
    for rel, source in _migration_entries(uid, manifest, rec, oldmeta).items():
        target = _safe_leaf(dest, rel)
        if target == source:
            continue
        if (target.exists() or target.is_symlink()) and _path_identity(target) != _path_identity(source):
            conflicts.append(rel)
    return sorted(conflicts)


def _migrate_layout(uid: str, manifest: ModuleManifest, rec: dict, oldmeta: dict,
                    *, force: bool = False):
    """先备份旧区、新区、账本与 Vault，再逐文件复制并验证，最后撤回旧件。

    pending=migration 始终保留旧目标，off 拒绝执行；复制阶段中断后可重复运行。
    所有新件验证成功前不删除任何旧件。删除阶段中断用迁移身份补验已落地文件，
    不能把部分迁移误判为完整启用。force 仅解决迁移目的地冲突，不丢弃旧修改。
    """
    from nyxuri.state.backup import backup_configs
    from nyxuri.deploy.atomic import atomic_replace_item
    old, dest = Path(oldmeta["target"]), _unit_dest(uid, manifest)
    entries = _migration_entries(uid, manifest, rec, oldmeta)
    conflicts = _migration_conflicts(uid, manifest, rec, oldmeta)
    backup = backup_configs(note=f"Before layout migration {uid}", interactive=False,
                            extra_paths=[old, dest, vault_dir(uid)])
    if backup is None:
        raise OSError(f"Migration backup failed: {uid}")
    previous = oldmeta.get("migration", {}) or {}
    identities = {**previous.get("files", {}), **{rel: _path_identity(path) for rel, path in entries.items()}}
    ledger.set_deployment(uid, **{**oldmeta, "pending": "migration",
        "migration": {"target": str(dest), "shape": _metadata(manifest, dest)["shape"],
                      "files": identities, "backup": str(backup)}})
    if conflicts and not force:
        return str(backup), conflicts, False
    for rel, source in entries.items():
        target = _safe_leaf(dest, rel)
        if target != source and _path_identity(target) != identities[rel]:
            if not atomic_replace_item(source, target):
                raise OSError(f"Migration copy failed: {rel}")
    for rel, digest in identities.items():
        if _path_identity(_safe_leaf(dest, rel)) != digest:
            raise OSError(f"Migration verification failed: {rel}")
    for rel, source in entries.items():
        if source != _safe_leaf(dest, rel):
            source.unlink()
    if old != dest and old.is_dir():
        _prune_empty_dirs(old)
        if not any(old.iterdir()):
            old.rmdir()
    ledger.set_deployment(uid, **{**_metadata(manifest, dest), "migration": None,
                                  "pending": "deploy"})
    return str(backup), conflicts, True


def _excluded_payload(manifest: ModuleManifest) -> set[str]:
    """按全部已启用单元与平台支持决定条件文件，不读取当前桌面会话。"""
    from nyxuri.pkg.requirements import resolve_requirements
    enabled = _enabled_set()
    excluded = set(manifest.retired_files)
    for rel, required in manifest.when_units.items():
        for uid in required:
            if uid not in enabled:
                excluded.add(rel)
                break
            try:
                supported = resolve_requirements(registry.load_unit(uid)).supported
            except KeyError:
                supported = False
            if not supported:
                excluded.add(rel)
                break
    return excluded


def _retire_payload(uid: str, manifest: ModuleManifest, dest: Path, baseline: dict,
                    excluded: set[str], backup: str):
    """退役旧通用规则；条件失效的已修改规则先入 Vault，供重新启用恢复。

    retired_files 中只有哈希等于旧基线的文件才删除；未知或修改版本不接管。
    条件规则只处理历史账本已登记的文件，避免删除其他桌面管理器留下的内容。
    """
    archived = {}
    kept = []
    for rel in sorted(excluded):
        path = _safe_leaf(dest, rel)
        if not (path.exists() or path.is_symlink()):
            if rel in baseline and rel not in manifest.retired_files:
                archived[rel] = baseline[rel]
            continue
        digest = _path_identity(path)
        if rel in manifest.retired_files:
            if baseline.get(rel) == digest:
                if not backup:
                    backup = str(backup_conflicts(uid, [rel]))
                path.unlink()
            else:
                kept.append(rel)
        elif rel in baseline:
            archived[rel] = baseline[rel]
            if digest != baseline[rel]:
                vault = _safe_leaf(vault_dir(uid), rel)
                if vault.exists() or vault.is_symlink():
                    if _path_identity(vault) != digest:
                        raise ValueError(f"Vault conflict: {rel}")
                else:
                    _copy_leaf(path, vault)
            path.unlink()
        else:
            kept.append(rel)
    return archived, kept, backup


def _sync_conditionals(changed: set[str]) -> List[Step]:
    """仅刷新已启用、引用本轮单元的条件配置；不启用单元、不重启 Portal。"""
    result = []
    for uid in sorted(_enabled_set()):
        try:
            manifest = registry.load_unit(uid)
        except KeyError:
            continue
        if any(changed.intersection(required) for required in manifest.when_units.values()):
            result.extend(unit_on(uid, refresh=True, run_hooks=False, check_packages=False,
                                  _sync_dependents=False, _configuration_sync=True))
    return result


def backup_conflicts(unit_id: str, paths: List[str]) -> Path:
    """强制覆盖前创建可由 rollback 恢复的完整快照；失败即停止覆盖。"""
    from nyxuri.state.backup import backup_configs
    backup = backup_configs(note=f"Before force {unit_id}: " + ", ".join(paths), interactive=False)
    if backup is None:
        raise OSError(f"Conflict backup failed: {unit_id}")
    return backup


def _source_for(uid: str, manifest: ModuleManifest, preset: Optional[str]):
    from nyxuri.deploy.preset import _find_preset_src, read_active_preset
    selected = "default" if (manifest.runtime or manifest.merge or manifest.target or not manifest.is_deployable) else (preset if preset is not None else read_active_preset(uid))
    if manifest.runtime or manifest.merge or manifest.target or not manifest.is_deployable:
        if preset is not None:
            raise ValueError(f"Preset unsupported for unit: {uid}")
        root = registry.unit_dir(uid)
        return (root / manifest.target if manifest.target and not manifest.merge else root), selected
    source = _find_preset_src(uid, selected)
    if source is None:
        raise ValueError(f"Invalid preset for {uid}: {selected}")
    return source, selected


def _payload_paths(unit_id: str, manifest: ModuleManifest, source: Path, selected: str) -> dict:
    """按部署同一过滤规则展开基底与预设，后者具名覆盖前者。"""
    from nyxuri.deploy.preset import resolve_preset_inheritance
    if source.is_file():
        return {source.name: source}
    sources = []
    if not manifest.merge and not manifest.runtime:
        base, include, exclude = resolve_preset_inheritance(unit_id, selected)
        if base is not None:
            sources.append((base, _base_deploy_ignore_factory(base, include, exclude)))
    sources.append((source, _deploy_ignore_factory(source)))
    payload = {}
    for root, ignore in sources:
        for directory, dirs, files in os.walk(root):
            skipped = ignore(directory, dirs + files)
            dirs[:] = [name for name in dirs if name not in skipped]
            for name in files + [name for name in dirs if (Path(directory) / name).is_symlink()]:
                if name not in skipped:
                    path = Path(directory) / name
                    payload[path.relative_to(root).as_posix()] = path
    excluded = _excluded_payload(manifest)
    return {rel: path for rel, path in payload.items() if rel not in excluded}


def plan_conflicts(unit_id: str, preset: Optional[str] = None) -> List[str]:
    """只读披露模板具名冲突及 Vault 同名冲突，不以新模板抹去旧归属。"""
    manifest = registry.load_unit(unit_id)
    if manifest.runtime:
        return []
    source, selected = _source_for(unit_id, manifest, preset)
    dest = _unit_dest(unit_id, manifest)
    rec = ledger.get_unit(unit_id) or {}
    oldmeta = ledger.get_deployment(unit_id)
    baseline = {**oldmeta.get("archived_baselines", {}), **rec.get("files", {})}
    single = bool(manifest.target and not manifest.merge)
    legacy = _legacy_metadata(unit_id, manifest, rec, oldmeta)
    conflicts = set(_migration_conflicts(unit_id, manifest, rec, legacy)) if legacy else set()
    for rel, src in _payload_paths(unit_id, manifest, source, selected).items():
        if _is_user_owned(rel, manifest):
            continue
        target = _safe_leaf(dest, rel, single=single)
        archived = _safe_leaf(vault_dir(unit_id), rel)
        for existing in (target, archived):
            if existing.exists() or existing.is_symlink():
                ident = _path_identity(existing)
                if baseline.get(rel) != ident and ident != _path_identity(src):
                    conflicts.add(rel)
    # Custom 的同名冲突也必须披露；此处不把它列为强制模板覆盖对象。
    for rel, archived in _leaves(vault_dir(unit_id)):
        if rel in _excluded_payload(manifest):
            continue
        target = _safe_leaf(dest, rel, single=single)
        if (target.exists() or target.is_symlink()) and _path_identity(target) != _path_identity(archived):
            conflicts.add(rel)
    return sorted(conflicts)


@_guarded
def unit_on(unit_id: str, *, preset: Optional[str] = None,
            install_packages: Optional[Callable[[str, List[str]], bool]] = None,
            force: bool = False, refresh: bool = False, run_hooks: bool = True,
            check_packages: bool = True, _sync_dependents: bool = True,
            _configuration_sync: bool = False) -> List[Step]:
    """预检全部输入，再按依赖序部署；文件提交后钩子失败保留 pending 供重试。"""
    plan = _enable_closure(unit_id)
    enabled = _enabled_set()
    if refresh and unit_id not in enabled:
        return [Step(unit_id, False, "not-enabled", status="skipped")]
    if refresh and any(uid not in enabled for uid in plan):
        return [Step(unit_id, False, "disabled-dependencies: " + ", ".join(uid for uid in plan if uid not in enabled), status="skipped")]
    meta = ledger.get_deployment(unit_id)
    if meta.get("pending") in ("part_deploy", "part_reload") and meta.get("pending_part"):
        from nyxuri.deploy.preset import apply_part
        part = meta["pending_part"]
        ok = apply_part(unit_id, part["slot"], part["variant"], force=force)
        return [Step(unit_id, ok, "refreshed" if ok else "partial; part-retry-failed", status="completed" if ok else "partial")]
    if meta.get("pending") == "preset_reload" and preset is None:
        from nyxuri.desktop.presets import _reload_preset
        manifest = registry.load_unit(unit_id)
        ok = _reload_preset(manifest)
        if ok:
            ledger.set_deployment(unit_id, pending=None)
        return [Step(unit_id, ok, "refreshed" if ok else "partial; preset-reload-failed", status="completed" if ok else "partial")]
    if unit_id in enabled and all(uid in enabled for uid in plan) and preset is None and not refresh and not force and not meta.get("pending") and not _legacy_metadata(unit_id, registry.load_unit(unit_id), ledger.get_unit(unit_id) or {}, meta):
        return [Step(unit_id, True, "already-enabled", status="unchanged")]
    # 1. 显式预设及全部依赖平台必须先通过，失败时不安装包、不修改 active/Vault。
    candidates = [uid for uid in plan if uid not in enabled or uid == unit_id]
    prepared = {}
    migrations = set()
    layouts = {}
    from nyxuri.pkg.requirements import resolve_requirements
    for uid in candidates:
        manifest = registry.load_unit(uid)
        source, selected = _source_for(uid, manifest, preset if uid == unit_id else None)
        oldmeta = ledger.get_deployment(uid)
        legacy = _legacy_metadata(uid, manifest, ledger.get_unit(uid) or {}, oldmeta)
        if legacy:
            layouts[uid] = legacy
        elif oldmeta and (oldmeta.get("target") != str(_unit_dest(uid, manifest))
                          or oldmeta.get("shape") != _metadata(manifest, _unit_dest(uid, manifest))["shape"]):
            oldrecord = ledger.get_unit(uid) or {}
            if oldrecord.get("state") != "disabled" or oldmeta.get("pending"):
                return [Step(uid, False, "layout-changed: disable old deployment before enabling", status="failed")]
            if oldmeta.get("shape") != _metadata(manifest, _unit_dest(uid, manifest))["shape"]:
                return [Step(uid, False, "layout-shape-changed: explicit migration required", status="failed")]
            migrations.add(uid)
        requirements = resolve_requirements(manifest)
        if not requirements.supported:
            return [Step(uid, False, "unsupported-platform: " + requirements.reason)]
        prepared[uid] = manifest, selected
    for uid in candidates:
        manifest, _ = prepared[uid]
        missing = missing_packages(manifest) if check_packages else []
        if missing and (install_packages is None or not install_packages(uid, missing) or missing_packages(manifest)):
            return [Step(uid, False, "missing-packages: " + ", ".join(missing))]
    results = []
    for uid in candidates:
        manifest, selected = prepared[uid]
        dest = _unit_dest(uid, manifest)
        rec = ledger.get_unit(uid) or {}
        oldmeta = ledger.get_deployment(uid)
        baseline = {**oldmeta.get("archived_baselines", {}), **rec.get("files", {})}
        # 保留路径只保存来源，不把个人内容重基为模板哈希。历史 files 中已有的
        # 保留路径也提供归属证据；单凭当前 preserve 名称不能接管旧个人文件。
        protected = set(oldmeta.get("protected_paths", []))
        protected.update(rel for rel in baseline if _is_user_owned(rel, manifest))
        if uid in migrations and oldmeta.get("shape") == "file" and len(baseline) == 1:
            baseline = {dest.name: next(iter(baseline.values()))}
        conflicts = plan_conflicts(uid, preset if uid == unit_id else None)
        backup = ""
        migrated = uid in layouts
        if migrated:
            backup, migration_conflicts, complete = _migrate_layout(uid, manifest, rec, layouts[uid], force=force)
            if not complete:
                return results + [Step(uid, False, "migration-conflicts: " + ", ".join(migration_conflicts),
                                       "partial", tuple(migration_conflicts), backup)]
        elif uid in migrations or force:
            backup = str(backup_conflicts(uid, conflicts))
        # 迁移中 force 已选定旧生效内容；本轮模板合流仍须保护该内容。
        deploy_force = force and not migrated
        if force and backup:
            from nyxuri.desktop.owned_outputs import authorize_output_overwrites
            authorize_output_overwrites(uid, Path(backup))
        # 2. 归档逐文件恢复；记录待部署阶段，以免中断被误报为已完成。
        ledger.set_deployment(uid, **{**_metadata(manifest, dest), "pending": "deploy"})
        carried = {}
        files = {}
        old_paths = {rel for rel, _ in _leaves(dest)}
        excluded = _excluded_payload(manifest)
        archived_baselines = {rel: digest for rel, digest in oldmeta.get("archived_baselines", {}).items()
                              if rel not in manifest.retired_files}
        kept = []
        if not manifest.runtime and manifest.is_deployable:
            archived, kept, backup = _retire_payload(uid, manifest, dest, baseline, excluded, backup)
            archived_baselines.update(archived)
            baseline = {rel: digest for rel, digest in baseline.items() if rel not in excluded}
            _vault_restore(uid, dest, single=bool(manifest.target and not manifest.merge), excluded=excluded)
            # Vault 恢复的个人内容不是本轮模板新建，不能授权渲染器接管。
            old_paths = {rel for rel, _ in _leaves(dest)}
            if manifest.merge:
                source, _ = _source_for(uid, manifest, None)
                merge_baseline = {rel: digest for rel, digest in baseline.items()
                                  if not _is_user_owned(rel, manifest)}
                laid = merge_deploy_unit(uid, manifest, baseline=merge_baseline, force=deploy_force,
                                         include_rels=set(_payload_paths(uid, manifest, source, selected)))
                if laid is None:
                    return results + [Step(uid, False, "deploy-failed", status="partial", backup=backup)]
                files = {rel: _path_identity(dest / rel) for rel in laid}
                for rel, digest in baseline.items():
                    if (dest / rel).exists() and rel not in files:
                        files[rel] = digest
                files = {rel: digest for rel, digest in files.items()
                         if not _is_user_owned(rel, manifest)}
            else:
                # force 只让模板重占具名冲突；未知额外文件仍由 carry 保留。
                effective = None if deploy_force else baseline
                policy = CarryPolicy(baselines={uid: effective}, unknown=not deploy_force, carried={uid: {}})
                if uid in _phase_atomic_deployment([uid], carry_policy=policy,
                        preset_overrides={uid: selected}, reconcile_parts=False):
                    return results + [Step(uid, False, "deploy-failed", status="partial", backup=backup)]
                if preset is not None and uid == unit_id:
                    write_active_preset(uid, selected)
                carried = policy.carried.get(uid, {})
                _phase_render_templates(only_app=uid, exclude=set(carried))
                files = snapshot_files(dest, manifest)
                for rel in carried:
                    if rel in baseline:
                        files[rel] = baseline[rel]
                    else:
                        files.pop(rel, None)
        if not manifest.runtime:
            from nyxuri.desktop.owned_outputs import register_deployed_outputs
            register_deployed_outputs(uid, {path for rel, path in _leaves(dest) if rel not in old_paths})
            protected.update(rel for rel, _ in _leaves(dest)
                             if rel not in old_paths and _is_user_owned(rel, manifest))
        ledger.set_deployment(uid, protected_paths=sorted(protected))
        # 零件目标由 manifest preserve 保留；只登记本次首次铺设的路径，已有路径沿用旧基线。
        for cfg in manifest.parts.values():
            target_rel = cfg.get("target")
            if not isinstance(target_rel, str) or not target_rel:
                continue
            target = _safe_leaf(dest, target_rel)
            for rel, path in _leaves(target):
                key = target_rel if target.is_file() or target.is_symlink() else target_rel + "/" + rel
                if key in baseline:
                    files[key] = baseline[key]
                elif key not in old_paths:
                    files[key] = _path_identity(path)
        # 3. 先提交实际文件基线，再跑钩子；失败不能把普通 on 变成 already-enabled。
        ledger.set_unit(uid, state="enabled", preset=selected, files=files, vault=None)
        # 先记录已落地配置，再准备用户截图目录；mkdir 失败后仍能按正确基线重试。
        prepare_screenshot_directory(only_app=uid, exclude=set(carried))
        from nyxuri.desktop.owned_outputs import rebase_transformations
        rebase_transformations(uid)
        if manifest.parts:
            from nyxuri.deploy.deploy import _reconcile_active_parts
            failed_parts = _reconcile_active_parts(uid, manifest)
            if failed_parts:
                return results + [Step(uid, False, "partial; parts-failed: " + ", ".join(failed_parts), status="partial")]
            files = dict(ledger.get_unit(uid)["files"])
        ledger.set_deployment(uid, pending="consumer-sync", archived_baselines=archived_baselines)
        before_hook = snapshot_files(dest, manifest) if not manifest.runtime else {}
        hook_paths = {rel for rel, _ in _leaves(dest)} if not manifest.runtime else set()
        from nyxuri.desktop.owned_outputs import managed_paths
        external_before = managed_paths()
        hook_ok = True
        try:
            from nyxuri.desktop.owned_outputs import refresh_consumer_outputs
            refresh_consumer_outputs({uid: True})
        except ImportError:
            pass
        if run_hooks and manifest.post_install:
            ledger.set_deployment(uid, pending="post_install")
            hook_ok = (_run_unit_hook(uid, manifest, manifest.post_install, force=True) if force
                       else _run_unit_hook(uid, manifest, manifest.post_install))
            if not manifest.runtime:
                # 外部产物账本负责 Fisher 等钩子输出的撤回，避免同一文件双重归属。
                external_owned = external_before | managed_paths()
                protected.update(rel for rel, path in _leaves(dest)
                                 if rel not in hook_paths and path not in external_owned
                                 and _is_user_owned(rel, manifest))
                ledger.set_deployment(uid, protected_paths=sorted(protected))
        if run_hooks and manifest.post_install and not manifest.runtime and not manifest.merge:
            after_hook = snapshot_files(dest, manifest)
            external_owned = external_before | managed_paths()
            for rel in list(files):
                if _safe_leaf(dest, rel, single=bool(manifest.target)) in external_owned:
                    files.pop(rel)
            # 只认领本次钩子新增或改变的非carry路径，未变外来文件不借机入账。
            for rel, digest in after_hook.items():
                if (rel not in carried and before_hook.get(rel) != digest
                        and _safe_leaf(dest, rel, single=bool(manifest.target)) not in external_owned):
                    files[rel] = digest
            ledger.set_unit(uid, state="enabled", preset=selected, files=files, vault=None)
        pending = None if check_packages or _configuration_sync else "config-only"
        if _configuration_sync and oldmeta.get("pending") not in (None, "deploy", "migration", "consumer-sync"):
            pending = oldmeta["pending"]
        if not run_hooks and manifest.post_install and oldmeta.get("pending") in ("post_install", "config-only"):
            pending = oldmeta["pending"]
        ledger.set_deployment(uid, pending=pending if hook_ok else "post_install")
        if hook_ok:
            _emit(uid, "enabled")
        detail = ("config-only" if not check_packages and not _configuration_sync else "refreshed" if refresh else "enabled") if hook_ok else "partial; hook-failed: " + manifest.post_install
        if kept:
            detail += "; foreign-left: " + ", ".join(kept)
        if conflicts:
            detail += "; conflicts: " + ", ".join(conflicts)
        if backup:
            detail += "; backup: " + backup
        results.append(Step(uid, hook_ok, detail, "completed" if hook_ok else "partial", tuple(conflicts), backup))
        if not hook_ok:
            break
    if _sync_dependents:
        results.extend(_sync_conditionals({step.unit for step in results if step.ok}))
    return results


def unit_refresh(unit_id: str, *, force: bool = False, run_hooks: bool = True,
                 install_packages: Optional[Callable[[str, List[str]], bool]] = None) -> List[Step]:
    """只刷新已启用单元，复用 on 的预检、备份、部署和待重试阶段。"""
    return unit_on(unit_id, force=force, refresh=True, run_hooks=run_hooks,
                   install_packages=install_packages)


@_guarded
def unit_off(unit_id: str, *, cascade: bool = False, _sync_dependents: bool = True) -> List[Step]:
    """按历史落地点归档修改再撤回，外来内容原地保留，钩子失败允许重试。"""
    if unit_id not in registry.unit_ids() and ledger.get_unit(unit_id) is None:
        raise KeyError(f"unknown unit: {unit_id}")
    plan = _disable_plan(unit_id) if unit_id in registry.unit_ids() else [unit_id]
    if len(plan) > 1 and not cascade:
        return [Step(unit_id, False, "blocked-by-enabled-dependents: " + ", ".join(uid for uid in plan if uid != unit_id))]
    results = []
    for uid in plan:
        rec = ledger.get_unit(uid)
        meta = ledger.get_deployment(uid)
        if meta.get("pending") == "migration":
            return results + [Step(uid, False, "migration-pending: retry on or rollback before off", status="partial")]
        manifest, dest = _historical_manifest(uid, rec)
        if ((rec or {}).get("state") == "disabled" or (rec is None and not dest.exists())) and not meta.get("pending"):
            results.append(Step(uid, True, "already-disabled", status="unchanged"))
            continue
        ledger.set_deployment(uid, **{**_metadata(manifest, dest), "pending": "withdraw",
            "archived_baselines": {**meta.get("archived_baselines", {}), **(rec or {}).get("files", {})}})
        try:
            from nyxuri.desktop.owned_outputs import refresh_consumer_outputs
            refresh_consumer_outputs({uid: False})
            from nyxuri.desktop.owned_outputs import withdraw_outputs
            withdraw_outputs(consumer=uid)
            withdraw_outputs(producer=uid)
            # 主文件运行时变换撤回会同步更新部署基线，归档必须使用更新后的值。
            rec = ledger.get_unit(uid)
        except ImportError:
            pass
        archived = [] if manifest.runtime else _vault_archive(uid, dest, manifest, rec)
        foreign = [] if manifest.runtime else _wipe_unit(uid, dest, rec, manifest)
        ledger.set_unit(uid, state="disabled", preset=(rec or {}).get("preset") or "default", files={}, vault=str(vault_dir(uid)))
        ledger.set_deployment(uid, pending="post_remove" if manifest.post_remove else None)
        hook_ok = not manifest.post_remove or _run_unit_hook(uid, manifest, manifest.post_remove)
        ledger.set_deployment(uid, pending=None if hook_ok else "post_remove")
        detail = "disabled" if hook_ok else "partial; hook-failed: " + manifest.post_remove
        if archived:
            detail += f"; archived: {len(archived)}; vault: {vault_dir(uid)}"
        if foreign:
            detail += "; foreign-left: " + ", ".join(foreign)
        from nyxuri.pkg.requirements import resolve_requirements
        req = resolve_requirements(manifest)
        packages = (*req.packages_repo, *req.packages_aur, *req.packages_flatpak)
        if packages:
            detail += "; packages-left: " + ", ".join(packages)
        if hook_ok:
            _emit(uid, "disabled")
        results.append(Step(uid, hook_ok, detail, "completed" if hook_ok else "partial"))
        if not hook_ok:
            break
    if _sync_dependents:
        results.extend(_sync_conditionals({step.unit for step in results if step.ok}))
    return results


def audit_units(unit_id: Optional[str] = None) -> Dict[str, str]:
    """只读逐文件核对历史基线；消失单元和未完成阶段单独报告而不打断其他项。"""
    known = registry.unit_ids()
    records = ledger.all_units()
    candidates = [unit_id] if unit_id is not None else sorted(set(known) | set(records))
    report = {}
    for uid in candidates:
        rec = records.get(uid)
        if uid not in known:
            if rec is None:
                raise KeyError(f"unknown unit: {uid}")
            report[uid] = "Orphan"
            continue
        manifest, dest = _historical_manifest(uid, rec)
        if ledger.get_deployment(uid).get("pending"):
            report[uid] = "Pending"
        elif rec and rec.get("state") == "enabled":
            single = bool(manifest.target and not manifest.merge)
            report[uid] = STATE_SYNCED if all(_path_identity(_safe_leaf(dest, rel, single=single)) == digest
                for rel, digest in rec.get("files", {}).items()) else STATE_DRIFTED
        elif manifest.runtime:
            if rec:
                report[uid] = STATE_SYNCED
        elif manifest.merge:
            if _merge_managed_view(dest, manifest):
                report[uid] = STATE_GHOST
            elif rec:
                report[uid] = STATE_SYNCED
        elif dest.exists() or dest.is_symlink():
            report[uid] = STATE_GHOST
        elif rec:
            report[uid] = STATE_SYNCED
    return report
