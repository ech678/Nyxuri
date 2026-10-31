"""Core runtime infrastructure: paths, locking, logging, traps, and version detection."""

import atexit
import datetime
import fcntl
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Dict, Optional


# --- Project Identity, Paths & Palettes (merged from constants.py, KM3.5) ---
# --- Project Identity ---
PROJECT_NAME = "Nyxuri"
CLI_CMD = "nyxuri"
STORAGE_NAME = "nyxuri"
LEGACY_PROJECT_NAMES = ("NyxNiri",)
LEGACY_CLI_CMDS = ("nyxniri",)
LEGACY_STORAGE_NAMES = ("NyxNiri", "nyxniri")
MAIN_WM = "niri"
SUPPORTED_WMS = ("niri", "mango")


def detect_preferred_wm() -> str:
    """Detect current running or preferred WM from environment."""
    xdg = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    for wm in SUPPORTED_WMS:
        if wm == xdg or wm in xdg:
            return wm
    return MAIN_WM


THEME_ENGINE = "noctalia"
GREETER_PKG = "noctalia-greeter"
GREETER_SESSION_BIN = "noctalia-greeter-session"
GREETER_ETC_CFG = Path("/etc/greetd/config.toml")
GREETER_DM_STATE = GREETER_ETC_CFG.parent / "nyxuri-display-manager"
GREETER_POLKIT_RULE = Path(f"/etc/polkit-1/rules.d/50-{GREETER_PKG}.rules")
GREETER_STATE_DIR = Path("/var/lib") / GREETER_PKG
FCITX_THEME = "nyxmellow"


def get_env_var(suffix: str, default: str | None = None) -> str | None:
    """Retrieve the NYXURI_<suffix> environment variable."""
    return os.environ.get(f"NYXURI_{suffix}", default)


# Carries the update deploy flag across the post-update re-exec, so the
# deploy runs on the freshly pulled code instead of modules already loaded
# into the old process (mixed old/new imports would crash mid-deploy).
PENDING_UPGRADE_ENV = "NYXURI_PENDING_UPGRADE"
# Set alongside PENDING_UPGRADE_ENV when the update came from the interactive
# menu: the fresh process returns to the menu after deploying instead of exiting.
PENDING_UPGRADE_MENU_ENV = "NYXURI_PENDING_UPGRADE_MENU"

# --- Directory Constants ---
# Blueprint root, renamed units/ → plugins/ at R0-1 (concept: Plugin).
CONFIG_DIR_NAME = "plugins"

# --- Repository & Network Mirrors ---
REPO_URL = "https://github.com/ech678/Nyxuri.git"

RAW_MIRROR_TEMPLATES = [
    ("Official", "https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
    ("jsDelivr-CDN", "https://fastly.jsdelivr.net/gh/{USER_REPO}@{BRANCH}/{FILE_PATH}"),
    ("gh-proxy.org", "https://gh-proxy.org/https://raw.githubusercontent.com/{USER_REPO}/{BRANCH}/{FILE_PATH}"),
]

# --- Dependencies ---
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

# Desktop integrations are selectable components; the management engine does
# not require a particular compositor or shell to start and diagnose itself.
DESKTOP_DEPS = [MAIN_WM, THEME_ENGINE]

AUR_DEPS = [
    "mpvpaper",
]

# --- ANSI Styling Palette (Nyxuri Native) ---
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


# --- Bilingual i18n Engine (merged from i18n.py, KM3.5) ---
_LOCALE_SOURCE: str = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG", "")
_CURRENT_LANG: str = "zh" if "zh" in _LOCALE_SOURCE.lower() else "en"

def get_lang() -> str:
    """Get currently selected language mode ('zh' or 'en')."""
    return _CURRENT_LANG

def set_lang(lang: str) -> None:
    """Set language mode ('zh' or 'en')."""
    global _CURRENT_LANG
    _CURRENT_LANG = "zh" if lang.startswith("zh") else "en"
    _MSG_CACHE.clear()

def text(zh: str, en: str) -> str:
    """Pick a one-off bilingual string by active language.

    Escape hatch for diagnostic/status lines not worth a TRANSLATIONS entry
    (``msg()`` remains the default for keyed strings). Centralizes the per-module
    ``_text()`` copies that had spread across doctor/fcitx/greeter/gtktheme.
    """
    return zh if get_lang() == "zh" else en

def _load_translations() -> Dict[str, Dict[str, str]]:
    with Path(__file__).with_name("translations.toml").open("rb") as source:
        translations = tomllib.load(source)
    constants = {
        "PROJECT_NAME": PROJECT_NAME,
        "CLI_CMD": CLI_CMD,
        "STORAGE_NAME": STORAGE_NAME,
    }
    constants.update({f"Colors.{name}": value for name, value in vars(Colors).items()
                      if name.isupper() and isinstance(value, str)})
    for entry in translations.values():
        for lang, template in entry.items():
            for name, value in constants.items():
                template = template.replace("{" + name + "}", value)
            entry[lang] = template
    return translations


TRANSLATIONS = _load_translations()

_MSG_CACHE: Dict[str, str] = {}

def msg(key: str, *args: Any) -> str:
    if not args:
        cached = _MSG_CACHE.get(key)
        if cached is not None:
            return cached
    lang = get_lang()
    entry = TRANSLATIONS.get(key)
    if not entry:
        result = key if not args else f"{key} ({', '.join(str(a) for a in args)})"
        if not args:
            _MSG_CACHE[key] = result
        return result
    template = entry.get(lang) or entry.get("en") or key
    if args:
        try:
            return template.format(*args)
        except Exception:
            return template
    _MSG_CACHE[key] = template
    return template


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
    if (root_dir / CONFIG_DIR_NAME).is_dir():
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
            if target.is_symlink() and not target.exists():
                return False
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

        self.units_src = self.repo_dir / CONFIG_DIR_NAME
        # Shell blueprint root (unit-model.md §6): the shell namespace's unit
        # manifests live inside the shell tree — file tree expresses architecture.
        self.shell_units_src = self.repo_dir / "shell" / "units"
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
        from nyxuri.core import msg
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

    Child interpreters never write bytecode (PYTHONDONTWRITEBYTECODE=1):
    hooks and tools frequently execute straight from the read-only blueprint
    tree, and a stray __pycache__ there pierces the source/config isolation
    invariant (unit-model §1).
    """
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
        # "install.sh" targets are recognized for one generation so links
        # owned by the pre-KM5 entry (which was the launcher itself) heal
        # to the dedicated launcher on the next ensure_nyxuri_symlink run.
        if target_path.name in ("launcher.sh", "install.sh"):
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
                target_path == e.repo_dir / "nyxuri" / "launcher.sh"
                or target_path == e.cache_dir / "nyxuri" / "launcher.sh"
                or target_path == e.repo_dir / "install.sh"
                or target_path == e.cache_dir / "install.sh"
            ):
                return True
    except (OSError, RuntimeError):
        pass
    return False




def clear_nyxuri_cli_symlink_marker() -> None:
    """Forget a CLI link only after its recorded link has been removed."""
    marker = _cli_link_marker()
    if marker.is_file() and not marker.is_symlink():
        try:
            marker.unlink()
        except OSError:
            pass


def launcher_path(env: "Environment") -> Optional[Path]:
    """The one permanent CLI entry, repo tree first. None if no tree ships one.

    launcher.sh is the only thing that puts the engine package on sys.path for
    repo/standalone runs, so every restart has to go through it.
    """
    for base in (env.repo_dir, env.cache_dir):
        candidate = base / "nyxuri" / "launcher.sh"
        if candidate.is_file():
            return candidate
    return None


def exec_cli(env: "Environment", **extra_env: str) -> bool:
    """Replace this process with the engine on disk; False if exec failed.

    Never spawn `python -m nyxuri` on its own: that only resolves the package
    when the cwd happens to be the repo root (#138).
    """
    target = launcher_path(env)
    argv = [str(target)] if target else [sys.executable, "-m", CLI_CMD]
    try:
        os.execve(argv[0], argv, {**os.environ, **extra_env})
    except OSError as e:
        log_msg("ERROR", f"Re-exec failed: {e}")
        print(msg("update_restart_needed"), file=sys.stderr)
        return False
    return True


def ensure_nyxuri_symlink() -> None:
    """Ensure ~/.local/bin/nyxuri points to the dedicated launcher (nyxuri/launcher.sh).

    KM5: install.sh retired to a one-time bootstrap; the CLI entry is the
    launcher script inside the engine package. Links owned by the pre-KM5
    entry (which pointed at install.sh) are recognized and healed here.

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

    root_launcher = launcher_path(env)
    if root_launcher is None:
        return

    try:
        if target_bin.is_symlink():
            if not is_nyxuri_cli_symlink(target_bin):
                return
            if target_bin.resolve(strict=False) == root_launcher.resolve(strict=False):
                _record_nyxuri_cli_symlink(target_bin)
                root_launcher.chmod(0o755)
                return
            target_bin.unlink(missing_ok=True)
        elif target_bin.exists():
            return
        target_bin.symlink_to(root_launcher)
        if _record_nyxuri_cli_symlink(target_bin):
            root_launcher.chmod(0o755)
        else:
            target_bin.unlink(missing_ok=True)
    except Exception:
        pass


def ensure_nyxuri_shell_symlink() -> None:
    """Ensure ~/.local/bin/nyxuri-shell points to shell/nyxuri-shell in repo mode."""
    env = get_env()
    if env.run_mode == "system":
        return

    bin_dir = env.home / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_bin = bin_dir / "nyxuri-shell"

    root_script = env.repo_dir / "shell" / "nyxuri-shell"
    if not root_script.is_file():
        root_script = env.repo_dir / "shell" / "bin" / "nyxuri-shell"
    if not root_script.is_file():
        return

    try:
        if target_bin.is_symlink():
            if target_bin.resolve(strict=False) == root_script.resolve(strict=False):
                root_script.chmod(0o755)
                return
            target_bin.unlink(missing_ok=True)
        elif target_bin.exists():
            return
        target_bin.symlink_to(root_script)
        root_script.chmod(0o755)
    except Exception:
        pass


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
        from nyxuri.core import msg
        print(msg("path_occlusion_warn"))
        log_msg("WARN", f"User-territory {CLI_CMD} link shadows the system package")
        return True
    return False
