#!/usr/bin/env python3
"""Container-only feature and negative scenario matrix for the shell.

The runner deliberately exercises only the IPC/process boundary.  It does not
claim keyboard or mouse behaviour; those rows remain ``UNAVAILABLE`` until a
browser or compositor input harness is available.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


STATUS = ("PASS", "PARTIAL", "UNAVAILABLE")
TARGET_NOT_FOUND = "Target not found."
OPTIONAL_COMMANDS = ("key", "lspci", "inotifywait", "ddcutil")
STANDARD_CASES = (
    ("shell.status", "shell", "status", (), "json"),
    ("shell.stage", "shell", "stage", (), "nonempty"),
    ("shell.is_ready", "shell", "isReady", (), "true"),
    ("shell.metrics", "shell", "metrics", (), "json"),
    ("shell.diagnostics", "shell", "diagnostics", (), "json"),
    ("shell.log", "shell", "log", (), "any"),
    ("unit.reload", "unit", "reload", (), "one_of:OK,DEGRADED"),
    ("theme.status", "theme", "status", (), "one_of:dark,light"),
    ("theme.set_dark", "theme", "set", ("dark",), "OK"),
    ("theme.toggle", "theme", "toggle", (), "OK"),
    ("wallpaper.clear", "wallpaper", "clear", (), "one_of:OK,INVALID"),
    ("shortcut_map.toggle", "shortcut-map", "toggle", (), "any"),
    ("spotlight.open", "spotlight", "open", (), "any"),
    ("spotlight.close", "spotlight", "close", (), "any"),
    ("control_center.open", "control-center", "open", (), "OK"),
    ("control_center.close", "control-center", "close", (), "one_of:CLOSED,OK"),
    ("sidebar.dashboard_toggle", "sidebar", "toggle", ("dashboard",), "one_of:DASHBOARD_OPEN,DASHBOARD_CLOSED"),
    ("keystone.dashboard", "keystone", "dashboard", (), "any"),
)


def _result(case_id: str, status: str, *, reason: str = "", **extra: Any) -> dict[str, Any]:
    if status not in STATUS:
        raise ValueError(f"invalid matrix status: {status}")
    row: dict[str, Any] = {"id": case_id, "status": status}
    if reason:
        row["reason"] = reason
    row.update(extra)
    return row


def _report(rows: list[dict[str, Any]], runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    counts = {status: sum(row["status"] == status for row in rows) for status in STATUS}
    overall = "PASS" if rows and counts["PARTIAL"] == counts["UNAVAILABLE"] == 0 else (
        "UNAVAILABLE" if counts["PASS"] == counts["PARTIAL"] == 0 else "PARTIAL"
    )
    report: dict[str, Any] = {"schema": 1, "runner": "feature_matrix", "container_only": True,
                              "status": overall, "summary": {"total": len(rows), "counts": counts}, "rows": rows}
    if runtime is not None:
        report["runtime"] = runtime
    return report


def _matches(value: str, expected: str) -> bool:
    if expected == "any":
        return True
    if expected == "nonempty":
        return bool(value)
    if expected == "true":
        return value.lower() == "true"
    if expected == "json":
        try:
            json.loads(value)
        except (TypeError, ValueError):
            return False
        return True
    if expected.startswith("one_of:"):
        return value in expected.removeprefix("one_of:").split(",")
    return value == expected


def classify_ipc(case_id: str, result: subprocess.CompletedProcess[str], expected: str, elapsed_ms: float) -> dict[str, Any]:
    value = result.stdout.strip()
    if result.returncode == 0 and value == TARGET_NOT_FOUND:
        return _result(
            case_id,
            "UNAVAILABLE",
            reason="IPC target is not loaded in this runtime",
            target_result={"returncode": result.returncode, "stdout": value, "stderr": result.stderr.strip()},
            elapsed_ms=round(elapsed_ms, 3),
        )
    valid = result.returncode == 0 and _matches(value, expected)
    return _result(
        case_id,
        "PASS" if valid else "PARTIAL",
        reason="unexpected IPC result" if not valid else "",
        target_result={"returncode": result.returncode, "stdout": value, "stderr": result.stderr.strip()},
        elapsed_ms=round(elapsed_ms, 3),
    )


def _unknown_target_rejected(result: subprocess.CompletedProcess[str]) -> bool:
    """Quickshell may reject a missing IPC target via exit status or stdout."""
    return result.returncode != 0 or result.stdout.strip() == TARGET_NOT_FOUND


def _ipc(qs: str, shell_dir: str, target: str, method: str, args: tuple[str, ...], env: dict[str, str]) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.perf_counter()
    result = subprocess.run([qs, "-p", shell_dir, "ipc", "call", target, method, *args], env=env,
                            capture_output=True, text=True, check=False, timeout=8)
    return result, (time.perf_counter() - started) * 1000


def _wait_marker(log: Path, process: subprocess.Popen[str], marker: str = "IPC_READY", timeout: float = 20) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if marker in log.read_text(errors="replace"):
            return True
        if process.poll() is not None:
            return False
        time.sleep(0.05)
    return False


def _qml_units(qs: str, shell_dir: str, env: dict[str, str]) -> set[str] | None:
    try:
        result, _ = _ipc(qs, shell_dir, "shell", "metrics", (), env)
        payload = json.loads(result.stdout)
        unit_census = payload.get("qml_census", {}).get("units", {})
        units = unit_census.get("loaded_ids", unit_census.get("ids"))
        return set(units) if result.returncode == 0 and isinstance(units, list) else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def _wait_unit_state(qs: str, shell_dir: str, env: dict[str, str], unit_id: str, enabled: bool,
                     timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        units = _qml_units(qs, shell_dir, env)
        if units is not None and ((unit_id in units) is enabled):
            return True
        time.sleep(0.1)
    return False


def _run_unit_transition(repo: Path, verb: str, env: dict[str, str], uid: int, gid: int) -> subprocess.CompletedProcess[str]:
    """Run the real CLI as an unprivileged container user, preserving its root guard."""
    def drop_privileges() -> None:
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)

    return subprocess.run([str(repo / "nyxuri/launcher.sh"), verb, "shell.bar"], env=env,
                          capture_output=True, text=True, check=False, timeout=20,
                          preexec_fn=drop_privileges)


def _write_projection_ledger(state_home: Path, enabled: bool) -> None:
    ledger = state_home / "nyxuri" / "state.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"plugins": {"shell.bar": {"state": "enabled" if enabled else "disabled"}}}) + "\n",
                      encoding="utf-8")


def _projection_lifecycle_rows(qs: str, shell_dir: str, env: dict[str, str], ready: bool) -> list[dict[str, Any]]:
    """Verify unit off/on projection without pretending it is a kernel transaction."""
    if not ready:
        return [_result(f"lifecycle.projection_{verb}", "UNAVAILABLE", reason="shell not ready") for verb in ("off", "on")]
    state_home = Path(env["XDG_STATE_HOME"])
    rows: list[dict[str, Any]] = []
    for verb, enabled in (("off", False), ("on", True)):
        reload_returncode: int | None = None
        try:
            _write_projection_ledger(state_home, enabled)
            reload_result, _ = _ipc(qs, shell_dir, "unit", "reload", (), env)
            reload_returncode = reload_result.returncode
            delivered = reload_result.returncode == 0 and reload_result.stdout.strip() in ("OK", "DEGRADED")
            projected = delivered and _wait_unit_state(qs, shell_dir, env, "shell.bar", enabled)
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            delivered = False
            projected = False
            error = str(exc)
        else:
            error = ""
        passed = delivered and projected
        rows.append(_result(f"lifecycle.projection_{verb}", "PASS" if passed else "PARTIAL",
                            reason=error or ("unit reload did not converge" if not passed else ""),
                            reload_returncode=reload_returncode,
                            qml_unit_present=enabled if projected else None))
    return rows


def _unit_lifecycle_rows(repo: Path, qs: str, shell_dir: str, env: dict[str, str], ready: bool) -> list[dict[str, Any]]:
    if not ready:
        return [_result(f"lifecycle.unit_{verb}", "UNAVAILABLE", reason="shell not ready") for verb in ("off", "on")]
    try:
        account = pwd.getpwnam("nobody")
    except KeyError:
        return [_result(f"lifecycle.unit_{verb}", "UNAVAILABLE", reason="container has no nobody account") for verb in ("off", "on")]
    if not hasattr(os, "setuid") or not hasattr(os, "setgroups"):
        return [_result(f"lifecycle.unit_{verb}", "UNAVAILABLE", reason="unprivileged subprocess is unsupported") for verb in ("off", "on")]
    if not (repo / "nyxuri/launcher.sh").is_file():
        return [_result(f"lifecycle.unit_{verb}", "UNAVAILABLE", reason="Nyxuri CLI launcher is missing") for verb in ("off", "on")]

    home = Path(env["HOME"])
    state_home = Path(env["XDG_STATE_HOME"])
    if not state_home.is_relative_to(home):
        return [_result(f"lifecycle.unit_{verb}", "UNAVAILABLE", reason="XDG state path escapes the private HOME") for verb in ("off", "on")]
    try:
        os.chown(home, account.pw_uid, account.pw_gid)
        if (home / ".local").is_dir():
            os.chown(home / ".local", account.pw_uid, account.pw_gid)
        state_home.mkdir(parents=True, exist_ok=True)
        os.chown(state_home, account.pw_uid, account.pw_gid)
        ledger_dir = state_home / "nyxuri"
        if ledger_dir.exists():
            os.chown(ledger_dir, account.pw_uid, account.pw_gid)
        user_env = dict(env)
        user_env.update({"HOME": str(home), "XDG_STATE_HOME": str(state_home),
                         "XDG_CONFIG_HOME": env["XDG_CONFIG_HOME"], "XDG_DATA_HOME": env["XDG_DATA_HOME"],
                         "XDG_CACHE_HOME": str(home / ".cache")})
        for key in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
            Path(user_env[key]).mkdir(parents=True, exist_ok=True)
            os.chown(user_env[key], account.pw_uid, account.pw_gid)
    except (OSError, KeyError) as exc:
        return [_result(f"lifecycle.unit_{verb}", "UNAVAILABLE", reason=f"cannot prepare unprivileged XDG tree: {exc}") for verb in ("off", "on")]

    def attempt(verb: str, enabled: bool) -> tuple[bool, dict[str, Any]]:
        try:
            result = _run_unit_transition(repo, verb, user_env, account.pw_uid, account.pw_gid)
        except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError) as exc:
            return False, {"reason": f"Nyxuri {verb} invocation failed: {exc}"}
        if result.returncode != 0:
            lock_path = state_home / "nyxuri" / "nyxuri.lock"
            try:
                lock_diagnostics = {
                    "path": str(lock_path),
                    "state_dir_mode": oct((state_home / "nyxuri").stat().st_mode & 0o777),
                    "state_dir_uid": (state_home / "nyxuri").stat().st_uid,
                    "lock_exists": lock_path.exists(),
                    "lock_mode": oct(lock_path.stat().st_mode & 0o777) if lock_path.exists() else None,
                    "lock_uid": lock_path.stat().st_uid if lock_path.exists() else None,
                    "lock_contents": lock_path.read_text(encoding="utf-8").strip() if lock_path.exists() else None,
                }
            except OSError as exc:
                lock_diagnostics = {"inspection_error": str(exc)}
            return False, {"reason": "Nyxuri transaction failed", "returncode": result.returncode,
                           "stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
                           "lock_diagnostics": lock_diagnostics}
        try:
            reload_result, _ = _ipc(qs, shell_dir, "unit", "reload", (), env)
            delivered = reload_result.returncode == 0 and reload_result.stdout.strip() in ("OK", "DEGRADED")
        except (OSError, subprocess.TimeoutExpired):
            delivered = False
        projected = delivered and _wait_unit_state(qs, shell_dir, env, "shell.bar", enabled)
        try:
            ledger = json.loads((state_home / "nyxuri" / "state.json").read_text(encoding="utf-8"))
            actual = ledger.get("plugins", {}).get("shell.bar", {}).get("state") == ("enabled" if enabled else "disabled")
        except (OSError, ValueError, AttributeError):
            actual = False
        return delivered and projected and actual, {
            "reason": "transaction, IPC projection, or ledger state did not converge" if not (delivered and projected and actual) else "",
            "returncode": result.returncode, "ledger_state": "enabled" if actual and enabled else "disabled" if actual else None,
            "qml_unit_present": enabled if projected else None,
            "stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
        }

    rows: list[dict[str, Any]] = []
    off_ok, off_details = attempt("off", False)
    rows.append(_result("lifecycle.unit_off", "PASS" if off_ok else "PARTIAL", **off_details))
    if not off_ok:
        rows.append(_result("lifecycle.unit_on", "UNAVAILABLE", reason="unit off did not complete; on transition not run"))
        return rows
    on_ok, on_details = attempt("on", True)
    if on_ok:
        rows.append(_result("lifecycle.unit_on", "PASS", **on_details))
    else:
        restored, restore_details = attempt("on", True)
        rows.append(_result("lifecycle.unit_on", "PARTIAL", reason=on_details.get("reason", "unit on did not converge"),
                            **{key: value for key, value in on_details.items() if key != "reason"},
                            recovery={"status": "PASS" if restored else "PARTIAL", **restore_details}))
    return rows


def _start_weston(env: dict[str, str], root: Path) -> subprocess.Popen[str] | None:
    runtime = Path(env["XDG_RUNTIME_DIR"])
    display = env["WAYLAND_DISPLAY"]
    process = subprocess.Popen(["weston", "--backend=headless", "--renderer=pixman", "--no-config",
                                "--socket=" + display, "--idle-time=0"], env=env,
                               stdout=(root / "weston.log").open("w"), stderr=subprocess.STDOUT,
                               start_new_session=True, text=True)
    socket = runtime / display
    for _ in range(200):
        if socket.exists():
            return process
        if process.poll() is not None:
            break
        time.sleep(0.05)
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)
    return None


def _fixture_probe(repo: Path) -> list[dict[str, Any]]:
    """Exercise the checked-in mock-niri fixture with valid and malformed data."""
    fixture = repo / "shell/tests/fixtures/mock-niri"
    if not fixture.is_file():
        return [_result("negative.mock_niri_fixture", "UNAVAILABLE", reason="fixture missing")]
    with tempfile.TemporaryDirectory(prefix="nyxuri-feature-matrix-") as directory:
        config = Path(directory) / "config.kdl"
        config.write_text("layout { gaps 8; }\n", encoding="utf-8")
        good = subprocess.run([str(fixture), "validate", "-c", str(config)], capture_output=True, text=True, check=False)
        config.write_text("INVALID\n", encoding="utf-8")
        bad = subprocess.run([str(fixture), "validate", "-c", str(config)], capture_output=True, text=True, check=False)
    ok = good.returncode == 0 and bad.returncode != 0
    return [_result("negative.malformed_config", "PASS" if ok else "PARTIAL",
                    reason="mock-niri fixture did not reject malformed config" if not ok else "",
                    fixture=str(fixture), valid_returncode=good.returncode, malformed_returncode=bad.returncode)]


def run_matrix(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo).resolve()
    rows: list[dict[str, Any]] = []
    rows.extend(_fixture_probe(repo))
    rows.extend([_result("interaction.keyboard", "UNAVAILABLE", reason="requires browser/input harness"),
                 _result("interaction.mouse", "UNAVAILABLE", reason="requires browser/input harness")])
    container_ok = os.environ.get("NYXURI_CONTAINER") == "1" or Path("/.dockerenv").exists()
    required = [shutil.which("qs"), shutil.which("weston")]
    if not container_ok:
        rows.extend(_result(case[0], "UNAVAILABLE", reason="container-only runner; set NYXURI_CONTAINER=1") for case in STANDARD_CASES)
        rows.extend([_result("lifecycle.unit_off", "UNAVAILABLE", reason="container runtime not started"),
                     _result("lifecycle.unit_on", "UNAVAILABLE", reason="container runtime not started"),
                     _result("negative.missing_optional_commands", "UNAVAILABLE", reason="container runtime not started"),
                     _result("negative.unknown_ipc_target", "UNAVAILABLE", reason="container runtime not started")])
        return _report(rows)
    if any(item is None for item in required):
        reason = "missing runtime command: " + ", ".join(name for name, value in zip(("qs", "weston"), required) if value is None)
        rows.extend(_result(case[0], "UNAVAILABLE", reason=reason) for case in STANDARD_CASES)
        rows.extend([_result("lifecycle.unit_off", "UNAVAILABLE", reason=reason), _result("lifecycle.unit_on", "UNAVAILABLE", reason=reason),
                     _result("negative.missing_optional_commands", "UNAVAILABLE", reason=reason), _result("negative.unknown_ipc_target", "UNAVAILABLE", reason=reason)])
        return _report(rows)

    qs = str(required[0])
    root = Path(tempfile.mkdtemp(prefix="nyxuri-feature-matrix-"))
    env = dict(os.environ)
    env.update({"HOME": str(root / "home"), "XDG_RUNTIME_DIR": str(root / "runtime"),
                "XDG_CACHE_HOME": str(root / "home" / ".cache"), "XDG_CONFIG_HOME": str(root / "home" / ".config"),
                "XDG_DATA_HOME": str(root / "home" / ".local/share"), "XDG_STATE_HOME": str(root / "home" / ".local/state"),
                "WAYLAND_DISPLAY": "nyxuri-feature-wayland", "QT_QPA_PLATFORM": "wayland",
                "QT_QUICK_BACKEND": "software", "QSG_RHI_BACKEND": "software"})
    for key in ("HOME", "XDG_RUNTIME_DIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o755)
    weston = _start_weston(env, root)
    if weston is None:
        rows.extend(_result(case[0], "UNAVAILABLE", reason="private Weston did not start") for case in STANDARD_CASES)
        return _report(rows)
    shell_dir = str(args.shell)
    log = root / "shell.log"
    shell = subprocess.Popen([shell_dir + "/nyxuri-shell", "-v"], env=env, stdout=log.open("w"), stderr=subprocess.STDOUT,
                             start_new_session=True, text=True)
    try:
        ready = _wait_marker(log, shell)
        if not ready:
            rows.extend(_result(case[0], "UNAVAILABLE", reason="shell did not reach IPC_READY") for case in STANDARD_CASES)
        else:
            for case_id, target, method, ipc_args, expected in STANDARD_CASES:
                try:
                    result, elapsed = _ipc(qs, shell_dir, target, method, ipc_args, env)
                    rows.append(classify_ipc(case_id, result, expected, elapsed))
                except (OSError, subprocess.TimeoutExpired) as exc:
                    rows.append(_result(case_id, "PARTIAL", reason=f"IPC invocation failed: {exc}"))
            try:
                result, elapsed = _ipc(qs, shell_dir, "missing-target", "ping", (), env)
                value = result.stdout.strip()
                rejected = _unknown_target_rejected(result)
                rows.append(_result(
                    "negative.unknown_ipc_target",
                    "PASS" if rejected else "PARTIAL",
                    reason="unknown target unexpectedly succeeded" if not rejected else "",
                    target_result={"returncode": result.returncode, "stdout": value, "stderr": result.stderr.strip()},
                    elapsed_ms=round(elapsed, 3),
                ))
            except (OSError, subprocess.TimeoutExpired) as exc:
                rows.append(_result("negative.unknown_ipc_target", "PARTIAL", reason=str(exc)))
            for case_id, target, method, ipc_args, expected in (
                ("negative.invalid_theme", "theme", "set", ("sepia",), "INVALID_MODE"),
                ("negative.invalid_wallpaper", "wallpaper", "set", ("/does/not/exist",), "INVALID"),
                ("negative.invalid_sidebar", "sidebar", "toggle", ("not-a-sidebar",), "INVALID_SIDE"),
                ("negative.invalid_spotlight_mode", "spotlight", "openMode", ("not-a-mode",), "INVALID_MODE"),
            ):
                try:
                    result, elapsed = _ipc(qs, shell_dir, target, method, ipc_args, env)
                    rows.append(classify_ipc(case_id, result, expected, elapsed))
                except (OSError, subprocess.TimeoutExpired) as exc:
                    rows.append(_result(case_id, "PARTIAL", reason=f"IPC invocation failed: {exc}"))
            rows.extend(_projection_lifecycle_rows(qs, shell_dir, env, ready))
            rows.extend(_unit_lifecycle_rows(repo, qs, shell_dir, env, ready))
            optional_bin = Path(tempfile.mkdtemp(prefix="nyxuri-no-optional-"))
            try:
                missing_env = dict(env); missing_env["PATH"] = str(optional_bin)
                absent = [name for name in OPTIONAL_COMMANDS if shutil.which(name, path=missing_env["PATH"]) is None]
                log_text = log.read_text(errors="replace")
                observed = [name for name in absent if name in log_text and "Process failed" in log_text]
                optional_status = "PASS" if ready and len(absent) == len(OPTIONAL_COMMANDS) and len(observed) > 0 else "PARTIAL"
                rows.append(_result("negative.missing_optional_commands", optional_status,
                                    reason="missing commands were not observed as graceful optional failures" if optional_status != "PASS" else "",
                                    commands=OPTIONAL_COMMANDS, absent=absent, observed_failures=observed))
            finally:
                shutil.rmtree(optional_bin, ignore_errors=True)
    finally:
        try:
            os.killpg(shell.pid, signal.SIGTERM)
            shell.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            shell.kill()
        try:
            os.killpg(weston.pid, signal.SIGTERM)
            weston.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            weston.kill()
        shutil.rmtree(root, ignore_errors=True)
    return _report(rows, {"shell": shell_dir, "optional_commands": OPTIONAL_COMMANDS})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path("/workspace"))
    parser.add_argument("--shell", type=Path, default=Path("/workspace/shell"))
    args = parser.parse_args()
    report = run_matrix(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
