#!/usr/bin/env python3
"""Run the native Nyxuri Shell benchmark inside an isolated Wayland session.

The runtime side intentionally uses only the Python standard library.  The
host launcher supplies Quickshell, Weston, Qt5Compat and Python through a
temporary Nix container; this module measures the actual process tree rather
than a mock or an offscreen QML fixture.
"""

from __future__ import annotations

import os
import re
import signal
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

IPC_METHODS: Final[tuple[str, ...]] = ("stage", "isReady", "status", "metrics")
IPC_MARKER: Final[re.Pattern[str]] = re.compile(
    r"Stage transition -> IPC_READY .*elapsed:\s*(\d+)ms"
)


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
    cgroup_memory_current_kb: int
    cgroup_memory_peak_kb: int


@dataclass(frozen=True, slots=True)
class RunResult:
    marker: bool
    startup_ms: float | None
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
    exit_code: int | None
    startup_valid: bool
    sample_valid: bool
    controlled_shutdown: bool
    success: bool
    log_path: str


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


def _cgroup_memory(proc: Path) -> tuple[int, int]:
    try:
        line = next(line for line in (proc / "cgroup").read_text().splitlines() if line.startswith("0::"))
        root = Path("/sys/fs/cgroup") / line[3:]
        return (_read_int(root / "memory.current", "") // 1024, _read_int(root / "memory.peak", "") // 1024)
    except (FileNotFoundError, PermissionError, StopIteration):
        return (0, 0)


def _process_tree(root_pid: int) -> ProcessSample | None:
    parents: dict[int, int] = {}
    records: dict[int, tuple[int, ...]] = {}
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
                            rss_file, rss_shmem, fd_count, threads, cgroup_current, cgroup_peak)
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
    rows = [records[pid] for pid in members if pid in records]
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
        cgroup_memory_current_kb=max(row[27] for row in rows), cgroup_memory_peak_kb=max(row[28] for row in rows),
    )


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
        thread_count=median("thread_count"), cgroup_memory_current_kb=median("cgroup_memory_current_kb"),
        cgroup_memory_peak_kb=median("cgroup_memory_peak_kb"),
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
        thread_count=max(sample.thread_count for sample in samples), cgroup_memory_current_kb=max(sample.cgroup_memory_current_kb for sample in samples),
        cgroup_memory_peak_kb=max(sample.cgroup_memory_peak_kb for sample in samples),
    )


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
        command = ["/workspace/shell/nyxuri-shell", "-v"] if not warm else [
            "qs", "-p", "/workspace/shell", "--no-duplicate", "-v"
        ]
        marker = IPC_MARKER
        child_env = dict(environment)
        if not warm:
            for key in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
                child_env[key] = f"{child_env[key]}-{run_number}"
                Path(child_env[key]).mkdir(parents=True, exist_ok=True)
    else:
        command = ["qs", "-p", str(baseline_dir), "--no-duplicate", "-v"]
        marker = re.compile(r"Configuration Loaded")
        child_env = dict(environment)

    log_path = log_dir / f"{kind}-{'warm-' if warm else ''}{run_number}.log"
    with log_path.open("w+", encoding="utf-8") as log:
        started = time.monotonic()
        process = subprocess.Popen(
            command,
            env=child_env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
        marker_time: float | None = None
        internal: dict[str, float] = {}
        samples: list[ProcessSample] = []
        steady_samples: list[ProcessSample] = []
        deadline = started + 15
        while time.monotonic() < deadline:
            now = time.monotonic()
            snapshot = _process_tree(process.pid)
            if snapshot is not None:
                samples.append(snapshot)
                if marker_time is not None:
                    steady_samples.append(snapshot)
            log.flush()
            text = log_path.read_text(errors="replace")
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
        process_start_failures = len(re.findall(r"Process failed to start", text, re.IGNORECASE))
        success = all((startup_valid, sample_valid, controlled_shutdown,
                       fatal_log_count == 0, compiled_empty == 0,
                       process_start_failures == 0))
        return RunResult(
            marker=marker_time is not None,
            startup_ms=(marker_time - started) * 1000 if marker_time is not None else None,
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
            process_start_failures=process_start_failures,
            exit_code=exit_code,
            startup_valid=startup_valid,
            sample_valid=sample_valid,
            controlled_shutdown=controlled_shutdown,
            success=success,
            log_path=str(log_path),
        )
