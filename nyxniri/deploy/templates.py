"""Portable template rendering — /home/user → real $HOME, dynamic paths.

Called by deployment and preset switching for each selected app, or by the
test pipeline for all apps. Kept side-effect-light: pure text substitution
on already-deployed config files.
"""

import re
from typing import Optional

from nyxniri.constants import MAIN_WM, THEME_ENGINE
from nyxniri.core import get_env, get_pics_dir


def _phase_render_templates(only_app: Optional[str] = None) -> None:
    """Render portable template paths (/home/user -> real $HOME, dynamic screenshot path).

    When ``only_app`` is set, render only that app's templates (narrow path for
    preset switches — no cross-app side effects). None = render all (full deploy).
    """
    env = get_env()
    home = env.home
    config_dir = env.config_dir
    wp_dest = get_pics_dir() / "Wallpapers"

    if only_app in (None, THEME_ENGINE):
        noctalia_conf = config_dir / THEME_ENGINE / f"{THEME_ENGINE}-config.toml"
        if noctalia_conf.is_file():
            content = noctalia_conf.read_text(encoding="utf-8", errors="replace")
            content = re.sub(r'^directory = ".*"', f'directory = "{wp_dest}"', content, flags=re.MULTILINE)
            content = re.sub(r'^video_directory = ".*"', f'video_directory = "{wp_dest / "video"}"', content, flags=re.MULTILINE)
            content = content.replace("/home/user", str(home))
            noctalia_conf.write_text(content, encoding="utf-8")

    if only_app in (None, MAIN_WM):
        niri_conf = config_dir / MAIN_WM / "config.kdl"
        if niri_conf.is_file():
            content = niri_conf.read_text(encoding="utf-8", errors="replace")
            content = content.replace("/home/user", str(home))
            pics_dir = get_pics_dir()
            if str(pics_dir).startswith(str(home)):
                rel_pics = "~" + str(pics_dir)[len(str(home)):]
            else:
                rel_pics = str(pics_dir)
            screenshot_target = f'screenshot-path "{rel_pics}/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png"'
            content = re.sub(r'^\s*(//)?\s*screenshot-path\s+.*', screenshot_target, content, flags=re.MULTILINE)
            niri_conf.write_text(content, encoding="utf-8")

    if only_app in (None, "fish"):
        fish_vars = config_dir / "fish" / "fish_variables"
        if fish_vars.is_file():
            content = fish_vars.read_text(encoding="utf-8", errors="replace")
            content = content.replace("/home/user", str(home))
            fish_vars.write_text(content, encoding="utf-8")
