"""Optional Noctalia Greeter (greetd login) installation and system setup."""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from nyxniri.constants import (
    Colors,
    GREETER_DM_STATE,
    GREETER_ETC_CFG,
    GREETER_PKG,
    GREETER_POLKIT_RULE,
    GREETER_SESSION_BIN,
    GREETER_STATE_DIR,
    MAIN_WM,
    THEME_ENGINE,
)
from nyxniri.core import log_msg, timed_run
from nyxniri.i18n import msg, text

CONFLICT_DMS = ["sddm", "lightdm", "gdm", "ly"]
TRUSTED_EXEC_DIRS = (Path("/usr/bin"), Path("/usr/local/bin"))
UNSAFE_PATH_CHARS = frozenset(chr(code) for code in range(32)) | {chr(127)} | set(" '$;&|<>(){}[]*?!\\\"`")


def _trusted_executable(candidate: Optional[str]) -> Optional[str]:
    """Return a canonical root-owned executable from a non-writable system path."""
    if not candidate or any(char in UNSAFE_PATH_CHARS for char in candidate):
        return None
    try:
        path = Path(candidate).resolve(strict=True)
        file_stat = path.stat()
    except OSError:
        return None
    if path.parent not in TRUSTED_EXEC_DIRS or not stat.S_ISREG(file_stat.st_mode):
        return None
    if file_stat.st_uid != 0 or not file_stat.st_mode & 0o111:
        return None
    parent = path.parent
    while True:
        try:
            parent_stat = parent.stat()
        except OSError:
            return None
        if parent_stat.st_uid != 0 or parent_stat.st_mode & 0o022:
            return None
        if parent == parent.parent:
            return str(path)
        parent = parent.parent


def _greeter_session_path() -> Optional[str]:
    return _trusted_executable(shutil.which(GREETER_SESSION_BIN) or f"/usr/bin/{GREETER_SESSION_BIN}")


def _write_root_file(content: str, destination: Path, mode: str = "644") -> bool:
    """Install private temporary content without passing it through a shell."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        result = subprocess.run(
            ["sudo", "install", "-D", "-o", "root", "-g", "root", "-m", mode, temp_path, str(destination)],
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _backup_path(path: Path) -> Path:
    return Path(f"{path}.nyxniri.bak")


def _backup_file(path: Path) -> tuple[bool, bool]:
    backup = _backup_path(path)
    if not path.is_file() or backup.exists():
        return True, False
    try:
        copied = subprocess.run(
            ["sudo", "cp", "-n", "--", str(path), str(backup)], check=False
        ).returncode == 0
        return copied, copied
    except OSError:
        return False, False


def _snapshot_file(path: Path) -> tuple[bool, Optional[str]]:
    if not path.is_file():
        return True, None
    try:
        result = subprocess.run(["sudo", "cat", str(path)], capture_output=True, text=True, check=False)
    except OSError:
        return False, None
    return result.returncode == 0, result.stdout if result.returncode == 0 else None


def _restore_or_remove_file(path: Path, content: Optional[str]) -> bool:
    return _write_root_file(content, path) if content is not None else _clear_file(path)


def _clear_file(path: Path) -> bool:
    try:
        return subprocess.run(["sudo", "rm", "-f", str(path)], check=False).returncode == 0
    except OSError:
        return False


def _rollback_setup(
    config_content: Optional[str],
    polkit_content: Optional[str],
    state_existed: bool,
    config_backup_created: bool,
    polkit_backup_created: bool,
) -> bool:
    config_restored = _restore_or_remove_file(GREETER_ETC_CFG, config_content)
    if config_restored and config_backup_created:
        config_restored = _clear_file(_backup_path(GREETER_ETC_CFG))
    polkit_restored = _restore_or_remove_file(GREETER_POLKIT_RULE, polkit_content)
    if polkit_restored and polkit_backup_created:
        polkit_restored = _clear_file(_backup_path(GREETER_POLKIT_RULE))
    restored = config_restored and polkit_restored
    if not state_existed:
        try:
            restored = subprocess.run(
                ["sudo", "rm", "-rf", str(GREETER_STATE_DIR)], check=False
            ).returncode == 0 and restored
        except OSError:
            restored = False
    return restored


def _enabled_conflicting_dm() -> Optional[str]:
    if not shutil.which("systemctl"):
        return None
    for dm in CONFLICT_DMS:
        if subprocess.run(["systemctl", "is-enabled", dm], capture_output=True, check=False).returncode == 0:
            return dm
    return None


def _recorded_display_manager() -> tuple[bool, Optional[str]]:
    """Read the root-owned previous display manager record, if present."""
    if not GREETER_DM_STATE.is_file():
        return True, None
    try:
        result = subprocess.run(
            ["sudo", "cat", str(GREETER_DM_STATE)], capture_output=True, text=True, check=False
        )
    except OSError:
        return False, None
    dm = result.stdout.strip()
    if result.returncode != 0 or dm not in CONFLICT_DMS:
        return False, None
    return True, dm


def _clear_display_manager_record() -> bool:
    try:
        return subprocess.run(["sudo", "rm", "-f", str(GREETER_DM_STATE)], check=False).returncode == 0
    except OSError:
        return False


def _enable_greetd() -> bool:
    try:
        return subprocess.run(
            ["sudo", "systemctl", "enable", "--force", "greetd"], check=False
        ).returncode == 0 and subprocess.run(
            ["systemctl", "is-enabled", "greetd"], capture_output=True, check=False
        ).returncode == 0
    except OSError:
        return False


def _restore_display_manager(previous_dm: Optional[str]) -> bool:
    try:
        greetd_disabled = subprocess.run(
            ["sudo", "systemctl", "disable", "greetd"], check=False
        ).returncode == 0 and subprocess.run(
            ["systemctl", "is-enabled", "greetd"], capture_output=True, check=False
        ).returncode != 0
    except OSError:
        greetd_disabled = False
    if not previous_dm:
        return greetd_disabled
    try:
        previous_enabled = subprocess.run(
            ["sudo", "systemctl", "enable", "--force", previous_dm], check=False
        ).returncode == 0 and subprocess.run(
            ["systemctl", "is-enabled", previous_dm], capture_output=True, check=False
        ).returncode == 0
    except OSError:
        previous_enabled = False
    restored = greetd_disabled and previous_enabled
    print(msg("greeter_dm_restored" if restored else "greeter_dm_restore_failed", previous_dm))
    return restored


def _switch_to_greetd(previous_dm: Optional[str], keep_record_on_rollback: bool = False) -> bool:
    """Switch the next-boot display manager and roll back any failed switch."""
    switch_started = False
    committed = False
    try:
        if previous_dm:
            switch_started = True
            if subprocess.run(["sudo", "systemctl", "disable", previous_dm], check=False).returncode != 0:
                print(msg("greeter_dm_disable_failed", previous_dm))
                return False
        switch_started = True
        enabled = subprocess.run(["sudo", "systemctl", "enable", "greetd"], check=False).returncode == 0
        verified = subprocess.run(
            ["systemctl", "is-enabled", "greetd"], capture_output=True, check=False
        ).returncode == 0
        if enabled and verified:
            committed = True
            print(msg("greeter_enabled"))
            return True
        print(msg("greeter_enable_failed"))
        return False
    except OSError:
        print(msg("greeter_enable_failed"))
        return False
    finally:
        if switch_started and not committed and _restore_display_manager(previous_dm) and not keep_record_on_rollback:
            _clear_display_manager_record()

def greeter_installed() -> bool:
    """Check if noctalia-greeter session binary exists in PATH."""
    return _greeter_session_path() is not None

_GREETER_STATUS_CACHE: Optional[str] = None

def greeter_status_label() -> str:
    global _GREETER_STATUS_CACHE
    if _GREETER_STATUS_CACHE is not None:
        return _GREETER_STATUS_CACHE
    if not greeter_installed():
        _GREETER_STATUS_CACHE = msg("status_not_installed")
        return _GREETER_STATUS_CACHE
    cfg_ok = False
    if GREETER_ETC_CFG.is_file():
        try:
            content = GREETER_ETC_CFG.read_text(encoding="utf-8", errors="ignore")
            if GREETER_SESSION_BIN in content:
                cfg_ok = True
        except Exception:
            pass
    enabled = False
    if shutil.which("systemctl"):
        # timed_run degrades a stalled probe to None instead of crashing the
        # menu render; an unavailable status reads as "not enabled" — safe.
        res = timed_run(["systemctl", "is-enabled", "greetd"], 10, capture_output=True, check=False)
        enabled = res is not None and res.returncode == 0
    if enabled and cfg_ok:
        _GREETER_STATUS_CACHE = msg("status_installed_enabled")
    else:
        _GREETER_STATUS_CACHE = msg("status_installed")
    return _GREETER_STATUS_CACHE

def _greeter_session_arg() -> str:
    """Check if niri session is discoverable by noctalia-greeter."""
    greeter_cli = _trusted_executable(shutil.which(GREETER_PKG))
    if greeter_cli:
        try:
            res = subprocess.run([greeter_cli, "sessions"], capture_output=True, text=True, check=False)
            if MAIN_WM.lower() in res.stdout.lower():
                return f"-- --session {MAIN_WM}"
        except Exception:
            pass
    return ""

def greeter_install_packages() -> bool:
    """Install greetd and noctalia-greeter."""
    from nyxniri.deps import ensure_aur_helper, get_preferred_pkg_manager
    print(msg("greeter_install_pkgs"))

    pkg_mgr = get_preferred_pkg_manager()
    is_aur = pkg_mgr != ["sudo", "pacman"]

    # Check greetd
    if shutil.which("pacman"):
        res = subprocess.run(["pacman", "-Qq", "greetd"], capture_output=True, check=False)
        if res.returncode != 0:
            subprocess.run([*pkg_mgr, "-S", "--noconfirm", "greetd"], check=False)

    if not greeter_installed():
        has_aur_helper = ensure_aur_helper() is not None if not is_aur else True
        if not has_aur_helper:
            print(msg("greeter_aur_required"))
            return False
        res_inst = subprocess.run([*pkg_mgr, "-S", "--noconfirm", GREETER_PKG], check=False)
        if res_inst.returncode != 0 or not greeter_installed():
            print(msg("greeter_install_failed"))
            return False

    return True

def greeter_install() -> bool:
    """Full Noctalia Greeter installation and configuration pipeline."""
    print(msg("greeter_install_title"))

    # Reject control characters and shell syntax before package installation
    # invokes a privileged package manager.  An absent entry is fine: the
    # package step below may be installing it for the first time.  The full
    # root-owned canonical-path check still happens below before use.
    session_candidate = shutil.which(GREETER_SESSION_BIN)
    if session_candidate and any(char in UNSAFE_PATH_CHARS for char in session_candidate):
        print(msg("greeter_install_failed"))
        return False

    if not greeter_install_packages():
        return False

    sess_path = _greeter_session_path()
    if not sess_path:
        print(msg("greeter_install_failed"))
        return False
    sess_arg = _greeter_session_arg()
    command_str = f"{sess_path} {sess_arg}".strip()

    toml_content = (
        "[terminal]\n"
        "vt = 1\n\n"
        "[default_session]\n"
        f'command = "{command_str}"\n'
        'user = "greeter"\n'
    )

    config_ok, config_content = _snapshot_file(GREETER_ETC_CFG)
    polkit_ok, polkit_content = _snapshot_file(GREETER_POLKIT_RULE)
    state_existed = GREETER_STATE_DIR.exists()
    if not config_ok or not polkit_ok:
        print(msg("greeter_cmd_failed", "backup"))
        return False
    config_backup_ok, config_backup_created = _backup_file(GREETER_ETC_CFG)
    if not config_backup_ok:
        print(msg("greeter_cmd_failed", "backup"))
        return False
    polkit_backup_ok, polkit_backup_created = _backup_file(GREETER_POLKIT_RULE)
    if not polkit_backup_ok:
        if config_backup_created:
            _clear_file(_backup_path(GREETER_ETC_CFG))
        print(msg("greeter_cmd_failed", "backup"))
        return False

    if not _write_root_file(toml_content, GREETER_ETC_CFG):
        print(msg("greeter_config_failed", str(GREETER_ETC_CFG)))
        _rollback_setup(
            config_content, polkit_content, state_existed, config_backup_created, polkit_backup_created
        )
        return False
    print(msg("greeter_config_written", str(GREETER_ETC_CFG)))

    if subprocess.run(
        ["sudo", "install", "-d", "-o", "greeter", "-g", "greeter", "-m", "755", str(GREETER_STATE_DIR)],
        check=False,
    ).returncode != 0:
        print(msg("greeter_cmd_failed", str(GREETER_STATE_DIR)))
        _rollback_setup(
            config_content, polkit_content, state_existed, config_backup_created, polkit_backup_created
        )
        return False
    print(msg("greeter_state_dir_created"))

    # Polkit rule
    polkit_rule = (
        'polkit.addRule(function(action, subject) {\n'
        f'    if (action.id == "org.{THEME_ENGINE}.greeter.apply-appearance" &&\n'
        '        subject.isInGroup("wheel")) {\n'
        '        return polkit.Result.YES;\n'
        '    }\n'
        '});\n'
    )
    if not _write_root_file(polkit_rule, GREETER_POLKIT_RULE):
        print(msg("greeter_polkit_failed"))
        _rollback_setup(
            config_content, polkit_content, state_existed, config_backup_created, polkit_backup_created
        )
        return False
    print(msg("greeter_polkit_written", str(GREETER_POLKIT_RULE)))

    if not shutil.which("systemctl") or subprocess.run(
        ["systemctl", "cat", "greetd"], capture_output=True, check=False
    ).returncode != 0:
        print(msg("greeter_service_missing"))
        _rollback_setup(
            config_content, polkit_content, state_existed, config_backup_created, polkit_backup_created
        )
        return False
    valid_record, recorded_dm = _recorded_display_manager()
    if not valid_record:
        print(msg("greeter_dm_record_invalid"))
        _rollback_setup(
            config_content, polkit_content, state_existed, config_backup_created, polkit_backup_created
        )
        return False
    greetd_enabled = subprocess.run(
        ["systemctl", "is-enabled", "greetd"], capture_output=True, check=False
    ).returncode == 0
    if greetd_enabled:
        print(msg("greeter_enabled_skip"))
        print(msg("greeter_reboot_hint"))
        log_msg("INFO", "Configured Noctalia Greeter")
        _GREETER_STATUS_CACHE = None
        return True

    previous_dm = _enabled_conflicting_dm()
    if previous_dm:
        print(msg("greeter_dm_conflict", previous_dm))
        if not _write_root_file(f"{previous_dm}\n", GREETER_DM_STATE, "600"):
            print(msg("greeter_cmd_failed", str(GREETER_DM_STATE)))
            _rollback_setup(
                config_content, polkit_content, state_existed, config_backup_created, polkit_backup_created
            )
            return False
    rollback_dm = previous_dm or recorded_dm
    if not _switch_to_greetd(rollback_dm, previous_dm is None and recorded_dm is not None):
        _rollback_setup(
            config_content, polkit_content, state_existed, config_backup_created, polkit_backup_created
        )
        return False

    print(msg("greeter_reboot_hint"))
    log_msg("INFO", "Configured Noctalia Greeter")
    _GREETER_STATUS_CACHE = None
    return True

def greeter_status() -> None:
    """Print detailed status of Noctalia Greeter."""
    print(msg("greeter_status_title"))
    if greeter_installed():
        print(msg("doctor_ok", text(f"{GREETER_PKG}: 已安装", f"{GREETER_PKG}: installed")))
    else:
        print(msg("doctor_warn", text(f"{GREETER_PKG}: 未安装", f"{GREETER_PKG}: not installed")))

    if GREETER_ETC_CFG.is_file():
        try:
            content = GREETER_ETC_CFG.read_text(encoding="utf-8", errors="ignore")
            if GREETER_SESSION_BIN in content:
                print(msg("doctor_ok", text(f"greetd 配置: 已使用 {GREETER_PKG}", f"greetd config: using {GREETER_PKG}")))
            else:
                print(msg("doctor_warn", text(
                    f"greetd 配置存在，但未使用 {GREETER_PKG}",
                    f"greetd config exists but does not use {GREETER_PKG}",
                )))
        except Exception:
            pass
    else:
        print(msg("doctor_warn", text(f"greetd 配置缺失: {GREETER_ETC_CFG}", f"greetd config is missing: {GREETER_ETC_CFG}")))

    if shutil.which("systemctl"):
        res = subprocess.run(["systemctl", "is-enabled", "greetd"], capture_output=True, check=False)
        if res.returncode == 0:
            print(msg("doctor_ok", text("greetd 服务: 已启用", "greetd service: enabled")))
        else:
            print(msg("doctor_warn", text("greetd 服务: 未启用", "greetd service: disabled")))

def greeter_uninstall() -> bool:
    """Uninstall Noctalia Greeter configuration and restore backups."""
    print(msg("greeter_uninstall_title"))

    valid_record, previous_dm = _recorded_display_manager()
    if not shutil.which("systemctl"):
        print(msg("greeter_enable_failed"))
        return False
    try:
        greetd_enabled = subprocess.run(
            ["systemctl", "is-enabled", "greetd"], capture_output=True, check=False
        ).returncode == 0
    except OSError:
        print(msg("greeter_enable_failed"))
        return False
    if not valid_record or (greetd_enabled and not previous_dm):
        print(msg("greeter_dm_record_invalid"))
        return False
    if previous_dm or greetd_enabled:
        try:
            disabled = subprocess.run(["sudo", "systemctl", "disable", "greetd"], check=False).returncode == 0
            greetd_disabled = subprocess.run(
                ["systemctl", "is-enabled", "greetd"], capture_output=True, check=False
            ).returncode != 0
        except OSError:
            disabled = greetd_disabled = False
    else:
        disabled = greetd_disabled = True
    if not disabled or not greetd_disabled:
        print(msg("greeter_enable_failed"))
        if not _enable_greetd():
            print(msg("greeter_greetd_restore_failed"))
        return False
    if previous_dm:
        try:
            restored = subprocess.run(
                ["sudo", "systemctl", "enable", "--force", previous_dm], check=False
            ).returncode == 0 and subprocess.run(
                ["systemctl", "is-enabled", previous_dm], capture_output=True, check=False
            ).returncode == 0
        except OSError:
            restored = False
        if not restored:
            print(msg("greeter_dm_restore_failed", previous_dm))
            if not _enable_greetd():
                print(msg("greeter_greetd_restore_failed"))
            return False
        print(msg("greeter_dm_restored", previous_dm))

    bak = Path(f"{GREETER_ETC_CFG}.nyxniri.bak")
    if bak.is_file():
        if subprocess.run(["sudo", "mv", "-f", str(bak), str(GREETER_ETC_CFG)], check=False).returncode != 0:
            print(msg("greeter_cmd_failed", str(GREETER_ETC_CFG)))
            return False
        print(msg("greeter_uninstall_restored", str(GREETER_ETC_CFG)))
    else:
        print(msg("greeter_uninstall_nobackup"))

    polkit_backup = _backup_path(GREETER_POLKIT_RULE)
    if polkit_backup.is_file():
        if subprocess.run(["sudo", "mv", "-f", str(polkit_backup), str(GREETER_POLKIT_RULE)], check=False).returncode != 0:
            print(msg("greeter_cmd_failed", str(GREETER_POLKIT_RULE)))
            return False
        print(msg("greeter_uninstall_polkit_restored"))
    elif GREETER_POLKIT_RULE.is_file():
        if subprocess.run(["sudo", "rm", "-f", str(GREETER_POLKIT_RULE)], check=False).returncode != 0:
            print(msg("greeter_cmd_failed", str(GREETER_POLKIT_RULE)))
            return False
        print(msg("greeter_uninstall_polkit"))

    # Remove the greeter's state directory (created at install; previously leaked)
    if subprocess.run(["sudo", "rm", "-rf", str(GREETER_STATE_DIR)], check=False).returncode != 0:
        print(msg("greeter_cmd_failed", str(GREETER_STATE_DIR)))
        return False
    print(msg("greeter_uninstall_state_dir", str(GREETER_STATE_DIR)))
    if not _clear_display_manager_record():
        print(msg("greeter_cmd_failed", str(GREETER_DM_STATE)))
        return False

    print(msg("greeter_uninstall_done"))
    log_msg("INFO", "Uninstalled Noctalia Greeter configuration")
    _GREETER_STATUS_CACHE = None
    return True
