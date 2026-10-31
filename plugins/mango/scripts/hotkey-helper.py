#!/usr/bin/env python3
# ==============================================================================
# Mango WM Hotkey Helper / Cheatsheet (按键引导与速查器)
# Auto-generates a categorized, searchable hotkey guide from config.conf
# ==============================================================================

import os
import re
import sys
import shutil
import subprocess

CONFIG_PATH = os.path.expanduser("~/.config/mango/config.conf")
ROFI_THEME = os.path.expanduser("~/.config/rofi/noctalia.rasi")

# 人性化功能映射表 (function/command -> (简短名称, 详细说明, 分类))
PRESET_MAP = {
    # 核心与窗口管理
    "toggleoverview": ("全局窗口概览", "纵览所有工作区与窗口 (Hycov 模式)", "🪟 窗口与系统"),
    "togglejump": ("字母跳跃直达", "窗口浮现字母快捷键，按键瞬间跳转并切 Tag", "🪟 窗口与系统"),
    "focuslast": ("历史焦点切换", "切换回上一个聚焦的窗口", "🪟 窗口与系统"),
    "killclient": ("关闭当前窗口", "安全关闭当前获得焦点的窗口", "🪟 窗口与系统"),
    "spawn,kitty": ("打开终端", "启动 Kitty 终端", "🪟 窗口与系统"),
    "spawn,nautilus": ("打开文件管理器", "启动 Nautilus 文件管理器", "🪟 窗口与系统"),
    "togglefloating": ("切换浮动/平铺", "在浮动窗口与平铺排版间切换", "🪟 窗口与系统"),
    "togglefullscreen": ("切换真全屏", "窗口独占全屏幕显示", "🪟 窗口与系统"),
    "togglemaximizescreen": ("切换最大化", "在当前工作区内最大化窗口", "🪟 窗口与系统"),
    "togglefakefullscreen": ("切换伪全屏", "窗口伪全屏 (保留外框与控制)", "🪟 窗口与系统"),
    "centerwin": ("居中浮动窗口", "将当前浮动窗口移动至屏幕中央", "🪟 窗口与系统"),
    "zoom": ("主窗口缩放/提权", "提升为主窗口或居中放大展示", "🪟 窗口与系统"),
    "toggleoverlay": ("窗口置顶叠加", "让窗口浮动并常驻在所有图层最顶层", "🪟 窗口与系统"),
    "toggle_all_floating": ("全量浮动切换", "一键在全浮动与全平铺间切换", "🪟 窗口与系统"),
    "reload_config": ("热重载配置", "重新读取并应用 Mango 配置文件", "🪟 窗口与系统"),
    "quit": ("退出桌面会话", "注销并退出当前 Mango 桌面环境", "🪟 窗口与系统"),

    # 外壳与桌面组件 (Noctalia 网关)
    "launcher": ("应用启动器", "呼出 Noctalia 应用程序搜索与启动菜单", "🚀 桌面与应用"),
    "session": ("电源与会话", "呼出锁屏/睡眠/重启/关机菜单", "🚀 桌面与应用"),
    "settings": ("系统设置中心", "打开 Noctalia 与桌面设置中心", "🚀 桌面与应用"),
    "clipboard": ("剪贴板历史", "查看并一键粘贴历史剪贴板内容", "🚀 桌面与应用"),
    "wallpaper-picker": ("壁纸选择器", "打开动态/静态壁纸挑选界面", "🚀 桌面与应用"),
    "wallpaper-random": ("随机切换壁纸", "随机更换桌面背景壁纸", "🚀 桌面与应用"),
    "radial-launcher": ("环形快捷启动器", "呼出 Orbit 轮盘式快速启动器", "🚀 桌面与应用"),
    "translate": ("划词与快速翻译", "打开 Orbit 翻译工具", "🚀 桌面与应用"),
    "nightlight-toggle": ("夜间模式开关", "切换夜间防蓝光色温模式", "🚀 桌面与应用"),

    # 布局与 Scroller 滚动带
    "switch_layout": ("循环切换平铺布局", "在 Scroller / Master / Grid / Dwindle 等布局间切换", "📜 布局与 Scroller"),
    "switch_proportion_preset": ("Scroller 比例切换", "循环切换横向窗口宽度比例预设", "📜 布局与 Scroller"),
    "scroller_stack,left": ("Scroller 向左堆叠", "将当前窗口与左侧窗口合并垂直堆叠", "📜 布局与 Scroller"),
    "scroller_stack,right": ("Scroller 向右堆叠", "将当前窗口与右侧窗口合并垂直堆叠", "📜 布局与 Scroller"),

    # 便签与分组
    "toggle_scratchpad": ("便签切换 (Scratchpad)", "呼出或隐藏临时便签悬浮窗", "📌 便签与分组"),
    "minimized": ("最小化到便签", "将当前窗口隐藏收纳入便签堆栈", "📌 便签与分组"),
    "restore_minimized": ("唤回最小化窗口", "恢复最近隐藏到便签的窗口", "📌 便签与分组"),
    "toggle_special_tag": ("特殊工作区 (Tag 0)", "显示或隐藏特殊的 Scratchpad 工作区", "📌 便签与分组"),
    "tag_special_tag": ("移至特殊工作区", "将当前窗口移入或移出特殊工作区", "📌 便签与分组"),
    "switcher,next": ("Alt-Tab 切换下一窗口", "快速在最近活跃窗口间切换", "📌 便签与分组"),
    "switcher,prev": ("Alt-Tab 切换上一窗口", "快速反向在活跃窗口间切换", "📌 便签与分组"),
    "setkeymode,resize": ("进入窗口大小调节模式", "进入精细 Resize 模式 (用方向键或 HJKL 调整)", "📌 便签与分组"),
}

def format_modifiers(mod_str):
    """将 SUPER+SHIFT 转换为可读性更好的 Super + Shift"""
    replacements = {
        "SUPER": "Super",
        "CTRL": "Ctrl",
        "SHIFT": "Shift",
        "ALT": "Alt",
        "NONE": "",
    }
    tokens = [t.strip() for t in mod_str.split("+") if t.strip()]
    formatted = [replacements.get(t.upper(), t) for t in tokens if replacements.get(t.upper(), t)]
    return " + ".join(formatted)

def parse_config(filepath):
    if not os.path.exists(filepath):
        return []

    entries = []
    has_tag_view = False
    has_tag_move = False

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("bind="):
                parts = [p.strip() for p in line[5:].split(",", 3)]
                if len(parts) < 3:
                    continue
                mods, key, func = parts[0], parts[1], parts[2]
                arg = parts[3] if len(parts) > 3 else ""

                # 整理工作区 1~9 快捷键为简洁的单行显示
                if func == "view" and key.isdigit():
                    if not has_tag_view:
                        entries.append({
                            "key": "Super + 1 ~ 9",
                            "name": "切换工作区",
                            "desc": "直接切换到对应的 Tag 1 ~ 9",
                            "category": "🏷️ 工作区 / Tags",
                            "cmd": ""
                        })
                        entries.append({
                            "key": "Super + Ctrl + 1 ~ 9",
                            "name": "混合多选工作区",
                            "desc": "在屏幕上同时显示多个 Tag 的窗口",
                            "category": "🏷️ 工作区 / Tags",
                            "cmd": ""
                        })
                        has_tag_view = True
                    continue

                if func == "tag" and key.isdigit():
                    if not has_tag_move:
                        entries.append({
                            "key": "Alt + 1 ~ 9",
                            "name": "发送窗口到工作区",
                            "desc": "将当前窗口移动至目标 Tag 1 ~ 9",
                            "category": "🏷️ 工作区 / Tags",
                            "cmd": ""
                        })
                        has_tag_move = True
                    continue

                # 识别方向移动类
                if func == "focusdir":
                    arrow = {"left": "← (左)", "right": "→ (右)", "up": "↑ (上)", "down": "↓ (下)"}.get(arg, arg)
                    entries.append({
                        "key": f"{format_modifiers(mods)} + {key}",
                        "name": f"向 {arrow} 聚焦窗口",
                        "desc": "移动活动焦点到相邻方向的窗口",
                        "category": "🧭 导航与移动",
                        "cmd": f"mmsg dispatch focusdir,{arg}"
                    })
                    continue

                if func == "exchange_client":
                    arrow = {"left": "← (左)", "right": "→ (右)", "up": "↑ (上)", "down": "↓ (下)"}.get(arg, arg)
                    entries.append({
                        "key": f"{format_modifiers(mods)} + {key}",
                        "name": f"与 {arrow} 窗口交换位置",
                        "desc": "将当前窗口与相邻方向的窗口对调位置",
                        "category": "🧭 导航与移动",
                        "cmd": f"mmsg dispatch exchange_client,{arg}"
                    })
                    continue

                if func == "move_client":
                    arrow = {"left": "← (左)", "right": "→ (右)", "up": "↑ (上)", "down": "↓ (下)"}.get(arg, arg)
                    entries.append({
                        "key": f"{format_modifiers(mods)} + {key}",
                        "name": f"向 {arrow} 移动窗口",
                        "desc": "在当前布局中向指定方向平移窗口",
                        "category": "🧭 导航与移动",
                        "cmd": f"mmsg dispatch move_client,{arg}"
                    })
                    continue

                # 查找预设动作映射
                full_fn = f"{func},{arg}".rstrip(",")
                target_key = full_fn
                if "shell-action.sh" in arg:
                    action_name = arg.split()[-1]
                    target_key = action_name

                mod_display = format_modifiers(mods)
                key_combo = f"{mod_display} + {key}" if mod_display else key

                if target_key in PRESET_MAP:
                    name, desc, category = PRESET_MAP[target_key]
                elif full_fn in PRESET_MAP:
                    name, desc, category = PRESET_MAP[full_fn]
                elif func in PRESET_MAP:
                    name, desc, category = PRESET_MAP[func]
                else:
                    name = func
                    desc = arg if arg else func
                    category = "⚙️ 其他快捷键"

                # 构造命令用于回车执行
                cmd = ""
                if func == "spawn":
                    cmd = arg
                elif func == "spawn_shell":
                    cmd = f"bash -c '{arg}'"
                else:
                    cmd = f"mmsg dispatch {full_fn}"

                entries.append({
                    "key": key_combo,
                    "name": name,
                    "desc": desc,
                    "category": category,
                    "cmd": cmd
                })

    return entries

def main():
    if not shutil.which("rofi"):
        subprocess.run([
            "notify-send",
            "-u", "normal",
            "-a", "Nyxuri",
            "快捷键速查",
            "未检测到 rofi 命令，请先安装 rofi 或 rofi-wayland 以使用按键引导\nRofi is not installed. Please install rofi or rofi-wayland."
        ], check=False)
        return

    entries = parse_config(CONFIG_PATH)
    if not entries:
        print("未能在 config.conf 中找到快捷键绑定。")
        return

    # 按分类分组排序
    categories = [
        "🪟 窗口与系统",
        "🚀 桌面与应用",
        "🧭 导航与移动",
        "📜 布局与 Scroller",
        "🏷️ 工作区 / Tags",
        "📌 便签与分组",
        "⚙️ 其他快捷键"
    ]
    
    sorted_entries = []
    for cat in categories:
        cat_items = [e for e in entries if e["category"] == cat]
        sorted_entries.extend(cat_items)

    # 格式化每行显示: [按键]  [功能名称] - 描述
    lines = []
    for e in sorted_entries:
        # 左侧按键固定对齐，中间功能名称，右侧详细说明
        key_part = f"{e['key']:<26}"
        name_part = f"{e['name']:<18}"
        line_text = f"{key_part} │  {name_part} │  {e['desc']}"
        lines.append(line_text)

    input_text = "\n".join(lines)

    # 构造 Rofi 调用
    rofi_cmd = [
        "rofi",
        "-dmenu",
        "-i",
        "-p", "⌨️ 快捷键速查 (按键引导)",
        "-format", "i",
        "-theme-str", """
            window { width: 75%; height: 60%; }
            listview { lines: 15; }
            element-text { font: "JetBrainsMono Nerd Font, Sans 10.5"; }
        """
    ]
    if os.path.exists(ROFI_THEME):
        rofi_cmd.extend(["-theme", ROFI_THEME])

    try:
        proc = subprocess.Popen(rofi_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        stdout, _ = proc.communicate(input=input_text)
        
        if proc.returncode == 0 and stdout.strip().isdigit():
            idx = int(stdout.strip())
            if 0 <= idx < len(sorted_entries):
                chosen = sorted_entries[idx]
                if chosen.get("cmd"):
                    subprocess.Popen(chosen["cmd"], shell=True)
    except Exception as err:
        print(f"执行失败: {err}", file=sys.stderr)

if __name__ == "__main__":
    main()
