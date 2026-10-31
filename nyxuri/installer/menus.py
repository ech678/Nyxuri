"""Interactive control panel and component selection."""

import os
import shutil
import sys
from typing import List, Optional

from nyxuri.core import (
    PENDING_UPGRADE_ENV,
    PENDING_UPGRADE_MENU_ENV,
    SUPPORTED_WMS,
    detect_preferred_wm,
)
from nyxuri.core import exec_cli, get_env
from nyxuri.deploy import (
    discover_config_items,
    discover_manifest_apps,
    discover_optional_apps,
)
from nyxuri.desktop.presets import (
    apply_preset,
    collect_presets,
    delete_preset,
    edit_preset,
    save_preset,
)
from nyxuri.installer.candidates import discover_install_config_items
from nyxuri.pkg.deps import is_dep_installed, run_dep_menu_loop, run_optional_apps_menu_loop, supply_installed
from nyxuri.sysdoctor import generate_bug_report, run_doctor
from nyxuri.state import (
    backup_configs,
    delete_backup,
    list_backups,
    rollback_configs,
    uninstall_nyxuri,
)
from nyxuri.core import msg
from nyxuri.pkg.net import safe_git_pull
from nyxuri.tui import (
    CheckboxEntry,
    CheckboxList,
    MenuItem,
    Menu,
    PresetSwitcher,
    drain_stdin,
    clear_screen,
    pad_display,
    press_any_key,
)

def run_master_component_menu(is_update: bool = False, mode: str = "full") -> Optional[dict]:
    """Interactive checklist for choosing configs, wallpapers, and backup behavior."""
    items = discover_install_config_items()
    from nyxuri.kernel import ledger, registry
    enabled = {uid for uid, rec in ledger.all_units().items() if rec.get("state") == "enabled"}
    if is_update:
        items = [uid for uid in registry.unit_ids() if uid in enabled
                 and not registry.load_unit(uid).runtime and uid != "wallpapers"]
    entries: List[CheckboxEntry] = []
    from nyxuri.pkg.requirements import resolve_requirements
    manifests = dict(discover_manifest_apps())

    wm_items = [i for i in items if i in SUPPORTED_WMS]
    app_items = [i for i in items if i not in SUPPORTED_WMS]
    preferred_wm = detect_preferred_wm()

    # 1. Window Managers (Radio - Single Selection)
    if wm_items:
        entries.append(CheckboxEntry(key="sep_wm", label=msg("master_item_wm_section"), is_separator=True))
        desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        for wm in wm_items:
            label = msg("master_item_config", wm)
            is_running = (wm in desktop_env or desktop_env in wm) if desktop_env else False
            is_inst = is_dep_installed(wm)
            if is_running:
                label = f"{label}  {msg('running')}"
            elif is_inst:
                label = f"{label}  {msg('installed')}"
            else:
                label = f"{label}  {msg('missing')}"

            is_checked = is_update or (wm == preferred_wm)
            if mode == "full" and wm in manifests and not resolve_requirements(manifests[wm]).supported:
                label = f"{label}  {msg('pkg_unsupported_label')}"
                is_checked = False
            entries.append(CheckboxEntry(
                key=f"config_{wm}",
                label=label,
                checked=is_checked,
                radio_group="" if is_update else "wm",
            ))

    # 2. Desktop Apps & Components
    if app_items:
        entries.append(CheckboxEntry(key="sep_apps", label=msg("master_item_apps_section"), is_separator=True))
        optional_set = set(discover_optional_apps())
        for item in app_items:
            label = msg("master_item_config", item)
            checked = True
            if item in optional_set:
                m = manifests.get(item)
                if m is not None:
                    is_inst = supply_installed(m)
                    label = f"{label}  {msg('installed') if is_inst else msg('missing')}"
                    if not is_inst and not is_update:
                        checked = False
            if mode == "full" and item in manifests:
                requirements = resolve_requirements(manifests[item])
                if not requirements.supported:
                    label = f"{label}  {msg('pkg_unsupported_label')}"
                    checked = False
                elif requirements.manual:
                    label = f"{label}  {msg('pkg_manual_label')}"
            entries.append(CheckboxEntry(key=f"config_{item}", label=label, checked=checked))

    if (mode == "full" and not is_update) or (is_update and "wallpapers" in enabled):
        # 默认静态壁纸随仓库离线部署；外部视频/大包是独立手动工具，不决定本项状态。
        wp_checked = True
        wp_status = msg("status_wallpapers_installed") if "wallpapers" in enabled else msg("status_wallpapers_missing")
        entries.append(CheckboxEntry(
            key="assets_wallpapers",
            label=msg("master_item_asset", wp_status),
            checked=wp_checked,
        ))

    # 3. Behavior: Backup
    entries.append(CheckboxEntry(key="sep_behavior", label=msg("master_item_behavior"), is_separator=True))
    entries.append(CheckboxEntry(key="behavior_backup", label=msg("master_item_backup"), checked=True))

    chk = CheckboxList("master_menu_title", entries, hint_key="selective_hint")
    chosen_keys = chk.run()
    if chosen_keys is None:
        return None

    chosen_configs = [k.removeprefix("config_") for k in chosen_keys if k.startswith("config_")]
    do_wallpapers = "assets_wallpapers" in chosen_keys
    do_backup = "behavior_backup" in chosen_keys

    return {
        "configs": chosen_configs,
        "wallpapers": do_wallpapers,
        "backup": do_backup,
    }


def snapshot_menu_loop() -> None:
    """Snapshot management interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("snapshot_sub_create")),
            MenuItem(label=msg("snapshot_sub_list")),
            MenuItem(label=msg("snapshot_sub_delete"), style="warn"),
            MenuItem(label=msg("snapshot_sub_rollback")),
            MenuItem(label=msg("snapshot_sub_back"), style="subtle"),
        ]
        menu = Menu("snapshot_menu_title", items, hint_key="submenu_hint", compact=True)
        choice = menu.run()
        if choice == 0:
            sys.stdout.write(msg("snapshot_note_prompt"))
            sys.stdout.flush()
            drain_stdin()
            note = sys.stdin.readline().strip()
            backup_configs(note=note, interactive=True)
            press_any_key()
        elif choice == 1:
            list_backups()
            press_any_key()
        elif choice == 2:
            delete_backup("")
            press_any_key()
        elif choice == 3:
            rollback_configs("")
            press_any_key()
        elif choice == 4:
            break


def deps_menu_loop() -> bool:
    """Dependencies & Recommended apps submenu."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return False
    from nyxuri.pkg.platform import backend_available
    if not backend_available():
        print(msg("deps_menu_unsupported"))
        return False

    while True:
        items = [
            MenuItem(label=msg("deps_sub_core")),
            MenuItem(label=msg("deps_sub_apps")),
            MenuItem(label=msg("deps_sub_back"), style="subtle"),
        ]
        menu = Menu("deps_menu_title", items, hint_key="submenu_hint", compact=True)
        choice = menu.run()
        if choice == 0: run_dep_menu_loop(); press_any_key()
        elif choice == 1: run_optional_apps_menu_loop(); press_any_key()
        elif choice == 2: break
    return True


def preset_switcher_loop() -> None:
    """Interactive Preset Studio (§9). Left = apps, right = presets + in-place actions."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    from nyxuri.desktop.presets import get_preset_info
    from nyxuri.deploy.preset import list_parts, get_active_part, apply_part

    from nyxuri.deploy.preset import _is_deployable_app
    apps = [app for app in discover_config_items() if _is_deployable_app(app)]

    def on_action(action: str, app: str, name: str) -> Optional[str]:
        if action == "apply":
            clear_screen()
            ok = apply_preset(app, name)
            # 操作报告含冲突/快照位置；等待用户阅读，避免被预设列表重绘吞掉。
            press_any_key()
            return msg("preset_toast_applied", app, name) if ok else msg("preset_apply_failed", app, name)
        elif action == "apply_part":
            slot, variant = name.split(":", 1)
            clear_screen()
            ok = apply_part(app, slot, variant)
            press_any_key()
            return msg("preset_part_toast_applied", app, slot, variant) if ok else msg("preset_apply_failed", app, f"{slot}:{variant}")
        elif action == "save":
            ok = save_preset(app, name)
            return msg("preset_toast_saved", app, name) if ok else None
        elif action == "delete":
            clear_screen()
            ok = delete_preset(app, name)
            press_any_key()
            return msg("preset_toast_deleted", app, name) if ok else None
        elif action == "edit":
            edit_preset(app, name)
            return msg("preset_edit_opened", app, name)
        return None

    PresetSwitcher(
        apps=apps,
        presets_for=collect_presets,
        info_for=get_preset_info,
        on_action=on_action,
        parts_for=list_parts,
        active_part_for=get_active_part,
    ).run()


def main_menu_loop() -> None:
    """Main Nyxuri control panel interactive loop."""
    from nyxuri.installer.workflows import install_configs_workflow

    env = get_env()
    while True:
        items = [
            # 部署
            MenuItem(label=msg("menu_opt1"), group_header=msg("menu_group_deploy")),
            MenuItem(label=msg("menu_opt_preset")),
            MenuItem(label=msg("menu_opt2")),
            # 管理
            MenuItem(label=msg("menu_opt3"), group_header=msg("menu_group_maint")),
            MenuItem(label=msg("menu_opt4")),
            MenuItem(label=msg("menu_apply_local")),
            MenuItem(label=msg("menu_opt7"), style="warn"),
            # 诊断
            MenuItem(label=msg("menu_opt5"), group_header=msg("menu_group_system")),
            MenuItem(label=msg("menu_opt6")),
            # 单元
            MenuItem(label=msg("menu_opt_workshop"), group_header=msg("menu_group_units")),
            # 退出
            MenuItem(label=msg("menu_opt0"), style="subtle"),
        ]
        menu = Menu("menu_title", items, hint_key="menu_hint")
        choice = menu.run()

        if choice == 0:
            install_configs_workflow("full")
        elif choice == 1:
            preset_switcher_loop()
        elif choice == 2:
            deps_menu_loop()
        elif choice == 3:
            snapshot_menu_loop()
        elif choice == 4:
            update_result = safe_git_pull(env.repo_dir)
            if update_result is True:
                print(msg("source_update_done"))
                press_any_key()
                # Re-exec first: the deploy offer must run on the freshly
                # pulled code, not on modules loaded before the pull.
                exec_cli(env, **{PENDING_UPGRADE_ENV: "",
                                 PENDING_UPGRADE_MENU_ENV: "1"})
            elif update_result is False:
                print(msg("updating_failed"), file=sys.stderr)
            else:
                print(msg("update_skipped_local_hint"))
            press_any_key()
        elif choice == 5:
            from nyxuri.installer.workflows import offer_overwrite_upgrade
            offer_overwrite_upgrade()
            press_any_key()
        elif choice == 6:
            uninstall_nyxuri("")
            press_any_key()
        elif choice == 7:
            run_doctor()
            press_any_key()
        elif choice == 8:
            generate_bug_report()
            press_any_key()
        elif choice == 9:
            from nyxuri.tui import UnitWorkshop
            UnitWorkshop().run()
        elif choice == 10:
            sys.exit(0)
