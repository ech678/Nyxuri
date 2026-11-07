"""System runtime environment: paths, context, locking, logging, and security."""

import atexit
import datetime
import fcntl
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional, Set

# --- Project Identity & Constants ---
PROJECT_NAME = "Nyxuri"
CLI_CMD = "nyxuri"
STORAGE_NAME = "nyxuri"
LEGACY_PROJECT_NAMES = ("NyxNiri",)
LEGACY_CLI_CMDS = ("nyxniri",)
LEGACY_STORAGE_NAMES = ("NyxNiri", "nyxniri")

THEME_ENGINE = "noctalia"
GREETER_PKG = "noctalia-greeter"
GREETER_SESSION_BIN = "noctalia-greeter-session"
GREETER_ETC_CFG = Path("/etc/greetd/config.toml")
GREETER_DM_STATE = GREETER_ETC_CFG.parent / "nyxuri-display-manager"
GREETER_POLKIT_RULE = Path(f"/etc/polkit-1/rules.d/50-{GREETER_PKG}.rules")
GREETER_STATE_DIR = Path("/var/lib") / GREETER_PKG
FCITX_THEME = "nyxmellow"

CONFIG_DIR_NAME = "plugins"
REPO_URL = "https://github.com/ech678/Nyxuri.git"

CONTAINER_MARKERS = ("/.dockerenv", "/run/.containerenv", "/.singularity.d/env/99-base.sh")
CONTAINER_ENV_VARS = ("container", "PROOT_L2S_DIR", "PROOT_LOADER", "PROOT_TMP_DIR")


RAW_MIRROR_TEMPLATES = [
    ("Official", "https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
    ("Ghproxy", "https://ghfast.top/https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
    ("FastGit", "https://raw.fastgit.org/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
]

CLONE_MIRROR_TEMPLATES = [
    ("Official", "https://github.com/{USER_REPO}.git"),
    ("Ghproxy", "https://ghfast.top/https://github.com/{USER_REPO}.git"),
    ("FastGit", "https://hub.fastgit.xyz/{USER_REPO}.git"),
]

CORE_DEPS = [
    "wlsunset",
    "fish",
    "starship",
    "kitty",
    "fastfetch",
    "eza",
    "mpvpaper",
    "ffmpeg",
    "jq",
    "tmux",
    "inotify-tools",
    "fzf",
    "ttf-jetbrains-mono",
    "ttf-jetbrains-mono-nerd",
    "noto-fonts-cjk",
    "qt6-imageformats",
    "cliphist",
]
CORE_NIRI_DEPS = ["niri", "xwayland-satellite"]
from nyxuri.system.compositors import MAIN_WM

DESKTOP_DEPS = [MAIN_WM, THEME_ENGINE]
AUR_DEPS = ["mpvpaper"]
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

PENDING_UPGRADE_ENV = "NYXURI_PENDING_UPGRADE"
PENDING_UPGRADE_MENU_ENV = "NYXURI_PENDING_UPGRADE_MENU"


def get_env_var(suffix: str, default: str | None = None) -> str | None:
    """Retrieve the NYXURI_<suffix> environment variable."""
    return os.environ.get(f"NYXURI_{suffix}", default)


def in_container() -> bool:
    """True when running as a container guest rather than on a real host."""
    if get_env_var("ALLOW_ROOT") == "1":
        return True
    if any(os.environ.get(name) for name in CONTAINER_ENV_VARS):
        return True
    return any(Path(marker).exists() for marker in CONTAINER_MARKERS)


# --- ANSI Styling Palette ---
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    DARK_GRAY = "\033[90m"

    # Bold Foreground colors
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_PURPLE = "\033[1;35m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_WHITE = "\033[1;37m"

    # Cursor controls
    CURSOR_HIDE = "\033[?25l"
    CURSOR_SHOW = "\033[?25h"
    CLEAR_SCREEN = "\033[H\033[J"
    CLEAR_LINE = "\033[2K\r"


# --- Temporary Paths Registry ---
_CLEANUP_TEMP_PATHS: Set[Path] = set()


def register_temp_path(path: Path | str) -> None:
    if path:
        _CLEANUP_TEMP_PATHS.add(Path(path))


def remove_path(path: Path) -> None:
    """Remove a path without following a top-level symlink."""
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
    for p in list(_CLEANUP_TEMP_PATHS):
        remove_path(p)
    _CLEANUP_TEMP_PATHS.clear()


atexit.register(cleanup_temp_paths)


# --- Path Security & Containment ---
def is_safe_leaf_name(value: str) -> bool:
    """True iff value is a single safe leaf filename (no traversal, no control chars)."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if value in (".", "..") or Path(value).is_absolute():
        return False
    if os.sep in value or (os.altsep and os.altsep in value):
        return False
    try:
        return len(os.fsencode(value)) <= 255 and all(
            unicodedata.category(char) not in ("Cc", "Cs") for char in value
        )
    except UnicodeEncodeError:
        return False


def safe_child(root: Path, *parts: str) -> Optional[Path]:
    """Return a non-symlink child contained below root, or None if unsafe."""
    if not all(is_safe_leaf_name(part) for part in parts):
        return None
    try:
        if root.exists() and root.is_symlink():
            return None
        candidate = root.joinpath(*parts)
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
        current = root
        for part in parts:
            current /= part
            if current.exists() and current.is_symlink():
                return None
        return candidate
    except (OSError, RuntimeError, ValueError):
        return None


def assert_contained(child: Path, root: Path) -> Path:
    """Raise ValueError if child does not resolve strictly within root."""
    try:
        child.resolve(strict=False).relative_to(root.resolve(strict=False))
        return child
    except (ValueError, RuntimeError) as exc:
        raise ValueError(f"Path escape detected: {child} outside {root}") from exc


# --- XDG User Directories ---
XDG_USER_DIR_DEFAULTS: Dict[str, str] = {
    "DESKTOP": "Desktop",
    "DOWNLOAD": "Downloads",
    "TEMPLATES": "Templates",
    "PUBLICSHARE": "Public",
    "DOCUMENTS": "Documents",
    "MUSIC": "Music",
    "PICTURES": "Pictures",
    "VIDEOS": "Videos",
}

_XDG_DIR_CACHE: Dict[str, Path] = {}
_PICS_DIR_CACHE: Optional[Path] = None


def get_xdg_user_dir(kind: str) -> Path:
    """Resolve an XDG user directory (e.g. PICTURES -> ~/Pictures or ~/图片)."""
    kind = kind.upper()
    if kind not in XDG_USER_DIR_DEFAULTS:
        raise ValueError(f"unsupported xdg category: '{kind}'")
    if kind in _XDG_DIR_CACHE:
        return _XDG_DIR_CACHE[kind]
    home = get_env().home
    try:
        res = subprocess.run(
            ["xdg-user-dir", kind],
            capture_output=True, text=True, check=False,
            timeout=5,
            env={**os.environ, "LC_ALL": "C"}
        )
        d = res.stdout.strip()
        if d and d != str(home):
            p = Path(d)
            _XDG_DIR_CACHE[kind] = p
            return p
    except Exception:
        pass
    fallback = home / XDG_USER_DIR_DEFAULTS[kind]
    _XDG_DIR_CACHE[kind] = fallback
    return fallback


def get_pics_dir() -> Path:
    global _PICS_DIR_CACHE
    if _PICS_DIR_CACHE is not None:
        return _PICS_DIR_CACHE
    _PICS_DIR_CACHE = get_xdg_user_dir("PICTURES")
    return _PICS_DIR_CACHE


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
    if (root_dir / CONFIG_DIR_NAME).is_dir():
        return ("repo", "Local Path", root_dir)
    return ("standalone", "Remote Cache", cache_dir)


def _merge_directory_contents(src: Path, dest: Path) -> bool:
    if not src.is_dir() or src.is_symlink():
        return False
    dest.mkdir(parents=True, exist_ok=True)
    moved_anything = False
    for item in list(src.iterdir()):
        dest_item = dest / item.name
        if dest_item.exists() or dest_item.is_symlink():
            continue
        try:
            shutil.move(str(item), str(dest_item))
            moved_anything = True
        except (OSError, shutil.Error):
            continue
    try:
        if not any(src.iterdir()):
            src.rmdir()
    except OSError:
        pass
    return moved_anything


def _safe_migrate_storage_dir(legacy_dir: Path, target_dir: Path) -> None:
    if not legacy_dir.is_dir() or legacy_dir.is_symlink():
        return
    if target_dir.is_symlink():
        return
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if not target_dir.exists():
        try:
            shutil.move(str(legacy_dir), str(target_dir))
            return
        except (OSError, shutil.Error):
            pass
    _merge_directory_contents(legacy_dir, target_dir)


def migrate_legacy_storage(env: "Environment") -> None:
    home = env.home
    legacy_base_names = ("NyxNiri", "nyxniri")

    for old_name in legacy_base_names:
        if old_name == STORAGE_NAME:
            continue
        _safe_migrate_storage_dir(env.config_dir / old_name, env.nyx_dir)
        _safe_migrate_storage_dir(env.cache_dir / old_name, env.cache_dir / STORAGE_NAME)

        old_state = (Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")) / old_name)
        _safe_migrate_storage_dir(old_state, env.state_dir)

        old_data = (Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")) / old_name)
        _safe_migrate_storage_dir(old_data, env.data_dir)


class Environment:
    def __init__(self, root_dir: Optional[Path] = None):
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

        raw_data = os.environ.get("XDG_DATA_HOME")
        if raw_data:
            data_path = Path(raw_data)
            try:
                if data_path.is_relative_to(self.home):
                    self.data_dir = data_path / STORAGE_NAME
                else:
                    self.data_dir = self.home / ".local/share" / STORAGE_NAME
            except (ValueError, AttributeError):
                self.data_dir = self.home / ".local/share" / STORAGE_NAME
        else:
            self.data_dir = self.home / ".local/share" / STORAGE_NAME

        self.cache_dir = self.home / ".cache" / STORAGE_NAME
        self.config_dir = self.home / ".config"
        self.nyx_dir = self.config_dir / STORAGE_NAME

        if root_dir is None:
            current_file = Path(__file__).resolve()
            root_dir = current_file.parent.parent.parent

        self.root_dir = root_dir
        self.run_mode, self.mode_label, self.repo_dir = _detect_run_mode(root_dir, self.cache_dir)
        self.target_dir = self.repo_dir

        self.plugins_src = self.repo_dir / CONFIG_DIR_NAME
        self.units_src = self.plugins_src

        self.shell_src = self.repo_dir / "shell"
        self.shell_units_src = self.shell_src / "plugins"
        self.quickshell_target = self.config_dir / "quickshell" / STORAGE_NAME

        self.backups_dir = self.nyx_dir / "backups"
        self.forms_dir = self.nyx_dir / "forms"
        self.hooks_dir = self.nyx_dir / "hooks"
        self.version = get_version(self.repo_dir)


_ENV: Optional[Environment] = None


def get_env() -> Environment:
    global _ENV
    if _ENV is None:
        _ENV = Environment()
        migrate_legacy_storage(_ENV)
    return _ENV


# --- Dynamic Version Extractor ---
def get_version(target_dir: Path) -> str:
    pkgbuild_path = target_dir / "packaging" / "PKGBUILD"
    if pkgbuild_path.is_file():
        try:
            content = pkgbuild_path.read_text(encoding="utf-8")
            ver_m = re.search(r"^pkgver=([^\s#]+)", content, re.MULTILINE)
            rel_m = re.search(r"^pkgrel=([^\s#]+)", content, re.MULTILINE)
            if ver_m:
                v = ver_m.group(1).strip()
                r = rel_m.group(1).strip() if rel_m else "1"
                return f"v{v}-{r}" if r != "1" else f"v{v}"
        except Exception:
            pass

    changelog_path = target_dir / "CHANGELOG.md"
    if changelog_path.is_file():
        try:
            content = changelog_path.read_text(encoding="utf-8")
            m = re.search(r"##\s*\[v?([0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-[a-zA-Z0-9.]+)?)\]", content)
            if m:
                return f"v{m.group(1).lstrip('v')}"
        except Exception:
            pass

    return "v4.0.0-alpha.2"


# --- Single-Instance Lock ---
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
        from nyxuri.system.i18n import msg
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


def init_logger() -> None:
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
    env = kw.get("env")
    if env is None:
        kw["env"] = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    else:
        kw["env"] = {**env, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        return subprocess.run(cmd, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        name = cmd[0] if cmd else "<empty>"
        log_msg("WARN", f"Command timed out after {timeout}s: {name}")
        return None
    except (FileNotFoundError, OSError):
        name = cmd[0] if cmd else "<empty>"
        log_msg("WARN", f"Command not available: {name}")
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
    if not path.is_symlink():
        return None
    try:
        st = path.lstat()
        return f"{path.resolve(strict=False)}\n{st.st_dev}:{st.st_ino}\n"
    except (OSError, RuntimeError):
        return None


def _record_nyxuri_cli_symlink(path: Path, env: Optional["Environment"] = None) -> bool:
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


def is_nyxuri_cli_symlink(path: Path, env: Optional["Environment"] = None) -> bool:
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
        if target_path.name in ("launcher.sh", "install.sh"):
            resolved_str = str(path.resolve(strict=False))
            raw_str = str(target_path)
            if (
                "Nyxuri" in raw_str
                or "nyxuri" in raw_str
                or "NyxNiri" in raw_str
                or "nyxniri" in raw_str
                or "Nyxuri" in resolved_str
                or "nyxuri" in resolved_str
                or "NyxNiri" in resolved_str
                or "nyxniri" in resolved_str
            ):
                return True
    except (OSError, RuntimeError):
        pass
    return False


def clear_nyxuri_cli_symlink_marker() -> None:
    marker = _cli_link_marker()
    try:
        if not marker.is_symlink() and marker.is_file():
            marker.unlink()
    except OSError:
        pass


def launcher_path(env: "Environment") -> Optional[Path]:
    for base in (env.repo_dir, env.root_dir, env.cache_dir / STORAGE_NAME):
        candidate = base / "nyxuri" / "launcher.sh"
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    return None


def exec_cli(env: "Environment", **extra_env: str) -> bool:
    target = launcher_path(env)
    argv = [str(target)] if target else [sys.executable, "-m", CLI_CMD]
    try:
        os.execve(argv[0], argv, {**os.environ, **extra_env})
    except OSError as e:
        log_msg("ERROR", f"Re-exec failed: {e}")
        from nyxuri.system.i18n import msg
        print(msg("update_restart_needed"), file=sys.stderr)
        return False
    return True


def ensure_nyxuri_symlink() -> None:
    env = get_env()
    if env.run_mode == "system":
        return

    bin_dir = env.home / ".local" / "bin"
    symlink_path = bin_dir / CLI_CMD
    target = launcher_path(env)
    if target is None:
        return

    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    if symlink_path.is_symlink():
        try:
            if symlink_path.resolve(strict=False) == target.resolve(strict=False):
                _record_nyxuri_cli_symlink(symlink_path, env)
                return
            if not is_nyxuri_cli_symlink(symlink_path, env):
                return
            symlink_path.unlink()
        except OSError:
            return
    elif symlink_path.exists():
        return

    try:
        symlink_path.symlink_to(target)
        _record_nyxuri_cli_symlink(symlink_path, env)
    except OSError:
        pass


def ensure_nyxuri_shell_symlink() -> None:
    env = get_env()
    bin_dir = env.home / ".local" / "bin"
    shell_link = bin_dir / "nyxuri-shell"

    if env.run_mode == "system":
        return

    target = env.repo_dir / "shell" / "nyxuri-shell"
    if not (target.is_file() and not target.is_symlink()):
        return

    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        if shell_link.is_symlink():
            if shell_link.resolve(strict=False) == target.resolve(strict=False):
                return
            shell_link.unlink()
        elif shell_link.exists():
            return
        shell_link.symlink_to(target)
    except OSError:
        pass


def check_path_occlusion() -> bool:
    env = get_env()
    if env.run_mode != "system":
        return False
    symlink_path = env.home / ".local" / "bin" / CLI_CMD
    if symlink_path.is_symlink() or symlink_path.exists():
        from nyxuri.system.i18n import msg
        print(msg("path_occlusion_warn"))
        log_msg("WARN", f"User-territory {CLI_CMD} link shadows the system package")
        return True
    return False
