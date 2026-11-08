#!/usr/bin/env python3
"""Run the container-only Quickshell compatibility probes used by the benchmark."""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LOCK_PATH = Path(__file__).with_name("benchmark-lock.json")


def _ipc_probe(qs: str, root: Path, environment: dict[str, str]) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "shell.qml").write_text(
        "import QtQuick\nimport Quickshell\nimport Quickshell.Io\n"
        'ShellRoot { IpcHandler { target: "compat"; function ping(): string { return "pong" } } '\
        'IpcHandler { target: "unit"; property bool enabled: true; function reload(): string { return "OK" } '\
        'function off(): string { enabled = false; return enabled ? "ON" : "OFF" } '\
        'function on(): string { enabled = true; return enabled ? "ON" : "OFF" } '\
        'function state(): string { return enabled ? "ON" : "OFF" } } }\n',
        encoding="utf-8",
    )
    log = root / "ipc.log"
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            [qs, "-p", str(root), "--no-duplicate", "-v"],
            env=environment, stdout=stream, stderr=subprocess.STDOUT,
            start_new_session=True, text=True,
        )
    try:
        ready = False
        for _ in range(120):
            text = log.read_text(errors="replace")
            if "Configuration Loaded" in text or "IpcHandler" in text:
                ready = True
                break
            if process.poll() is not None:
                break
            time.sleep(0.05)
        calls: dict[str, object] = {}
        for target, method, expected, key in (
            ("compat", "ping", "pong", "compat.ping"),
            ("unit", "reload", "OK", "unit.reload"),
            ("unit", "off", "OFF", "unit.off"),
            ("unit", "state", "OFF", "unit.state_after_off"),
            ("unit", "on", "ON", "unit.on"),
            ("unit", "state", "ON", "unit.state_after_on"),
        ):
            result = subprocess.run(
                [qs, "-p", str(root), "ipc", "call", target, method],
                env=environment, capture_output=True, text=True, check=False,
            )
            value = result.stdout.strip()
            calls[key] = {
                "returncode": result.returncode,
                "value": value,
                "valid": ready and result.returncode == 0 and value == expected,
            }
        return {"ready": ready, "calls": calls}
    finally:
        try:
            process.terminate()
            process.wait(timeout=3)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            process.kill()


def _calls_ok(probe: dict[str, object]) -> bool:
    calls = probe.get("calls")
    return isinstance(calls, dict) and all(
        isinstance(item, dict) and item.get("valid") is True for item in calls.values()
    )


def _start_compositor(environment: dict[str, str], root: Path) -> tuple[subprocess.Popen[str], Path]:
    runtime = Path(environment["XDG_RUNTIME_DIR"])
    runtime.mkdir(parents=True, exist_ok=True)
    os.chmod(runtime, 0o700)
    display = "nyxuri-compat-wayland"
    environment["WAYLAND_DISPLAY"] = display
    socket = runtime / display
    log_path = root / "weston.log"
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        ["weston", "--backend=headless", "--renderer=pixman", "--no-config",
         "--socket=" + display, "--idle-time=0"],
        env=environment, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True, text=True,
    )
    for _ in range(200):
        if socket.exists():
            log.close()
            return process, socket
        if process.poll() is not None:
            break
        time.sleep(0.05)
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)
    log.close()
    raise RuntimeError(f"private compatibility Weston did not start; see {log_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--channel", choices=("old", "new"), default=os.environ.get("NYXURI_QUICKSHELL_CHANNEL", "new"))
    args = parser.parse_args()
    if os.environ.get("NYXURI_CONTAINER") != "1":
        parser.error("compatibility probes may only run inside benchmark-shell.py's private container")
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    qs = shutil.which("qs")
    if not qs:
        parser.error("qs is required inside the benchmark container")
    environment = dict(os.environ)
    environment.setdefault("XDG_RUNTIME_DIR", "/tmp/nyxuri-runtime")
    environment.setdefault("XDG_CACHE_HOME", "/tmp/nyxuri-cache")
    environment.setdefault("XDG_CONFIG_HOME", "/tmp/nyxuri-config")
    environment.setdefault("XDG_DATA_HOME", "/tmp/nyxuri-data")
    environment.setdefault("XDG_STATE_HOME", "/tmp/nyxuri-state")
    environment.setdefault("QT_QPA_PLATFORM", "wayland")
    environment.setdefault("QT_QUICK_BACKEND", "software")
    environment.setdefault("QSG_RHI_BACKEND", "software")
    root = Path(tempfile.mkdtemp(prefix="nyxuri-compat-"))
    compositor: subprocess.Popen[str] | None = None
    try:
        compositor, _ = _start_compositor(environment, root)
        ipc = _ipc_probe(qs, root / "ipc", environment)
        cache_root = Path(environment["XDG_CACHE_HOME"]) / "quickshell" / "qmlcache"
        cache_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(cache_root, ignore_errors=True)
        cold = _ipc_probe(qs, root / "qmlcache-cold", environment)
        cache_after_cold = cache_root.exists()
        warm = _ipc_probe(qs, root / "qmlcache-warm", environment)
        loader_script = Path(__file__).with_name("spike-loader-registry.py")
        loader = subprocess.run(
            [sys.executable, str(loader_script), "--all", "--runs", "1"],
            env=environment, capture_output=True, text=True, check=False,
        )
        loader_text = loader.stdout + loader.stderr
        loader_matrix = {
            "returncode": loader.returncode,
            "file_url": "SUMMARY url-file:" in loader_text and "OK 1/1" in loader_text,
            "external_file_url": "SUMMARY external:" in loader_text and "OK 1/1" in loader_text,
            "output": loader_text,
        }
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        channel_info = lock.get("quickshell_old" if args.channel == "old" else "quickshell_new", {})
        output = {
            "schema": 1,
            "channel": args.channel,
            "locked_package": channel_info,
            "quickshell": subprocess.run([qs, "--version"], capture_output=True, text=True, check=False).stdout.strip(),
            "loader_matrix": loader_matrix,
            "ipc": ipc,
            "qmlcache": {
                "cold": cold,
                "warm": warm,
                "cache_created_after_cold": cache_after_cold,
            },
            "success": bool(
                ipc.get("ready")
                and loader_matrix["returncode"] == 0
                and loader_matrix["file_url"]
                and loader_matrix["external_file_url"]
                and _calls_ok(ipc)
                and _calls_ok(cold)
                and _calls_ok(warm)
            ),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
        print(json.dumps(output, ensure_ascii=True, indent=2))
        return 0 if output["success"] else 1
    finally:
        if compositor is not None:
            try:
                os.killpg(compositor.pid, signal.SIGTERM)
                compositor.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(compositor.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
