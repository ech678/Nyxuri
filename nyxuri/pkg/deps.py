"""System dependency management, package detection, AUR bootstrap, and optional software installer."""

import re
import shutil
import sys
from typing import Dict, List, Optional

from nyxuri.core import AUR_DEPS, CORE_DEPS
from nyxuri.core import log_msg
from nyxuri.core import msg
from nyxuri.tui import (
    CheckboxEntry,
    CheckboxList,
    pad_display,
    prompt_confirm,
)

from nyxuri import pkg
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

def plugin_package_installer(plugin_id: str, missing: List[str]) -> bool:
    """Installer injected into the transaction by every surface (CLI/TUI): the
    plugin's own manifest declares the three-way split, this layer owns the
    package-manager calls (AUR via an ensured helper, Flatpak via its own
    channel)."""
    repo = missing
    aur: List[str] = []
    flat: List[str] = []
    try:
        from nyxuri.kernel import registry

        manifest = registry.load_plugin(plugin_id)
        repo = [p for p in missing if p in manifest.packages_repo]
        aur = [p for p in missing if p in manifest.packages_aur]
        flat = [p for p in missing if p in manifest.packages_flatpak]
    except Exception:
        pass  # no manifest context → treat every name as a repo package
    if flat:
        repo = repo + ["flatpak"]
    ok = pkg.install(repo) if repo else True
    if aur:
        helper = ensure_aur_helper()
        if not helper:
            print(msg("aur_skip", ", ".join(aur)), file=sys.stderr)
            return False
        ok = pkg.install(aur, source="aur", manager=helper) and ok
    if flat:
        ok = pkg.install_flatpaks(flat) and ok
    return bool(ok)


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


def run_dep_menu_loop() -> bool:
    """Open interactive checkbox list for core dependencies."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return False

    status_map = check_all_deps()
    entries = []
    for dep in CORE_DEPS:
        is_inst = status_map[dep]
        status_tag = msg("installed") if is_inst else msg("missing")
        label = f"{pad_display(dep, 24)} {status_tag}"
        entries.append(CheckboxEntry(key=dep, label=label, checked=not is_inst))

    chk = CheckboxList("dep_menu_title", entries, hint_key="dep_menu_hint")
    chosen = chk.run()
    if not chosen:
        return True
    print(msg("installing_selected"))
    return bool(install_selected_deps(chosen))
