"""管理双 Shell 运行态、就绪探测和 Wayland 会话中的热切换。

按 P0-06 状态机完成 Noctalia 与 Nyxuri Shell 的交接：
1. 预检目标入口、平台运行依赖、字体与 QML 导入。
2. 检查锁屏状态。
3. 请求旧实例优雅退出，等待上限 2.5s，超时后强制终止。
4. 在后台启动新实例。
5. 按目标预算探测就绪：Noctalia 30s，Nyxuri Shell 4s。
6. 成功后提交账本；失败时回滚并恢复旧 Shell。
"""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from nyxuri.kernel.ledger import active_shell, custom_shell_bin, set_shell


def normalize_shell_name(name: str) -> str:
    """Normalize shell slot names, accepting aliases 'custom' and 'nyxuri'."""
    s = str(name).strip().lower()
    if s in ("custom", "nyxuri", "nyxuri-shell"):
        return "nyxuri-shell"
    if s == "noctalia":
        return "noctalia"
    return s


def find_default_custom_bin() -> str:
    """先从仓库根目录查找 Shell 入口，再回退到 PATH。"""
    # 本文件位于 nyxuri/desktop/，向上三层才是包含 shell/ 的仓库根目录。
    repo_root = Path(__file__).resolve().parents[2]
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

    from_env = os.environ.get("NYXURI_CUSTOM_SHELL_BIN")
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
    """验证目标入口与实际运行能力；失败时调用方尚未停止旧Shell。

    返回 (ok, resolved_binary, error_reason)。Nyxuri Shell会执行隔离的无窗口
    QML导入探针；Noctalia仍在实际切换后通过IPC就绪探测确认桌面实例。
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

    from nyxuri.desktop.shell_runtime import preflight_runtime
    error = preflight_runtime(Path(resolved))
    if error:
        return False, resolved, error
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
    # Exclude only this process — never the parent. When the RUNNING shell
    # dispatches a unit switch (UnitControlService), this CLI's parent IS
    # the qs instance the bridge must notify; excluding getppid() turned
    # every shell-originated unit-changed delivery into a silent no-op
    # (2026-10-17 acceptance regression: toggles landed the ledger but the
    # desktop never re-projected). The wrapper exec's into qs, so a parent
    # is never a lingering wrapper script, and non-shell parents (terminals,
    # test runners) are filtered by classify() anyway.
    my_pids = {os.getpid()}

    def nyxuri_shell_dirs() -> "set[Path]":
        dirs: "set[Path]" = set()
        # 同时识别显式配置入口和当前源码树，避免源码启动实例漏出切换清理范围。
        for raw in (resolve_custom_bin(), str(Path(__file__).resolve().parents[2] / "shell")):
            if not raw:
                continue
            path = Path(raw)
            for probe in (path, path.parent):
                try:
                    resolved = probe.resolve()
                except OSError:
                    continue
                if resolved.is_dir():
                    dirs.add(resolved)
        return dirs

    known_shell_dirs = nyxuri_shell_dirs()

    def qs_profile(args: "list[str]") -> "str | None":
        for index, arg in enumerate(args):
            if arg == "-p" and index + 1 < len(args):
                return args[index + 1]
            if arg.startswith("-p") and len(arg) > 2:
                return arg[2:]
            if arg.startswith("--path="):
                return arg.split("=", 1)[1]
        return None

    def classify(args: "list[str]") -> "str | None":
        prog = Path(args[0]).name
        cmd = " ".join(args)
        if any(bad in cmd for bad in ["nyxuri shell", "test_shell", "pytest", "shell_switcher"]):
            return None
        if prog in ("qs", "quickshell", "nyxuri-shell"):
            if any(sub in args for sub in ["ipc", "kill", "--stop", "--check-ready", "--status", "--stage"]):
                return None
            if prog == "nyxuri-shell":
                return "nyxuri-shell"
            profile = qs_profile(args)
            if profile:
                try:
                    if Path(profile).resolve() in known_shell_dirs:
                        return "nyxuri-shell"
                except OSError:
                    pass
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
    # 空 XDG 值与未设置相同；日志不能因空字符串而写入当前工作目录。
    state_base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    log_dir = state_base / "nyxuri"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / f"{norm}-session.log", "a", encoding="utf-8")
    cmd = [bin_path]
    return subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
    )


def _shell_ready_timeout(shell_name: str) -> float:
    """目标与回滚共用预算；为 Noctalia 约 25 秒的单次 D-Bus 初始化等待留出启动余量。"""
    return 30.0 if normalize_shell_name(shell_name) == "noctalia" else 4.0


def wait_shell_ready(shell_name: str, proc: subprocess.Popen, bin_path: str,
                     timeout: Optional[float] = None) -> bool:
    """在单调时钟总预算内等待真实 IPC 响应，进程存活本身不代表就绪。

    每次 IPC 的超时和轮询间隔都受剩余预算限制；不会在最后一次探测额外等待
    完整的 0.5/1 秒。进程退出、未知目标或预算耗尽均明确返回 False。
    """
    norm = normalize_shell_name(shell_name)
    if norm == "nyxuri-shell":
        command, probe_limit = [bin_path, "--check-ready"], 0.5
    elif norm == "noctalia":
        # Noctalia 没有 ping；theme-mode-get 必须由真正运行的服务回应。
        command, probe_limit = ["noctalia", "msg", "theme-mode-get"], 1.0
    else:
        return False
    budget = _shell_ready_timeout(norm) if timeout is None else timeout
    deadline = time.monotonic() + max(0.0, budget)
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            res = subprocess.run(command, timeout=min(probe_limit, remaining),
                                 capture_output=True, check=False)
            if res.returncode == 0:
                return time.monotonic() <= deadline
        except (OSError, subprocess.SubprocessError):
            pass
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(0.15, remaining))
    return False


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
    """只检查网关是否已经由 Niri 事务部署，不在 Shell 切换时改写配置。

    网关升级属于 Niri 的 refresh；切换 Shell 不能先对齐源码再发现启动失败，
    也不能把用户编辑的脚本当成旧版本覆盖。
    """
    from nyxuri.core import get_env
    env = get_env()
    dest_dir = env.config_dir / "niri" / "scripts"
    if not dest_dir.is_dir():
        return
    for script_name in ("session-shell.sh", "shell-action.sh"):
        script = dest_dir / script_name
        if not script.is_file() or not os.access(script, os.X_OK):
            raise RuntimeError(f"Compositor gateway unavailable; refresh niri: {script}")


def capture_active_theme_state(current_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Capture the runtime theme mode (dark/light) and wallpaper path from current shell."""
    mode = None
    wallpaper = None
    norm = normalize_shell_name(current_name)

    # 1. Capture theme mode
    if norm == "noctalia" and shutil.which("noctalia"):
        try:
            res = subprocess.run(["noctalia", "msg", "theme-mode-get"], timeout=1.0, capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip() in ("dark", "light"):
                mode = res.stdout.strip()
        except Exception:
            pass
    elif norm == "nyxuri-shell":
        try:
            from nyxuri.desktop.theme import _nyxuri_shell_ipc
            val = _nyxuri_shell_ipc(["theme", "status"], timeout=1.0)
            if val in ("dark", "light"):
                mode = val
        except Exception:
            pass

    if mode is None:
        try:
            from nyxuri.core import get_env
            cfg_file = get_env().config_dir / "nyxuri" / "config.json"
            if cfg_file.is_file():
                import json
                with cfg_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    val = data.get("theme", {}).get("mode")
                    if val in ("dark", "light"):
                        mode = val
        except Exception:
            pass

    if mode is None:
        try:
            from nyxuri.desktop.theme import _mode_from_system
            mode = _mode_from_system()
        except Exception:
            mode = "dark"

    # 2. Capture wallpaper
    if norm == "noctalia" and shutil.which("noctalia"):
        try:
            res = subprocess.run(["noctalia", "msg", "wallpaper-get"], timeout=1.0, capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                wp = res.stdout.strip()
                if os.path.exists(wp):
                    wallpaper = wp
        except Exception:
            pass
    elif norm == "nyxuri-shell":
        try:
            from nyxuri.core import get_env
            cfg_file = get_env().config_dir / "nyxuri" / "config.json"
            if cfg_file.is_file():
                import json
                with cfg_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    wp_data = data.get("wallpaper", {})
                    wp = ""
                    if mode == "dark":
                        wp = wp_data.get("pathDark") or wp_data.get("path")
                    elif mode == "light":
                        wp = wp_data.get("pathLight") or wp_data.get("path")
                    else:
                        wp = wp_data.get("path")
                    if wp and os.path.exists(wp):
                        wallpaper = wp
        except Exception:
            pass

    if not wallpaper:
        try:
            from nyxuri.core import get_env
            env = get_env()
            for candidate in (env.state_dir / "current_wallpaper",
                              env.config_dir / "nyxuri" / "current_wallpaper",
                              Path.home() / ".cache" / "current_wallpaper"):
                if candidate.is_file():
                    content = candidate.read_text(encoding="utf-8").strip()
                    if content and os.path.exists(content):
                        wallpaper = content
                        break
        except Exception:
            pass

    return mode, wallpaper


def handoff_theme_state(target: str, mode: Optional[str], wallpaper: Optional[str]) -> None:
    """Propagate the captured theme mode and wallpaper into the newly ready target shell."""
    norm = normalize_shell_name(target)
    if norm == "nyxuri-shell":
        try:
            from nyxuri.desktop.theme import _nyxuri_shell_ipc
            if mode in ("dark", "light"):
                _nyxuri_shell_ipc(["theme", "set", mode], timeout=2.0)
            if wallpaper and os.path.exists(wallpaper):
                _nyxuri_shell_ipc(["wallpaper", "set", wallpaper], timeout=2.0)
        except Exception:
            pass
    elif norm == "noctalia" and shutil.which("noctalia"):
        try:
            if mode in ("dark", "light"):
                subprocess.run(["noctalia", "msg", "theme-mode-set", mode], timeout=2.0, capture_output=True, check=False)
            if wallpaper and os.path.exists(wallpaper):
                subprocess.run(["noctalia", "msg", "wallpaper-set", wallpaper], timeout=2.0, capture_output=True, check=False)
        except Exception:
            pass

    try:
        from nyxuri.desktop.theme import sync
        sync(mode or "sync")
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

    def commit_running_bin() -> None:
        if target != "nyxuri-shell":
            set_shell(target, None)
            return
        set_shell(target, custom_shell_bin() or target_bin)

    # "Already active" requires a clean field: the target running AND zero
    # instances of the other shell. A target-up-but-side-lingering state is
    # crashed-switch residue, not success.
    if target_pids and not other_instances:
        commit_running_bin()
        return True, f"{target} is already the active running shell (PID: {target_pids[0]})"

    if target_pids and other_instances:
        removed = []
        for name, pid in other_instances:
            if stop_shell_process(name, pid, shutil.which(name) or "", timeout=2.5):
                removed.append(f"{name}({pid})")
        leftover = [(name, pid) for name, pid in probe_running_shells() if name != target]
        if not leftover:
            commit_running_bin()
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

    # Capture active theme mode and wallpaper before terminating current shell
    captured_mode, captured_wallpaper = capture_active_theme_state(current_name)

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
            try:
                restore_proc = spawn_shell(current_name, old_bin)
                restore_timeout = _shell_ready_timeout(current_name)
                restored = wait_shell_ready(current_name, restore_proc, old_bin, timeout=restore_timeout)
                if not restored:
                    return False, (f"Failed to spawn target shell: {e}; restore of {current_name} "
                                   f"failed readiness probe within {restore_timeout:.1f}s.")
                handoff_theme_state(current_name, captured_mode, captured_wallpaper)
                return False, (f"Failed to spawn target shell: {e}; successfully recovered {current_name} "
                               f"(readiness budget: {restore_timeout:.1f}s).")
            except Exception as restore_error:
                return False, f"Failed to spawn target shell: {e}; restore of {current_name} also failed: {restore_error}"
        return False, f"Failed to spawn target shell: {e}"

    # 新目标与失败回滚都按各自 Shell 的预算等待，不能把慢启动误判成崩溃。
    ready_timeout = _shell_ready_timeout(target)
    is_ready = wait_shell_ready(target, new_proc, target_bin, timeout=ready_timeout)
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
        restore_timeout = _shell_ready_timeout(current_name)
        if current_name != "none" and old_bin:
            try:
                restore_proc = spawn_shell(current_name, old_bin)
                restored = wait_shell_ready(current_name, restore_proc, old_bin, timeout=restore_timeout)
            except Exception:
                pass

        fail_msg = f"Target shell {target} failed readiness probe within {ready_timeout:.1f}s."
        if restored:
            handoff_theme_state(current_name, captured_mode, captured_wallpaper)
            fail_msg += f" Successfully recovered and rolled back to {current_name} (readiness budget: {restore_timeout:.1f}s)."
        else:
            fail_msg += f" Critical: Failed to restore previous shell {current_name} within {restore_timeout:.1f}s!"
        return False, fail_msg

    # Successfully verified: commit ledger state and hand off theme state
    set_shell(target, target_bin if target == "nyxuri-shell" else None)
    handoff_theme_state(target, captured_mode, captured_wallpaper)
    return True, f"Successfully switched to {target} (PID: {new_proc.pid}, readiness budget: {ready_timeout:.1f}s)"
