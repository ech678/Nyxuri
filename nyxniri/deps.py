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
from nyxniri.deploy.manifest import (
    discover_manifest_apps,
    discover_optional_apps,
    load_optional_apps,
)
from nyxniri.tui import (
    CategoryAppEntry,
    CategoryCheckboxList,
    CategoryGroup,
    CheckboxEntry,
    CheckboxList,
    pad_display,
    prompt_confirm,
)

_PACMAN_INSTALLED_CACHE: Optional[set] = None
_FLATPAK_LIST_CACHE: Optional[set] = None
_FC_LIST_CACHE: Optional[str] = None
_GI_CACHE: Optional[dict] = None

FLATHUB_REMOTE_URL = "https://dl.flathub.org/repo/flathub.remote"

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

def _get_flatpak_apps() -> set:
    global _FLATPAK_LIST_CACHE
    if _FLATPAK_LIST_CACHE is not None:
        return _FLATPAK_LIST_CACHE
    if not shutil.which("flatpak"):
        _FLATPAK_LIST_CACHE = set()
        return _FLATPAK_LIST_CACHE
    env = {**os.environ, "LC_ALL": "C"}
    res = timed_run(
        ["flatpak", "list", "--system", "--app", "--columns=application"],
        15, capture_output=True, text=True, check=False, env=env,
    )
    _FLATPAK_LIST_CACHE = set(res.stdout.split()) if res is not None and res.returncode == 0 else set()
    return _FLATPAK_LIST_CACHE

def is_flatpak_installed(app_id: str) -> bool:
    return app_id in _get_flatpak_apps()

def _check_gi(version: str) -> bool:
    global _GI_CACHE
    if _GI_CACHE is None:
        _GI_CACHE = {}
    if version in _GI_CACHE:
        return _GI_CACHE[version]
    code = "import gi" if version == "gi" else f"import gi; gi.require_version('{version}', '0.1')"
    res = timed_run([sys.executable, "-c", code], 10, capture_output=True, check=False)
    _GI_CACHE[version] = res is not None and res.returncode == 0
    return _GI_CACHE[version]

def is_dep_installed(cmd: str) -> bool:
    if cmd in _get_pacman_installed():
        return True
    if cmd == "inotify-tools":
        return shutil.which("inotifywait") is not None
    elif cmd == "python-gobject":
        return _check_gi("gi")
    elif cmd == "gtk-layer-shell":
        return _check_gi("GtkLayerShell")
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

_AUR_HELPER_CACHE: Optional[str] = None

def aur_helper_usable() -> Optional[str]:
    global _AUR_HELPER_CACHE
    if _AUR_HELPER_CACHE is not None:
        return _AUR_HELPER_CACHE if _AUR_HELPER_CACHE else None
    for helper in ("paru", "yay"):
        if shutil.which(helper):
            try:
                res = subprocess.run([helper, "--version"], capture_output=True, check=False, timeout=10)
                if res.returncode == 0:
                    _AUR_HELPER_CACHE = helper
                    return helper
            except Exception:
                pass
    _AUR_HELPER_CACHE = ""
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
        # The first probe of this call may have cached "unusable"; the fresh
        # install must be re-detected, not read from the stale cache.
        global _AUR_HELPER_CACHE
        _AUR_HELPER_CACHE = None
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
    _AUR_HELPER_CACHE = None
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
    flatpak_ids: List[str] = []
    has_fcitx = False
    for app in selected_apps:
        manifest = manifests.get(app)
        if manifest is None:
            continue
        repo_pkgs.extend(manifest.packages_repo)
        aur_pkgs.extend(manifest.packages_aur)
        flatpak_ids.extend(manifest.packages_flatpak)
        if app == "fcitx5-rime":
            has_fcitx = True

    if not repo_pkgs and not aur_pkgs and not flatpak_ids:
        print(msg("opt_apps_none_selected"))
        return

    print(msg("installing_selected_apps"))
    pkg_mgr = get_preferred_pkg_manager()

    # Flatpak apps need the flatpak runtime itself; add it to the repo batch.
    if flatpak_ids and "flatpak" not in repo_pkgs:
        repo_pkgs.append("flatpak")

    if repo_pkgs:
        subprocess.run([*pkg_mgr, "-S", "--needed", "--noconfirm", *repo_pkgs], check=False)

    if aur_pkgs:
        helper = aur_helper_usable()
        if not helper:
            helper = ensure_aur_helper()
        if helper:
            subprocess.run([helper, "-S", "--needed", "--noconfirm", *aur_pkgs], check=False)

    if flatpak_ids and shutil.which("flatpak"):
        subprocess.run(["flatpak", "remote-add", "--if-not-exists", "flathub", FLATHUB_REMOTE_URL], check=False)
        print(msg("installing_flatpak_apps", " ".join(flatpak_ids)))
        subprocess.run(["flatpak", "install", "--system", "--noninteractive", *flatpak_ids], check=False)

    if has_fcitx and shutil.which("fcitx5"):
        try:
            from nyxniri.modules.fcitx import fcitx_install
            fcitx_install()
        except Exception:
            pass

    # Fresh detection on the next menu visit: installs just performed must
    # not be masked by the probe caches built before them.
    global _MISSING_DEPS_CACHE, _PACMAN_INSTALLED_CACHE, _FLATPAK_LIST_CACHE
    _MISSING_DEPS_CACHE = None
    _PACMAN_INSTALLED_CACHE = None
    _FLATPAK_LIST_CACHE = None

    print(msg("opt_apps_install_done"))


def run_optional_apps_menu_loop() -> None:
    """Open the category accordion checklist for recommended applications."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    manifests = dict(discover_manifest_apps())
    grouped: Dict[str, List[CategoryAppEntry]] = {}
    order = {name: i for i, name in enumerate(load_optional_apps())}
    for app in discover_optional_apps():
        manifest = manifests.get(app)
        if manifest is None:
            continue
        is_inst = is_dep_installed(manifest.detect)
        if not is_inst and manifest.packages_flatpak:
            is_inst = all(is_flatpak_installed(fid) for fid in manifest.packages_flatpak)
        entry = CategoryAppEntry(
            key=app,
            label=msg(f"app_{app.replace('-', '_')}"),
            checked=False,
            installed=is_inst,
            source_tag="Flatpak" if manifest.packages_flatpak else "",
        )
        grouped.setdefault(manifest.category or "other", []).append(entry)

    # Discovery is name-sorted; restore the toml's registration order for both
    # categories (first appearance) and the apps inside each group.
    cat_order: List[str] = []
    for name in load_optional_apps():
        m = manifests.get(name)
        cat = (m.category if m else "") or "other"
        if cat not in cat_order:
            cat_order.append(cat)
    for cat in grouped:
        if cat not in cat_order:
            cat_order.append(cat)
    for entries in grouped.values():
        entries.sort(key=lambda e: order.get(e.key, len(order)))

    cat_groups = [
        CategoryGroup(key=cat, label=msg(f"apps_cat_{cat}"), entries=grouped[cat])
        for cat in cat_order
    ]

    chk = CategoryCheckboxList("opt_apps_menu_title", cat_groups, hint_key="opt_apps_menu_hint")
    chosen = chk.run()
    if chosen:
        install_optional_apps(chosen)
    else:
        print(msg("opt_apps_none_selected"))
