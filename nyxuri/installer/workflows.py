"""Install and update orchestration with pre-flight checks."""

import shutil
import subprocess
import sys
from typing import Dict, List, Optional

from nyxuri.core import SUPPORTED_WMS, detect_preferred_wm
from nyxuri.core import get_env, log_msg
from nyxuri.deploy import (
    config_item_dest,
    config_item_src,
    render_completion_screen,
    run_user_hooks,
)
from nyxuri.pkg.deps import (
    core_requirements, get_missing_deps, install_selected_deps, unit_package_installer,
    supply_installed,
)
from nyxuri.pkg.platform import backend_available, current_platform
from nyxuri.pkg.requirements import resolve_requirements
from nyxuri.pkg.detection import DependencyProbe
from nyxuri.kernel import registry, transaction
from nyxuri.core import msg
from nyxuri.tui import MenuItem, Menu, prompt_confirm
from nyxuri.installer.menus import run_master_component_menu
from nyxuri.installer.candidates import discover_install_config_items

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


def _enabled_update_items() -> List[str]:
    """从账本选择仍有蓝图的已启用单元；不借更新认领外来配置。"""
    from nyxuri.kernel import ledger
    known = set(registry.unit_ids())
    return [uid for uid, rec in ledger.all_units().items()
            if rec.get("state") == "enabled" and uid in known]


def _ordered_units(items: List[str]) -> List[str]:
    """按依赖拓扑排列所选单元；只返回调用方允许处理的集合。"""
    selected = set(items)
    result = []
    for uid in items:
        for dep in transaction.plan_on(uid):
            if dep in selected and dep not in result:
                result.append(dep)
    return result


def _deploy_units(items: List[str], *, update: bool, mode: str = "full",
                  force: bool = False, backup: bool = False,
                  conflict_decision: Optional[bool] = None) -> bool:
    """先披露全部冲突并建立快照，再逐个执行统一事务并汇总真实结果。"""
    from nyxuri.tui import choose_conflict_policy, format_steps
    from nyxuri.state import backup_configs

    items = _ordered_units(items)
    decision = (choose_conflict_policy(items, force=force)
                if conflict_decision is None else conflict_decision)
    if decision is None:
        print(msg("cli_aborted"))
        return False
    if backup and items and backup_configs(note="before-update" if update else "before-install",
                                           interactive=False) is None:
        return False
    failed = []
    wallpaper_selected = "wallpapers" in items
    wallpaper_ok = None
    for uid in items:
        if update:
            steps = transaction.unit_refresh(uid, force=decision, install_packages=unit_package_installer)
        else:
            steps = transaction.unit_on(uid, force=decision,
                install_packages=unit_package_installer if mode == "full" else None,
                run_hooks=mode == "full", check_packages=mode == "full")
        for line in format_steps(steps):
            print(line)
        step_failed = any(not step.ok for step in steps)
        if uid == "wallpapers":
            # 只报告本轮壁纸事务结果；外部手动大包或既存视频不能冒充部署成功。
            wallpaper_ok = bool(steps) and not step_failed
            step_failed = not wallpaper_ok
        if step_failed:
            failed.append(uid)
            # 已完成单元保留真实状态，失败后不再触发后续消费者或用户钩子。
            break
    if failed:
        render_completion_screen("update" if update else mode, chosen_items=items,
                                 failed_items=failed, wallpaper_selected=wallpaper_selected,
                                 wallpaper_ok=wallpaper_ok)
        return False
    if mode == "config":
        print(msg("install_config_only_notice"))
        render_completion_screen(mode, chosen_items=items, wallpaper_selected=wallpaper_selected,
                                 wallpaper_ok=wallpaper_ok)
    else:
        _finish_successful_deploy("update" if update else mode, chosen_items=items,
                                 wallpaper_selected=wallpaper_selected, wallpaper_ok=wallpaper_ok)
    return True


def install_configs_workflow(mode: str = "full") -> bool:
    """安装先检查供应范围，再通过单元事务部署、登记和执行钩子。"""
    if mode == "full" and not backend_available():
        print(msg("distro_unsupported"))
        print(msg("distro_unsupported_hint"))
        return False
    if sys.stdin.isatty():
        chosen = run_master_component_menu(is_update=False, mode=mode)
        if not chosen:
            print(msg("install_cancelled"))
            return True
        items = list(chosen["configs"])
        wallpapers, backup = chosen["wallpapers"], chosen["backup"]
    else:
        preferred = detect_preferred_wm()
        items = [uid for uid in discover_install_config_items()
                 if uid not in SUPPORTED_WMS or uid == preferred]
        # 非交互full同样选择随仓库提供的默认壁纸，不触发外部大包下载。
        wallpapers, backup = mode == "full", False
        if mode == "full" and current_platform() == "ubuntu":
            probe = DependencyProbe()
            items = [uid for uid in items if not registry.load_unit(uid).is_optional
                     or supply_installed(registry.load_unit(uid), probe)]
    if wallpapers:
        items.append("wallpapers")
    if not items:
        print(msg("install_cancelled"))
        return True
    # 依赖也纳入冲突披露和供应检查，避免先写消费者再发现上游不可用。
    closure = []
    for uid in items:
        for dep in transaction.plan_on(uid):
            if dep not in closure:
                closure.append(dep)
    for uid in closure:
        requirements = resolve_requirements(registry.load_unit(uid))
        if not requirements.supported:
            print(msg("pkg_unit_unsupported", uid, requirements.reason), file=sys.stderr)
            return False
    from nyxuri.tui import choose_conflict_policy
    decision = choose_conflict_policy(closure)
    if decision is None:
        print(msg("cli_aborted"))
        return False
    _phase_preflight_check(mode, closure, wallpapers, backup)
    if mode == "full":
        missing = get_missing_deps()
        if missing and not install_selected_deps(missing):
            print(msg("pkg_deploy_incomplete", ", ".join(get_missing_deps())), file=sys.stderr)
            return False
        for uid in closure:
            manifest = registry.load_unit(uid)
            missing = transaction.missing_packages(manifest)
            if missing and (not unit_package_installer(uid, missing)
                            or transaction.missing_packages(manifest)):
                return False
    return _deploy_units(closure, update=False, mode=mode, backup=backup, conflict_decision=decision)


def offer_overwrite_upgrade(flag: str = "") -> bool:
    """刷新账本中已启用的单元；--force 仅覆盖已披露冲突并强制备份。"""
    if flag == "--no-deploy":
        return True
    items = _enabled_update_items()
    if flag in ("--force", "--deploy") or not sys.stdin.isatty():
        return _deploy_units(items, update=True, force=flag == "--force", backup=True)
    options = [MenuItem(label=msg("overwrite_opt1")),
               MenuItem(label=msg("overwrite_opt2")),
               MenuItem(label=msg("overwrite_opt3"), style="subtle")]
    choice = Menu("overwrite_title", options, hint_key="submenu_hint").run()
    if choice == 0:
        chosen = run_master_component_menu(is_update=True, mode="full")
        if not chosen:
            return True
        selected = list(chosen["configs"])
        if chosen["wallpapers"]:
            selected.append("wallpapers")
        return _deploy_units([uid for uid in selected if uid in items], update=True,
                             backup=chosen["backup"])
    if choice == 1:
        # 比较视图只读取本次可更新单元；merge/单文件目标由统一路径解析器处理。
        for uid in items:
            if registry.load_unit(uid).runtime:
                continue
            src, dest = config_item_src(uid), config_item_dest(uid)
            if src.exists() and dest.exists():
                subprocess.run(["diff", "-urN", "--color=always", str(dest), str(src)], check=False)
    else:
        print(msg("log_config_deploy_skipped"))
    return True


def check_new_deps_post_update() -> None:
    """兼容旧入口；依赖已由各个刷新事务在写文件前检查。"""
