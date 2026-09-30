"""GTK Material You theme (Noctalia user template integration)."""

import shutil
import subprocess

from nyxuri.constants import THEME_ENGINE
from nyxuri.core import get_env, log_msg, timed_run
from nyxuri.i18n import msg, text
from nyxuri.template_registry import remove_sections, validate, write_atomic

GTK_TEMPLATE_KEYS = ("nyxuri_gtk3", "nyxuri_gtk4")
LEGACY_GTK_TEMPLATE_KEYS = ("nyxniri_gtk3", "nyxniri_gtk4")


def _paths():
    env = get_env()
    noctalia_conf = env.config_dir / THEME_ENGINE / f"{THEME_ENGINE}-config.toml"
    gtk3_css = env.config_dir / "gtk-3.0" / "gtk.css"
    gtk4_css = env.config_dir / "gtk-4.0" / "gtk.css"
    return noctalia_conf, gtk3_css, gtk4_css


def noctalia_available() -> bool:
    """Check if noctalia CLI is in PATH."""
    return shutil.which(THEME_ENGINE) is not None


def gtktheme_registered() -> bool:
    """Check if GTK templates are registered in noctalia-config.toml."""
    noctalia_conf, _, _ = _paths()
    if not noctalia_conf.is_file():
        return False
    try:
        content = noctalia_conf.read_text(encoding="utf-8", errors="ignore")
        return all(f"theme.templates.user.{key}" in content for key in GTK_TEMPLATE_KEYS) or \
               all(f"theme.templates.user.{key}" in content for key in LEGACY_GTK_TEMPLATE_KEYS)
    except Exception:
        return False


def gtktheme_status_label() -> str:
    """Return compact status label for menus."""
    return msg("status_enabled") if gtktheme_registered() else msg("status_not_installed")


def gtktheme_rendered() -> bool:
    """Check if gtk.css files exist and contain rendered M3 colors."""
    _, gtk3_css, gtk4_css = _paths()
    marker = "@define-color accent_bg_color"
    for css in (gtk3_css, gtk4_css):
        if not css.is_file():
            return False
        try:
            if marker not in css.read_text(encoding="utf-8", errors="ignore"):
                return False
        except Exception:
            return False
    return True


def gtktheme_trigger_render() -> None:
    """Ask Noctalia to reload config and render GTK templates immediately."""
    if not noctalia_available():
        print(msg("gtk_render_pending"))
        return

    timed_run(
        [THEME_ENGINE, "msg", "config-reload"], 15,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    res = timed_run(
        [THEME_ENGINE, "msg", "templates-apply"], 30,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if res is not None and res.returncode == 0:
        print(msg("gtk_render_ok"))
    else:
        print(msg("gtk_render_pending"))


def _clean_legacy_overrides() -> None:
    """Remove gtk-dark.css symlinks that import libadwaita.css and override M3 colors."""
    _, gtk3_dir, gtk4_dir = (p.parent for p in _paths())
    for css_dir in (gtk3_dir, gtk4_dir):
        dark_css = css_dir / "gtk-dark.css"
        if dark_css.is_symlink():
            dark_css.unlink()
            log_msg("INFO", f"Removed legacy gtk-dark.css symlink: {dark_css}")


def gtktheme_install() -> bool:
    """Trigger Noctalia to render GTK templates for current palette."""
    print(msg("gtk_install_title"))
    if not gtktheme_registered():
        print(msg("gtk_not_registered"))
        log_msg("WARN", "GTK templates not registered in noctalia-config.toml")
        return False
    _clean_legacy_overrides()
    gtktheme_trigger_render()
    log_msg("INFO", "GTK Material You theme render triggered")
    return True


def gtktheme_status() -> None:
    """Display GTK theme registration and render status."""
    noctalia_conf, gtk3_css, gtk4_css = _paths()
    print(msg("gtk_status_title"))

    if gtktheme_registered():
        print(msg("doctor_ok", text(
            f"模板注册: 已注册 ({noctalia_conf})",
            f"Templates: registered ({noctalia_conf})",
        )))
    else:
        print(msg("doctor_warn", text(
            f"模板注册: 未注册 ({noctalia_conf})",
            f"Templates: not registered ({noctalia_conf})",
        )))

    for label, css in (("GTK3", gtk3_css), ("GTK4", gtk4_css)):
        if css.is_file():
            try:
                content = css.read_text(encoding="utf-8", errors="ignore")
                if "@define-color accent_bg_color" in content:
                    print(msg("doctor_ok", text(
                        f"{label}: 已渲染并跟随壁纸 ({css})",
                        f"{label}: rendered, following wallpaper ({css})",
                    )))
                else:
                    print(msg("doctor_warn", text(
                        f"{label}: 文件存在但缺少 M3 色彩定义 ({css})",
                        f"{label}: file exists but missing M3 color definitions ({css})",
                    )))
            except Exception:
                print(msg("doctor_warn", text(f"{label}: 读取失败", f"{label}: read error")))
        else:
            print(msg("doctor_warn", text(
                f"{label}: 未渲染，运行 nyxuri gtk install 触发",
                f"{label}: not rendered, run nyxuri gtk install",
            )))


def gtktheme_uninstall() -> bool:
    """Remove rendered gtk.css files and unregister templates from toml."""
    noctalia_conf, gtk3_css, gtk4_css = _paths()
    print(msg("gtk_uninstall_title"))

    # Unregister from noctalia-config.toml
    if noctalia_conf.is_file() and gtktheme_registered():
        sections = {f"theme.templates.user.{key}" for key in GTK_TEMPLATE_KEYS} | {
            f"theme.templates.user.{key}" for key in LEGACY_GTK_TEMPLATE_KEYS
        }
        cleaned = remove_sections(noctalia_conf.read_text(encoding="utf-8"), sections)
        validate(cleaned)
        write_atomic(noctalia_conf, cleaned)
        print(msg("gtk_unregistered", THEME_ENGINE))

    # Remove rendered gtk.css files
    for css in (gtk3_css, gtk4_css):
        if css.is_file():
            css.unlink()
            print(msg("gtk_css_removed", str(css)))

    log_msg("INFO", "Uninstalled GTK Material You theme")
    print(msg("gtk_uninstall_done"))
    return True
