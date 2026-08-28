"""Bilingual internationalization and translation engine with automatic fallbacks."""

import os
import sys
from typing import Any, Dict

from nyxniri.constants import Colors, PROJECT_NAME

_CURRENT_LANG: str = "zh" if "zh" in os.environ.get("LANG", "").lower() or "zh" in os.environ.get("LC_ALL", "").lower() else "en"

def get_lang() -> str:
    """Get currently selected language mode ('zh' or 'en')."""
    return _CURRENT_LANG

def set_lang(lang: str) -> None:
    """Set language mode ('zh' or 'en')."""
    global _CURRENT_LANG
    _CURRENT_LANG = "zh" if lang.startswith("zh") else "en"
    _MSG_CACHE.clear()

def text(zh: str, en: str) -> str:
    """Pick a one-off bilingual string by active language.

    Escape hatch for diagnostic/status lines not worth a TRANSLATIONS entry
    (``msg()`` remains the default for keyed strings). Centralizes the per-module
    ``_text()`` copies that had spread across doctor/fcitx/greeter/gtktheme.
    """
    return zh if get_lang() == "zh" else en

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # Status badges
    "installed": {
        "zh": f"{Colors.BOLD_GREEN}[已安装]{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[Installed]{Colors.RESET}",
    },
    "missing": {
        "zh": f"{Colors.BOLD_RED}[未安装]{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[Not installed]{Colors.RESET}",
    },

    # Main Menu
    "menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── {PROJECT_NAME} 控制面板 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── {PROJECT_NAME} Control Panel ──{Colors.RESET}\n",
    },
    "menu_group_deploy": {
        "zh": f"  {Colors.BOLD_BLUE}部署{Colors.RESET}",
        "en": f"  {Colors.BOLD_BLUE}Setup{Colors.RESET}",
    },
    "menu_opt1": {
        "zh": "应用配置",
        "en": "Apply configs",
    },
    "menu_opt_preset": {
        "zh": "切换预设",
        "en": "Switch preset",
    },
    "menu_opt2": {
        "zh": "软件与依赖",
        "en": "Software & Dependencies",
    },
    "menu_group_maint": {
        "zh": f"  {Colors.BOLD_BLUE}管理{Colors.RESET}",
        "en": f"  {Colors.BOLD_BLUE}Manage{Colors.RESET}",
    },
    "menu_group_system": {
        "zh": f"  {Colors.BOLD_BLUE}诊断{Colors.RESET}",
        "en": f"  {Colors.BOLD_BLUE}Diagnostics{Colors.RESET}",
    },
    "menu_opt3": {
        "zh": "快照管理",
        "en": "Snapshots",
    },
    "menu_opt4": {
        "zh": "检查更新",
        "en": "Check updates",
    },
    "menu_opt5": {
        "zh": "系统诊断",
        "en": "System diagnostics",
    },
    "menu_opt6": {
        "zh": "导出报告",
        "en": "Export report",
    },
    "menu_opt7": {
        "zh": "卸载",
        "en": "Uninstall",
    },
    "menu_opt8": {
        "zh": "扩展",
        "en": "Extensions",
    },
    "menu_opt0": {
        "zh": "退出",
        "en": "Exit",
    },

    # Snapshot Submenu
    "snapshot_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 快照管理 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Snapshot Management ──{Colors.RESET}\n",
    },
    "snapshot_sub_create": {
        "zh": "创建快照",
        "en": "Create Snapshot",
    },
    "snapshot_sub_list": {
        "zh": "查看快照列表",
        "en": "List Snapshots",
    },
    "snapshot_sub_delete": {
        "zh": "删除快照",
        "en": "Delete Snapshot",
    },
    "snapshot_sub_rollback": {
        "zh": "回滚快照",
        "en": "Rollback Snapshot",
    },
    "snapshot_sub_back": {
        "zh": "返回",
        "en": "Back",
    },

    # Extensions Submenu
    "ext_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 扩展 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Extensions ──{Colors.RESET}\n",
    },
    "ext_sub_greeter": {
        "zh": "Noctalia Greeter",
        "en": "Noctalia Greeter",
    },
    "ext_sub_fcitx": {
        "zh": "NyxMellow fcitx5 皮肤",
        "en": "NyxMellow fcitx5 skin",
    },
    "ext_sub_gtk": {
        "zh": "GTK Material You 主题",
        "en": "GTK Material You theme",
    },
    "ext_sub_fisher": {
        "zh": "fisher 插件管理器",
        "en": "fisher plugin manager",
    },
    "ext_back": {
        "zh": "返回",
        "en": "Back",
    },

    # Greeter Submenu
    "greeter_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── Noctalia Greeter ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Noctalia Greeter ──{Colors.RESET}\n",
    },
    "greeter_sub_install": {
        "zh": "安装与配置",
        "en": "Install & Configure",
    },
    "greeter_sub_status": {
        "zh": "查看状态",
        "en": "Show Status",
    },
    "greeter_sub_uninstall": {
        "zh": "卸载配置",
        "en": "Uninstall Config",
    },
    "greeter_sub_back": {
        "zh": "返回",
        "en": "Back",
    },

    # Fcitx Submenu
    "fcitx_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── NyxMellow fcitx5 皮肤 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── NyxMellow fcitx5 Skin ──{Colors.RESET}\n",
    },
    "fcitx_sub_install": {
        "zh": "安装皮肤",
        "en": "Install Skin",
    },
    "fcitx_sub_status": {
        "zh": "查看状态",
        "en": "Show Status",
    },
    "fcitx_sub_uninstall": {
        "zh": "卸载皮肤",
        "en": "Uninstall Skin",
    },
    "fcitx_sub_back": {
        "zh": "返回",
        "en": "Back",
    },

    # GTK Theme Submenu
    "gtk_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── GTK Material You 主题 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── GTK Material You Theme ──{Colors.RESET}\n",
    },
    "gtk_sub_install": {
        "zh": "安装",
        "en": "Install",
    },
    "gtk_sub_status": {
        "zh": "查看状态",
        "en": "Show status",
    },
    "gtk_sub_uninstall": {
        "zh": "卸载",
        "en": "Uninstall",
    },
    "gtk_sub_back": {
        "zh": "返回",
        "en": "Back",
    },

    # Fisher Submenu
    "fisher_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── fisher ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── fisher ──{Colors.RESET}\n",
    },
    "fisher_sub_install": {
        "zh": "安装",
        "en": "Install",
    },
    "fisher_sub_status": {
        "zh": "查看状态",
        "en": "Show status",
    },
    "fisher_sub_uninstall": {
        "zh": "卸载",
        "en": "Uninstall",
    },
    "fisher_sub_back": {
        "zh": "返回",
        "en": "Back",
    },

    # Module Status Labels
    "status_installed_enabled": {
        "zh": f"{Colors.BOLD_GREEN}[已安装+已启用]{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[Installed + Enabled]{Colors.RESET}",
    },
    "status_installed": {
        "zh": f"{Colors.BOLD_YELLOW}[已安装]{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[Installed]{Colors.RESET}",
    },
    "status_not_installed": {
        "zh": f"{Colors.BOLD_RED}[未安装]{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[Not installed]{Colors.RESET}",
    },
    "status_enabled": {
        "zh": f"{Colors.BOLD_GREEN}[已启用]{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[Enabled]{Colors.RESET}",
    },
    "status_disabled": {
        "zh": f"{Colors.BOLD_YELLOW}[未启用]{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[Not enabled]{Colors.RESET}",
    },
    "status_fcitx5_missing": {
        "zh": f"{Colors.BOLD_RED}[fcitx5 未安装]{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[fcitx5 not installed]{Colors.RESET}",
    },
    "status_wallpapers_installed": {
        "zh": f"{Colors.BOLD_GREEN}[已下载]{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[Downloaded]{Colors.RESET}",
    },
    "status_wallpapers_missing": {
        "zh": f"{Colors.BOLD_YELLOW}[未下载]{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[Not downloaded]{Colors.RESET}",
    },

    # Wallpapers
    "msg_downloading_wallpapers": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 拉取壁纸包…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Downloading wallpapers…{Colors.RESET}",
    },
    "msg_downloading_wallpapers_node": {
        "zh": "  [{0}] 从 [{1}] 节点拉取壁纸仓库…",
        "en": "  [{0}] Pulling from [{1}]…",
    },
    "msg_wallpapers_download_success": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 壁纸包已部署{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Wallpapers deployed{Colors.RESET}",
    },
    "msg_wallpapers_download_failed": {
        "zh": f"{Colors.BOLD_RED}[!] 壁纸包下载失败，改用内置壁纸{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Wallpaper download failed; using the built-in fallback{Colors.RESET}",
    },
    "msg_wallpapers_refresh_failed": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 壁纸包刷新失败，现有内容未改动{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Wallpaper refresh failed; the existing pack was kept{Colors.RESET}",
    },

    # Install Flow
    "fcitx_skipped_not_installed": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 未检测到 fcitx5，已跳过皮肤激活。安装后运行: nyxniri fcitx install{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] fcitx5 not detected; skin activation skipped. Run: nyxniri fcitx install{Colors.RESET}",
    },
    "install_cancelled": {
        "zh": f"{Colors.BOLD_BLUE}已取消，未写入配置{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}Cancelled; no configs were written{Colors.RESET}",
    },
    "install_step_configs": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] 安装配置…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] Installing configs…{Colors.RESET}",
    },
    "install_step_wallpapers": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] 安装壁纸…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] Installing wallpapers…{Colors.RESET}",
    },
    "install_step_deps": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] 安装依赖…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] Installing dependencies…{Colors.RESET}",
    },
    "install_step_fcitx": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] 配置 fcitx5 皮肤…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] Configuring fcitx5 skin…{Colors.RESET}",
    },
    "install_step_greeter": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] 配置 Noctalia Greeter…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [{Colors.BOLD_CYAN}{{0}}{Colors.BOLD_BLUE}] Configuring Noctalia Greeter…{Colors.RESET}",
    },

    # Summary screen
    "summary_title_install": {
        "zh": "主人，NyxNiri 装完了喵~",
        "en": "All set, nya~",
    },
    "summary_title_update": {
        "zh": "主人，NyxNiri 更新完了喵~",
        "en": "All updated, nya~",
    },
    "summary_title_test": {
        "zh": "测试部署完成喵~",
        "en": "Test deploy complete nya~",
    },
    "summary_title_failed": {
        "zh": "安装未完成",
        "en": "Installation incomplete",
    },
    "summary_section_details": {
        "zh": "明细",
        "en": "Details",
    },
    "summary_item_configs_ok": {
        "zh": "配置:       已安装 {0} 项",
        "en": "Configs:        {0} installed",
    },
    "summary_item_configs_skip": {
        "zh": "配置:       已跳过",
        "en": "Configs:        Skipped",
    },
    "summary_item_configs_failed": {
        "zh": "配置:       安装失败 ({0})",
        "en": "Configs:        Failed ({0})",
    },
    "summary_item_wallpapers_downloaded": {
        "zh": "壁纸包:     已下载",
        "en": "Wallpapers:     Downloaded",
    },
    "summary_item_wallpapers_existing": {
        "zh": "壁纸包:     已存在",
        "en": "Wallpapers:     Already present",
    },
    "summary_item_wallpapers_fallback": {
        "zh": "壁纸包:     仅内置",
        "en": "Wallpapers:     Built-in only",
    },
    "summary_item_wallpapers_refresh_failed": {
        "zh": "壁纸包:     刷新失败，已保留原包",
        "en": "Wallpapers:     Refresh failed; kept existing",
    },
    "summary_item_wallpapers_failed_fallback": {
        "zh": "壁纸包:     下载失败，已用内置",
        "en": "Wallpapers:     Download failed; using built-in",
    },
    "summary_item_wallpapers_failed": {
        "zh": "壁纸包:     下载失败",
        "en": "Wallpapers:     Download failed",
    },
    "summary_item_wallpapers_skip": {
        "zh": "壁纸包:     已跳过",
        "en": "Wallpapers:     Skipped",
    },
    "summary_item_fcitx_ok": {
        "zh": "输入法:     NyxMellow fcitx5 skin",
        "en": "Input Method:   NyxMellow fcitx5 skin",
    },
    "summary_item_fcitx_skip": {
        "zh": "输入法:     已跳过",
        "en": "Input Method:   Skipped",
    },
    "summary_item_deps_ok": {
        "zh": "系统依赖:   依赖已就绪",
        "en": "System Deps:    Ready",
    },
    "summary_item_deps_skip": {
        "zh": "系统依赖:   未完全满足",
        "en": "System Deps:    Incomplete",
    },
    "summary_item_greeter_ok": {
        "zh": "登录器:     Noctalia Greeter",
        "en": "Greeter:        Noctalia Greeter",
    },
    "summary_section_preserved": {
        "zh": "保留的配置",
        "en": "Preserved configs",
    },
    "summary_section_next": {
        "zh": "下一步",
        "en": "Next Steps",
    },
    "summary_next_start": {
        "zh": "启动桌面 : 运行 niri-session",
        "en": "Start Desktop : Run niri-session",
    },
    "summary_next_manual": {
        "zh": "速查手册 : 运行 nyxhelp",
        "en": "Quick Manual  : Run nyxhelp",
    },
    "summary_next_panel": {
        "zh": "控制面板 : 运行 nyxniri",
        "en": "Control Panel : Run nyxniri",
    },

    # Summary action card
    "summary_action_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 下一步 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Next Steps ──{Colors.RESET}\n",
    },
    "summary_action_apps": {
        "zh": "常用软件",
        "en": "Recommended Apps",
    },
    "summary_action_star": {
        "zh": "给作者 GitHub 点 Star",
        "en": "Star on GitHub",
    },
    "summary_action_exit": {
        "zh": "退出",
        "en": "Exit",
    },
    "summary_action_hint": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Enter/Space] 选择  [0/q] 退出{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Enter/Space] Select  [0/q] Exit{Colors.RESET}",
    },
    "summary_action_hint_short": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓] 移动  [Enter] 选择  [q] 退出{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓] Move  [Enter] Select  [q] Exit{Colors.RESET}",
    },
    "msg_star_opened": {
        "zh": f"\n  {Colors.BOLD_GREEN}[✓] 感谢支持！已打开项目主页:{Colors.RESET} {{0}}\n",
        "en": f"\n  {Colors.BOLD_GREEN}[✓] Thanks for your support! Opened repository:{Colors.RESET} {{0}}\n",
    },

    # Test & General Prompts
    "test_start": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [test] 幂等测试部署 (跳过备份与依赖检查)…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [test] Idempotent test deploy (skipped backup & deps)…{Colors.RESET}",
    },
    "menu_hint": {
        "zh": f"\n  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Enter/Space] 选择  [0/q] 退出{Colors.RESET}",
        "en": f"\n  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Enter/Space] Select  [0/q] Exit{Colors.RESET}",
    },
    "menu_hint_short": {
        "zh": f"\n  {Colors.DARK_GRAY}[↑/↓] 移动  [Enter] 选择  [q] 退出{Colors.RESET}",
        "en": f"\n  {Colors.DARK_GRAY}[↑/↓] Move  [Enter] Select  [q] Exit{Colors.RESET}",
    },
    "submenu_hint": {
        "zh": f"\n  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Enter/Space] 选择  [0/q] 返回{Colors.RESET}",
        "en": f"\n  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Enter/Space] Select  [0/q] Back{Colors.RESET}",
    },
    "submenu_hint_short": {
        "zh": f"\n  {Colors.DARK_GRAY}[↑/↓] 移动  [Enter] 选择  [q] 返回{Colors.RESET}",
        "en": f"\n  {Colors.DARK_GRAY}[↑/↓] Move  [Enter] Select  [q] Back{Colors.RESET}",
    },
    "checklist_hint_short": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓] 移动  [Space] 勾选  [Enter] 确认  [Esc] 取消{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓] Move  [Space] Toggle  [Enter] Confirm  [Esc] Cancel{Colors.RESET}",
    },
    "press_any_key": {
        "zh": "\n按任意键继续…",
        "en": "\nPress any key to continue…",
    },
    "generating_report": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在收集诊断数据…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Collecting diagnostic data…{Colors.RESET}",
    },
    "report_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 诊断报告已导出至:{Colors.RESET} {{0}}\n{Colors.BOLD_CYAN}提交 Issue 请附带此文件{Colors.RESET}\n{Colors.DARK_GRAY}QQ 群: 631425889 | Telegram: @Echoes678{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Report exported to:{Colors.RESET} {{0}}\n{Colors.BOLD_CYAN}Please attach this file when opening an issue{Colors.RESET}\n{Colors.DARK_GRAY}QQ Group: 631425889 | Telegram: @Echoes678{Colors.RESET}",
    },

    # Overwrite & Upgrade
    "overwrite_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── NyxNiri 配置更新 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── NyxNiri Config Update ──{Colors.RESET}\n",
    },
    "overwrite_opt1": {
        "zh": "更新组件",
        "en": "Update components",
    },
    "overwrite_opt2": {
        "zh": "查看改动",
        "en": "View changes",
    },
    "overwrite_opt3": {
        "zh": "仅更新代码",
        "en": "Update code only",
    },
    "selective_hint": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Space] 切换  [a] 全选  [n] 清空  [Enter] 确认  [Esc] 取消{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Space] Toggle  [a] All  [n] None  [Enter] Confirm  [Esc] Cancel{Colors.RESET}",
    },
    "upgrading_selected": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在更新选中组件…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Updating selected components…{Colors.RESET}",
    },
    "master_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 选择组件 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Select components ──{Colors.RESET}\n",
    },
    "master_item_config": {
        "zh": "配置: {0}",
        "en": "Config: {0}",
    },
    "master_item_module": {
        "zh": "扩展: {0}",
        "en": "Extension: {0}",
    },
    "master_item_asset": {
        "zh": "壁纸包: {0}",
        "en": "Wallpapers: {0}",
    },
    "master_item_behavior": {
        "zh": "\n  ── 选项 ──",
        "en": "\n  ── Options ──",
    },
    "master_item_backup": {
        "zh": "安装前自动创建快照",
        "en": "Auto-create snapshot before install",
    },
    "diff_viewer_title": {
        "zh": f"\n{Colors.BOLD_CYAN}:: 配置改动 (按 q 退出){Colors.RESET}",
        "en": f"\n{Colors.BOLD_CYAN}:: Changes (press q to quit){Colors.RESET}",
    },

    # Uninstall
    "uninstall_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 卸载 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Uninstall ──{Colors.RESET}\n",
    },
    "uninstall_hint": {
        "zh": f"  {Colors.DARK_GRAY}空格 切换  a 全选  n 全不选  Enter 确认  q 取消{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}Space toggle  a all  n none  Enter confirm  q cancel{Colors.RESET}",
    },
    "uninstall_group_user": {
        "zh": f"  {Colors.BOLD_BLUE}用户配置{Colors.RESET}",
        "en": f"  {Colors.BOLD_BLUE}User config{Colors.RESET}",
    },
    "uninstall_group_self": {
        "zh": f"  {Colors.BOLD_BLUE}NyxNiri 自身{Colors.RESET}",
        "en": f"  {Colors.BOLD_BLUE}NyxNiri itself{Colors.RESET}",
    },
    "uninstall_group_modules": {
        "zh": f"  {Colors.BOLD_BLUE}扩展{Colors.RESET}",
        "en": f"  {Colors.BOLD_BLUE}Extensions{Colors.RESET}",
    },
    "uninstall_item_configs": {
        "zh": "~/.config/<{0} 个 app 配置>",
        "en": "~/.config/<{0} app configs>",
    },
    "uninstall_item_nyx_dir": {
        "zh": "~/.config/NyxNiri/  (快照 + 预设)",
        "en": "~/.config/NyxNiri/  (snapshots + presets)",
    },
    "uninstall_item_archives": {
        "zh": "~/.config/NyxNiri_archive_*  (历史归档)",
        "en": "~/.config/NyxNiri_archive_*  (past archives)",
    },
    "uninstall_item_wallpapers": {
        "zh": "~/Pictures/Wallpapers/",
        "en": "~/Pictures/Wallpapers/",
    },
    "uninstall_item_cli": {
        "zh": "~/.local/bin/nyxniri  (命令入口)",
        "en": "~/.local/bin/nyxniri  (CLI entry)",
    },
    "uninstall_item_state": {
        "zh": "~/.local/state/NyxNiri/  (锁 + 日志)",
        "en": "~/.local/state/NyxNiri/  (lock + log)",
    },
    "uninstall_item_cache": {
        "zh": "~/.cache/NyxNiri/  (curl 缓存)",
        "en": "~/.cache/NyxNiri/  (curl cache)",
    },
    "uninstall_item_fcitx": {
        "zh": "fcitx NyxMellow 皮肤  (~/.local/share/fcitx5/themes/nyxmellow/)",
        "en": "fcitx NyxMellow skin  (~/.local/share/fcitx5/themes/nyxmellow/)",
    },
    "uninstall_item_gtk": {
        "zh": "GTK Material You 主题  (~/.config/gtk-3.0,4.0/gtk.css)",
        "en": "GTK Material You theme  (~/.config/gtk-3.0,4.0/gtk.css)",
    },
    "uninstall_item_greeter": {
        "zh": "Noctalia Greeter  [sudo]",
        "en": "Noctalia Greeter  [sudo]",
    },
    "uninstall_item_fisher": {
        "zh": "fisher + fish 插件  (~/.config/fish/functions/fisher.fish, conf.d/)",
        "en": "fisher + fish plugins  (~/.config/fish/functions/fisher.fish, conf.d/)",
    },
    "uninstall_removed": {
        "zh": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} 已删除: {{0}}",
        "en": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} Removed: {{0}}",
    },
    "uninstall_skipped": {
        "zh": f"{Colors.DARK_GRAY}[!]{Colors.RESET} 不存在，跳过: {{0}}",
        "en": f"{Colors.DARK_GRAY}[!]{Colors.RESET} Not present, skipped: {{0}}",
    },
    "uninstall_failed": {
        "zh": f"{Colors.BOLD_RED}[✗]{Colors.RESET} 失败: {{0}}",
        "en": f"{Colors.BOLD_RED}[✗]{Colors.RESET} Failed: {{0}}",
    },
    "uninstall_module_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} 已清理: {{0}}",
        "en": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} Cleaned: {{0}}",
    },
    "uninstall_system_hint": {
        "zh": f"\n  {Colors.BOLD_YELLOW}源码包归 pacman 管，完全卸载请再跑: sudo pacman -R nyxniri-git{Colors.RESET}",
        "en": f"\n  {Colors.BOLD_YELLOW}The system package is managed by pacman; run: sudo pacman -R nyxniri-git{Colors.RESET}",
    },
    "uninstall_archived": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 当前配置已归档至:{Colors.RESET} {{0}}",
        "en": f"{Colors.BOLD_GREEN}[✓] Configs archived to:{Colors.RESET} {{0}}",
    },
    "uninstall_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] NyxNiri 卸载完成{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Uninstall complete{Colors.RESET}",
    },
    "purge_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 深度清理完成{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Deep clean complete{Colors.RESET}",
    },
    "purge_warning": {
        "zh": f"\n{Colors.BOLD_RED}[!] 将清空配置、快照、缓存与壁纸。不可撤销。{Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}[!] This clears configs, snapshots, cache, and wallpapers. It cannot be undone.{Colors.RESET}",
    },
    "purge_prompt": {
        "zh": "▸ 确认深度清理？[y/N]: ",
        "en": "▸ Continue with deep clean? [y/N]: ",
    },
    "purge_cancelled": {
        "zh": f"{Colors.BOLD_BLUE}已取消深度清理{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}Deep clean cancelled{Colors.RESET}",
    },
    "purge_start": {
        "zh": f"\n{Colors.BOLD_RED}:: 开始深度清理…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}:: Starting deep clean…{Colors.RESET}",
    },
    "restore_origin_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已恢复至初始环境{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Restored system to original state{Colors.RESET}",
    },

    # Rollback & Snapshots
    "no_backups_found": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 未找到可用快照{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] No configuration snapshots found{Colors.RESET}",
    },
    "available_backups": {
        "zh": f"\n{Colors.BOLD_CYAN}:: 可用快照列表{Colors.RESET}",
        "en": f"\n{Colors.BOLD_CYAN}:: Available NyxNiri Snapshots{Colors.RESET}",
    },
    "select_rollback_target": {
        "zh": "▸ 请选择要恢复的快照序号 (Ctrl+C 取消): ",
        "en": "▸ Select snapshot to restore (Ctrl+C to cancel): ",
    },
    "rollback_select_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 选择要恢复的快照 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Select Snapshot to Restore ──{Colors.RESET}\n",
    },
    "rollback_select_hint": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Enter] 确认回滚  [Esc/q] 取消{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Enter] Confirm Rollback  [Esc/q] Cancel{Colors.RESET}",
    },
    "delete_snapshot_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 选择要删除的快照 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Select Snapshots to Delete ──{Colors.RESET}\n",
    },
    "delete_snapshot_hint": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Space] 勾选  [a] 全选  [n] 清空  [Enter] 确认  [Esc] 取消{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Space] Toggle  [a] All  [n] None  [Enter] Confirm  [Esc] Cancel{Colors.RESET}",
    },
    "rollback_invalid_num": {
        "zh": f"{Colors.BOLD_RED}[✗] 无效序号，已取消回滚{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Invalid selection{Colors.RESET}",
    },
    "rollback_source_missing": {
        "zh": f"{Colors.BOLD_RED}[✗] 所选快照已不存在，已取消回滚: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Selected snapshot is no longer available; rollback cancelled: {{0}}{Colors.RESET}",
    },
    "rollback_no_items": {
        "zh": f"{Colors.BOLD_RED}[✗] 所选快照没有可恢复的配置，已取消回滚{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Selected snapshot contains no restorable configuration; rollback cancelled{Colors.RESET}",
    },
    "rolling_back": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在从快照 [{{0}}] 恢复配置…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Restoring from snapshot [{{0}}]…{Colors.RESET}",
    },
    "pre_rollback_backup": {
        "zh": f"{Colors.DARK_GRAY}[✓] 已自动为当前配置创建回滚前快照: {{0}}{Colors.RESET}",
        "en": f"{Colors.DARK_GRAY}[✓] Auto-saved pre-rollback snapshot: {{0}}{Colors.RESET}",
    },
    "rollback_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已恢复至快照: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Restored to snapshot: {{0}}{Colors.RESET}",
    },
    "snapshot_note_prompt": {
        "zh": "▸ 请输入快照备注 (直接回车跳过): ",
        "en": "▸ Enter snapshot note (press Enter to skip): ",
    },
    "delete_confirm": {
        "zh": f"\n{Colors.BOLD_RED}[!] 将删除快照: {{0}}{Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}[!] Will delete snapshot: {{0}}{Colors.RESET}",
    },
    "delete_confirm_many": {
        "zh": f"\n{Colors.BOLD_RED}[!] 将删除以下 {{0}} 个快照:{Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}[!] Will delete these {{0}} snapshots:{Colors.RESET}",
    },
    "delete_prompt": {
        "zh": "▸ 确认删除所选快照？[y/N]: ",
        "en": "▸ Delete the selected snapshot(s)? [y/N]: ",
    },
    "delete_cancelled": {
        "zh": f"{Colors.BOLD_BLUE}已取消删除{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}Deletion cancelled{Colors.RESET}",
    },
    "delete_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已删除快照 [{{0}}]，剩余 {{1}} 个{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Deleted snapshot [{{0}}], {{1}} snapshot(s) remaining{Colors.RESET}",
    },
    "delete_invalid_num": {
        "zh": f"{Colors.BOLD_RED}[✗] 无效序号，已取消删除{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Invalid selection{Colors.RESET}",
    },
    "delete_none_selected": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 未选择任何快照，已取消删除{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] No snapshots selected; deletion cancelled{Colors.RESET}",
    },
    "delete_failed": {
        "zh": f"{Colors.BOLD_RED}[✗] 删除快照失败: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Failed to delete snapshot: {{0}}{Colors.RESET}",
    },
    "delete_done_many": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已删除 {{0}} 个快照，剩余 {{1}} 个{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Deleted {{0}} snapshots, {{1}} remaining{Colors.RESET}",
    },

    # Software & Dependencies
    "deps_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 软件与依赖 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Software & Dependencies ──{Colors.RESET}\n",
    },
    "deps_sub_core": {
        "zh": "核心依赖",
        "en": "Core dependencies",
    },
    "deps_sub_apps": {
        "zh": "常用软件",
        "en": "Recommended apps",
    },
    "deps_sub_back": {
        "zh": "返回",
        "en": "Back",
    },
    "dep_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 核心依赖 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Core Dependencies ──{Colors.RESET}\n",
    },
    "dep_menu_hint": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Space] 切换  [a] 全选  [n] 清空  [Enter] 安装  [0/q] 返回{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Space] Toggle  [a] All  [n] None  [Enter] Install  [0/q] Back{Colors.RESET}",
    },
    "installing_selected": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在安装选中依赖…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Installing selected dependencies…{Colors.RESET}",
    },
    "installing_official_packages": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 安装官方仓库软件包: {{0}}…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Installing official packages: {{0}}…{Colors.RESET}",
    },
    "installing_aur_packages": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 安装 AUR 软件包: {{0}}…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Installing AUR packages: {{0}}…{Colors.RESET}",
    },
    "opt_apps_menu_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── 常用软件 ──{Colors.RESET}\n",
        "en": f"\n  {Colors.BOLD_CYAN}── Recommended Apps ──{Colors.RESET}\n",
    },
    "opt_apps_menu_hint": {
        "zh": f"  {Colors.DARK_GRAY}[↑/↓/j/k] 移动  [Space] 切换  [a] 全选  [n] 清空  [Enter] 安装  [0/q] 返回{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[↑/↓/j/k] Move  [Space] Toggle  [a] All  [n] None  [Enter] Install  [0/q] Back{Colors.RESET}",
    },
    "app_nautilus": {
        "zh": "Nautilus (文件管理器)",
        "en": "Nautilus (File Manager)",
    },
    "app_missioncenter": {
        "zh": "Mission Center (系统监视器)",
        "en": "Mission Center (System Monitor)",
    },
    "app_fcitx5_rime": {
        "zh": "Fcitx5 + 雾凇拼音 (输入法)",
        "en": "Fcitx5 + Rime Ice (Input Method)",
    },
    "installing_selected_apps": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在安装常用软件…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Installing recommended apps…{Colors.RESET}",
    },
    "opt_apps_install_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 常用软件安装完成{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Recommended apps installed{Colors.RESET}",
    },
    "opt_apps_none_selected": {
        "zh": f"{Colors.DARK_GRAY}未选择任何软件。{Colors.RESET}",
        "en": f"{Colors.DARK_GRAY}No apps selected.{Colors.RESET}",
    },
    "interactive_terminal_required": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 需要交互式终端。{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Needs an interactive terminal.{Colors.RESET}",
    },
    "new_deps_detected": {
        "zh": f"\n  {Colors.BOLD_YELLOW}[!] 检测到未安装的依赖:{Colors.RESET} {{0}}",
        "en": f"\n  {Colors.BOLD_YELLOW}[!] Missing dependencies detected:{Colors.RESET} {{0}}",
    },
    "prompt_install_missing_deps": {
        "zh": "▸ 是否现在安装？[Y/n]: ",
        "en": "▸ Install now? [Y/n]: ",
    },
    "deps_install_skipped": {
        "zh": f"{Colors.DARK_GRAY}已跳过安装。稍后可运行 nyxniri deps 安装。{Colors.RESET}",
        "en": f"{Colors.DARK_GRAY}Skipped installation. Run nyxniri deps to install anytime.{Colors.RESET}",
    },

    # Greeter
    "greeter_install_title": {
        "zh": f"\n{Colors.BOLD_PURPLE}:: Noctalia Greeter 安装{Colors.RESET}",
        "en": f"\n{Colors.BOLD_PURPLE}:: Noctalia Greeter{Colors.RESET}",
    },
    "greeter_install_pkgs": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在安装 greetd 与 noctalia-greeter…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Installing greetd & noctalia-greeter…{Colors.RESET}",
    },
    "greeter_aur_required": {
        "zh": f"{Colors.BOLD_YELLOW}[!] noctalia-greeter (AUR) 需要 paru 或 yay。请先安装 AUR helper。{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] noctalia-greeter (AUR) requires paru/yay. Install an AUR helper first.{Colors.RESET}",
    },
    "greeter_pkg_failed": {
        "zh": f"{Colors.BOLD_RED}[!] 软件包 {{0}} 安装失败，继续后续步骤…{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] Failed to install {{0}}; continuing…{Colors.RESET}",
    },
    "greeter_install_failed": {
        "zh": f"{Colors.BOLD_RED}[!] noctalia-greeter 安装失败。稍后运行 nyxniri greeter install 重试。{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] Install failed. Retry later with: nyxniri greeter install{Colors.RESET}",
    },
    "greeter_install_skipped": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 已跳过 Noctalia Greeter 配置{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Noctalia Greeter setup skipped{Colors.RESET}",
    },
    "greeter_dm_conflict": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 存在冲突的显示管理器 ({{0}})，请先手动将其禁用。{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Conflicting display manager detected ({{0}}). Please disable it manually.{Colors.RESET}",
    },
    "greeter_config_written": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已写入 greetd 配置: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] greetd config written: {{0}}{Colors.RESET}",
    },
    "greeter_config_failed": {
        "zh": f"{Colors.BOLD_RED}[!] 写入 greetd 配置失败: {{0}} (需要 sudo 权限){Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] Failed to write greetd config: {{0}} (requires sudo){Colors.RESET}",
    },
    "greeter_state_dir_created": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已创建状态目录 /var/lib/noctalia-greeter{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Created state dir /var/lib/noctalia-greeter{Colors.RESET}",
    },
    "greeter_cmd_failed": {
        "zh": f"{Colors.BOLD_RED}[!] 特权命令执行失败: {{0}} (需要 sudo 权限){Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] Privileged command failed: {{0}} (requires sudo){Colors.RESET}",
    },
    "greeter_polkit_skip": {
        "zh": f"{Colors.BOLD_GREEN}[✓] polkit 规则已存在，跳过{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] polkit rule already present; skipped{Colors.RESET}",
    },
    "greeter_polkit_written": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已写入 polkit 免密规则: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] polkit rule written: {{0}}{Colors.RESET}",
    },
    "greeter_polkit_failed": {
        "zh": f"{Colors.BOLD_RED}[!] 写入 polkit 规则失败{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] Failed to write polkit rule{Colors.RESET}",
    },
    "greeter_enabled": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已启用 greetd 服务 (重启生效){Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] greetd service enabled (takes effect after reboot){Colors.RESET}",
    },
    "greeter_enabled_skip": {
        "zh": f"{Colors.BOLD_GREEN}[✓] greetd 服务已启用{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] greetd service already enabled{Colors.RESET}",
    },
    "greeter_enable_failed": {
        "zh": f"{Colors.BOLD_RED}[!] 启用 greetd 服务失败。请手动运行: sudo systemctl enable greetd{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] Failed to enable greetd. Run manually: sudo systemctl enable greetd{Colors.RESET}",
    },
    "greeter_reboot_hint": {
        "zh": f"{Colors.BOLD_CYAN}重启后生效。主题同步: Noctalia 设置 → 安全 → Noctalia Greeter → Sync Now{Colors.RESET}",
        "en": f"{Colors.BOLD_CYAN}Active after reboot. Sync theme: Noctalia Settings → Security → Noctalia Greeter → Sync Now{Colors.RESET}",
    },
    "greeter_status_title": {
        "zh": f"\n{Colors.BOLD_CYAN}:: Noctalia Greeter 状态{Colors.RESET}",
        "en": f"\n{Colors.BOLD_CYAN}:: Noctalia Greeter status{Colors.RESET}",
    },
    "fisher_status_title": {
        "zh": f"\n{Colors.BOLD_CYAN}:: fisher 插件管理器状态{Colors.RESET}",
        "en": f"\n{Colors.BOLD_CYAN}:: fisher plugin manager status{Colors.RESET}",
    },
    "greeter_status_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 登录界面已就绪{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Login screen ready{Colors.RESET}",
    },
    "greeter_status_hint": {
        "zh": f"{Colors.BOLD_CYAN}运行 nyxniri greeter install 完成配置{Colors.RESET}",
        "en": f"{Colors.BOLD_CYAN}Run nyxniri greeter install to set up{Colors.RESET}",
    },
    "greeter_uninstall_title": {
        "zh": f"\n{Colors.BOLD_YELLOW}:: 卸载 Noctalia Greeter{Colors.RESET}",
        "en": f"\n{Colors.BOLD_YELLOW}:: Uninstall Noctalia Greeter{Colors.RESET}",
    },
    "greeter_uninstall_restored": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已还原 greetd 配置: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Restored greetd config: {{0}}{Colors.RESET}",
    },
    "greeter_uninstall_nobackup": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 未找到 greetd 配置备份，已保留当前配置{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] No greetd backup found; kept current config{Colors.RESET}",
    },
    "greeter_uninstall_polkit": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已移除 polkit 免密规则{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] polkit rule removed{Colors.RESET}",
    },
    "greeter_uninstall_state_dir": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已清理状态目录: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Removed state directory: {{0}}{Colors.RESET}",
    },
    "greeter_uninstall_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 登录界面已卸载。若需移除软件包: paru -R noctalia-greeter greetd{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Login screen uninstalled. To remove packages: paru -R noctalia-greeter greetd{Colors.RESET}",
    },

    # Fcitx5
    "fcitx_install_title": {
        "zh": f"\n{Colors.BOLD_PURPLE}:: NyxMellow fcitx5 皮肤安装{Colors.RESET}",
        "en": f"\n{Colors.BOLD_PURPLE}:: NyxMellow fcitx5 skin{Colors.RESET}",
    },
    "fcitx_skip_no_fcitx5": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 未找到 fcitx5，已跳过皮肤激活 (安装后运行 nyxniri fcitx install 即可){Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] fcitx5 not detected; skipped skin activation (theme templates deployed; run nyxniri fcitx install after installing fcitx5).{Colors.RESET}",
    },
    "fcitx_templates_deployed": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 主题模板已部署: ~/.local/share/fcitx5/themes/nyxmellow/templates/{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Theme templates deployed: ~/.local/share/fcitx5/themes/nyxmellow/templates/{Colors.RESET}",
    },
    "fcitx_render_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓] Noctalia 已按当前主题渲染 nyxmellow 皮肤{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Noctalia rendered skin with current theme{Colors.RESET}",
    },
    "fcitx_render_pending": {
        "zh": f"{Colors.BOLD_YELLOW}[!] noctalia 未运行，模板将在下次主题切换时生效{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] noctalia not running; templates will apply on next theme change{Colors.RESET}",
    },
    "fcitx_theme_set": {
        "zh": f"{Colors.BOLD_GREEN}[✓] fcitx5 已切换主题: nyxmellow ({{0}}){Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] fcitx5 switched to theme: nyxmellow ({{0}}){Colors.RESET}",
    },
    "fcitx_restarted": {
        "zh": f"{Colors.BOLD_GREEN}[✓] fcitx5 已重启以加载新皮肤{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] fcitx5 restarted{Colors.RESET}",
    },
    "fcitx_status_title": {
        "zh": f"\n{Colors.BOLD_CYAN}:: NyxMellow fcitx5 皮肤状态{Colors.RESET}",
        "en": f"\n{Colors.BOLD_CYAN}:: NyxMellow fcitx5 skin status{Colors.RESET}",
    },
    "fcitx_uninstall_title": {
        "zh": f"\n{Colors.BOLD_YELLOW}:: 卸载 NyxMellow fcitx5 皮肤{Colors.RESET}",
        "en": f"\n{Colors.BOLD_YELLOW}:: Uninstall NyxMellow fcitx5 skin{Colors.RESET}",
    },
    "fcitx_uninstall_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] NyxMellow 皮肤已卸载，fcitx5 主题已还原{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] NyxMellow skin uninstalled; fcitx5 theme reverted{Colors.RESET}",
    },
    "fcitx_registered": {
        "zh": f"{Colors.BOLD_GREEN}[✓] Noctalia 模板已注册 ({{0}}){Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Noctalia templates registered ({{0}}){Colors.RESET}",
    },
    "fcitx_not_registered": {
        "zh": f"{Colors.BOLD_YELLOW}[!] Noctalia 模板未注册 ({{0}}){Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Noctalia templates not registered ({{0}}){Colors.RESET}",
    },

    # GTK Material You Theme
    "gtk_install_title": {
        "zh": f"\n{Colors.BOLD_PURPLE}:: GTK Material You 主题安装{Colors.RESET}",
        "en": f"\n{Colors.BOLD_PURPLE}:: GTK Material You theme{Colors.RESET}",
    },
    "gtk_render_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓] Noctalia 已按当前主题渲染 GTK 配色{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Noctalia rendered GTK theme with current palette{Colors.RESET}",
    },
    "gtk_render_pending": {
        "zh": f"{Colors.BOLD_YELLOW}[!] noctalia 未运行，GTK 配色将在下次主题切换时生效{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] noctalia not running; GTK theme will apply on next theme change{Colors.RESET}",
    },
    "gtk_not_registered": {
        "zh": f"{Colors.BOLD_YELLOW}[!] GTK 模板未注册，请先运行 nyxniri install 安装 noctalia 配置{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] GTK templates not registered; run nyxniri install to set up noctalia config{Colors.RESET}",
    },
    "gtk_status_title": {
        "zh": f"\n{Colors.BOLD_CYAN}:: GTK Material You 主题状态{Colors.RESET}",
        "en": f"\n{Colors.BOLD_CYAN}:: GTK Material You theme status{Colors.RESET}",
    },
    "gtk_uninstall_title": {
        "zh": f"\n{Colors.BOLD_YELLOW}:: 卸载 GTK Material You 主题{Colors.RESET}",
        "en": f"\n{Colors.BOLD_YELLOW}:: Uninstall GTK Material You theme{Colors.RESET}",
    },
    "gtk_unregistered": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已从 {{0}} 配置中移除 GTK 模板注册{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] GTK templates unregistered from {{0}} config{Colors.RESET}",
    },
    "gtk_css_removed": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已删除: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Removed: {{0}}{Colors.RESET}",
    },
    "gtk_uninstall_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] GTK Material You 主题已移除，GTK 应用回退到 adw-gtk3 默认配色{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] GTK Material You theme removed; GTK apps reverted to adw-gtk3 defaults{Colors.RESET}",
    },

    # Core Install & Backup
    "backing_up": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在创建配置快照…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Creating configuration snapshot…{Colors.RESET}",
    },
    "backup_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已创建快照: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Snapshot created: {{0}}{Colors.RESET}",
    },
    "copying_configs": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在安装配置…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Installing configs…{Colors.RESET}",
    },
    "copy_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 配置已安装{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Configs installed{Colors.RESET}",
    },
    "deploy_failed": {
        "zh": f"{Colors.BOLD_RED}[✗] 配置安装失败: {{0}}。已停止后续步骤。{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Config install failed: {{0}}. Remaining steps stopped.{Colors.RESET}",
    },
    "log_deploy_config_failed": {
        "zh": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} 配置安装失败: {{0}}",
        "en": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} Config install failed: {{0}}",
    },

    # Doctor
    "running_doctor": {
        "zh": f"\n{Colors.BOLD_PURPLE}:: 正在诊断系统…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_PURPLE}:: Running diagnostics…{Colors.RESET}",
    },
    "doctor_sec_desktop": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [1/5] 桌面与合成器{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [1/5] Desktop & Compositor{Colors.RESET}",
    },
    "doctor_sec_core": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [2/5] 核心依赖与脚本{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [2/5] Core Tools & Scripts{Colors.RESET}",
    },
    "doctor_sec_hardware": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [3/5] 音频、显示与外设{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [3/5] Audio, Displays & Hardware{Colors.RESET}",
    },
    "doctor_sec_services": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [4/5] 门户与系统服务{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [4/5] Portals & System Services{Colors.RESET}",
    },
    "doctor_sec_extensions": {
        "zh": f"\n{Colors.BOLD_BLUE}:: [5/5] 扩展与环境健康{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: [5/5] Extensions & Health{Colors.RESET}",
    },
    "doctor_summary_tally": {
        "zh": f"  {Colors.BOLD_GREEN}[✓] {{0}} 项正常{Colors.RESET}  {Colors.BOLD_YELLOW}[!] {{1}} 项提示{Colors.RESET}  {Colors.BOLD_RED}[✗] {{2}} 项异常{Colors.RESET}",
        "en": f"  {Colors.BOLD_GREEN}[✓] {{0}} passed{Colors.RESET}  {Colors.BOLD_YELLOW}[!] {{1}} warnings{Colors.RESET}  {Colors.BOLD_RED}[✗] {{2}} errors{Colors.RESET}",
    },
    "doctor_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} {{0}}",
        "en": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} {{0}}",
    },
    "doctor_warn": {
        "zh": f"{Colors.BOLD_YELLOW}[!]{Colors.RESET} {{0}}",
        "en": f"{Colors.BOLD_YELLOW}[!]{Colors.RESET} {{0}}",
    },
    "doctor_err": {
        "zh": f"{Colors.BOLD_RED}[✗]{Colors.RESET} {{0}}",
        "en": f"{Colors.BOLD_RED}[✗]{Colors.RESET} {{0}}",
    },
    "all_done": {
        "zh": f"\n{Colors.BOLD_GREEN}[✓] 诊断完成{Colors.RESET}",
        "en": f"\n{Colors.BOLD_GREEN}[✓] Diagnostics complete{Colors.RESET}",
    },
    "reboot_hint": {
        "zh": f"{Colors.BOLD_CYAN}建议重启 Noctalia 或重新加载 Niri 以使配置生效{Colors.RESET}",
        "en": f"{Colors.BOLD_CYAN}Restart Noctalia or reload Niri for settings to take effect{Colors.RESET}",
    },

    # System Errors & Preflight
    "err_sudo_aborted": {
        "zh": f"\n{Colors.BOLD_RED}[✗] 缺少管理员权限。已中止。{Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}[✗] Administrator privileges required. Aborted.{Colors.RESET}",
    },
    "err_sudo_missing": {
        "zh": f"\n{Colors.BOLD_RED}[✗] 未找到 sudo。请先安装 sudo，再重新运行。{Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}[✗] sudo is not installed. Install it, then retry.{Colors.RESET}",
    },
    "err_aborted_code": {
        "zh": f"\n{Colors.BOLD_RED}[✗] 异常终止 (退出码: {{0}}){Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}[✗] Aborted with exit code: {{0}}{Colors.RESET}",
    },
    "err_already_running": {
        "zh": f"\n{Colors.BOLD_YELLOW}[!] 进程已在运行 (PID: {{0}}){Colors.RESET}",
        "en": f"\n{Colors.BOLD_YELLOW}[!] Process already running (PID: {{0}}){Colors.RESET}",
    },
    "err_root_denied": {
        "zh": f"\n{Colors.BOLD_RED}[✗] 请以普通用户身份运行 NyxNiri，不要使用 root。{Colors.RESET}",
        "en": f"\n{Colors.BOLD_RED}[✗] Run NyxNiri as a normal user, not root.{Colors.RESET}",
    },
    "err_engine_incomplete": {
        "zh": f"{Colors.BOLD_RED}[✗] 引擎文件不完整或更新中途被打断。{Colors.RESET}\n    重新运行 install.sh 即可恢复；若仍失败，请重新克隆仓库。",
        "en": f"{Colors.BOLD_RED}[✗] Engine files are incomplete or an update was interrupted.{Colors.RESET}\n    Rerun install.sh to recover; if it still fails, re-clone the repository.",
    },
    "check_probe_timeout": {
        "zh": "检测项超时，已跳过",
        "en": "Check timed out, skipped",
    },
    "err_unknown_command": {
        "zh": f"{Colors.BOLD_RED}[✗] 未知命令: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Unknown command: {{0}}{Colors.RESET}",
    },
    "err_invalid_args": {
        "zh": f"{Colors.BOLD_RED}[✗] 参数无效。用法: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Invalid arguments. Usage: {{0}}{Colors.RESET}",
    },
    "err_theme_sync_missing": {
        "zh": f"{Colors.BOLD_RED}[✗] 未找到 theme-sync.sh。请先运行 nyxniri install config。{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] theme-sync.sh was not found. Run nyxniri install config first.{Colors.RESET}",
    },
    "cli_help": {
        "zh": """{0} 配置管理工具 ({1})
用法: {1} [命令] [参数]

命令:
  install [full|config]              应用配置（full = 含壁纸、扩展、依赖）
  update [--force|--no-deploy]       更新源码，并按需应用配置
  preset <app> [list|apply|save|edit|delete] <name>  切换或管理预设
  snapshot [备注]                    创建配置快照
  snapshot delete [序号]             删除快照；无序号时可批量选择
  rollback [序号]                    恢复配置快照
  list                               列出快照
  uninstall                          归档当前配置并卸载
  purge                              清空配置、快照、缓存与壁纸
  doctor                             诊断桌面环境
  deps [core|apps]                   管理依赖或常用软件
  apps                               打开常用软件菜单
  wallpapers                         下载壁纸包
  theme [toggle|dark|light|sync|status]  切换或同步深浅主题
  bug | report                       导出诊断报告
  test                               开发者沙箱部署测试
  greeter [install|status|uninstall] 管理 Noctalia Greeter
  fcitx [install|status|uninstall]   管理 NyxMellow fcitx5 皮肤
  gtk [install|status|uninstall]     管理 GTK Material You 主题
  fisher [install|status|uninstall]  管理 fisher 插件管理器
  help                               显示本帮助
  无参数                             打开控制面板""",
        "en": """{0} dotfiles manager ({1})
Usage: {1} [command] [args]

Commands:
  install [full|config]              Apply configs (full = wallpapers, extensions, deps)
  update [--force|--no-deploy]       Update source, optionally apply configs
  preset <app> [list|apply|save|edit|delete] <name>  Switch or manage presets
  snapshot [note]                    Create a config snapshot
  snapshot delete [index]            Delete snapshots; multi-select without index
  rollback [index]                   Restore a config snapshot
  list                               List snapshots
  uninstall                          Archive current configs and uninstall
  purge                              Clear configs, snapshots, cache, and wallpapers
  doctor                             Diagnose the desktop environment
  deps [core|apps]                   Manage dependencies or recommended apps
  apps                               Open the recommended apps menu
  wallpapers                         Download the wallpaper pack
  theme [toggle|dark|light|sync|status]  Switch or sync light/dark theme
  bug | report                       Export a diagnostic report
  test                               Run the developer sandbox deploy
  greeter [install|status|uninstall] Manage Noctalia Greeter
  fcitx [install|status|uninstall]   Manage the NyxMellow fcitx5 skin
  gtk [install|status|uninstall]     Manage the GTK Material You theme
  fisher [install|status|uninstall]  Manage the fisher plugin manager
  help                               Show this help
  no arguments                       Open the control panel""",
    },
    "preflight_express_summary": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 即将执行以下更改:{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Changes to apply:{Colors.RESET}",
    },
    "preflight_comp_config": {
        "zh": f"  {Colors.BOLD_CYAN}- 配置:{Colors.RESET} {{0}} 项",
        "en": f"  {Colors.BOLD_CYAN}- Configs:{Colors.RESET} {{0}} item(s)",
    },
    "preflight_comp_assets": {
        "zh": f"  {Colors.BOLD_CYAN}- 下载:{Colors.RESET} 壁纸包",
        "en": f"  {Colors.BOLD_CYAN}- Download:{Colors.RESET} wallpaper pack",
    },
    "preflight_comp_module_fcitx": {
        "zh": f"  {Colors.BOLD_CYAN}- 扩展:{Colors.RESET} {{0}} fcitx5 皮肤",
        "en": f"  {Colors.BOLD_CYAN}- Extension:{Colors.RESET} {{0}} fcitx5 skin",
    },
    "preflight_comp_module_greeter": {
        "zh": f"  {Colors.BOLD_CYAN}- 扩展:{Colors.RESET} {{0}}",
        "en": f"  {Colors.BOLD_CYAN}- Extension:{Colors.RESET} {{0}}",
    },
    "preflight_comp_deps": {
        "zh": f"  {Colors.BOLD_CYAN}- 依赖:{Colors.RESET} 检查并安装缺失项",
        "en": f"  {Colors.BOLD_CYAN}- Dependencies:{Colors.RESET} Check and install missing packages",
    },
    "preflight_comp_backup": {
        "zh": f"  {Colors.BOLD_CYAN}- 快照:{Colors.RESET} 写入前保存当前配置",
        "en": f"  {Colors.BOLD_CYAN}- Snapshot:{Colors.RESET} Save current configs before writing",
    },
    "preflight_custom_config_kept": {
        "zh": f"{Colors.BOLD_CYAN}[ 保留的自定义配置 ]{Colors.RESET}",
        "en": f"{Colors.BOLD_CYAN}[ Preserved custom configs ]{Colors.RESET}",
    },
    "preflight_sudo_prompt": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 以下步骤需要 sudo，验证一次：{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: These steps need sudo. Authenticate once:{Colors.RESET}",
    },

    # Network
    "net_pull_repo": {
        "zh": f"{Colors.BOLD_BLUE}:: 拉取仓库 (官方 -> gh-proxy)…{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}:: Pulling repository (Official -> gh-proxy)…{Colors.RESET}",
    },
    "net_pull_node": {
        "zh": f"\n  {Colors.BOLD_CYAN}[{{0}}/{{1}}] 从 [{{2}}] 节点拉取…{Colors.RESET}",
        "en": f"\n  {Colors.BOLD_CYAN}[{{0}}/{{1}}] Pulling from [{{2}}]…{Colors.RESET}",
    },
    "net_pull_node_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已从 [{{0}}] 拉取{Colors.RESET}\n",
        "en": f"{Colors.BOLD_GREEN}[✓] Pulled from [{{0}}]{Colors.RESET}\n",
    },
    "net_pull_node_fail": {
        "zh": f"{Colors.BOLD_RED}[!] 从 [{{0}}] 拉取失败，尝试下一节点…{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] Pull from [{{0}}] failed, trying next…{Colors.RESET}",
    },
    "net_pull_all_fail": {
        "zh": f"{Colors.BOLD_RED}[✗] 所有镜像节点均拉取失败。请检查网络。{Colors.RESET}\n",
        "en": f"{Colors.BOLD_RED}[✗] All mirror nodes failed. Please check network.{Colors.RESET}\n",
    },
    "net_download_asset": {
        "zh": f"{Colors.BOLD_BLUE}:: 下载资源 ({{0}}/{{1}})…{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}:: Downloading asset ({{0}}/{{1}})…{Colors.RESET}",
    },
    "net_download_hint": {
        "zh": f"  {Colors.DARK_GRAY}[Esc/Ctrl+C] 跳过当前节点并切换下一源{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[Esc/Ctrl+C] Skip this mirror and try the next{Colors.RESET}",
    },
    "net_download_node": {
        "zh": "  [{0}/{1}] [{2}] 下载中… ",
        "en": "  [{0}/{1}] [{2}] Downloading… ",
    },
    "net_download_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 成功 (HTTP 200, {{0}}ms){Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Success (HTTP 200, {{0}}ms){Colors.RESET}",
    },
    "net_download_node_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已通过 [{{0}}] 拉取{Colors.RESET}\n",
        "en": f"{Colors.BOLD_GREEN}[✓] Downloaded via [{{0}}]{Colors.RESET}\n",
    },
    "net_download_fail": {
        "zh": f"{Colors.BOLD_RED}[✗] 失败 (HTTP {{0}}){Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Failed (HTTP {{0}}){Colors.RESET}",
    },
    "net_download_interrupted": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 已跳过当前节点，尝试下一节点…{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Current mirror skipped; trying next…{Colors.RESET}",
    },
    "net_download_all_fail": {
        "zh": f"{Colors.BOLD_RED}[✗] 所有镜像节点均拉取失败{Colors.RESET}\n",
        "en": f"{Colors.BOLD_RED}[✗] All mirror nodes failed{Colors.RESET}\n",
    },

    # Logging & Atomic Install
    "log_keep_custom_file": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 保留自定义文件: ~/.config/{{0}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Preserved custom file: ~/.config/{{0}}",
    },
    "log_keep_custom_dir": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 保留自定义目录: ~/.config/{{0}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Preserved custom dir: ~/.config/{{0}}",
    },
    "log_keep_preserved_file": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 保留受保护文件: ~/.config/{{0}}/{{1}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Preserved file: ~/.config/{{0}}/{{1}}",
    },
    "log_deploy_config_item": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 安装配置: ~/.config/{{0}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Installed config: ~/.config/{{0}}",
    },
    "log_nvidia_gpu_detected": {
        "zh": ":: 检测到 NVIDIA 显卡，已启用相应环境变量",
        "en": ":: NVIDIA GPU detected (env enabled)",
    },
    "log_nvidia_gpu_not_detected": {
        "zh": ":: 未发现 NVIDIA GPU (保持默认)",
        "en": ":: No NVIDIA GPU detected (kept default env)",
    },
    "log_gtk_theme_init": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 初始化主题与 GTK 同步",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Initializing theme & GTK sync",
    },
    "log_enable_mpvpaper": {
        "zh": ":: 启用 mpvpaper 插件",
        "en": ":: Enabling mpvpaper plugin",
    },
    "log_check_fisher": {
        "zh": f"{Colors.BOLD_BLUE}:: 检查 Fisher…{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}:: Checking Fisher…{Colors.RESET}",
    },
    "log_install_fish_plugins": {
        "zh": ":: 安装 fish_plugins 插件…",
        "en": ":: Installing fish_plugins…",
    },
    "log_fisher_update_skipped": {
        "zh": f"{Colors.BOLD_RED}[!]{Colors.RESET} Fisher 更新跳过 (网络受限)",
        "en": f"{Colors.BOLD_RED}[!]{Colors.RESET} Fisher update skipped (network restricted)",
    },
    "log_fisher_install_skipped": {
        "zh": f"{Colors.BOLD_RED}[!]{Colors.RESET} Fisher 安装跳过 (网络受限)",
        "en": f"{Colors.BOLD_RED}[!]{Colors.RESET} Fisher install skipped (network restricted)",
    },
    "log_sync_wallpapers": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 同步壁纸库: {{0}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Syncing wallpapers: {{0}}",
    },
    "log_no_components_selected": {
        "zh": "未选择任何组件",
        "en": "No components selected",
    },
    "log_config_deploy_skipped": {
        "zh": "已跳过配置部署",
        "en": "Config deployment skipped",
    },
    "log_backup_item": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 已备份: ~/.config/{{0}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Backed up: ~/.config/{{0}}",
    },
    "log_restore_item": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 已恢复: ~/.config/{{0}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Restored: ~/.config/{{0}}",
    },
    "log_remove_item": {
        "zh": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} 已移除: ~/.config/{{0}}",
        "en": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} Removed: ~/.config/{{0}}",
    },
    "log_restoring_origin_config": {
        "zh": ":: 正在恢复初始配置: {0}…",
        "en": ":: Restoring initial backup: {0}…",
    },
    "log_uninstall_cancelled": {
        "zh": "已取消卸载",
        "en": "Uninstall cancelled",
    },
    "log_fcitx_template_missing": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} 仓库缺失主题模板源码: {{0}}",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} Theme template source missing: {{0}}",
    },
    "log_fcitx_template_unregistered": {
        "zh": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} {{0}} 模板注册已移除",
        "en": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} {{0}} template registration removed",
    },
    "log_fcitx_theme_dir_removed": {
        "zh": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} 已删除主题目录: {{0}}",
        "en": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} Removed theme dir: {{0}}",
    },
    "log_official_pkgs_partial_fail": {
        "zh": f"{Colors.BOLD_RED}[!]{Colors.RESET} 部分官方源软件包安装失败，继续后续步骤…",
        "en": f"{Colors.BOLD_RED}[!]{Colors.RESET} Some official packages failed to install; continuing…",
    },
    "log_aur_pkgs_partial_fail": {
        "zh": f"{Colors.BOLD_RED}[!]{Colors.RESET} 部分 AUR 软件包安装失败，继续后续步骤…",
        "en": f"{Colors.BOLD_RED}[!]{Colors.RESET} Some AUR packages failed to install; continuing…",
    },

    # AUR Bootstrap & Updates
    "aur_skip": {
        "zh": f"{Colors.BOLD_YELLOW}[!] AUR 软件包 ({{0}}) 需要 paru 或 yay，已跳过。{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] AUR packages ({{0}}) require paru/yay; skipped.{Colors.RESET}",
    },
    "aur_helper_required": {
        "zh": f"{Colors.BOLD_YELLOW}    请先安装 paru 或 yay，而后重新运行依赖安装。{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}    Install paru or yay first, then retry.{Colors.RESET}",
    },
    "aur_bootstrap_prompt": {
        "zh": "▸ 未找到可用 AUR 助手 (paru/yay)。是否自动安装 paru？[Y/n]: ",
        "en": "▸ No usable AUR helper (paru/yay) found. Auto-bootstrap paru? [Y/n]: ",
    },
    "aur_bootstrap_start": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 正在准备 paru…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Setting up paru…{Colors.RESET}",
    },
    "aur_bootstrap_cleanup": {
        "zh": f"{Colors.BOLD_BLUE}:: 移除残留 paru-bin 包…{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}:: Removing stale paru-bin packages…{Colors.RESET}",
    },
    "aur_bootstrap_repo": {
        "zh": f"{Colors.BOLD_BLUE}:: 从官方源安装 paru…{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}:: Installing paru from official repos…{Colors.RESET}",
    },
    "aur_bootstrap_source": {
        "zh": f"{Colors.BOLD_BLUE}:: 源码构建 paru (约 1-3 分钟)…{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}:: Building paru from source (~1-3 min)…{Colors.RESET}",
    },
    "aur_bootstrap_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓] paru 安装成功{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] paru installed successfully{Colors.RESET}",
    },
    "aur_bootstrap_failed": {
        "zh": f"{Colors.BOLD_RED}[!] paru 安装失败，已跳过 AUR 依赖。请手动安装后重试。{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[!] paru bootstrap failed; skipped AUR packages. Install manually and retry.{Colors.RESET}",
    },
    "aur_bootstrap_skip": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 已取消安装 paru，跳过 AUR 依赖{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Auto-install of paru cancelled; skipped AUR packages{Colors.RESET}",
    },
    "checking_mpvpaper": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 检查 mpvpaper 版本…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Checking mpvpaper version…{Colors.RESET}",
    },
    "mpvpaper_version_ok": {
        "zh": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} mpvpaper {{0}} >= 1.9，无已知内存泄漏",
        "en": f"{Colors.BOLD_GREEN}[✓]{Colors.RESET} mpvpaper {{0}} >= 1.9, no known memory leak",
    },
    "mpvpaper_leak_warn": {
        "zh": f"{Colors.BOLD_YELLOW}[!]{Colors.RESET} mpvpaper {{0}} 在默认硬解配置下存在 OpenGL 内存泄漏，建议升级至 1.9+ 或 mpvpaper-git\n   (参见: https://github.com/GhostNaN/mpvpaper/issues/127)",
        "en": f"{Colors.BOLD_YELLOW}[!]{Colors.RESET} mpvpaper {{0}} has an OpenGL memory leak. Upgrade to 1.9+ or install mpvpaper-git\n   (See: https://github.com/GhostNaN/mpvpaper/issues/127)",
    },
    "mpvpaper_upgrade_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] mpvpaper-git 已安装{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] mpvpaper-git installed{Colors.RESET}",
    },
    "mpvpaper_upgrade_skip": {
        "zh": "手动升级命令: paru -S mpvpaper-git 或 yay -S mpvpaper-git",
        "en": "Manual upgrade: paru -S mpvpaper-git or yay -S mpvpaper-git",
    },
    "mpvpaper_upgrade_prompt": {
        "zh": "是否立即安装 mpvpaper-git 修复版？ [y/N] ",
        "en": "Install mpvpaper-git fix now? [y/N] ",
    },
    "err_mpvpaper_git_failed": {
        "zh": f"{Colors.BOLD_RED}[✗] mpvpaper-git 安装失败{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Failed to install mpvpaper-git{Colors.RESET}",
    },
    "git_required": {
        "zh": f"{Colors.BOLD_RED}[✗] 未找到 git。请先安装。{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] git is missing. Please install it first.{Colors.RESET}",
    },
    "cloning_repo": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 拉取仓库至缓存 ({{0}})…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Pulling repository to cache ({{0}})…{Colors.RESET}",
    },
    "checking_updates": {
        "zh": f"\n{Colors.BOLD_BLUE}:: 检查更新…{Colors.RESET}",
        "en": f"\n{Colors.BOLD_BLUE}:: Checking for updates…{Colors.RESET}",
    },
    "updating_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 更新完成，正在重启…{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Update complete. Restarting…{Colors.RESET}",
    },
    "updating_failed": {
        "zh": f"{Colors.BOLD_RED}[✗] 更新失败。请检查网络与 Git 状态后重试 nyxniri update。{Colors.RESET}",
        "en": f"{Colors.BOLD_RED}[✗] Update failed. Check the network and Git state, then retry nyxniri update.{Colors.RESET}",
    },
    "update_restart_needed": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 更新已完成，但自动重启失败。请手动重新运行 nyxniri。{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Update complete, but auto-restart failed. Please re-run nyxniri manually.{Colors.RESET}",
    },
    "dirty_tree_warn": {
        "zh": f"{Colors.BOLD_YELLOW}[!] {{0}} 存在未提交的改动。{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] Uncommitted local changes detected in {{0}}.{Colors.RESET}",
    },
    "dirty_tree_confirm": {
        "zh": ":: 继续将丢弃这些改动。是否继续？[y/N]: ",
        "en": ":: Continuing will discard these changes. Continue? [y/N]: ",
    },
    "update_cancelled_dirty": {
        "zh": f"{Colors.BOLD_BLUE}已取消更新，改动已保留。{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}Update cancelled; local changes preserved.{Colors.RESET}",
    },
    "update_skipped_dev_repo": {
        "zh": f"\n{Colors.BOLD_YELLOW}[!] 本地仓库 ({{0}}) 有未提交的改动或分支偏离。{Colors.RESET}\n{Colors.BOLD_CYAN}已跳过更新，源码和现有配置均未改动。{Colors.RESET}\n",
        "en": f"\n{Colors.BOLD_YELLOW}[!] Local repo ({{0}}) has uncommitted changes or has diverged.{Colors.RESET}\n{Colors.BOLD_CYAN}Update skipped; source and installed configs were left unchanged.{Colors.RESET}\n",
    },
    "update_use_pacman": {
        "zh": f"\n{Colors.BOLD_CYAN}系统包由 pacman 管理，已跳过 git pull。更新请运行: sudo pacman -Syu nyxniri-git{Colors.RESET}\n",
        "en": f"\n{Colors.BOLD_CYAN}System package is managed by pacman; git pull skipped. Run: sudo pacman -Syu nyxniri-git{Colors.RESET}\n",
    },
    "update_pin_target": {
        "zh": f"{Colors.BOLD_BLUE}:: 正在切换到指定版本 ({{0}})…{Colors.RESET}",
        "en": f"{Colors.BOLD_BLUE}:: Switching to pinned ref ({{0}})…{Colors.RESET}",
    },
    "update_pin_done": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已固定到指定版本: {{0}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Pinned to ref: {{0}}{Colors.RESET}",
    },
    "path_occlusion_warn": {
        "zh": f"{Colors.BOLD_YELLOW}[!] 检测到 ~/.local/bin/nyxniri 遮蔽了系统包 (/usr/bin/nyxniri)。建议删除旧软链以使用系统包: rm ~/.local/bin/nyxniri{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] ~/.local/bin/nyxniri is shadowing the system package (/usr/bin/nyxniri). Remove the stale link to use the package: rm ~/.local/bin/nyxniri{Colors.RESET}",
    },

    # Presets
    "preset_list_title": {
        "zh": f"\n  {Colors.BOLD_CYAN}── {Colors.RESET}{{0}} 预设{Colors.BOLD_CYAN} ──{Colors.RESET}  ({Colors.DIM}* = 当前活动{Colors.RESET})\n",
        "en": f"\n  {Colors.BOLD_CYAN}── {Colors.RESET}{{0}} presets{Colors.BOLD_CYAN} ──{Colors.RESET}  ({Colors.DIM}* = active{Colors.RESET})\n",
    },
    "preset_src_official": {
        "zh": "官方",
        "en": "official",
    },
    "preset_src_user": {
        "zh": "用户",
        "en": "user",
    },
    "preset_applied": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 已切换 {{0}} 预设: {{1}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Switched {{0}} to preset: {{1}}",
    },
    "preset_apply_failed": {
        "zh": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} 切换 {{0}} 预设 {{1}} 失败",
        "en": f"  {Colors.BOLD_RED}[✗]{Colors.RESET} Failed to apply preset '{{1}}' to {{0}}",
    },
    "preset_not_found": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} {{0}} 没有名为 '{{1}}' 的预设",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} No preset '{{1}}' for {{0}}",
    },
    "preset_name_reserved": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} 预设名 '{{0}}' 是保留字（apply default = 回默认）",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} Preset name '{{0}}' is reserved (apply default = reset)",
    },
    "preset_official_name_collision": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} 预设名 '{{0}}' 与官方预设重名，请改名",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} Preset name '{{0}}' collides with an official preset; rename it",
    },
    "preset_nothing_to_save": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} {{0}} 尚无配置，无可保存",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} No {{0}} config to save yet",
    },
    "preset_saved": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 已保存 {{0}} 用户预设: {{1}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Saved {{0}} user preset: {{1}}",
    },
    "preset_delete_official_denied": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} 预设 '{{0}}' 是官方预设，无法删除",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} Preset '{{0}}' is official, cannot be deleted",
    },
    "preset_deleted": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 已删除 {{0}} 用户预设: {{1}}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Deleted {{0}} user preset: {{1}}",
    },
    "preset_edit_official_denied": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} '{{0}}' 是官方预设，不能编辑（先 save 成用户预设再改）",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} '{{0}}' is an official preset, can't edit (save a copy first)",
    },
    "preset_edit_notty": {
        "zh": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} 非交互终端，无法打开编辑器。预设目录: {{0}}",
        "en": f"  {Colors.BOLD_YELLOW}[!]{Colors.RESET} Non-interactive terminal, can't open editor. Preset dir: {{0}}",
    },
    "preset_edit_opened": {
        "zh": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} 已在编辑器打开 {{0}} 预设 {{1}}\n  {Colors.DIM}改完重新 `nyxniri preset {{0}} apply {{1}}` 即生效{Colors.RESET}",
        "en": f"  {Colors.BOLD_GREEN}[✓]{Colors.RESET} Opened {{0}} preset {{1}} in editor\n  {Colors.DIM}Re-run `nyxniri preset {{0}} apply {{1}}` to apply edits{Colors.RESET}",
    },
    "preset_warn_upstream_removed": {
        "zh": f"{Colors.BOLD_YELLOW}[!] {{0}}: 原预设 '{{1}}' 已被上游移除，已回退默认配置{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] {{0}}: preset '{{1}}' was removed upstream, fell back to defaults{Colors.RESET}",
    },
    "preset_warn_frozen": {
        "zh": f"{Colors.BOLD_YELLOW}[!] {{0}}: 活动预设 '{{1}}' 已不在仓库中，当前 ~/.config/{{0}} 内容保持冻结，未重新部署{Colors.RESET}\n    {Colors.BOLD_CYAN}运行 `{Colors.RESET}nyxniri preset {{0}} list{Colors.BOLD_CYAN}` 选新预设{Colors.RESET}",
        "en": f"{Colors.BOLD_YELLOW}[!] {{0}}: active preset '{{1}}' is no longer in the repo; ~/.config/{{0}} is frozen, not redeployed{Colors.RESET}\n    {Colors.BOLD_CYAN}Run `{Colors.RESET}nyxniri preset {{0}} list{Colors.BOLD_CYAN}` to pick a new preset{Colors.RESET}",
    },
    "preset_switcher_title": {
        "zh": "预设管理",
        "en": "Preset Management",
    },
    "preset_switcher_hint": {
        "zh": f"  {Colors.DARK_GRAY}[Enter] 展开/应用   [Tab] 详情   [s] 保存当前   [e] 编辑   [d] 删除   [q] 返回{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[Enter] Expand/Apply   [Tab] Details   [s] Save   [e] Edit   [d] Delete   [q] Back{Colors.RESET}",
    },
    "preset_switcher_hint_short": {
        "zh": f"  {Colors.DARK_GRAY}[Enter] 选  [Tab] 详  [s] 存  [e] 改  [d] 删  [q] 退{Colors.RESET}",
        "en": f"  {Colors.DARK_GRAY}[Enter] Select  [Tab] Info  [s] Save  [e] Edit  [d] Del  [q] Back{Colors.RESET}",
    },
    "preset_status_active": {
        "zh": f"{Colors.BOLD_GREEN}●{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}●{Colors.RESET}",
    },
    "preset_prompt_save_name": {
        "zh": "▸ 新预设名称 (Esc 取消): ",
        "en": "▸ New preset name (Esc to cancel): ",
    },
    "preset_prompt_delete_confirm": {
        "zh": "▸ 确认删除用户预设 '{0}'？[y/N]: ",
        "en": "▸ Delete user preset '{0}'? [y/N]: ",
    },
    "preset_toast_applied": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已应用 {{0}} 预设: {{1}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Applied {{0}} preset: {{1}}{Colors.RESET}",
    },
    "preset_toast_saved": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已保存 {{0}} 用户预设: {{1}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Saved {{0}} user preset: {{1}}{Colors.RESET}",
    },
    "preset_toast_deleted": {
        "zh": f"{Colors.BOLD_GREEN}[✓] 已删除 {{0}} 用户预设: {{1}}{Colors.RESET}",
        "en": f"{Colors.BOLD_GREEN}[✓] Deleted {{0}} user preset: {{1}}{Colors.RESET}",
    },
    "preset_info_source": {
        "zh": "源",
        "en": "Source",
    },
    "preset_info_files": {
        "zh": "包含文件",
        "en": "Included Files",
    },
    "preset_info_preserve": {
        "zh": "保留文件",
        "en": "Preserved Files",
    },
    "preset_info_none": {
        "zh": "(无)",
        "en": "(none)",
    },
    "preset_switcher_col_app": {
        "zh": "应用",
        "en": "App",
    },
    "preset_switcher_col_preset": {
        "zh": f"预设 ({{0}})",
        "en": f"Presets ({{0}})",
    },
}

_MSG_CACHE: Dict[str, str] = {}

def msg(key: str, *args: Any) -> str:
    if not args:
        cached = _MSG_CACHE.get(key)
        if cached is not None:
            return cached
    lang = get_lang()
    entry = TRANSLATIONS.get(key)
    if not entry:
        result = key if not args else f"{key} ({', '.join(str(a) for a in args)})"
        if not args:
            _MSG_CACHE[key] = result
        return result
    template = entry.get(lang) or entry.get("en") or key
    if args:
        try:
            return template.format(*args)
        except Exception:
            return template
    _MSG_CACHE[key] = template
    return template
