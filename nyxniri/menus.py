"""Interactive control panel and component selection."""

import os
import shutil
import sys
from typing import List, Optional

from nyxniri.constants import CLI_CMD, PENDING_UPGRADE_ENV, PENDING_UPGRADE_MENU_ENV
from nyxniri.core import get_env, log_msg
from nyxniri.deploy import (
    apply_preset,
    collect_presets,
    delete_preset,
    discover_config_items,
    discover_manifest_apps,
    discover_optional_apps,
    edit_preset,
    save_preset,
    wallpapers_pack_present,
)
from nyxniri.deps import is_dep_installed, run_dep_menu_loop, run_optional_apps_menu_loop
from nyxniri.doctor import generate_bug_report, run_doctor
from nyxniri.modules.fcitx import (
    fcitx_enabled,
    fcitx_install,
    fcitx_status,
    fcitx_status_label,
    fcitx_uninstall,
    fcitx5_installed,
)
from nyxniri.modules.greeter import (
    greeter_install,
    greeter_status,
    greeter_status_label,
    greeter_uninstall,
)
from nyxniri.modules import (
    fisher_install,
    fisher_status,
    fisher_status_label,
    fisher_uninstall,
    gtktheme_install,
    gtktheme_status,
    gtktheme_status_label,
    gtktheme_uninstall,
)
from nyxniri.state import (
    backup_configs,
    delete_backup,
    list_backups,
    rollback_configs,
    uninstall_nyxniri,
)
from nyxniri.i18n import msg
from nyxniri.network import safe_git_pull
from nyxniri.tui import (
    CheckboxEntry,
    CheckboxList,
    MenuItem,
    Menu,
    PresetSwitcher,
    drain_stdin,
    pad_display,
    press_any_key,
)

def run_master_component_menu(is_update: bool = False, mode: str = "full") -> Optional[dict]:
    """Interactive checklist for choosing configs, wallpapers, modules, and backup behavior."""
    items = discover_config_items()
    entries: List[CheckboxEntry] = []

    # 1. Configs — optional apps (listed in .optional-apps.toml) show install
    #    status, so the user sees whether deploying this config is useful now.
    #    An optional app whose package is missing defaults UNCHECKED — don't
    #    litter ~/.config with config for an absent app. §6 / §8.4 path-display.
    optional_set = set(discover_optional_apps())
    manifests = dict(discover_manifest_apps())
    for item in items:
        label = msg("master_item_config", item)
        checked = True
        if item in optional_set:
            m = manifests.get(item)
            if m is not None:
                is_inst = is_dep_installed(m.detect)
                label = f"{label}  {msg('installed') if is_inst else msg('missing')}"
                if not is_inst:
                    checked = False
        entries.append(CheckboxEntry(key=f"config_{item}", label=label, checked=checked))

    if mode == "full" or is_update:
        # 2. Heavy assets (wallpapers)
        wp_checked = not wallpapers_pack_present()
        wp_status = msg("status_wallpapers_installed") if wallpapers_pack_present() else msg("status_wallpapers_missing")
        entries.append(CheckboxEntry(
            key="assets_wallpapers",
            label=msg("master_item_asset", f"Wallpapers & Videos {wp_status}"),
            checked=wp_checked,
        ))

        # 3. Fcitx5
        if fcitx5_installed():
            fcitx_check = not (is_update and not fcitx_enabled())
            entries.append(CheckboxEntry(
                key="module_fcitx",
                label=msg("master_item_module", f"NyxMellow fcitx5 {fcitx_status_label()}"),
                checked=fcitx_check,
            ))

        # 4. Greeter
        entries.append(CheckboxEntry(
            key="module_greeter",
            label=msg("master_item_module", f"Noctalia Greeter {greeter_status_label()}"),
            checked=False,
        ))

    # 5. Behavior: Backup
    entries.append(CheckboxEntry(key="sep_behavior", label=msg("master_item_behavior"), is_separator=True))
    entries.append(CheckboxEntry(key="behavior_backup", label=msg("master_item_backup"), checked=True))

    chk = CheckboxList("master_menu_title", entries, hint_key="selective_hint")
    chosen_keys = chk.run()
    if chosen_keys is None:
        return None

    chosen_configs = [k.removeprefix("config_") for k in chosen_keys if k.startswith("config_")]
    do_wallpapers = "assets_wallpapers" in chosen_keys
    do_fcitx = "module_fcitx" in chosen_keys
    do_greeter = "module_greeter" in chosen_keys
    do_backup = "behavior_backup" in chosen_keys

    return {
        "configs": chosen_configs,
        "wallpapers": do_wallpapers,
        "fcitx": do_fcitx,
        "greeter": do_greeter,
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


def greeter_menu_loop() -> None:
    """Noctalia Greeter interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("greeter_sub_install")),
            MenuItem(label=msg("greeter_sub_status")),
            MenuItem(label=msg("greeter_sub_uninstall"), style="warn"),
            MenuItem(label=msg("greeter_sub_back"), style="subtle"),
        ]
        menu = Menu("greeter_menu_title", items, hint_key="submenu_hint", compact=True)
        choice = menu.run()
        if choice == 0: greeter_install(); press_any_key()
        elif choice == 1: greeter_status(); press_any_key()
        elif choice == 2: greeter_uninstall(); press_any_key()
        elif choice == 3: break


def fcitx_menu_loop() -> None:
    """NyxMellow Fcitx5 skin interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("fcitx_sub_install")),
            MenuItem(label=msg("fcitx_sub_status")),
            MenuItem(label=msg("fcitx_sub_uninstall"), style="warn"),
            MenuItem(label=msg("fcitx_sub_back"), style="subtle"),
        ]
        menu = Menu("fcitx_menu_title", items, hint_key="submenu_hint", compact=True)
        choice = menu.run()
        if choice == 0: fcitx_install(); press_any_key()
        elif choice == 1: fcitx_status(); press_any_key()
        elif choice == 2: fcitx_uninstall(); press_any_key()
        elif choice == 3: break


def gtk_menu_loop() -> None:
    """GTK Material You theme interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("gtk_sub_install")),
            MenuItem(label=msg("gtk_sub_status")),
            MenuItem(label=msg("gtk_sub_uninstall"), style="warn"),
            MenuItem(label=msg("gtk_sub_back"), style="subtle"),
        ]
        menu = Menu("gtk_menu_title", items, hint_key="submenu_hint", compact=True)
        choice = menu.run()
        if choice == 0: gtktheme_install(); press_any_key()
        elif choice == 1: gtktheme_status(); press_any_key()
        elif choice == 2: gtktheme_uninstall(); press_any_key()
        elif choice == 3: break


def fisher_menu_loop() -> None:
    """fisher plugin manager interactive submenu."""
    while True:
        items = [
            MenuItem(label=msg("fisher_sub_install")),
            MenuItem(label=msg("fisher_sub_status")),
            MenuItem(label=msg("fisher_sub_uninstall"), style="warn"),
            MenuItem(label=msg("fisher_sub_back"), style="subtle"),
        ]
        menu = Menu("fisher_menu_title", items, hint_key="submenu_hint", compact=True)
        choice = menu.run()
        if choice == 0: fisher_install(); press_any_key()
        elif choice == 1: fisher_status(); press_any_key()
        elif choice == 2: fisher_uninstall(); press_any_key()
        elif choice == 3: break


def deps_menu_loop() -> None:
    """Dependencies & Recommended apps submenu."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return
    if not shutil.which("pacman"):
        print(msg("deps_menu_unsupported"))
        return

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


def extensions_menu_loop() -> None:
    """Extensions interactive submenu: greeter / fcitx / gtk / fisher."""
    while True:
        label_greeter = pad_display(msg("ext_sub_greeter"), 26) + greeter_status_label()
        label_fcitx = pad_display(msg("ext_sub_fcitx"), 26) + fcitx_status_label()
        label_gtk = pad_display(msg("ext_sub_gtk"), 26) + gtktheme_status_label()
        label_fisher = pad_display(msg("ext_sub_fisher"), 26) + fisher_status_label()

        items = [
            MenuItem(label=label_greeter),
            MenuItem(label=label_fcitx),
            MenuItem(label=label_gtk),
            MenuItem(label=label_fisher),
            MenuItem(label=msg("ext_back"), style="subtle"),
        ]
        menu = Menu("ext_menu_title", items, hint_key="submenu_hint", compact=True)
        choice = menu.run()
        if choice == 0: greeter_menu_loop()
        elif choice == 1: fcitx_menu_loop()
        elif choice == 2: gtk_menu_loop()
        elif choice == 3: fisher_menu_loop()
        elif choice == 4: break


def preset_switcher_loop() -> None:
    """Interactive Preset Studio (§9). Left = apps, right = presets + in-place actions."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    from nyxniri.deploy.preset import get_preset_info

    apps = discover_config_items()

    def on_action(action: str, app: str, name: str) -> Optional[str]:
        if action == "apply":
            ok = apply_preset(app, name)
            return msg("preset_toast_applied", app, name) if ok else msg("preset_apply_failed", app, name)
        elif action == "save":
            ok = save_preset(app, name)
            return msg("preset_toast_saved", app, name) if ok else None
        elif action == "delete":
            ok = delete_preset(app, name)
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
    ).run()


def main_menu_loop() -> None:
    """Main NyxNiri control panel interactive loop."""
    from nyxniri.workflows import install_configs_workflow

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
            MenuItem(label=msg("menu_opt7"), style="warn"),
            # 诊断
            MenuItem(label=msg("menu_opt5"), group_header=msg("menu_group_system")),
            MenuItem(label=msg("menu_opt6")),
            # 扩展
            MenuItem(label=msg("menu_opt8")),
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
                print(msg("updating_done"))
                press_any_key()
                # Re-exec first: the deploy offer must run on the freshly
                # pulled code, not on modules loaded before the pull.
                try:
                    os.execve(sys.executable, [sys.executable, "-m", CLI_CMD],
                              {**os.environ, PENDING_UPGRADE_ENV: "",
                               PENDING_UPGRADE_MENU_ENV: "1"})
                except Exception as e:
                    log_msg("ERROR", f"Re-exec failed: {e}")
                    print(msg("update_restart_needed"), file=sys.stderr)
            elif update_result is False:
                print(msg("updating_failed"), file=sys.stderr)
            press_any_key()
        elif choice == 5:
            uninstall_nyxniri("")
            press_any_key()
        elif choice == 6:
            run_doctor()
            press_any_key()
        elif choice == 7:
            generate_bug_report()
            press_any_key()
        elif choice == 8:
            extensions_menu_loop()
        elif choice == 9:
            sys.exit(0)

