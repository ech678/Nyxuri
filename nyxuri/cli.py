"""Command routing and process entry point."""

import os
import subprocess
import sys
from typing import List

from nyxuri.core import (
    CLI_CMD,
    Colors,
    PENDING_UPGRADE_ENV,
    PENDING_UPGRADE_MENU_ENV,
    PROJECT_NAME,
)
from nyxuri.core import (
    acquire_lock,
    check_path_occlusion,
    ensure_nyxuri_symlink,
    exec_cli,
    get_env,
    init_logger,
    validate_xdg_layout,
    XDGLayoutError,
)

from nyxuri.deploy import test_deploy
from nyxuri.desktop.presets import (
    apply_preset,
    delete_preset,
    edit_preset,
    list_presets,
    save_preset,
)
from nyxuri.pkg.deps import ensure_aur_helper, run_dep_menu_loop, run_optional_apps_menu_loop
from nyxuri.sysdoctor import generate_bug_report, run_doctor
from nyxuri.kernel import ledger, registry, transaction
from nyxuri.state import (
    backup_configs,
    delete_backup,
    list_backups,
    rollback_configs,
    uninstall_nyxuri,
)
from nyxuri.core import msg
from nyxuri.desktop import bridge
from nyxuri.pkg.net import safe_git_checkout_ref, safe_git_pull
from nyxuri.tui import press_any_key, prompt_confirm, select_language
from nyxuri.installer.menus import deps_menu_loop, main_menu_loop
from nyxuri.installer.workflows import (
    check_new_deps_post_update,
    install_configs_workflow,
    offer_overwrite_upgrade,
)

def print_help(file=None) -> None:
    """Print standard CLI help and commands overview."""
    if file is None:
        file = sys.stdout
    print(msg("cli_help", PROJECT_NAME, CLI_CMD), file=file)


def exit_usage(usage: str) -> None:
    """Report invalid arguments and exit without entering the interactive flow."""
    print(msg("err_invalid_args", usage), file=sys.stderr)
    sys.exit(2)


# --- KM3 core verbs (unit-model.md §5) ----------------------------------------
#
# Four canonical verbs — list / on / off / doctor — are the market-facing
# surface; every switch flip routes through nyxuri.transaction, and this
# layer only adds disclosure, prose and exit codes. The legacy alias table
# was executed at KM3.5: old names are plain unknown commands.


def _package_installer(unit_id: str, missing: List[str]) -> bool:
    """Thin alias: the shared transaction installer lives in deps (CLI and
    TUI must inject the exact same package-manager behavior)."""
    from nyxuri.pkg.deps import unit_package_installer

    return unit_package_installer(unit_id, missing)


def _report_steps(steps) -> int:
    """Turn transaction Steps into bilingual prose; 0 only if every unit won."""
    from nyxuri.tui import format_steps

    lines = format_steps(steps)
    for line in lines:
        print(line)
    return 0 if steps and all(s.ok for s in steps) else (1 if steps else 0)


def _cmd_on(sub_args: List[str]) -> int:
    """nyxuri on <unit> [--preset <name>] — disclose, then transact."""
    usage = f"{CLI_CMD} on <unit> [--preset <name>] [--force]"
    rest = list(sub_args)
    unit = rest.pop(0) if rest and not rest[0].startswith("-") else ""
    if not unit:
        exit_usage(usage)
    preset = None
    force = False
    while rest:
        cur = rest.pop(0)
        if cur == "--preset":
            preset = rest.pop(0) if rest else ""
            if not preset:
                exit_usage(usage)
        elif cur == "--force":
            force = True
        else:
            exit_usage(usage)
    try:
        plan = transaction.plan_on(unit)
    except KeyError:
        print(msg("cli_unknown_unit", unit), file=sys.stderr)
        return 2
    from nyxuri.tui import choose_conflict_policy
    decision = choose_conflict_policy(plan, presets={unit: preset} if preset else {}, force=force)
    if decision is None:
        print(msg("cli_aborted"))
        return 1
    enabled = {u for u, rec in ledger.all_units().items() if rec.get("state") == "enabled"}
    incoming = [u for u in plan if u not in enabled or ledger.get_deployment(u).get("pending")]
    if incoming:
        print(msg("cli_plan_on", " → ".join(incoming)))
    need_install: List[str] = []
    for uid in incoming:
        from nyxuri.pkg.requirements import resolve_requirements
        manifest = registry.load_unit(uid)
        requirements = resolve_requirements(manifest)
        if not requirements.supported:
            print(msg("pkg_unit_unsupported", uid, requirements.reason), file=sys.stderr)
            return 1
        missing = transaction.missing_packages(manifest)
        manual = [name for name in missing if name in requirements.manual]
        if manual:
            print(msg("pkg_manual_missing", ", ".join(manual)), file=sys.stderr)
            if requirements.reason:
                print(msg("pkg_source_hint", uid, requirements.reason), file=sys.stderr)
            return 1
        if missing:
            need_install.extend(missing)
            print(msg("cli_plan_packages", uid, ", ".join(missing)))
    if need_install and not prompt_confirm("cli_confirm_install", "y"):
        print(msg("cli_aborted"), file=sys.stderr)
        return 1
    return _report_steps(
        transaction.unit_on(unit, preset=preset, force=decision, install_packages=_package_installer)
    )


def _cmd_off(sub_args: List[str]) -> int:
    """nyxuri off <unit> [--cascade] — guard, disclose, then transact."""
    usage = f"{CLI_CMD} off <unit> [--cascade]"
    rest = list(sub_args)
    unit = rest.pop(0) if rest and not rest[0].startswith("-") else ""
    if not unit:
        exit_usage(usage)
    cascade = False
    while rest:
        cur = rest.pop(0)
        if cur == "--cascade":
            cascade = True
        else:
            exit_usage(usage)
    try:
        plan = transaction.plan_off(unit)
    except KeyError:
        print(msg("cli_unknown_unit", unit), file=sys.stderr)
        return 2
    dependents = [u for u in plan if u != unit]
    if dependents and not cascade:
        print(msg("cli_off_blocked", unit, ", ".join(dependents)), file=sys.stderr)
        return 1
    if dependents:
        print(msg("cli_plan_off_cascade", ", ".join(dependents)))
    return _report_steps(transaction.unit_off(unit, cascade=cascade))


def _state_cell(state: str, width: int) -> str:
    """Ledger state as a width-fixed colored cell."""
    if state == "enabled":
        text, color = state, Colors.BOLD_GREEN
    elif state == "disabled":
        text, color = state, Colors.DIM
    else:
        text, color = "-", Colors.DIM
    return f"{color}{text.ljust(width)}{Colors.RESET}"


def _cmd_list(sub_args: List[str]) -> int:
    """nyxuri list [unit] — the whole blueprint, or one unit in detail."""
    if len(sub_args) > 1:
        exit_usage(f"{CLI_CMD} list [unit]")
    if sub_args:
        return _show_unit_detail(sub_args[0])
    recs = ledger.all_units()
    ids = sorted(set(registry.unit_ids()) | set(recs))
    if not ids:
        print(msg("cli_list_none"))
        return 0
    print(msg("cli_list_header"))
    for uid in ids:
        rec = recs.get(uid) or {}
        print(f"  {uid:<24}{_state_cell(rec.get('state', ''), 12)}{rec.get('preset', '-')}")
    return 0


def _show_unit_detail(unit: str) -> int:
    """One unit: manifest declarations joined with its ledger record."""
    known = unit in registry.unit_ids()
    if not known and unit not in ledger.all_units():
        print(msg("cli_unknown_unit", unit), file=sys.stderr)
        return 2
    print(f"{Colors.BOLD}{unit}{Colors.RESET}")
    if known:
        m = registry.load_unit(unit)
        if m.label:
            print(f"  {msg('cli_detail_label')}: {m.label}")
        if m.category:
            print(f"  {msg('cli_detail_category')}: {m.category}")
        if m.runtime:
            print(f"  {msg('cli_detail_runtime')}")
        else:
            print(f"  {msg('cli_detail_target')}: {get_env().config_dir / (m.target or unit)}")
        if m.dependencies:
            print(f"  {msg('cli_detail_dependencies')}: {', '.join(m.dependencies)}")
        from nyxuri.pkg.requirements import resolve_requirements
        requirements = resolve_requirements(m)
        pkgs = (*requirements.packages_repo, *requirements.packages_aur,
                *requirements.packages_flatpak)
        if pkgs:
            print(f"  {msg('cli_detail_packages')}: {', '.join(pkgs)}")
        if requirements.manual:
            print(f"  {msg('pkg_manual_label')}: {', '.join(requirements.manual)}")
        if not requirements.supported:
            print(f"  {msg('pkg_unsupported_label')}: {requirements.reason}")
        elif requirements.reason:
            print(msg("pkg_source_hint", unit, requirements.reason))
        if m.requires_root or m.system_paths:
            paths = f" ({', '.join(m.system_paths)})" if m.system_paths else ""
            print(f"  {msg('cli_detail_privilege')}: root{paths}")
    rec = ledger.get_unit(unit)
    if rec:
        print(f"  {msg('cli_detail_state')}: {rec.get('state', '-')}")
        print(f"  {msg('cli_detail_preset')}: {rec.get('preset', '-')}")
        pending = ledger.get_deployment(unit).get("pending")
        if pending:
            print(f"  {msg('cli_detail_pending')}: {pending}")
        if rec.get("vault"):
            print(f"  {msg('cli_detail_vault')}: {rec['vault']}")
        if rec.get("updated"):
            print(f"  {msg('cli_detail_updated')}: {rec['updated']}")
    else:
        print(f"  {msg('cli_detail_never_switched')}")
    try:
        audit = transaction.audit_units(unit)
    except KeyError:
        audit = {}
    if audit.get(unit):
        print(f"  {msg('cli_detail_audit')}: {audit[unit]}")
    return 0


def _print_audit(report: dict) -> None:
    """Three-state reconciliation table (Synced / Drifted / Ghost)."""
    if not report:
        print(msg("cli_audit_clean"))
        return
    print(msg("cli_audit_header"))
    marks = {
        transaction.STATE_SYNCED: (Colors.BOLD_GREEN, "[✓]"),
        transaction.STATE_DRIFTED: (Colors.BOLD_YELLOW, "[!]"),
        transaction.STATE_GHOST: (Colors.BOLD_RED, "[✗]"),
        "Pending": (Colors.BOLD_YELLOW, "[!]"),
        "Orphan": (Colors.BOLD_RED, "[!]"),
    }
    for uid in sorted(report):
        color, mark = marks.get(report[uid], (Colors.DIM, "[•]"))
        print(f"  {color}{mark}{Colors.RESET} {uid:<24}{report[uid]}")
    # The three states are verdicts with an action now (#139): drift is a
    # protected user change, a ghost is an adoptable unit — say so.
    if transaction.STATE_DRIFTED in report.values():
        print(msg("cli_audit_drifted_hint"))
    if transaction.STATE_GHOST in report.values():
        print(msg("cli_audit_ghost_hint"))
    if "Pending" in report.values():
        print(msg("cli_audit_pending_hint"))
    if "Orphan" in report.values():
        print(msg("cli_audit_orphan_hint"))


def _cmd_doctor(sub_args: List[str]) -> int:
    """nyxuri doctor [unit] — audit first, system checkup as the annex."""
    if len(sub_args) > 1:
        exit_usage(f"{CLI_CMD} doctor [unit]")
    unit = sub_args[0] if sub_args else None
    try:
        report = transaction.audit_units(unit)
    except KeyError:
        print(msg("cli_unknown_unit", unit), file=sys.stderr)
        return 2
    _print_audit(report)
    if unit is None:
        run_doctor()
    return 0


def _cmd_install(sub_args: List[str]) -> int:
    mode = sub_args[0] if sub_args else "full"
    if len(sub_args) > 1 or mode not in ("full", "config"):
        exit_usage(f"{CLI_CMD} install [full|config]")
    return 0 if install_configs_workflow(mode) else 1


def _cmd_snapshot(sub_args: List[str]) -> int:
    if sub_args and sub_args[0] == "list":
        if len(sub_args) > 1:
            exit_usage(f"{CLI_CMD} snapshot list")
        list_backups()
        return 0
    if sub_args and sub_args[0] in ("delete", "rm"):
        if len(sub_args) > 2:
            exit_usage(f"{CLI_CMD} snapshot delete [index]")
        target = sub_args[1] if len(sub_args) > 1 else ""
        return 0 if delete_backup(target) else 1
    note = " ".join(sub_args)
    return 0 if backup_configs(note=note, interactive=False) else 1


def _cmd_rollback(sub_args: List[str]) -> int:
    if len(sub_args) > 1:
        exit_usage(f"{CLI_CMD} rollback [index]")
    target = sub_args[0] if sub_args else ""
    return 0 if rollback_configs(target) else 1


def _cmd_uninstall(sub_args: List[str]) -> int:
    target = sub_args[0] if sub_args else ""
    valid = ("", "standard", "restore", "purge", "--all", "all",
             "--safe", "safe", "1", "--restore", "2", "--purge", "3")
    if len(sub_args) > 1 or target not in valid:
        exit_usage(f"{CLI_CMD} uninstall [--all|standard|restore|purge]")
    return 0 if uninstall_nyxuri(target) else 1


def _cmd_deps(sub_args: List[str]) -> int:
    sub = sub_args[0].lower() if sub_args else ""
    if len(sub_args) > 1 or sub not in ("", "core", "apps", "opt", "optional"):
        exit_usage(f"{CLI_CMD} deps [core|apps]")
    if sub == "core":
        ok = run_dep_menu_loop()
    elif sub in ("apps", "opt", "optional"):
        ok = run_optional_apps_menu_loop()
    else:
        ok = deps_menu_loop()
    return 0 if ok else 1


def _cmd_bug(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} bug")
    generate_bug_report()
    return 0


def _cmd_test(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} test")
    return 0 if test_deploy() else 1


def _cmd_preset(sub_args: List[str]) -> int:
    """nyxuri preset <app> [list|apply <name>|save <name>|edit <name>|delete <name>|parts|part <slot> <name>]"""
    usage = f"{CLI_CMD} preset <app> [list|apply <name>|save <name>|edit <name>|delete <name>|parts|part <slot> <name>]"
    force = "--force" in sub_args
    if force:
        sub_args = list(sub_args)
        sub_args.remove("--force")
        if len(sub_args) < 2 or sub_args[1] not in ("apply", "part"):
            exit_usage(usage)
    if len(sub_args) < 2:
        exit_usage(usage)
    app = sub_args[0]
    action = sub_args[1]
    name = sub_args[2] if len(sub_args) > 2 else ""
    if action == "list":
        if len(sub_args) > 2:
            exit_usage(f"{CLI_CMD} preset {app} list")
        list_presets(app)
        return 0
    if action == "parts":
        if len(sub_args) > 2:
            exit_usage(f"{CLI_CMD} preset {app} parts")
        from nyxuri.deploy.preset import list_parts
        from nyxuri.kernel.ledger import read_ledger
        slots = list_parts(app)
        if not slots:
            print(f"[!] {app} 暂无可用零件插槽")
            return 0
        current_parts = read_ledger().get("parts", {})
        print(f"\n── {app} 零件插槽 ──\n")
        for slot, info in slots.items():
            curr = current_parts.get(f"{app}:{slot}", info.get("default", "default"))
            print(f"  [{slot}] 目标: {info.get('target', '')} (当前: {curr})")
            for var in info.get("variants", []):
                mark = "*" if var == curr else " "
                print(f"    {mark} {var}")
        print()
        return 0
    if action == "part":
        if len(sub_args) != 4:
            exit_usage(f"{CLI_CMD} preset {app} part <slot> <name>")
        slot = sub_args[2]
        part_name = sub_args[3]
        from nyxuri.deploy.preset import apply_part
        if apply_part(app, slot, part_name, force=force):
            print(f"[✓] 已切换 {app} 零件 [{slot}]: {part_name}")
            return 0
        else:
            print(f"[✗] 切换 {app} 零件 [{slot}]: {part_name} 失败")
            return 1
    if action in ("apply", "save", "edit", "delete"):
        if not name or len(sub_args) > 3:
            exit_usage(f"{CLI_CMD} preset {app} {action} <name>")
        fn = {"apply": apply_preset, "save": save_preset, "edit": edit_preset, "delete": delete_preset}[action]
        return 0 if (fn(app, name, force=force) if action == "apply" else fn(app, name)) else 1
    exit_usage(usage)


def _cmd_theme(sub_args: List[str]) -> int:
    sub = sub_args[0] if sub_args else "toggle"
    if len(sub_args) > 1 or sub not in ("toggle", "dark", "light", "sync", "status"):
        exit_usage(f"{CLI_CMD} theme [toggle|dark|light|sync|status]")
    from nyxuri.desktop.theme import status, sync
    if sub == "status":
        return status()
    return sync(sub)


_SHELL_EXPERIMENTAL_NOTE = (
    "[EXPERIMENTAL] Nyxuri Shell is under active development: expect bugs and an "
    "unfinished look. Not recommended for daily use yet."
)


def _cmd_shell(sub_args: List[str]) -> int:
    sub = sub_args[0] if sub_args else "status"
    usage = f"{CLI_CMD} shell [get|set <noctalia|nyxuri-shell> [bin_path]|switch [<noctalia|nyxuri-shell> [bin_path]]|status] [EXPERIMENTAL]"
    from nyxuri.kernel.ledger import active_shell, nyxuri_shell_bin
    from nyxuri.desktop.shell_switcher import normalize_shell_name, probe_running_shell, resolve_custom_bin, hot_switch_shell
    if sub == "get":
        if len(sub_args) > 1:
            exit_usage(usage)
        print(active_shell())
        return 0
    elif sub == "status":
        if len(sub_args) > 1:
            exit_usage(usage)
        current = active_shell()
        cbin = nyxuri_shell_bin()
        if current == "nyxuri-shell":
            print(_SHELL_EXPERIMENTAL_NOTE)
        effective_bin = resolve_custom_bin(cbin)
        running_name, running_pid = probe_running_shell()
        print(f"Active Shell: {current}")
        print(f"Running Instance: {running_name}" + (f" (PID: {running_pid})" if running_pid else " (not running)"))
        if current in ("nyxuri-shell", "custom") or cbin:
            print(f"Nyxuri Shell Binary: {cbin or effective_bin or '<unset>'}")
            if effective_bin and os.path.isfile(effective_bin) and os.access(effective_bin, os.X_OK):
                print("Nyxuri Shell Status: Ready")
            else:
                print("Nyxuri Shell Status: Not executable (will fallback to Noctalia)")
        return 0
    elif sub in ("set", "switch"):
        if sub == "switch" and len(sub_args) == 1:
            current = active_shell()
            target = "noctalia" if current in ("nyxuri-shell", "custom") else "nyxuri-shell"
            bin_path = None
        else:
            if len(sub_args) < 2 or len(sub_args) > 3:
                exit_usage(usage)
            raw_target = sub_args[1].lower()
            target = normalize_shell_name(raw_target)
            if target not in ("noctalia", "nyxuri-shell"):
                exit_usage(usage)
            bin_path = sub_args[2] if len(sub_args) > 2 else None

        if target == "nyxuri-shell":
            print(_SHELL_EXPERIMENTAL_NOTE)

        success, message = hot_switch_shell(target, bin_path)
        if success:
            action_verb = "switched" if sub == "switch" else "set"
            print(f"Shell {action_verb} to: {target}" + (f" ({bin_path})" if bin_path else ""))
            print(f"[✓] {message}")
            return 0
        else:
            print(f"[✗] {message}", file=sys.stderr)
            return 1
    else:
        exit_usage(usage)


def _cmd_update(sub_args: List[str]) -> int:
    usage = f"{CLI_CMD} update [--local] [--force|--deploy|--no-deploy] [--to <tag|commit>]"
    flag = ""
    to_ref = ""
    local = False
    it = iter(sub_args)
    for cur in it:
        if cur == "--to":
            to_ref = next(it, "")
            if not to_ref or to_ref.startswith("-"):
                exit_usage(usage)
        elif cur == "--local":
            local = True
        elif cur in ("--force", "--deploy", "--no-deploy"):
            if flag:
                exit_usage(usage)
            flag = cur
        else:
            exit_usage(usage)
    if local:
        if to_ref or flag == "--no-deploy":
            exit_usage(usage)
        return 0 if offer_overwrite_upgrade(flag) else 1
    env = get_env()
    check_path_occlusion()
    if to_ref:
        update_result = safe_git_checkout_ref(env.repo_dir, to_ref)
    else:
        update_result = safe_git_pull(env.repo_dir)
    if update_result is True:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=env.repo_dir,
            capture_output=True, text=True, check=False,
        )
        if head.returncode == 0 and head.stdout.strip():
            from nyxuri.kernel.ledger import update_ledger
            update_ledger(last_update_head=head.stdout.strip())
        # KM5: the linear migrations module was liquidated — the ledger is the
        # only truth and the nyxniri-era tombstones are years past their sweep.
        # Hand the deploy over to a fresh process so it runs on the updated
        # engine code instead of the modules loaded before the pull.
        if not exec_cli(env, **{PENDING_UPGRADE_ENV: flag}):
            return 1
    if update_result is False:
        print(msg("updating_failed"), file=sys.stderr)
        return 1
    if update_result is None:
        print(msg("update_skipped_local_hint"), file=sys.stderr)
        return 1
    return 0


def _cmd_clean(sub_args: List[str]) -> int:
    from nyxuri.desktop.clean import main as clean
    return clean(sub_args)


def _cmd_pkg(sub_args: List[str]) -> int:
    from nyxuri.pkg.fzf import main as packages
    return packages(sub_args)


def _cmd_help(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} help")
    print_help()
    return 0


COMMANDS = {
    "on":        (_cmd_on,        f"{CLI_CMD} on <unit> [--preset <name>] [--force]"),
    "enable":    (_cmd_on,        f"{CLI_CMD} on <unit> [--preset <name>] [--force]"),
    "off":       (_cmd_off,       f"{CLI_CMD} off <unit> [--cascade]"),
    "disable":   (_cmd_off,       f"{CLI_CMD} off <unit> [--cascade]"),
    "list":      (_cmd_list,      f"{CLI_CMD} list [unit]"),
    "pkg":       (_cmd_pkg,       f"{CLI_CMD} pkg <install|upgrade|remove|search|info|installed>"),
    "clean":     (_cmd_clean,     f"{CLI_CMD} clean [-n] [--only <tasks>]"),
    "install":   (_cmd_install,   f"{CLI_CMD} install [full|config]"),
    "snapshot":  (_cmd_snapshot,  f"{CLI_CMD} snapshot [note|list|delete [index]]"),
    "rollback":  (_cmd_rollback,  f"{CLI_CMD} rollback [index]"),
    "uninstall": (_cmd_uninstall, f"{CLI_CMD} uninstall [--all|standard|restore|purge]"),
    "doctor":    (_cmd_doctor,    f"{CLI_CMD} doctor [unit]"),
    "deps":      (_cmd_deps,      f"{CLI_CMD} deps [core|apps]"),
    "bug":       (_cmd_bug,       f"{CLI_CMD} bug"),
    "test":      (_cmd_test,      f"{CLI_CMD} test"),
    "preset":    (_cmd_preset,    f"{CLI_CMD} preset <app> [list|apply <name>|save <name>|edit <name>|delete <name>|parts|part <slot> <name>]"),
    "theme":     (_cmd_theme,     f"{CLI_CMD} theme [toggle|dark|light|sync|status]"),
    "shell":     (_cmd_shell,     f"{CLI_CMD} shell [get|set <noctalia|nyxuri-shell> [bin_path]|switch [<noctalia|nyxuri-shell> [bin_path]]|status] [EXPERIMENTAL]"),
    "update":    (_cmd_update,    f"{CLI_CMD} update [--local] [--force|--deploy|--no-deploy] [--to <tag|commit>]"),
    "help":      (_cmd_help,      f"{CLI_CMD} help"),
}


def main() -> None:
    """Main CLI entrypoint."""
    # 即使 Environment 已缓存，也检查本次进程环境；拒绝必须早于锁、日志与迁移。
    try:
        validate_xdg_layout()
    except XDGLayoutError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    if os.geteuid() == 0 or os.getuid() == 0:
        print(msg("err_root_denied"), file=sys.stderr)
        sys.exit(1)

    # These tools own no deployment state; fzf probes and clean previews stay read-only.
    args = sys.argv[1:]
    if args and args[0] in ("pkg", "clean"):
        sys.exit(COMMANDS[args[0]][0](args[1:]))

    acquire_lock()
    init_logger()
    get_env()
    # The event delivery is the outer layer's job (unit-model.md §6): wire
    # the Shell bridge once so every verb (CLI, TUI, installer menus) that
    # lands a unit transaction notifies the running shell over its own IPC.
    bridge.wire()
    ensure_nyxuri_symlink()

    # Post-update handoff: a previous run pulled new code and re-execed into
    # us, so the deploy offer runs on the updated engine instead of the stale
    # modules the old process had loaded before the pull.
    pending_flag = os.environ.pop(PENDING_UPGRADE_ENV, None)
    pending_from_menu = os.environ.pop(PENDING_UPGRADE_MENU_ENV, None)

    args = sys.argv[1:]
    if args:
        cmd = args[0].lower()
        sub_args = args[1:]

        entry = COMMANDS.get(cmd)
        if entry:
            sys.exit(entry[0](sub_args))

        print(msg("err_unknown_command", args[0]), file=sys.stderr)
        print_help(file=sys.stderr)
        sys.exit(2)

    if pending_flag is not None:
        deploy_ok = offer_overwrite_upgrade(pending_flag)
        print(msg("updating_done" if deploy_ok else "updating_failed"))
        if not sys.stdin.isatty():
            sys.exit(0 if deploy_ok else 1)
        press_any_key()
        if not pending_from_menu:
            sys.exit(0 if deploy_ok else 1)

    # Interactive flow
    if not sys.stdin.isatty():
        sys.exit(0 if install_configs_workflow("full") else 1)
    select_language()
    main_menu_loop()


if __name__ == "__main__":
    main()
