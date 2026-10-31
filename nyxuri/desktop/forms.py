"""Form flows — the user-facing half of the form mechanism.

apply / save / delete / edit + the listing/info surfaces. All file
mechanics (fd safety, staging, inheritance, ledger writes) live in
the engine half at ``nyxuri.deploy.forms``; this module only composes them
into interactive flows and renders the results (渲染归 UI 域).
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

from nyxuri.core import Colors, STORAGE_NAME, get_env, log_msg, msg
from nyxuri.deploy.forms import (
    InvalidActiveFormError,
    _DIR_FLAGS,
    _find_official_forms_dir,
    _is_deployable_app,
    _is_safe_component,
    _open_child_dir,
    _open_forms_dir,
    _remove_tree_at,
    _safe_child,
    read_active_form,
    use_form,
)

@dataclass
class FormInfo:
    """Metadata inspection for a plugin's whole-axis form."""
    app: str
    name: str
    source: str          # 'official' | 'user'
    is_active: bool
    path: str
    files: List[str]
    preserve: List[str]
    is_editable: bool
    is_deletable: bool


def get_form_info(app: str, name: str) -> FormInfo:
    """Inspect detailed metadata and key files for a plugin's form."""
    from nyxuri.deploy.manifest import load_manifest_for

    valid = _is_deployable_app(app) and _is_safe_component(name)
    try:
        active = read_active_form(app) if valid else None
    except InvalidActiveFormError:
        active = None
    is_active = active == name
    app_root = _safe_child(get_env().plugins_src, app) if valid else None
    official_dir = _find_official_forms_dir(app_root)
    official = _safe_child(official_dir, name) if official_dir else None
    user_src = _safe_child(get_env().forms_dir, app, name)
    source = "official"
    is_editable = False
    is_deletable = False
    if not valid:
        src = None
        rel_path = "(invalid)"
    elif name == "default":
        src = None
        rel_path = f"configs/{app}"
    elif official is not None and official.is_dir() and not official.is_symlink():
        src = official
        rel_path = f"configs/{app}/__forms__/{name}"
    elif user_src is not None and user_src.is_dir() and not user_src.is_symlink():
        src = user_src
        source = "user"
        is_editable = True
        is_deletable = True
        rel_path = f"~/.config/{STORAGE_NAME}/forms/{app}/{name}"
    else:
        src = None
        rel_path = f"configs/{app}/__forms__/{name} (not found)"

    files: List[str] = []
    if src and src.is_dir():
        for p in sorted(src.rglob("*")):
            if p.is_file() and not p.name.startswith(".") and "__custom__" not in p.name:
                if name == "default" and any(part in ("forms", "__forms__") for part in p.parts):
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

    return FormInfo(
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


def collect_forms(app: str) -> List[Tuple[str, str, bool]]:
    """Return (name, source, is_active) for every whole-axis form of a plugin.

    source is 'official' (shipped in repo) or 'user' (saved under nyx_dir).
    'default' is always first. Used by list_forms (printing) and the TUI
    switcher. Slot-axis source trees under ``__forms__/`` never appear here.
    """
    if not _is_deployable_app(app):
        return []
    active = read_active_form(app)
    slot_source_dirs: set[str] = set()
    try:
        from nyxuri.deploy.manifest import load_manifest_for
        manifest = load_manifest_for(app)
        if manifest.forms:
            slot_source_dirs = {cfg.get("source_dir", slot) for slot, cfg in manifest.forms.items()}
    except Exception:
        pass

    entries: List[Tuple[str, str, bool]] = [("default", "official", active == "default")]

    env = get_env()
    app_root = _safe_child(env.plugins_src, app)
    official_dir = _find_official_forms_dir(app_root)
    if official_dir is not None and official_dir.is_dir() and not official_dir.is_symlink():
        for p in sorted(official_dir.iterdir(), key=lambda x: x.name):
            if p.name in slot_source_dirs:
                continue
            if _is_safe_component(p.name) and p.is_dir() and not p.is_symlink():
                entries.append((p.name, "official", active == p.name))
    user_dir = _safe_child(env.forms_dir, app)
    if user_dir is not None and user_dir.is_dir() and not user_dir.is_symlink():
        for p in sorted(user_dir.iterdir(), key=lambda x: x.name):
            if _is_safe_component(p.name) and p.is_dir() and not p.is_symlink():
                entries.append((p.name, "user", active == p.name))
    return entries


def list_forms(app: str) -> List[Tuple[str, str, bool]]:
    """List whole-axis forms for a plugin; the active one is marked.

    ``use <app> list``-grade status surface: prints a numbered list with the
    active entry prefixed by ``*``.
    """
    entries = collect_forms(app)
    print(msg("preset_list_title", app))
    for i, (name, source, is_active) in enumerate(entries, 1):
        marker = "*" if is_active else " "
        tag = msg(f"preset_src_{source}")
        print(f"  {marker} [{i}] {name}  {Colors.DIM}{tag}{Colors.RESET}")
    return entries


def _render_form_result(app: str, name: str, preserved_lines: List[str], failed: bool = False) -> None:
    """Lightweight feedback reusing the completion screen's preserved section."""
    if failed:
        print(msg("preset_apply_failed", app, name))
        return
    print(msg("preset_applied", app, name))
    if preserved_lines:
        print(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_preserved')}{Colors.RESET}")
        for pline in sorted(set(preserved_lines)):
            print(f"    {pline}")


def apply_form(app: str, name: str) -> bool:
    """Switch a plugin to a named whole-axis form (prose over the engine path).

    The engine's :func:`use_form` owns the narrow deploy and the ledger
    write (deploy-then-write iron law); this wrapper only validates loudly
    and renders the result, including the preserved-file section.
    """
    from nyxuri.deploy.forms import _find_form_src

    if not _is_deployable_app(app) or not _is_safe_component(name):
        print(msg("preset_not_found", app, name))
        return False
    if _find_form_src(app, name) is None:
        print(msg("preset_not_found", app, name))
        return False
    preserved_log: List[str] = []
    if not use_form(app, None, name, preserved_log=preserved_log):
        _render_form_result(app, name, preserved_log, failed=True)
        return False
    _render_form_result(app, name, preserved_log)
    return True


def _ignore_custom_and_manifest(_src_dir, names):
    """copytree ignore: drop __custom__ entries (any depth) and manifest.toml."""
    return {n for n in names if "__custom__" in n or n == "manifest.toml"}


def _discard_staging_form(app: str, staging: str) -> None:
    try:
        forms_fd = _open_forms_dir()
        try:
            user_fd = _open_child_dir(forms_fd, app)
            try:
                _remove_tree_at(user_fd, staging)
            finally:
                os.close(user_fd)
        finally:
            os.close(forms_fd)
    except OSError:
        pass


def save_form(app: str, name: str) -> bool:
    """Snapshot current ~/.config/<app>/ into a user form, minus __custom__.

    'default' is reserved (use default = reset). Official-name collisions
    are rejected (official forms win on name).
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
    official_dir = _find_official_forms_dir(_safe_child(env.plugins_src, app))
    official = _safe_child(official_dir, name) if official_dir else None
    if official is not None and official.is_dir() and not official.is_symlink():
        print(msg("preset_official_name_collision", name))
        return False

    staging = f".{name}.{secrets.token_hex(8)}"
    try:
        with ExitStack() as stack:
            src_fd = os.open(dest, _DIR_FLAGS)
            stack.callback(os.close, src_fd)
            forms_fd = _open_forms_dir(create=True)
            stack.callback(os.close, forms_fd)
            user_fd = _open_child_dir(forms_fd, app, create=True)
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
                raise OSError("form target changed while saving")
            try:
                _remove_tree_at(user_fd, name)
            except FileNotFoundError:
                pass
            os.rename(staging, name, src_dir_fd=user_fd, dst_dir_fd=user_fd)
    except OSError as e:
        _discard_staging_form(app, staging)
        print(msg("preset_save_failed", app, name))
        log_msg("ERROR", f"Failed to save form '{name}' for {app}: {e}")
        return False
    print(msg("preset_saved", app, name))
    return True


def delete_form(app: str, name: str) -> bool:
    """Delete a user form. Official forms cannot be deleted."""
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    if not _is_deployable_app(app) or not _is_safe_component(name):
        print(msg("preset_not_found", app, name))
        return False
    env = get_env()
    official_dir = _find_official_forms_dir(_safe_child(env.plugins_src, app))
    official = _safe_child(official_dir, name) if official_dir else None
    if official is not None and official.is_dir() and not official.is_symlink():
        print(msg("preset_delete_official_denied", name))
        return False
    try:
        forms_fd = _open_forms_dir()
        try:
            user_fd = _open_child_dir(forms_fd, app)
            try:
                _remove_tree_at(user_fd, name)
            finally:
                os.close(user_fd)
        finally:
            os.close(forms_fd)
    except OSError:
        print(msg("preset_not_found", app, name))
        return False
    try:
        if read_active_form(app) == name:
            from nyxuri.deploy.forms import write_active_form
            write_active_form(app, "default")
    except (OSError, ValueError):
        pass
    print(msg("preset_deleted", app, name))
    return True

def edit_form(app: str, name: str) -> bool:
    """Open a user form's directory in $EDITOR (rejects default + official).

    Default is reserved; official forms are repo-owned read-only. Only user
    forms under ~/.config/nyxuri/forms/<app>/<name>/ are editable in place;
    re-running ``use <app> <name>`` deploys the edits. Non-interactive → hint path.
    """
    if name == "default":
        print(msg("preset_name_reserved", name))
        return False
    if not _is_deployable_app(app) or not _is_safe_component(name):
        print(msg("preset_not_found", app, name))
        return False
    env = get_env()
    official_dir = _find_official_forms_dir(_safe_child(env.plugins_src, app))
    official = _safe_child(official_dir, name) if official_dir else None
    if official is not None and official.is_dir() and not official.is_symlink():
        print(msg("preset_edit_official_denied", name))
        return False
    try:
        with ExitStack() as stack:
            forms_fd = _open_forms_dir()
            stack.callback(os.close, forms_fd)
            user_parent_fd = _open_child_dir(forms_fd, app)
            stack.callback(os.close, user_parent_fd)
            target_fd = os.open(name, _DIR_FLAGS, dir_fd=user_parent_fd)
            stack.callback(os.close, target_fd)
            if not sys.stdin.isatty():
                print(msg("preset_edit_notty", env.forms_dir / app / name))
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
