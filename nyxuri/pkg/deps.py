"""解析当前平台的依赖，统一供安装器、单元事务和应用菜单安装与检查。"""

import re
import shutil
import sys
from types import SimpleNamespace
from typing import Dict, List, Optional

from nyxuri.core import AUR_DEPS, CORE_DEPS, CORE_DEP_PLATFORMS
from nyxuri.core import log_msg
from nyxuri.core import msg
from nyxuri.deploy.manifest import discover_manifest_apps
from nyxuri.pkg.catalog import CatalogEntry, catalog_entries, get_entry
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
from nyxuri.pkg import platform
from nyxuri.pkg.requirements import resolve_requirements


def core_requirements():
    """把会话工具链转换为与单元相同的依赖结构，保留 Arch 打包输入。"""
    return resolve_requirements(SimpleNamespace(
        name="session", packages_repo=[name for name in CORE_DEPS if name not in AUR_DEPS],
        packages_aur=list(AUR_DEPS), packages_flatpak=[], platforms=CORE_DEP_PLATFORMS,
    ))


def is_dep_installed(cmd: str) -> bool:
    return DependencyProbe().installed(cmd)


def check_all_deps() -> Dict[str, bool]:
    """一次查询当前平台的会话依赖；手动资源也显示真实缺失状态。"""
    probe = DependencyProbe()
    requirements = core_requirements()
    names = (*requirements.packages_repo, *requirements.packages_aur, *requirements.manual)
    return {dep: probe.installed(dep) for dep in names}


def get_missing_deps() -> List[str]:
    return [dep for dep, installed in check_all_deps().items() if not installed]


def supply_installed(item, probe=None) -> bool:
    """按完整平台依赖判断应用是否就绪；命令入口不能代替附属资源。"""
    probe = probe or DependencyProbe()
    requirements = resolve_requirements(item)
    if not requirements.supported:
        return False
    names = (*requirements.packages_repo, *requirements.packages_aur, *requirements.manual)
    if not names and not requirements.packages_flatpak:
        return probe.installed(getattr(item, "detect", item.name))
    return all(probe.installed(name) for name in names) and all(
        app in probe.flatpaks for app in requirements.packages_flatpak
    )


def aur_helper_usable() -> Optional[str]:
    return pkg.aur_helper()


def ensure_aur_helper() -> Optional[str]:
    """仅在 Arch 上从已配置的仓库准备 AUR 助手，不运行源码构建。"""
    if platform.current_platform() != "arch":
        print(msg("pkg_aur_unsupported"), file=sys.stderr)
        return None
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
    """读取发行版包版本检查 mpvpaper；Ubuntu 不提供 AUR 升级操作。"""
    if platform.current_platform() != "arch":
        version = platform.native_package_version("mpvpaper")
        if version:
            print(msg("pkg_version", "mpvpaper", version))
        return
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

def unit_package_installer(unit_id: str, missing: List[str]) -> bool:
    """按当前平台声明安装缺失包；未知单元或未声明的名字不能进入包管理器。"""
    try:
        from nyxuri.kernel import registry
        requirements = resolve_requirements(registry.load_unit(unit_id))
    except (KeyError, OSError, ValueError) as error:
        log_msg("WARN", f"Cannot resolve packages for {unit_id}: {error}")
        return False
    if not requirements.supported:
        print(msg("pkg_unit_unsupported", unit_id, requirements.reason), file=sys.stderr)
        return False
    declared = set((*requirements.packages_repo, *requirements.packages_aur,
                    *requirements.packages_flatpak, *requirements.manual))
    if any(name not in declared for name in missing):
        print(msg("pkg_undeclared", ", ".join(name for name in missing if name not in declared)), file=sys.stderr)
        return False
    if requirements.reason:
        print(msg("pkg_source_hint", unit_id, requirements.reason))
    return _install_groups(
        [p for p in missing if p in requirements.packages_repo],
        [p for p in missing if p in requirements.packages_aur],
        [p for p in missing if p in requirements.packages_flatpak],
        [p for p in missing if p in requirements.manual],
    )


def _install_groups(repo, aur, flat, manual=()) -> bool:
    """分渠道安装可获取的依赖，并报告手动资源；任何未解决项都返回失败。

    手动资源不对应包管理器的包名。即使同批普通包能够安装，也不能把仍
    缺少手动资源的单元记为依赖齐全；事务层会在部署前再次检查。
    """
    repo = list(repo)
    probe = DependencyProbe()
    pending_manual = [name for name in manual if not probe.installed(name)]
    if pending_manual:
        print(msg("pkg_manual_missing", ", ".join(pending_manual)), file=sys.stderr)
    if flat:
        repo = repo + ["flatpak"]
    ok = pkg.install(repo) if repo else True
    if aur:
        helper = ensure_aur_helper()
        if not helper:
            print(msg("aur_skip", ", ".join(aur)), file=sys.stderr)
            ok = False
        else:
            ok = pkg.install(aur, source="aur", manager=helper) and ok
    if flat:
        ok = pkg.install_flatpaks(flat) and ok
    return bool(ok and not pending_manual)


def install_selected_deps(selected_deps: List[str]) -> bool:
    """只接受当前平台工具链中的依赖名，避免把 Arch 名字送给 APT。"""
    requirements = core_requirements()
    if not requirements.supported:
        print(msg("distro_unsupported"), file=sys.stderr)
        return False
    declared = set((*requirements.packages_repo, *requirements.packages_aur, *requirements.manual))
    unknown = [name for name in selected_deps if name not in declared]
    if unknown:
        print(msg("pkg_undeclared", ", ".join(unknown)), file=sys.stderr)
        return False
    ok = _install_groups(
        [name for name in selected_deps if name in requirements.packages_repo],
        [name for name in selected_deps if name in requirements.packages_aur], [],
        [name for name in selected_deps if name in requirements.manual],
    )
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
    manual = set(core_requirements().manual)
    for dep in status_map:
        is_inst = status_map[dep]
        status_tag = msg("installed") if is_inst else msg("missing")
        if dep in manual and not is_inst:
            status_tag = msg("pkg_manual_label")
        label = f"{pad_display(dep, 24)} {status_tag}"
        entries.append(CheckboxEntry(key=dep, label=label, checked=not is_inst and dep not in manual))

    chk = CheckboxList("dep_menu_title", entries, hint_key="dep_menu_hint")
    chosen = chk.run()
    if not chosen:
        return True
    print(msg("installing_selected"))
    return bool(install_selected_deps(chosen))

def install_optional_apps(selected_apps: List[str]) -> bool:
    """安装目录应用或可选单元的当前平台依赖，不改变单元启用状态。"""
    repo_pkgs, aur_pkgs, flatpak_ids, manual = [], [], [], []
    supported = True
    manifests = dict(discover_manifest_apps())
    for app in selected_apps:
        item = get_entry(app) or manifests.get(app)
        if item is None:
            print(msg("pkg_undeclared", app), file=sys.stderr)
            supported = False
            continue
        requirements = resolve_requirements(item)
        if not requirements.supported:
            print(msg("pkg_unit_unsupported", app, requirements.reason), file=sys.stderr)
            supported = False
            continue
        if requirements.reason:
            print(msg("pkg_source_hint", app, requirements.reason))
        repo_pkgs.extend(requirements.packages_repo)
        aur_pkgs.extend(requirements.packages_aur)
        flatpak_ids.extend(requirements.packages_flatpak)
        manual.extend(requirements.manual)
    if not repo_pkgs and not aur_pkgs and not flatpak_ids and not manual:
        print(msg("opt_apps_none_selected"))
        return supported
    print(msg("installing_selected_apps"))
    ok = _install_groups(repo_pkgs, aur_pkgs, flatpak_ids, manual) and supported
    print(msg("opt_apps_install_done" if ok else "log_official_pkgs_partial_fail"))
    return ok


def _supply_items() -> List[dict]:
    """The optional software surface: catalog entries + optional real units.

    One shape for both sources so the menu and the installer never special-
    case where a declaration came from."""
    items: List[dict] = []
    for entry in catalog_entries():
        requirements = resolve_requirements(entry)
        items.append({
            "key": entry.name,
            "category": entry.category,
            "repo": requirements.packages_repo,
            "aur": requirements.packages_aur,
            "flat": requirements.packages_flatpak,
            "manual": requirements.manual,
            "supported": requirements.supported,
            "detect": entry.detect,
        })
    manifests = dict(discover_manifest_apps())
    for app, manifest in manifests.items():
        if not manifest.is_optional:
            continue
        requirements = resolve_requirements(manifest)
        items.append({
            "key": app,
            "category": manifest.category,
            "repo": requirements.packages_repo,
            "aur": requirements.packages_aur,
            "flat": requirements.packages_flatpak,
            "manual": requirements.manual,
            "supported": requirements.supported,
            "detect": manifest.detect,
        })
    return items


def run_optional_apps_menu_loop() -> bool:
    """Open the category accordion checklist for recommended applications."""
    if not sys.stdin.isatty():
        print(msg("interactive_terminal_required"), file=sys.stderr)
        return False

    probe = DependencyProbe()
    grouped: Dict[str, List[CategoryAppEntry]] = {}
    for item in _supply_items():
        # 以整个依赖集合判断是否齐全；仅找到入口命令不能证明输入法插件、
        # 字体或 schema 等附属资源已经就绪。
        declared = (*item["repo"], *item["aur"], *item["manual"])
        is_inst = item["supported"] and all(probe.installed(name) for name in declared)
        is_inst = is_inst and all(fid in probe.flatpaks for fid in item["flat"])
        if not declared and not item["flat"]:
            is_inst = item["supported"] and probe.installed(item["detect"])
        source_tag = "Flatpak" if item["flat"] else ""
        if not item["supported"]:
            source_tag = msg("pkg_unsupported_label")
        elif item["manual"]:
            source_tag = msg("pkg_manual_label")
        entry = CategoryAppEntry(
            key=item["key"],
            label=msg(f"app_{item['key'].replace('-', '_')}"),
            checked=False,
            installed=is_inst,
            source_tag=source_tag,
        )
        grouped.setdefault(item["category"] or "other", []).append(entry)

    # Discovery is name-sorted: categories and entries inside each group
    # are both plain alphabetical — zero curated order to maintain.
    cat_order = sorted(grouped)

    cat_groups = [
        CategoryGroup(key=cat, label=msg(f"apps_cat_{cat}"), entries=grouped[cat])
        for cat in cat_order
    ]

    chk = CategoryCheckboxList("opt_apps_menu_title", cat_groups, hint_key="opt_apps_menu_hint")
    chosen = chk.run()
    if chosen:
        return install_optional_apps(chosen)
    else:
        print(msg("opt_apps_none_selected"))
    return True
