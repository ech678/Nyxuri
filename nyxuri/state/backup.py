"""Configuration snapshot, backup, rollback, and uninstallation management."""

import datetime
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from nyxuri.core import Colors
from nyxuri.core import (
    copy_path,
    remove_path,
    get_env,
    log_msg,
    register_temp_path,
)
from nyxuri.core import msg
from nyxuri.tui import CheckboxEntry, CheckboxList, Menu, MenuItem, prompt_confirm, truncate_display


_MANAGED_SNAPSHOT_RE = re.compile(
    r"^(?:(?:snapshot|pre_rollback)_\d{8}_\d{6}(?:_\d+){0,2}|dotfiles_backup_.+)$"
)


def get_backup_base_dir() -> Path:
    """Resolve standard backup base directory ~/.config/nyxuri/backups."""
    return get_env().nyx_dir / "backups"


MAX_SNAPSHOTS = 30
SNAPSHOT_VERSION = 2


def _safe_target(value: str) -> Path:
    """只接受当前 HOME 内的具体目标，且不允许父目录软链接越界。"""
    home = get_env().home.resolve()
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path == home:
        raise ValueError(f"Unsafe snapshot target: {value}")
    path.relative_to(home)
    path.parent.resolve().relative_to(home)
    return path


def _safe_unit_id(uid: str) -> None:
    """快照中的单位 ID 也用于 Vault 和 active 文件名，禁止路径片段。"""
    if not isinstance(uid, str) or not uid or uid in (".", "..") or "/" in uid or "\\" in uid:
        raise ValueError(f"Unsafe snapshot unit: {uid}")


def _remove_checked(path: Path) -> None:
    """恢复状态时不吞删除错误，避免旧 Vault 残留被当成完整恢复。"""
    _safe_target(str(path))
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _capture_path(source: Path, root: Path, rel: str) -> dict:
    """记录存在与缺失；目录按叶子复制，恢复时不会整目录吞掉外来文件。"""
    source = _safe_target(str(source))
    present = source.exists() or source.is_symlink()
    entry = {"target": str(source), "payload": rel, "present": present,
             "directory": source.is_dir() and not source.is_symlink(), "files": [], "directories": []}
    if not present:
        return entry
    target = root / rel
    if entry["directory"]:
        target.mkdir(parents=True)
        for current, dirs, files in os.walk(source):
            # os.walk 不跟随目录链接；链接本身也必须保存。
            for name in list(dirs):
                item = Path(current) / name
                if item.is_symlink():
                    files.append(name)
                    dirs.remove(name)
                else:
                    entry["directories"].append(item.relative_to(source).as_posix())
            for name in sorted(files):
                item = Path(current) / name
                item_rel = item.relative_to(source).as_posix()
                destination = target / item_rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                copy_path(item, destination)
                entry["files"].append(item_rel)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        copy_path(source, target)
    return entry


def _unit_target(uid: str, data: dict) -> Optional[Path]:
    """历史目标优先；旧记录只能在当前蓝图仍存在时补全目标。"""
    from nyxuri.kernel import registry, transaction
    deployment = data.get("deployments", {}).get(uid, {})
    if deployment.get("shape") == "runtime":
        return None
    if deployment.get("target"):
        return _safe_target(deployment["target"])
    manifest = registry.load_unit(uid)
    return None if transaction._is_runtime(manifest) else _safe_target(str(transaction._unit_dest(uid, manifest)))


def _write_managed_snapshot(root: Path, extra_paths: Optional[list[Path]] = None) -> None:
    """保存单位内容、对应账本、预设与 Vault，避免只回滚文件却保留新账本。"""
    from nyxuri.kernel import ledger, registry
    from nyxuri.desktop import owned_outputs
    from nyxuri.deploy.deploy import config_item_dest, discover_config_items
    env = get_env()
    data = ledger.read_ledger()
    units = data.get("units", {})
    manifest = {"version": SNAPSHOT_VERSION, "units": units,
                "deployments": data.get("deployments", {}),
                "presets": data.get("presets", {}), "parts": data.get("parts", {}), "paths": []}
    targets = []
    for index, uid in enumerate(sorted(units)):
        _safe_unit_id(uid)
        target = _unit_target(uid, data)
        if target is not None:
            targets.append(target)
            manifest["paths"].append(_capture_path(target, root, f"units/{index}"))
        manifest["paths"].append(_capture_path(env.state_dir / "vault" / uid, root, f"vault/{index}"))
        manifest["paths"].append(_capture_path(env.presets_dir / f"{uid}.active", root, f"active/{index}"))
    # 首次安装前也可主动 snapshot；未登记目录只保存文件，恢复不替它登记归属。
    for index, item in enumerate(discover_config_items()):
        target = config_item_dest(item)
        if any(target == managed or target.is_relative_to(managed) or managed.is_relative_to(target)
               for managed in targets):
            continue
        manifest["paths"].append(_capture_path(target, root, f"unmanaged/{index}"))
        targets.append(target)
    # 首次强制接管的 merge 单元尚无账本，且不在 config items 中；仍须先保全共享目录。
    for index, uid in enumerate(registry.unit_ids()):
        target = _unit_target(uid, data)
        if target is None or any(target == managed or target.is_relative_to(managed) or managed.is_relative_to(target)
                                 for managed in targets):
            continue
        if target.exists() or target.is_symlink():
            manifest["paths"].append(_capture_path(target, root, f"unmanaged-units/{index}"))
            targets.append(target)
    manifest["paths"].append(_capture_path(env.presets_dir, root, "user-presets"))
    # 迁移的旧默认路径可能尚无版本化目标记录，必须在首次改写归属前保全它。
    captured = [Path(entry["target"]) for entry in manifest["paths"]]
    for index, target in enumerate(extra_paths or []):
        target = _safe_target(str(target))
        if any(target == item or target.is_relative_to(item) for item in captured):
            continue
        manifest["paths"].append(_capture_path(target, root, f"extra/{index}"))
        captured.append(target)
    # 钩子恢复记录属于单位域；无需备份 install.log、全局锁等无关状态。
    manifest["auxiliary"] = []
    for name in ("fisher.json", "fcitx-nyxmellow-theme.prev", "fcitx-nyxmellow-quickphrase.prev"):
        manifest["auxiliary"].append(_capture_path(env.state_dir / name, root, f"auxiliary/{name}"))
    manifest["external"] = owned_outputs.snapshot_state(root / "external")
    (root / "snapshot.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_managed_snapshot(root: Path) -> Optional[dict]:
    """先验证全部恢复输入；旧目录没有元数据时明确走文件级兼容路径。"""
    from nyxuri.desktop import owned_outputs
    from nyxuri.kernel import ledger
    metadata = root / "snapshot.json"
    if not metadata.exists():
        return None
    manifest = json.loads(metadata.read_text(encoding="utf-8"))
    if manifest.get("version") != SNAPSHOT_VERSION:
        raise ValueError("Unsupported snapshot version")
    for key in ("units", "deployments", "presets"):
        if not isinstance(manifest.get(key), dict):
            raise ValueError(f"Invalid snapshot {key}")
    # 来源路径等新增部署字段也须在撤回现状之前完成校验，不能写回账本时才失败。
    try:
        ledger._validate_ledger({"units": manifest["units"], "deployments": manifest["deployments"]})
    except ledger.LedgerError as exc:
        raise ValueError(f"Invalid snapshot ownership: {exc}") from exc
    if not isinstance(manifest.get("parts", {}), dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in manifest.get("parts", {}).items()):
        raise ValueError("Invalid snapshot parts")
    for uid, record in manifest["units"].items():
        _safe_unit_id(uid)
        if not isinstance(record, dict) or record.get("state") not in ("enabled", "disabled"):
            raise ValueError(f"Invalid snapshot unit record: {uid}")
        if not isinstance(record.get("files"), dict) or not isinstance(record.get("preset"), str):
            raise ValueError(f"Invalid snapshot unit metadata: {uid}")
        for rel, digest in record["files"].items():
            if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts or not isinstance(digest, str):
                raise ValueError(f"Invalid snapshot managed file: {uid}")
    for uid, deployment in manifest["deployments"].items():
        _safe_unit_id(uid)
        if not isinstance(deployment, dict) or deployment.get("version") != 1:
            raise ValueError(f"Invalid snapshot deployment: {uid}")
        _safe_target(deployment["target"])
        if deployment.get("shape") not in ("directory", "file", "merge", "runtime"):
            raise ValueError(f"Invalid snapshot deployment shape: {uid}")
    for entry in manifest["paths"] + manifest.get("auxiliary", []):
        _safe_target(entry["target"])
        rel = Path(entry["payload"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Unsafe snapshot payload")
        payload = root / rel
        if entry["present"] and not (payload.exists() or payload.is_symlink()):
            raise ValueError(f"Missing snapshot payload: {rel}")
        for file_rel in entry["files"] + entry.get("directories", []):
            path_rel = Path(file_rel)
            if path_rel.is_absolute() or ".." in path_rel.parts:
                raise ValueError("Unsafe snapshot file")
            item = payload / path_rel
            if file_rel in entry["files"] and not (item.exists() or item.is_symlink()):
                raise ValueError(f"Missing snapshot file: {item}")
    owned_outputs.validate_snapshot_state(root / "external", manifest.get("external", {}))
    return manifest


def _restore_paths(root: Path, entries: list[dict]) -> None:
    """逐文件还原快照；外来文件保留，缺失目标只撤回明确登记的单文件。"""
    from nyxuri.deploy.atomic import atomic_replace_item
    for entry in entries:
        target = _safe_target(entry["target"])
        if not entry["present"]:
            continue
        source = root / entry["payload"]
        if entry["directory"]:
            if target.is_symlink() or (target.exists() and not target.is_dir()):
                raise ValueError(f"Snapshot directory conflicts with file: {target}")
            target.mkdir(parents=True, exist_ok=True)
            for rel in entry.get("directories", []):
                directory = _safe_target(str(target / rel))
                if directory.is_symlink():
                    raise ValueError(f"Snapshot directory conflicts with symlink: {directory}")
                directory.mkdir(parents=True, exist_ok=True)
            pairs = [(source / rel, target / rel) for rel in entry["files"]]
        else:
            pairs = [(source, target)]
        for src, dst in pairs:
            _safe_target(str(dst))
            if dst.is_dir() and not dst.is_symlink():
                raise ValueError(f"Snapshot file conflicts with directory: {dst}")
            if not atomic_replace_item(src, dst, preserve_custom=False):
                raise OSError(f"Failed to restore snapshot file: {dst}")


def _restore_managed_snapshot(root: Path, manifest: dict) -> bool:
    """先撤回当前受管单位，再恢复内容与单位域状态；新增单位保留停用记录。"""
    from nyxuri.kernel import ledger, transaction
    from nyxuri.desktop import owned_outputs
    with ledger.mutation_lock():
        for uid, record in ledger.all_units().items():
            deployment = ledger.get_deployment(uid)
            # 普通 off 禁止处理中途迁移；rollback 已先完成安全快照，可按迁移身份
            # 撤回新区已复制且未变的文件，再从原历史目标执行常规归档和撤回。
            migration = deployment.get("migration")
            if deployment.get("pending") == "migration" and migration:
                from nyxuri.deploy.atomic import _path_identity
                target = _safe_target(migration["target"])
                if str(target) != deployment["target"]:
                    for rel, digest in migration["files"].items():
                        path = transaction._safe_leaf(target, rel)
                        if _path_identity(path) == digest:
                            path.unlink()
                ledger.set_deployment(uid, pending="deploy", migration=None)
            if record.get("state") == "enabled" or ledger.get_deployment(uid).get("pending"):
                # 回滚要恢复一个完整单位集合；中途不按半恢复的开关重写 Portal 等条件载荷。
                steps = transaction.unit_off(uid, cascade=True, _sync_dependents=False)
                if not all(step.ok for step in steps):
                    raise RuntimeError(f"Could not withdraw current unit: {uid}")
        # Vault/active 状态与目标内容一同恢复；预先备份已保存回滚前的个人修改。
        for uid in manifest["units"]:
            _remove_checked(get_env().state_dir / "vault" / uid)
            _remove_checked(get_env().presets_dir / f"{uid}.active")
        _restore_paths(root, manifest["paths"] + manifest.get("auxiliary", []))
        owned_outputs.restore_state(root / "external", manifest.get("external", {}))
        units = {**ledger.all_units(), **manifest["units"]}
        current = ledger.read_ledger()
        # 旧五字段快照没有部署元数据；不能残留回滚前的新目标、pending 或归属。
        deployments = {uid: meta for uid, meta in current.get("deployments", {}).items()
                       if uid not in manifest["units"]}
        deployments.update(manifest["deployments"])
        # 零件选择与其恢复文件同属单位形态；其他单位的选择不被旧快照抹除。
        snap_units = set(manifest["units"])
        parts = {key: value for key, value in current.get("parts", {}).items()
                 if key.rpartition(":")[0] not in snap_units}
        parts.update({key: value for key, value in manifest.get("parts", {}).items()
                      if key.rpartition(":")[0] in snap_units})
        ledger.replace_unit_state(units, deployments, manifest["presets"], parts=parts)
        owned_outputs.refresh_consumer_outputs()
    return True


def _prune_old_snapshots(base_dir: Path, protected_snapshot: Optional[Path] = None) -> None:
    """Keep at most MAX_SNAPSHOTS managed snapshots; drop oldest beyond that."""
    if not base_dir.is_dir():
        return
    snapshots = [
        d for d in base_dir.iterdir()
        if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name)
    ]
    if len(snapshots) <= MAX_SNAPSHOTS:
        return
    snapshots.sort(key=lambda p: p.name)
    excess = len(snapshots) - MAX_SNAPSHOTS
    for old in snapshots:
        if old == protected_snapshot:
            continue
        shutil.rmtree(old, ignore_errors=True)
        log_msg("INFO", f"Pruned old snapshot {old.name}")
        excess -= 1
        if not excess:
            break


def backup_configs(
    note: str = "", interactive: bool = True, protected_snapshot: Optional[Path] = None,
    extra_paths: Optional[list[Path]] = None
) -> Optional[Path]:
    """Create a complete snapshot of all active dotfiles configurations."""
    from nyxuri.deploy.deploy import config_item_dest, discover_config_items

    env = get_env()
    base_dir = get_backup_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    if interactive:
        print(msg("backing_up"))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = base_dir / f"snapshot_{timestamp}"
    suffix = 1
    while backup_dir.exists() or backup_dir.is_symlink():
        backup_dir = base_dir / f"snapshot_{timestamp}_{suffix}"
        suffix += 1

    tmp_dir = Path(tempfile.mkdtemp(prefix=".snapshot.", dir=base_dir))
    register_temp_path(tmp_dir)

    from nyxuri.kernel import ledger
    try:
        with ledger.mutation_lock():
            _write_managed_snapshot(tmp_dir, extra_paths=extra_paths)
            # 安装前的文件级副本仍保留，供旧工具与手工恢复使用；v2 回滚以单位元数据为准。
            for item in discover_config_items():
                cfg_path = config_item_dest(item)
                if cfg_path.exists() or cfg_path.is_symlink():
                    copy_path(cfg_path, tmp_dir / item)
                    if interactive:
                        print(msg("log_backup_item", item))
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        log_msg("ERROR", f"Snapshot failed before publication: {exc}")
        return None

    if note.strip():
        (tmp_dir / "note.txt").write_text(note.strip(), encoding="utf-8")

    tmp_dir.rename(backup_dir)
    _prune_old_snapshots(base_dir, protected_snapshot)
    if interactive:
        print(msg("backup_done", str(backup_dir)))
    log_msg("INFO", f"Created configuration snapshot at {backup_dir}")
    return backup_dir


def get_all_backups() -> List[Path]:
    """Discover all snapshot directories including legacy dotfiles_backup_* folders."""
    env = get_env()
    base_dir = get_backup_base_dir()
    backups: List[Path] = []

    if base_dir.is_dir():
        for d in base_dir.iterdir():
            if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name):
                backups.append(d)

    # 完全卸载保留的最后保险独立于可选删除的配置目录。
    recovery_base = env.state_dir / "uninstall-backups"
    if recovery_base.is_dir():
        for d in recovery_base.iterdir():
            if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name):
                backups.append(d)

    # Legacy snapshots directly under ~/.config/
    if env.config_dir.is_dir():
        for d in env.config_dir.iterdir():
            if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name):
                backups.append(d)

    # Legacy snapshots under ~/.config/NyxNiri/backups and ~/.config/nyxniri/backups
    for legacy_name in ("NyxNiri", "nyxniri"):
        legacy_base = env.config_dir / legacy_name / "backups"
        if legacy_base.is_dir() and legacy_base != base_dir:
            for d in legacy_base.iterdir():
                if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name):
                    backups.append(d)

    return sorted(backups, key=lambda p: p.name)


def _resolve_backup_arg(target_arg: str, backups: List[Path]) -> Optional[Path]:
    """Resolve a CLI snapshot argument only against discovered snapshot paths."""
    value = target_arg.strip()
    if not value:
        return None
    if value.isdecimal():
        idx = int(value) - 1
        return backups[idx] if 0 <= idx < len(backups) else None
    try:
        candidate = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    for backup in backups:
        try:
            if candidate == backup.resolve(strict=True):
                return backup
        except (OSError, RuntimeError):
            continue
    return None


def _read_snapshot_note(backup: Path) -> str:
    """Read a note for display without allowing terminal control characters."""
    note_file = backup / "note.txt"
    if not note_file.is_file():
        return ""
    try:
        raw = note_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    text = " ".join("".join(ch if ch.isprintable() else " " for ch in raw).split())
    return truncate_display(text, 50, suffix="...")


def _snapshot_label(index: int, backup: Path) -> str:
    """Build a compact selectable label with an optional user note."""
    note = _read_snapshot_note(backup)
    suffix = f" - {note}" if note else ""
    kind = "state+files" if (backup / "snapshot.json").is_file() else "files only (legacy)"
    return f"[{index}] {backup.name} [{kind}]{suffix}"


def list_backups() -> List[Path]:
    """Display a numbered list of all available snapshots."""
    backups = get_all_backups()
    if not backups:
        print(msg("no_backups_found"))
        return []

    print(msg("available_backups"))
    for idx, b in enumerate(backups, start=1):
        note = _read_snapshot_note(b)
        note_str = f" {Colors.DARK_GRAY}— {note}{Colors.RESET}" if note else ""
        kind = "state+files" if (b / "snapshot.json").is_file() else "files only (legacy)"
        print(f"  {Colors.BOLD_CYAN}[{idx}]{Colors.RESET} {Colors.BOLD_WHITE}{b.name}{Colors.RESET} [{kind}]{note_str}")
        print(f"      {Colors.DARK_GRAY}{b}{Colors.RESET}")
    print()
    return backups


def rollback_configs(target_arg: str = "") -> bool:
    """Restore configuration from a selected historical snapshot."""
    from nyxuri.deploy.atomic import atomic_replace_item
    from nyxuri.deploy.deploy import config_item_dest, discover_config_items

    backups = list_backups()
    if not backups:
        return False

    chosen_backup = _resolve_backup_arg(target_arg, backups)
    if target_arg.strip() and chosen_backup is None:
        print(msg("rollback_invalid_num"))
        return False

    if chosen_backup is None:
        if not sys.stdin.isatty():
            print(msg("rollback_invalid_num"))
            return False
        items = [
            MenuItem(label=_snapshot_label(idx, b))
            for idx, b in enumerate(backups, start=1)
        ]
        items.append(MenuItem(label=msg("menu_opt0"), style="subtle"))
        choice = Menu("rollback_select_title", items, hint_key="rollback_select_hint", compact=True).run()
        if choice == len(items) - 1:
            print(msg("delete_cancelled"))
            return False
        chosen_backup = backups[choice]

    if not chosen_backup.is_dir() or chosen_backup.is_symlink():
        print(msg("rollback_source_missing", chosen_backup.name), file=sys.stderr)
        log_msg("ERROR", f"Selected rollback snapshot disappeared: {chosen_backup}")
        return False

    try:
        managed = _load_managed_snapshot(chosen_backup)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log_msg("ERROR", f"Invalid rollback snapshot: {exc}")
        return False
    env = get_env()
    expected_items = [
        item for item in discover_config_items()
        if (chosen_backup / item).exists() or (chosen_backup / item).is_symlink()
    ]
    if managed is None and not expected_items:
        print(msg("rollback_no_items"), file=sys.stderr)
        log_msg("ERROR", f"Selected rollback snapshot has no restorable configuration: {chosen_backup}")
        return False

    print(msg("rolling_back", chosen_backup.name))

    # Auto pre-rollback snapshot
    pre_snap = backup_configs(
        note="pre-rollback safety snapshot", interactive=False, protected_snapshot=chosen_backup
    )
    if not pre_snap:
        log_msg("ERROR", "Rollback refused: safety snapshot failed")
        return False
    print(msg("pre_rollback_backup", str(pre_snap)))

    if not chosen_backup.is_dir() or chosen_backup.is_symlink():
        print(msg("rollback_source_missing", chosen_backup.name), file=sys.stderr)
        log_msg("ERROR", f"Selected rollback snapshot disappeared: {chosen_backup}")
        return False

    if managed is not None:
        try:
            # 安全快照期间可能有外部删除；再次检查后才允许第一个撤回动作。
            managed = _load_managed_snapshot(chosen_backup)
            if managed is None:
                raise ValueError("Snapshot metadata disappeared")
            _restore_managed_snapshot(chosen_backup, managed)
        except Exception as exc:
            log_msg("ERROR", f"Managed rollback failed; safety snapshot retained at {pre_snap}: {exc}")
            print(f"Rollback incomplete: {exc}; safety snapshot: {pre_snap}", file=sys.stderr)
            return False
        print(msg("rollback_done", chosen_backup.name))
        return True

    for item in expected_items:
        snap_item = chosen_backup / item
        if not snap_item.exists() and not snap_item.is_symlink():
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            log_msg("ERROR", f"Selected rollback snapshot item disappeared: {snap_item}")
            return False

    for item in expected_items:
        snap_item = chosen_backup / item
        dest_item = config_item_dest(item)
        if not atomic_replace_item(snap_item, dest_item, preserve_custom=False):
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            log_msg("ERROR", f"Failed to restore snapshot item {snap_item}")
            return False
        print(msg("log_restore_item", item))

    print(msg("rollback_done", chosen_backup.name))
    log_msg("INFO", f"Rolled back dotfiles from snapshot {chosen_backup}")
    return True


def delete_backup(target_arg: str = "") -> bool:
    """Delete one or more configuration snapshots after explicit confirmation."""
    backups = get_all_backups()
    if not backups:
        print(msg("no_backups_found"))
        return False

    selected: List[Path] = []
    if target_arg.strip():
        chosen_backup = _resolve_backup_arg(target_arg, backups)
        if chosen_backup is None:
            print(msg("delete_invalid_num"))
            return False
        selected = [chosen_backup]
    elif sys.stdin.isatty():
        entries = [
            CheckboxEntry(key=str(index), label=_snapshot_label(index, backup))
            for index, backup in enumerate(backups, start=1)
        ]
        chosen_keys = CheckboxList(
            "delete_snapshot_title", entries, hint_key="delete_snapshot_hint"
        ).run()
        if chosen_keys is None:
            print(msg("delete_cancelled"))
            return False
        selected = [backups[int(key) - 1] for key in chosen_keys]
    else:
        print(msg("delete_invalid_num"))
        return False

    if not selected:
        print(msg("delete_none_selected"))
        return False

    if len(selected) == 1:
        print(msg("delete_confirm", selected[0].name))
    else:
        print(msg("delete_confirm_many", len(selected)))
        for backup in selected:
            print(f"    {backup.name}")
    if not prompt_confirm("delete_prompt", "n", destructive=True):
        print(msg("delete_cancelled"))
        return False

    deleted: List[Path] = []
    for backup in selected:
        try:
            shutil.rmtree(backup)
            deleted.append(backup)
        except OSError as exc:
            print(msg("delete_failed", backup.name), file=sys.stderr)
            log_msg("ERROR", f"Failed to delete snapshot {backup}: {exc}")

    if not deleted:
        return False
    remaining = len(backups) - len(deleted)
    if len(deleted) == 1:
        print(msg("delete_done", deleted[0].name, remaining))
    else:
        print(msg("delete_done_many", len(deleted), remaining))
    for backup in deleted:
        log_msg("INFO", f"Deleted snapshot {backup}")
    return len(deleted) == len(selected)
