"""Pinned Fisher installation with ownership-scoped cleanup."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from nyxniri.core import get_env, log_msg, register_temp_path
from nyxniri.i18n import msg, text
from nyxniri.network import fetch_raw_with_fallback


FISHER_BOOTSTRAP_COMMIT = "791da644d33d392216f6b1a9b5fc1e470db6d7f2"
FISHER_BOOTSTRAP_SHA256 = "0fb6c81ae3003e95b5671766fa6c25c3597066e29965b7772f6c1b007387356d"
FISHER_PLUGINS = (
    f"jorgebucaran/fisher@{FISHER_BOOTSTRAP_COMMIT}",
    "jorgebucaran/autopair.fish@4d1752ff5b39819ab58d7337c69220342e9de0e2",
    "PatrickF1/fzf.fish@6a6136998879dcc1f29a405dfdd6b92c5f229c39",
)
MANAGED_FILES = frozenset((
    "functions/fisher.fish", "completions/fisher.fish",
    "conf.d/autopair.fish", "functions/_autopair_backspace.fish",
    "functions/_autopair_insert_left.fish", "functions/_autopair_insert_right.fish",
    "functions/_autopair_insert_same.fish", "functions/_autopair_tab.fish",
    "conf.d/fzf.fish", "completions/fzf_configure_bindings.fish",
    "functions/_fzf_configure_bindings_help.fish", "functions/_fzf_extract_var_info.fish",
    "functions/_fzf_preview_changed_file.fish", "functions/_fzf_preview_file.fish",
    "functions/_fzf_report_diff_type.fish", "functions/_fzf_report_file_type.fish",
    "functions/_fzf_search_directory.fish", "functions/_fzf_search_git_log.fish",
    "functions/_fzf_search_git_status.fish", "functions/_fzf_search_history.fish",
    "functions/_fzf_search_processes.fish", "functions/_fzf_search_variables.fish",
    "functions/_fzf_wrapper.fish", "functions/fzf_configure_bindings.fish",
))


def _ownership_path() -> Path:
    return get_env().state_dir / "fisher.json"


def _load_ownership() -> dict | None:
    try:
        state = json.loads(_ownership_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict) or not isinstance(state.get("files"), list) or not isinstance(state.get("fisher_preexisting"), bool):
        return None
    if not all(isinstance(path, str) and path in MANAGED_FILES for path in state["files"]):
        return None
    return state


def _write_ownership(state: dict) -> None:
    path = _ownership_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="fisher.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, sort_keys=True)
        Path(name).replace(path)
    finally:
        Path(name).unlink(missing_ok=True)


def _locked_plugins() -> bool:
    plugins_file = get_env().config_dir / "fish" / "fish_plugins"
    try:
        plugins = plugins_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    return plugins == list(FISHER_PLUGINS)


def _managed_files(fish_dir: Path) -> set[str]:
    return {path for path in MANAGED_FILES if (fish_dir / path).is_file() or (fish_dir / path).is_symlink()}


def _record_new_files(state: dict, before: set[str], fish_dir: Path) -> None:
    state["files"] = sorted(set(state["files"]) | (_managed_files(fish_dir) - before))
    _write_ownership(state)


def _install_is_current(state: dict, fish_dir: Path) -> bool:
    return (
        state.get("complete") is True
        and state.get("plugins") == list(FISHER_PLUGINS)
        and set(state["files"]) <= _managed_files(fish_dir)
    )


def fisher_installed() -> bool:
    """True only when NyxNiri has a valid Fisher ownership record."""
    return _load_ownership() is not None


def fisher_status_label() -> str:
    """Compact status label for menus."""
    return msg("status_enabled") if fisher_installed() else msg("status_not_installed")


def fisher_install() -> bool:
    """Install the reviewed, pinned plugins without touching unmanaged ones."""
    if not shutil.which("fish"):
        return False
    fish_dir = get_env().config_dir / "fish"
    state = _load_ownership()
    if state and state["fisher_preexisting"]:
        log_msg("INFO", "Fisher predated NyxNiri ownership; skipped")
        return False
    if not _locked_plugins():
        log_msg("ERROR", "Refused Fisher install: fish_plugins is not the reviewed lockfile")
        return False
    fisher_file = fish_dir / "functions" / "fisher.fish"
    if state is None and (fisher_file.is_file() or fisher_file.is_symlink()):
        log_msg("INFO", "Fisher already exists without NyxNiri ownership; skipped")
        return False
    if state and _install_is_current(state, fish_dir):
        return True
    if state:
        state["complete"] = False
        _write_ownership(state)

    print(msg("log_check_fisher"))
    fd, name = tempfile.mkstemp(suffix=".fish")
    os.close(fd)
    bootstrap = Path(name)
    register_temp_path(bootstrap)
    if not fetch_raw_with_fallback(
        "jorgebucaran/fisher",
        FISHER_BOOTSTRAP_COMMIT,
        "functions/fisher.fish",
        bootstrap,
        FISHER_BOOTSTRAP_SHA256,
    ):
        print(msg("log_fisher_install_skipped"))
        return False

    if state is None:
        state = {
            "complete": False,
            "files": [],
            "fisher_preexisting": False,
        }
        _write_ownership(state)

    before = _managed_files(fish_dir)
    plugins = FISHER_PLUGINS[1:] if state["fisher_preexisting"] else FISHER_PLUGINS
    temp_config = Path(tempfile.mkdtemp(prefix="fisher."))
    register_temp_path(temp_config)
    command = [
        "fish", "-c", "set --global fisher_path $argv[2]; source -- $argv[1]; fisher install $argv[3..-1]",
        "--", str(bootstrap), str(fish_dir), *plugins,
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            timeout=60,
            env={**os.environ, "XDG_CONFIG_HOME": str(temp_config)},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _record_new_files(state, before, fish_dir)
        log_msg("WARN", f"Pinned Fisher install failed: {exc}")
        return False
    _record_new_files(state, before, fish_dir)
    if result.returncode != 0:
        log_msg("WARN", "Pinned Fisher install failed; ownership retained for safe retry")
        return False
    state["plugins"] = list(FISHER_PLUGINS)
    state["complete"] = True
    _write_ownership(state)
    return True


def fisher_uninstall() -> bool:
    """Remove exactly the Fisher files NyxNiri recorded as its own."""
    state = _load_ownership()
    if state is None:
        return False
    fish_dir = get_env().config_dir / "fish"
    for relative in state["files"]:
        path = fish_dir / relative
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
    _ownership_path().unlink(missing_ok=True)
    log_msg("INFO", "Removed NyxNiri-owned Fisher files")
    return True


def fisher_status() -> None:
    """Print Fisher install state."""
    print(msg("fisher_status_title"))
    if fisher_installed():
        print(msg("doctor_ok", text("fisher: 已安装", "fisher: installed")))
    else:
        print(msg("doctor_warn", text("fisher: 未安装", "fisher: not installed")))
