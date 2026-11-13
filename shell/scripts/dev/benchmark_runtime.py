#!/usr/bin/env python3
"""Run the native Nyxuri Shell benchmark inside an isolated Wayland session.

The runtime side intentionally uses only the Python standard library.  The
host launcher supplies Quickshell, Weston, Qt5Compat and Python through a
temporary Nix container; this module measures the actual process tree rather
than a mock or an offscreen QML fixture.
"""

from __future__ import annotations

import json
import os
import re
import signal
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Literal

IPC_METHODS: Final[tuple[str, ...]] = ("stage", "isReady", "status", "metrics")
IPC_MARKER: Final[re.Pattern[str]] = re.compile(
    r"Stage transition -> IPC_READY .*elapsed:\s*(\d+)ms"
)
REAL_FIRST_FRAME_MARKER: Final[re.Pattern[str]] = re.compile(
    r"\[ShellStartup\]\s+REAL_FIRST_FRAME\s+source:\s*"
    r"(?P<source>[^\r\n]*?)\s*(?:\(\s*elapsed:|$)",
    re.IGNORECASE,
)
PROCESS_FAILURE_MARKER: Final[re.Pattern[str]] = re.compile(
    r"Process failed to start", re.IGNORECASE
)
PROCESS_FAILURE_COMMAND: Final[re.Pattern[str]] = re.compile(
    r"Command:\s*QList\(\s*\"([^\"]+)\"", re.IGNORECASE
)
OPTIONAL_PROCESS_COMMANDS: Final[frozenset[str]] = frozenset({
    "key", "lspci", "inotifywait", "ddcutil",
})
RUNTIME_QML_RESOURCE_KEYS: Final[tuple[str, ...]] = (
    "loaders", "timers", "processes", "fileviews", "connections", "delegates",
    "canvas", "layers", "windows",
)
RUNTIME_QML_RESOURCE_STATE_KEYS: Final[tuple[str, ...]] = ("timer", "process")
RUNTIME_QML_RESOURCE_STATE_FIELDS: Final[tuple[str, ...]] = (
    "total", "running", "stopped", "unknown",
)


@dataclass(frozen=True, slots=True)
class ProcessStartFailure:
    command: str | None
    category: Literal["optional", "required", "unattributed"]
    reason: str


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    pid: int
    start_ticks: int
    command: str


@dataclass(slots=True)
class _ObservedProcess:
    pid: int
    start_ticks: int
    command: str
    first_seen_ms: int
    last_seen_ms: int
    observations: int = 1


class ProcessLifecycleTracker:
    """Aggregate sampled process-tree sightings without claiming complete events."""

    def __init__(self) -> None:
        self._processes: dict[tuple[int, int], _ObservedProcess] = {}
        self._command_launches: dict[str, int] = {}
        self._restarts = 0
        self._sample_count = 0

    def observe(self, observations: tuple[ProcessObservation, ...], elapsed_ms: int) -> None:
        for row in observations:
            key = (row.pid, row.start_ticks)
            existing = self._processes.get(key)
            if existing is None:
                self._processes[key] = _ObservedProcess(
                    pid=row.pid,
                    start_ticks=row.start_ticks,
                    command=row.command,
                    first_seen_ms=elapsed_ms,
                    last_seen_ms=elapsed_ms,
                )
                launches = self._command_launches.get(row.command, 0)
                if launches:
                    self._restarts += 1
                self._command_launches[row.command] = launches + 1
            else:
                existing.last_seen_ms = elapsed_ms
                existing.observations += 1
        self._sample_count += 1

    def report(self, failures: tuple[ProcessStartFailure, ...]) -> dict[str, object]:
        """Return sampled lifetimes and explicitly separate failed launch evidence."""
        processes = [
            {
                "pid": row.pid,
                "start_ticks": row.start_ticks,
                "command": row.command,
                "owner": None,
                "category": f"command:{row.command}",
                "first_seen_ms": row.first_seen_ms,
                "last_seen_ms": row.last_seen_ms,
                "observed_duration_ms": row.last_seen_ms - row.first_seen_ms,
                "observation_count": row.observations,
                "duration_is_lower_bound": True,
            }
            for row in sorted(self._processes.values(), key=lambda item: (item.first_seen_ms, item.pid))
        ]
        return {
            "schema": 1,
            "status": "partial",
            "source": "sampled_proc_process_tree_and_benchmark_log",
            "sample_interval_ms": 50,
            "sample_count": self._sample_count,
            "launch_count": len(processes),
            "restart_count": self._restarts,
            "failed_launch_count": len(failures),
            "processes": processes,
            "failed_launches": [
                {"command": failure.command, "category": failure.category, "reason": failure.reason}
                for failure in failures
            ],
            "limitations": [
                "sampled_processes_only_short_lived_children_may_be_missed",
                "duration_is_observed_lower_bound_not_kernel_exit_time",
                "restart_count_means_repeated_observed_executable_not_confirmed_restart_chain",
                "owner_unavailable_without_stable_qml_process_mapping",
                "cpu_and_output_bytes_are_not_attributed_per_process",
            ],
        }


@dataclass(frozen=True, slots=True)
class ProcessSample:
    rss_kb: int
    pss_kb: int
    private_kb: int
    cpu_ticks: int
    user_cpu_ticks: int
    system_cpu_ticks: int
    context_switches: int
    voluntary_context_switches: int
    involuntary_context_switches: int
    page_faults: int
    minor_page_faults: int
    major_page_faults: int
    io_read_bytes: int
    io_write_bytes: int
    io_rchar_bytes: int
    io_wchar_bytes: int
    io_syscr: int
    io_syscw: int
    io_cancelled_write_bytes: int
    vm_peak_kb: int
    vm_hwm_kb: int
    vm_swap_kb: int
    rss_anon_kb: int
    rss_file_kb: int
    rss_shmem_kb: int
    process_count: int
    fd_count: int
    thread_count: int
    cgroup_memory_current_kb: int | None
    cgroup_memory_peak_kb: int | None


@dataclass(frozen=True, slots=True)
class RunResult:
    """Runner observations; wall time is first 50 ms-poll observation, not presentation time."""
    marker: bool
    startup_ms: float | None
    real_first_frame_wall_ms: float | None
    real_first_frame_source: str | None
    real_first_frame_status: Literal["available", "unavailable", "observed_after_exit"]
    internal_ms: dict[str, float]
    steady: ProcessSample | None
    peak: ProcessSample | None
    cpu_ms: float | None
    user_cpu_ms: float | None
    system_cpu_ms: float | None
    cpu_util_percent: float | None
    log_errors: int
    log_warnings: int
    fatal_log_count: int
    compiled_empty: int
    process_start_failures: int
    optional_process_start_failures: int
    required_process_start_failures: int
    unattributed_process_start_failures: int
    process_start_failure_details: tuple[ProcessStartFailure, ...]
    process_lifecycle: dict[str, object]
    live_telemetry: dict[str, object] | None
    exit_code: int | None
    startup_valid: bool
    sample_valid: bool
    controlled_shutdown: bool
    success: bool
    log_path: str


def classify_process_start_failures(text: str) -> tuple[ProcessStartFailure, ...]:
    """Classify each failed spawn; unknown commands remain required for gating."""
    markers = list(PROCESS_FAILURE_MARKER.finditer(text))
    failures: list[ProcessStartFailure] = []
    for index, marker in enumerate(markers):
        next_start = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        block = text[marker.start():next_start]
        command_match = PROCESS_FAILURE_COMMAND.search(block)
        if command_match is None:
            failures.append(ProcessStartFailure(
                command=None, category="unattributed", reason="command_not_logged"
            ))
            continue

        command = command_match.group(1).strip().rsplit("/", 1)[-1]
        if command in OPTIONAL_PROCESS_COMMANDS:
            failures.append(ProcessStartFailure(
                command=command, category="optional", reason="optional_dependency_unavailable"
            ))
        elif command:
            failures.append(ProcessStartFailure(
                command=command, category="required", reason="required_process_unavailable"
            ))
        else:
            failures.append(ProcessStartFailure(
                command=None, category="unattributed", reason="command_not_logged"
            ))
    return tuple(failures)


def process_failure_counts(
    failures: tuple[ProcessStartFailure, ...],
) -> dict[str, int]:
    """Return fail-closed counts; unattributed failures are included as required."""
    optional = sum(failure.category == "optional" for failure in failures)
    unattributed = sum(failure.category == "unattributed" for failure in failures)
    return {
        "process_start_failures": len(failures),
        "optional_process_start_failures": optional,
        "required_process_start_failures": len(failures) - optional,
        "unattributed_process_start_failures": unattributed,
    }


def has_required_process_failures(failures: tuple[ProcessStartFailure, ...]) -> bool:
    """Unknown and required command failures block success; optional ones do not."""
    return any(failure.category != "optional" for failure in failures)


def _unavailable_live_telemetry(sampled_at_ms: int, reason: str) -> dict[str, object]:
    return {
        "schema": 1,
        "source": "qs-ipc-shell-metrics",
        "sampled_at_ms": sampled_at_ms,
        "status": "unavailable",
        "reason": reason,
        "startup_metrics": None,
        "qml_resources": {
            "status": "unavailable",
            "reason": "resource_counts_not_exposed_by_shell_metrics",
            "counts": {key: None for key in RUNTIME_QML_RESOURCE_KEYS},
            "states": {key: None for key in RUNTIME_QML_RESOURCE_STATE_KEYS},
            "state_owners": {},
            "states_status": "unavailable",
            "states_reason": "resource_running_states_not_exposed_by_shell_metrics",
        },
    }


def parse_live_telemetry(reply: str, *, sampled_at_ms: int) -> dict[str, object]:
    """Parse shell IPC metrics and preserve partial live QML census honestly."""
    try:
        payload = json.loads(reply)
    except json.JSONDecodeError:
        return _unavailable_live_telemetry(sampled_at_ms, "invalid_json_reply")
    if not isinstance(payload, dict):
        return _unavailable_live_telemetry(sampled_at_ms, "non_object_reply")

    census = payload.get("qml_census")
    raw_resources = payload.get("qml_resources")
    if not isinstance(raw_resources, dict) and isinstance(census, dict):
        raw_resources = census.get("qml_resources") or census.get("resources")
    counts: dict[str, int | None] = {key: None for key in RUNTIME_QML_RESOURCE_KEYS}
    states: dict[str, dict[str, int] | None] = {
        key: None for key in RUNTIME_QML_RESOURCE_STATE_KEYS
    }
    state_owners: dict[str, dict[str, dict[str, int]]] = {}
    resource_status = "unavailable"
    resource_reason = "resource_counts_not_exposed_by_shell_metrics"
    states_status = "unavailable"
    states_reason = "resource_running_states_not_exposed_by_shell_metrics"
    if isinstance(raw_resources, dict):
        raw_counts = raw_resources.get("counts", raw_resources)
        if not isinstance(raw_counts, dict):
            raw_counts = {}
        valid_values = 0
        for key in RUNTIME_QML_RESOURCE_KEYS:
            value = raw_counts.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                counts[key] = value
                valid_values += 1
        if valid_values == len(RUNTIME_QML_RESOURCE_KEYS):
            resource_status = "available"
            resource_reason = ""
        elif valid_values > 0:
            resource_status = str(raw_resources.get("status") or "partial")
            if resource_status not in {"available", "partial", "unavailable", "invalid"}:
                resource_status = "partial"
            resource_reason = str(raw_resources.get("reason") or "incomplete_resource_counts")
        else:
            resource_status = str(raw_resources.get("status") or "invalid")
            if resource_status not in {"available", "partial", "unavailable", "invalid"}:
                resource_status = "invalid"
            resource_reason = str(raw_resources.get("reason") or "invalid_resource_counts")

        if "states" in raw_resources:
            raw_states = raw_resources.get("states")
            valid_states = 0

            def parse_state_bucket(value: object) -> dict[str, int] | None:
                if not isinstance(value, dict):
                    return None
                parsed: dict[str, int] = {}
                for field in RUNTIME_QML_RESOURCE_STATE_FIELDS:
                    field_value = value.get(field)
                    if (not isinstance(field_value, int) or isinstance(field_value, bool)
                            or field_value < 0):
                        return None
                    parsed[field] = field_value
                if parsed["total"] != parsed["running"] + parsed["stopped"] + parsed["unknown"]:
                    return None
                return parsed

            if isinstance(raw_states, dict):
                for key in RUNTIME_QML_RESOURCE_STATE_KEYS:
                    parsed = parse_state_bucket(raw_states.get(key))
                    if parsed is not None:
                        states[key] = parsed
                        valid_states += 1
                if valid_states == len(RUNTIME_QML_RESOURCE_STATE_KEYS):
                    states_status = "available"
                    states_reason = ""
                elif valid_states > 0:
                    states_status = "partial"
                    states_reason = "incomplete_resource_running_states"
                else:
                    states_status = "invalid"
                    states_reason = "invalid_resource_running_states"
            else:
                states_status = "invalid"
                states_reason = "invalid_resource_running_states"

            raw_state_owners = raw_resources.get("state_owners")
            if raw_state_owners is not None:
                owners_valid = isinstance(raw_state_owners, dict)
                if owners_valid:
                    for owner, owner_states in raw_state_owners.items():
                        if not isinstance(owner, str) or not isinstance(owner_states, dict):
                            owners_valid = False
                            break
                        parsed_owner_states: dict[str, dict[str, int]] = {}
                        for key, value in owner_states.items():
                            if key not in RUNTIME_QML_RESOURCE_STATE_KEYS:
                                owners_valid = False
                                break
                            parsed = parse_state_bucket(value)
                            if parsed is None:
                                owners_valid = False
                                break
                            parsed_owner_states[key] = parsed
                        if not owners_valid:
                            break
                        state_owners[owner] = parsed_owner_states
                if not owners_valid:
                    states_status = "invalid"
                    states_reason = "invalid_resource_running_state_owners"

            if resource_status == "available" and states_status != "available":
                resource_status = "invalid" if states_status == "invalid" else "partial"
                resource_reason = states_reason

    return {
        "schema": 1,
        "source": "qs-ipc-shell-metrics",
        "sampled_at_ms": sampled_at_ms,
        "status": "available",
        "reason": "",
        "startup_metrics": payload,
        "qml_census": census if isinstance(census, dict) else None,
        "qml_resources": {
            "status": resource_status,
            "reason": resource_reason,
            "counts": counts,
            "states": states,
            "state_owners": state_owners,
            "states_status": states_status,
            "states_reason": states_reason,
        },
    }


def _capture_live_telemetry(environment: dict[str, str], config_path: str) -> dict[str, object]:
    """Query metrics over the private benchmark IPC after performance sampling."""
    sampled_at_ms = int(time.time() * 1000)
    try:
        result = subprocess.run(
            ["qs", "-p", config_path, "ipc", "call", "shell", "metrics"],
            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _unavailable_live_telemetry(sampled_at_ms, "ipc_call_failed")
    if result.returncode != 0:
        return _unavailable_live_telemetry(sampled_at_ms, "ipc_call_failed")
    return parse_live_telemetry(result.stdout, sampled_at_ms=sampled_at_ms)


def _quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _read_int(path: Path, key: str) -> int:
    try:
        if key == "":
            return int(path.read_text().strip())
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith(key):
                return int(line.split()[1])
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        pass
    return 0


def _cgroup_memory_value(path: Path) -> int | None:
    value = _read_int(path, "")
    return value // 1024 if value >= 1024 else None


def _cgroup_memory(
    proc: Path,
    cgroup_root: Path = Path("/sys/fs/cgroup"),
) -> tuple[int | None, int | None]:
    try:
        line = next(line for line in (proc / "cgroup").read_text().splitlines() if line.startswith("0::"))
        root = cgroup_root / line[3:].lstrip("/")
        return (_cgroup_memory_value(root / "memory.current"), _cgroup_memory_value(root / "memory.peak"))
    except (FileNotFoundError, PermissionError, ProcessLookupError, StopIteration):
        return (None, None)


def _process_tree(
    root_pid: int,
    on_processes: Callable[[tuple[ProcessObservation, ...]], None] | None = None,
) -> ProcessSample | None:
    parents: dict[int, int] = {}
    start_ticks: dict[int, int] = {}
    records: dict[int, tuple[int, ...]] = {}
    cgroup_records: dict[int, tuple[int | None, int | None]] = {}
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(proc.name)
            parents[pid] = _read_int(proc / "status", "PPid:")
            rss = _read_int(proc / "status", "VmRSS:")
            voluntary = _read_int(proc / "status", "voluntary_ctxt_switches:")
            involuntary = _read_int(proc / "status", "nonvoluntary_ctxt_switches:")
            context = voluntary + involuntary
            threads = _read_int(proc / "status", "Threads:")
            stat = (proc / "stat").read_text(errors="replace")
            fields = stat[stat.rfind(") ") + 2 :].split()
            start_ticks[pid] = int(fields[19])
            user_ticks = int(fields[11])
            system_ticks = int(fields[12])
            ticks = user_ticks + system_ticks
            minor_faults = int(fields[7])
            major_faults = int(fields[9])
            faults = minor_faults + major_faults
            pss = rss
            private = 0
            rss_anon = rss_file = rss_shmem = vm_peak = vm_hwm = vm_swap = 0
            vm_peak = _read_int(proc / "status", "VmPeak:")
            vm_hwm = _read_int(proc / "status", "VmHWM:")
            vm_swap = _read_int(proc / "status", "VmSwap:")
            rss_anon = _read_int(proc / "status", "RssAnon:")
            rss_file = _read_int(proc / "status", "RssFile:")
            rss_shmem = _read_int(proc / "status", "RssShmem:")
            try:
                for line in (proc / "smaps_rollup").read_text(errors="replace").splitlines():
                    if line.startswith("Pss:"):
                        pss = int(line.split()[1])
                    elif line.startswith(("Private_Clean:", "Private_Dirty:")):
                        private += int(line.split()[1])
            except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
                pass
            read_bytes = _read_int(proc / "io", "read_bytes:")
            write_bytes = _read_int(proc / "io", "write_bytes:")
            rchar = _read_int(proc / "io", "rchar:")
            wchar = _read_int(proc / "io", "wchar:")
            syscr = _read_int(proc / "io", "syscr:")
            syscw = _read_int(proc / "io", "syscw:")
            cancelled = _read_int(proc / "io", "cancelled_write_bytes:")
            fd_count = len(list((proc / "fd").glob("*")))
            cgroup_current, cgroup_peak = _cgroup_memory(proc)
            records[pid] = (rss, pss, private, ticks, user_ticks, system_ticks, context, voluntary,
                            involuntary, faults, minor_faults, major_faults, read_bytes, write_bytes,
                            rchar, wchar, syscr, syscw, cancelled, vm_peak, vm_hwm, vm_swap, rss_anon,
                            rss_file, rss_shmem, fd_count, threads)
            cgroup_records[pid] = (cgroup_current, cgroup_peak)
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
            continue

    members = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in members and pid not in members:
                members.add(pid)
                changed = True
    if on_processes is not None:
        observations: list[ProcessObservation] = []
        for pid in members:
            if pid == root_pid or pid not in start_ticks:
                continue
            proc = Path("/proc") / str(pid)
            try:
                command = proc.joinpath("cmdline").read_bytes().split(b"\0", 1)[0].decode(errors="replace")
                command = Path(command).name if command else proc.joinpath("comm").read_text().strip()
                observations.append(ProcessObservation(pid, start_ticks[pid], command))
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
        on_processes(tuple(observations))
    rows = [records[pid] for pid in members if pid in records]
    cgroup_rows = [cgroup_records[pid] for pid in members if pid in cgroup_records]
    if not rows:
        return None
    return ProcessSample(
        rss_kb=sum(row[0] for row in rows),
        pss_kb=sum(row[1] for row in rows),
        private_kb=sum(row[2] for row in rows),
        cpu_ticks=sum(row[3] for row in rows),
        user_cpu_ticks=sum(row[4] for row in rows), system_cpu_ticks=sum(row[5] for row in rows),
        context_switches=sum(row[6] for row in rows), voluntary_context_switches=sum(row[7] for row in rows),
        involuntary_context_switches=sum(row[8] for row in rows), page_faults=sum(row[9] for row in rows),
        minor_page_faults=sum(row[10] for row in rows), major_page_faults=sum(row[11] for row in rows),
        io_read_bytes=sum(row[12] for row in rows), io_write_bytes=sum(row[13] for row in rows),
        io_rchar_bytes=sum(row[14] for row in rows), io_wchar_bytes=sum(row[15] for row in rows),
        io_syscr=sum(row[16] for row in rows), io_syscw=sum(row[17] for row in rows),
        io_cancelled_write_bytes=sum(row[18] for row in rows), vm_peak_kb=sum(row[19] for row in rows),
        vm_hwm_kb=sum(row[20] for row in rows), vm_swap_kb=sum(row[21] for row in rows),
        rss_anon_kb=sum(row[22] for row in rows), rss_file_kb=sum(row[23] for row in rows),
        rss_shmem_kb=sum(row[24] for row in rows),
        process_count=len(rows),
        fd_count=sum(row[25] for row in rows), thread_count=sum(row[26] for row in rows),
        cgroup_memory_current_kb=max((current for current, _ in cgroup_rows if current is not None), default=None),
        cgroup_memory_peak_kb=max((peak for _, peak in cgroup_rows if peak is not None), default=None),
    )


def _optional_median(samples: list[ProcessSample], field: str) -> int | None:
    values = [getattr(sample, field) for sample in samples]
    present = [value for value in values if value is not None]
    return int(statistics.median(present)) if present else None


def _optional_max(samples: list[ProcessSample], field: str) -> int | None:
    values = [getattr(sample, field) for sample in samples]
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _sample_stat(samples: list[ProcessSample]) -> ProcessSample | None:
    if not samples:
        return None

    def median(field: str) -> int:
        return int(statistics.median(getattr(sample, field) for sample in samples))

    return ProcessSample(
        rss_kb=median("rss_kb"),
        pss_kb=median("pss_kb"),
        private_kb=median("private_kb"),
        cpu_ticks=median("cpu_ticks"),
        user_cpu_ticks=median("user_cpu_ticks"), system_cpu_ticks=median("system_cpu_ticks"),
        context_switches=median("context_switches"),
        voluntary_context_switches=median("voluntary_context_switches"), involuntary_context_switches=median("involuntary_context_switches"),
        page_faults=median("page_faults"),
        minor_page_faults=median("minor_page_faults"), major_page_faults=median("major_page_faults"),
        io_read_bytes=median("io_read_bytes"),
        io_write_bytes=median("io_write_bytes"),
        io_rchar_bytes=median("io_rchar_bytes"), io_wchar_bytes=median("io_wchar_bytes"),
        io_syscr=median("io_syscr"), io_syscw=median("io_syscw"), io_cancelled_write_bytes=median("io_cancelled_write_bytes"),
        vm_peak_kb=median("vm_peak_kb"), vm_hwm_kb=median("vm_hwm_kb"), vm_swap_kb=median("vm_swap_kb"),
        rss_anon_kb=median("rss_anon_kb"), rss_file_kb=median("rss_file_kb"), rss_shmem_kb=median("rss_shmem_kb"),
        process_count=median("process_count"),
        fd_count=median("fd_count"),
        thread_count=median("thread_count"), cgroup_memory_current_kb=_optional_median(samples, "cgroup_memory_current_kb"),
        cgroup_memory_peak_kb=_optional_median(samples, "cgroup_memory_peak_kb"),
    )


def _sample_peak(samples: list[ProcessSample]) -> ProcessSample | None:
    if not samples:
        return None
    return ProcessSample(
        rss_kb=max(sample.rss_kb for sample in samples),
        pss_kb=max(sample.pss_kb for sample in samples),
        private_kb=max(sample.private_kb for sample in samples),
        cpu_ticks=max(sample.cpu_ticks for sample in samples),
        user_cpu_ticks=max(sample.user_cpu_ticks for sample in samples), system_cpu_ticks=max(sample.system_cpu_ticks for sample in samples),
        context_switches=max(sample.context_switches for sample in samples),
        voluntary_context_switches=max(sample.voluntary_context_switches for sample in samples), involuntary_context_switches=max(sample.involuntary_context_switches for sample in samples),
        page_faults=max(sample.page_faults for sample in samples),
        minor_page_faults=max(sample.minor_page_faults for sample in samples), major_page_faults=max(sample.major_page_faults for sample in samples),
        io_read_bytes=max(sample.io_read_bytes for sample in samples),
        io_write_bytes=max(sample.io_write_bytes for sample in samples),
        io_rchar_bytes=max(sample.io_rchar_bytes for sample in samples), io_wchar_bytes=max(sample.io_wchar_bytes for sample in samples),
        io_syscr=max(sample.io_syscr for sample in samples), io_syscw=max(sample.io_syscw for sample in samples), io_cancelled_write_bytes=max(sample.io_cancelled_write_bytes for sample in samples),
        vm_peak_kb=max(sample.vm_peak_kb for sample in samples), vm_hwm_kb=max(sample.vm_hwm_kb for sample in samples), vm_swap_kb=max(sample.vm_swap_kb for sample in samples),
        rss_anon_kb=max(sample.rss_anon_kb for sample in samples), rss_file_kb=max(sample.rss_file_kb for sample in samples), rss_shmem_kb=max(sample.rss_shmem_kb for sample in samples),
        process_count=max(sample.process_count for sample in samples),
        fd_count=max(sample.fd_count for sample in samples),
        thread_count=max(sample.thread_count for sample in samples), cgroup_memory_current_kb=_optional_max(samples, "cgroup_memory_current_kb"),
        cgroup_memory_peak_kb=_optional_max(samples, "cgroup_memory_peak_kb"),
    )


def start_compositor(environment: dict[str, str], log_dir: Path) -> subprocess.Popen[str]:
    """Start a private layer-shell compositor, never a host Wayland session."""
    if os.environ.get("NYXURI_CONTAINER") != "1":
        raise RuntimeError("compositor probes require NYXURI_CONTAINER=1")
    runtime = Path(environment["XDG_RUNTIME_DIR"])
    previous = set(runtime.glob("wayland-*"))
    config = log_dir / "sway.conf"
    config.write_text("output * mode 1280x720@60Hz\nseat * hide_cursor 1000\n", encoding="utf-8")
    child_env = dict(environment)
    child_env.update(WLR_BACKENDS="headless", WLR_RENDERER="pixman", WLR_LIBINPUT_NO_DEVICES="1")
    with (log_dir / "sway.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["sway", "--unsupported-gpu", "-c", str(config)], env=child_env,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True,
        )
    for _ in range(200):
        sockets = sorted(path for path in runtime.glob("wayland-*")
                         if path not in previous and not path.name.endswith(".lock"))
        if sockets:
            environment["WAYLAND_DISPLAY"] = sockets[0].name
            return process
        if process.poll() is not None:
            break
        time.sleep(0.05)
    _terminate(process)
    detail = (log_dir / "sway.log").read_text(errors="replace")[-2000:]
    raise RuntimeError("private Sway layer-shell socket did not appear: " + detail.strip())


def _terminate(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        # Reap a process that exited just before the signal, otherwise
        # Popen.returncode stays unset and a normal exit is misclassified.
        try:
            process.wait(timeout=0)
        except (subprocess.TimeoutExpired, ChildProcessError):
            pass
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)


def _run_process(
    *,
    kind: str,
    run_number: int,
    environment: dict[str, str],
    baseline_dir: Path,
    log_dir: Path,
    warm: bool = False,
) -> RunResult:
    if kind == "shell":
        command = ["/workspace/shell/nyxuri-shell", "-v"]
        marker = IPC_MARKER
        child_env = dict(environment)
        # Warm launches reuse the run-0 priming namespace through the same
        # production wrapper; bypassing it silently measures a different cache.
        namespace = 0 if warm else run_number
        for key in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            child_env[key] = f"{child_env[key]}-{namespace}"
            Path(child_env[key]).mkdir(parents=True, exist_ok=True)
    else:
        command = ["qs", "-p", str(baseline_dir), "--no-duplicate", "-v"]
        marker = re.compile(r"Configuration Loaded")
        child_env = dict(environment)

    log_path = log_dir / f"{kind}-{'warm-' if warm else ''}{run_number}.log"
    with log_path.open("w+", encoding="utf-8") as log:
        started = time.monotonic()
        started_ns = time.monotonic_ns()
        process = subprocess.Popen(
            command,
            env=child_env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
        marker_time: float | None = None
        real_first_frame_wall_ms: float | None = None
        real_first_frame_source: str | None = None
        real_first_frame_observed_after_exit = False
        internal: dict[str, float] = {}
        samples: list[ProcessSample] = []
        steady_samples: list[ProcessSample] = []
        process_tracker = ProcessLifecycleTracker()
        deadline = started + 15
        while time.monotonic() < deadline:
            now = time.monotonic()
            now_elapsed_ms = int((now - started) * 1000)
            snapshot = _process_tree(
                process.pid,
                lambda observations: process_tracker.observe(observations, now_elapsed_ms),
            )
            if snapshot is not None:
                samples.append(snapshot)
                if marker_time is not None:
                    steady_samples.append(snapshot)
            log.flush()
            text = log_path.read_text(errors="replace")
            if process.poll() is None and real_first_frame_wall_ms is None:
                real_frame = REAL_FIRST_FRAME_MARKER.search(text)
                if real_frame is not None:
                    # stdout/stderr are merged into the log file. Record the
                    # monotonic time when polling first observes the event;
                    # this avoids blocking pipe reads and their deadlock risk.
                    real_first_frame_wall_ms = (
                        time.monotonic_ns() - started_ns
                    ) / 1_000_000
                    real_first_frame_source = real_frame.group("source").strip() or "unknown"
            if marker_time is None:
                found = marker.search(text)
                if found:
                    marker_time = now
                    if kind == "shell":
                        internal["ipc_ready_ms"] = float(found.group(1))
                        for stage in ("READY", "FIRST_FRAME"):
                            stage_match = re.search(
                                rf"Stage transition -> {stage} .*elapsed:\s*(\d+)ms", text
                            )
                            if stage_match:
                                internal[f"{stage.lower()}_ms"] = float(stage_match.group(1))
            if marker_time is not None and now - marker_time >= 2:
                break
            time.sleep(0.05)
        if kind == "shell":
            live_telemetry = (
                _capture_live_telemetry(child_env, "/workspace/shell")
                if process.poll() is None
                else _unavailable_live_telemetry(int(time.time() * 1000), "shell_not_running")
            )
        else:
            live_telemetry = None
        _terminate(process)
        hz = os.sysconf("SC_CLK_TCK")
        cpu_ms = None
        user_cpu_ms = None
        system_cpu_ms = None
        cpu_util_percent = None
        if samples:
            cpu_ms = samples[-1].cpu_ticks * 1000 / hz
            user_cpu_ms = samples[-1].user_cpu_ticks * 1000 / hz
            system_cpu_ms = samples[-1].system_cpu_ticks * 1000 / hz
            elapsed_ms = max((time.monotonic() - started) * 1000, 1)
            cpu_util_percent = cpu_ms / elapsed_ms * 100
        text = log_path.read_text(errors="replace")
        if real_first_frame_wall_ms is None:
            real_frame = REAL_FIRST_FRAME_MARKER.search(text)
            if real_frame is not None:
                real_first_frame_source = real_frame.group("source").strip() or "unknown"
                real_first_frame_observed_after_exit = True
        exit_code = process.returncode
        # SIGTERM is the runner's normal teardown request. Some Quickshell builds
        # handle it and return zero, so success must not depend on one exit code.
        controlled_shutdown = exit_code in (0, -signal.SIGTERM)
        fatal_log_count = len(re.findall(
            r"\b(?:FATAL|CRITICAL)\b|QQmlApplicationEngine failed|Segmentation fault",
            text,
            re.IGNORECASE,
        ))
        startup_valid = marker_time is not None
        sample_valid = bool(samples) and bool(steady_samples)
        compiled_empty = len(re.findall(r"compiled empty", text, re.IGNORECASE))
        process_failures = classify_process_start_failures(text)
        failure_counts = process_failure_counts(process_failures)
        success = all((startup_valid, sample_valid, controlled_shutdown,
                       fatal_log_count == 0, compiled_empty == 0,
                       not has_required_process_failures(process_failures)))
        return RunResult(
            marker=marker_time is not None,
            startup_ms=(marker_time - started) * 1000 if marker_time is not None else None,
            real_first_frame_wall_ms=real_first_frame_wall_ms,
            real_first_frame_source=real_first_frame_source,
            real_first_frame_status=(
                "available" if real_first_frame_wall_ms is not None
                else "observed_after_exit" if real_first_frame_observed_after_exit
                else "unavailable"
            ),
            internal_ms=internal,
            steady=_sample_stat(steady_samples),
            peak=_sample_peak(samples),
            cpu_ms=cpu_ms,
            user_cpu_ms=user_cpu_ms,
            system_cpu_ms=system_cpu_ms,
            cpu_util_percent=cpu_util_percent,
            log_errors=len(re.findall(r"\bERROR\b", text)),
            log_warnings=len(re.findall(r"\bWARN\b", text)),
            fatal_log_count=fatal_log_count,
            compiled_empty=compiled_empty,
            process_start_failures=failure_counts["process_start_failures"],
            optional_process_start_failures=failure_counts["optional_process_start_failures"],
            required_process_start_failures=failure_counts["required_process_start_failures"],
            unattributed_process_start_failures=failure_counts["unattributed_process_start_failures"],
            process_start_failure_details=process_failures,
            process_lifecycle=process_tracker.report(process_failures),
            live_telemetry=live_telemetry,
            exit_code=exit_code,
            startup_valid=startup_valid,
            sample_valid=sample_valid,
            controlled_shutdown=controlled_shutdown,
            success=success,
            log_path=str(log_path),
        )
