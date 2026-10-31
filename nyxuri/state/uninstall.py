"""Checkbox-style uninstall (§8): the user picks what to remove.

Shared path primitives (copy_path, remove_path from core) and snapshot lookup
(get_all_backups, rollback_configs) come from state.backup — the legacy
'restore' mode folds into rollback. Execution order (§8.6): module
uninstallers first (fcitx reads .prev in state_dir), then user-territory
deletions, then nyx_dir + state last.
"""

import datetime
import json
import sys
from pathlib import Path

from nyxuri.core import CLI_CMD, PROJECT_NAME, STORAGE_NAME
from nyxuri.core import (
    get_env,
    get_pics_dir,
    log_msg,
    copy_path,
    remove_path,
    is_nyxuri_cli_symlink,
    clear_nyxuri_cli_symlink_marker,
)
from nyxuri.core import msg
from nyxuri.tui import CheckboxEntry, CheckboxList, drain_stdin, prompt_confirm
from nyxuri.state.backup import get_all_backups, rollback_configs


def _rm_report(path: Path) -> None:
    """Remove a path and print a result line ([✓] removed / [!] skipped)."""
    if path.is_symlink() or path.exists():
        remove_path(path)
        print(msg("uninstall_removed", str(path)))
    else:
        print(msg("uninstall_skipped", str(path)))


def uninstall_nyxuri(mode: str = "") -> bool:
    """Checkbox-style uninstall (§8): the user picks what to remove.

    Defaults = the old 'standard' scope (archive configs + CLI + installed
    modules, now including greeter + fisher — fixes gaps #4). purge/--all and
    non-interactive use the same standard scope. Legacy 'restore' rolls back to the origin
    snapshot (folded into `nyxuri rollback`).
    """
    from nyxuri.deploy.deploy import config_item_dest, discover_config_items
    from nyxuri.kernel import ledger, registry, transaction

    env = get_env()
    items = discover_config_items()

    # --- Legacy mode aliases ---
    if mode in ("1", "safe", "--safe", "standard"):
        mode = ""  # interactive checkbox (or all+archive when non-TTY)
    elif mode in ("2", "--restore", "restore"):
        # Restore folded into `nyxuri rollback`; kept as a legacy alias.
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

    # --- KM3: plugin switches replace the module checkboxes. Enabled plugins
    # with living-area side effects are offered through `off` (cascade off),
    # which vaults customs and wipes to white paper.
    HOOK_PLUGINS = ("fcitx5-rime", "fish", "greeter", "noctalia")
    enabled_hooked = [
        uid for uid in HOOK_PLUGINS
        if uid in registry.plugin_ids()
        and (ledger.get_plugin(uid) or {}).get("state") == "enabled"
    ]

    # --- Build checkbox entries (defaults = standard scope) ---
    entries = [
        CheckboxEntry(key="__sep_user__", label=msg("uninstall_group_user"), is_separator=True),
        CheckboxEntry(key="configs", label=msg("uninstall_item_configs", len(items)), checked=True),
        CheckboxEntry(key="nyx_dir", label=msg("uninstall_item_nyx_dir"), checked=False),
        CheckboxEntry(key="archives", label=msg("uninstall_item_archives"), checked=False),
        CheckboxEntry(key="wallpapers", label=msg("uninstall_item_wallpapers", get_pics_dir()), checked=False),
        CheckboxEntry(key="__sep_self__", label=msg("uninstall_group_self"), is_separator=True),
        CheckboxEntry(key="cli", label=msg("uninstall_item_cli"), checked=True),
        CheckboxEntry(key="state", label=msg("uninstall_item_state"), checked=False),
        CheckboxEntry(key="cache", label=msg("uninstall_item_cache"), checked=False),
    ]
    plugin_entries = [
        CheckboxEntry(key=f"plugin:{uid}", label=msg("uninstall_item_plugin", uid), checked=True)
        for uid in enabled_hooked
    ]
    if plugin_entries:
        entries.append(CheckboxEntry(key="__sep_mod__", label=msg("uninstall_group_plugins"), is_separator=True))
        entries.extend(plugin_entries)

    all_keys = [e.key for e in entries if not e.is_separator]
    default_keys = [e.key for e in entries if not e.is_separator and e.checked]

    # --- Resolve the selected key set + whether configs are archived ---
    if mode == "all":
        selected = set(all_keys)
        archive_configs = False  # purge = delete, no archive
        if sys.stdin.isatty():
            print(msg("purge_warning"))
            if not prompt_confirm("purge_prompt", "n", destructive=True):
                print(msg("purge_cancelled"))
                return False
            print(msg("purge_start"))
    elif not sys.stdin.isatty():
        # Non-interactive (pipe) → the same standard defaults as the checklist.
        selected = set(default_keys)
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
    existing_archives = sorted(
        set(env.config_dir.glob(f"{PROJECT_NAME}_archive_*"))
        | set(env.config_dir.glob(f"{STORAGE_NAME}_archive_*"))
        | set(env.config_dir.glob("NyxNiri_archive_*"))
        | set(env.config_dir.glob("nyxniri_archive_*"))
    )

    # Drain the confirming Enter's residue + any held-repeat burst before any
    # module uninstaller runs — greeter's sudo reads /dev/tty directly (bypassing
    # read_key), so stale \r would feed its password prompt as bad input.
    drain_stdin()

    # 1. Enabled hook plugins FIRST — `off` vaults customs and wipes to white
    #    paper (side-domain cleanup via each plugin's post_remove hook).
    #    nyx_dir/state must outlive these.
    for uid in enabled_hooked:
        if f"plugin:{uid}" in selected:
            try:
                steps = transaction.plugin_off(uid, cascade=True)
                if not all(s.ok for s in steps):
                    log_msg("WARN", f"plugin off reported failure: {uid}")
                    print(msg("uninstall_failed", uid))
                    return False
                print(msg("uninstall_module_done", uid))
            except Exception as e:
                log_msg("WARN", f"plugin off failed for {uid}: {e}")
                print(msg("uninstall_failed", uid))
                return False

    # 2. Configs — archive-then-delete (interactive), or delete-only (purge).
    if "configs" in selected:
        archive_dir = None
        if archive_configs:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{PROJECT_NAME}_archive_{timestamp}"
            archive_dir = env.config_dir / base_name
            suffix = 1
            while True:
                try:
                    archive_dir.mkdir(parents=True, exist_ok=False)
                    break
                except FileExistsError:
                    archive_dir = env.config_dir / f"{base_name}_{suffix}"
                    suffix += 1
        for item in items:
            p = config_item_dest(item)
            if p.exists() or p.is_symlink():
                if archive_dir is not None:
                    copy_path(p, archive_dir / item)
                remove_path(p)
                print(msg("log_remove_item", item))
        if archive_dir is not None:
            print(msg("uninstall_archived", str(archive_dir)))

    # 3. nyx_dir (~/.config/nyxuri/: snapshots, presets, active state, hooks) + legacy snapshots.
    if "nyx_dir" in selected:
        for backup in get_all_backups():
            remove_path(backup)
        _rm_report(env.nyx_dir)
        # Clean historical namespaces as well (zero residue)
        for legacy_name in ("NyxNiri", "nyxniri"):
            legacy_config = env.config_dir / legacy_name
            if legacy_config.exists() and legacy_config != env.nyx_dir:
                _rm_report(legacy_config)

    # 4. Archives (~/.config/Nyxuri_archive_* / NyxNiri_archive_*)
    if "archives" in selected:
        for p in existing_archives:
            _rm_report(p)

    # 5. Wallpapers.
    if "wallpapers" in selected:
        wp_dir = get_pics_dir() / "Wallpapers"
        removed = False
        for marker_name in (".nyxuri-managed.json", ".nyxniri-managed.json"):
            marker = wp_dir / marker_name
            if marker.exists():
                try:
                    names = json.loads(marker.read_text(encoding="utf-8"))
                    if isinstance(names, list):
                        for name in names:
                            if isinstance(name, str) and name not in ("", ".", ".."):
                                target = wp_dir / name
                                if target.parent == wp_dir and (target.exists() or target.is_symlink()):
                                    remove_path(target)
                                    removed = True
                    marker.unlink(missing_ok=True)
                except (OSError, ValueError, TypeError):
                    pass
        if removed:
            print(msg("uninstall_removed", str(wp_dir)))
        else:
            print(msg("uninstall_skipped", str(wp_dir)))

    # 6. CLI entry.
    if "cli" in selected:
        target_bin = env.home / ".local/bin" / CLI_CMD
        if is_nyxuri_cli_symlink(target_bin):
            target_bin.unlink(missing_ok=True)
            clear_nyxuri_cli_symlink_marker()
            print(msg("uninstall_removed", str(target_bin)))
        else:
            print(msg("uninstall_skipped", str(target_bin)))
        # Also clean legacy nyxniri symlink if present
        legacy_bin = env.home / ".local/bin" / "nyxniri"
        if legacy_bin.is_symlink() and (is_nyxuri_cli_symlink(legacy_bin)):
            legacy_bin.unlink(missing_ok=True)
        shell_bin = env.home / ".local/bin" / "nyxuri-shell"
        if shell_bin.is_symlink():
            try:
                resolved = str(shell_bin.resolve(strict=False))
            except (OSError, ValueError):
                resolved = ""
            if resolved.endswith("/shell/nyxuri-shell") or resolved.endswith("/shell/bin/nyxuri-shell"):
                shell_bin.unlink(missing_ok=True)
                print(msg("uninstall_removed", str(shell_bin)))

    # 7. state_dir — AFTER module uninstallers (.prev lives here). §8.6
    if "state" in selected:
        _rm_report(env.state_dir)
        for legacy_name in ("NyxNiri", "nyxniri"):
            legacy_state = env.home / ".local" / "state" / legacy_name
            if legacy_state.exists() and legacy_state != env.state_dir:
                _rm_report(legacy_state)

    # 8. cache_dir.
    if "cache" in selected:
        _rm_report(env.cache_dir)
        for legacy_name in ("NyxNiri", "nyxniri"):
            legacy_cache = env.home / ".cache" / legacy_name
            if legacy_cache.exists() and legacy_cache != env.cache_dir:
                _rm_report(legacy_cache)

    if env.run_mode == "system":
        print(msg("uninstall_system_hint"))

    print(msg("uninstall_done"))
    log_msg("INFO", f"Uninstall completed (selected: {sorted(selected)})")
    return True

