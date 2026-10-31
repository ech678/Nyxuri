"""先保全恢复点，再按账本统一停用并执行用户选择的自身清理。"""

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
from nyxuri.state.backup import backup_configs, get_all_backups, rollback_configs


def _rm_report(path: Path) -> bool:
    """Remove a path and print a result line ([✓] removed / [!] skipped)."""
    if path.is_symlink() or path.exists():
        remove_path(path)
        if path.exists() or path.is_symlink():
            print(msg("uninstall_failed", str(path)))
            return False
        print(msg("uninstall_removed", str(path)))
    else:
        print(msg("uninstall_skipped", str(path)))
    return True


def _uninstall_nyxuri(mode: str = "") -> bool:
    """解析卸载范围，强制备份后撤回单元；失败时保留状态供重试。

    非交互模式使用默认勾选范围；all 选择全部可选清理，但仍保留本轮保险。
    restore 兼容别名直接返回历史快照回滚结果。
    """
    from nyxuri.kernel import ledger, transaction

    env = get_env()
    records = ledger.all_units()
    managed = [uid for uid, record in records.items()
               if record.get("state") == "enabled" or ledger.get_deployment(uid).get("pending")]
    items = [uid for uid in managed if ledger.get_deployment(uid).get("shape") != "runtime"]

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
        restored = rollback_configs(str(backups[0]))
        if restored:
            print(msg("restore_origin_done"))
        return restored
    elif mode in ("3", "--purge", "purge", "--all", "all"):
        mode = "all"

    # 账本是唯一归属依据；蓝图存在或旧 marker 本身都不能证明用户文件可删除。
    enabled_hooked = managed

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
    unit_entries = [
        CheckboxEntry(key=f"unit:{uid}", label=msg("uninstall_item_unit", uid), checked=True)
        for uid in enabled_hooked
    ]
    if unit_entries:
        entries.append(CheckboxEntry(key="__sep_mod__", label=msg("uninstall_group_units"), is_separator=True))
        entries.extend(unit_entries)

    all_keys = [e.key for e in entries if not e.is_separator]
    default_keys = [e.key for e in entries if not e.is_separator and e.checked]

    # --- Resolve the selected key set + whether configs are archived ---
    if mode == "all":
        selected = set(all_keys)
        if sys.stdin.isatty():
            print(msg("purge_warning"))
            if not prompt_confirm("purge_prompt", "n", destructive=True):
                print(msg("purge_cancelled"))
                return False
            print(msg("purge_start"))
    elif not sys.stdin.isatty():
        # Non-interactive (pipe) → the same standard defaults as the checklist.
        selected = set(default_keys)
    else:
        # Interactive checkbox.
        chk = CheckboxList("uninstall_title", entries, hint_key="uninstall_hint")
        chosen = chk.run()
        if chosen is None:
            print(msg("log_uninstall_cancelled"))
            return False
        selected = set(chosen)

    # 只对执行前已有的旧归档应用清理选项，本轮保险使用独立的状态目录。
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

    # 1. 所有撤回动作之前先保存完整快照。失败时不进入任何删除步骤。
    selected_units = {uid for uid in managed if f"unit:{uid}" in selected}
    if "configs" in selected:
        selected_units.update(items)
    if "wallpapers" in selected and "wallpapers" in managed:
        selected_units.add("wallpapers")
    if "state" in selected or "nyx_dir" in selected:
        # 删除归属域之前必须统一停用，不能留下仍 enabled 的假状态。
        selected_units.update(managed)
    safety = backup_configs(note="pre-uninstall safety snapshot", interactive=False)
    if safety is None:
        print(msg("uninstall_failed", "safety snapshot"))
        return False
    # 自身目录清理也不得删除本轮保险。恢复目录保留在状态域，供手工或 rollback 使用。
    recovery = env.state_dir / "uninstall-backups" / safety.name
    recovery.parent.mkdir(parents=True, exist_ok=True)
    try:
        copy_path(safety, recovery)
    except OSError as exc:
        log_msg("ERROR", f"Uninstall safety backup failed: {exc}")
        return False
    print(msg("uninstall_archived", str(recovery)))
    for uid in sorted(selected_units):
        try:
            # 上一个 cascade 可能已停用依赖者，重复 off 按幂等语义处理。
            steps = transaction.unit_off(uid, cascade=True)
            if not all(step.ok for step in steps):
                print(msg("uninstall_failed", uid))
                return False
            print(msg("uninstall_module_done", uid))
        except Exception as exc:
            log_msg("WARN", f"unit off failed for {uid}: {exc}")
            print(msg("uninstall_failed", uid))
            return False

    # 3. nyx_dir (~/.config/nyxuri/: snapshots, presets, active state, hooks) + legacy snapshots.
    if "nyx_dir" in selected:
        for backup in get_all_backups():
            if backup != recovery:
                if not _rm_report(backup):
                    return False
        if not _rm_report(env.nyx_dir):
            return False
        # Clean historical namespaces as well (zero residue)
        for legacy_name in ("NyxNiri", "nyxniri"):
            legacy_config = env.config_dir / legacy_name
            if legacy_config.exists() and legacy_config != env.nyx_dir:
                if not _rm_report(legacy_config):
                    return False

    # 4. Archives (~/.config/Nyxuri_archive_* / NyxNiri_archive_*)
    if "archives" in selected:
        for p in existing_archives:
            if not _rm_report(p):
                return False

    # 5. 壁纸由账本单元的 off 统一撤回；旧 marker 不再授予删除权限。

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
        for child in env.state_dir.iterdir():
            if child.name != "uninstall-backups":
                if not _rm_report(child):
                    return False
        for legacy_name in ("NyxNiri", "nyxniri"):
            legacy_state = env.home / ".local" / "state" / legacy_name
            if legacy_state.exists() and legacy_state != env.state_dir:
                if not _rm_report(legacy_state):
                    return False

    # 8. cache_dir.
    if "cache" in selected:
        if not _rm_report(env.cache_dir):
            return False
        for legacy_name in ("NyxNiri", "nyxniri"):
            legacy_cache = env.home / ".cache" / legacy_name
            if legacy_cache.exists() and legacy_cache != env.cache_dir:
                if not _rm_report(legacy_cache):
                    return False

    if env.run_mode == "system":
        from nyxuri.pkg.platform import current_platform
        print(msg("uninstall_system_hint" if current_platform() == "arch" else "uninstall_system_package_generic"))

    print(msg("uninstall_done"))
    log_msg("INFO", f"Uninstall completed (selected: {sorted(selected)})")
    return True



def uninstall_nyxuri(mode: str = "") -> bool:
    """将清理阶段的异常转为失败结果，保留保险路径与已完成阶段供重试。"""
    try:
        return _uninstall_nyxuri(mode)
    except (OSError, RuntimeError, ValueError) as exc:
        log_msg("ERROR", f"Uninstall incomplete: {exc}")
        print(msg("uninstall_failed", str(exc)), file=sys.stderr)
        return False
