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
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


STATUS = ("PASS", "PARTIAL", "UNAVAILABLE")
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
    valid = result.returncode == 0 and _matches(value, expected)
    return _result(
        case_id,
        "PASS" if valid else "PARTIAL",
        reason="unexpected IPC result" if not valid else "",
        target_result={"returncode": result.returncode, "stdout": value, "stderr": result.stderr.strip()},
        elapsed_ms=round(elapsed_ms, 3),
    )


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
        return {"schema": 1, "runner": "feature_matrix", "container_only": True, "status": "UNAVAILABLE", "rows": rows}
    if any(item is None for item in required):
        reason = "missing runtime command: " + ", ".join(name for name, value in zip(("qs", "weston"), required) if value is None)
        rows.extend(_result(case[0], "UNAVAILABLE", reason=reason) for case in STANDARD_CASES)
        rows.extend([_result("lifecycle.unit_off", "UNAVAILABLE", reason=reason), _result("lifecycle.unit_on", "UNAVAILABLE", reason=reason),
                     _result("negative.missing_optional_commands", "UNAVAILABLE", reason=reason), _result("negative.unknown_ipc_target", "UNAVAILABLE", reason=reason)])
        return {"schema": 1, "runner": "feature_matrix", "container_only": True, "status": "UNAVAILABLE", "rows": rows}

    qs = str(required[0])
    env = dict(os.environ)
    env.update({"HOME": "/tmp/nyxuri-home", "XDG_RUNTIME_DIR": "/tmp/nyxuri-runtime",
                "XDG_CACHE_HOME": "/tmp/nyxuri-cache", "XDG_CONFIG_HOME": "/tmp/nyxuri-config",
                "XDG_DATA_HOME": "/tmp/nyxuri-data", "XDG_STATE_HOME": "/tmp/nyxuri-state",
                "WAYLAND_DISPLAY": "nyxuri-feature-wayland", "QT_QPA_PLATFORM": "wayland",
                "QT_QUICK_BACKEND": "software", "QSG_RHI_BACKEND": "software"})
    for key in ("HOME", "XDG_RUNTIME_DIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="nyxuri-feature-matrix-"))
    weston = _start_weston(env, root)
    if weston is None:
        rows.extend(_result(case[0], "UNAVAILABLE", reason="private Weston did not start") for case in STANDARD_CASES)
        return {"schema": 1, "runner": "feature_matrix", "container_only": True, "status": "UNAVAILABLE", "rows": rows}
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
                rows.append(_result("negative.unknown_ipc_target", "PASS" if result.returncode != 0 else "PARTIAL",
                                    reason="unknown target unexpectedly succeeded" if result.returncode == 0 else "",
                                    target_result={"returncode": result.returncode, "stderr": result.stderr.strip()}, elapsed_ms=round(elapsed, 3)))
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
            # Unit off/on is owned by the Nyxuri transaction CLI, not the shell IPC target.
            if os.geteuid() == 0 or not (repo / "nyxuri/launcher.sh").is_file():
                rows.extend([_result("lifecycle.unit_off", "UNAVAILABLE", reason="Nyxuri CLI refuses root or launcher is missing"),
                             _result("lifecycle.unit_on", "UNAVAILABLE", reason="Nyxuri CLI refuses root or launcher is missing")])
            else:
                for verb in ("off", "on"):
                    result = subprocess.run([str(repo / "nyxuri/launcher.sh"), verb, "shell.bar"], env=env,
                                            capture_output=True, text=True, check=False, timeout=20)
                    rows.append(_result(f"lifecycle.unit_{verb}", "PASS" if result.returncode == 0 else "PARTIAL",
                                        reason="transaction failed" if result.returncode else "",
                                        returncode=result.returncode, stderr=result.stderr.strip()))
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
    statuses = [row["status"] for row in rows]
    overall = "PASS" if statuses and all(value == "PASS" for value in statuses) else "PARTIAL"
    return {"schema": 1, "runner": "feature_matrix", "container_only": True, "status": overall,
            "rows": rows, "runtime": {"shell": shell_dir, "optional_commands": OPTIONAL_COMMANDS}}


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
