"""System dependency management, package detection, AUR bootstrap, and optional software installer."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nyxniri.constants import AUR_DEPS, CORE_DEPS
from nyxniri.core import timed_run
from nyxniri.i18n import msg
from nyxniri.deploy.manifest import discover_manifest_apps, discover_optional_apps
from nyxniri.tui import CheckboxEntry, CheckboxList, pad_display, prompt_confirm

_PACMAN_INSTALLED_CACHE: Optional[set] = None
_FC_LIST_CACHE: Optional[str] = None

def _get_pacman_installed() -> set:
    global _PACMAN_INSTALLED_CACHE
    if _PACMAN_INSTALLED_CACHE is not None:
        return _PACMAN_INSTALLED_CACHE
    if not shutil.which("pacman"):
        _PACMAN_INSTALLED_CACHE = set()
        return _PACMAN_INSTALLED_CACHE
    env = {**os.environ, "LC_ALL": "C"}
    # Timeout degrades to an empty set: which()/font probes still run, worst
    # case is re-suggesting a package — never a crash in the deps check.
    res = timed_run(["pacman", "-Qq"], 30, capture_output=True, text=True, check=False, env=env)
    _PACMAN_INSTALLED_CACHE = set(res.stdout.split()) if res is not None and res.returncode == 0 else set()
    return _PACMAN_INSTALLED_CACHE

def _get_fc_list() -> str:
    global _FC_LIST_CACHE
    if _FC_LIST_CACHE is not None:
        return _FC_LIST_CACHE
    if not shutil.which("fc-list"):
        _FC_LIST_CACHE = ""
        return _FC_LIST_CACHE
    env = {**os.environ, "LC_ALL": "C"}
    res = timed_run(["fc-list", ":", "family"], 15, capture_output=True, text=True, check=False, env=env)
    _FC_LIST_CACHE = res.stdout.lower() if res is not None and res.returncode == 0 else ""
    return _FC_LIST_CACHE

def is_dep_installed(cmd: str) -> bool:
    if cmd in _get_pacman_installed():
        return True
    if cmd == "inotify-tools":
        return shutil.which("inotifywait") is not None
    elif cmd == "python-gobject":
        res = timed_run([sys.executable, "-c", "import gi"], 10, capture_output=True, check=False)
        return res is not None and res.returncode == 0
    elif cmd == "gtk-layer-shell":
        res = timed_run([sys.executable, "-c", "import gi; gi.require_version('GtkLayerShell', '0.1')"], 10, capture_output=True, check=False)
        return res is not None and res.returncode == 0
    elif cmd == "ttf-jetbrains-mono":
        return "jetbrains mono" in _get_fc_list()
    elif cmd == "ttf-jetbrains-mono-nerd":
        return bool(re.search(r"jetbrains.*nerd", _get_fc_list(), re.IGNORECASE))
    elif cmd == "noto-fonts-cjk":
        return bool(re.search(r"noto.*cjk", _get_fc_list(), re.IGNORECASE))
    return shutil.which(cmd) is not None

_MISSING_DEPS_CACHE: Optional[List[str]] = None

def check_all_deps() -> Dict[str, bool]:
    return {dep: is_dep_installed(dep) for dep in CORE_DEPS}

def get_missing_deps() -> List[str]:
    global _MISSING_DEPS_CACHE
    if _MISSING_DEPS_CACHE is not None:
        return _MISSING_DEPS_CACHE
    status_map = check_all_deps()
    _MISSING_DEPS_CACHE = [dep for dep, installed in status_map.items() if not installed]
    return _MISSING_DEPS_CACHE

def aur_helper_usable() -> Optional[str]:
    """Return name of a functioning AUR helper (paru or yay) after verifying binary execution."""
    for helper in ("paru", "yay"):
        if shutil.which(helper):
            try:
                res = subprocess.run([helper, "--version"], capture_output=True, check=False)
                if res.returncode == 0:
                    return helper
            except Exception:
                pass
    return None

def get_preferred_pkg_manager() -> List[str]:
    """Resolve preferred package manager (AUR helper if available, otherwise ['sudo', 'pacman'])."""
    helper = aur_helper_usable()
    if helper:
        return [helper]
    return ["sudo", "pacman"]

def ensure_aur_helper() -> Optional[str]:
    """Bootstrap an AUR helper from official repositories only."""
    helper = aur_helper_usable()
    if helper:
        return helper

    if not prompt_confirm("aur_bootstrap_prompt", "y"):
        print(msg("aur_bootstrap_skip"))
        return None

    print(msg("aur_bootstrap_start"))
    if not shutil.which("pacman"):
        print(msg("aur_bootstrap_failed"))
        return None

    # Remove stale paru-bin if conflicting
    env = {**os.environ, "LC_ALL": "C"}
    for stale in ("paru-bin", "paru-bin-debug"):
        res = subprocess.run(["pacman", "-Qq", stale], capture_output=True, check=False, env=env)
        if res.returncode == 0:
            print(msg("aur_bootstrap_cleanup"))
            subprocess.run(["sudo", "pacman", "-Rdd", "--noconfirm", stale], check=False)

    # 1. Try official repo package
    res_si = subprocess.run(["pacman", "-Si", "paru"], capture_output=True, check=False, env=env)
    if res_si.returncode == 0:
        print(msg("aur_bootstrap_repo"))
        subprocess.run(["sudo", "pacman", "-S", "--needed", "--noconfirm", "paru"], check=False)
        helper = aur_helper_usable()
        if helper:
            print(msg("aur_bootstrap_ok"))
            return helper
        # Repo paru installed but not usable — remove the failed install.
        subprocess.run(["sudo", "pacman", "-Rdd", "--noconfirm", "paru"], check=False)

    print(msg("aur_bootstrap_failed"))
    return None

def check_mpvpaper_leak() -> None:
    """Check mpvpaper version for the OpenGL memory leak bug (< 1.9) and offer upgrade."""
    if not shutil.which("pacman"):
        return
    env = {**os.environ, "LC_ALL": "C"}

    # Already on git version?
    res_git = subprocess.run(["pacman", "-Qi", "mpvpaper-git"], capture_output=True, text=True, check=False, env=env)
    if res_git.returncode == 0:
        git_ver = ""
        for line in res_git.stdout.splitlines():
            if line.startswith("Version"):
                git_ver = line.split(":", 1)[1].strip()
                break
        print(msg("mpvpaper_version_ok", f"git ({git_ver or 'unknown'})"))
        return

    if not shutil.which("mpvpaper"):
        return

    print(msg("checking_mpvpaper"))
    res = subprocess.run(["pacman", "-Qi", "mpvpaper"], capture_output=True, text=True, check=False, env=env)
    version = ""
    for line in res.stdout.splitlines():
        if line.startswith("Version"):
            version = line.split(":", 1)[1].strip()
            break
    if not version:
        return

    # Strip epoch and pkgrel: "1:1.8.2-3" → "1.8.2"
    clean_ver = re.sub(r'^[0-9]+:', '', version)
    clean_ver = re.sub(r'-.*$', '', clean_ver)
    clean_ver = re.sub(r'[^0-9.]', '', clean_ver)
    parts = clean_ver.split(".")
    try:
        major = int(parts[0]) if parts and parts[0].isdigit() else 0
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    except ValueError:
        return

    if major > 1 or (major == 1 and minor >= 9):
        print(msg("mpvpaper_version_ok", version))
    else:
        print(msg("mpvpaper_leak_warn", version))
        if prompt_confirm("mpvpaper_upgrade_prompt", "n"):
            mgr = aur_helper_usable()
            if not mgr:
                mgr = ensure_aur_helper()
            if mgr:
                res_inst = subprocess.run([mgr, "-S", "--noconfirm", "mpvpaper-git"], check=False)
                if res_inst.returncode == 0:
                    print(msg("mpvpaper_upgrade_done"))
                else:
                    print(msg("err_mpvpaper_git_failed"))
            else:
                print(msg("mpvpaper_upgrade_skip"))
        else:
            print(msg("mpvpaper_upgrade_skip"))

def install_selected_deps(selected_deps: List[str]) -> bool:
    global _MISSING_DEPS_CACHE, _PACMAN_INSTALLED_CACHE
    if not selected_deps:
        return True

    repo_pkgs = [pkg for pkg in selected_deps if pkg not in AUR_DEPS]
    aur_pkgs = [pkg for pkg in selected_deps if pkg in AUR_DEPS]

    if repo_pkgs:
        pkg_mgr = get_preferred_pkg_manager()
        cmd = [*pkg_mgr, "-S", "--needed", "--noconfirm", *repo_pkgs]
        print(msg("installing_official_packages", " ".join(repo_pkgs)))
        res = subprocess.run(cmd, check=False)
        if res.returncode != 0:
            print(msg("log_official_pkgs_partial_fail"))

    if aur_pkgs:
        helper = ensure_aur_helper()
        if helper:
            cmd = [helper, "-S", "--needed", "--noconfirm", *aur_pkgs]
            print(msg("installing_aur_packages", " ".join(aur_pkgs)))
            res = subprocess.run(cmd, check=False)
            if res.returncode != 0:
                print(msg("log_aur_pkgs_partial_fail"))
        else:
            print(msg("aur_skip", ", ".join(aur_pkgs)))
            print(msg("aur_helper_required"))

    if "mpvpaper" in selected_deps or shutil.which("mpvpaper"):
        check_mpvpaper_leak()

    _MISSING_DEPS_CACHE = None
    _PACMAN_INSTALLED_CACHE = None
    return True

def run_dep_menu_loop() -> None:
    """Open interactive checkbox list for core dependencies."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    status_map = check_all_deps()
    entries = []
    for dep in CORE_DEPS:
        is_inst = status_map[dep]
        status_tag = msg("installed") if is_inst else msg("missing")
        label = f"{pad_display(dep, 24)} {status_tag}"
        entries.append(CheckboxEntry(key=dep, label=label, checked=not is_inst))

    chk = CheckboxList("dep_menu_title", entries, hint_key="dep_menu_hint")
    chosen = chk.run()
    if chosen:
        print(msg("installing_selected"))
        install_selected_deps(chosen)

def install_optional_apps(selected_apps: List[str]) -> None:
    """Install selected optional apps using per-app manifest package mapping."""
    manifests = dict(discover_manifest_apps())
    repo_pkgs: List[str] = []
    aur_pkgs: List[str] = []
    has_fcitx = False
    for app in selected_apps:
        manifest = manifests.get(app)
        if manifest is None:
            continue
        repo_pkgs.extend(manifest.packages_repo)
        aur_pkgs.extend(manifest.packages_aur)
        if app == "fcitx5-rime":
            has_fcitx = True

    if not repo_pkgs and not aur_pkgs:
        print(msg("opt_apps_none_selected"))
        return

    print(msg("installing_selected_apps"))
    pkg_mgr = get_preferred_pkg_manager()

    if repo_pkgs:
        subprocess.run([*pkg_mgr, "-S", "--needed", "--noconfirm", *repo_pkgs], check=False)

    if aur_pkgs:
        helper = aur_helper_usable()
        if not helper:
            helper = ensure_aur_helper()
        if helper:
            subprocess.run([helper, "-S", "--needed", "--noconfirm", *aur_pkgs], check=False)

    if has_fcitx and shutil.which("fcitx5"):
        try:
            from nyxniri.modules.fcitx import fcitx_install
            fcitx_install()
        except Exception:
            pass

    print(msg("opt_apps_install_done"))


def run_optional_apps_menu_loop() -> None:
    """Open interactive checkbox list for recommended applications."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    manifests = dict(discover_manifest_apps())
    entries = []
    for app in discover_optional_apps():
        manifest = manifests.get(app)
        if manifest is None:
            continue
        is_inst = is_dep_installed(manifest.detect)
        status_tag = msg("installed") if is_inst else msg("missing")
        app_label = msg(f"app_{app.replace('-', '_')}")
        label = f"{pad_display(app_label, 32)} {status_tag}"
        entries.append(CheckboxEntry(key=app, label=label, checked=not is_inst))

    chk = CheckboxList("opt_apps_menu_title", entries, hint_key="opt_apps_menu_hint")
    chosen = chk.run()
    if chosen:
        install_optional_apps(chosen)
    else:
        print(msg("opt_apps_none_selected"))
