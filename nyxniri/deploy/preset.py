"""Preset mechanism — switch an app's active variant (default / official / user).

Three layers stack, lowest to highest (§2.4)::

    默认 config  ←  官方预设  ←  __custom__ 文件

The active choice lives in a state file ``~/.config/NyxNiri/presets/<app>.active``
(one line: the preset name, or ``default``). This module owns the read/write and
the src-resolution that picks which directory gets deployed for an app.

Write timing (iron law, §3.2): apply flows deploy first, then write the active
file. The dest-missing reset is the only sanctioned write-before-deploy (dest is
empty, so a half-written state self-heals next run).
"""

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

from nyxniri.constants import PROJECT_NAME, Colors
from nyxniri.core import get_env, log_msg
from nyxniri.i18n import msg


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
    from nyxniri.deploy.manifest import discover_deployable_apps

    source = _safe_child(get_env().configs_src, app)
    try:
        return source is not None and app in discover_deployable_apps() and (
            source.is_dir() or source.is_file()
        )
    except OSError:
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
        nyx_fd = _open_child_dir(config_fd, PROJECT_NAME, create=create)
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


def read_active_preset(app: str) -> str:
    """Return the active preset or raise instead of silently deploying defaults."""
    if not _is_deployable_app(app):
        raise InvalidActivePresetError("invalid preset app")
    presets_fd: Optional[int] = None
    try:
        presets_fd = _open_presets_dir()
    except FileNotFoundError:
        return "default"
    except OSError as exc:
        raise InvalidActivePresetError("invalid active preset state") from exc
    try:
        fd = os.open(f"{app}.active", _READ_FLAGS, dir_fd=presets_fd)
    except FileNotFoundError:
        os.close(presets_fd)
        return "default"
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


def resolve_preset_src(app: str, active: str, dest: Path) -> PresetSrcResult:
    """Resolve which source dir to deploy for ``app`` given its ``active`` preset.

    Four branches (§3.2): dest-missing reset; default; official preset;
    user preset. If none matches, src is None (freeze + warn) — we never
    silently fall back to default, which would wipe the user's frozen state.
    """
    env = get_env()
    app_root = _safe_child(env.configs_src, app)
    repo_presets = _safe_child(app_root, "presets") if app_root else None
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
        return PresetSrcResult(src=official, reset_active=None)

    user = _safe_child(user_presets, active)
    if user is not None and is_safe_dir(user):
        return PresetSrcResult(src=user, reset_active=None)

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
    env = get_env()
    app_root = _safe_child(env.configs_src, app)
    repo_presets = _safe_child(app_root, "presets") if app_root else None
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


@dataclass
class PresetInfo:
    """Metadata inspection for an app preset."""
    app: str
    name: str
    source: str          # 'official' | 'user'
    is_active: bool
    path: str
    files: List[str]
    preserve: List[str]
    is_editable: bool
    is_deletable: bool


def get_preset_info(app: str, name: str) -> PresetInfo:
    """Inspect detailed metadata and key files for an app preset."""
    from nyxniri.deploy.manifest import load_manifest_for

    valid = _is_deployable_app(app) and _is_safe_component(name)
    try:
        active = read_active_preset(app) if valid else None
    except InvalidActivePresetError:
        active = None
    is_active = active == name
    src = _find_preset_src(app, name) if valid else None
    source = "official"
    is_editable = False
    is_deletable = False
    if not valid:
        rel_path = "(invalid)"
    elif name == "default":
        rel_path = f"configs/{app}"
    elif src is not None:
        official = _safe_child(get_env().configs_src, app, "presets", name)
        if src == official:
            rel_path = f"configs/{app}/presets/{name}"
        else:
            source = "user"
            is_editable = True
            is_deletable = True
            rel_path = f"~/.config/{PROJECT_NAME}/presets/{app}/{name}"
    else:
        rel_path = f"configs/{app}/presets/{name} (not found)"

    files: List[str] = []
    if src and src.is_dir():
        for p in sorted(src.rglob("*")):
            if p.is_file() and not p.name.startswith(".") and "__custom__" not in p.name:
                if name == "default" and "presets" in p.parts:
                    continue
                try:
                    rel = str(p.relative_to(src))
                    files.append(rel)
                except ValueError:
                    pass

    preserve: List[str] = []
    if valid:
        try:
            manifest = load_manifest_for(app)
            preserve = manifest.preserve or []
        except Exception:
            pass

    return PresetInfo(
        app=app,
        name=name,
        source=source,
        is_active=is_active,
        path=rel_path,
        files=files,
        preserve=preserve,
        is_editable=is_editable,
        is_deletable=is_deletable,
    )


def collect_presets(app: str) -> List[Tuple[str, str, bool]]:
    """Return (name, source, is_active) for every preset of an app.

    source is 'official' (shipped in repo) or 'user' (saved under nyx_dir).
    'default' is always first. Used by list_presets (printing) and the TUI
    switcher. An invalid active-state file is reported and returns no choices,
    so callers never silently treat it as the default preset.
    """
    if not _is_deployable_app(app):
        return []
    try:
        active = read_active_preset(app)
    except InvalidActivePresetError:
        print(msg("preset_warn_invalid_active", app))
        return []
    entries: List[Tuple[str, str, bool]] = [("default", "official", active == "default")]

    env = get_env()
    app_root = _safe_child(env.configs_src, app)
    official_dir = _safe_child(app_root, "presets") if app_root else None
    if official_dir is not None and official_dir.is_dir() and not official_dir.is_symlink():
        for p in sorted(official_dir.iterdir(), key=lambda x: x.name):
            if _is_safe_component(p.name) and p.is_dir() and not p.is_symlink():
                entries.append((p.name, "official", active == p.name))
    user_dir = _safe_child(env.presets_dir, app)
    if user_dir is not None and user_dir.is_dir() and not user_dir.is_symlink():
        for p in sorted(user_dir.iterdir(), key=lambda x: x.name):
            if _is_safe_component(p.name) and p.is_dir() and not p.is_symlink():
                entries.append((p.name, "user", active == p.name))
    return entries


def list_presets(app: str) -> List[Tuple[str, str, bool]]:
    """List presets for an app; the active one is marked. ``list`` is status.

    Prints a numbered list with the active entry prefixed by ``*``.
    """
    entries = collect_presets(app)
    print(msg("preset_list_title", app))
    for i, (name, source, is_active) in enumerate(entries, 1):
        marker = "*" if is_active else " "
        tag = msg(f"preset_src_{source}")
        print(f"  {marker} [{i}] {name}  {Colors.DIM}{tag}{Colors.RESET}")
    return entries


def _render_preset_result(app: str, name: str, preserved_lines: List[str], failed: bool = False) -> None:
    """Lightweight feedback reusing the completion screen's preserved section."""
    if failed:
        print(msg("preset_apply_failed", app, name))
        return
    print(msg("preset_applied", app, name))
    if preserved_lines:
        print(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_preserved')}{Colors.RESET}")
        for pline in sorted(set(preserved_lines)):
            print(f"    {pline}")


def apply_preset(app: str, name: str) -> bool:
    """Switch an app to a named preset (narrow deploy path).

    Runs only atomic_replace + template render for this app — no hardware
    patches, no post-install services (§9: switching kitty must not rerun
    fisher). Writes the active file AFTER deploy succeeds (iron law, §3.2).

    The manifest ``preserve`` list (e.g. niri/monitor.kdl, niri/effects.kdl) is
    honoured just like the full-deploy path: a preset switch must not wipe
    runtime-managed files the new variant doesn't ship.
    """
    from nyxniri.deploy.templates import _phase_render_templates
    from nyxniri.deploy.atomic import atomic_replace_item
    from nyxniri.deploy.manifest import load_manifest_for

    env = get_env()
    dest = _safe_child(env.config_dir, app)
    if not _is_deployable_app(app) or not _is_safe_component(name) or dest is None:
        print(msg("preset_not_found", app, name))
        return False
    src = _find_preset_src(app, name)
    if src is None:
        print(msg("preset_not_found", app, name))
        return False

    # Preserve the same manifest-declared files the full deploy would; a preset
    # switch is otherwise indistinguishable to runtime state like effects.kdl.
    preserve = None
    try:
        preserve = load_manifest_for(app).preserve or None
    except Exception:
        pass

    preserved_log: List[str] = []
    if not atomic_replace_item(src, dest, preserved_log=preserved_log, preserve=preserve):
        _render_preset_result(app, name, preserved_log, failed=True)
        return False

    _phase_render_templates(only_app=app)
    # deploy-then-write: a crash mid-flow must not leave active pointing at a
    # preset whose deploy didn't complete (would skip re-deploy next run). §3.2
    try:
        write_active_preset(app, name)
    except OSError as e:
        # Deploy landed but the choice was not recorded — say so loudly instead
        # of a bare traceback; next update would otherwise redeploy defaults.
        print(msg("preset_apply_failed", app, name))
        log_msg("ERROR", f"Deployed preset '{name}' to {app} but recording active state failed: {e}")
        return False
    _render_preset_result(app, name, preserved_log)
    return True


def _ignore_custom_and_manifest(_src_dir, names):
    """copytree ignore: drop __custom__ entries (any depth) and .module.toml."""
    return {n for n in names if "__custom__" in n or n == ".module.toml"}


def save_preset(app: str, name: str) -> bool:
    """Snapshot current ~/.config/<app>/ into a user preset, minus __custom__.

    'default' is reserved (apply default = reset). Official-name collisions
    are rejected (official presets win on name). §2.2
    """
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    if not _is_deployable_app(app) or not _is_safe_component(name):
        print(msg("preset_not_found", app, name))
        return False
    env = get_env()
    dest = _safe_child(env.config_dir, app)
    if dest is None or not dest.is_dir() or dest.is_symlink():
        print(msg("preset_nothing_to_save", app))
        return False
    official = _safe_child(env.configs_src, app, "presets", name)
    if official is not None and official.is_dir() and not official.is_symlink():
        print(msg("preset_official_name_collision", name))
        return False

    try:
        with ExitStack() as stack:
            src_fd = os.open(dest, _DIR_FLAGS)
            stack.callback(os.close, src_fd)
            presets_fd = _open_presets_dir(create=True)
            stack.callback(os.close, presets_fd)
            user_fd = _open_child_dir(presets_fd, app, create=True)
            stack.callback(os.close, user_fd)
            try:
                _remove_tree_at(user_fd, name)
            except FileNotFoundError:
                pass
            os.mkdir(name, mode=0o700, dir_fd=user_fd)
            target_fd = os.open(name, _DIR_FLAGS, dir_fd=user_fd)
            stack.callback(os.close, target_fd)
            shutil.copytree(
                f"/proc/self/fd/{src_fd}",
                f"/proc/self/fd/{target_fd}",
                symlinks=True,
                ignore=_ignore_custom_and_manifest,
                dirs_exist_ok=True,
            )
            current = os.stat(name, dir_fd=user_fd, follow_symlinks=False)
            bound = os.fstat(target_fd)
            if (current.st_dev, current.st_ino) != (bound.st_dev, bound.st_ino):
                raise OSError("preset target changed while saving")
    except OSError:
        print(msg("preset_not_found", app, name))
        return False
    print(msg("preset_saved", app, name))
    return True


def delete_preset(app: str, name: str) -> bool:
    """Delete a user preset. Official presets cannot be deleted. §2.5"""
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    if not _is_deployable_app(app) or not _is_safe_component(name):
        print(msg("preset_not_found", app, name))
        return False
    env = get_env()
    official = _safe_child(env.configs_src, app, "presets", name)
    if official is not None and official.is_dir() and not official.is_symlink():
        print(msg("preset_delete_official_denied", name))
        return False
    try:
        presets_fd = _open_presets_dir()
        try:
            user_fd = _open_child_dir(presets_fd, app)
            try:
                _remove_tree_at(user_fd, name)
            finally:
                os.close(user_fd)
        finally:
            os.close(presets_fd)
    except OSError:
        print(msg("preset_not_found", app, name))
        return False
    print(msg("preset_deleted", app, name))
    return True

def edit_preset(app: str, name: str) -> bool:
    """Open a user preset's directory in $EDITOR (rejects default + official).

    Default is reserved; official presets are repo-owned read-only. Only user
    presets under ~/.config/NyxNiri/presets/<app>/<name>/ are editable in place;
    re-running ``apply <name>`` deploys the edits. Non-interactive → hint path.
    """
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    if not _is_deployable_app(app) or not _is_safe_component(name):
        print(msg("preset_not_found", app, name))
        return False
    env = get_env()
    official = _safe_child(env.configs_src, app, "presets", name)
    if official is not None and official.is_dir() and not official.is_symlink():
        print(msg("preset_edit_official_denied", name))
        return False
    try:
        with ExitStack() as stack:
            presets_fd = _open_presets_dir()
            stack.callback(os.close, presets_fd)
            user_parent_fd = _open_child_dir(presets_fd, app)
            stack.callback(os.close, user_parent_fd)
            target_fd = os.open(name, _DIR_FLAGS, dir_fd=user_parent_fd)
            stack.callback(os.close, target_fd)
            if not sys.stdin.isatty():
                print(msg("preset_edit_notty", env.presets_dir / app / name))
                return False
            editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
            subprocess.run(
                [editor, f"/proc/self/fd/{target_fd}"],
                check=False,
                pass_fds=(target_fd,),
            )
    except OSError:
        print(msg("preset_not_found", app, name))
        return False
    print(msg("preset_edit_opened", app, name))
    return True
