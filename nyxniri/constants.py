"""Global constants, paths, URLs, and color palettes for NyxNiri."""

import os
from pathlib import Path

# --- Project Identity ---
PROJECT_NAME = "NyxNiri"
CLI_CMD = "nyxniri"
MAIN_WM = "niri"
THEME_ENGINE = "noctalia"
GREETER_PKG = "noctalia-greeter"
GREETER_SESSION_BIN = "noctalia-greeter-session"
GREETER_ETC_CFG = Path("/etc/greetd/config.toml")
GREETER_DM_STATE = GREETER_ETC_CFG.parent / "nyxniri-display-manager"
GREETER_POLKIT_RULE = Path(f"/etc/polkit-1/rules.d/50-{GREETER_PKG}.rules")
GREETER_STATE_DIR = Path("/var/lib") / GREETER_PKG
FCITX_THEME = "nyxmellow"

# Carries the update deploy flag across the post-update re-exec, so the
# deploy runs on the freshly pulled code instead of modules already loaded
# into the old process (mixed old/new imports would crash mid-deploy).
PENDING_UPGRADE_ENV = "NYXNIRI_PENDING_UPGRADE"
# Set alongside PENDING_UPGRADE_ENV when the update came from the interactive
# menu: the fresh process returns to the menu after deploying instead of exiting.
PENDING_UPGRADE_MENU_ENV = "NYXNIRI_PENDING_UPGRADE_MENU"

# --- Directory Constants ---
CONFIG_DIR_NAME = "configs"
ASSETS_DIR_NAME = "assets"

# --- Repository & Network Mirrors ---
REPO_URL = "https://github.com/ech678/NyxNiri.git"

if os.environ.get("NYXNIRI_REPO"):
    GIT_MIRROR_REGISTRY = [("Custom", os.environ["NYXNIRI_REPO"])]
else:
    GIT_MIRROR_REGISTRY = [
        ("Official", "https://github.com/ech678/NyxNiri.git"),
        ("gh-proxy.org", "https://gh-proxy.org/https://github.com/ech678/NyxNiri.git"),
    ]

# Single-source override is user-configured, never silently replaced: an
# address that isn't a git remote is refused loudly at the point of cloning.
CUSTOM_REPO_URL = os.environ.get("NYXNIRI_REPO", "")
CUSTOM_REPO_URL_VALID = CUSTOM_REPO_URL.startswith(("https://", "git@", "ssh://"))

RAW_MIRROR_TEMPLATES = [
    ("Official", "https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
    ("jsDelivr-CDN", "https://fastly.jsdelivr.net/gh/{USER_REPO}@{BRANCH}/{FILE_PATH}"),
    ("gh-proxy.org", "https://gh-proxy.org/https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
]

WALLPAPER_MIRRORS = [
    ("Official", "https://github.com/ech678/wallpaper-collection.git"),
    ("gh-proxy.org", "https://gh-proxy.org/https://github.com/ech678/wallpaper-collection.git"),
]

# --- Dependencies ---
CORE_DEPS = [
    MAIN_WM,
    THEME_ENGINE,
    "wlsunset",
    "fish",
    "starship",
    "kitty",
    "fastfetch",
    "eza",
    "mpvpaper",
    "ffmpeg",
    "jq",
    "tmux",
    "inotify-tools",
    "fzf",
    "python-gobject",
    "gtk-layer-shell",
    "ttf-jetbrains-mono",
    "ttf-jetbrains-mono-nerd",
    "noto-fonts-cjk",
]

AUR_DEPS = [
    "mpvpaper",
]

# --- ANSI Styling Palette (NyxNiri Native) ---
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    DARK_GRAY = "\033[90m"

    # Bold Foreground colors
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_PURPLE = "\033[1;35m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_WHITE = "\033[1;37m"

    # Cursor controls
    CURSOR_HIDE = "\033[?25l"
    CURSOR_SHOW = "\033[?25h"
    CLEAR_SCREEN = "\033[H\033[J"
    CLEAR_LINE = "\033[2K\r"
