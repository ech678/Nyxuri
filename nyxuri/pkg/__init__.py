"""Shared package commands for the installer and interactive shell."""

import os
import re
import shutil
import subprocess
import sys

QUERY_TIMEOUT = 30
INSTALL_TIMEOUT = 1800
FLATHUB_REMOTE_URL = "https://dl.flathub.org/repo/flathub.remote"

_APT_PACKAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+.-]*(?::[A-Za-z0-9][A-Za-z0-9-]*)?")
_APT_INSTALL_PACKAGE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9+.-]*(?::[A-Za-z0-9][A-Za-z0-9-]*)?"
    r"(?:=[A-Za-z0-9.+:~:-]+)?"
)
_ARCH_PACKAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9@._+-]*")


def _validate_package_operands(packages, manager: str, action: str) -> None:
    """在构造命令前拒绝选项和控制字符，并保留 APT 的显式 pin 语法。"""
    pattern = (
        _APT_INSTALL_PACKAGE if action == "install" else _APT_PACKAGE
    ) if manager == "apt" else _ARCH_PACKAGE
    for package in packages:
        if not isinstance(package, str) or pattern.fullmatch(package) is None:
            raise ValueError("Invalid package operand")


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
    from pathlib import Path
    from nyxuri.pkg.platform import current_platform

    return current_platform() == "arch" and Path("/etc/cachyos-release").is_file()


def aur_helper() -> str | None:
    from nyxuri.pkg.platform import current_platform

    if current_platform() != "arch":
        return None
    candidates = ("shelly", "paru", "yay") if _is_cachyos() else ("paru", "yay", "shelly")
    for name in candidates:
        if shutil.which(name) and run([name, "--version"], capture=True, timeout=10).returncode == 0:
            return name
    return None


def preferred_manager() -> str:
    from nyxuri.pkg.platform import current_platform

    platform = current_platform()
    if platform == "ubuntu":
        return "apt"
    if platform == "arch":
        return aur_helper() or "pacman"
    return "unsupported"


def command(action: str, packages=(), *, source: str = "repo", automatic: bool = False,
            manager: str | None = None) -> list[str]:
    """Build backend arguments; no process or filesystem changes occur here."""
    if isinstance(packages, str):
        packages = [packages]
    else:
        try:
            packages = list(packages)
        except TypeError as error:
            raise ValueError("Invalid package operands") from error
    if action not in ("install", "remove", "upgrade") or source not in ("repo", "aur"):
        raise ValueError("Unsupported package operation")
    manager = manager or preferred_manager()
    if manager not in ("paru", "yay", "shelly", "pacman", "apt"):
        raise ValueError("Unsupported package manager")
    _validate_package_operands(packages, manager, action)
    if source == "aur" and manager in ("pacman", "apt"):
        if manager == "apt":
            raise ValueError("AUR packages are unavailable through APT; install them from a supported Ubuntu source")
        raise ValueError("AUR requires paru, yay or shelly")
    if manager == "apt":
        argv = ["sudo", "apt-get", {"install": "install", "remove": "remove", "upgrade": "upgrade"}[action]]
        if automatic:
            argv.append("--yes")
        if action == "upgrade":
            if packages:
                raise ValueError("APT upgrade does not accept package names")
            return argv
        # 移除操作只卸载软件包；删除配置文件必须由用户另行明确执行。
        argv.append("--")
    elif manager == "shelly":
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


def install(packages, *, source="repo", manager=None, automatic=True) -> bool:
    if isinstance(packages, str):
        packages = [packages]
    if not packages:
        return True
    manager = manager or preferred_manager()
    try:
        packages = list(packages)
        _validate_package_operands(packages, manager, "install")
    except (TypeError, ValueError) as error:
        print(str(error) or "Invalid package operand", file=sys.stderr)
        return False
    packages = list(dict.fromkeys(packages))
    if manager == "apt" and source == "repo":
        from nyxuri.pkg.platform import (
            backend_available,
            installed_package_names,
            package_candidate_available,
            package_indexes_available,
        )

        if not backend_available():
            print("APT package backend is unavailable; install was skipped", file=sys.stderr)
            return False
        installed = installed_package_names()
        # 指定版本的请求可能意在降级；即使同名包已安装也要交给 APT 判断。
        packages = [name for name in packages if "=" in name or name not in installed]
        if not packages:
            return True
        if not package_indexes_available():
            print("APT package indexes are unavailable; refresh configured indexes, then retry", file=sys.stderr)
            print("Skipped packages: " + ", ".join(packages), file=sys.stderr)
            return False
        unavailable = [name for name in packages if not package_candidate_available(name)]
        if unavailable:
            print("No candidate was found in the configured APT sources; install was skipped", file=sys.stderr)
            print("Unavailable packages: " + ", ".join(unavailable), file=sys.stderr)
            return False
    try:
        argv = command("install", packages, source=source,
                       manager=manager, automatic=automatic)
    except ValueError as error:
        print(str(error), file=sys.stderr)
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
