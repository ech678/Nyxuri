"""账本读写的唯一入口：严格读取、事务加锁和原子合并提交。

units 保持 state / preset / files / vault / updated 五字段兼容形状；
deployments 使用独立版本保存历史目标、归档基线和待重试阶段。
不存在表示首次使用；损坏、权限或锁错误必须停止修改，不能退化为空账本。
"""

from contextlib import contextmanager
from contextvars import ContextVar
import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nyxuri.core import get_env

UNIT_STATES = ("enabled", "disabled")

# --- generic ledger primitives -------------------------------------------


def ledger_path() -> Path:
    return get_env().state_dir / "state.json"


class LedgerError(RuntimeError):
    """账本不可读、结构损坏或无法加锁；调用方必须停止所有落地操作。"""


_lock_depth = ContextVar("nyxuri_ledger_lock_depth", default=0)


def _safe_unit_id(value: Any) -> bool:
    """账本键用于 Vault 相对目录，拒绝目录跳转和路径分隔符。"""
    return isinstance(value, str) and bool(value) and value not in (".", "..") and not any(c in value for c in ("/", "\\", "\0"))


def _safe_relative(value: Any) -> bool:
    """所有权与保留规则只能命名目标内的相对项。"""
    return (isinstance(value, str) and bool(value) and value != "."
            and not Path(value).is_absolute() and ".." not in Path(value).parts
            and "\0" not in value)


def _validate_ledger(data: Any) -> dict[str, Any]:
    """在读取与提交前共用结构验证，避免把无效元数据先写入再拒绝读取。"""
    try:
        if not isinstance(data, dict):
            raise ValueError("ledger root must be an object")
        if data.get("deployment_version", 1) != 1:
            raise ValueError("unsupported deployment metadata version")
        for key in ("units", "deployments"):
            if key in data and not isinstance(data[key], dict):
                raise ValueError(f"{key} must be an object")
        for uid, rec in data.get("units", {}).items():
            if not _safe_unit_id(uid):
                raise ValueError("invalid unit identifier")
            if not isinstance(rec, dict) or rec.get("state") not in UNIT_STATES:
                raise ValueError(f"invalid unit record: {uid}")
            files = rec.get("files", {})
            if not isinstance(files, dict) or not all(_safe_relative(rel) and isinstance(digest, str) for rel, digest in files.items()):
                raise ValueError(f"invalid managed paths: {uid}")
        for uid, meta in data.get("deployments", {}).items():
            if not _safe_unit_id(uid) or not isinstance(meta, dict) or meta.get("version") != 1:
                raise ValueError(f"invalid deployment metadata: {uid}")
            if meta.get("shape") not in ("directory", "file", "merge", "runtime"):
                raise ValueError(f"invalid deployment shape: {uid}")
            target = meta.get("target")
            if not isinstance(target, str) or not Path(target).is_absolute() or ".." in Path(target).parts or "\0" in target:
                raise ValueError(f"invalid deployment target: {uid}")
            if meta.get("pending") not in (None, "deploy", "post_install", "withdraw", "post_remove", "config-only", "part_deploy", "part_reload", "preset_reload", "consumer-sync", "migration"):
                raise ValueError(f"invalid deployment phase: {uid}")
            preserve = meta.get("preserve", [])
            protected = meta.get("protected_paths", [])
            archived = meta.get("archived_baselines", {})
            if not isinstance(preserve, list) or not all(_safe_relative(rel) for rel in preserve):
                raise ValueError(f"invalid deployment preservation: {uid}")
            if not isinstance(protected, list) or not all(_safe_relative(rel) for rel in protected):
                raise ValueError(f"invalid protected path ownership: {uid}")
            if not isinstance(archived, dict) or not all(_safe_relative(rel) and isinstance(digest, str) for rel, digest in archived.items()):
                raise ValueError(f"invalid archived baselines: {uid}")
            migration = meta.get("migration")
            if migration is not None:
                if (not isinstance(migration, dict) or migration.get("shape") not in ("directory", "merge")
                        or not isinstance(migration.get("target"), str) or not Path(migration["target"]).is_absolute()
                        or ".." in Path(migration["target"]).parts
                        or not isinstance(migration.get("backup"), str)
                        or not isinstance(migration.get("files"), dict)
                        or not all(_safe_relative(rel) and isinstance(digest, str) for rel, digest in migration["files"].items())):
                    raise ValueError(f"invalid pending migration: {uid}")
            part = meta.get("pending_part")
            if part is not None and (not isinstance(part, dict) or not _safe_unit_id(part.get("slot")) or not _safe_unit_id(part.get("variant"))):
                raise ValueError(f"invalid pending part: {uid}")
        return data
    except (ValueError, TypeError) as exc:
        raise LedgerError(f"Invalid ledger: {exc}") from exc


def read_ledger() -> dict[str, Any]:
    """只把不存在的账本视为空状态；损坏和权限错误必须明确失败。"""
    try:
        raw = ledger_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError) as exc:
        raise LedgerError(f"Cannot read ledger: {exc}") from exc
    try:
        return _validate_ledger(json.loads(raw))
    except ValueError as exc:
        raise LedgerError(f"Invalid ledger: {exc}") from exc


@contextmanager
def mutation_lock():
    """在首次文件写入前锁定并验证账本；嵌套记账沿用当前事务的锁。"""
    if _lock_depth.get():
        yield
        return
    path = ledger_path()
    read_ledger()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(path.with_name(f".{path.name}.lock"), "a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
        except OSError:
            handle.close()
            raise
    except OSError as exc:
        raise LedgerError(f"Cannot lock ledger: {exc}") from exc
    token = _lock_depth.set(1)
    try:
        read_ledger()
        yield
    finally:
        _lock_depth.reset(token)
        handle.close()


def update_ledger(*, replace_keys: tuple[str, ...] = (), **changes: Any) -> dict[str, Any]:
    """持锁合并顶层映射，再以原子替换提交；失败保留原件。"""
    with mutation_lock():
        path = ledger_path()
        data = read_ledger()
        for key, value in changes.items():
            if key not in replace_keys and isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
        _validate_ledger(data)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        return data


def replace_unit_state(units: dict, deployments: dict, presets: dict,
                       parts: dict | None = None) -> dict[str, Any]:
    """恢复单位域的完整映射，保留 Shell 选择等不属于快照的全局设置。"""
    changes = dict(units=units, deployments=deployments, presets=presets)
    if parts is not None:
        changes["parts"] = parts
    return update_ledger(replace_keys=tuple(changes), **changes)


def get_deployment(unit_id: str) -> dict[str, Any]:
    """读取独立版本化部署元数据；旧五字段记录返回空映射。"""
    value = read_ledger().get("deployments", {}).get(unit_id, {})
    if not isinstance(value, dict) or value.get("version", 1) != 1:
        raise LedgerError(f"Unsupported deployment metadata: {unit_id}")
    return dict(value)


def set_deployment(unit_id: str, **metadata: Any) -> dict[str, Any]:
    """合并单元历史目标、待重试阶段和归档基线，不重新计算个人文件哈希。"""
    with mutation_lock():
        value = {**get_deployment(unit_id), **metadata, "version": 1}
        update_ledger(deployment_version=1, deployments={unit_id: value})
        return value


# --- shell selection ------------------------------------------------------


def active_shell(default: str = "noctalia") -> str:
    value = read_ledger().get("active_shell", default)
    if not isinstance(value, str):
        return default
    if value in {"nyxuri-shell", "nyxuri", "custom"}:
        return "nyxuri-shell"
    if value == "noctalia":
        return "noctalia"
    return default


def custom_shell_bin() -> str:
    ledger = read_ledger()
    val = ledger.get("custom_shell_bin") or ledger.get("nyxuri_shell_bin", "")
    return str(val) if isinstance(val, str) else ""


def nyxuri_shell_bin() -> str:
    return custom_shell_bin()


def set_shell(shell_name: str, bin_path: str | None = None) -> dict[str, Any]:
    s = str(shell_name).strip().lower()
    if s in {"nyxuri-shell", "nyxuri", "custom"}:
        canonical = "nyxuri-shell"
    elif s == "noctalia":
        canonical = "noctalia"
    else:
        raise ValueError(f"Invalid shell: {shell_name} (must be 'noctalia' or 'nyxuri-shell')")
    changes: dict[str, Any] = {"active_shell": canonical}
    if bin_path is not None:
        changes["custom_shell_bin"] = bin_path
    return update_ledger(**changes)


# --- unit records (KM0 frozen five-field shape) ---------------------------


def all_units() -> dict[str, dict[str, Any]]:
    """Every unit record in the ledger, keyed by unit id."""
    units = read_ledger().get("units")
    if not isinstance(units, dict):
        return {}
    return {uid: dict(rec) for uid, rec in units.items() if isinstance(rec, dict)}


def get_unit(unit_id: str) -> dict[str, Any] | None:
    """One unit record, or None when the unit was never switched."""
    return all_units().get(unit_id)


def set_unit(
    unit_id: str,
    *,
    state: str,
    preset: str = "default",
    files: dict[str, str] | None = None,
    vault: str | None = None,
    updated: str | None = None,
) -> dict[str, Any]:
    """Upsert one unit record, enforcing the frozen five-field shape.

    ``state``: ``enabled`` / ``disabled`` (the only switch axis).
    ``preset``: current form-axis choice. ``files``: ``{relpath: sha256}``
    snapshot of managed files. ``vault``: archive location of the user's
    custom files — mandatory once the unit is ``disabled``. ``updated``:
    ISO timestamp, defaulted to now (UTC).
    """
    if not _safe_unit_id(unit_id):
        raise ValueError("invalid unit identifier")
    if state not in UNIT_STATES:
        raise ValueError(f"invalid unit state '{state}' (must be 'enabled' or 'disabled')")
    if not isinstance(preset, str) or not preset:
        raise ValueError("preset must be a non-empty string")
    if files is None:
        files = {}
    if not isinstance(files, dict) or not all(
        isinstance(k, str) and k and k != "." and not Path(k).is_absolute()
        and ".." not in Path(k).parts and isinstance(v, str) for k, v in files.items()
    ):
        raise ValueError("files must map relative paths to hash strings")
    if vault is not None and not isinstance(vault, str):
        raise ValueError("vault must be an archive path string or None")
    if state == "disabled" and not vault:
        raise ValueError(f"disabled unit '{unit_id}' requires a vault archive path")
    if updated is None:
        updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record: dict[str, Any] = {
        "state": state,
        "preset": preset,
        "files": dict(files),
        "vault": vault,
        "updated": updated,
    }
    data = update_ledger(units={unit_id: record})
    return dict(data["units"][unit_id])
