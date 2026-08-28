"""Checkbox-style uninstall (§8): the user picks what to remove.

Shared path primitives (copy_path, remove_path from core) and snapshot lookup
(get_all_backups, rollback_configs) come from state.backup — the legacy
'restore' mode folds into rollback. Execution order (§8.6): module
uninstallers first (fcitx reads .prev in state_dir), then user-territory
deletions, then nyx_dir + state last.
"""

import datetime
import sys
from pathlib import Path

from nyxniri.constants import CLI_CMD, PROJECT_NAME
from nyxniri.core import get_env, get_pics_dir, log_msg, copy_path, remove_path, is_nyxniri_cli_symlink, clear_nyxniri_cli_symlink_marker
from nyxniri.i18n import msg
from nyxniri.tui import CheckboxEntry, CheckboxList, drain_stdin, prompt_confirm
from nyxniri.state.backup import get_all_backups, rollback_configs


def _rm_report(path: Path) -> None:
    """Remove a path and print a result line ([✓] removed / [!] skipped)."""
    if path.is_symlink() or path.exists():
        remove_path(path)
        print(msg("uninstall_removed", str(path)))
    else:
        print(msg("uninstall_skipped", str(path)))


def uninstall_nyxniri(mode: str = "") -> bool:
    """Checkbox-style uninstall (§8): the user picks what to remove.

    Defaults = the old 'standard' scope (archive configs + CLI + installed
    modules, now including greeter + fisher — fixes gaps #4). purge/--all and
    non-interactive = all selected. Legacy 'restore' rolls back to the origin
    snapshot (folded into `nyxniri rollback`).
    """
    from nyxniri.deploy.deploy import discover_config_items
    from nyxniri.modules.fcitx import fcitx5_installed, fcitx_uninstall
    from nyxniri.modules.fisher import fisher_installed, fisher_uninstall
    from nyxniri.modules.greeter import greeter_installed, greeter_uninstall
    from nyxniri.modules.gtktheme import gtktheme_registered, gtktheme_uninstall

    env = get_env()
    items = discover_config_items()

    # --- Legacy mode aliases ---
    if mode in ("1", "safe", "--safe", "standard"):
        mode = ""  # interactive checkbox (or all+archive when non-TTY)
    elif mode in ("2", "--restore", "restore"):
        # Restore folded into `nyxniri rollback`; kept as a legacy alias.
        backups = get_all_backups()
        if not backups:
            print(msg("no_backups_found"))
            return False
        print(msg("log_restoring_origin_config", backups[0].name))
        rollback_configs(str(backups[0]))
        print(msg("restore_origin_done"))
        return True
    elif mode in ("3", "--purge", "purge", "--all", "all"):
        mode = "all"

    # --- Detect installed modules (only installed ones are shown) ---
    has_fcitx = fcitx5_installed()
    has_gtk = gtktheme_registered()
    has_greeter = greeter_installed()
    has_fisher = fisher_installed()

    # --- Build checkbox entries (defaults = standard scope) ---
    entries = [
        CheckboxEntry(key="__sep_user__", label=msg("uninstall_group_user"), is_separator=True),
        CheckboxEntry(key="configs", label=msg("uninstall_item_configs", len(items)), checked=True),
        CheckboxEntry(key="nyx_dir", label=msg("uninstall_item_nyx_dir"), checked=False),
        CheckboxEntry(key="archives", label=msg("uninstall_item_archives"), checked=False),
        CheckboxEntry(key="wallpapers", label=msg("uninstall_item_wallpapers"), checked=False),
        CheckboxEntry(key="__sep_self__", label=msg("uninstall_group_self"), is_separator=True),
        CheckboxEntry(key="cli", label=msg("uninstall_item_cli"), checked=True),
        CheckboxEntry(key="state", label=msg("uninstall_item_state"), checked=False),
        CheckboxEntry(key="cache", label=msg("uninstall_item_cache"), checked=False),
    ]
    module_entries = []
    if has_fcitx:
        module_entries.append(CheckboxEntry(key="fcitx", label=msg("uninstall_item_fcitx"), checked=True))
    if has_gtk:
        module_entries.append(CheckboxEntry(key="gtk", label=msg("uninstall_item_gtk"), checked=True))
    if has_greeter:
        module_entries.append(CheckboxEntry(key="greeter", label=msg("uninstall_item_greeter"), checked=True))
    if has_fisher:
        module_entries.append(CheckboxEntry(key="fisher", label=msg("uninstall_item_fisher"), checked=True))
    if module_entries:
        entries.append(CheckboxEntry(key="__sep_mod__", label=msg("uninstall_group_modules"), is_separator=True))
        entries.extend(module_entries)

    all_keys = [e.key for e in entries if not e.is_separator]

    # --- Resolve the selected key set + whether configs are archived ---
    if mode == "all":
        selected = set(all_keys)
        archive_configs = False  # purge = delete, no archive
        if sys.stdin.isatty():
            print(msg("purge_warning"))
            if not prompt_confirm("purge_prompt", "n"):
                print(msg("purge_cancelled"))
                return False
            print(msg("purge_start"))
    elif not sys.stdin.isatty():
        # Non-interactive (pipe) → all selected; archive configs for safety.
        selected = set(all_keys)
        archive_configs = True
    else:
        # Interactive checkbox.
        chk = CheckboxList("uninstall_title", entries, hint_key="uninstall_hint")
        chosen = chk.run()
        if chosen is None:
            print(msg("log_uninstall_cancelled"))
            return False
        selected = set(chosen)
        archive_configs = True

    # --- Execute (inherited purge order; §8.6) ---
    # Snapshot pre-existing archives first: if 'configs' archives this run AND
    # 'archives' is also selected (non-TTY/purge), the archives step must not
    # delete the archive we just created.
    existing_archives = sorted(env.config_dir.glob(f"{PROJECT_NAME}_archive_*"))

    # Drain the confirming Enter's residue + any held-repeat burst before any
    # module uninstaller runs — greeter's sudo reads /dev/tty directly (bypassing
    # read_key), so stale \r would feed its password prompt as bad input.
    drain_stdin()

    # 1. Module uninstallers FIRST — fcitx reads .prev in state_dir; greeter's
    #    sudo restore+rm runs here. nyx_dir/state must outlive these.
    for key, fn, label in (
        ("fcitx", fcitx_uninstall, "fcitx"),
        ("gtk", gtktheme_uninstall, "GTK theme"),
        ("greeter", greeter_uninstall, "greeter"),
        ("fisher", fisher_uninstall, "fisher"),
    ):
        if key in selected:
            try:
                if not fn():
                    log_msg("WARN", f"{label} uninstall reported failure")
                    print(msg("uninstall_failed", label))
                    return False
                print(msg("uninstall_module_done", label))
            except Exception as e:
                log_msg("WARN", f"{label} uninstall failed: {e}")
                print(msg("uninstall_failed", label))
                return False

    # 2. Configs — archive-then-delete (interactive), or delete-only (purge).
    if "configs" in selected:
        archive_dir = None
        if archive_configs:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_dir = env.config_dir / f"{PROJECT_NAME}_archive_{timestamp}"
            archive_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            p = env.config_dir / item
            if p.exists() or p.is_symlink():
                if archive_dir is not None:
                    copy_path(p, archive_dir / item)
                remove_path(p)
                print(msg("log_remove_item", item))
        if archive_dir is not None:
            print(msg("uninstall_archived", str(archive_dir)))

    # 3. nyx_dir (~/.config/NyxNiri/: snapshots + presets) + legacy ~/.config/ snapshots.
    if "nyx_dir" in selected:
        for backup in get_all_backups():
            remove_path(backup)
        _rm_report(env.config_dir / PROJECT_NAME)

    # 4. Archives (~/.config/NyxNiri_archive_*) — gap #1 fix. Only pre-existing
    #    ones (the snapshot above), so a freshly-created config archive survives.
    if "archives" in selected:
        for p in existing_archives:
            _rm_report(p)

    # 5. Wallpapers.
    if "wallpapers" in selected:
        _rm_report(get_pics_dir() / "Wallpapers")

    # 6. CLI entry.
    if "cli" in selected:
        target_bin = env.home / ".local/bin" / CLI_CMD
        if is_nyxniri_cli_symlink(target_bin):
            target_bin.unlink(missing_ok=True)
            clear_nyxniri_cli_symlink_marker()
            print(msg("uninstall_removed", str(target_bin)))
        else:
            print(msg("uninstall_skipped", str(target_bin)))

    # 7. state_dir — AFTER module uninstallers (.prev lives here). §8.6
    if "state" in selected:
        _rm_report(env.state_dir)

    # 8. cache_dir.
    if "cache" in selected:
        _rm_report(env.cache_dir)

    if env.run_mode == "system":
        print(msg("uninstall_system_hint"))

    print(msg("uninstall_done"))
    log_msg("INFO", f"Uninstall completed (selected: {sorted(selected)})")
    return True
