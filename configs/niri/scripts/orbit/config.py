"""
Orbit Launcher Configuration Engine
Declarative default menu tree, Tier-1 search engines, and multi-source prioritized TOML/JSON loaders.
"""

import os
import sys
import json

try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    try:
        import tomli as tomllib
        HAS_TOMLLIB = True
    except ImportError:
        HAS_TOMLLIB = False

# ── Geometry & Physical Constants ─────────────────────────────────────────────
BASE_ORBIT_RADIUS = 168.0   # Golden ratio orbital radius (+16% breathing space)
DEADZONE_RADIUS = 48.0      # Calibrated deadzone radius (r < 48px: center hub focus)
HYSTERESIS_DEG = 6.0        # Angular hysteresis margin (±6° entry threshold)
FLOAT_SPRING = 16.0         # Radial outward displacement on activation (+16px)

CAPSULE_IDLE_H = 48.0       # Idle capsule height (px)
CAPSULE_ACTIVE_H = 54.0     # Active capsule height (px)

# Config Search Paths (Prioritized)
CONFIG_PATHS = [
    os.path.expanduser("~/.config/niri/orbit-items__custom__.toml"),
    os.path.expanduser("~/.config/niri/scratchpad-items__custom__.toml"),
    os.path.expanduser("~/.config/niri/orbit-items.toml"),
    os.path.expanduser("~/.config/niri/scratchpad-items.toml"),
    os.path.expanduser("~/.config/niri/scratchpad-items.json"),
]

# ── Built-in Declarative Menu Tree ───────────────────────────────────────────
DEFAULT_MENU_TREE = [
    {
        "id": "kitty",
        "name": "Kitty",
        "desc": "Terminal",
        "icon": "󰞷",
        "cmd": "kitty",
        "shortcut": "1",
        "color_key": "secondary",
    },
    {
        "id": "tools",
        "name": "System Tools",
        "desc": "Folder · 3 Tools",
        "icon": "󰘳",
        "shortcut": "2",
        "color_key": "secondary",
        "children": [
            {
                "id": "missioncenter",
                "name": "Mission Center",
                "desc": "System Monitor",
                "icon": "󰓅",
                "cmd": "missioncenter",
                "shortcut": "1",
                "color_key": "secondary",
            },
            {
                "id": "eyecare",
                "name": "Eye Care",
                "desc": "Toggle Warmth",
                "icon": "󰛨",
                "cmd": "~/.config/niri/scripts/toggle-eyecare.sh",
                "shortcut": "2",
                "color_key": "secondary",
            },
            {
                "id": "cache",
                "name": "Clean Cache",
                "desc": "Free Disk Space",
                "icon": "󰃢",
                "cmd": "~/.config/fish/clean-cache.py",
                "shortcut": "3",
                "color_key": "secondary",
            },
        ],
    },
    {
        "id": "websites",
        "name": "Websites",
        "desc": "Folder · 3 Sites",
        "icon": "󰖟",
        "shortcut": "3",
        "color_key": "secondary",
        "children": [
            {
                "id": "zhihu",
                "name": "Zhihu",
                "desc": "知乎 · 发现更大世界",
                "icon": "󰖟",
                "url": "https://www.zhihu.com",
                "shortcut": "1",
                "color_key": "secondary",
            },
            {
                "id": "bilibili",
                "name": "Bilibili",
                "desc": "哔哩哔哩 (゜-゜)つロ",
                "icon": "󰕧",
                "url": "https://www.bilibili.com",
                "shortcut": "2",
                "color_key": "secondary",
            },
            {
                "id": "github",
                "name": "GitHub",
                "desc": "Code Repository",
                "icon": "󰊤",
                "url": "https://github.com",
                "shortcut": "3",
                "color_key": "secondary",
            },
        ],
    },
    {
        "id": "wallpaper",
        "name": "Wallpapers",
        "desc": "Static & Live",
        "icon": "󰸉",
        "cmd": "~/.config/niri/scripts/wallpaper-picker.py",
        "shortcut": "4",
        "color_key": "secondary",
    },
]

# ── Built-in Declarative Tier-1 Search Engine Suite ───────────────────────────
DEFAULT_SEARCH_ENGINES = [
    {
        "id": "bing",
        "name": "Bing",
        "icon": "󰍉",
        "url": "https://www.bing.com/search?q={query}",
    },
    {
        "id": "google",
        "name": "Google",
        "icon": "󰊭",
        "url": "https://www.google.com/search?q={query}",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "icon": "󰈺",
        "url": "https://chat.deepseek.com/?q={query}",
    },
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "icon": "󰚩",
        "url": "https://chatgpt.com/?hints=search&q={query}",
    },
    {
        "id": "claude",
        "name": "Claude",
        "icon": "󰣆",
        "url": "https://claude.ai/new?q={query}",
    },
]


def load_menu_tree() -> list:
    """Load menu tree from prioritized TOML/JSON custom configurations or return default tree."""
    for conf_path in CONFIG_PATHS:
        if not os.path.isfile(conf_path):
            continue

        if conf_path.endswith(".toml") and HAS_TOMLLIB:
            try:
                with open(conf_path, "rb") as f:
                    data = tomllib.load(f)
                    items = data.get("items", [])
                    if isinstance(items, list) and len(items) > 0:
                        return items
            except Exception as e:
                print(f"Error loading menu from {conf_path}: {e}", file=sys.stderr)

        elif conf_path.endswith(".json"):
            try:
                with open(conf_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
                    elif isinstance(data, dict) and "items" in data:
                        return data["items"]
            except Exception as e:
                print(f"Error loading menu from {conf_path}: {e}", file=sys.stderr)

    return DEFAULT_MENU_TREE


def load_search_config() -> tuple:
    """Load search engines suite and metadata from prioritized configuration or return defaults."""
    for conf_path in CONFIG_PATHS:
        if not os.path.isfile(conf_path):
            continue

        if conf_path.endswith(".toml") and HAS_TOMLLIB:
            try:
                with open(conf_path, "rb") as f:
                    data = tomllib.load(f)
                    engines = data.get("search_engines", [])
                    search_meta = data.get("search", {})
                    if isinstance(engines, list) and len(engines) > 0:
                        return engines, search_meta
                    elif isinstance(search_meta, dict) and "engines" in search_meta:
                        return search_meta["engines"], search_meta
            except Exception as e:
                print(f"Error loading search config from {conf_path}: {e}", file=sys.stderr)

        elif conf_path.endswith(".json"):
            try:
                with open(conf_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        engines = data.get("search_engines", [])
                        search_meta = data.get("search", {})
                        if isinstance(engines, list) and len(engines) > 0:
                            return engines, search_meta
            except Exception as e:
                print(f"Error loading search config from {conf_path}: {e}", file=sys.stderr)

    return DEFAULT_SEARCH_ENGINES, {"default_engine": "bing", "placeholder": "Search or ask..."}
