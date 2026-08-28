"""Configuration snapshot, backup, rollback, and uninstallation management."""

import datetime
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from nyxniri.constants import Colors, PROJECT_NAME
from nyxniri.core import (
    copy_path,
    get_env,
    log_msg,
    register_temp_path,
)
from nyxniri.i18n import msg
from nyxniri.tui import CheckboxEntry, CheckboxList, Menu, MenuItem, drain_stdin, prompt_confirm, truncate_display


_MANAGED_SNAPSHOT_RE = re.compile(
    r"^(?:(?:snapshot|pre_rollback)_\d{8}_\d{6}(?:_\d+){0,2}|dotfiles_backup_.+)$"
)


def get_backup_base_dir() -> Path:
    """Resolve standard backup base directory ~/.config/NyxNiri/backups."""
    return get_env().config_dir / PROJECT_NAME / "backups"


MAX_SNAPSHOTS = 30


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
    note: str = "", interactive: bool = True, protected_snapshot: Optional[Path] = None
) -> Optional[Path]:
    """Create a complete snapshot of all active dotfiles configurations."""
    from nyxniri.deploy.deploy import discover_config_items

    env = get_env()
    base_dir = get_backup_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    print(msg("backing_up"))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = base_dir / f"snapshot_{timestamp}"
    suffix = 1
    while backup_dir.exists() or backup_dir.is_symlink():
        backup_dir = base_dir / f"snapshot_{timestamp}_{suffix}"
        suffix += 1

    tmp_dir = Path(tempfile.mkdtemp(prefix=".snapshot.", dir=base_dir))
    register_temp_path(tmp_dir)

    items = discover_config_items()
    for item in items:
        cfg_path = env.config_dir / item
        if cfg_path.exists() or cfg_path.is_symlink():
            target = tmp_dir / item
            copy_path(cfg_path, target)
            if interactive:
                print(msg("log_backup_item", item))

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

    # Legacy snapshots directly under ~/.config/
    if env.config_dir.is_dir():
        for d in env.config_dir.iterdir():
            if d.is_dir() and not d.is_symlink() and _MANAGED_SNAPSHOT_RE.fullmatch(d.name):
                backups.append(d)

    return sorted(backups, key=lambda p: p.name)


def _resolve_backup_arg(target_arg: str, backups: List[Path]) -> Optional[Path]:
    """Resolve a CLI snapshot argument only against discovered snapshot paths."""
    value = target_arg.strip()
    if not value:
        return None
    if value.isdigit():
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
    return f"[{index}] {backup.name}{suffix}"


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
        print(f"  {Colors.BOLD_CYAN}[{idx}]{Colors.RESET} {Colors.BOLD_WHITE}{b.name}{Colors.RESET}{note_str}")
        print(f"      {Colors.DARK_GRAY}{b}{Colors.RESET}")
    print()
    return backups


def rollback_configs(target_arg: str = "") -> bool:
    """Restore configuration from a selected historical snapshot."""
    from nyxniri.deploy.atomic import atomic_replace_item
    from nyxniri.deploy.deploy import discover_config_items

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

    env = get_env()
    expected_items = [
        item for item in discover_config_items()
        if (chosen_backup / item).exists() or (chosen_backup / item).is_symlink()
    ]
    if not expected_items:
        print(msg("rollback_no_items"), file=sys.stderr)
        log_msg("ERROR", f"Selected rollback snapshot has no restorable configuration: {chosen_backup}")
        return False

    print(msg("rolling_back", chosen_backup.name))

    # Auto pre-rollback snapshot
    pre_snap = backup_configs(
        note="pre-rollback safety snapshot", interactive=False, protected_snapshot=chosen_backup
    )
    if pre_snap:
        print(msg("pre_rollback_backup", str(pre_snap)))

    if not chosen_backup.is_dir() or chosen_backup.is_symlink():
        print(msg("rollback_source_missing", chosen_backup.name), file=sys.stderr)
        log_msg("ERROR", f"Selected rollback snapshot disappeared: {chosen_backup}")
        return False

    for item in expected_items:
        snap_item = chosen_backup / item
        if not snap_item.exists() and not snap_item.is_symlink():
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            log_msg("ERROR", f"Selected rollback snapshot item disappeared: {snap_item}")
            return False

    for item in expected_items:
        snap_item = chosen_backup / item
        dest_item = env.config_dir / item
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
