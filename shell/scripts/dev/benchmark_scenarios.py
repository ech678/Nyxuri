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

from benchmark_runtime import IPC_METHODS, ProcessSample, RunResult, _process_tree, _quantile, _run_process, _terminate

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


def _sample_dict(sample: ProcessSample | None) -> dict[str, object] | None:
    return asdict(sample) if sample is not None else None


def _wait_for_marker(log_path: Path, marker: str, process: subprocess.Popen[str], timeout: float) -> float | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        log_path.touch(exist_ok=True)
        text = log_path.read_text(errors="replace")
        if marker in text:
            return time.monotonic()
        if process.poll() is not None:
            return None
        time.sleep(0.05)
    return None


def steady_state_benchmark(
    environment: dict[str, str], log_dir: Path, duration_seconds: float, interval_seconds: float = 1.0,
) -> dict[str, object]:
    """Keep the real shell alive and preserve every process-tree sample."""
    if duration_seconds <= 0 or interval_seconds <= 0:
        raise ValueError("duration and interval must be positive")
    log_path = log_dir / "steady-state-host.log"
    samples: list[dict[str, object]] = []
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["/workspace/shell/nyxuri-shell", "-v"], env=environment,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True,
        )
        started = time.monotonic()
        marker_time = _wait_for_marker(log_path, "IPC_READY", process, timeout=20.0)
        if marker_time is None:
            _terminate(process)
            return {
                "scenario": "long_steady_state", "requested_seconds": duration_seconds,
                "elapsed_seconds": max(time.monotonic() - started, 0.0), "startup_valid": False,
                "sample_valid": False, "controlled_shutdown": process.returncode in (0, -15),
                "samples": [], "log_path": str(log_path),
            }
        deadline = marker_time + duration_seconds
        while time.monotonic() < deadline and process.poll() is None:
            sample = _process_tree(process.pid)
            if sample is not None:
                samples.append({"elapsed_seconds": time.monotonic() - marker_time, "sample": asdict(sample)})
            time.sleep(interval_seconds)
        _terminate(process)
    elapsed = max(time.monotonic() - marker_time, 0.0)
    rss: list[int] = []
    for row in samples:
        sample = row.get("sample")
        if isinstance(sample, dict) and isinstance(sample.get("rss_kb"), int):
            rss.append(sample["rss_kb"])
    return {
        "scenario": "long_steady_state", "requested_seconds": duration_seconds,
        "elapsed_seconds": elapsed, "startup_valid": True, "sample_valid": bool(samples),
        "controlled_shutdown": process.returncode in (0, -15), "sample_count": len(samples),
        "rss_kb": {"first": rss[0] if rss else None, "last": rss[-1] if rss else None,
                   "min": min(rss) if rss else None, "max": max(rss) if rss else None,
                   "delta": (rss[-1] - rss[0]) if len(rss) >= 2 else None},
        "samples": samples, "log_path": str(log_path),
    }


def reclamation_benchmark(
    environment: dict[str, str], log_dir: Path, cycles: int, close_wait_seconds: float = 0.1,
) -> dict[str, object]:
    """Open and close a real unit repeatedly, retaining post-close observations."""
    if cycles < 1 or close_wait_seconds < 0:
        raise ValueError("cycles must be >= 1 and close wait must be >= 0")
    log_path = log_dir / "reclamation-host.log"
    rows: list[dict[str, object]] = []
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["/workspace/shell/nyxuri-shell", "-v"], env=environment,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True,
        )
        marker_time = _wait_for_marker(log_path, "IPC_READY", process, timeout=20.0)
        if marker_time is None:
            _terminate(process)
            return {"scenario": "reclamation", "requested_cycles": cycles, "completed_cycles": 0,
                    "startup_valid": False, "sample_valid": False, "controlled_shutdown": process.returncode in (0, -15),
                    "cycles": [], "horizon_samples": {}, "log_path": str(log_path)}
        for cycle in range(1, cycles + 1):
            opened = subprocess.run(
                ["qs", "-p", "/workspace/shell", "ipc", "call", "spotlight", "open"],
                env=environment, capture_output=True, text=True, check=False,
            )
            closed = subprocess.run(
                ["qs", "-p", "/workspace/shell", "ipc", "call", "spotlight", "close"],
                env=environment, capture_output=True, text=True, check=False,
            )
            time.sleep(close_wait_seconds)
            sample = _process_tree(process.pid)
            rows.append({
                "cycle": cycle, "open_returncode": opened.returncode, "close_returncode": closed.returncode,
                "open_value": opened.stdout.strip(), "close_value": closed.stdout.strip(),
                "sample_after_close": _sample_dict(sample),
            })
        horizon: dict[str, dict[str, object] | None] = {}
        for delay in (0.1, 1.0, 2.0, 5.0):
            time.sleep(delay if delay == 0.1 else delay - (0.1 if delay > 0.1 else 0))
            horizon[str(delay)] = _sample_dict(_process_tree(process.pid))
        _terminate(process)
    successful = [row for row in rows if row["open_returncode"] == 0 and row["close_returncode"] == 0]
    return {
        "scenario": "reclamation", "requested_cycles": cycles, "completed_cycles": len(rows),
        "successful_cycles": len(successful), "startup_valid": True, "sample_valid": any(
            row["sample_after_close"] is not None for row in rows),
        "controlled_shutdown": process.returncode in (0, -15), "cycles": rows,
        "horizon_samples": horizon, "log_path": str(log_path),
    }


def _frame_probe_source(duration_seconds: float, target_fps: float) -> str:
    """Return a self-contained Qt Quick frame-swap probe.

    This deliberately uses only QQuickWindow's public ``frameSwapped`` signal.
    Weston presentation feedback and scene-graph texture counters are not
    available through the pinned headless/pixman stack, so the caller reports
    those fields as partial instead of inferring them from CPU samples.
    """
    duration_ms = max(100, int(duration_seconds * 1000))
    return f'''import QtQuick
import QtQuick.Window
import Quickshell

ShellRoot {{
    Window {{
        id: probe
        visible: true
        width: 1280
        height: 720
        color: "#18212b"
        property double startedMs: Date.now()
        property double lastFrameMs: 0
        property var intervals: []
        property int frames: 0
        property int droppedFrames: 0
        property double targetFps: {target_fps:.6f}

        Rectangle {{
            id: canvas
            anchors.fill: parent
            color: probe.frames % 2 ? "#243746" : "#18212b"
            opacity: 0.98
        }}
        NumberAnimation {{
            target: canvas
            property: "rotation"
            from: 0
            to: 360
            duration: 1000
            loops: Animation.Infinite
            running: true
        }}

        function quantile(values, probability) {{
            if (!values.length)
                return null;
            const sorted = values.slice().sort((a, b) => a - b);
            const position = (sorted.length - 1) * probability;
            const low = Math.floor(position);
            const high = Math.min(low + 1, sorted.length - 1);
            return sorted[low] + (sorted[high] - sorted[low]) * (position - low);
        }}

        function finish() {{
            const now = Date.now();
            const elapsed = Math.max(now - startedMs, 1);
            const payload = {{
                "schema": 1,
                "status": frames > 0 ? "available" : "partial",
                "source": "Qt QQuickWindow.frameSwapped",
                "elapsed_ms": elapsed,
                "frames": frames,
                "dropped_frames": droppedFrames,
                "estimated_fps": frames * 1000 / elapsed,
                "target_fps": targetFps,
                "frame_interval_ms": {{
                    "n": intervals.length,
                    "p50": quantile(intervals, 0.50),
                    "p95": quantile(intervals, 0.95),
                    "p99": quantile(intervals, 0.99),
                    "min": intervals.length ? Math.min.apply(null, intervals) : null,
                    "max": intervals.length ? Math.max.apply(null, intervals) : null
                }},
                "unsupported": [
                    "weston_presentation_feedback",
                    "texture_count",
                    "offscreen_target_count"
                ]
            }};
            console.log("FRAME_PROFILE " + JSON.stringify(payload));
            Qt.quit();
        }}

        onFrameSwapped: {{
            const now = Date.now();
            if (lastFrameMs > 0) {{
                const interval = now - lastFrameMs;
                if (intervals.length < 10000)
                    intervals.push(interval);
                droppedFrames += Math.max(0, Math.ceil(interval / (1000 / targetFps)) - 1);
            }}
            lastFrameMs = now;
            frames += 1;
        }}

        Timer {{
            interval: {duration_ms}
            running: true
            repeat: false
            onTriggered: probe.finish()
        }}
    }}
}}
'''


def _renderer_profile(log_text: str, environment: dict[str, str]) -> dict[str, object]:
    """Extract only renderer facts emitted by Qt/Weston, preserving limits."""
    scenegraph_lines = [
        line.strip() for line in log_text.splitlines()
        if any(token in line.lower() for token in ("scenegraph", "rhi", "renderer", "graphics api"))
    ]
    return {
        "status": "partial",
        "source": ["benchmark-lock.json", "Qt scenegraph log"],
        "qt_quick_backend": environment.get("QT_QUICK_BACKEND"),
        "qsg_rhi_backend": environment.get("QSG_RHI_BACKEND"),
        "weston_renderer": "pixman",
        "scenegraph_log_lines": scenegraph_lines[-40:],
        "reason": "Qt frameSwapped is observable; Weston presentation feedback and texture/offscreen counters are not exposed by this headless pixman probe",
    }


def frame_profile_benchmark(
    environment: dict[str, str], log_dir: Path, duration_seconds: float = 5.0,
    target_fps: float = 60.0,
) -> dict[str, object]:
    """Profile Qt frame swaps in the isolated Weston session.

    This is intentionally a separate probe rather than a host-run or an
    inferred process metric. Missing frame callbacks remain a valid partial
    result and retain the raw log for diagnosis.
    """
    if duration_seconds <= 0 or target_fps <= 0:
        raise ValueError("duration and target fps must be positive")
    root = log_dir / "frame-profile"
    root.mkdir(parents=True, exist_ok=True)
    (root / "shell.qml").write_text(
        _frame_probe_source(duration_seconds, target_fps), encoding="utf-8"
    )
    log_path = root / "probe.log"
    probe_env = dict(environment)
    probe_env.update({
        "QSG_INFO": "1",
        "QT_LOGGING_RULES": "qt.scenegraph.general=true;qt.rhi.*=true",
    })
    payload: dict[str, object] | None = None
    with log_path.open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["qs", "-p", str(root), "--no-duplicate", "-v"],
            env=probe_env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, text=True,
        )
        deadline = time.monotonic() + duration_seconds + 15
        while time.monotonic() < deadline:
            log.flush()
            text = log_path.read_text(errors="replace")
            for line in reversed(text.splitlines()):
                if line.startswith("FRAME_PROFILE "):
                    try:
                        parsed = json.loads(line.removeprefix("FRAME_PROFILE "))
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict):
                        payload = parsed
                        break
            if payload is not None or process.poll() is not None:
                break
            time.sleep(0.05)
        _terminate(process)
        text = log_path.read_text(errors="replace")
    result: dict[str, object] = {
        "scenario": "frame_profile",
        "requested_seconds": duration_seconds,
        "target_fps": target_fps,
        "probe": payload or {
            "schema": 1,
            "status": "partial",
            "source": "Qt QQuickWindow.frameSwapped",
            "reason": "frame profile marker was not emitted",
            "frames": 0,
            "dropped_frames": None,
            "frame_interval_ms": None,
        },
        "renderer": _renderer_profile(text, probe_env),
        "controlled_shutdown": process.returncode in (0, -15),
        "log_path": str(log_path),
    }
    return result


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
    parser.add_argument("--steady-seconds", type=float, default=600.0)
    parser.add_argument("--reclaim-cycles", type=int, default=100)
    parser.add_argument("--reclaim-close-wait", type=float, default=0.1)
    parser.add_argument("--frame-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.steady_seconds <= 0:
        parser.error("--steady-seconds must be > 0")
    if args.reclaim_cycles < 1:
        parser.error("--reclaim-cycles must be >= 1")
    if args.reclaim_close_wait < 0:
        parser.error("--reclaim-close-wait must be >= 0")
    if args.frame_seconds <= 0:
        parser.error("--frame-seconds must be > 0")
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
        steady_state = steady_state_benchmark(env, log_dir, args.steady_seconds)
        reclamation = reclamation_benchmark(env, log_dir, args.reclaim_cycles, args.reclaim_close_wait)
        frame_profile = frame_profile_benchmark(env, log_dir, args.frame_seconds)
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
            "steady_seconds": args.steady_seconds,
            "reclaim_cycles": args.reclaim_cycles,
            "reclaim_close_wait": args.reclaim_close_wait,
            "frame_seconds": args.frame_seconds,
            "optional_process_commands": ["key", "lspci", "inotifywait", "ddcutil"],
        },
        "baseline": [numeric_run(run) for run in baseline], "cold_start": [numeric_run(run) for run in cold],
        "warm_start": [numeric_run(run) for run in warm],
        "ipc": {"baseline": ipc_baseline, "shell": ipc_shell},
        "actions": actions,
        "long_steady_state": steady_state,
        "reclamation": reclamation,
        "frame_profile": frame_profile,
        "source_profile": source_profile(),
    }
    output.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
