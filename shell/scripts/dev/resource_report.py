#!/usr/bin/env python3
"""Summarize resource-probe JSON without turning missing values into zero."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Iterable


RESOURCE_FIELDS = (
    "process_count", "thread_count", "fd_count", "rss_kb", "pss_kb", "private_kb",
    "vm_peak_kb", "vm_hwm_kb", "vm_swap_kb", "minor_page_faults", "major_page_faults",
    "voluntary_context_switches", "involuntary_context_switches", "io_read_bytes",
    "io_write_bytes", "io_rchar_bytes", "io_wchar_bytes", "io_syscr", "io_syscw",
    "cgroup_memory_current_kb", "cgroup_memory_peak_kb",
)


def _samples(document: dict[str, object]) -> list[dict[str, object]]:
    runtime = document.get("runtime")
    if not isinstance(runtime, dict):
        return []
    values = runtime.get("samples")
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def summarize(document: dict[str, object]) -> dict[str, object]:
    samples = _samples(document)
    metrics: dict[str, dict[str, float | int | None]] = {}
    for field in RESOURCE_FIELDS:
        values: list[float] = []
        for sample in samples:
            value = sample.get(field)
            if isinstance(value, (int, float)):
                values.append(float(value))
        metrics[field] = {
            "n": len(values),
            "first": values[0] if values else None,
            "last": values[-1] if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "median": statistics.median(values) if values else None,
            "delta": values[-1] - values[0] if len(values) >= 2 else None,
        }
    static_qml = document.get("static_qml")
    static_summary: dict[str, object] = {}
    if isinstance(static_qml, dict):
        counts = static_qml.get("counts")
        if isinstance(counts, dict):
            static_summary = {key: value for key, value in counts.items() if isinstance(value, int)}
        static_summary["qml_js_files"] = static_qml.get("qml_js_files")
        static_summary["source_bytes"] = static_qml.get("source_bytes")
    return {
        "schema": 1,
        "sample_count": len(samples),
        "resource_metrics": metrics,
        "static_qml": static_summary,
        "growth": {
            "rss_kb": metrics["rss_kb"]["delta"],
            "pss_kb": metrics["pss_kb"]["delta"],
            "process_count": metrics["process_count"]["delta"],
            "fd_count": metrics["fd_count"]["delta"],
            "thread_count": metrics["thread_count"]["delta"],
        },
    }


def markdown(summary: dict[str, object], source: str = "") -> str:
    metrics = summary.get("resource_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    lines = ["# Nyxuri Shell Resource Probe", "", f"Source: `{source or 'unknown'}`", "",
             f"Samples: **{summary.get('sample_count', 0)}**", "",
             "| Metric | First | Median | Last | Delta |", "|---|---:|---:|---:|---:|"]
    for field in RESOURCE_FIELDS:
        item = metrics.get(field)
        if not isinstance(item, dict):
            continue
        lines.append(f"| `{field}` | {item.get('first')} | {item.get('median')} | {item.get('last')} | {item.get('delta')} |")
    static = summary.get("static_qml")
    if isinstance(static, dict) and static:
        lines += ["", "## Static QML inventory", "", "| Resource | Count |", "|---|---:|"]
        for key in sorted(static):
            lines.append(f"| `{key}` | {static[key]} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("probe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.probe.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise SystemExit("probe JSON root must be an object")
    summary = summarize(document)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "resource-summary.json").write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    (args.output / "resource-summary.md").write_text(markdown(summary, args.probe.name), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
