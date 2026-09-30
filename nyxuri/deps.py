"""System dependency management, package detection, AUR bootstrap, and optional software installer."""

import re
import shutil
import sys
from typing import Dict, List, Optional

from nyxuri.constants import AUR_DEPS, CORE_DEPS
from nyxuri.core import log_msg
from nyxuri.i18n import msg
from nyxuri.deploy.manifest import (
    discover_manifest_apps,
    discover_optional_apps,
    load_optional_apps,
)
from nyxuri.tui import (
    CategoryAppEntry,
    CategoryCheckboxList,
    CategoryGroup,
    CheckboxEntry,
    CheckboxList,
    pad_display,
    prompt_confirm,
)

from nyxuri import pkg
from nyxuri.pkg import FLATHUB_REMOTE_URL
from nyxuri.pkg.detection import DependencyProbe


def is_dep_installed(cmd: str) -> bool:
    return DependencyProbe().installed(cmd)


def check_all_deps() -> Dict[str, bool]:
    probe = DependencyProbe()
    return {dep: probe.installed(dep) for dep in CORE_DEPS}


def get_missing_deps() -> List[str]:
    return [dep for dep, installed in check_all_deps().items() if not installed]


def aur_helper_usable() -> Optional[str]:
    return pkg.aur_helper()


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

    from pathlib import Path
    is_cachyos = Path("/etc/cachyos-release").is_file()
    candidates = ["shelly", "paru"] if is_cachyos else ["paru"]

    for cand in candidates:
        res = pkg.run(["pacman", "-Si", cand], capture=True, timeout=pkg.QUERY_TIMEOUT)
        if res.returncode == 0:
            print(msg("aur_bootstrap_repo"))
            if pkg.install([cand], manager="pacman"):
                helper = aur_helper_usable()
                if helper:
                    print(msg("aur_bootstrap_ok"))
                    return helper

    print(msg("aur_bootstrap_failed"))
    return None

def check_mpvpaper_leak() -> None:
    """Check mpvpaper version for the OpenGL memory leak bug (< 1.9) and offer upgrade."""
    if not shutil.which("pacman"):
        return
    # Already on git version?
    res_git = pkg.run(["pacman", "-Qi", "mpvpaper-git"], capture=True, timeout=pkg.QUERY_TIMEOUT)
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
    res = pkg.run(["pacman", "-Qi", "mpvpaper"], capture=True, timeout=pkg.QUERY_TIMEOUT)
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
                if pkg.install(["mpvpaper-git"], source="aur", manager=mgr):
                    print(msg("mpvpaper_upgrade_done"))
                else:
                    print(msg("err_mpvpaper_git_failed"))
            else:
                print(msg("mpvpaper_upgrade_skip"))
        else:
            print(msg("mpvpaper_upgrade_skip"))

def install_selected_deps(selected_deps: List[str]) -> bool:
    repo_pkgs = [name for name in selected_deps if name not in AUR_DEPS]
    aur_pkgs = [name for name in selected_deps if name in AUR_DEPS]
    ok = pkg.install(repo_pkgs)
    if aur_pkgs:
        helper = ensure_aur_helper()
        if helper:
            ok = pkg.install(aur_pkgs, source="aur", manager=helper) and ok
        else:
            print(msg("aur_skip", ", ".join(aur_pkgs)))
            ok = False
    if "mpvpaper" in selected_deps:
        check_mpvpaper_leak()
    return ok


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

def install_optional_apps(selected_apps: List[str]) -> bool:
    """Install package declarations; skin activation belongs to its own module."""
    manifests = dict(discover_manifest_apps())
    repo_pkgs, aur_pkgs, flatpak_ids = [], [], []
    for app in selected_apps:
        manifest = manifests.get(app)
        if manifest is None:
            continue
        repo_pkgs.extend(manifest.packages_repo)
        aur_pkgs.extend(manifest.packages_aur)
        flatpak_ids.extend(manifest.packages_flatpak)
    if not repo_pkgs and not aur_pkgs and not flatpak_ids:
        print(msg("opt_apps_none_selected"))
        return True
    print(msg("installing_selected_apps"))
    if flatpak_ids:
        repo_pkgs.append("flatpak")
    ok = pkg.install(repo_pkgs)
    if aur_pkgs:
        helper = ensure_aur_helper()
        ok = bool(helper and pkg.install(aur_pkgs, source="aur", manager=helper)) and ok
    if flatpak_ids:
        ok = pkg.install_flatpaks(flatpak_ids) and ok
    if ok:
        for app in selected_apps:
            manifest = manifests.get(app)
            if manifest and manifest.post_install:
                _run_post_install_hook(manifest.post_install)
    print(msg("opt_apps_install_done" if ok else "log_official_pkgs_partial_fail"))
    return ok


def _run_post_install_hook(hook_spec: str) -> bool:
    """Execute a lifecycle hook declared as 'module:function' (e.g. 'fcitx:setup_rime_ice')."""
    if not hook_spec or ":" not in hook_spec:
        return False
    mod_name, fn_name = hook_spec.split(":", 1)
    try:
        import importlib
        root_pkg = (__package__ or "nyxuri").split(".")[0]
        mod = importlib.import_module(f"{root_pkg}.modules.{mod_name}")
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            return bool(fn())
    except Exception as e:
        log_msg("WARN", f"Module post-install hook '{hook_spec}' failed: {e}")
    return False


def run_optional_apps_menu_loop() -> None:
    """Open the category accordion checklist for recommended applications."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return

    manifests = dict(discover_manifest_apps())
    probe = DependencyProbe()
    grouped: Dict[str, List[CategoryAppEntry]] = {}
    order = {name: i for i, name in enumerate(load_optional_apps())}
    for app in discover_optional_apps():
        manifest = manifests.get(app)
        if manifest is None:
            continue
        is_inst = probe.installed(manifest.detect)
        if not is_inst and manifest.packages_flatpak:
            is_inst = all(fid in probe.flatpaks for fid in manifest.packages_flatpak)
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
