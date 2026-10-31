"""Portable template rendering — /home/user → real $HOME, dynamic paths.

Called by deployment and preset switching for each selected app, or by the
test pipeline for all apps. Kept side-effect-light: pure text substitution
on already-deployed config files.

截图目录准备使用单独入口，只由成功落地后的部署阶段调用；单纯渲染不创建目录。
"""

import re
from pathlib import Path
from typing import Optional

from nyxuri.core import MAIN_WM, THEME_ENGINE
from nyxuri.core import get_env, get_pics_dir


def _niri_screenshot_setting(pictures: Path, home: Path) -> str:
    """生成同一条默认截图路径，供模板渲染与部署后目录准备核对。"""
    try:
        prefix = "~/" + str(pictures.relative_to(home))
    except ValueError:
        prefix = str(pictures)
    return f'screenshot-path "{prefix}/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png"'


def prepare_screenshot_directory(only_app: Optional[str] = None, *,
                                 exclude: Optional[set[str]] = None) -> None:
    """部署成功后准备 Niri 默认截图容器，纯渲染、预览与回滚不调用此入口。

    只处理本轮落地的默认路径；个人 carry、软链配置及其他截图设置不在此范围。
    Niri 26.04 的 Portal 路径直接创建文件，不会先创建父目录；提前准备可避免
    首次截图失败。目录和截图属于用户数据，不登记为单元文件，也不在停用时删除。
    mkdir 失败直接传播，调用事务保留 pending，不能把未就绪配置报告为成功。
    """
    if only_app not in (None, MAIN_WM) or "config.kdl" in (exclude or set()):
        return
    env = get_env()
    config = env.config_dir / MAIN_WM / "config.kdl"
    if not config.is_file() or config.is_symlink():
        return
    pictures = get_pics_dir()
    expected = _niri_screenshot_setting(pictures, env.home)
    if expected not in {line.strip() for line in config.read_text(encoding="utf-8").splitlines()}:
        return
    (pictures / "Screenshots").mkdir(parents=True, exist_ok=True)


def _phase_render_templates(only_app: Optional[str] = None, *, exclude: Optional[set[str]] = None) -> None:
    """只渲染本次落地的模板，保留 carry 路径的个人内容。

    exclude 使用单元目标目录内的相对路径；单文件单元使用目标文件名。
    因此用户修改即使含 /home/user，也不会在更新时被再次替换。
    """
    exclude = exclude or set()
    def may_render(path, uid):
        rel = path.relative_to(get_env().config_dir / uid).as_posix()
        return path.is_file() and not path.is_symlink() and rel not in exclude

    env = get_env()
    home = env.home
    config_dir = env.config_dir
    wp_dest = get_pics_dir() / "Wallpapers"

    if only_app in (None, THEME_ENGINE):
        noctalia_conf = config_dir / THEME_ENGINE / f"{THEME_ENGINE}-config.toml"
        if may_render(noctalia_conf, THEME_ENGINE):
            content = noctalia_conf.read_text(encoding="utf-8", errors="replace")
            content = re.sub(r'^directory = ".*"', lambda _m: f'directory = "{wp_dest}"', content, flags=re.MULTILINE)
            content = re.sub(r'^video_directory = ".*"', lambda _m: f'video_directory = "{wp_dest / "video"}"', content, flags=re.MULTILINE)
            content = content.replace("/home/user", str(home))
            noctalia_conf.write_text(content, encoding="utf-8")

    if only_app in (None, MAIN_WM):
        niri_conf = config_dir / MAIN_WM / "config.kdl"
        if may_render(niri_conf, MAIN_WM):
            content = niri_conf.read_text(encoding="utf-8", errors="replace")
            content = content.replace("/home/user", str(home))
            pics_dir = get_pics_dir()
            screenshot_target = _niri_screenshot_setting(pics_dir, home)
            content = re.sub(r'^\s*(//)?\s*screenshot-path\s+.*', lambda _m: screenshot_target, content, flags=re.MULTILINE)
            niri_conf.write_text(content, encoding="utf-8")

    if only_app in (None, "mango"):
        mango_conf = config_dir / "mango" / "config.conf"
        if may_render(mango_conf, "mango"):
            content = mango_conf.read_text(encoding="utf-8", errors="replace")
            content = content.replace("/home/user", str(home))
            mango_conf.write_text(content, encoding="utf-8")

    if only_app in (None, "fish"):
        fish_vars = config_dir / "fish" / "fish_variables"
        if may_render(fish_vars, "fish"):
            content = fish_vars.read_text(encoding="utf-8", errors="replace")
            content = content.replace("/home/user", str(home))
            fish_vars.write_text(content, encoding="utf-8")
