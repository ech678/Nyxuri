#!/usr/bin/env python3
"""Collect container-scoped runtime and QML resource observations.

The probe deliberately has no Quickshell dependency.  Run it *inside* the
benchmark container, where ``/proc`` and ``/sys/fs/cgroup`` describe only the
test namespace.  The QML scan is a source-side inventory, while process
samples are live observations; the report keeps those two evidence classes
separate instead of pretending that a static count is a runtime count.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ProcessSnapshot:
    timestamp_ms: int
    root_pid: int
    process_count: int
    thread_count: int
    fd_count: int
    rss_kb: int
    pss_kb: int
    private_kb: int
    vm_peak_kb: int
    vm_hwm_kb: int
    vm_swap_kb: int
    rss_anon_kb: int
    rss_file_kb: int
    rss_shmem_kb: int
    user_cpu_ticks: int
    system_cpu_ticks: int
    minor_page_faults: int
    major_page_faults: int
    voluntary_context_switches: int
    involuntary_context_switches: int
    io_read_bytes: int
    io_write_bytes: int
    io_rchar_bytes: int
    io_wchar_bytes: int
    io_syscr: int
    io_syscw: int
    io_cancelled_write_bytes: int
    cgroup_memory_current_kb: int | None
    cgroup_memory_peak_kb: int | None


RESOURCE_PATTERNS: dict[str, re.Pattern[str]] = {
    "singletons": re.compile(r"^\s*pragma\s+Singleton\b", re.MULTILINE),
    "timers": re.compile(r"^\s*Timer\s*\{", re.MULTILINE),
    "processes": re.compile(r"^\s*(?:component\s+\w+\s*:\s*)?Process\s*\{", re.MULTILINE),
    "fileviews": re.compile(r"^\s*FileView\s*\{", re.MULTILINE),
    "loaders": re.compile(r"^\s*Loader\s*\{", re.MULTILINE),
    "connections": re.compile(r"^\s*Connections\s*\{", re.MULTILINE),
    "repeaters": re.compile(r"^\s*Repeater\s*\{", re.MULTILINE),
    "listviews": re.compile(r"^\s*(?:ListView|GridView)\s*\{", re.MULTILINE),
    "canvas": re.compile(r"^\s*Canvas\s*\{", re.MULTILINE),
    "layers": re.compile(r"\blayer\.enabled\s*:", re.MULTILINE),
    "windows": re.compile(r"^\s*(?:FloatingWindow|PanelWindow|WlSessionLockSurface)\s*\{", re.MULTILINE),
}


def _int_file(path: Path, key: str = "") -> int | None:
    try:
        text = path.read_text(errors="replace")
        if not key:
            return int(text.strip())
        for line in text.splitlines():
            if line.startswith(key):
                return int(line.split()[1])
    except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
        return None
    return None


def _status(path: Path, key: str) -> int:
    return _int_file(path / "status", key) or 0


def _proc_stat(path: Path) -> tuple[int, int, int, int] | None:
    try:
        text = (path / "stat").read_text(errors="replace")
        fields = text[text.rfind(") ") + 2 :].split()
        return (int(fields[11]), int(fields[12]), int(fields[7]), int(fields[9]))
    except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
        return None


def _proc_io(path: Path) -> tuple[int, ...]:
    keys = (
        "read_bytes:", "write_bytes:", "rchar:", "wchar:", "syscr:",
        "syscw:", "cancelled_write_bytes:",
    )
    values: list[int] = []
    try:
        lines = (path / "io").read_text(errors="replace").splitlines()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        lines = []
    for key in keys:
        value = next((line.split()[1] for line in lines if line.startswith(key)), "0")
        try:
            values.append(int(value))
        except ValueError:
            values.append(0)
    return tuple(values)


def _pss_private(path: Path) -> tuple[int, int]:
    pss = _status(path, "VmRSS:")
    private = 0
    try:
        for line in (path / "smaps_rollup").read_text(errors="replace").splitlines():
            if line.startswith("Pss:"):
                pss = int(line.split()[1])
            elif line.startswith(("Private_Clean:", "Private_Dirty:")):
                private += int(line.split()[1])
    except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
        pass
    return pss, private


def _cgroup_values(proc_path: Path, cgroup_root: Path) -> tuple[int | None, int | None]:
    try:
        line = next(line for line in (proc_path / "cgroup").read_text().splitlines() if line.startswith("0::"))
    except (FileNotFoundError, PermissionError, ProcessLookupError, StopIteration):
        return None, None
    group = cgroup_root / line[3:].lstrip("/")
    current = _memory_kb(group / "memory.current")
    peak = _memory_kb(group / "memory.peak")
    return current, peak


def _memory_kb(path: Path) -> int | None:
    """Return cgroup memory in KiB, or None when it rounds below one KiB."""
    value = _int_file(path)
    if value is None or value < 1024:
        return None
    return value // 1024


def _descendants(root_pid: int, proc_root: Path) -> list[Path]:
    parents: dict[int, int] = {}
    paths: dict[int, Path] = {}
    for path in proc_root.iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        parent = _status(path, "PPid:")
        parents[pid] = parent
        paths[pid] = path
    members = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in members and pid not in members:
                members.add(pid)
                changed = True
    return [paths[pid] for pid in sorted(members) if pid in paths]


def sample_process_tree(
    root_pid: int,
    *,
    proc_root: Path = Path("/proc"),
    cgroup_root: Path = Path("/sys/fs/cgroup"),
) -> ProcessSnapshot | None:
    """Read one process-tree sample; return ``None`` if the root is gone."""
    rows = _descendants(root_pid, proc_root)
    if not rows:
        return None
    totals = [0] * 22
    for path in rows:
        rss = _status(path, "VmRSS:")
        pss, private = _pss_private(path)
        stat = _proc_stat(path)
        user, system, minor, major = stat or (0, 0, 0, 0)
        io = _proc_io(path)
        values = [rss, pss, private, _status(path, "VmPeak:"), _status(path, "VmHWM:"),
                  _status(path, "VmSwap:"), _status(path, "RssAnon:"), _status(path, "RssFile:"),
                  _status(path, "RssShmem:"), user, system, minor, major,
                  _status(path, "voluntary_ctxt_switches:"), _status(path, "nonvoluntary_ctxt_switches:"),
                  *io]
        for index, value in enumerate(values):
            totals[index] += value
    cgroup_current, cgroup_peak = _cgroup_values(rows[0], cgroup_root)
    fd_count = 0
    for path in rows:
        try:
            fd_count += sum(1 for _ in (path / "fd").iterdir())
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return ProcessSnapshot(
        timestamp_ms=int(time.time() * 1000), root_pid=root_pid, process_count=len(rows),
        thread_count=sum(_status(path, "Threads:") for path in rows), fd_count=fd_count,
        rss_kb=totals[0], pss_kb=totals[1], private_kb=totals[2], vm_peak_kb=totals[3],
        vm_hwm_kb=totals[4], vm_swap_kb=totals[5], rss_anon_kb=totals[6], rss_file_kb=totals[7],
        rss_shmem_kb=totals[8], user_cpu_ticks=totals[9], system_cpu_ticks=totals[10],
        minor_page_faults=totals[11], major_page_faults=totals[12],
        voluntary_context_switches=totals[13], involuntary_context_switches=totals[14],
        io_read_bytes=totals[15], io_write_bytes=totals[16], io_rchar_bytes=totals[17],
        io_wchar_bytes=totals[18], io_syscr=totals[19], io_syscw=totals[20],
        io_cancelled_write_bytes=totals[21], cgroup_memory_current_kb=cgroup_current,
        cgroup_memory_peak_kb=cgroup_peak,
    )


def _qml_files(root: Path) -> Iterable[Path]:
    yield from sorted(path for path in root.rglob("*") if path.is_file() and path.suffix in {".qml", ".js"})


def scan_qml_resources(root: Path) -> dict[str, object]:
    """Build a deterministic static inventory for QML resource-bearing objects."""
    counts = {name: 0 for name in RESOURCE_PATTERNS}
    files = 0
    source_bytes = 0
    by_file: list[dict[str, object]] = []
    for path in _qml_files(root):
        try:
            text = path.read_text(errors="replace")
        except (OSError, UnicodeError):
            continue
        files += 1
        source_bytes += path.stat().st_size
        file_counts = {name: len(pattern.findall(text)) for name, pattern in RESOURCE_PATTERNS.items()}
        for name, value in file_counts.items():
            counts[name] += value
        if any(file_counts.values()):
            by_file.append({"file": path.relative_to(root).as_posix(), **file_counts})
    # Do not persist the caller's host path in a report.  The container runner
    # mounts the source at /workspace, but the same tool is also useful in a
    # temporary host fixture and must not leak that path into artifacts.
    return {"root": "qml-source", "qml_js_files": files, "source_bytes": source_bytes,
            "counts": counts, "by_file": by_file}


def run_samples(root_pid: int, *, samples: int, interval_s: float, proc_root: Path, cgroup_root: Path) -> list[dict[str, object]]:
    if samples < 1:
        raise ValueError("samples must be >= 1")
    if interval_s < 0:
        raise ValueError("interval must be >= 0")
    output: list[dict[str, object]] = []
    for index in range(samples):
        snapshot = sample_process_tree(root_pid, proc_root=proc_root, cgroup_root=cgroup_root)
        if snapshot is None:
            break
        output.append(asdict(snapshot))
        if index + 1 < samples:
            time.sleep(interval_s)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, default=os.getpid(), help="root PID in the container namespace")
    parser.add_argument("--qml-root", type=Path, help="shell source root for static resource counts")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"))
    parser.add_argument("--cgroup-root", type=Path, default=Path("/sys/fs/cgroup"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.pid <= 0:
        parser.error("--pid must be positive")
    runtime = run_samples(args.pid, samples=args.samples, interval_s=args.interval,
                          proc_root=args.proc_root, cgroup_root=args.cgroup_root)
    payload: dict[str, object] = {"schema": 1, "scope": "container-process-tree",
                                  "runtime": {"pid": args.pid, "samples": runtime,
                                               "proc_root": str(args.proc_root),
                                               "cgroup_root": str(args.cgroup_root)}}
    if args.qml_root:
        payload["static_qml"] = scan_qml_resources(args.qml_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return 0 if runtime else 1


if __name__ == "__main__":
    raise SystemExit(main())
