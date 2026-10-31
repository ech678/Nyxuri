"""Preset flows — the user-facing half of the preset mechanism.

apply / save / delete / edit + the listing/info/render surfaces. All file
mechanics (fd safety, staging, inheritance, active-state writes) live in
the engine half at ``nyxuri.deploy.preset``; this module only composes them
into interactive flows and renders the results (渲染归 UI 域, ROADMAP KM3.5).
"""

import os
import secrets
import shutil
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from nyxuri.core import Colors, STORAGE_NAME, get_env, log_msg, msg, timed_run
from nyxuri.deploy.preset import (
    InvalidActivePresetError,
    _DIR_FLAGS,
    _find_official_presets_dir,
    _find_preset_src,
    _is_deployable_app,
    _is_safe_component,
    _open_child_dir,
    _open_presets_dir,
    _remove_tree_at,
    _safe_child,
    resolve_preset_inheritance,
    write_active_preset,
    read_active_preset,
)

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
    from nyxuri.deploy.manifest import load_manifest_for

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
    app_root = _safe_child(get_env().plugins_src, app) if valid else None
    official_dir = _find_official_presets_dir(app_root)
    dir_name = official_dir.name if official_dir else "presets"
    if not valid:
        rel_path = "(invalid)"
    elif name == "default":
        rel_path = f"configs/{app}"
    elif src is not None:
        official = _safe_child(official_dir, name) if official_dir else None
        if src == official:
            rel_path = f"configs/{app}/{dir_name}/{name}"
        else:
            source = "user"
            is_editable = True
            is_deletable = True
            rel_path = f"~/.config/{STORAGE_NAME}/presets/{app}/{name}"
    else:
        rel_path = f"configs/{app}/{dir_name}/{name} (not found)"

    files: List[str] = []
    if src and src.is_dir():
        for p in sorted(src.rglob("*")):
            if p.is_file() and not p.name.startswith(".") and "__custom__" not in p.name:
                if name == "default" and any(part in ("presets", "__presets__") for part in p.parts):
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
    part_source_dirs: set[str] = set()
    try:
        from nyxuri.deploy.manifest import load_manifest_for
        manifest = load_manifest_for(app)
        if manifest.parts:
            part_source_dirs = {cfg.get("source_dir", slot) for slot, cfg in manifest.parts.items()}
    except Exception:
        pass

    entries: List[Tuple[str, str, bool]] = [("default", "official", active == "default")]

    env = get_env()
    app_root = _safe_child(env.plugins_src, app)
    official_dir = _find_official_presets_dir(app_root)
    if official_dir is not None and official_dir.is_dir() and not official_dir.is_symlink():
        for p in sorted(official_dir.iterdir(), key=lambda x: x.name):
            if p.name in part_source_dirs:
                continue
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

    Runs only atomic_replace + template render for this app, without
    post-install services (§9: switching kitty must not rerun
    fisher). Writes the active file AFTER deploy succeeds (iron law, §3.2).

    The manifest ``preserve`` list (e.g. niri/monitor.kdl, niri/effects.kdl) is
    honoured just like the full-deploy path: a preset switch must not wipe
    runtime-managed files the new variant doesn't ship.
    """
    from nyxuri.deploy.templates import _phase_render_templates
    from nyxuri.deploy.atomic import atomic_replace_item
    from nyxuri.deploy.manifest import load_manifest_for

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
    preserve_values = None
    try:
        preset_manifest = load_manifest_for(app)
        preserve = preset_manifest.preserve or None
        preserve_values = preset_manifest.preserve_values or None
    except Exception:
        pass

    base_src, base_inc, base_exc = resolve_preset_inheritance(app, name)
    preserved_log: List[str] = []
    if not atomic_replace_item(
        src,
        dest,
        preserved_log=preserved_log,
        preserve=preserve,
        preserve_values=preserve_values,
        base_src=base_src,
        base_include=base_inc,
        base_exclude=base_exc,
    ):
        _render_preset_result(app, name, preserved_log, failed=True)
        return False

    _phase_render_templates(only_app=app)
    manifest = None
    try:
        manifest = load_manifest_for(app)
    except Exception:
        manifest = None
    if manifest is not None:
        for pattern in manifest.chmod:
            for path in dest.glob(pattern):
                if path.is_file():
                    try:
                        path.chmod(0o755)
                    except OSError:
                        pass
        try:
            from nyxuri.deploy.deploy import _reconcile_active_parts
            for failure in _reconcile_active_parts(app, manifest):
                log_msg("WARN", f"Failed to reconcile active part {failure}")
        except Exception as e:
            log_msg("WARN", f"Failed to reconcile active parts for {app}: {e}")
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
    try:
        from nyxuri.deploy.manifest import load_manifest_for
        manifest = load_manifest_for(app)
        if manifest.preset_reload:
            timed_run(manifest.preset_reload, 2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception as e:
        log_msg("WARN", f"Failed to reload preset for {app}: {e}")
    return True


def _ignore_custom_and_manifest(_src_dir, names):
    """copytree ignore: drop __custom__ entries (any depth) and manifest.toml."""
    return {n for n in names if "__custom__" in n or n == "manifest.toml"}


def _discard_staging_preset(app: str, staging: str) -> None:
    try:
        presets_fd = _open_presets_dir()
        try:
            user_fd = _open_child_dir(presets_fd, app)
            try:
                _remove_tree_at(user_fd, staging)
            finally:
                os.close(user_fd)
        finally:
            os.close(presets_fd)
    except OSError:
        pass


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
    official_dir = _find_official_presets_dir(_safe_child(env.plugins_src, app))
    official = _safe_child(official_dir, name) if official_dir else None
    if official is not None and official.is_dir() and not official.is_symlink():
        print(msg("preset_official_name_collision", name))
        return False

    staging = f".{name}.{secrets.token_hex(8)}"
    try:
        with ExitStack() as stack:
            src_fd = os.open(dest, _DIR_FLAGS)
            stack.callback(os.close, src_fd)
            presets_fd = _open_presets_dir(create=True)
            stack.callback(os.close, presets_fd)
            user_fd = _open_child_dir(presets_fd, app, create=True)
            stack.callback(os.close, user_fd)
            try:
                _remove_tree_at(user_fd, staging)
            except FileNotFoundError:
                pass
            os.mkdir(staging, mode=0o700, dir_fd=user_fd)
            target_fd = os.open(staging, _DIR_FLAGS, dir_fd=user_fd)
            stack.callback(os.close, target_fd)
            shutil.copytree(
                f"/proc/self/fd/{src_fd}",
                f"/proc/self/fd/{target_fd}",
                symlinks=True,
                ignore=_ignore_custom_and_manifest,
                dirs_exist_ok=True,
            )
            current = os.stat(staging, dir_fd=user_fd, follow_symlinks=False)
            bound = os.fstat(target_fd)
            if (current.st_dev, current.st_ino) != (bound.st_dev, bound.st_ino):
                raise OSError("preset target changed while saving")
            try:
                _remove_tree_at(user_fd, name)
            except FileNotFoundError:
                pass
            os.rename(staging, name, src_dir_fd=user_fd, dst_dir_fd=user_fd)
    except OSError as e:
        _discard_staging_preset(app, staging)
        print(msg("preset_save_failed", app, name))
        log_msg("ERROR", f"Failed to save preset '{name}' for {app}: {e}")
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
    official_dir = _find_official_presets_dir(_safe_child(env.plugins_src, app))
    official = _safe_child(official_dir, name) if official_dir else None
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
    try:
        if read_active_preset(app) == name:
            write_active_preset(app, "default")
    except (OSError, ValueError):
        pass
    print(msg("preset_deleted", app, name))
    return True

def edit_preset(app: str, name: str) -> bool:
    """Open a user preset's directory in $EDITOR (rejects default + official).

    Default is reserved; official presets are repo-owned read-only. Only user
    presets under ~/.config/nyxuri/presets/<app>/<name>/ are editable in place;
    re-running ``apply <name>`` deploys the edits. Non-interactive → hint path.
    """
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    if not _is_deployable_app(app) or not _is_safe_component(name):
        print(msg("preset_not_found", app, name))
        return False
    env = get_env()
    official_dir = _find_official_presets_dir(_safe_child(env.plugins_src, app))
    official = _safe_child(official_dir, name) if official_dir else None
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


