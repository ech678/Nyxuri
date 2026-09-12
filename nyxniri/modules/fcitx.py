"""Optional NyxMellow dynamic Fcitx5 skin (Noctalia user template integration)."""

import configparser
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

from nyxniri.constants import FCITX_THEME, THEME_ENGINE
from nyxniri.core import get_env, log_msg, timed_run
from nyxniri.i18n import msg, text
from nyxniri.deploy.atomic import atomic_replace_item
from nyxniri.modules.lifecycle import module_action


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
            content = tomllib.loads(noctalia_conf.read_text(encoding="utf-8"))
            registered = content.get("theme", {}).get("templates", {}).get("user", {})
            return any(f"{FCITX_THEME}_{suffix}" in registered for suffix in ("theme", "panel", "highlight"))
        except (OSError, tomllib.TOMLDecodeError):
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
        content = _parse_ini(classicui.read_text(encoding="utf-8"))
        t = content.get("ClassicUI", "Theme", fallback="")
        dt = content.get("ClassicUI", "DarkTheme", fallback="")

    state_file.write_text(f"Existed={existed}\nTheme={t}\nDarkTheme={dt}\n", encoding="utf-8")

def fcitx_deploy_templates() -> bool:
    """Deploy theme template SVGs and theme.conf into ~/.local/share/fcitx5/themes/nyxmellow/templates/."""
    _, _, template_dir, _, _, _, _, source_dir = _fcitx_paths()
    if not source_dir.is_dir():
        print(msg("log_fcitx_template_missing", str(source_dir)))
        return False

    if not atomic_replace_item(source_dir, template_dir):
        return False
    print(msg("fcitx_templates_deployed"))
    return True

def _parse_ini(content):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(content)
    return parser


def _edit_ini(content, section, changes):
    # Validate before editing; retain comments, ordering and unrelated sections.
    _parse_ini(content)
    lines = content.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if (match := configparser.ConfigParser.SECTCRE.match(line.strip()))
                  and match.group("header") == section), None)
    if start is None:
        additions = [f"{key}={value}\n" for key, value in changes.items() if value is not None]
        return content + ("\n" if content and not content.endswith("\n") else "") + (f"[{section}]\n" + "".join(additions) if additions else "")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
    pending = dict(changes)
    edited = []
    for line in lines[start + 1:end]:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith(("#", ";")) else None
        if key in pending:
            value = pending.pop(key)
            if value is not None:
                edited.append(f"{key}={value}\n")
        else:
            edited.append(line)
    if edited and not edited[-1].endswith("\n"):
        edited[-1] += "\n"
    edited.extend(f"{key}={value}\n" for key, value in pending.items() if value is not None)
    return "".join(lines[:start + 1] + edited + lines[end:])


def _write_config(path, content):
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / path.name
        source.write_text(content, encoding="utf-8")
        if path.is_file():
            source.chmod(path.stat().st_mode & 0o777)
        if not atomic_replace_item(source, path):
            raise OSError(f"Could not replace {path}")

def fcitx_set_theme_conf() -> None:
    """Update Theme & DarkTheme in classicui.conf."""
    _, _, _, classicui, _, _, _, _ = _fcitx_paths()
    fcitx_backup_theme_settings()
    content = classicui.read_text(encoding="utf-8") if classicui.is_file() else ""
    _write_config(classicui, _edit_ini(content, "ClassicUI", {"Theme": FCITX_THEME, "DarkTheme": FCITX_THEME}))
    print(msg("fcitx_theme_set", str(classicui)))



def fcitx_reload() -> None:
    """Reload a running daemon without taking ownership of its lifecycle."""
    if not shutil.which("fcitx5-remote"):
        return
    res = timed_run(["fcitx5-remote", "--check", "-r"], 5, capture_output=True, check=False)
    if res is not None and res.returncode == 0:
        print(msg("fcitx_reloaded"))


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

    content = noctalia_conf.read_text(encoding="utf-8")
    tomllib.loads(content)
    original = content
    content = content.replace(
        "if pgrep -x fcitx5 >/dev/null 2>&1; then pkill -x fcitx5; sleep 1; fcitx5 -d >/dev/null 2>&1 & fi",
        "fcitx5-remote --check -r >/dev/null 2>&1 || true",
    )
    env = get_env()
    home = str(env.home).replace("\\", "\\\\").replace('"', '\\"')
    registered = tomllib.loads(content).get("theme", {}).get("templates", {}).get("user", {})
    for index, (suffix, filename) in enumerate((("theme", "theme.conf"), ("panel", "panel.svg"), ("highlight", "highlight.svg"))):
        name = f"{FCITX_THEME}_{suffix}"
        if name in registered:
            continue
        base = f"{home}/.local/share/fcitx5/themes/{FCITX_THEME}"
        content = content.rstrip() + f'\n\n[theme.templates.user.{name}]\nindex = {index}\ninput_path = "{base}/templates/{filename}"\noutput_path = "{base}/{filename}"\n'
        if suffix == "highlight":
            content += 'post_hook = "fcitx5-remote --check -r >/dev/null 2>&1 || true"\n'
    if content != original:
        tomllib.loads(content)
        _write_config(noctalia_conf, content)
    return True

@module_action
def fcitx_install() -> bool:
    """Deploy templates, apply configuration, and activate NyxMellow skin."""
    print(msg("fcitx_install_title"))
    if not fcitx_deploy_templates():
        return False

    _, _, _, _, _, _, enabled_marker, _ = _fcitx_paths()
    if fcitx5_installed():
        if not fcitx_register_templates():
            return False
        fcitx_set_theme_conf()
        fcitx_trigger_render()
        fcitx_reload()
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
            content = _parse_ini(classicui.read_text(encoding="utf-8"))
            t_str = content.get("ClassicUI", "Theme", fallback="")
            dt_str = content.get("ClassicUI", "DarkTheme", fallback="")
            print(msg("doctor_ok", f"classicui.conf: Theme={t_str} DarkTheme={dt_str}"))
        except (OSError, configparser.Error):
            pass
    else:
        print(msg("doctor_warn", text("classicui.conf: 缺失", "classicui.conf: missing")))

def _restore_settings(path, state_file, section, owned):
    if not state_file.is_file():
        return
    state = _parse_ini("[Previous]\n" + state_file.read_text(encoding="utf-8"))["Previous"]
    if path.is_file():
        content = path.read_text(encoding="utf-8")
        parser = _parse_ini(content)
        changes = {key: state.get(key) or None for key, value in owned.items()
                   if parser.get(section, key, fallback=None) == value}
        updated = _edit_ini(content, section, changes)
        remaining = _parse_ini(updated)
        if state.get("Existed") != "1" and not any(dict(remaining[s]) for s in remaining.sections()):
            path.unlink()
        elif updated != content:
            _write_config(path, updated)
    state_file.unlink()


@module_action
def fcitx_uninstall() -> bool:
    """Uninstall NyxMellow skin, unregister templates, and revert classicui settings."""
    _, theme_dir, _, classicui, noctalia_conf, state_file, enabled_marker, _ = _fcitx_paths()
    print(msg("fcitx_uninstall_title"))

    # Unregister from noctalia-config.toml
    if noctalia_conf.is_file() and fcitx_templates_registered():
        lines = noctalia_conf.read_text(encoding="utf-8").splitlines()
        new_lines = []
        skip = False
        owned = {f"[theme.templates.user.{FCITX_THEME}_{suffix}]" for suffix in ("theme", "panel", "highlight")}
        for line in lines:
            if line.split("#", 1)[0].strip() in owned:
                skip = True
                continue
            if skip and line.lstrip().startswith("["):
                skip = False
            if not skip:
                new_lines.append(line)
        content = "\n".join(new_lines) + "\n"
        tomllib.loads(content)
        _write_config(noctalia_conf, content)
        print(msg("log_fcitx_template_unregistered", THEME_ENGINE))

    # Remove only shipped/rendered assets; leave personal files in place.
    for directory in (theme_dir / "templates", theme_dir):
        for name in ("theme.conf", "panel.svg", "highlight.svg"):
            (directory / name).unlink(missing_ok=True)
        try:
            directory.rmdir()
        except OSError:
            pass

    _restore_settings(classicui, state_file, "ClassicUI", {"Theme": FCITX_THEME, "DarkTheme": FCITX_THEME})
    # Older installs managed QuickPhrase. Restore only values still owned by us.
    env = get_env()
    _restore_settings(
        env.config_dir / "fcitx5/conf/quickphrase.conf",
        env.state_dir / f"fcitx-{FCITX_THEME}-quickphrase.prev",
        "Hotkey", {"TriggerKey": "Super+semicolon", "AlternativeTriggerKey": ""},
    )

    enabled_marker.unlink(missing_ok=True)
    fcitx_reload()
    print(msg("fcitx_uninstall_done"))
    log_msg("INFO", "Uninstalled NyxMellow fcitx5 skin")
    return True
