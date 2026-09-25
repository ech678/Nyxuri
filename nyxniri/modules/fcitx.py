"""Optional NyxMellow dynamic Fcitx5 skin (Noctalia user template integration)."""

import configparser
import re
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
from nyxniri.template_registry import remove_sections, set_section_key, validate


FCITX_CLASSICUI_RELOAD = [
    "busctl", "--user", "--auto-start=no", "call", "org.fcitx.Fcitx5", "/controller",
    "org.fcitx.Fcitx.Controller1", "ReloadAddonConfig", "s", "classicui",
]
FCITX_CLASSICUI_RELOAD_HOOK = "busctl --user --auto-start=no call org.fcitx.Fcitx5 /controller org.fcitx.Fcitx.Controller1 ReloadAddonConfig s classicui >/dev/null 2>&1 || true"
FCITX_RELOAD_CONFIG = [
    "busctl", "--user", "--auto-start=no", "call", "org.fcitx.Fcitx5", "/controller",
    "org.fcitx.Fcitx.Controller1", "ReloadConfig",
]


def fcitx_reload_all() -> None:
    """Reload all Fcitx5 configurations via D-Bus controller."""
    if shutil.which("busctl"):
        timed_run(FCITX_RELOAD_CONFIG, 5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


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
    from nyxniri.state.ledger import read_ledger
    modules = read_ledger().get("modules", {})
    if isinstance(modules, dict) and "fcitx" in modules:
        return bool(modules["fcitx"])
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
    try:
        parser.read_string(content)
    except configparser.MissingSectionHeaderError:
        parser.read_string("[ClassicUI]\n" + content)
    return parser


def _edit_ini(content, section, changes):
    # Validate before editing; retain comments, ordering and unrelated sections.
    _parse_ini(content)
    lines = content.splitlines(keepends=True)
    section_start = next((i for i, line in enumerate(lines)
                          if configparser.ConfigParser.SECTCRE.match(line.strip())), None)
    if section_start is None:
        pending = dict(changes)
        edited = []
        for line in lines:
            key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith(("#", ";")) else None
            if key in pending:
                value = pending.pop(key)
                edited.append(f"{key}={value}\n")
            else:
                edited.append(line)
        edited.extend(f"{key}={value}\n" for key, value in pending.items() if value is not None)
        return "".join(edited)

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


def _edit_flat_config(content, changes):
    lines = content.splitlines(keepends=True)
    active_section = None
    legacy = []
    sections = []
    for line in lines:
        match = configparser.ConfigParser.SECTCRE.match(line.strip())
        if match:
            active_section = match.group("header")
            if active_section != "ClassicUI":
                sections.append((active_section, [line]))
            continue
        if active_section == "ClassicUI":
            legacy.append(line)
        elif sections:
            sections[-1][1].append(line)
        else:
            legacy.append(line)

    root = legacy
    pending = dict(changes)
    updated = []
    for line in root:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith(("#", ";")) else None
        if key in pending:
            updated.append(f"{key}={pending.pop(key)}\n")
        else:
            updated.append(line)
    updated.extend(f"{key}={value}\n" for key, value in pending.items() if value is not None)
    return "".join(updated + [line for _, group in sections for line in group])


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
    _write_config(classicui, _edit_flat_config(content, {"Theme": FCITX_THEME, "DarkTheme": FCITX_THEME}))
    print(msg("fcitx_theme_set", str(classicui)))



def fcitx_reload() -> None:
    if shutil.which("busctl"):
        res = timed_run(FCITX_CLASSICUI_RELOAD, 5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if res is not None and res.returncode == 0:
            print(msg("fcitx_reloaded"))
            return


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
    highlight_section = f"{FCITX_THEME}_highlight"
    content = set_section_key(
        content, f"theme.templates.user.{highlight_section}", "post_hook", FCITX_CLASSICUI_RELOAD_HOOK,
    )
    content = content.replace(
        "if pgrep -x fcitx5 >/dev/null 2>&1; then pkill -x fcitx5; sleep 1; fcitx5 -d >/dev/null 2>&1 & fi",
        FCITX_CLASSICUI_RELOAD_HOOK,
    ).replace("fcitx5-remote --check -r >/dev/null 2>&1 || true", FCITX_CLASSICUI_RELOAD_HOOK)
    env = get_env()
    home = str(env.home).replace("\\", "\\\\").replace('"', '\\"')
    registered = tomllib.loads(content).get("theme", {}).get("templates", {}).get("user", {})
    if highlight_section in registered and "post_hook" not in registered[highlight_section]:
        content = set_section_key(
            content, f"theme.templates.user.{highlight_section}", "post_hook", FCITX_CLASSICUI_RELOAD_HOOK,
        )
    for index, (suffix, filename) in enumerate((("theme", "theme.conf"), ("panel", "panel.svg"), ("highlight", "highlight.svg"))):
        name = f"{FCITX_THEME}_{suffix}"
        if name in registered:
            continue
        base = f"{home}/.local/share/fcitx5/themes/{FCITX_THEME}"
        content = content.rstrip() + f'\n\n[theme.templates.user.{name}]\nindex = {index}\ninput_path = "{base}/templates/{filename}"\noutput_path = "{base}/{filename}"\n'
        if suffix == "highlight":
            content += f'post_hook = "{FCITX_CLASSICUI_RELOAD_HOOK}"\n'
    if content != original:
        tomllib.loads(content)
        _write_config(noctalia_conf, content)
    return True

def fcitx_preflight_plan(set_default: bool = True) -> list[str]:
    """Return explicit list of actions and filesystem paths affected by skin setup."""
    _, theme_dir, _, classicui, noctalia_conf, _, _, _ = _fcitx_paths()
    plan = [
        f"  [+] {text('素材释放', 'Deploy assets')}: {theme_dir}/templates/",
        f"  [+] {text('模板注册', 'Register templates')}: {noctalia_conf}",
    ]
    if set_default:
        plan.append(f"  [+] {text('设为默认', 'Set as default')}: {classicui} (Theme={FCITX_THEME})")
    else:
        plan.append(f"  [ ] {text('设为默认', 'Set as default')}: {text('跳过 (可通过 nyxniri fcitx activate 激活)', 'Skipped (run nyxniri fcitx activate to apply)')}")
    return plan


@module_action
def fcitx_deploy_assets() -> bool:
    """Deploy skin templates and register Noctalia dynamic rendering without altering classicui.conf."""
    if not fcitx_deploy_templates():
        return False
    if fcitx5_installed():
        if not fcitx_register_templates():
            return False
        fcitx_trigger_render()
        log_msg("INFO", "Deployed NyxMellow fcitx5 skin assets and registered templates")
        return True
    else:
        print(msg("fcitx_skip_no_fcitx5"))
        return True


@module_action
def fcitx_activate() -> bool:
    """Activate NyxMellow skin as default/dark theme in classicui.conf."""
    if not fcitx5_installed():
        print(msg("fcitx_skip_no_fcitx5"))
        return False
    _, _, _, _, _, _, enabled_marker, _ = _fcitx_paths()
    if not fcitx_register_templates():
        return False
    fcitx_set_theme_conf()
    fcitx_trigger_render()
    fcitx_reload()
    enabled_marker.parent.mkdir(parents=True, exist_ok=True)
    enabled_marker.touch()
    from nyxniri.state.ledger import update_ledger
    update_ledger(modules={"fcitx": True})
    log_msg("INFO", "Activated NyxMellow fcitx5 skin as default theme")
    return True


@module_action
def fcitx_install(set_default: bool = True) -> bool:
    """Deploy templates, output pre-flight plan, and conditionally activate NyxMellow skin."""
    print(msg("fcitx_install_title"))
    print(text(":: 变更清单 (Pre-flight Checklist):", ":: Pre-flight Checklist:"))
    for line in fcitx_preflight_plan(set_default=set_default):
        print(line)
    if not fcitx_deploy_assets():
        return False
    if set_default:
        if fcitx5_installed():
            return fcitx_activate()
        else:
            return False
    return True


@module_action
def setup_rime_ice() -> bool:
    """Mount rime_ice schema into user rime dir, precompile, and ensure rime in fcitx5 profile."""
    env = get_env()
    rime_dir = env.home / ".local/share/fcitx5/rime"
    rime_dir.mkdir(parents=True, exist_ok=True)
    custom_yaml = rime_dir / "default.custom.yaml"

    # 1. Mount rime_ice patch in default.custom.yaml
    needs_patch = True
    if custom_yaml.is_file():
        existing_yaml = custom_yaml.read_text(encoding="utf-8")
        if "rime_ice" in existing_yaml:
            needs_patch = False

    if needs_patch:
        patched = False
        if shutil.which("rime_deployer"):
            res = timed_run(["rime_deployer", "--add-schema", "rime_ice"], 15, cwd=str(rime_dir), check=False)
            if res is not None and res.returncode == 0:
                patched = True
        if not patched:
            if custom_yaml.is_file() and custom_yaml.read_text(encoding="utf-8").strip():
                content = custom_yaml.read_text(encoding="utf-8")
                if "patch:" in content and "schema_list:" in content:
                    content = content.replace("schema_list:\n", "schema_list:\n    - schema: rime_ice\n", 1)
                elif "patch:" in content:
                    content = content.rstrip() + "\n  schema_list:\n    - schema: rime_ice\n"
                else:
                    content = content.rstrip() + "\n\npatch:\n  schema_list:\n    - schema: rime_ice\n"
                custom_yaml.write_text(content, encoding="utf-8")
            else:
                custom_yaml.write_text("patch:\n  schema_list:\n    - schema: rime_ice\n", encoding="utf-8")

    # 2. Precompile schema with rime_deployer if available
    shared_data = Path("/usr/share/rime-data")
    if shutil.which("rime_deployer") and shared_data.is_dir():
        build_dir = rime_dir / "build"
        timed_run(["rime_deployer", "--build", str(rime_dir), str(shared_data), str(build_dir)], 45, check=False)
        timed_run(["rime_deployer", "--set-active-schema", "rime_ice"], 15, cwd=str(rime_dir), check=False)
    else:
        user_yaml = rime_dir / "user.yaml"
        if not user_yaml.is_file():
            user_yaml.write_text("var:\n  previously_selected_schema: rime_ice\n", encoding="utf-8")

    # 3. Ensure rime is registered in ~/.config/fcitx5/profile
    profile_path = env.config_dir / "fcitx5/profile"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    if profile_path.is_file():
        profile_content = profile_path.read_text(encoding="utf-8")
    else:
        profile_content = ""

    if "Name=rime" not in profile_content:
        if not profile_content.strip():
            new_profile = (
                "[Groups/0]\n"
                "Name=默认\n"
                "Default Layout=us\n"
                "DefaultIM=keyboard-us\n\n"
                "[Groups/0/Items/0]\n"
                "Name=rime\n"
                "Layout=\n\n"
                "[Groups/0/Items/1]\n"
                "Name=keyboard-us\n"
                "Layout=\n\n"
                "[GroupOrder]\n"
                "0=默认\n"
            )
            _write_config(profile_path, new_profile)
        else:
            existing_indices = [int(m.group(1)) for m in re.finditer(r"\[Groups/0/Items/(\d+)\]", profile_content)]
            next_idx = max(existing_indices) + 1 if existing_indices else 0
            addition = f"[Groups/0/Items/{next_idx}]\nName=rime\nLayout=\n"
            if "[GroupOrder]" in profile_content:
                profile_content = profile_content.replace("[GroupOrder]", addition + "\n[GroupOrder]")
            else:
                profile_content = profile_content.rstrip() + "\n\n" + addition
            _write_config(profile_path, profile_content)

    # 4. Trigger Fcitx5 reload via D-Bus controller
    fcitx_reload_all()
    print(msg("fcitx_rime_setup_ok"))
    log_msg("INFO", "Configured and precompiled Rime Ice schema for Fcitx5")
    return True


fcitx_setup_rime = setup_rime_ice


def fcitx_status() -> None:
    """Check and display status of fcitx5, NyxMellow theme, and Rime configuration."""
    _, theme_dir, _, classicui, noctalia_conf, _, _, _ = _fcitx_paths()
    env = get_env()
    rime_dir = env.home / ".local/share/fcitx5/rime"
    profile_path = env.config_dir / "fcitx5/profile"
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

    # Rime Ice status
    custom_yaml = rime_dir / "default.custom.yaml"
    if custom_yaml.is_file() and "rime_ice" in custom_yaml.read_text(encoding="utf-8"):
        print(msg("doctor_ok", text("Rime: 雾凇拼音已配置 (rime_ice)", "Rime: Rime Ice configured (rime_ice)")))
    else:
        print(msg("doctor_warn", text("Rime: 雾凇拼音未配置", "Rime: Rime Ice not configured")))

    if profile_path.is_file() and "Name=rime" in profile_path.read_text(encoding="utf-8"):
        print(msg("doctor_ok", text("Fcitx5 profile: rime 输入法已激活", "Fcitx5 profile: rime input method active")))
    else:
        print(msg("doctor_warn", text("Fcitx5 profile: rime 输入法未加入", "Fcitx5 profile: rime input method missing")))

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


def _remove_rime_ice_patch(rime_dir: Path) -> None:
    """Remove only the schema selection lines NyxNiri added for Rime Ice."""
    custom = rime_dir / "default.custom.yaml"
    if custom.is_file():
        lines = custom.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if "schema: rime_ice" not in line]
        while kept and not kept[-1].strip():
            kept.pop()
        if kept == ["patch:", "  schema_list:"] or not kept:
            custom.unlink(missing_ok=True)
        elif kept != lines:
            custom.write_text("\n".join(kept) + "\n", encoding="utf-8")

    user = rime_dir / "user.yaml"
    if user.is_file():
        lines = user.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if "previously_selected_schema: rime_ice" not in line]
        while kept and not kept[-1].strip():
            kept.pop()
        if kept:
            user.write_text("\n".join(kept) + "\n", encoding="utf-8")
        else:
            user.unlink(missing_ok=True)


@module_action
def fcitx_uninstall() -> bool:
    """Uninstall NyxMellow skin, unregister templates, and revert classicui settings."""
    _, theme_dir, _, classicui, noctalia_conf, state_file, enabled_marker, _ = _fcitx_paths()
    print(msg("fcitx_uninstall_title"))

    # Unregister from noctalia-config.toml
    if noctalia_conf.is_file() and fcitx_templates_registered():
        owned = {f"theme.templates.user.{FCITX_THEME}_{suffix}" for suffix in ("theme", "panel", "highlight")}
        content = remove_sections(noctalia_conf.read_text(encoding="utf-8"), owned)
        validate(content)
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
    _remove_rime_ice_patch(env.home / ".local/share/fcitx5/rime")
    _restore_settings(
        env.config_dir / "fcitx5/conf/quickphrase.conf",
        env.state_dir / f"fcitx-{FCITX_THEME}-quickphrase.prev",
        "Hotkey", {"TriggerKey": "Super+semicolon", "AlternativeTriggerKey": ""},
    )

    enabled_marker.unlink(missing_ok=True)
    from nyxniri.state.ledger import update_ledger
    update_ledger(modules={"fcitx": False})
    fcitx_reload()
    print(msg("fcitx_uninstall_done"))
    log_msg("INFO", "Uninstalled NyxMellow fcitx5 skin")
    return True
