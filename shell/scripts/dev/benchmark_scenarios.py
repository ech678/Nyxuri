#!/usr/bin/env python3
"""Orchestrate benchmark scenarios in the prepared Nix runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, TypedDict

from benchmark_runtime import IPC_METHODS, ProcessSample, RunResult, _process_tree, _quantile, _run_process, _terminate, start_compositor

LOCK_PATH = Path(__file__).with_name("benchmark-lock.json")
WORKSPACE_SHELL_ROOT: Final[Path] = Path("/workspace/shell")
PROFILE_CHOICES: Final[tuple[str, ...]] = (
    "empty-shellroot", "minimal-nyxuri", "default-full",
)
EMPTY_SHELLROOT_SOURCE: Final[str] = "import Quickshell\nShellRoot {}\n"
BENCHMARK_IPC_REFERENCE_SOURCE: Final[str] = (
    "import QtQuick\nimport Quickshell\nimport Quickshell.Io\n"
    "ShellRoot { IpcHandler { target: \"benchmark\"; function ping(): string { return \"pong\" } } }\n"
)
INHERITED_ENVIRONMENT: Final[tuple[str, ...]] = (
    "PATH", "NIX_PATH", "NIX_PROFILES", "NIX_SSL_CERT_FILE", "SSL_CERT_FILE",
    "TERM",
)
FIXED_ENVIRONMENT: Final[dict[str, str]] = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LC_CTYPE": "C.UTF-8",
    "LANGUAGE": "C",
    "TZ": "UTC",
    "PYTHONHASHSEED": "0",
    "QT_HASH_SEED": "0",
    "SOURCE_DATE_EPOCH": "0",
    "QT_SCALE_FACTOR": "1",
    "QT_AUTO_SCREEN_SCALE_FACTOR": "0",
}


class ProfileMetadata(TypedDict):
    profile_id: str
    meaning: str
    config_path: str
    config_kind: str
    config_sha256: str
    ipc_status: Literal["available", "unavailable"]
    ipc_unavailable_reason: str | None
    unit_actions_status: Literal["available", "unavailable"]
    unit_actions_unavailable_reason: str | None
    disabled_unit_ids: list[str]
    state_ledger_sha256: str | None


class IpcReferenceMetadata(TypedDict):
    profile_id: str
    config_path: str
    config_sha256: str
    meaning: str

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


def source_profile(root: Path = Path("/workspace/shell")) -> dict[str, int]:
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


_REAL_FIRST_FRAME_RE: Final[re.Pattern[str]] = re.compile(
    r"\[ShellStartup\]\s+REAL_FIRST_FRAME\s+source:\s*(?P<source>.*?)"
    r"\s+\(?(?:elapsed:\s*)?(?P<elapsed>[-+]?\d+(?:\.\d+)?)\s*ms\)?",
    re.IGNORECASE,
)


def parse_real_first_frame(log_text: str) -> dict[str, object]:
    """Parse the first real frame event without treating the legacy marker as truth.

    ``first_frame_ms`` is emitted by the old Qt.callLater path.  Only the explicit
    REAL_FIRST_FRAME event is accepted here; malformed or absent events have
    null values. This QML elapsed/source layer cannot set runner wall status.
    """
    for line in log_text.splitlines():
        match = _REAL_FIRST_FRAME_RE.search(line)
        if not match:
            continue
        try:
            elapsed = float(match.group("elapsed"))
        except ValueError:
            continue
        if elapsed < 0:
            continue
        source = match.group("source").strip().rstrip("(").strip()
        if not source:
            source = "unknown"
        return {
            "real_first_frame_ms": elapsed,
            "real_first_frame_source": source,
        }
    return {
        "real_first_frame_ms": None,
        "real_first_frame_source": None,
    }


def _startup_record(run: RunResult, profile_id: str | None = None) -> dict[str, object]:
    data = numeric_run(run, profile_id)
    # Keep runner observations separate from QML elapsed/source parsed below.
    # real_first_frame_status remains a compatibility alias for runner status.
    data["real_first_frame_wall_source"] = run.real_first_frame_source
    data["real_first_frame_wall_status"] = run.real_first_frame_status
    log_path = Path(str(run.log_path))
    try:
        log_text = log_path.read_text(errors="replace")
    except OSError:
        log_text = ""
    data.update(parse_real_first_frame(log_text))
    return data


def numeric_run(run: RunResult, profile_id: str | None = None) -> dict[str, object]:
    data = asdict(run)
    data["log_path"] = str(Path(str(data["log_path"])).relative_to(Path("/results")))
    if profile_id is not None:
        data["profile_id"] = profile_id
    return data


def first_party_unit_ids(shell_root: Path) -> tuple[str, ...]:
    """Derive production unit IDs using PluginRegistry's directory contract."""
    return tuple(sorted(
        f"shell.{plugin.name}"
        for plugin in (shell_root / "plugins").iterdir()
        if plugin.is_dir() and (plugin / "manifest.toml").is_file()
    ))


def _disabled_ledger(unit_ids: tuple[str, ...]) -> dict[str, dict[str, dict[str, str]]]:
    return {"plugins": {unit_id: {"state": "disabled"} for unit_id in unit_ids}}


def write_disabled_unit_ledger(state_home: Path, unit_ids: tuple[str, ...]) -> Path:
    """Write StateProjection's all-first-party-units-disabled state fixture."""
    ledger_path = state_home / "nyxuri" / "state.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(_disabled_ledger(unit_ids), ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return ledger_path


def profile_metadata(
    profile_id: str, shell_root: Path, profile_root: Path,
) -> ProfileMetadata:
    """Materialize isolated config when needed and return the raw profile contract."""
    if profile_id not in PROFILE_CHOICES:
        raise ValueError(f"unknown benchmark profile: {profile_id}")

    shell_config = shell_root / "shell.qml"
    if profile_id == "empty-shellroot":
        profile_root.mkdir(parents=True, exist_ok=True)
        config_path = profile_root
        config_kind = "generated_shellroot_without_handlers"
        config_bytes = EMPTY_SHELLROOT_SOURCE.encode("utf-8")
        (profile_root / "shell.qml").write_bytes(config_bytes)
        meaning = "One generated Quickshell ShellRoot with no QML children or IPC handlers."
        unit_ids: tuple[str, ...] = ()
        ipc_status = "unavailable"
        ipc_reason: str | None = "empty_shellroot_declares_no_ipc_handler"
        actions_status = "unavailable"
        actions_reason: str | None = "profile_has_no_shell_ipc_or_units"
        ledger_sha256 = None
    else:
        config_path = shell_root
        config_kind = "checked_in_production_shell_root"
        config_bytes = shell_config.read_bytes()
        unit_ids = first_party_unit_ids(shell_root) if profile_id == "minimal-nyxuri" else ()
        ledger_sha256 = None
        if profile_id == "minimal-nyxuri":
            if not unit_ids:
                raise RuntimeError(f"no checked-in first-party unit manifests found under {shell_root}")
            ledger_bytes = (
                json.dumps(_disabled_ledger(unit_ids), ensure_ascii=True, sort_keys=True, indent=2) + "\n"
            ).encode("utf-8")
            ledger_sha256 = hashlib.sha256(ledger_bytes).hexdigest()
            meaning = (
                "Checked-in Nyxuri production root and host services with every first-party unit disabled "
                "through StateProjection's isolated state ledger; core shell IPC remains available."
            )
            ipc_status = "available"
            ipc_reason = None
            actions_status = "unavailable"
            actions_reason = "all_first_party_units_disabled_by_profile"
        else:
            meaning = (
                "Checked-in Nyxuri production root with no state ledger; StateProjection's documented "
                "missing-ledger default enables all first-party units."
            )
            ipc_status = "available"
            ipc_reason = None
            actions_status = "available"
            actions_reason = None

    return {
        "profile_id": profile_id,
        "meaning": meaning,
        "config_path": str(config_path),
        "config_kind": config_kind,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "ipc_status": ipc_status,
        "ipc_unavailable_reason": ipc_reason,
        "unit_actions_status": actions_status,
        "unit_actions_unavailable_reason": actions_reason,
        "disabled_unit_ids": list(unit_ids),
        "state_ledger_sha256": ledger_sha256,
    }


def ipc_reference_metadata(config_path: Path) -> IpcReferenceMetadata:
    """Describe the handler-only reference used for IPC latency calibration."""
    return {
        "profile_id": "benchmark-ipc-reference",
        "config_path": str(config_path),
        "config_sha256": hashlib.sha256(BENCHMARK_IPC_REFERENCE_SOURCE.encode("utf-8")).hexdigest(),
        "meaning": "Single ping handler used only to calibrate IPC latency; not an empty ShellRoot baseline.",
    }


def default_full_profile_contract(
    identity: ProfileMetadata,
    startup_baseline: ProfileMetadata,
    ipc_reference: IpcReferenceMetadata,
) -> dict[str, object]:
    """Keep the startup baseline and IPC-only reference distinct in raw output."""
    return {
        "identity": identity,
        "baseline_reference": {
            "profile_id": startup_baseline["profile_id"],
            "identity": startup_baseline,
            "meaning": "Generated ShellRoot with no children or IPC handlers; startup comparison only.",
        },
        "ipc_reference": ipc_reference,
        "raw_paths": {
            "baseline": "$.baseline",
            "cold_start": "$.cold_start",
            "warm_start": "$.warm_start",
            "ipc": "$.ipc",
            "actions": "$.actions",
            "long_steady_state": "$.long_steady_state",
            "reclamation": "$.reclamation",
            "frame_profile": "$.frame_profile",
        },
    }


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


def _wait_spotlight_phase(environment: dict[str, str], expected: str, timeout: float = 3.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    last: dict[str, object] = {}
    while time.monotonic() < deadline:
        reply = subprocess.run(
            ["qs", "-p", "/workspace/shell", "ipc", "call", "spotlight", "lifecycle"],
            env=environment, capture_output=True, text=True, check=False, timeout=2,
        )
        try:
            last = json.loads(reply.stdout)
        except (ValueError, TypeError):
            last = {}
        if last.get("phase") == expected:
            return {"status": "available", **last}
        time.sleep(0.05)
    return {"status": "unavailable", "reason": "spotlight_phase_timeout", "expected": expected, "last": last}


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
            opened_state = _wait_spotlight_phase(environment, "open")
            closed = subprocess.run(
                ["qs", "-p", "/workspace/shell", "ipc", "call", "spotlight", "close"],
                env=environment, capture_output=True, text=True, check=False,
            )
            closed_state = _wait_spotlight_phase(environment, "hidden")
            time.sleep(close_wait_seconds)
            sample = _process_tree(process.pid)
            rows.append({
                "cycle": cycle, "open_returncode": opened.returncode, "close_returncode": closed.returncode,
                "opened_lifecycle": opened_state, "closed_lifecycle": closed_state,
                "open_value": opened.stdout.strip(), "close_value": closed.stdout.strip(),
                "sample_after_close": _sample_dict(sample),
            })
        horizon: dict[str, dict[str, object] | None] = {}
        for delay in (0.1, 1.0, 2.0, 5.0):
            time.sleep(delay if delay == 0.1 else delay - (0.1 if delay > 0.1 else 0))
            horizon[str(delay)] = _sample_dict(_process_tree(process.pid))
        _terminate(process)
    successful = [row for row in rows if row["open_returncode"] == 0 and row["close_returncode"] == 0
                  and row["opened_lifecycle"].get("results_loaded") is True
                  and row["closed_lifecycle"].get("status") == "available"
                  and row["closed_lifecycle"].get("results_loaded") is False]
    return {
        "scenario": "reclamation", "requested_cycles": cycles, "completed_cycles": len(rows),
        "successful_cycles": len(successful), "startup_valid": True, "sample_valid": len(successful) == cycles and all(
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
                "dropped_frames": null,
                "dropped_frames_estimate": droppedFrames,
                "drop_metric_status": "partial",
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
        "compositor": "sway",
        "compositor_renderer": "pixman",
        "scenegraph_log_lines": scenegraph_lines[-40:],
        "reason": "Qt frameSwapped is observable; Weston presentation feedback and texture/offscreen counters are not exposed by this headless pixman probe",
    }


def _frame_profile_payload(log_text: str) -> dict[str, object] | None:
    marker = "FRAME_PROFILE "
    for line in reversed(log_text.splitlines()):
        marker_index = line.find(marker)
        if marker_index < 0:
            continue
        try:
            payload = json.loads(line[marker_index + len(marker):])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


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
            payload = _frame_profile_payload(text)
            if payload is not None or process.poll() is not None:
                break
            time.sleep(0.05)
        _terminate(process)
        text = log_path.read_text(errors="replace")
    result: dict[str, object] = {
        "scenario": "frame_profile",
        "requested_seconds": duration_seconds,
        "target_fps": target_fps,
        "probe": _frame_profile_payload(text) or {
            "schema": 1,
            "status": "partial",
            "source": "Qt QQuickWindow.frameSwapped",
            "reason": "frame profile marker was not emitted",
            "frames": 0,
            "dropped_frames": None,
            "dropped_frames_estimate": None,
            "drop_metric_status": "partial",
            "frame_interval_ms": None,
        },
        "renderer": _renderer_profile(text, probe_env),
        "controlled_shutdown": process.returncode in (0, -15),
        "log_path": str(log_path),
    }
    return result


def environment(*, qml_root: Path | None = None) -> dict[str, str]:
    runtime = Path("/tmp/nyxuri-runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    os.chmod(runtime, 0o700)
    values = {
        "HOME": "/tmp/nyxuri-home", "XDG_RUNTIME_DIR": str(runtime),
        "XDG_CACHE_HOME": "/tmp/nyxuri-cache", "XDG_CONFIG_HOME": "/tmp/nyxuri-config",
        "XDG_DATA_HOME": "/tmp/nyxuri-data", "XDG_STATE_HOME": "/tmp/nyxuri-state",
        "WAYLAND_DISPLAY": "nyxuri-benchmark-wayland", "QT_QPA_PLATFORM": "wayland",
        "QT_QUICK_BACKEND": "software",
    }
    qml_path = qml_root or next(Path("/nix/store").glob("*qt5compat-*/lib/qt-6/qml"), None)
    if qml_path is None:
        raise RuntimeError("qt5compat QML import path is unavailable in the Nix environment")
    values["QML2_IMPORT_PATH"] = str(qml_path) + ":/workspace/shell/ui/shapes"
    values["QML_IMPORT_PATH"] = values["QML2_IMPORT_PATH"]
    result = {
        key: os.environ[key]
        for key in INHERITED_ENVIRONMENT
        if os.environ.get(key)
    }
    result.update(FIXED_ENVIRONMENT)
    dbus_address = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if dbus_address.startswith(("unix:path=/tmp/", "unix:abstract=")):
        result["DBUS_SESSION_BUS_ADDRESS"] = dbus_address
    result.update(values)
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        Path(result[key]).mkdir(parents=True, exist_ok=True)
    return result


def _namespace_link(name: str) -> str | None:
    try:
        return os.readlink(f"/proc/self/ns/{name}")
    except OSError:
        return None


def _private_container_scope() -> bool:
    """Detect Podman/Nix containers without relying on an image marker file."""
    if any(Path(path).exists() for path in ("/.dockerenv", "/run/.containerenv")):
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8").splitlines()
        pid1 = Path("/proc/1/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except (OSError, UnicodeError):
        return False
    return "0::/" in cgroup and "systemd" not in pid1


def container_environment_fingerprint(
    environment: dict[str, str], lock: dict[str, object],
) -> dict[str, object]:
    """Describe only the private container namespace and deterministic inputs."""
    affinity = None
    try:
        affinity = sorted(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        pass
    marker_paths = [path for path in ("/.dockerenv", "/run/.containerenv") if Path(path).exists()]
    dbus_address = environment.get("DBUS_SESSION_BUS_ADDRESS")
    return {
        "scope": "container-process-tree",
        "container_markers": marker_paths,
        "pid_namespace": _namespace_link("pid"),
        "mount_namespace": _namespace_link("mnt"),
        "proc_root": "/proc",
        "proc_scope": "private-pid-namespace",
        "host_proc_access": "not_configured",
        "host_user_directory_access": "not_configured",
        "host_socket_access": "not_configured",
        "cpu_affinity": affinity if affinity is not None else {"status": "unavailable", "reason": "sched_getaffinity_unavailable"},
        "locale": {key: environment.get(key) for key in ("LANG", "LC_ALL", "LC_CTYPE", "LANGUAGE")},
        "timezone": environment.get("TZ") or {"status": "unavailable", "reason": "TZ_not_set"},
        "screen": {
            "status": "unavailable",
            "reason": "requested_sway_mode_not_independently_observed",
            "requested_width_px": 1280,
            "requested_height_px": 720,
            "requested_refresh_hz": 60,
            "width_px": None,
            "height_px": None,
            "refresh_hz": None,
        },
        "renderer": {
            "compositor": "sway",
            "compositor_renderer": lock.get("renderer"),
            "qt_quick_backend": environment.get("QT_QUICK_BACKEND"),
            "qsg_rhi_backend": environment.get("QSG_RHI_BACKEND"),
        },
        "wayland": {
            "display": environment.get("WAYLAND_DISPLAY"),
            "socket": f"{environment.get('XDG_RUNTIME_DIR', '')}/{environment.get('WAYLAND_DISPLAY', '')}",
            "backend": lock.get("weston_backend"),
        },
        "dbus": {
            "status": "available" if dbus_address else "unavailable",
            "scope": "session",
            "address": dbus_address,
        },
        "xdg": {key: environment.get(key) for key in (
            "XDG_RUNTIME_DIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME",
            "XDG_DATA_HOME", "XDG_STATE_HOME",
        )},
        "home": environment.get("HOME"),
        "random_seed": {
            "PYTHONHASHSEED": environment.get("PYTHONHASHSEED"),
            "QT_HASH_SEED": environment.get("QT_HASH_SEED"),
            "SOURCE_DATE_EPOCH": environment.get("SOURCE_DATE_EPOCH"),
        },
        "container_digest": lock.get("container_digest"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--ipc-runs", type=int, default=20)
    parser.add_argument("--steady-seconds", type=float, default=600.0)
    parser.add_argument("--reclaim-cycles", type=int, default=100)
    parser.add_argument("--reclaim-close-wait", type=float, default=0.1)
    parser.add_argument("--frame-seconds", type=float, default=5.0)
    parser.add_argument(
        "--profile", choices=PROFILE_CHOICES, action="append", dest="profiles",
        help="Benchmark profile; repeat to select several (default: default-full).",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.profiles = args.profiles or ["default-full"]
    if len(set(args.profiles)) != len(args.profiles):
        parser.error("--profile cannot be repeated with the same value")
    return args


@dataclass(frozen=True, slots=True)
class StartupTarget:
    profile_id: str
    config_root: Path
    run_kind: str
    environment: dict[str, str]
    log_dir: Path


def startup_samples(target: StartupTarget, count: int) -> dict[str, list[dict[str, object]]]:
    """Run isolated cold and warm startup samples for one profile root."""
    _run_process(
        kind=target.run_kind, run_number=0, environment=target.environment,
        baseline_dir=target.config_root, log_dir=target.log_dir,
    )
    cold = [
        _startup_record(
            _run_process(
                kind=target.run_kind, run_number=number, environment=target.environment,
                baseline_dir=target.config_root, log_dir=target.log_dir,
            ),
            target.profile_id,
        )
        for number in range(1, count + 1)
    ]
    warm = [
        _startup_record(
            _run_process(
                kind=target.run_kind, run_number=number, environment=target.environment,
                baseline_dir=target.config_root, log_dir=target.log_dir, warm=True,
            ),
            target.profile_id,
        )
        for number in range(1, max(2, count // 2) + 1)
    ]
    return {"cold_start": cold, "warm_start": warm}


def isolated_profile_environment(base_environment: dict[str, str], profile_id: str) -> dict[str, str]:
    """Give a production profile separate XDG state without changing its runtime."""
    profile_environment = dict(base_environment)
    profile_environment["HOME"] += f"/{profile_id}"
    for key in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        profile_environment[key] += f"/{profile_id}"
        Path(profile_environment[key]).mkdir(parents=True, exist_ok=True)
    Path(profile_environment["HOME"]).mkdir(parents=True, exist_ok=True)
    return profile_environment


def prepare_minimal_ledgers(
    state_home: Path, unit_ids: tuple[str, ...], cold_runs: int,
) -> None:
    """Seed the isolated ledger used by each cold run and the shared warm run."""
    for suffix in ("", *(f"-{number}" for number in range(cold_runs + 1))):
        write_disabled_unit_ledger(Path(f"{state_home}{suffix}"), unit_ids)


def run_isolated_profile(
    profile_id: str, args: argparse.Namespace, base_environment: dict[str, str], output_root: Path,
) -> dict[str, object]:
    """Run a profile that does not use the legacy default-full report path."""
    shell_root = WORKSPACE_SHELL_ROOT
    profile_root = output_root / profile_id / "config"
    identity = profile_metadata(profile_id, shell_root, profile_root)
    profile_logs = output_root / profile_id / "logs"
    profile_logs.mkdir(parents=True, exist_ok=True)
    profile_env = isolated_profile_environment(base_environment, profile_id)
    run_kind = "baseline" if profile_id == "empty-shellroot" else "shell"
    if profile_id == "minimal-nyxuri":
        prepare_minimal_ledgers(
            Path(profile_env["XDG_STATE_HOME"]), first_party_unit_ids(shell_root), args.runs,
        )

    startup = startup_samples(
        StartupTarget(profile_id, profile_root if run_kind == "baseline" else shell_root,
                      run_kind, profile_env, profile_logs),
        args.runs,
    )
    not_profile_bound = {
        "status": "unavailable",
        "reason": "standalone_frame_probe_does_not_execute_this_profile",
    }
    result: dict[str, object] = {
        "identity": identity,
        "source_profile": source_profile(profile_root if profile_id == "empty-shellroot" else shell_root),
        "startup": startup,
        "ipc": {"status": "unavailable", "reason": identity["ipc_unavailable_reason"]},
        "actions": {"status": "unavailable", "reason": identity["unit_actions_unavailable_reason"]},
        "long_steady_state": {
            "status": "unavailable",
            "reason": "steady_state_runner_requires_shell_ipc_ready",
        },
        "reclamation": {
            "status": "unavailable",
            "reason": identity["unit_actions_unavailable_reason"],
        },
        "frame_profile": not_profile_bound,
    }
    if profile_id == "minimal-nyxuri":
        result["ipc"] = {
            "status": "available",
            "shell": ipc_benchmark(
                profile_env, profile_logs, args.ipc_runs, str(shell_root), "shell", IPC_METHODS,
                "IPC_READY", ["/workspace/shell/nyxuri-shell", "-v"],
            ),
        }
        result["long_steady_state"] = steady_state_benchmark(
            profile_env, profile_logs, args.steady_seconds,
        )
    return result


def main() -> int:
    parser = build_parser()
    args = parse_args()
    profile_names: list[str] = args.profiles or ["default-full"]
    if os.environ.get("NYXURI_CONTAINER") != "1" or not _private_container_scope():
        parser.error("benchmark runtime may only run inside benchmark-shell.py's private container")
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
    profile_root = output.parent / "profiles"
    profile_root.mkdir(exist_ok=True)
    env = environment()
    weston = start_compositor(env, log_dir)
    baseline: list[dict[str, object]] = []
    cold: list[dict[str, object]] = []
    warm: list[dict[str, object]] = []
    ipc_baseline: dict[str, dict[str, float | int]] = {}
    ipc_shell: dict[str, dict[str, float | int]] = {}
    actions: dict[str, dict[str, float | int]] = {}
    steady_state: dict[str, object] = {"status": "unavailable", "reason": "default_full_not_selected"}
    reclamation: dict[str, object] = {"status": "unavailable", "reason": "default_full_not_selected"}
    frame_profile: dict[str, object] = {"status": "unavailable", "reason": "default_full_not_selected"}
    source_profile_summary: dict[str, int] | None = None
    profiles: dict[str, dict[str, object]] = {}
    try:
        socket = Path(env["XDG_RUNTIME_DIR"]) / env["WAYLAND_DISPLAY"]
        for _ in range(200):
            if socket.exists(): break
            time.sleep(0.05)
        if not socket.exists(): raise RuntimeError("private Weston socket did not appear")
        if "default-full" in profile_names:
            startup_baseline_dir = profile_root / "empty-shellroot" / "config"
            startup_baseline_identity = profile_metadata(
                "empty-shellroot", WORKSPACE_SHELL_ROOT, startup_baseline_dir,
            )
            ipc_reference_dir = output.parent / "ipc-reference"
            ipc_reference_dir.mkdir(exist_ok=True)
            (ipc_reference_dir / "shell.qml").write_text(
                BENCHMARK_IPC_REFERENCE_SOURCE, encoding="utf-8",
            )
            _run_process(kind="baseline", run_number=0, environment=env,
                         baseline_dir=startup_baseline_dir, log_dir=log_dir)
            _run_process(kind="shell", run_number=0, environment=env,
                         baseline_dir=startup_baseline_dir, log_dir=log_dir)
            baseline = [_startup_record(
                _run_process(kind="baseline", run_number=i, environment=env,
                             baseline_dir=startup_baseline_dir, log_dir=log_dir),
                "empty-shellroot",
            ) for i in range(1, args.runs + 1)]
            cold = [_startup_record(
                _run_process(kind="shell", run_number=i, environment=env,
                             baseline_dir=startup_baseline_dir, log_dir=log_dir),
                "default-full",
            ) for i in range(1, args.runs + 1)]
            warm = [_startup_record(
                _run_process(kind="shell", run_number=i, environment=env,
                             baseline_dir=startup_baseline_dir, log_dir=log_dir, warm=True),
                "default-full",
            ) for i in range(1, max(2, args.runs // 2) + 1)]
            ipc_baseline = ipc_benchmark(
                env, log_dir, args.ipc_runs, str(ipc_reference_dir), "benchmark", ("ping",),
                "Configuration Loaded", ["qs", "-p", str(ipc_reference_dir), "--no-duplicate", "-v"]
            )
            ipc_shell = ipc_benchmark(
                env, log_dir, args.ipc_runs, "/workspace/shell", "shell", IPC_METHODS,
                "IPC_READY", ["/workspace/shell/nyxuri-shell", "-v"]
            )
            actions = action_benchmark(env, log_dir, max(5, args.ipc_runs // 3))
            steady_state = steady_state_benchmark(env, log_dir, args.steady_seconds)
            reclamation = reclamation_benchmark(env, log_dir, args.reclaim_cycles, args.reclaim_close_wait)
            frame_profile = frame_profile_benchmark(env, log_dir, args.frame_seconds)
            source_profile_summary = source_profile()
            profiles["default-full"] = default_full_profile_contract(
                profile_metadata("default-full", WORKSPACE_SHELL_ROOT, profile_root),
                startup_baseline_identity,
                ipc_reference_metadata(ipc_reference_dir),
            )
        for profile_id in profile_names:
            if profile_id == "default-full":
                continue
            profiles[profile_id] = run_isolated_profile(profile_id, args, env, profile_root)
    finally:
        _terminate(weston)
        if "default-full" in profile_names:
            shutil.rmtree(output.parent / "ipc-reference", ignore_errors=True)

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
        "schema": 3,
        "selected_profiles": profile_names,
        "profiles": profiles,
        "runtime": {
            "quickshell": command_output("qs", "--version"),
            "qt": command_output("qtpaths", "--qt-version"),
            "compositor": command_output("sway", "--version"),
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
            "environment_fingerprint": container_environment_fingerprint(env, lock),
            "runs": args.runs,
            "warmup_discarded": 1,
            "ipc_runs": args.ipc_runs,
            "steady_seconds": args.steady_seconds,
            "reclaim_cycles": args.reclaim_cycles,
            "reclaim_close_wait": args.reclaim_close_wait,
            "frame_seconds": args.frame_seconds,
            "selected_profiles": profile_names,
            "optional_process_commands": ["key", "lspci", "inotifywait", "ddcutil"],
        },
        "baseline": baseline, "cold_start": cold,
        "warm_start": warm,
        "ipc": {"baseline": ipc_baseline, "shell": ipc_shell},
        "actions": actions,
        "long_steady_state": steady_state,
        "reclamation": reclamation,
        "frame_profile": frame_profile,
        "source_profile": source_profile_summary,
    }
    output.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
