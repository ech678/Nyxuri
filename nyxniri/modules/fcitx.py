"""Optional NyxMellow dynamic Fcitx5 skin (Noctalia user template integration)."""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from nyxniri.constants import Colors, FCITX_THEME, PROJECT_NAME, THEME_ENGINE
from nyxniri.core import get_env, log_msg, timed_run
from nyxniri.i18n import msg, text


def _fcitx_paths():
    env = get_env()
    themes_dir = env.home / ".local/share/fcitx5/themes"
    theme_dir = themes_dir / FCITX_THEME
    template_dir = theme_dir / "templates"
    classicui = env.config_dir / "fcitx5" / "conf" / "classicui.conf"
    noctalia_conf = env.config_dir / THEME_ENGINE / f"{THEME_ENGINE}-config.toml"
    state_file = env.state_dir / f"fcitx-{FCITX_THEME}-theme.prev"
    enabled_marker = env.state_dir / f"fcitx-{FCITX_THEME}.enabled"
    source_dir = env.assets_src / "fcitx5" / FCITX_THEME / "templates"
    return themes_dir, theme_dir, template_dir, classicui, noctalia_conf, state_file, enabled_marker, source_dir

def fcitx5_installed() -> bool:
    """Check if fcitx5 binary is in PATH."""
    return shutil.which("fcitx5") is not None

def noctalia_available() -> bool:
    """Check if noctalia CLI is in PATH."""
    return shutil.which(THEME_ENGINE) is not None

def fcitx_enabled() -> bool:
    """Check if user consent marker exists."""
    _, _, _, _, _, _, enabled_marker, _ = _fcitx_paths()
    return enabled_marker.is_file()

def fcitx_status_label() -> str:
    """Return compact status label for menus."""
    if not fcitx5_installed():
        return msg("status_fcitx5_missing")
    if fcitx_enabled():
        return msg("status_enabled")
    return msg("status_disabled")

def fcitx_templates_registered() -> bool:
    """Check if noctalia-config.toml registers any nyxmellow template."""
    _, _, _, _, noctalia_conf, _, _, _ = _fcitx_paths()
    if noctalia_conf.is_file():
        try:
            content = noctalia_conf.read_text(encoding="utf-8", errors="ignore")
            return (
                f"theme.templates.user.{FCITX_THEME}_theme" in content
                or f"theme.templates.user.{FCITX_THEME}_panel" in content
                or f"theme.templates.user.{FCITX_THEME}_highlight" in content
            )
        except Exception:
            pass
    return False

def fcitx_backup_theme_settings() -> None:
    """Save existing Theme and DarkTheme settings before applying NyxMellow."""
    _, _, _, classicui, _, state_file, _, _ = _fcitx_paths()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    if state_file.is_file():
        return

    existed = 0
    t, dt = "", ""
    if classicui.is_file():
        existed = 1
        try:
            content = classicui.read_text(encoding="utf-8", errors="ignore")
            m_t = re.search(r"^Theme=(.*)", content, re.MULTILINE)
            if m_t: t = m_t.group(1).strip()
            m_dt = re.search(r"^DarkTheme=(.*)", content, re.MULTILINE)
            if m_dt: dt = m_dt.group(1).strip()
        except Exception:
            pass

    state_file.write_text(f"Existed={existed}\nTheme={t}\nDarkTheme={dt}\n", encoding="utf-8")

def fcitx_deploy_templates() -> bool:
    """Deploy theme template SVGs and theme.conf into ~/.local/share/fcitx5/themes/nyxmellow/templates/."""
    _, _, template_dir, _, _, _, _, source_dir = _fcitx_paths()
    if not source_dir.is_dir():
        print(msg("log_fcitx_template_missing", str(source_dir)))
        return False

    template_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        shutil.copy2(item, template_dir / item.name)
    print(msg("fcitx_templates_deployed"))
    return True

def _update_ini_file(file_path: Path, section: str, key: str, val: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.is_file():
        file_path.write_text(f"[{section}]\n{key}={val}\n", encoding="utf-8")
        return

    content = file_path.read_text(encoding="utf-8", errors="replace")
    if re.search(rf"^{re.escape(key)}=", content, re.MULTILINE):
        content = re.sub(rf"^{re.escape(key)}=.*", f"{key}={val}", content, flags=re.MULTILINE)
    else:
        if re.search(rf"^\[{re.escape(section)}\]", content, re.MULTILINE):
            content = re.sub(rf"(^\[{re.escape(section)}\].*)", rf"\1\n{key}={val}", content, flags=re.MULTILINE)
        else:
            content += f"\n[{section}]\n{key}={val}\n"
    file_path.write_text(content, encoding="utf-8")

def fcitx_set_theme_conf() -> None:
    """Update Theme & DarkTheme in classicui.conf."""
    _, _, _, classicui, _, _, _, _ = _fcitx_paths()
    fcitx_backup_theme_settings()
    _update_ini_file(classicui, "ClassicUI", "Theme", FCITX_THEME)
    _update_ini_file(classicui, "ClassicUI", "DarkTheme", FCITX_THEME)
    print(msg("fcitx_theme_set", str(classicui)))

def fcitx_configure_quickphrase() -> None:
    """Configure QuickPhrase hotkey in quickphrase.conf."""
    env = get_env()
    qp_conf = env.config_dir / "fcitx5" / "conf" / "quickphrase.conf"
    fcitx_backup_quickphrase()
    _update_ini_file(qp_conf, "Hotkey", "TriggerKey", "Super+semicolon")
    _update_ini_file(qp_conf, "Hotkey", "AlternativeTriggerKey", "")

def fcitx_backup_quickphrase() -> None:
    """Save prior QuickPhrase hotkeys before NyxNiri overrides them.

    Mirrors fcitx_backup_theme_settings: an Existed= flag distinguishes
    'file didn't exist' (uninstall deletes it) from 'existed with other hotkeys'
    (uninstall restores the saved lines). Idempotent.
    """
    env = get_env()
    qp_conf = env.config_dir / "fcitx5" / "conf" / "quickphrase.conf"
    state = env.state_dir / f"fcitx-{FCITX_THEME}-quickphrase.prev"
    state.parent.mkdir(parents=True, exist_ok=True)
    if state.is_file():
        return

    existed = 0
    tk, atk = "", ""
    if qp_conf.is_file():
        existed = 1
        try:
            content = qp_conf.read_text(encoding="utf-8", errors="ignore")
            m_tk = re.search(r"^TriggerKey=(.*)", content, re.MULTILINE)
            if m_tk:
                tk = m_tk.group(1).strip()
            m_atk = re.search(r"^AlternativeTriggerKey=(.*)", content, re.MULTILINE)
            if m_atk:
                atk = m_atk.group(1).strip()
        except Exception:
            pass

    state.write_text(
        f"Existed={existed}\nTriggerKey={tk}\nAlternativeTriggerKey={atk}\n",
        encoding="utf-8",
    )

def fcitx_restart() -> None:
    """Start fcitx5, replacing the running daemon when necessary."""
    if fcitx5_installed():
        res = timed_run(["pgrep", "-x", "fcitx5"], 5, capture_output=True, check=False)
        if res is not None and res.returncode == 0:
            timed_run(["pkill", "-x", "fcitx5"], 5, check=False)
            time.sleep(1)
        subprocess.Popen(["fcitx5", "-d"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(msg("fcitx_restarted"))

def fcitx_configure_trigger_key() -> bool:
    """Auto-configure Ctrl+Space as fcitx5 trigger key on first fcitx install.

    Skips if:
    - fcitx5 config doesn't exist (user hasn't initialised fcitx5 yet)
    - [Hotkey/TriggerKeys] 0= is already set (respect user's existing choice)
    - niri config.kdl already binds Ctrl+space

    Mod+space is intentionally NOT treated as a conflict — nyxniri's own
    Mod+Space is used for switch-preset-column-width, but niri intercepts
    that binding so Ctrl+Space still reaches fcitx5 untouched.

    Returns:
        True if configured, False if skipped/failed (caller should not raise).
    """
    env = get_env()
    config_path = env.config_dir / "fcitx5" / "config"
    niri_config = env.config_dir / "niri" / "config.kdl"

    target = "Ctrl+space"

    if not config_path.is_file():
        log_msg("INFO", "fcitx5 config 不存在，跳过触发键配置（用户尚未首次启动 fcitx5）")
        return False

    # 1. Key-conflict detection: only Ctrl+Space. Mod+Space is niri's
    #    switch-preset-column-width and never reaches fcitx5, so it is no conflict.
    if niri_config.is_file():
        try:
            binds = "\n".join(
                line
                for line in niri_config.read_text(encoding="utf-8", errors="ignore").splitlines()
                if not line.lstrip().startswith("//")
            )
            if re.search(r"\bCtrl\+space\b", binds, re.IGNORECASE):
                log_msg("INFO", "niri config 已绑定 Ctrl+space，跳过 fcitx5 触发键自动配置")
                return False
        except Exception as e:
            log_msg("WARN", f"读取 niri config 失败：{e}")

    # 2. Respect existing user choice
    try:
        content = config_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        log_msg("WARN", f"读取 fcitx5 config 失败：{e}")
        return False

    # Decide against comment-stripped lines; write back to the original text.
    probe = "\n".join(
        line for line in content.splitlines() if not line.lstrip().startswith("#")
    )
    if re.search(r"\[Hotkey/TriggerKeys\][^\[]*?\b\d+=\S+", probe, re.DOTALL):
        log_msg("INFO", "fcitx5 触发键已存在用户配置，跳过自动写入")
        return False

    if "[Hotkey/TriggerKeys]" in probe:
        new_content = re.sub(
            r"(\[Hotkey/TriggerKeys\]\s*\n)",
            rf"\g<1>0={target}\n",
            content,
            count=1,
        )
    else:
        sep = "\n\n" if content and not content.rstrip().endswith("\n") else "\n"
        new_content = content.rstrip() + sep + f"[Hotkey/TriggerKeys]\n0={target}\n"

    try:
        config_path.write_text(new_content, encoding="utf-8")
        log_msg("INFO", f"已自动配置 fcitx5 触发键为 {target}")
        return True
    except OSError as e:
        log_msg("WARN", f"写入 fcitx5 config 失败：{e}")
        return False

def fcitx_trigger_render() -> None:
    """Ask Noctalia daemon to render templates for current palette."""
    if noctalia_available():
        timed_run([THEME_ENGINE, "msg", "config-reload"], 15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        res = timed_run([THEME_ENGINE, "msg", "templates-apply"], 30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if res is not None and res.returncode == 0:
            print(msg("fcitx_render_ok"))
        else:
            print(msg("fcitx_render_pending"))
    else:
        print(msg("fcitx_render_pending"))

def fcitx_register_templates() -> bool:
    """Ensure nyxmellow templates are fully registered in noctalia-config.toml."""
    _, _, _, _, noctalia_conf, _, _, _ = _fcitx_paths()
    if not noctalia_conf.is_file():
        return False

    content = noctalia_conf.read_text(encoding="utf-8", errors="replace")
    env = get_env()
    home = str(env.home)
    expected_theme = f"[theme.templates.user.{FCITX_THEME}_theme]"
    expected_panel = f"[theme.templates.user.{FCITX_THEME}_panel]"
    expected_highlight = f"[theme.templates.user.{FCITX_THEME}_highlight]"

    if expected_theme not in content or expected_panel not in content or expected_highlight not in content:
        lines = content.splitlines()
        clean_lines = []
        skip = False
        prefix = f"[theme.templates.user.{FCITX_THEME}_"
        for line in lines:
            if line.startswith(prefix):
                skip = True
                continue
            if skip and line.startswith("["):
                skip = False
            if not skip:
                clean_lines.append(line)

        template_block = f"""
# NyxMellow 动态 fcitx5 皮肤（mellow 形状 + Material You 自动取色）
# 路径中的 /home/user 为占位符，由 nyxniri.deploy 在部署时替换为实际 $HOME
[theme.templates.user.{FCITX_THEME}_theme]
index = 0
input_path = "{home}/.local/share/fcitx5/themes/{FCITX_THEME}/templates/theme.conf"
output_path = "{home}/.local/share/fcitx5/themes/{FCITX_THEME}/theme.conf"

[theme.templates.user.{FCITX_THEME}_panel]
index = 1
input_path = "{home}/.local/share/fcitx5/themes/{FCITX_THEME}/templates/panel.svg"
output_path = "{home}/.local/share/fcitx5/themes/{FCITX_THEME}/panel.svg"

[theme.templates.user.{FCITX_THEME}_highlight]
index = 2
input_path = "{home}/.local/share/fcitx5/themes/{FCITX_THEME}/templates/highlight.svg"
output_path = "{home}/.local/share/fcitx5/themes/{FCITX_THEME}/highlight.svg"
post_hook = "if pgrep -x fcitx5 >/dev/null 2>&1; then pkill -x fcitx5; sleep 1; fcitx5 -d >/dev/null 2>&1 & fi"
"""
        new_content = "\n".join(clean_lines).rstrip() + "\n" + template_block
        noctalia_conf.write_text(new_content, encoding="utf-8")
        log_msg("INFO", "Registered NyxMellow templates in noctalia-config.toml")
    return True

def fcitx_install() -> bool:
    """Deploy templates, apply configuration, and activate NyxMellow skin."""
    print(msg("fcitx_install_title"))
    if not fcitx_deploy_templates():
        return False

    _, _, _, _, _, _, enabled_marker, _ = _fcitx_paths()
    if fcitx5_installed():
        fcitx_register_templates()
        fcitx_set_theme_conf()
        fcitx_configure_quickphrase()
        fcitx_configure_trigger_key()
        fcitx_trigger_render()
        fcitx_restart()
        enabled_marker.parent.mkdir(parents=True, exist_ok=True)
        enabled_marker.touch()
        log_msg("INFO", "Deployed and activated NyxMellow fcitx5 skin")
        return True
    else:
        print(msg("fcitx_skip_no_fcitx5"))
        return False

def fcitx_status() -> None:
    """Check and display status of fcitx5 and NyxMellow theme."""
    _, theme_dir, _, classicui, noctalia_conf, _, _, _ = _fcitx_paths()
    print(msg("fcitx_status_title"))

    if fcitx5_installed():
        print(msg("doctor_ok", text("fcitx5: 已安装", "fcitx5: installed")))
    else:
        print(msg("doctor_warn", text("fcitx5: 未安装", "fcitx5: not installed")))

    if fcitx_templates_registered():
        print(msg("fcitx_registered", str(noctalia_conf)))
    else:
        print(msg("fcitx_not_registered", str(noctalia_conf)))

    if theme_dir.is_dir():
        print(msg("doctor_ok", text(f"主题目录: {theme_dir}", f"Theme directory: {theme_dir}")))
        if (theme_dir / "theme.conf").is_file() and (theme_dir / "panel.svg").is_file() and (theme_dir / "highlight.svg").is_file():
            print(msg("doctor_ok", text("渲染文件: 已生成并跟随 Noctalia 配色", "Rendered files: present and following Noctalia colors")))
        else:
            print(msg("doctor_warn", text(
                f"渲染文件缺失；请运行 {THEME_ENGINE} msg config-reload 或 nyxniri fcitx install",
                f"Rendered files are missing; run {THEME_ENGINE} msg config-reload or nyxniri fcitx install",
            )))
    else:
        print(msg("doctor_warn", text(f"主题目录缺失: {theme_dir}", f"Theme directory is missing: {theme_dir}")))

    if classicui.is_file():
        try:
            content = classicui.read_text(encoding="utf-8", errors="ignore")
            t = re.search(r"^Theme=(.*)", content, re.MULTILINE)
            dt = re.search(r"^DarkTheme=(.*)", content, re.MULTILINE)
            t_str = t.group(1).strip() if t else ""
            dt_str = dt.group(1).strip() if dt else ""
            print(msg("doctor_ok", f"classicui.conf: Theme={t_str} DarkTheme={dt_str}"))
        except Exception:
            pass
    else:
        print(msg("doctor_warn", text("classicui.conf: 缺失", "classicui.conf: missing")))

def fcitx_uninstall() -> bool:
    """Uninstall NyxMellow skin, unregister templates, and revert classicui settings."""
    _, theme_dir, _, classicui, noctalia_conf, state_file, enabled_marker, _ = _fcitx_paths()
    print(msg("fcitx_uninstall_title"))

    # Unregister from noctalia-config.toml
    if noctalia_conf.is_file() and fcitx_templates_registered():
        lines = noctalia_conf.read_text(encoding="utf-8").splitlines()
        new_lines = []
        skip = False
        prefix = f"[theme.templates.user.{FCITX_THEME}_"
        for line in lines:
            if line.startswith(prefix):
                skip = True
                continue
            if skip and line.startswith("["):
                skip = False
            if not skip:
                new_lines.append(line)
        noctalia_conf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(msg("log_fcitx_template_unregistered", THEME_ENGINE))

    # Remove theme directory
    if theme_dir.is_dir():
        shutil.rmtree(theme_dir, ignore_errors=True)
        print(msg("log_fcitx_theme_dir_removed", str(theme_dir)))

    # Revert classicui.conf
    if state_file.is_file():
        try:
            state_txt = state_file.read_text(encoding="utf-8")
            m_ex = re.search(r"^Existed=(.*)", state_txt, re.MULTILINE)
            m_t = re.search(r"^Theme=(.*)", state_txt, re.MULTILINE)
            m_dt = re.search(r"^DarkTheme=(.*)", state_txt, re.MULTILINE)
            existed = m_ex.group(1).strip() if m_ex else "0"
            t = m_t.group(1).strip() if m_t else ""
            dt = m_dt.group(1).strip() if m_dt else ""

            if existed != "1":
                classicui.unlink(missing_ok=True)
            else:
                if classicui.is_file():
                    content = classicui.read_text(encoding="utf-8")
                    if t: content = re.sub(r"^Theme=.*", f"Theme={t}", content, flags=re.MULTILINE)
                    else: content = re.sub(r"^Theme=.*\n?", "", content, flags=re.MULTILINE)
                    if dt: content = re.sub(r"^DarkTheme=.*", f"DarkTheme={dt}", content, flags=re.MULTILINE)
                    else: content = re.sub(r"^DarkTheme=.*\n?", "", content, flags=re.MULTILINE)
                    classicui.write_text(content, encoding="utf-8")
        except Exception:
            pass
        state_file.unlink(missing_ok=True)

    # Revert quickphrase.conf (same backup/restore mechanism as classicui)
    env = get_env()
    qp_conf = env.config_dir / "fcitx5" / "conf" / "quickphrase.conf"
    qp_state = env.state_dir / f"fcitx-{FCITX_THEME}-quickphrase.prev"
    if qp_state.is_file():
        try:
            qs = qp_state.read_text(encoding="utf-8")
            m_ex = re.search(r"^Existed=(.*)", qs, re.MULTILINE)
            m_tk = re.search(r"^TriggerKey=(.*)", qs, re.MULTILINE)
            m_atk = re.search(r"^AlternativeTriggerKey=(.*)", qs, re.MULTILINE)
            existed = m_ex.group(1).strip() if m_ex else "0"
            tk = m_tk.group(1).strip() if m_tk else ""
            atk = m_atk.group(1).strip() if m_atk else ""
            if existed != "1":
                qp_conf.unlink(missing_ok=True)
            elif qp_conf.is_file():
                content = qp_conf.read_text(encoding="utf-8")
                if tk:
                    content = re.sub(r"^TriggerKey=.*", f"TriggerKey={tk}", content, flags=re.MULTILINE)
                else:
                    content = re.sub(r"^TriggerKey=.*\n?", "", content, flags=re.MULTILINE)
                if atk:
                    content = re.sub(r"^AlternativeTriggerKey=.*", f"AlternativeTriggerKey={atk}", content, flags=re.MULTILINE)
                else:
                    content = re.sub(r"^AlternativeTriggerKey=.*\n?", "", content, flags=re.MULTILINE)
                qp_conf.write_text(content, encoding="utf-8")
        except Exception:
            pass
        qp_state.unlink(missing_ok=True)

    enabled_marker.unlink(missing_ok=True)
    fcitx_restart()
    print(msg("fcitx_uninstall_done"))
    log_msg("INFO", "Uninstalled NyxMellow fcitx5 skin")
    return True
