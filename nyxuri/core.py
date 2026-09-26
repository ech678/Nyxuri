"""Core runtime infrastructure: paths, locking, logging, traps, and version detection."""

import atexit
import datetime
import fcntl
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from nyxuri.constants import (
    ASSETS_DIR_NAME,
    CLI_CMD,
    CONFIG_DIR_NAME,
    LEGACY_CLI_CMDS,
    LEGACY_PROJECT_NAMES,
    LEGACY_STORAGE_NAMES,
    PROJECT_NAME,
    STORAGE_NAME,
)

# --- Temporary Paths Registry ---
_CLEANUP_TEMP_PATHS: set[Path] = set()

def register_temp_path(path: Path | str) -> None:
    """Register a temporary path to be swept on process exit."""
    if path:
        _CLEANUP_TEMP_PATHS.add(Path(path))

def remove_path(path: Path) -> None:
    """Remove a path without following a top-level symlink.

    Shared by deploy.atomic (swap cleanup) and state.backup/uninstall (archive
    + delete). The symlink check precedes is_dir() so a symlink to a directory
    is unlinked, not rmtree'd through the link.
    """
    try:
        if path.is_symlink():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    except OSError:
        pass

def copy_path(src: Path, dest: Path) -> None:
    """Copy one path while preserving a top-level symlink as a symlink."""
    if src.is_symlink():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.unlink(missing_ok=True)
        dest.symlink_to(os.readlink(src))
    elif src.is_dir():
        shutil.copytree(src, dest, symlinks=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

def cleanup_temp_paths() -> None:
    """Remove all registered temporary files and directories."""
    for p in list(_CLEANUP_TEMP_PATHS):
        remove_path(p)
    _CLEANUP_TEMP_PATHS.clear()

atexit.register(cleanup_temp_paths)

# --- Path Resolution & Environment Context ---
def _detect_run_mode(root_dir: Path, cache_dir: Path):
    """Decide (run_mode, mode_label, repo_dir) from the package's root_dir.

    §5.2 — "where you run it is the mode it is". The .system-install marker wins
    first so a system package at /usr/share/nyxuri (which also ships configs/
    + assets/) is not mis-detected as 'repo'.
    """
    if (root_dir / ".system-install").is_file():
        return ("system", "System Package", root_dir)
    if root_dir.resolve() == cache_dir.resolve():
        return ("standalone", "Remote Cache", cache_dir)
    if (root_dir / CONFIG_DIR_NAME).is_dir() and (root_dir / ASSETS_DIR_NAME).is_dir():
        return ("repo", "Local Path", root_dir)
    return ("standalone", "Remote Cache", cache_dir)


def _merge_directory_contents(src: Path, dest: Path) -> bool:
    """Recursively merge contents of src into dest without clobbering existing files.

    Returns True if all operations completed without unhandled errors.
    """
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            target = dest / item.name
            if item.is_symlink():
                if not target.exists() and not target.is_symlink():
                    copy_path(item, target)
            elif item.is_dir():
                if not target.exists() and not target.is_symlink():
                    shutil.copytree(item, target, symlinks=True)
                elif target.is_dir() and not target.is_symlink():
                    if not _merge_directory_contents(item, target):
                        return False
            else:
                if not target.exists() and not target.is_symlink():
                    copy_path(item, target)
        return True
    except OSError:
        return False


def _safe_migrate_storage_dir(legacy_dir: Path, target_dir: Path) -> None:
    """Migrate legacy_dir to target_dir cleanly, never deleting legacy_dir on failure."""
    if not (legacy_dir.exists() or legacy_dir.is_symlink()) or legacy_dir == target_dir:
        return
    if legacy_dir.is_symlink():
        remove_path(legacy_dir)
        return

    migrated = False
    if not target_dir.exists() and not target_dir.is_symlink():
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            os.replace(legacy_dir, target_dir)
            migrated = True
        except OSError:
            if _merge_directory_contents(legacy_dir, target_dir):
                migrated = True
    else:
        if _merge_directory_contents(legacy_dir, target_dir):
            migrated = True

    if migrated and target_dir.exists():
        remove_path(legacy_dir)


def migrate_legacy_storage(env: "Environment") -> None:
    """Transparently migrate legacy NyxNiri storage directories to nyxuri,

    then cleanly purge legacy directories with zero residue.
    """
    # 1. Config directory: ~/.config/NyxNiri / ~/.config/nyxniri -> ~/.config/nyxuri
    for legacy_name in LEGACY_STORAGE_NAMES:
        _safe_migrate_storage_dir(env.config_dir / legacy_name, env.nyx_dir)

    # 2. State directory: ~/.local/state/NyxNiri / nyxniri -> ~/.local/state/nyxuri
    raw_state = os.environ.get("XDG_STATE_HOME")
    state_base = Path(raw_state) if raw_state else (env.home / ".local/state")
    for legacy_name in LEGACY_STORAGE_NAMES:
        _safe_migrate_storage_dir(state_base / legacy_name, env.state_dir)

    # 3. Cache directory: ~/.cache/NyxNiri / nyxniri -> ~/.cache/nyxuri
    cache_base = env.home / ".cache"
    for legacy_name in LEGACY_STORAGE_NAMES:
        _safe_migrate_storage_dir(cache_base / legacy_name, env.cache_dir)

    # 4. Old CLI symlinks: ~/.local/bin/nyxniri
    for legacy_cmd in LEGACY_CLI_CMDS:
        old_link = env.home / ".local/bin" / legacy_cmd
        if old_link.is_symlink() or old_link.exists():
            if is_nyxuri_cli_symlink(old_link, env):
                old_link.unlink(missing_ok=True)


class Environment:
    def __init__(self):
        self.home = Path(os.environ.get("HOME", str(Path.home())))
        raw_state = os.environ.get("XDG_STATE_HOME")
        if raw_state:
            state_path = Path(raw_state)
            try:
                if state_path.is_relative_to(self.home):
                    self.state_dir = state_path / STORAGE_NAME
                else:
                    self.state_dir = self.home / ".local/state" / STORAGE_NAME
            except (ValueError, AttributeError):
                self.state_dir = self.home / ".local/state" / STORAGE_NAME
        else:
            self.state_dir = self.home / ".local/state" / STORAGE_NAME
        self.cache_dir = self.home / ".cache" / STORAGE_NAME
        self.config_dir = self.home / ".config"

        # Discover execution location & mode. §5.2: the .system-install marker
        # is checked first — a system package under /usr/share/nyxuri also has
        # configs/+assets/ and would otherwise mis-detect as 'repo'.
        current_file = Path(__file__).resolve()
        pkg_dir = current_file.parent
        root_dir = pkg_dir.parent
        self.run_mode, self.mode_label, self.repo_dir = _detect_run_mode(root_dir, self.cache_dir)

        self.configs_src = self.repo_dir / CONFIG_DIR_NAME
        self.assets_src = self.repo_dir / ASSETS_DIR_NAME
        # Nyxuri's own home under ~/.config: backups, presets, active state.
        # (state_dir holds runtime transient; nyx_dir holds user data — §10.4)
        self.nyx_dir = self.config_dir / STORAGE_NAME
        self.presets_dir = self.nyx_dir / "presets"
        self.version = get_version(self.repo_dir)

        # Migrate legacy storage if existing, then purge old directories
        migrate_legacy_storage(self)

_ENV: Optional[Environment] = None

def get_env() -> Environment:
    """Retrieve or initialize the global Environment context."""
    global _ENV
    if _ENV is None:
        _ENV = Environment()
    return _ENV

_PICS_DIR_CACHE: Optional[Path] = None

def get_pics_dir() -> Path:
    global _PICS_DIR_CACHE
    if _PICS_DIR_CACHE is not None:
        return _PICS_DIR_CACHE
    home = get_env().home
    try:
        res = subprocess.run(
            ["xdg-user-dir", "PICTURES"],
            capture_output=True, text=True, check=False,
            timeout=5,
            env={**os.environ, "LC_ALL": "C"}
        )
        d = res.stdout.strip()
        if d and d != str(home):
            _PICS_DIR_CACHE = Path(d)
            return _PICS_DIR_CACHE
    except Exception:
        pass
    _PICS_DIR_CACHE = home / "Pictures"
    return _PICS_DIR_CACHE

# --- Dynamic Version Extractor ---
_VERSION_CACHE: str = ""

def get_version(target_dir: Path) -> str:
    global _VERSION_CACHE
    if _VERSION_CACHE:
        return _VERSION_CACHE
    changelog = target_dir / "CHANGELOG.md"
    if changelog.is_file():
        try:
            content = changelog.read_text(encoding="utf-8")
            for candidate in re.findall(r"^##\s+\[([^\]]+)\]", content, re.MULTILINE):
                if candidate.lower() != "unreleased":
                    _VERSION_CACHE = candidate
                    return _VERSION_CACHE
        except Exception:
            pass
    if (target_dir / ".git").is_dir():
        try:
            res = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=target_dir, capture_output=True, text=True, check=False,
                timeout=5,
                env={**os.environ, "LC_ALL": "C"}
            )
            v = res.stdout.strip()
            if v:
                _VERSION_CACHE = v
                return _VERSION_CACHE
        except Exception:
            pass
    if (target_dir / ".git").is_dir():
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=target_dir, capture_output=True, text=True, check=False,
                timeout=5,
                env={**os.environ, "LC_ALL": "C"}
            )
            v = res.stdout.strip()
            if v:
                _VERSION_CACHE = v
                return _VERSION_CACHE
        except Exception:
            pass
    _VERSION_CACHE = "v3.0.0"
    return _VERSION_CACHE

# --- Single-Instance Lock (fcntl.flock — auto-releases on process death) ---
_LOCK_FILE: Optional[Path] = None
_LOCK_FD: Optional[int] = None
_LOCK_ACQUIRED = False

def acquire_lock() -> None:
    """Acquire single-instance lock via fcntl.flock.

    flock is kernel-level and auto-releases when the process exits (even on
    SIGKILL), so there is no stale-lock healing to do and no check-then-write
    race. A PID is still written to the file for diagnostics only.
    """
    global _LOCK_FILE, _LOCK_FD, _LOCK_ACQUIRED
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE = env.state_dir / f"{CLI_CMD}.lock"
    lock_fd: Optional[int] = None
    try:
        lock_fd = os.open(_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except OSError:
                pass
        _LOCK_FD = None
        _LOCK_ACQUIRED = False
        # Another instance holds the lock — surface its PID if we can read it
        pid = "unknown"
        try:
            content = _LOCK_FILE.read_text().strip()
            if content.isdigit():
                pid = content
        except Exception:
            pass
        from nyxuri.i18n import msg
        print(msg("err_already_running", pid), file=sys.stderr)
        sys.exit(1)
    _LOCK_FD = lock_fd
    _LOCK_ACQUIRED = True
    # Best-effort PID write for diagnostics (the lock itself is the source of truth)
    try:
        os.ftruncate(_LOCK_FD, 0)
        os.write(_LOCK_FD, str(os.getpid()).encode())
    except Exception:
        pass

def release_lock() -> None:
    """Release the lock held by this process; keep the stable lock path."""
    global _LOCK_FD, _LOCK_ACQUIRED
    if _LOCK_ACQUIRED and _LOCK_FD is not None:
        try:
            fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
        except Exception:
            pass
        finally:
            try:
                os.close(_LOCK_FD)
            except Exception:
                pass
            _LOCK_FD = None
            _LOCK_ACQUIRED = False

atexit.register(release_lock)

# --- Rolling Log Engine ---
_LOG_FILE: Optional[Path] = None
ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def init_logger() -> None:
    """Initialize state directory and truncate log to the last 800 lines."""
    global _LOG_FILE
    env = get_env()
    env.state_dir.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = env.state_dir / "install.log"

    if _LOG_FILE.is_file():
        try:
            lines = _LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) > 800:
                _LOG_FILE.write_text("\n".join(lines[-800:]) + "\n", encoding="utf-8")
        except Exception:
            pass

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"{now} [INFO] {PROJECT_NAME} Session Started ({env.version}) [mode: {env.mode_label}]\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(header)
    except Exception:
        pass

def log_msg(level: str, message: str) -> None:
    """Write timestamped, clean message (stripped of ANSI codes) to log file."""
    if _LOG_FILE is None:
        return
    clean_text = ANSI_ESCAPE_RE.sub("", message)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now} [{level}] {clean_text}\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def timed_run(cmd: list, timeout: float, **kw) -> Optional[subprocess.CompletedProcess]:
    """subprocess.run that degrades a timeout to None instead of raising.

    Every external command with a timeout must go through here: a stalled
    network call or unresponsive daemon is polish failing, not a reason to
    crash the whole flow mid-deploy (v3.0.3 shipped timeouts but only
    network.py caught the exception — everything else turned hang into crash).
    """
    try:
        return subprocess.run(cmd, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        log_msg("WARN", f"Command timed out after {timeout}s: {cmd[0]}")
        return None

# --- CLI Binary Symlink ---
def _cli_link_marker(env: Optional["Environment"] = None) -> Path:
    if env is not None:
        return env.state_dir / f"{CLI_CMD}.link"
    global _ENV
    if _ENV is not None:
        return _ENV.state_dir / f"{CLI_CMD}.link"
    return get_env().state_dir / f"{CLI_CMD}.link"


def _cli_link_record(path: Path) -> Optional[str]:
    """Return the exact target and inode proof for a CLI symlink."""
    if not path.is_symlink():
        return None
    try:
        st = path.lstat()
        return f"{path.resolve(strict=False)}\n{st.st_dev}:{st.st_ino}\n"
    except (OSError, RuntimeError):
        return None


def _record_nyxuri_cli_symlink(path: Path, env: Optional["Environment"] = None) -> bool:
    """Persist ownership of one exact CLI symlink."""
    record = _cli_link_record(path)
    marker = _cli_link_marker(env)
    if record is None or marker.is_symlink() or (marker.exists() and not marker.is_file()):
        return False
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(record, encoding="utf-8")
        marker.chmod(0o600)
        return True
    except OSError:
        return False


_record_nyxniri_cli_symlink = _record_nyxuri_cli_symlink


def is_nyxuri_cli_symlink(path: Path, env: Optional["Environment"] = None) -> bool:
    """Whether path matches Nyxuri's recorded CLI symlink or points to a Nyxuri/NyxNiri installer."""
    if not path.is_symlink():
        return False
    record = _cli_link_record(path)
    marker = _cli_link_marker(env)
    if record is not None and not marker.is_symlink() and marker.is_file():
        try:
            if marker.read_text(encoding="utf-8") == record:
                return True
        except OSError:
            pass
    try:
        raw_target = os.readlink(path)
        target_path = Path(raw_target)
        if target_path.name == "install.sh":
            resolved_str = str(path.resolve(strict=False))
            raw_str = str(target_path)
            if (
                "Nyxuri" in raw_str
                or "nyxuri" in raw_str
                or "Nyxuri" in resolved_str
                or "nyxuri" in resolved_str
                or "NyxNiri" in raw_str
                or "nyxniri" in raw_str
                or "NyxNiri" in resolved_str
                or "nyxniri" in resolved_str
            ):
                return True
            e = env or (_ENV if _ENV is not None else get_env())
            if (
                target_path == e.repo_dir / "install.sh"
                or target_path == e.cache_dir / "install.sh"
            ):
                return True
    except (OSError, RuntimeError):
        pass
    return False


is_nyxniri_cli_symlink = is_nyxuri_cli_symlink


def clear_nyxuri_cli_symlink_marker() -> None:
    """Forget a CLI link only after its recorded link has been removed."""
    marker = _cli_link_marker()
    if marker.is_file() and not marker.is_symlink():
        try:
            marker.unlink()
        except OSError:
            pass


clear_nyxniri_cli_symlink_marker = clear_nyxuri_cli_symlink_marker


def ensure_nyxuri_symlink() -> None:
    """Ensure ~/.local/bin/nyxuri points to install.sh.

    In system mode the package owns /usr/bin/nyxuri and must not touch the
    user's ~/.local/bin/nyxuri (§5.3). A stale user link shadowing the system
    package is surfaced separately by check_path_occlusion().
    """
    env = get_env()
    if env.run_mode == "system":
        # Package owns the CLI entry; do not (re)create a user-territory link.
        return

    bin_dir = env.home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_bin = bin_dir / CLI_CMD

    # Clean legacy nyxniri symlink if it points to an installer
    legacy_bin = bin_dir / "nyxniri"
    if legacy_bin != target_bin and legacy_bin.is_symlink() and is_nyxuri_cli_symlink(legacy_bin):
        legacy_bin.unlink(missing_ok=True)

    root_installer = env.repo_dir / "install.sh"
    if not root_installer.is_file():
        if (env.cache_dir / "install.sh").is_file():
            root_installer = env.cache_dir / "install.sh"
        else:
            return

    try:
        if target_bin.is_symlink():
            if not is_nyxuri_cli_symlink(target_bin):
                return
            if target_bin.resolve(strict=False) == root_installer.resolve(strict=False):
                _record_nyxuri_cli_symlink(target_bin)
                root_installer.chmod(0o755)
                return
            target_bin.unlink(missing_ok=True)
        elif target_bin.exists():
            return
        target_bin.symlink_to(root_installer)
        if _record_nyxuri_cli_symlink(target_bin):
            root_installer.chmod(0o755)
        else:
            target_bin.unlink(missing_ok=True)
    except Exception:
        pass


ensure_nyxniri_symlink = ensure_nyxuri_symlink


def check_path_occlusion() -> bool:
    """In system mode, warn if ~/.local/bin/nyxuri shadows /usr/bin/nyxuri.

    ~/.local/bin precedes /usr/bin on PATH, so a stale user link (left from a
    prior curl/git install) silently overrides the system package — the user
    would be running old code while thinking pacman updates them. This check
    is called at the top of update/doctor for a persistent reminder (§5.3).
    Returns True if an occlusion was reported.
    """
    env = get_env()
    if env.run_mode != "system":
        return False
    user_link = env.home / ".local/bin" / CLI_CMD
    if user_link.is_symlink() or user_link.exists():
        from nyxuri.i18n import msg
        print(msg("path_occlusion_warn"))
        log_msg("WARN", f"User-territory {CLI_CMD} link shadows the system package")
        return True
    return False
