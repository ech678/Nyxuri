"""Install and update orchestration with pre-flight checks."""

import shutil
import subprocess
import sys
from typing import Dict, List

from nyxuri.core import SUPPORTED_WMS, detect_preferred_wm
from nyxuri.core import get_env, log_msg
from nyxuri.deploy import (
    config_item_dest,
    config_item_src,
    deploy_selected_configs,
    discover_config_items,
    render_completion_screen,
    run_user_hooks,
)
from nyxuri.deploy.deploy import (
    enable_theme_unit as _enable_theme,
    enable_wallpapers_unit as _enable_wallpapers,
    wallpapers_pack_present,
)
from nyxuri.pkg.deps import get_missing_deps, install_selected_deps
from nyxuri.kernel import transaction
from nyxuri.core import msg
from nyxuri.tui import MenuItem, Menu, prompt_confirm
from nyxuri.installer.menus import run_master_component_menu
from nyxuri.deploy.atomic import CarryPolicy

def _phase_preflight_check(
    mode: str,
    chosen_configs: List[str],
    do_wallpapers: bool,
    do_backup: bool,
) -> None:
    """Pre-flight checklist & upfront sudo access validation."""
    needs_sudo = mode == "full"

    print(msg("preflight_express_summary"))
    print(msg("preflight_comp_config", len(chosen_configs)))
    if do_wallpapers:
        print(msg("preflight_comp_assets"))
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


def _update_carry_policy(items: List[str]) -> "CarryPolicy":
    """Update-grade ownership carry (#139): ledger baselines, 宁可错保.

    ``unknown=True``: a unit without an enabled record (Ghost) has every
    dest entry carried — the update must never guess wrong about files it
    cannot attribute. Adoption paths (install/``on``) use ``unknown=False``.
    """
    return CarryPolicy(baselines=transaction.carry_baselines(items), unknown=True)


def _resnapshot_after_deploy(items: List[str], policy: Optional[CarryPolicy]) -> None:
    """Re-baseline enabled units after an out-of-band deploy + hook replay."""
    if policy is None:
        transaction.resnapshot_units(items, carried={})
    else:
        transaction.resnapshot_units(items, carried=policy.carried)


def _ghost_notices(items: List[str], policy: Optional[CarryPolicy]) -> List[str]:
    """Per-unit notices for deployed-but-unregistered (Ghost) units (#139)."""
    baselines = policy.baselines if policy is not None else transaction.carry_baselines(items)
    notices = []
    for item in items:
        if baselines.get(item) is not None:
            continue
        try:
            dest = config_item_dest(item)
        except Exception:
            continue
        if dest.exists() or dest.is_symlink():
            notices.append(msg("update_ghost_hint", item))
    return notices


def _carried_groups(items: List[str], policy: Optional[CarryPolicy]) -> Dict[str, List[str]]:
    """Carried display paths grouped by kind, for the completion screen.

    Report credibility (#139 field report): "your changes", "your files" and
    "unknown origin" are different verdicts — they must not share one bucket.
    """
    if policy is None:
        return {}
    config_dir = get_env().config_dir
    groups: Dict[str, List[str]] = {}
    for item in items:
        for rel, kind in policy.carried.get(item, {}).items():
            dest = config_item_dest(item)
            disp = rel if dest == config_dir / rel else f"{item}/{rel}"
            groups.setdefault(kind, []).append(f"~/.config/{disp}")
    return groups


def install_configs_workflow(mode: str = "full") -> bool:
    """Full execution pipeline for dotfiles, dependencies, wallpapers, and hooks."""
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
        do_backup = chosen_dict["backup"]

        if not chosen_configs and not do_wallpapers:
            print(msg("install_cancelled"))
            return True
    else:
        all_items = discover_config_items()
        preferred_wm = detect_preferred_wm()
        chosen_configs = [
            item for item in all_items
            if item not in SUPPORTED_WMS or item == preferred_wm
        ]
        do_wallpapers = not wallpapers_pack_present()
        do_backup = False

    # Safety: ensure at most one WM is selected
    selected_wms = [c for c in chosen_configs if c in SUPPORTED_WMS]
    if len(selected_wms) > 1:
        preferred = detect_preferred_wm()
        chosen_wm = preferred if preferred in selected_wms else selected_wms[0]
        chosen_configs = [c for c in chosen_configs if c not in SUPPORTED_WMS or c == chosen_wm]

    _phase_preflight_check(mode, chosen_configs, do_wallpapers, do_backup)

    # Step counting
    steps = 3 if do_wallpapers else 2  # configs [+ wallpapers] + unit hooks
    if mode == "full":
        steps += 1  # deps
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
        # Install is adoption (#139): payload names are claimed, user-placed
        # extras are carried. An already-enabled unit's ledger record acts as
        # the drift baseline so a re-install never eats edits.
        carry_policy = CarryPolicy(
            baselines=transaction.carry_baselines(chosen_configs), unknown=False
        )
        failed_items = deploy_selected_configs(
            do_backup=do_backup,
            items_to_deploy=chosen_configs,
            preserved_log=preserved_log,
            carry_policy=carry_policy,
        )
        if failed_items:
            render_completion_screen(
                mode=mode,
                chosen_items=chosen_configs,
                preserved_lines=preserved_log,
                failed_items=failed_items,
            )
            return False

    # 3. Wallpapers — the unit path: `on wallpapers` syncs the blueprint
    # fallback into the shared living area (no-clobber). The external pack
    # is user-domain content (plugins/wallpapers/hooks/install-pack), never
    # an install phase. The theme pool (shared template living area) rides
    # the same unit path: `on theme` no-clobber merges the blueprint
    # templates; user-edited templates are never clobbered.
    wallpaper_ok = None
    if do_wallpapers:
        cur_step += 1
        print(msg("install_step_wallpapers", f"{cur_step}/{steps}"))
        wallpaper_ok = _enable_wallpapers()
    _enable_theme()

    # 4. Unit hook replay: already-enabled units re-run their declared
    # on-side hooks (skins, renders). Activation of NEW units belongs to
    # `nyxuri on <unit>` — the installer never invents switch state.
    cur_step += 1
    print(msg("install_step_unit_hooks", f"{cur_step}/{steps}"))
    for step in transaction.replay_enabled_hooks():
        if not step.ok:
            log_msg("WARN", f"unit hook replay failed for {step.unit}: {step.detail}")

    # Hook products and template renders changed the laid truth under any
    # already-enabled unit: re-baseline so the next audit stays honest (#139).
    if chosen_configs:
        _resnapshot_after_deploy(chosen_configs, carry_policy)

    # Completion
    _finish_successful_deploy(
        mode=mode,
        chosen_items=chosen_configs,
        preserved_lines=preserved_log,
        wallpaper_ok=wallpaper_ok,
    )
    return True


def offer_overwrite_upgrade(flag: str = "") -> bool:
    """Handle update flow: ask to deploy changes, view diff, or code update only.

    Every deploy path rides the ownership carry (#139): user-modified and
    user-placed files are carried, never clobbered. ``--force`` is the one
    template-wins verb for DRIFT — the template claims its payload names and
    re-baselines the ledger ("I reviewed the drift, adopt the template side")
    — but it is not a purge: user-placed extras are still carried.
    """
    if flag in ("--force", "--deploy"):
        # Force = adopt: no baselines, payload names claimed, extras carried.
        items = discover_config_items()
        force_policy = CarryPolicy(baselines={}, unknown=False, carried={})
        failed_items = deploy_selected_configs(
            do_backup=True, items_to_deploy=items, carry_policy=force_policy
        )
        if failed_items:
            render_completion_screen("update", failed_items=failed_items)
            return False
        wallpaper_ok = _enable_wallpapers()
        _enable_theme()
        transaction.replay_enabled_hooks()
        # Re-baseline every deployed unit so the drift the user just
        # reviewed clears instead of haunting doctor forever.
        _resnapshot_after_deploy(items, force_policy)
        _finish_successful_deploy("update", wallpaper_ok=wallpaper_ok)
        return True
    elif flag == "--no-deploy":
        return True

    if not sys.stdin.isatty():
        # Updates must always create a protected snapshot before replacing
        # configuration; a failed update must have a concrete rollback point.
        items = discover_config_items()
        carry_policy = _update_carry_policy(items)
        preserved: List[str] = []
        failed_items = deploy_selected_configs(
            do_backup=True, preserved_log=preserved, carry_policy=carry_policy
        )
        if failed_items:
            render_completion_screen("update", failed_items=failed_items)
            return False
        wallpaper_ok = _enable_wallpapers()
        _enable_theme()
        transaction.replay_enabled_hooks()
        _resnapshot_after_deploy(items, carry_policy)
        _finish_successful_deploy(
            "update",
            preserved_lines=preserved,
            wallpaper_ok=wallpaper_ok,
            notice_lines=_ghost_notices(items, carry_policy),
            carried_groups=_carried_groups(items, carry_policy),
        )
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
            if not chosen["configs"] and not chosen["wallpapers"]:
                print(msg("log_no_components_selected"))
                return True
            print(msg("upgrading_selected"))
            carry_policy = _update_carry_policy(chosen["configs"])
            preserved: List[str] = []
            if chosen["configs"]:
                failed_items = deploy_selected_configs(
                    do_backup=chosen["backup"],
                    items_to_deploy=chosen["configs"],
                    preserved_log=preserved,
                    carry_policy=carry_policy,
                )
                if failed_items:
                    render_completion_screen("update", chosen_items=chosen["configs"], preserved_lines=preserved, failed_items=failed_items)
                    return False
            wallpaper_ok = None
            if chosen["wallpapers"]:
                wallpaper_ok = _enable_wallpapers()
            transaction.replay_enabled_hooks()
            _resnapshot_after_deploy(chosen["configs"], carry_policy)
            _finish_successful_deploy(
                "update",
                chosen_items=chosen["configs"],
                preserved_lines=preserved,
                wallpaper_ok=wallpaper_ok,
                notice_lines=_ghost_notices(chosen["configs"], carry_policy),
                carried_groups=_carried_groups(chosen["configs"], carry_policy),
            )
            return True
    elif choice == 1:
        print(msg("diff_viewer_title"))
        config_items = discover_config_items()
        diff_cmds = []
        for it in config_items:
            src = config_item_src(it)
            dest = config_item_dest(it)
            if src.exists() and dest.exists():
                diff_cmds.append(["diff", "-urN", "--color=always", str(dest), str(src)])
        if diff_cmds:
            if shutil.which("less"):
                pager = subprocess.Popen(["less", "-R"], stdin=subprocess.PIPE, text=True)
                for cmd in diff_cmds:
                    if pager.poll() is not None:
                        break
                    subprocess.run(cmd, stdout=pager.stdin, stderr=subprocess.STDOUT, check=False)
                if pager.stdin:
                    try:
                        pager.stdin.close()
                    except (BrokenPipeError, OSError):
                        pass
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
