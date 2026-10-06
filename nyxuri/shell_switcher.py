"""Dual shell runtime management, readiness probe, and hot-switching state machine.

Ensures safe transitions between Noctalia and Nyxuri Shell (custom) under Wayland.
Strictly follows the P0-06 state machine:
1. Target preflight
2. Lock safety check
3. Graceful stop of old instance (bounded 2.5s)
4. Background spawn of new instance
5. Bounded readiness probe (3.0s)
6. Commit ledger on success; rollback and restore old shell on failure.
"""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from nyxuri.state.ledger import active_shell, custom_shell_bin, set_shell


def normalize_shell_name(name: str) -> str:
    """Normalize shell slot names, accepting aliases 'custom' and 'nyxuri'."""
    s = str(name).strip().lower()
    if s in ("custom", "nyxuri", "nyxuri-shell"):
        return "nyxuri-shell"
    if s == "noctalia":
        return "noctalia"
    return s


def find_default_custom_bin() -> str:
    """Discover default nyxuri-shell binary from repo or PATH."""
    repo_root = Path(__file__).resolve().parent.parent
    local_script = repo_root / "shell" / "nyxuri-shell"
    if local_script.is_file() and os.access(local_script, os.X_OK):
        return str(local_script)

    legacy_script = repo_root / "shell" / "bin" / "nyxuri-shell"
    if legacy_script.is_file() and os.access(legacy_script, os.X_OK):
        return str(legacy_script)

    from_path = shutil.which("nyxuri-shell")
    if from_path and os.path.isfile(from_path) and os.access(from_path, os.X_OK):
        return from_path

    return ""


find_default_shell_bin = find_default_custom_bin


def resolve_custom_bin(specified_bin: Optional[str] = None) -> str:
    """Resolve effective nyxuri-shell executable path."""
    if specified_bin and specified_bin.strip():
        candidate = specified_bin.strip()
        # Self-healing for explicit legacy path
        if candidate.endswith("/shell/bin/nyxuri-shell") and not os.path.isfile(candidate):
            healed = candidate.replace("/shell/bin/nyxuri-shell", "/shell/nyxuri-shell")
            if os.path.isfile(healed) and os.access(healed, os.X_OK):
                return healed
        return candidate

    from_env = os.environ.get("NYXURI_CUSTOM_SHELL_BIN") or os.environ.get("NYXNIRI_CUSTOM_SHELL_BIN")
    if from_env and from_env.strip():
        candidate = from_env.strip()
        if candidate.endswith("/shell/bin/nyxuri-shell") and not os.path.isfile(candidate):
            healed = candidate.replace("/shell/bin/nyxuri-shell", "/shell/nyxuri-shell")
            if os.path.isfile(healed) and os.access(healed, os.X_OK):
                return healed
        return candidate

    recorded = custom_shell_bin()
    if recorded and recorded.strip():
        candidate = recorded.strip()
        if candidate.endswith("/shell/bin/nyxuri-shell") and not os.path.isfile(candidate):
            healed = candidate.replace("/shell/bin/nyxuri-shell", "/shell/nyxuri-shell")
            if os.path.isfile(healed) and os.access(healed, os.X_OK):
                return healed
        return candidate

    return find_default_custom_bin()


resolve_shell_bin = resolve_custom_bin


def preflight_shell(target: str, bin_path: Optional[str] = None) -> Tuple[bool, str, str]:
    """Validate target shell readiness without acquiring shared desktop resources.

    Returns:
        (ok, resolved_binary, error_reason)
    """
    target = normalize_shell_name(target)
    if target not in ("noctalia", "nyxuri-shell"):
        return False, "", f"Unknown target shell: {target} (must be 'noctalia' or 'nyxuri-shell')"

    if target == "noctalia":
        executable = shutil.which("noctalia")
        if not executable:
            return False, "", "Executable 'noctalia' not found in PATH"
        return True, executable, ""

    # target == "nyxuri-shell"
    resolved = resolve_custom_bin(bin_path)
    if not resolved:
        return False, "", "Nyxuri Shell binary not specified and no default nyxuri-shell found"
    if not os.path.isfile(resolved):
        return False, resolved, f"Nyxuri Shell binary does not exist: {resolved}"
    if not os.access(resolved, os.X_OK):
        return False, resolved, f"Nyxuri Shell binary is not executable: {resolved}"

    return True, resolved, ""


def find_pids(pattern: str) -> list[int]:
    """Find running process IDs matching pattern using pure Python /proc parsing."""
    pids = []
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return pids

    for entry in proc_dir.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline_file = entry / "cmdline"
            if not cmdline_file.is_file():
                continue
            raw = cmdline_file.read_bytes()
            cmd = raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
            if pattern in cmd and os.getpid() != int(entry.name):
                pids.append(int(entry.name))
        except (PermissionError, ProcessLookupError, FileNotFoundError):
            continue
    return pids


def probe_running_shells() -> "list[Tuple[str, int]]":
    """Inventory every running shell instance of both kinds.

    probe_running_shell() answers "what is running"; this answers "what is
    ALL running". A crashed switch can leave both shells alive, and a switch
    may only declare a clean field after removing every non-target instance.
    """
    instances: "list[Tuple[str, int]]" = []
    my_pids = {os.getpid(), os.getppid()}

    def classify(args: "list[str]") -> "str | None":
        prog = Path(args[0]).name
        cmd = " ".join(args)
        if any(bad in cmd for bad in ["nyxuri shell", "test_shell", "pytest", "shell_switcher"]):
            return None
        if prog in ("qs", "quickshell", "nyxuri-shell"):
            if any(sub in args for sub in ["ipc", "kill", "--stop", "--check-ready", "--status", "--stage"]):
                return None
            if any("shell" in a for a in args) or prog == "nyxuri-shell":
                return "nyxuri-shell"
            return None
        if (prog == "noctalia" or args[0].endswith("/noctalia")) and "python" not in prog:
            if "greeter" not in cmd:
                return "noctalia"
        return None

    candidate_pids = sorted(set(
        find_pids("qs") + find_pids("quickshell") + find_pids("nyxuri-shell") + find_pids("noctalia")
    ))
    for pid in candidate_pids:
        if pid in my_pids:
            continue
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
            args = [a.decode("utf-8", errors="ignore") for a in raw.split(b"\x00") if a]
            if not args:
                continue
            kind = classify(args)
            if kind:
                instances.append((kind, pid))
        except Exception:
            continue
    return instances


def probe_running_shell() -> Tuple[str, Optional[int]]:
    """Determine currently active running shell process and primary PID.

    Compatibility wrapper over probe_running_shells(); nyxuri-shell instances
    win over noctalia, matching the historical probe order.
    """
    instances = probe_running_shells()
    nyxuri = [pid for name, pid in instances if name == "nyxuri-shell"]
    if nyxuri:
        return "nyxuri-shell", nyxuri[0]
    noctalia = [pid for name, pid in instances if name == "noctalia"]
    if noctalia:
        return "noctalia", noctalia[0]
    return "none", None


def stop_shell_process(shell_name: str, pid: Optional[int], bin_path: str = "", timeout: float = 2.5) -> bool:
    """Gracefully terminate a shell process with bounded timeout.

    Returns True only when the target PID is verifiably gone (or no PID was
    given and only the bin-level stop ran). Callers that must guarantee a
    clean field re-probe afterwards instead of trusting this alone.
    """
    norm = normalize_shell_name(shell_name)
    if norm == "nyxuri-shell":
        effective_bin = bin_path or resolve_shell_bin()
        if effective_bin and os.path.isfile(effective_bin) and os.access(effective_bin, os.X_OK):
            try:
                subprocess.run([effective_bin, "--stop"], timeout=1.0, capture_output=True, check=False)
            except Exception:
                pass

    if not pid:
        return True

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except Exception:
        pass

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            return True

    # Force kill if still lingering
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass

    # Bounded wait so SIGKILL delivery is observable, not assumed.
    deadline = time.time() + 1.0
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            return True
    return False


def stop_all_shell_instances(shell_name: str, bin_path: str = "", timeout: float = 2.5) -> bool:
    """Stop every running instance of the given shell kind.

    True when none remain afterwards. This is the switcher's field-sweep
    primitive: single-PID stops are how dual-shell residue happens.
    """
    norm = normalize_shell_name(shell_name)
    clean = True
    for kind, pid in probe_running_shells():
        if kind != norm:
            continue
        if not stop_shell_process(kind, pid, bin_path, timeout=timeout):
            clean = False
    return clean


def spawn_shell(shell_name: str, bin_path: str) -> subprocess.Popen:
    """Launch target shell in an independent session with logging."""
    norm = normalize_shell_name(shell_name)
    log_dir = Path.home() / ".local" / "state" / "nyxuri"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / f"{norm}-session.log", "a", encoding="utf-8")
    cmd = [bin_path]
    return subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
    )


def wait_shell_ready(shell_name: str, proc: subprocess.Popen, bin_path: str, timeout: float = 3.5) -> bool:
    """Poll for target shell readiness within bounded timeout."""
    norm = normalize_shell_name(shell_name)
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Check if process crashed immediately
        poll_res = proc.poll()
        if poll_res is not None:
            return False

        if norm == "nyxuri-shell":
            try:
                res = subprocess.run([bin_path, "--check-ready"], timeout=0.5, capture_output=True, check=False)
                if res.returncode == 0:
                    return True
            except Exception:
                pass
        elif norm == "noctalia":
            # Probe the daemon over its real IPC surface. `noctalia msg` has
            # NO ping subcommand; theme-mode-get is the lightest query that
            # returns 0 only when the daemon answers. A process merely alive
            # past one second is NOT ready evidence: layer-shell conflicts
            # can keep it dying slowly, and reporting ready then would leave
            # both shells running.
            try:
                res = subprocess.run(["noctalia", "msg", "theme-mode-get"], timeout=1.0, capture_output=True, check=False)
                if res.returncode == 0:
                    return True
            except Exception:
                pass

        time.sleep(0.15)


def is_shell_locked(shell_name: str, bin_path: str = "") -> bool:
    """Check if the currently running shell is in locked state."""
    norm = normalize_shell_name(shell_name)
    if norm == "nyxuri-shell":
        effective_bin = bin_path or resolve_shell_bin()
        shell_dir = None
        if effective_bin:
            p = Path(effective_bin).resolve()
            if (p.parent / "shell.qml").is_file():
                shell_dir = p.parent
            elif (p.parent.parent / "shell.qml").is_file():
                shell_dir = p.parent.parent
        if shell_dir and (shell_dir / "shell.qml").is_file():
            try:
                res = subprocess.run(
                    ["qs", "-p", str(shell_dir), "ipc", "call", "lock", "isLocked"],
                    timeout=1.0, capture_output=True, text=True, check=False,
                )
                if res.returncode == 0 and res.stdout.strip().lower() in ("true", "1", "locked"):
                    return True
            except Exception:
                pass
    elif norm == "noctalia":
        try:
            res = subprocess.run(
                ["loginctl", "show-session", "self", "-p", "LockedHint"],
                timeout=0.5, capture_output=True, text=True, check=False,
            )
            if "LockedHint=yes" in res.stdout:
                return True
        except Exception:
            pass

    return False


def ensure_compositor_gateway_scripts() -> None:
    """Ensure compositor gateway scripts in niri/scripts match the repository source."""
    from nyxuri.core import get_env
    env = get_env()
    dest_dir = env.config_dir / "niri" / "scripts"
    src_dir = env.configs_src / "niri" / "scripts"
    if not dest_dir.is_dir() or not src_dir.is_dir():
        return

    for script_name in ("session-shell.sh", "shell-action.sh"):
        src = src_dir / script_name
        dest = dest_dir / script_name
        if not src.is_file():
            continue
        need_copy = False
        if not dest.is_file():
            need_copy = True
        else:
            try:
                if src.read_bytes() != dest.read_bytes():
                    need_copy = True
            except OSError:
                need_copy = True

        if need_copy:
            temp_dest = dest.with_name(f".{script_name}.tmp.{os.getpid()}")
            temp_dest.write_bytes(src.read_bytes())
            temp_dest.chmod(0o755)
            temp_dest.replace(dest)
        elif not os.access(dest, os.X_OK):
            dest.chmod(0o755)

    try:
        from nyxuri.core import ensure_nyxuri_shell_symlink
        ensure_nyxuri_shell_symlink()
    except Exception:
        pass


def hot_switch_shell(target: str, custom_bin_override: Optional[str] = None) -> Tuple[bool, str]:
    """Execute end-to-end atomic hot-switch state machine between shells.

    Returns:
        (success, message)
    """
    in_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
    target = normalize_shell_name(target)
    ok, target_bin, err = preflight_shell(target, custom_bin_override)
    if not ok:
        return False, f"Preflight failed: {err}"

    ensure_compositor_gateway_scripts()

    # If no graphical session is present, record target preference and exit cleanly
    if not in_wayland:
        set_shell(target, target_bin if target == "nyxuri-shell" else None)
        return True, f"Recorded preference for {target} (no graphical Wayland session active)"

    # Inventory every running instance of both shells.
    instances = probe_running_shells()
    target_pids = [pid for name, pid in instances if name == target]
    other_instances = [(name, pid) for name, pid in instances if name != target]

    # "Already active" requires a clean field: the target running AND zero
    # instances of the other shell. A target-up-but-side-lingering state is
    # crashed-switch residue, not success.
    if target_pids and not other_instances:
        set_shell(target, target_bin if target == "nyxuri-shell" else None)
        return True, f"{target} is already the active running shell (PID: {target_pids[0]})"

    if target_pids and other_instances:
        removed = []
        for name, pid in other_instances:
            if stop_shell_process(name, pid, shutil.which(name) or "", timeout=2.5):
                removed.append(f"{name}({pid})")
        leftover = [(name, pid) for name, pid in probe_running_shells() if name != target]
        if not leftover:
            set_shell(target, target_bin if target == "nyxuri-shell" else None)
            return True, (f"{target} is the active running shell (PID: {target_pids[0]}); "
                          f"cleaned lingering residue: {', '.join(removed)}")
        # Residue survived the sweep: fall through to a full switch with a
        # fresh view instead of pretending the field is clean.
        instances = probe_running_shells()
        target_pids = [pid for name, pid in instances if name == target]
        current_name, current_pid = (instances[0] if instances else ("none", None))
        other_instances = [(name, pid) for name, pid in instances if name != target]
    else:
        current_name, current_pid = (instances[0] if instances else ("none", None))

    # Stop current running shell
    old_bin = ""
    if current_name == "nyxuri-shell":
        old_bin = resolve_shell_bin()
    elif current_name == "noctalia":
        old_bin = shutil.which("noctalia") or ""

    # 2. Lock safety check: refuse switching while locked
    if is_shell_locked(current_name, old_bin):
        return False, "Cannot switch shell while screen is locked (security invariant violated)"

    if current_pid:
        stop_shell_process(current_name, current_pid, old_bin, timeout=2.5)

    # Field sweep: neither kind may keep a surviving instance before the
    # target spawns. A target-side survivor would double the panels; a
    # current-side survivor would rot into a zombie shell.
    stop_all_shell_instances("nyxuri-shell", target_bin if target == "nyxuri-shell" else old_bin, timeout=1.5)
    stop_all_shell_instances("noctalia", timeout=1.5)

    # Launch target shell
    try:
        new_proc = spawn_shell(target, target_bin)
    except Exception as e:
        # Restore old shell immediately; sweep first so the revival is the
        # only instance on the field.
        stop_all_shell_instances("nyxuri-shell", "", timeout=1.5)
        stop_all_shell_instances("noctalia", timeout=1.5)
        if current_name != "none" and old_bin:
            spawn_shell(current_name, old_bin)
        return False, f"Failed to spawn target shell: {e}"

    # Bounded readiness probe
    is_ready = wait_shell_ready(target, new_proc, target_bin, timeout=4.0)
    if not is_ready:
        # Target failed to report ready or crashed: cleanup the whole field —
        # this spawn AND any residue from earlier switches — so the rollback
        # revives into a clean single-shell state.
        try:
            new_proc.terminate()
            time.sleep(0.2)
            if new_proc.poll() is None:
                new_proc.kill()
        except Exception:
            pass
        stop_all_shell_instances("nyxuri-shell", "", timeout=1.5)
        stop_all_shell_instances("noctalia", timeout=1.5)

        # Rollback: revive old shell
        restored = False
        if current_name != "none" and old_bin:
            try:
                restore_proc = spawn_shell(current_name, old_bin)
                restored = wait_shell_ready(current_name, restore_proc, old_bin, timeout=4.0)
            except Exception:
                pass

        fail_msg = f"Target shell {target} failed readiness probe within 4.0s."
        if restored:
            fail_msg += f" Successfully recovered and rolled back to {current_name}."
        else:
            fail_msg += f" Critical: Failed to restore previous shell {current_name}!"
        return False, fail_msg

    # Successfully verified: commit ledger state
    set_shell(target, target_bin if target == "nyxuri-shell" else None)
    return True, f"Successfully switched to {target} (PID: {new_proc.pid})"
