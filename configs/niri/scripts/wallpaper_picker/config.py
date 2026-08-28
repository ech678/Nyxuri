"""
NyxNiri Wallpaper Picker Configuration Engine
Multi-source prioritized wallpaper directory resolver and format definitions.
"""

import os
import sys
import subprocess

try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    try:
        import tomli as tomllib
        HAS_TOMLLIB = True
    except ImportError:
        HAS_TOMLLIB = False

# ── File Format Definitions ───────────────────────────────────────────────────
STATIC_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".jxl", ".avif", ".bmp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".gif"}
ALL_SUPPORTED_EXTENSIONS = STATIC_EXTENSIONS | VIDEO_EXTENSIONS

CACHE_DIR = os.path.expanduser("~/.cache/nyxniri/thumbnails")
NOCTALIA_CONFIG_PATH = os.path.expanduser("~/.config/noctalia/noctalia-config.toml")
USER_DIRS_PATH = os.path.expanduser("~/.config/user-dirs.dirs")


def get_xdg_pictures_dir() -> str:
    """Resolve the user's Pictures directory (XDG-aware with multilingual fallback)."""
    try:
        res = subprocess.run(["xdg-user-dir", "PICTURES"], capture_output=True, text=True, timeout=1)
        d = res.stdout.strip()
        if d and d != os.path.expanduser("~") and os.path.isdir(d):
            return d
    except Exception:
        pass

    if os.path.isfile(USER_DIRS_PATH):
        try:
            with open(USER_DIRS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("XDG_PICTURES_DIR="):
                        val = line.split("=", 1)[1].strip('"\'')
                        val = val.replace("$HOME", os.path.expanduser("~"))
                        if os.path.isdir(val):
                            return val
        except Exception:
            pass

    for cand in [
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/图片"),
        os.path.expanduser("~/画像"),
        os.path.expanduser("~/Bilder"),
        os.path.expanduser("~/Images"),
    ]:
        if os.path.isdir(cand):
            return cand

    return os.path.expanduser("~/Pictures")


def get_wallpaper_search_roots() -> list:
    """
    Resolve and deduplicate all candidate wallpaper root directories.
    Prioritizes Noctalia config, XDG get_pics_dir, common paths, and built-in fallbacks.
    """
    candidates = []

    # Priority 1: Noctalia runtime configuration
    if os.path.isfile(NOCTALIA_CONFIG_PATH) and HAS_TOMLLIB:
        try:
            with open(NOCTALIA_CONFIG_PATH, "rb") as f:
                data = tomllib.load(f)
                wp_dir = data.get("wallpaper", {}).get("directory")
                if wp_dir:
                    candidates.append(os.path.expanduser(wp_dir))
                video_dir = data.get("plugin_settings", {}).get("noctalia/mpvpaper", {}).get("video_directory")
                if video_dir:
                    candidates.append(os.path.expanduser(video_dir))
        except Exception as e:
            print(f"Notice: Failed to load Noctalia config: {e}", file=sys.stderr)

    # Priority 2: XDG Pictures directory + Wallpapers
    pics_dir = get_xdg_pictures_dir()
    candidates.append(os.path.join(pics_dir, "Wallpapers"))
    candidates.append(os.path.join(pics_dir, "Wallpapers", "video"))

    # Priority 3: Multilingual standard paths
    candidates.append(os.path.expanduser("~/图片/Wallpapers"))
    candidates.append(os.path.expanduser("~/Pictures/Wallpapers"))
    candidates.append(os.path.expanduser("~/Wallpapers"))

    # Priority 4: Environment variable override
    env_dir = os.environ.get("NYXNIRI_WALLPAPERS_DIR")
    if env_dir:
        candidates.insert(0, os.path.expanduser(env_dir))

    # Priority 5: Built-in local fallbacks
    candidates.append(os.path.expanduser("~/.config/Wallpapers"))
    repo_fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Wallpapers")
    candidates.append(os.path.abspath(repo_fallback))

    resolved_roots = []
    seen_real_paths = set()

    for path in candidates:
        exp_path = os.path.expanduser(os.path.expandvars(path))
        if os.path.isdir(exp_path):
            real_path = os.path.realpath(exp_path)
            if real_path not in seen_real_paths:
                seen_real_paths.add(real_path)
                resolved_roots.append(real_path)

    return resolved_roots
