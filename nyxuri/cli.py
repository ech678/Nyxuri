"""Command routing and process entry point."""

import os
import subprocess
import sys
from typing import List

from nyxuri.constants import (
    CLI_CMD,
    PENDING_UPGRADE_ENV,
    PENDING_UPGRADE_MENU_ENV,
    PROJECT_NAME,
)
from nyxuri.core import (
    acquire_lock,
    check_path_occlusion,
    ensure_nyxuri_symlink,
    get_env,
    init_logger,
    log_msg,
)

ensure_nyxniri_symlink = ensure_nyxuri_symlink
from nyxuri.deploy import (
    apply_preset,
    delete_preset,
    deploy_wallpapers,
    edit_preset,
    list_presets,
    save_preset,
    test_deploy,
)
from nyxuri.deps import run_dep_menu_loop, run_optional_apps_menu_loop
from nyxuri.doctor import generate_bug_report, run_doctor
from nyxuri.state import (
    backup_configs,
    delete_backup,
    list_backups,
    rollback_configs,
    uninstall_nyxuri,
)
from nyxuri.i18n import msg
from nyxuri.network import safe_git_checkout_ref, safe_git_pull
from nyxuri.tui import press_any_key, select_language
from nyxuri.menus import deps_menu_loop, main_menu_loop
from nyxuri.workflows import (
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


def _cmd_install(sub_args: List[str]) -> int:
    mode = sub_args[0] if sub_args else "full"
    if len(sub_args) > 1 or mode not in ("full", "config"):
        exit_usage(f"{CLI_CMD} install [full|config]")
    return 0 if install_configs_workflow(mode) else 1


def _cmd_snapshot(sub_args: List[str]) -> int:
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


def _cmd_list(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} list")
    list_backups()
    return 0


def _cmd_uninstall(sub_args: List[str]) -> int:
    target = sub_args[0] if sub_args else ""
    valid = ("", "standard", "restore", "purge", "--all", "all",
             "--safe", "safe", "1", "--restore", "2", "--purge", "3")
    if len(sub_args) > 1 or target not in valid:
        exit_usage(f"{CLI_CMD} uninstall [--all|standard|restore|purge]")
    return 0 if uninstall_nyxuri(target) else 1


def _cmd_purge(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} purge")
    return 0 if uninstall_nyxuri("purge") else 1


def _cmd_doctor(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} doctor")
    run_doctor()
    return 0


def _cmd_deps(sub_args: List[str]) -> int:
    sub = sub_args[0].lower() if sub_args else ""
    if len(sub_args) > 1 or sub not in ("", "core", "apps", "opt", "optional"):
        exit_usage(f"{CLI_CMD} deps [core|apps]")
    if sub == "core":
        run_dep_menu_loop()
    elif sub in ("apps", "opt", "optional"):
        run_optional_apps_menu_loop()
    else:
        deps_menu_loop()
    return 0


def _cmd_apps(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} apps")
    run_optional_apps_menu_loop()
    return 0


def _cmd_wallpapers(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} wallpapers")
    wallpaper_result = deploy_wallpapers(do_download=True)
    return 0 if wallpaper_result.downloaded else 1


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
        from nyxuri.state.ledger import read_ledger
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
        if apply_part(app, slot, part_name):
            print(f"[✓] 已切换 {app} 零件 [{slot}]: {part_name}")
            return 0
        else:
            print(f"[✗] 切换 {app} 零件 [{slot}]: {part_name} 失败")
            return 1
    if action in ("apply", "save", "edit", "delete"):
        if not name or len(sub_args) > 3:
            exit_usage(f"{CLI_CMD} preset {app} {action} <name>")
        fn = {"apply": apply_preset, "save": save_preset, "edit": edit_preset, "delete": delete_preset}[action]
        return 0 if fn(app, name) else 1
    exit_usage(usage)


def _module_handler(module_name: str, triad_name: str):
    """Factory: build a handler for install|status|uninstall triad (greeter/fcitx).

    """
    def handler(sub_args: List[str]) -> int:
        import importlib
        root_pkg = (__package__ or "nyxuri").split(".")[0]
        mod = importlib.import_module(f"{root_pkg}.modules.{module_name}")
        install_fn = getattr(mod, f"{module_name}_install")
        uninstall_fn = getattr(mod, f"{module_name}_uninstall")
        status_fn = getattr(mod, f"{module_name}_status")
        deploy_fn = getattr(mod, f"{module_name}_deploy_assets", None)
        activate_fn = getattr(mod, f"{module_name}_activate", None)

        valid_subs = ["", "install", "setup", "status", "uninstall", "remove"]
        if deploy_fn is not None:
            valid_subs.append("deploy")
        if activate_fn is not None:
            valid_subs.append("activate")

        sub = sub_args[0].lower() if sub_args else ""
        deploy_only = "--deploy-only" in sub_args
        if len(sub_args) > 2 or (len(sub_args) == 2 and not deploy_only) or sub not in valid_subs:
            usage_cmds = "|".join(s for s in ("install", "deploy", "activate", "status", "uninstall") if s in valid_subs or s in ("install", "status", "uninstall"))
            exit_usage(f"{CLI_CMD} {triad_name} [{usage_cmds}]")

        if sub == "deploy":
            return 0 if (deploy_fn() if deploy_fn else install_fn()) else 1
        elif sub == "activate":
            return 0 if (activate_fn() if activate_fn else install_fn()) else 1
        elif sub in ("install", "setup"):
            if deploy_only and deploy_fn is not None:
                return 0 if deploy_fn() else 1
            return 0 if install_fn() else 1
        elif sub in ("uninstall", "remove"):
            return 0 if uninstall_fn() else 1
        else:
            status_fn()
            return 0
    return handler


def _cmd_theme(sub_args: List[str]) -> int:
    sub = sub_args[0] if sub_args else "toggle"
    if len(sub_args) > 1 or sub not in ("toggle", "dark", "light", "sync", "status"):
        exit_usage(f"{CLI_CMD} theme [toggle|dark|light|sync|status]")
    from nyxuri.theme import status, sync
    if sub == "status":
        return status()
    return sync(sub)


def _cmd_shell(sub_args: List[str]) -> int:
    sub = sub_args[0] if sub_args else "status"
    usage = f"{CLI_CMD} shell [get|set <noctalia|custom> [bin_path]|status]"
    from nyxuri.state.ledger import active_shell, custom_shell_bin, set_shell
    if sub == "get":
        if len(sub_args) > 1:
            exit_usage(usage)
        print(active_shell())
        return 0
    elif sub == "status":
        if len(sub_args) > 1:
            exit_usage(usage)
        current = active_shell()
        cbin = custom_shell_bin()
        print(f"Active Shell: {current}")
        if current == "custom":
            print(f"Custom Shell Binary: {cbin or '<unset>'}")
            if cbin and os.path.isfile(cbin) and os.access(cbin, os.X_OK):
                print("Custom Shell Status: Ready")
            else:
                print("Custom Shell Status: Not executable (will fallback to Noctalia)")
        return 0
    elif sub == "set":
        if len(sub_args) < 2 or len(sub_args) > 3:
            exit_usage(usage)
        target = sub_args[1].lower()
        if target not in ("noctalia", "custom"):
            exit_usage(usage)
        bin_path = sub_args[2] if len(sub_args) > 2 else None
        set_shell(target, bin_path)
        print(f"Shell set to: {target}" + (f" ({bin_path})" if bin_path else ""))
        if target == "custom":
            cbin = custom_shell_bin()
            if not cbin or not os.path.isfile(cbin) or not os.access(cbin, os.X_OK):
                print(f"Notice: Custom shell binary is not executable ({cbin or 'unset'}). Specify with: {CLI_CMD} shell set custom <path>")
        return 0
    else:
        exit_usage(usage)


def _cmd_update(sub_args: List[str]) -> int:
    usage = f"{CLI_CMD} update [--force|--no-deploy] [--to <tag|commit>]"
    flag = ""
    to_ref = ""
    it = iter(sub_args)
    for cur in it:
        if cur == "--to":
            to_ref = next(it, "")
            if not to_ref:
                exit_usage(usage)
        elif cur in ("--force", "--deploy", "--no-deploy"):
            if flag:
                exit_usage(usage)
            flag = cur
        else:
            exit_usage(usage)
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
            from nyxuri.state.ledger import update_ledger
            update_ledger(last_update_head=head.stdout.strip())
        from nyxuri.migrations import run as run_migrations
        if not run_migrations():
            print(msg("migration_failed"), file=sys.stderr)
            return 1
        # Hand the deploy over to a fresh process so it runs on the updated
        # engine code instead of the modules loaded before the pull.
        try:
            os.execve(sys.executable, [sys.executable, "-m", CLI_CMD],
                      {**os.environ, PENDING_UPGRADE_ENV: flag})
        except Exception as e:
            log_msg("ERROR", f"Re-exec failed: {e}")
            print(msg("update_restart_needed"), file=sys.stderr)
            return 1
    if update_result is False:
        print(msg("updating_failed"), file=sys.stderr)
        return 1
    return 0


def _cmd_clean(sub_args: List[str]) -> int:
    from nyxuri.clean import main as clean
    return clean(sub_args)


def _cmd_pkg(sub_args: List[str]) -> int:
    from nyxuri.pkg.cli import main as packages
    return packages(sub_args)


def _cmd_help(sub_args: List[str]) -> int:
    if sub_args:
        exit_usage(f"{CLI_CMD} help")
    print_help()
    return 0


COMMANDS = {
    "pkg":       (_cmd_pkg,       f"{CLI_CMD} pkg <install|upgrade|remove|search|info|installed>"),
    "clean":     (_cmd_clean,     f"{CLI_CMD} clean [-n] [--only <tasks>]"),
    "install":   (_cmd_install,   f"{CLI_CMD} install [full|config]"),
    "deploy":    (_cmd_install,   f"{CLI_CMD} install [full|config]"),
    "snapshot":  (_cmd_snapshot,  f"{CLI_CMD} snapshot [note]"),
    "backup":    (_cmd_snapshot,  f"{CLI_CMD} snapshot [note]"),
    "rollback":  (_cmd_rollback,  f"{CLI_CMD} rollback [index]"),
    "restore":   (_cmd_rollback,  f"{CLI_CMD} rollback [index]"),
    "list":      (_cmd_list,      f"{CLI_CMD} list"),
    "uninstall": (_cmd_uninstall, f"{CLI_CMD} uninstall [--all|standard|restore|purge]"),
    "remove":    (_cmd_uninstall, f"{CLI_CMD} uninstall [--all|standard|restore|purge]"),
    "purge":     (_cmd_purge,     f"{CLI_CMD} purge"),
    "doctor":    (_cmd_doctor,    f"{CLI_CMD} doctor"),
    "deps":      (_cmd_deps,      f"{CLI_CMD} deps [core|apps]"),
    "apps":      (_cmd_apps,      f"{CLI_CMD} apps"),
    "recommended": (_cmd_apps,    f"{CLI_CMD} apps"),
    "wallpapers": (_cmd_wallpapers, f"{CLI_CMD} wallpapers"),
    "wp":        (_cmd_wallpapers, f"{CLI_CMD} wallpapers"),
    "bug":       (_cmd_bug,       f"{CLI_CMD} bug"),
    "report":    (_cmd_bug,       f"{CLI_CMD} bug"),
    "test":      (_cmd_test,      f"{CLI_CMD} test"),
    "preset":    (_cmd_preset,    f"{CLI_CMD} preset <app> [list|apply <name>|save <name>|edit <name>|delete <name>|parts|part <slot> <name>]"),
    "greeter":   (_module_handler("greeter", "greeter"),
                  f"{CLI_CMD} greeter [install|status|uninstall]"),
    "fcitx":     (_module_handler("fcitx", "fcitx"),
                  f"{CLI_CMD} fcitx [install|deploy|activate|status|uninstall]"),
    "gtk":       (_module_handler("gtktheme", "gtk"),
                  f"{CLI_CMD} gtk [install|status|uninstall]"),
    "fisher":    (_module_handler("fisher", "fisher"),
                  f"{CLI_CMD} fisher [install|status|uninstall]"),
    "theme":     (_cmd_theme,     f"{CLI_CMD} theme [toggle|dark|light|sync|status]"),
    "shell":     (_cmd_shell,     f"{CLI_CMD} shell [get|set <noctalia|custom> [path]|status]"),
    "update":    (_cmd_update,    f"{CLI_CMD} update [--force|--no-deploy] [--to <tag|commit>]"),
    "help":      (_cmd_help,      f"{CLI_CMD} help"),
    "-h":        (_cmd_help,      f"{CLI_CMD} help"),
    "--help":    (_cmd_help,      f"{CLI_CMD} help"),
}


def main() -> None:
    """Main CLI entrypoint."""
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
            handler, _ = entry
            sys.exit(handler(sub_args))

        print(msg("err_unknown_command", args[0]), file=sys.stderr)
        print_help(file=sys.stderr)
        sys.exit(2)

    if pending_flag is not None:
        deploy_ok = offer_overwrite_upgrade(pending_flag)
        check_new_deps_post_update()
        print(msg("updating_done"))
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
