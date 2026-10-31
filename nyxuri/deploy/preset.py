"""Preset mechanism — switch an app's active variant (default / official / user).

Three layers stack, lowest to highest (§2.4)::

    默认 config  ←  官方预设  ←  __custom__ 文件

The active choice lives in a state file ``~/.config/nyxuri/presets/<app>.active``
(one line: the preset name, or ``default``). This module owns the read/write and
the src-resolution that picks which directory gets deployed for an app.

Write timing (iron law, §3.2): apply flows deploy first, then write the active
file. The dest-missing reset is the only sanctioned write-before-deploy (dest is
empty, so a half-written state self-heals next run).
"""

import fnmatch
import os
import secrets
import shutil
import stat
import subprocess
import sys
import unicodedata
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from nyxuri.core import Colors, STORAGE_NAME
from nyxuri.core import get_env, log_msg, timed_run
from nyxuri.core import msg


_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


class InvalidActivePresetError(ValueError):
    """The active preset slot is present but cannot be safely used."""


def _is_safe_component(value: str) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if value in (".", "..") or Path(value).is_absolute():
        return False
    if os.sep in value or (os.altsep and os.altsep in value):
        return False
    try:
        return len(os.fsencode(value)) <= 255 and all(
            unicodedata.category(char) not in ("Cc", "Cs") for char in value
        )
    except UnicodeEncodeError:
        return False


def _safe_child(root: Path, *parts: str) -> Optional[Path]:
    """Return a non-symlink child contained below root, if it is safe."""
    if not all(_is_safe_component(part) for part in parts):
        return None
    try:
        if root.exists() and root.is_symlink():
            return None
        candidate = root.joinpath(*parts)
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
        current = root
        for part in parts:
            current /= part
            if current.exists() and current.is_symlink():
                return None
        return candidate
    except (OSError, RuntimeError, ValueError):
        return None


def _is_deployable_app(app: str) -> bool:
    if not _is_safe_component(app):
        return False
    from nyxuri.deploy.manifest import discover_deployable_apps, load_manifest_for

    source = _safe_child(get_env().units_src, app)
    try:
        manifest = load_manifest_for(app)
        if manifest.target or manifest.merge or manifest.runtime:
            return False
        return source is not None and app in discover_deployable_apps() and (
            source.is_dir() or source.is_file()
        )
    except (OSError, ValueError, KeyError):
        return False


def _open_dir(path: Path, *, create: bool = False) -> int:
    try:
        return os.open(path, _DIR_FLAGS)
    except FileNotFoundError:
        if not create:
            raise
    path.mkdir(parents=True, exist_ok=True)
    return os.open(path, _DIR_FLAGS)


def _open_child_dir(parent_fd: int, name: str, *, create: bool = False) -> int:
    try:
        return os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
    os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    return os.open(name, _DIR_FLAGS, dir_fd=parent_fd)


def _open_presets_dir(*, create: bool = False) -> int:
    config_fd = _open_dir(get_env().config_dir, create=create)
    try:
        nyx_fd = _open_child_dir(config_fd, STORAGE_NAME, create=create)
    finally:
        os.close(config_fd)
    try:
        return _open_child_dir(nyx_fd, "presets", create=create)
    finally:
        os.close(nyx_fd)


def _remove_tree_at(parent_fd: int, name: str) -> None:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        raise OSError("unsafe preset target")
    child_fd = os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
    try:
        child_info = os.fstat(child_fd)
        if (child_info.st_dev, child_info.st_ino) != (info.st_dev, info.st_ino):
            raise OSError("preset target changed while binding")
        for entry in os.listdir(child_fd):
            entry_info = os.stat(entry, dir_fd=child_fd, follow_symlinks=False)
            if stat.S_ISDIR(entry_info.st_mode):
                _remove_tree_at(child_fd, entry)
            else:
                os.unlink(entry, dir_fd=child_fd)
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise OSError("preset target changed while deleting")
        os.rmdir(name, dir_fd=parent_fd)
    finally:
        os.close(child_fd)


def _ledger_active_preset(app: str) -> str:
    from nyxuri.kernel.ledger import read_ledger
    ledger_presets = read_ledger().get("presets", {})
    if isinstance(ledger_presets, dict) and isinstance(ledger_presets.get(app), str):
        return ledger_presets[app]
    return "default"


def read_active_preset(app: str) -> str:
    """只读取得活动预设；旧 .active 文件的迁移由成功的写事务完成。

    预检和冲突展示会调用此函数，读取不能创建或重写账本。无效状态应报错，
    不能通过静默回退默认预设掩盖来源问题。
    """
    if not _is_deployable_app(app):
        raise InvalidActivePresetError("invalid preset app")
    presets_fd: Optional[int] = None
    try:
        presets_fd = _open_presets_dir()
    except FileNotFoundError:
        return _ledger_active_preset(app)
    except OSError as exc:
        raise InvalidActivePresetError("invalid active preset state") from exc
    try:
        fd = os.open(f"{app}.active", _READ_FLAGS, dir_fd=presets_fd)
    except FileNotFoundError:
        os.close(presets_fd)
        return _ledger_active_preset(app)
    except OSError as exc:
        os.close(presets_fd)
        raise InvalidActivePresetError("invalid active preset state") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise InvalidActivePresetError("invalid active preset state")
        content = os.read(fd, 4097)
    finally:
        os.close(fd)
        if presets_fd is not None:
            os.close(presets_fd)
    try:
        name = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidActivePresetError("invalid active preset state") from exc
    if len(content) > 4096 or not _is_safe_component(name):
        raise InvalidActivePresetError("invalid active preset state")
    return name


def write_active_preset(app: str, name: str) -> None:
    """Atomically write the active preset file (temp + rename).

    Atomic replacement prevents a half-written state file from freezing a
    deployment (§3.2).
    """
    if not _is_deployable_app(app):
        raise ValueError("invalid preset app")
    if not _is_safe_component(name):
        raise ValueError("invalid preset name")
    presets_fd = _open_presets_dir(create=True)
    tmp = f".{app}.active.{secrets.token_hex(16)}"
    try:
        try:
            current = os.stat(f"{app}.active", dir_fd=presets_fd, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current is not None and not stat.S_ISREG(current.st_mode):
            raise OSError("unsafe active preset target")
        fd = os.open(
            tmp,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=presets_fd,
        )
        try:
            os.write(fd, name.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, f"{app}.active", src_dir_fd=presets_fd, dst_dir_fd=presets_fd)
        from nyxuri.kernel.ledger import read_ledger, update_ledger
        presets = read_ledger().get("presets", {})
        update_ledger(presets={**(presets if isinstance(presets, dict) else {}), app: name})
    finally:
        try:
            os.unlink(tmp, dir_fd=presets_fd)
        except FileNotFoundError:
            pass
        finally:
            os.close(presets_fd)


@dataclass
class PresetSrcResult:
    """Outcome of resolving an app's active preset to a deploy source."""

    src: Optional[Path]          # None → freeze dest, skip deploy (preset not found)
    reset_active: Optional[str]  # write this before deploy (dest-missing reset to default)
    warnings: List[str] = field(default_factory=list)
    base_src: Optional[Path] = None
    base_include: List[str] = field(default_factory=list)
    base_exclude: List[str] = field(default_factory=list)


def resolve_preset_inheritance(
    app: str, name: str
) -> Tuple[Optional[Path], List[str], List[str]]:
    """Determine whether preset `name` of `app` inherits from `configs/<app>`.

    Returns (base_src, include_patterns, exclude_patterns).
    If inheritance is not applicable or not enabled, returns (None, [], []).
    Simultaneously enforces blacklist veto and whitelist match.
    """
    if name == "default":
        return None, [], []

    env = get_env()
    app_root = _safe_child(env.units_src, app)
    if app_root is None or not (app_root.is_dir() and not app_root.is_symlink()):
        return None, [], []

    try:
        from nyxuri.deploy.manifest import load_manifest_for
        manifest = load_manifest_for(app)
    except Exception:
        return None, [], []

    # 1. Blacklist has absolute veto power
    if manifest.preset_standalone:
        if any(fnmatch.fnmatch(name, pat.strip()) for pat in manifest.preset_standalone if pat.strip()):
            return None, [], []

    # 2. Whitelist requirement (if declared)
    if manifest.preset_allow:
        if not any(fnmatch.fnmatch(name, pat.strip()) for pat in manifest.preset_allow if pat.strip()):
            return None, [], []
    elif not manifest.preset_inherit:
        return None, [], []

    return app_root, list(manifest.preset_include), list(manifest.preset_exclude)


def _find_official_presets_dir(app_root: Optional[Path]) -> Optional[Path]:
    if app_root is None:
        return None
    for dirname in ("__presets__", "presets"):
        d = _safe_child(app_root, dirname)
        if d is not None and d.is_dir() and not d.is_symlink():
            return d
    return _safe_child(app_root, "__presets__") or _safe_child(app_root, "presets")


def resolve_preset_src(app: str, active: str, dest: Path) -> PresetSrcResult:
    """Resolve which source dir to deploy for ``app`` given its ``active`` preset.

    Four branches (§3.2): dest-missing reset; default; official preset;
    user preset. If none matches, src is None (freeze + warn) — we never
    silently fall back to default, which would wipe the user's frozen state.
    """
    env = get_env()
    app_root = _safe_child(env.units_src, app)
    repo_presets = _find_official_presets_dir(app_root)
    user_presets = _safe_child(env.presets_dir, app)
    expected_dest = _safe_child(env.config_dir, app)
    if (
        not _is_deployable_app(app)
        or not _is_safe_component(active)
        or app_root is None
        or repo_presets is None
        or user_presets is None
        or expected_dest is None
        or dest != expected_dest
    ):
        return PresetSrcResult(
            src=None,
            reset_active=None,
            warnings=[msg("preset_warn_frozen", app, active)],
        )

    def is_safe_dir(path: Path) -> bool:
        return path.is_dir() and not path.is_symlink()

    # Boundary: user rm -rf'd ~/.config/<app> but the active file still points
    # at a (possibly upstream-removed) preset. Nothing to freeze — reset to
    # default so the next deploy reinstalls defaults. If the original preset is
    # also gone from repo+user, surface an extra warning (upstream rename/remove
    # info must not be swallowed by the dest-missing rule).
    if not dest.exists() and active != "default":
        official = _safe_child(repo_presets, active)
        user = _safe_child(user_presets, active)
        upstream_removed = not (
            official is not None and is_safe_dir(official)
        ) and not (user is not None and is_safe_dir(user))
        warnings: List[str] = []
        if upstream_removed:
            warnings.append(msg("preset_warn_upstream_removed", app, active))
        return PresetSrcResult(src=app_root, reset_active="default", warnings=warnings)

    if active == "default":
        return PresetSrcResult(src=app_root, reset_active=None)

    official = _safe_child(repo_presets, active)
    if official is not None and is_safe_dir(official):
        base_src, base_inc, base_exc = resolve_preset_inheritance(app, active)
        return PresetSrcResult(
            src=official,
            reset_active=None,
            base_src=base_src,
            base_include=base_inc,
            base_exclude=base_exc,
        )

    user = _safe_child(user_presets, active)
    if user is not None and is_safe_dir(user):
        base_src, base_inc, base_exc = resolve_preset_inheritance(app, active)
        return PresetSrcResult(
            src=user,
            reset_active=None,
            base_src=base_src,
            base_include=base_inc,
            base_exclude=base_exc,
        )

    # Active points at a preset that no longer exists anywhere — freeze dest,
    # do NOT fall back to default (would silently wipe the user's config).
    return PresetSrcResult(
        src=None,
        reset_active=None,
        warnings=[msg("preset_warn_frozen", app, active)],
    )


# --- CLI-facing operations ----------------------------------------------------

def _find_preset_src(app: str, name: str) -> Optional[Path]:
    """Direct lookup of a named preset (apply flow). No dest-missing reset.

    Distinct from resolve_preset_src (update flow): apply is an explicit user
    choice, so a missing dest does not silently reset to default — the named
    preset is deployed as-is. 'default' resolves to the app root.
    """
    if not _is_deployable_app(app) or not _is_safe_component(name):
        return None
    try:
        from nyxuri.deploy.manifest import load_manifest_for
        manifest = load_manifest_for(app)
        if manifest.parts and name in {cfg.get("source_dir", slot) for slot, cfg in manifest.parts.items()}:
            return None
    except Exception:
        pass
    env = get_env()
    app_root = _safe_child(env.units_src, app)
    repo_presets = _find_official_presets_dir(app_root)
    user_presets = _safe_child(env.presets_dir, app)
    if app_root is None or repo_presets is None or user_presets is None:
        return None
    if name == "default":
        return app_root if (app_root.is_dir() or app_root.is_file()) and not app_root.is_symlink() else None
    official = _safe_child(repo_presets, name)
    if official is not None and official.is_dir() and not official.is_symlink():
        return official
    user = _safe_child(user_presets, name)
    if user is not None and user.is_dir() and not user.is_symlink():
        return user
    return None


def list_parts(app: str) -> dict:
    """Return declared parts slots and available variant options for an app."""
    from nyxuri.deploy.manifest import load_manifest_for
    try:
        manifest = load_manifest_for(app)
    except Exception:
        return {}
    if not manifest.parts:
        return {}
    env = get_env()
    app_root = _safe_child(env.units_src, app)
    official_dir = _find_official_presets_dir(app_root)
    result = {}
    for slot, cfg in manifest.parts.items():
        slot_info = dict(cfg)
        variants = []
        source_dir_name = cfg.get("source_dir", slot)
        if official_dir:
            src_slot_dir = _safe_child(official_dir, source_dir_name)
            if src_slot_dir and src_slot_dir.is_dir():
                for item in sorted(src_slot_dir.iterdir()):
                    if not item.name.startswith(".") and not item.is_symlink():
                        variants.append(item.stem if item.is_file() else item.name)
        slot_info["variants"] = variants
        result[slot] = slot_info
    return result


def apply_part(app: str, slot: str, variant: str, *, force: bool = False,
               _preserve_conflicts: bool = False) -> bool:
    """切换已启用单元的零件，保留未写路径，原子提交选择与实际部署基线。

    普通冲突保留原件并取消本次切换；显式 force 在可恢复快照成功后采用模板。
    内部刷新使用 _preserve_conflicts，只跳过已修改零件，不把个人版本重新认领。
    """
    from datetime import datetime, timezone
    from nyxuri.kernel import ledger, registry, transaction
    from nyxuri.deploy.atomic import atomic_replace_item, _path_identity
    from nyxuri.tui import choose_conflict_policy

    try:
        with ledger.mutation_lock():
            record = ledger.get_unit(app)
            manifest = registry.load_unit(app)
            if not record or record.get("state") != "enabled" or manifest.target or manifest.merge or manifest.runtime:
                log_msg("WARN", f"Part switch requires an enabled directory unit: {app}")
                return False
            if slot not in manifest.parts or not _is_safe_component(variant):
                return False
            cfg = manifest.parts[slot]
            relative = cfg.get("target")
            source_dir = cfg.get("source_dir", slot)
            if not isinstance(relative, str) or not relative or not _is_safe_component(source_dir):
                return False
            destination = transaction._safe_leaf(get_env().config_dir / app, relative)
            official = _find_official_presets_dir(registry.unit_dir(app))
            sources = _safe_child(official, source_dir) if official else None
            candidate = next((p for p in sorted(sources.iterdir())
                              if (p.name == variant or p.stem == variant) and not p.is_symlink()), None) if sources and sources.is_dir() else None
            if candidate is None:
                return False
            is_file = candidate.is_file()
            prefix = relative + "/"
            baseline = {}
            for rel, digest in record.get("files", {}).items():
                if is_file and rel == relative:
                    baseline[destination.name] = digest
                elif not is_file and rel.startswith(prefix):
                    baseline[rel[len(prefix):]] = digest
            conflicts = []
            for rel, src in transaction._leaves(candidate):
                target = transaction._safe_leaf(destination, rel, single=is_file)
                if target.exists() or target.is_symlink():
                    identity = _path_identity(target)
                    if identity != baseline.get(destination.name if is_file else rel) and identity != _path_identity(src):
                        conflicts.append(relative if is_file else prefix + rel)
            if conflicts and _preserve_conflicts and not force:
                return True
            decision = choose_conflict_policy([app], force=force, conflicts={app: conflicts})
            if decision is None or (conflicts and not decision):
                return False
            if decision and conflicts:
                backup = transaction.backup_conflicts(app, conflicts)
                print(f"Backup: {backup}")
            metadata = ledger.get_deployment(app) or transaction._metadata(manifest, get_env().config_dir / app)
            ledger.set_deployment(app, **{**metadata, "pending": "part_deploy",
                                          "pending_part": {"slot": slot, "variant": variant}})
            carried = {}
            if not atomic_replace_item(candidate, destination, carry=True,
                    carry_baseline=None if decision else baseline,
                    carry_unknown=not decision, carried_out=carried):
                return False
            files = dict(record.get("files", {}))
            # 删除旧零件不再铺设的未修改项；carry 项保留旧hash，不用当前个人内容替换。
            for rel in list(files):
                if rel == relative or rel.startswith(prefix):
                    del files[rel]
            for rel, path in transaction._leaves(destination):
                key = relative if is_file else prefix + rel
                if rel in carried:
                    if rel in baseline:
                        files[key] = baseline[rel]
                else:
                    files[key] = _path_identity(path)
            updated = {**record, "files": files,
                       "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            ledger.update_ledger(units={app: updated}, parts={f"{app}:{slot}": variant})
            ledger.set_deployment(app, pending="part_reload" if manifest.preset_reload else None)
            if manifest.preset_reload:
                from nyxuri.desktop.presets import _reload_preset
                if not _reload_preset(manifest):
                    return False
            ledger.set_deployment(app, pending=None, pending_part=None)
            return True
    except (KeyError, OSError, ValueError, RuntimeError) as exc:
        log_msg("ERROR", f"Part switch failed for {app}:{slot}: {exc}")
        return False


def get_active_part(app: str, slot: str) -> str:
    """Return the currently active variant for an app's part slot."""
    from nyxuri.kernel.ledger import read_ledger
    ledger = read_ledger()
    parts = ledger.get("parts", {})
    if isinstance(parts, dict) and f"{app}:{slot}" in parts:
        val = parts[f"{app}:{slot}"]
        if isinstance(val, str) and val:
            return val
    try:
        from nyxuri.deploy.manifest import load_manifest_for
        m = load_manifest_for(app)
        if slot in m.parts:
            return m.parts[slot].get("default", "default")
    except Exception:
        pass
    return "default"

