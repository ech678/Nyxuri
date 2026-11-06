#!/usr/bin/env python3
"""Orchestrate benchmark scenarios in the prepared Nix runtime."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

from benchmark_runtime import IPC_METHODS, RunResult, _process_tree, _quantile, _run_process, _terminate

LOCK_PATH = Path(__file__).with_name("benchmark-lock.json")

ACTION_CASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("spotlight_toggle", ("spotlight", "toggle")),
    ("control_center_toggle", ("control-center", "toggle", "")),
    ("sidebar_dashboard_toggle", ("sidebar", "toggle", "dashboard")),
    ("keystone_dashboard", ("keystone", "dashboard")),
    ("wallpaper_random", ("wallpaper", "random")),
)


def ipc_benchmark(
    environment: dict[str, str],
    log_dir: Path,
    count: int,
    config_path: str,
    target: str,
    methods: tuple[str, ...],
    marker: str,
    launch_command: list[str],
) -> dict[str, dict[str, float | int]]:
    log_path = log_dir / "ipc-host.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            launch_command, env=environment,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True,
        )
        try:
            for _ in range(300):
                log.flush()
                if marker in log_path.read_text(errors="replace"):
                    break
                time.sleep(0.05)
            results: dict[str, dict[str, float | int]] = {}
            for method in methods:
                values: list[float] = []
                errors = 0
                for _ in range(count):
                    started = time.perf_counter()
                    result = subprocess.run(
                        ["qs", "-p", config_path, "ipc", "call", target, method],
                        env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, check=False,
                    )
                    values.append((time.perf_counter() - started) * 1000)
                    errors += int(result.returncode != 0)
                results[method] = {
                    "p50_ms": float(_quantile(values, 0.50) or 0),
                    "p95_ms": float(_quantile(values, 0.95) or 0),
                    "p99_ms": float(_quantile(values, 0.99) or 0),
                    "min_ms": min(values), "max_ms": max(values), "errors": errors,
                }
            return results
        finally:
            _terminate(process)


def source_profile() -> dict[str, int]:
    root = Path("/workspace/shell")
    files = [path for path in root.rglob("*") if path.is_file() and path.suffix in {".qml", ".js"}]
    contents = [path.read_text(errors="replace") for path in files]
    joined = "\n".join(contents)
    return {
        "qml_js_files": len(files), "qml_files": sum(path.suffix == ".qml" for path in files),
        "js_files": sum(path.suffix == ".js" for path in files),
        "source_bytes": sum(path.stat().st_size for path in files),
        "source_lines": sum(text.count("\n") + 1 for text in contents),
        "imports": len(re.findall(r"^\s*import\s+", joined, re.MULTILINE)),
        "singletons": len(re.findall(r"^\s*pragma Singleton", joined, re.MULTILINE)),
        "timers": len(re.findall(r"^\s*Timer\s*\{", joined, re.MULTILINE)),
        "processes": len(re.findall(r"^\s*Process\s*\{", joined, re.MULTILINE)),
        "fileviews": len(re.findall(r"^\s*FileView\s*\{", joined, re.MULTILINE)),
        "loaders": len(re.findall(r"^\s*Loader\s*\{", joined, re.MULTILINE)),
        "repeaters": len(re.findall(r"^\s*Repeater\s*\{", joined, re.MULTILINE)),
        "destruction_hooks": len(re.findall(r"Component\.onDestruction", joined)),
    }


def numeric_run(run: RunResult) -> dict[str, object]:
    data = asdict(run)
    data["log_path"] = str(Path(str(data["log_path"])).relative_to(Path("/results")))
    return data


def action_benchmark(environment: dict[str, str], log_dir: Path, count: int) -> dict[str, dict[str, float | int]]:
    log_path = log_dir / "actions-host.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["/workspace/shell/nyxuri-shell", "-v"], env=environment,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True,
        )
        try:
            for _ in range(300):
                log.flush()
                if "IPC_READY" in log_path.read_text(errors="replace"):
                    break
                time.sleep(0.05)
            results: dict[str, dict[str, float | int]] = {}
            for name, argv in ACTION_CASES:
                values: list[float] = []
                errors = 0
                peak_rss = 0
                peak_processes = 0
                for _ in range(count):
                    started = time.perf_counter()
                    result = subprocess.run(
                        ["qs", "-p", "/workspace/shell", "ipc", "call", *argv],
                        env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, check=False,
                    )
                    values.append((time.perf_counter() - started) * 1000)
                    errors += int(result.returncode != 0)
                    time.sleep(0.1)
                    sample = _process_tree(process.pid)
                    if sample is not None:
                        peak_rss = max(peak_rss, sample.rss_kb)
                        peak_processes = max(peak_processes, sample.process_count)
                results[name] = {
                    "p50_ms": float(_quantile(values, 0.50) or 0),
                    "p95_ms": float(_quantile(values, 0.95) or 0),
                    "p99_ms": float(_quantile(values, 0.99) or 0),
                    "min_ms": min(values), "max_ms": max(values), "errors": errors,
                    "peak_rss_kb": peak_rss, "peak_processes": peak_processes,
                }
            return results
        finally:
            _terminate(process)


def environment() -> dict[str, str]:
    runtime = Path("/tmp/nyxuri-runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    os.chmod(runtime, 0o700)
    values = {
        "HOME": "/tmp/nyxuri-home", "XDG_RUNTIME_DIR": str(runtime),
        "XDG_CACHE_HOME": "/tmp/nyxuri-cache", "XDG_CONFIG_HOME": "/tmp/nyxuri-config",
        "XDG_DATA_HOME": "/tmp/nyxuri-data", "XDG_STATE_HOME": "/tmp/nyxuri-state",
        "WAYLAND_DISPLAY": "nyxuri-benchmark-wayland", "QT_QPA_PLATFORM": "wayland",
        "QT_QUICK_BACKEND": "software", "QSG_RHI_BACKEND": "software",
    }
    qml_path = next(Path("/nix/store").glob("*qt5compat-*/lib/qt-6/qml"), None)
    if qml_path is None:
        raise RuntimeError("qt5compat QML import path is unavailable in the Nix environment")
    values["QML2_IMPORT_PATH"] = str(qml_path) + ":/workspace/shell/ui/shapes"
    values["QML_IMPORT_PATH"] = values["QML2_IMPORT_PATH"]
    result = dict(os.environ); result.update(values)
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        Path(result[key]).mkdir(parents=True, exist_ok=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--ipc-runs", type=int, default=20)
    args = parser.parse_args()
    output = args.output; output.parent.mkdir(parents=True, exist_ok=True)
    log_dir = output.parent / "logs"; log_dir.mkdir(exist_ok=True)
    env = environment(); weston_log = (log_dir / "weston.log").open("w")
    weston = subprocess.Popen(
        ["weston", "--backend=headless", "--renderer=pixman", "--no-config",
         "--socket=" + env["WAYLAND_DISPLAY"], "--idle-time=0"], env=env,
        stdout=weston_log, stderr=subprocess.STDOUT, start_new_session=True, text=True,
    )
    baseline_dir = output.parent / "baseline"; baseline_dir.mkdir(exist_ok=True)
    (baseline_dir / "shell.qml").write_text(
        "import QtQuick\nimport Quickshell\nimport Quickshell.Io\n"
        "ShellRoot { IpcHandler { target: \"benchmark\"; function ping(): string { return \"pong\" } } }\n"
    )
    try:
        socket = Path(env["XDG_RUNTIME_DIR"]) / env["WAYLAND_DISPLAY"]
        for _ in range(200):
            if socket.exists(): break
            time.sleep(0.05)
        if not socket.exists(): raise RuntimeError("private Weston socket did not appear")
        _run_process(kind="baseline", run_number=0, environment=env, baseline_dir=baseline_dir, log_dir=log_dir)
        _run_process(kind="shell", run_number=0, environment=env, baseline_dir=baseline_dir, log_dir=log_dir)
        baseline = [_run_process(kind="baseline", run_number=i, environment=env, baseline_dir=baseline_dir, log_dir=log_dir) for i in range(1, args.runs + 1)]
        cold = [_run_process(kind="shell", run_number=i, environment=env, baseline_dir=baseline_dir, log_dir=log_dir) for i in range(1, args.runs + 1)]
        warm = [_run_process(kind="shell", run_number=i, environment=env, baseline_dir=baseline_dir, log_dir=log_dir, warm=True) for i in range(1, max(2, args.runs // 2) + 1)]
        ipc_baseline = ipc_benchmark(
            env, log_dir, args.ipc_runs, str(baseline_dir), "benchmark", ("ping",),
            "Configuration Loaded", ["qs", "-p", str(baseline_dir), "--no-duplicate", "-v"]
        )
        ipc_shell = ipc_benchmark(
            env, log_dir, args.ipc_runs, "/workspace/shell", "shell", IPC_METHODS,
            "IPC_READY", ["/workspace/shell/nyxuri-shell", "-v"]
        )
        actions = action_benchmark(env, log_dir, max(5, args.ipc_runs // 3))
    finally:
        _terminate(weston); weston_log.close()
        shutil.rmtree(baseline_dir, ignore_errors=True)

    def command_output(*command: str) -> str:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.stdout.strip() or result.stderr.strip()

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    git_sha = os.environ.get("NYXURI_BENCHMARK_GIT_SHA", "") or command_output(
        "git", "-C", "/workspace", "rev-parse", "HEAD"
    )
    dirty_value = os.environ.get("NYXURI_BENCHMARK_GIT_DIRTY")
    git_dirty = (dirty_value == "1") if dirty_value is not None else bool(
        command_output("git", "-C", "/workspace", "status", "--porcelain")
    )
    environment_summary = {
        key: env.get(key) for key in (
            "HOME", "XDG_RUNTIME_DIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME",
            "XDG_DATA_HOME", "XDG_STATE_HOME", "WAYLAND_DISPLAY",
            "QT_QPA_PLATFORM", "QT_QUICK_BACKEND", "QSG_RHI_BACKEND",
            "DBUS_SESSION_BUS_ADDRESS",
        )
    }
    result = {
        "schema": 2,
        "runtime": {
            "quickshell": command_output("qs", "--version"),
            "qt": command_output("qtpaths", "--qt-version"),
            "weston": command_output("weston", "--version"),
            "wayland_backend": lock.get("weston_backend"),
            "renderer": lock.get("renderer"),
            "qt_quick_backend": lock.get("qt_quick_backend"),
            "container_image": lock.get("container_image"),
            "container_digest": lock.get("container_digest"),
            "nixpkgs_revision": lock.get("nixpkgs_revision"),
            "git_sha": git_sha or None,
            "git_dirty": git_dirty,
            "environment": environment_summary,
            "runs": args.runs,
            "warmup_discarded": 1,
            "ipc_runs": args.ipc_runs,
        },
        "baseline": [numeric_run(run) for run in baseline], "cold_start": [numeric_run(run) for run in cold],
        "warm_start": [numeric_run(run) for run in warm],
        "ipc": {"baseline": ipc_baseline, "shell": ipc_shell},
        "actions": actions,
        "source_profile": source_profile(),
    }
    output.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
