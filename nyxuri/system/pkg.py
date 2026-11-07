"""Package management, dependency detection, and AUR integration."""

import json
import os
import re
import shutil
import subprocess
import sys
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional

from nyxuri.system import backend
from nyxuri.system.env import AUR_DEPS, CORE_DEPS, log_msg, timed_run
from nyxuri.system.i18n import msg
from nyxuri.ui.tui import (
    CheckboxEntry,
    CheckboxList,
    pad_display,
    prompt_confirm,
)

QUERY_TIMEOUT = 30
INSTALL_TIMEOUT = 1800
FLATHUB_REMOTE_URL = "https://dl.flathub.org/repo/flathub.remote"


def run(argv: list[str], *, capture: bool = False, timeout: int = INSTALL_TIMEOUT):
    """Keep external failures and timeouts visible as ordinary exit codes."""
    try:
        options = {"env": {**os.environ, "LC_ALL": "C"}} if capture else {}
        result = subprocess.run(argv, check=False, capture_output=capture, text=True, timeout=timeout, **options)
        if result.returncode >= 0:
            return result
        return subprocess.CompletedProcess(
            result.args, 128 - result.returncode, result.stdout, result.stderr,
        )
    except subprocess.TimeoutExpired:
        result = subprocess.CompletedProcess(argv, 124, "", f"Timed out after {timeout}s: {argv[0]}")
    except OSError as error:
        result = subprocess.CompletedProcess(argv, 127, "", str(error))
    if not capture:
        print(result.stderr, file=sys.stderr)
    return result


def _is_cachyos() -> bool:
    return Path("/etc/cachyos-release").is_file()


def aur_helper() -> str | None:
    candidates = ("shelly", "paru", "yay") if _is_cachyos() else ("paru", "yay", "shelly")
    for name in candidates:
        if shutil.which(name) and run([name, "--version"], capture=True, timeout=10).returncode == 0:
            return name
    return None


def preferred_manager() -> str:
    return aur_helper() or backend.native_manager()


def aur_supported() -> bool:
    return backend.supports_aur()


def privileged(argv: list[str]) -> list[str]:
    if backend.needs_superuser_prefix() and shutil.which("sudo"):
        return ["sudo", *argv]
    return argv


def _dnf_command(action: str, packages, *, automatic: bool) -> list[str]:
    verb = {"install": "install", "remove": "remove", "upgrade": "upgrade"}[action]
    argv = privileged(["dnf", verb])
    if automatic:
        argv.append("-y")
    argv.extend(backend.rename(name) for name in packages)
    return argv


def command(action: str, packages=(), *, source: str = "repo", automatic: bool = False,
            manager: str | None = None) -> list[str]:
    """Build backend arguments; no process or filesystem changes occur here."""
    if isinstance(packages, str):
        packages = [packages]
    if action not in ("install", "remove", "upgrade") or source not in ("repo", "aur"):
        raise ValueError("Unsupported package operation")
    manager = manager or preferred_manager()
    if manager == "dnf":
        if source == "aur":
            raise ValueError("AUR is not available on this distribution")
        return _dnf_command(action, packages, automatic=automatic)
    if manager not in ("paru", "yay", "shelly", "pacman"):
        raise ValueError("Unsupported package manager")
    if source == "aur" and manager == "pacman":
        raise ValueError("AUR requires paru, yay or shelly")
    if manager == "shelly":
        verb = {"install": "install", "remove": "remove", "upgrade": "upgrade"}[action]
        kind = "all" if action == "upgrade" else "aur" if source == "aur" else "standard"
        argv = [manager, verb, kind]
        if automatic:
            argv.append("--no-confirm")
    else:
        argv = ["sudo", "pacman"] if manager == "pacman" else [manager]
        argv.append({"install": "-S", "remove": "-Rns", "upgrade": "-Syu"}[action])
        if action == "install" and automatic:
            argv.append("--needed")
        if automatic:
            argv.append("--noconfirm")
    argv.extend(packages)
    return argv


def _enable_copr(project: str) -> bool:
    print(msg("copr_enabling", project))
    result = run(privileged(["dnf", "-y", "copr", "enable", project]), capture=True)
    if result.returncode != 0:
        print(msg("copr_failed", project), file=sys.stderr)
        return False
    return True


def _rpm_installed(name: str) -> bool:
    if not shutil.which("rpm"):
        return False
    return run(["rpm", "-q", name], capture=True, timeout=QUERY_TIMEOUT).returncode == 0


def _install_fedora(packages) -> bool:
    index = repo_packages()
    wanted: list[str] = []
    channels: list[str] = []
    for name in packages:
        native = backend.rename(name)
        if native in index:
            wanted.append(native)
            continue
        project = backend.copr(name)
        if project:
            wanted.append(native)
            if project not in channels:
                channels.append(project)
            continue
        print(msg("package_absent_here", name), file=sys.stderr)
    for project in channels:
        if not _enable_copr(project):
            return False
    if not wanted:
        return True
    result = run(_dnf_command("install", wanted, automatic=True))
    if result.returncode == 0:
        return True
    absent = [name for name in wanted if not _rpm_installed(name)]
    if absent:
        return False
    print(msg("dnf_scriptlet_ignored"), file=sys.stderr)
    return True


def install(packages, *, source="repo", manager=None, automatic=True) -> bool:
    if isinstance(packages, str):
        packages = [packages]
    if not packages:
        return True
    unique = list(dict.fromkeys(packages))
    if manager is None and backend.family() == backend.FEDORA:
        return _install_fedora(unique)
    try:
        argv = command("install", unique, source=source, manager=manager, automatic=automatic)
    except ValueError:
        return False
    return run(argv).returncode == 0


def install_flatpaks(app_ids) -> bool:
    if not app_ids:
        return True
    if not shutil.which("flatpak"):
        return False
    remote = run(["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", FLATHUB_REMOTE_URL])
    if remote.returncode != 0:
        return False
    return run(["flatpak", "install", "--system", "--noninteractive", "flathub",
                *dict.fromkeys(app_ids)]).returncode == 0


# --- Dependency Detection Probe ---

_REPO_INDEX = None


def repo_packages() -> set:
    """Names the host repository offers; one query per process."""
    global _REPO_INDEX
    if _REPO_INDEX is not None:
        return _REPO_INDEX
    if backend.family() == backend.FEDORA:
        argv = ["dnf", "-q", "repoquery", "--available", "--qf", "%{name}\n"]
    else:
        argv = ["pacman", "-Slq"]
    if not shutil.which(argv[0]):
        return set()
    result = timed_run(argv, 120, capture_output=True, text=True, check=False,
                       env={**os.environ, "LC_ALL": "C"})
    _REPO_INDEX = set(result.stdout.split()) if result is not None and result.returncode == 0 else set()
    return _REPO_INDEX


class DependencyProbe:
    def _query(self, executable, args, timeout):
        if not shutil.which(executable):
            return ""
        result = timed_run([executable, *args], timeout, capture_output=True, text=True,
                           check=False, env={**os.environ, "LC_ALL": "C"})
        return result.stdout if result is not None and result.returncode == 0 else ""

    @cached_property
    def packages(self):
        if backend.family() == backend.FEDORA:
            return set(self._query("rpm", ["-qa", "--qf", "%{NAME}\n"], 30).split())
        return set(self._query("pacman", ["-Qq"], 30).split())

    @cached_property
    def fonts(self):
        return self._query("fc-list", [":", "family"], 15).lower()

    @cached_property
    def flatpaks(self):
        return set(self._query("flatpak", ["list", "--system", "--app", "--columns=application"], 15).split())

    def installed(self, name: str) -> bool:
        if backend.rename(name) in self.packages:
            return True
        if name == "inotify-tools":
            return shutil.which("inotifywait") is not None
        if name in ("python-gobject", "gtk-layer-shell"):
            code = "import gi" if name == "python-gobject" else "import gi; gi.require_version('GtkLayerShell', '0.1')"
            result = timed_run([sys.executable, "-c", code], 10, capture_output=True, check=False)
            return result is not None and result.returncode == 0
        patterns = {"ttf-jetbrains-mono": "jetbrains mono", "ttf-jetbrains-mono-nerd": r"jetbrains.*nerd",
                    "noto-fonts-cjk": r"noto.*cjk"}
        if name in patterns:
            return bool(re.search(patterns[name], self.fonts))
        return shutil.which(name) is not None

    def available(self, name: str) -> bool:
        """Whether this distribution can supply the declared name at all."""
        if backend.family() != backend.FEDORA:
            return True
        return backend.rename(name) in repo_packages()


def is_dep_installed(cmd: str) -> bool:
    return DependencyProbe().installed(cmd)


def check_all_deps() -> Dict[str, bool]:
    probe = DependencyProbe()
    return {dep: probe.installed(dep) for dep in CORE_DEPS}


def get_missing_deps() -> List[str]:
    return [dep for dep, installed in check_all_deps().items() if not installed]


def aur_helper_usable() -> Optional[str]:
    return aur_helper()


def ensure_aur_helper() -> Optional[str]:
    """Bootstrap an AUR helper from official repositories only."""
    helper = aur_helper_usable()
    if helper:
        return helper

    if not aur_supported():
        return None

    if not prompt_confirm("aur_bootstrap_prompt", "y"):
        print(msg("aur_bootstrap_skip"))
        return None

    print(msg("aur_bootstrap_start"))
    if not shutil.which("pacman"):
        print(msg("aur_bootstrap_failed"))
        return None

    is_cachyos = Path("/etc/cachyos-release").is_file()
    candidates = ["shelly", "paru"] if is_cachyos else ["paru"]

    for cand in candidates:
        res = run(["pacman", "-Si", cand], capture=True, timeout=QUERY_TIMEOUT)
        if res.returncode == 0:
            print(msg("aur_bootstrap_repo"))
            if install([cand], manager="pacman"):
                helper = aur_helper_usable()
                if helper:
                    print(msg("aur_bootstrap_ok"))
                    return helper

    print(msg("aur_bootstrap_failed"))
    return None


def check_mpvpaper_leak() -> None:
    """Check mpvpaper version for the OpenGL memory leak bug (< 1.9) and offer upgrade."""
    if not shutil.which("pacman") or not aur_supported():
        return
    res_git = run(["pacman", "-Qi", "mpvpaper-git"], capture=True, timeout=QUERY_TIMEOUT)
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
    res = run(["pacman", "-Qi", "mpvpaper"], capture=True, timeout=QUERY_TIMEOUT)
    version = ""
    for line in res.stdout.splitlines():
        if line.startswith("Version"):
            version = line.split(":", 1)[1].strip()
            break
    if not version:
        return

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
                if install(["mpvpaper-git"], source="aur", manager=mgr):
                    print(msg("mpvpaper_upgrade_done"))
                else:
                    print(msg("err_mpvpaper_git_failed"))
            else:
                print(msg("mpvpaper_upgrade_skip"))
        else:
            print(msg("mpvpaper_upgrade_skip"))


def plugin_package_installer(plugin_id: str, missing: List[str]) -> bool:
    """Installer injected into the engine by every surface (CLI/TUI)."""
    repo = missing
    aur: List[str] = []
    flat: List[str] = []
    try:
        from nyxuri.deploy.catalog import load_plugin
        manifest = load_plugin(plugin_id)
        repo = [p for p in missing if p in manifest.packages_repo]
        aur = [p for p in missing if p in manifest.packages_aur]
        flat = [p for p in missing if p in manifest.packages_flatpak]
    except Exception:
        pass
    if flat:
        repo = repo + ["flatpak"]
    ok = install(repo) if repo else True
    if aur:
        if not aur_supported():
            ok = install(aur, source="aur") and ok
        else:
            helper = ensure_aur_helper()
            if not helper:
                print(msg("aur_skip", ", ".join(aur)), file=sys.stderr)
                return False
            ok = install(aur, source="aur", manager=helper) and ok
    if flat:
        ok = install_flatpaks(flat) and ok
    return bool(ok)


def install_selected_deps(selected_deps: List[str]) -> bool:
    repo_pkgs = [name for name in selected_deps if name not in AUR_DEPS]
    aur_pkgs = [name for name in selected_deps if name in AUR_DEPS]
    ok = install(repo_pkgs)
    if aur_pkgs:
        if not aur_supported():
            ok = install(aur_pkgs, source="aur") and ok
        else:
            helper = ensure_aur_helper()
            if helper:
                ok = install(aur_pkgs, source="aur", manager=helper) and ok
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


# --- CLI / FZF Search Adapter ---

def _print_result(result) -> int:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode


def _group_operands(operands, available):
    groups = {"repo": [], "aur": []}
    for operand in operands:
        if operand.startswith(("aur/", "repo/")):
            source, name = operand.split("/", 1)
        else:
            name = operand
            source = "repo" if name in available else "aur"
        if not name or name.startswith("-"):
            return None
        groups[source].append(name)
    return groups


def _run_groups(action, groups, manager) -> int:
    for source, packages in groups.items():
        if not packages:
            continue
        try:
            argv = command(action, packages, source=source, manager=manager)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        result = run(argv)
        if result.returncode:
            return result.returncode
    return 0


def _fedora_search(keyword: str, source: str) -> int:
    if source == "aur":
        print(msg("aur_unavailable_here"), file=sys.stderr)
        return 1
    names = sorted(name for name in repo_packages() if keyword.casefold() in name.casefold())
    for name in names:
        print(f"[RPM] {name}")
    return 0


def _fedora_installed(operands) -> int:
    result = run(["rpm", "-qa", "--qf", "%{NAME}\n"], capture=True, timeout=QUERY_TIMEOUT)
    if result.returncode == 0 and operands:
        result.stdout = "".join(name + "\n" for name in result.stdout.splitlines()
                                if all(word.casefold() in name.casefold() for word in operands))
    return _print_result(result)


def _fedora_main(action: str, operands) -> int:
    if action == "search":
        return search(" ".join(operands))
    if action == "installed":
        return _fedora_installed(operands)
    if action == "info":
        if len(operands) != 1 or operands[0].startswith("-"):
            return 2
        return _print_result(run(["dnf", "info", "--", operands[0]], capture=True, timeout=QUERY_TIMEOUT))
    if action in ("install", "remove") and (not operands or any(p.startswith("-") for p in operands)):
        return 2
    names = [operand.split("/", 1)[1] if operand.startswith(("aur/", "repo/")) else operand
             for operand in operands]
    if not all(names):
        return 2
    if action == "install":
        return 0 if install(names) else 1
    return run(command(action, list(dict.fromkeys(names)), manager="dnf")).returncode


def search(query: str) -> int:
    parts = query.strip().split(maxsplit=1)
    source = parts[0] if parts and parts[0] in ("aur", "pac", "repo") else "repo"
    keyword = (parts[1] if len(parts) > 1 else "") if parts and parts[0] in ("aur", "pac", "repo") else query.strip()
    if backend.family() == backend.FEDORA:
        return _fedora_search(keyword, source)
    if source == "aur":
        if not keyword:
            return 0
        manager = preferred_manager()
        if manager == "pacman":
            print("AUR search requires paru, yay or shelly", file=sys.stderr)
            return 1
        argv = ([manager, "search", "aur", "--json", "--", keyword] if manager == "shelly"
                else [manager, "-Ssq", "--aur", "--", keyword])
        result = run(argv, capture=True, timeout=QUERY_TIMEOUT)
        if result.returncode:
            return _print_result(result)
        if manager == "shelly":
            try:
                data = json.loads(result.stdout)
                if not isinstance(data, list):
                    raise ValueError("Expected an array")
                entries = data
                names = [entry["Name"] for entry in entries]
                if not all(isinstance(name, str) and name and not any(c.isspace() for c in name) for name in names):
                    raise ValueError("Invalid package name")
            except (ValueError, KeyError, TypeError):
                print("Invalid package search response from Shelly", file=sys.stderr)
                return 1
        else:
            names = result.stdout.splitlines()
        tag = "AUR"
    else:
        result = run(["pacman", "-Slq"], capture=True, timeout=QUERY_TIMEOUT)
        if result.returncode:
            return _print_result(result)
        names = [name for name in result.stdout.splitlines() if keyword.casefold() in name.casefold()]
        tag = "PAC"
    for name in dict.fromkeys(names):
        print(f"[{tag}] {name}")
    return 0


def main(args: list[str]) -> int:
    if not args or args[0] not in ("install", "upgrade", "remove", "search", "info", "installed"):
        print("pkg: expected install, upgrade, remove, search, info or installed", file=sys.stderr)
        return 2
    action, *operands = args
    if backend.family() == backend.FEDORA:
        return _fedora_main(action, operands)
    if action == "search":
        return search(" ".join(operands))
    if action == "installed":
        result = run(["pacman", "-Qq"], capture=True, timeout=QUERY_TIMEOUT)
        if result.returncode == 0 and operands:
            result.stdout = "".join(name + "\n" for name in result.stdout.splitlines()
                                    if all(word.casefold() in name.casefold() for word in operands))
        return _print_result(result)
    manager = preferred_manager()
    if action == "info":
        if len(operands) != 1 or operands[0].startswith("-"):
            return 2
        name = operands[0]
        local = run(["pacman", "-Si", "--", name], capture=True, timeout=QUERY_TIMEOUT)
        if local.returncode == 0:
            return _print_result(local)
        installed = run(["pacman", "-Qi", "--", name], capture=True, timeout=QUERY_TIMEOUT)
        if installed.returncode == 0:
            return _print_result(installed)
        if manager == "pacman":
            return _print_result(local)
        argv = (["shelly", "search", "aur", "--detail", name] if manager == "shelly"
                else [manager, "-Si", "--", name])
        return _print_result(run(argv, capture=True, timeout=QUERY_TIMEOUT))
    if action in ("install", "remove") and (not operands or any(p.startswith("-") for p in operands)):
        return 2
    if action != "install":
        if action == "remove" and manager == "shelly":
            repo = run(["pacman", "-Slq"], capture=True, timeout=QUERY_TIMEOUT)
            if repo.returncode:
                return _print_result(repo)
            groups = _group_operands(operands, set(repo.stdout.splitlines()))
            if groups is None:
                return 2
            return _run_groups("remove", groups, manager)
        return run(command(action, operands, manager=manager)).returncode

    repo = run(["pacman", "-Slq"], capture=True, timeout=QUERY_TIMEOUT)
    if repo.returncode:
        return _print_result(repo)
    groups = _group_operands(operands, set(repo.stdout.splitlines()))
    if groups is None:
        return 2
    return _run_groups("install", groups, manager)
