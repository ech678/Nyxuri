"""Install and update orchestration with pre-flight checks."""

import shutil
import subprocess
import sys
from typing import List

from nyxuri.constants import FCITX_THEME, GREETER_PKG
from nyxuri.core import get_env, log_msg
from nyxuri.deploy import (
    deploy_selected_configs,
    deploy_wallpapers,
    discover_config_items,
    render_completion_screen,
    run_user_hooks,
    wallpapers_pack_present,
)
from nyxuri.deps import get_missing_deps, install_selected_deps
from nyxuri.modules.fcitx import fcitx_enabled, fcitx_install
from nyxuri.modules.greeter import greeter_install
from nyxuri.i18n import msg
from nyxuri.tui import MenuItem, Menu, prompt_confirm
from nyxuri.menus import run_master_component_menu

def _phase_preflight_check(
    mode: str,
    chosen_configs: List[str],
    do_fcitx: bool,
    do_greeter: bool,
    do_wallpapers: bool,
    do_backup: bool,
) -> None:
    """Pre-flight checklist & upfront sudo access validation."""
    needs_sudo = mode == "full" or do_greeter

    print(msg("preflight_express_summary"))
    print(msg("preflight_comp_config", len(chosen_configs)))
    if do_wallpapers:
        print(msg("preflight_comp_assets"))
    if do_fcitx:
        print(msg("preflight_comp_module_fcitx", FCITX_THEME))
    if do_greeter:
        print(msg("preflight_comp_module_greeter", GREETER_PKG))
    if mode == "full":
        print(msg("preflight_comp_deps"))
    if do_backup:
        print(msg("preflight_comp_backup"))

    if needs_sudo:
        sys.stdout.write(msg("preflight_sudo_prompt") + "\n")
        sys.stdout.flush()
        try:
            res = subprocess.run(["sudo", "-n", "/bin/sh", "-c", ":"], check=False)
            if res.returncode != 0:
                sudo_command = ["sudo", "-v"] if sys.stdin.isatty() else ["sudo", "-n", "-v"]
                res = subprocess.run(sudo_command, check=False)
        except FileNotFoundError:
            print(msg("err_sudo_missing"), file=sys.stderr)
            sys.exit(1)
        if res.returncode != 0:
            print(msg("err_sudo_aborted"))
            sys.exit(1)
        log_msg("INFO", "Sudo access verified upfront during pre-flight.")


def _finish_successful_deploy(mode: str, **completion_args) -> None:
    """Run user hooks once, then render the matching completion screen."""
    completion_args["hook_diagnostics"] = run_user_hooks()
    render_completion_screen(mode, **completion_args)


def install_configs_workflow(mode: str = "full") -> bool:
    """Full execution pipeline for dotfiles, dependencies, wallpapers, and optional modules."""
    if mode == "full" and not shutil.which("pacman"):
        print(msg("distro_unsupported"))
        print(msg("distro_unsupported_hint"))
        return False
    if sys.stdin.isatty():
        chosen_dict = run_master_component_menu(is_update=False, mode=mode)
        if not chosen_dict:
            print(msg("install_cancelled"))
            return True

        chosen_configs = chosen_dict["configs"]
        do_wallpapers = chosen_dict["wallpapers"]
        do_fcitx = chosen_dict["fcitx"]
        do_greeter = chosen_dict["greeter"]
        do_backup = chosen_dict["backup"]

        if not chosen_configs and not do_wallpapers and not do_fcitx and not do_greeter:
            print(msg("install_cancelled"))
            return True
    else:
        chosen_configs = discover_config_items()
        do_wallpapers = not wallpapers_pack_present()
        do_fcitx = fcitx_enabled()
        do_greeter = False
        do_backup = False

    _phase_preflight_check(mode, chosen_configs, do_fcitx, do_greeter, do_wallpapers, do_backup)

    # Step counting
    steps = 2  # configs + wallpapers
    if mode == "full":
        steps += 1  # deps
    if do_fcitx:
        steps += 1
    if do_greeter:
        steps += 1
    cur_step = 0

    # 1. Deps
    if mode == "full":
        cur_step += 1
        print(msg("install_step_deps", f"{cur_step}/{steps}"))
        missing = get_missing_deps()
        if missing and not install_selected_deps(missing):
            return False

    # 2. Configs
    cur_step += 1
    print(msg("install_step_configs", f"{cur_step}/{steps}"))
    preserved_log: List[str] = []
    if chosen_configs:
        failed_items = deploy_selected_configs(do_backup=do_backup, items_to_deploy=chosen_configs, preserved_log=preserved_log)
        if failed_items:
            render_completion_screen(
                mode=mode,
                chosen_items=chosen_configs,
                preserved_lines=preserved_log,
                failed_items=failed_items,
            )
            return False

    # 3. Wallpapers (always run — at least syncs offline fallback wallpapers)
    wallpaper_result = None
    cur_step += 1
    print(msg("install_step_wallpapers", f"{cur_step}/{steps}"))
    wallpaper_result = deploy_wallpapers(do_download=do_wallpapers)

    # 4. Fcitx5
    if do_fcitx:
        cur_step += 1
        print(msg("install_step_fcitx", f"{cur_step}/{steps}"))
        if not fcitx_install():
            return False

    # 5. Greeter
    if do_greeter:
        cur_step += 1
        print(msg("install_step_greeter", f"{cur_step}/{steps}"))
        if not greeter_install():
            return False

    # Completion
    _finish_successful_deploy(
        mode=mode,
        chosen_items=chosen_configs,
        preserved_lines=preserved_log,
        wallpaper_result=wallpaper_result,
        do_fcitx=do_fcitx,
        do_greeter=do_greeter,
    )
    return True


def offer_overwrite_upgrade(flag: str = "") -> bool:
    """Handle update flow: ask to deploy changes, view diff, or code update only."""
    env = get_env()
    if flag in ("--force", "--deploy"):
        failed_items = deploy_selected_configs(do_backup=True)
        if failed_items:
            render_completion_screen("update", failed_items=failed_items)
            return False
        wallpaper_result = deploy_wallpapers(do_download=True)
        if fcitx_enabled():
            if not fcitx_install():
                return False
        try:
            if not greeter_install():
                return False
        except Exception as e:
            log_msg("WARN", f"Greeter install skipped during --force update: {e}")
            return False
        _finish_successful_deploy("update", wallpaper_result=wallpaper_result)
        return True
    elif flag == "--no-deploy":
        return True

    if not sys.stdin.isatty():
        # Updates must always create a protected snapshot before replacing
        # configuration; a failed update must have a concrete rollback point.
        failed_items = deploy_selected_configs(do_backup=True)
        if failed_items:
            render_completion_screen("update", failed_items=failed_items)
            return False
        wallpaper_result = deploy_wallpapers(do_download=False)
        if fcitx_enabled() and not fcitx_install():
            return False
        _finish_successful_deploy("update", wallpaper_result=wallpaper_result)
        return True

    # Interactive choice menu
    items = [
        MenuItem(label=msg("overwrite_opt1")),
        MenuItem(label=msg("overwrite_opt2")),
        MenuItem(label=msg("overwrite_opt3"), style="subtle"),
    ]
    menu = Menu("overwrite_title", items, hint_key="submenu_hint")
    choice = menu.run()

    if choice == 0:
        chosen = run_master_component_menu(is_update=True, mode="full")
        if chosen:
            if not chosen["configs"] and not chosen["wallpapers"] and not chosen["fcitx"] and not chosen["greeter"]:
                print(msg("log_no_components_selected"))
                return True
            print(msg("upgrading_selected"))
            preserved: List[str] = []
            if chosen["configs"]:
                failed_items = deploy_selected_configs(do_backup=chosen["backup"], items_to_deploy=chosen["configs"], preserved_log=preserved)
                if failed_items:
                    render_completion_screen("update", chosen_items=chosen["configs"], preserved_lines=preserved, failed_items=failed_items)
                    return False
            wallpaper_result = None
            if chosen["wallpapers"]:
                wallpaper_result = deploy_wallpapers(do_download=True)
            if chosen["fcitx"]:
                if not fcitx_install():
                    return False
            if chosen["greeter"]:
                if not greeter_install():
                    return False
            _finish_successful_deploy(
                "update",
                chosen_items=chosen["configs"],
                preserved_lines=preserved,
                wallpaper_result=wallpaper_result,
            )
            return True
    elif choice == 1:
        print(msg("diff_viewer_title"))
        config_items = discover_config_items()
        diff_cmds = []
        for it in config_items:
            src = env.configs_src / it
            dest = env.config_dir / it
            if src.exists() and dest.exists():
                diff_cmds.append(["diff", "-urN", "--color=always", str(dest), str(src)])
        if diff_cmds:
            if shutil.which("less"):
                pager = subprocess.Popen(["less", "-R"], stdin=subprocess.PIPE, text=True)
                for cmd in diff_cmds:
                    subprocess.run(cmd, stdout=pager.stdin, stderr=subprocess.STDOUT, check=False)
                pager.stdin.close()
                pager.wait()
            else:
                for cmd in diff_cmds:
                    subprocess.run(cmd, check=False)
    else:
        print(msg("log_config_deploy_skipped"))
    return True


def check_new_deps_post_update() -> None:
    """Check for newly introduced core dependencies after a repository update."""
    missing = get_missing_deps()
    if not missing:
        return
    print(msg("new_deps_detected", " ".join(missing)))
    if not sys.stdin.isatty():
        log_msg("INFO", f"Auto-installing new deps non-interactively: {' '.join(missing)}")
        install_selected_deps(missing)
        return
    if prompt_confirm("prompt_install_missing_deps", "y"):
        install_selected_deps(missing)
    else:
        print(msg("deps_install_skipped"))
