"""Portable template rendering — /home/user → real $HOME, dynamic paths.

Called by deployment and preset switching for each selected app, or by the
test pipeline for all apps. Kept side-effect-light: pure text substitution
on already-deployed config files.
"""

import re
from typing import Optional

from nyxuri.system.compositors import COMPOSITORS, MAIN_WM
from nyxuri.system.env import THEME_ENGINE, get_env, get_pics_dir


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
            content = re.sub(r'^directory = ".*"', lambda _m: f'directory = "{wp_dest}"', content, flags=re.MULTILINE)
            content = re.sub(r'^video_directory = ".*"', lambda _m: f'video_directory = "{wp_dest / "video"}"', content, flags=re.MULTILINE)
            content = content.replace("/home/user", str(home))
            noctalia_conf.write_text(content, encoding="utf-8")

    for comp in COMPOSITORS.values():
        if comp.config_relpath and only_app in (None, comp.id):
            conf_file = config_dir / comp.config_relpath
            if conf_file.is_file():
                content = conf_file.read_text(encoding="utf-8", errors="replace")
                content = content.replace("/home/user", str(home))
                if comp.id == MAIN_WM:
                    pics_dir = get_pics_dir()
                    try:
                        rel_pics = "~/" + str(pics_dir.relative_to(home))
                    except ValueError:
                        rel_pics = str(pics_dir)
                    screenshot_target = f'screenshot-path "{rel_pics}/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png"'
                    content = re.sub(r'^\s*(//)?\s*screenshot-path\s+.*', lambda _m: screenshot_target, content, flags=re.MULTILINE)
                conf_file.write_text(content, encoding="utf-8")

    if only_app in (None, "fish"):
        fish_vars = config_dir / "fish" / "fish_variables"
        if fish_vars.is_file():
            content = fish_vars.read_text(encoding="utf-8", errors="replace")
            content = content.replace("/home/user", str(home))
            fish_vars.write_text(content, encoding="utf-8")
