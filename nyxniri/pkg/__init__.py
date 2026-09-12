"""Shared package commands for the installer and interactive shell."""

import os
import shutil
import subprocess
import sys

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


def aur_helper() -> str | None:
    for name in ("paru", "yay", "shelly"):
        if shutil.which(name) and run([name, "--version"], capture=True, timeout=10).returncode == 0:
            return name
    return None


def preferred_manager() -> str:
    return aur_helper() or "pacman"


def command(action: str, packages=(), *, source: str = "repo", automatic: bool = False,
            manager: str | None = None) -> list[str]:
    """Build backend arguments; no process or filesystem changes occur here."""
    if action not in ("install", "remove", "upgrade") or source not in ("repo", "aur"):
        raise ValueError("Unsupported package operation")
    manager = manager or preferred_manager()
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


def install(packages, *, source="repo", manager=None, automatic=True) -> bool:
    if not packages:
        return True
    try:
        argv = command("install", list(dict.fromkeys(packages)), source=source,
                       manager=manager, automatic=automatic)
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
