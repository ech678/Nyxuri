#!/usr/bin/env python3
"""Turn raw Shell benchmark samples into raw summaries and normalized scores."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Final

from benchmark_html import render_html

FIELDS: Final[tuple[str, ...]] = (
    "startup_ms", "cpu_ms", "user_cpu_ms", "system_cpu_ms", "cpu_util_percent",
    "steady.rss_kb", "steady.pss_kb", "steady.private_kb", "steady.vm_peak_kb",
    "steady.vm_hwm_kb", "steady.vm_swap_kb", "steady.rss_anon_kb", "steady.rss_file_kb",
    "steady.rss_shmem_kb", "steady.cgroup_memory_current_kb", "steady.cgroup_memory_peak_kb",
    "peak.rss_kb", "peak.pss_kb", "peak.private_kb", "peak.vm_peak_kb", "peak.vm_hwm_kb",
    "peak.vm_swap_kb", "peak.rss_anon_kb", "peak.rss_file_kb", "peak.rss_shmem_kb",
    "peak.cgroup_memory_current_kb", "peak.cgroup_memory_peak_kb", "peak.context_switches",
    "peak.voluntary_context_switches", "peak.involuntary_context_switches", "peak.page_faults",
    "peak.minor_page_faults", "peak.major_page_faults", "peak.io_read_bytes", "peak.io_write_bytes",
    "peak.io_rchar_bytes", "peak.io_wchar_bytes", "peak.io_syscr", "peak.io_syscw",
    "peak.io_cancelled_write_bytes", "peak.process_count", "peak.thread_count", "peak.fd_count",
    "log_errors", "log_warnings", "fatal_log_count", "compiled_empty", "process_start_failures",
    "optional_process_start_failures", "required_process_start_failures",
    "startup_valid", "sample_valid", "controlled_shutdown", "success",
)


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def read_path(record: dict[str, object], path: str) -> float | None:
    value: object = record
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def summarize(records: list[dict[str, object]]) -> dict[str, dict[str, float | int | None]]:
    output: dict[str, dict[str, float | int | None]] = {}
    for field in FIELDS:
        values = [value for record in records if (value := read_path(record, field)) is not None]
        output[field] = {
            "n": len(values),
            "p50": quantile(values, 0.50),
            "p95": quantile(values, 0.95),
            "p99": quantile(values, 0.99),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    return output


def median_internal(records: list[dict[str, object]], key: str) -> float | None:
    values: list[float] = []
    for record in records:
        internal = record.get("internal_ms")
        if isinstance(internal, dict) and isinstance(internal.get(key), (int, float)):
            values.append(float(internal[key]))
    return statistics.median(values) if values else None


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def score(overhead: float | None) -> float | None:
    if overhead is None or overhead <= 0:
        return None
    return min(100.0, 100.0 / overhead)


def build_report(raw: dict[str, object]) -> dict[str, object]:
    def records(name: str) -> list[dict[str, object]]:
        value = raw.get(name, [])
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    baseline = records("baseline")
    cold = records("cold_start")
    warm = records("warm_start")
    base_summary = summarize(baseline)
    cold_summary = summarize(cold)
    warm_summary = summarize(warm)
    pairs = {
        "startup": ("startup_ms", "startup_ms"),
        "cpu": ("cpu_ms", "cpu_ms"),
        "user_cpu": ("user_cpu_ms", "user_cpu_ms"),
        "system_cpu": ("system_cpu_ms", "system_cpu_ms"),
        "cpu_util": ("cpu_util_percent", "cpu_util_percent"),
        "rss": ("steady.rss_kb", "steady.rss_kb"),
        "pss": ("steady.pss_kb", "steady.pss_kb"),
        "private_memory": ("steady.private_kb", "steady.private_kb"),
        "vm_peak": ("peak.vm_peak_kb", "peak.vm_peak_kb"),
        "vm_hwm": ("peak.vm_hwm_kb", "peak.vm_hwm_kb"),
        "vm_swap": ("peak.vm_swap_kb", "peak.vm_swap_kb"),
        "rss_anon": ("steady.rss_anon_kb", "steady.rss_anon_kb"),
        "rss_file": ("steady.rss_file_kb", "steady.rss_file_kb"),
        "rss_shmem": ("steady.rss_shmem_kb", "steady.rss_shmem_kb"),
        "cgroup_memory": ("peak.cgroup_memory_peak_kb", "peak.cgroup_memory_peak_kb"),
        "process_count": ("peak.process_count", "peak.process_count"),
        "fd_count": ("peak.fd_count", "peak.fd_count"),
        "page_faults": ("peak.page_faults", "peak.page_faults"),
        "context_switches": ("peak.context_switches", "peak.context_switches"),
        "io_read": ("peak.io_read_bytes", "peak.io_read_bytes"),
        "io_write": ("peak.io_write_bytes", "peak.io_write_bytes"),
        "io_rchar": ("peak.io_rchar_bytes", "peak.io_rchar_bytes"),
        "io_wchar": ("peak.io_wchar_bytes", "peak.io_wchar_bytes"),
        "io_syscr": ("peak.io_syscr", "peak.io_syscr"),
        "io_syscw": ("peak.io_syscw", "peak.io_syscw"),
        "io_cancelled_write": ("peak.io_cancelled_write_bytes", "peak.io_cancelled_write_bytes"),
        "log_errors": ("log_errors", "log_errors"),
        "log_warnings": ("log_warnings", "log_warnings"),
        "fatal_log_count": ("fatal_log_count", "fatal_log_count"),
        "compiled_empty": ("compiled_empty", "compiled_empty"),
        "process_start_failures": ("process_start_failures", "process_start_failures"),
        "optional_process_start_failures": ("optional_process_start_failures", "optional_process_start_failures"),
        "required_process_start_failures": ("required_process_start_failures", "required_process_start_failures"),
        "startup_valid": ("startup_valid", "startup_valid"),
        "sample_valid": ("sample_valid", "sample_valid"),
        "controlled_shutdown": ("controlled_shutdown", "controlled_shutdown"),
        "success": ("success", "success"),
    }
    ratios: dict[str, float | None] = {}
    scores: dict[str, float | None] = {}
    warm_ratios: dict[str, float | None] = {}
    warm_scores: dict[str, float | None] = {}
    for name, (base_field, shell_field) in pairs.items():
        overhead = ratio(
            cold_summary[shell_field]["p50"],
            base_summary[base_field]["p50"],
        )
        ratios[name] = overhead
        scores[name] = score(overhead)
        warm_overhead = ratio(
            warm_summary[shell_field]["p50"],
            base_summary[base_field]["p50"],
        )
        warm_ratios[name] = warm_overhead
        warm_scores[name] = score(warm_overhead)
    available = [value for value in scores.values() if value is not None and value > 0]
    composite = math.prod(available) ** (1 / len(available)) if available else None
    ipc = raw.get("ipc", {})
    ipc_scores: dict[str, float | None] = {}
    ipc_ratios: dict[str, float | None] = {}
    if isinstance(ipc, dict):
        baseline_ipc = ipc.get("baseline")
        shell_ipc = ipc.get("shell")
        baseline_ping = baseline_ipc.get("ping") if isinstance(baseline_ipc, dict) else None
        baseline_p50 = baseline_ping.get("p50_ms") if isinstance(baseline_ping, dict) else None
        if isinstance(shell_ipc, dict) and isinstance(baseline_p50, (int, float)):
            for method, data in shell_ipc.items():
                if isinstance(data, dict) and isinstance(data.get("p50_ms"), (int, float)):
                    overhead = ratio(float(data["p50_ms"]), float(baseline_p50))
                    ipc_ratios[f"ipc.{method}"] = overhead
                    ipc_scores[f"ipc.{method}"] = score(overhead)
    ratios.update(ipc_ratios)
    actions = raw.get("actions", {})
    action_scores: dict[str, float | None] = {}
    action_ratios: dict[str, float | None] = {}
    baseline_ping = None
    if isinstance(ipc, dict) and isinstance(ipc.get("baseline"), dict):
        ping = ipc["baseline"].get("ping")
        if isinstance(ping, dict) and isinstance(ping.get("p50_ms"), (int, float)):
            baseline_ping = float(ping["p50_ms"])
    if isinstance(actions, dict) and baseline_ping is not None:
        for name, data in actions.items():
            if isinstance(data, dict) and isinstance(data.get("p50_ms"), (int, float)):
                overhead = ratio(float(data["p50_ms"]), baseline_ping)
                action_ratios[f"action.{name}"] = overhead
                action_scores[f"action.{name}"] = score(overhead)
    ratios.update(action_ratios)
    return {
        "schema": 2,
        "runtime": raw.get("runtime", {}),
        "raw": {
            "baseline": base_summary,
            "cold_start": cold_summary,
            "warm_start": warm_summary,
            "ipc": ipc,
            "actions": raw.get("actions", {}),
            "long_steady_state": raw.get("long_steady_state", {}),
            "reclamation": raw.get("reclamation", {}),
            "source_profile": raw.get("source_profile", {}),
        },
        "normalized": {
            "baseline_reference": "Empty ShellRoot in the same container/runtime",
            "ratios_shell_over_baseline": ratios,
            "scores_0_100": {**scores, **ipc_scores, **action_scores},
            "warm_ratios_shell_over_baseline": warm_ratios,
            "warm_scores_0_100": warm_scores,
            "composite_score_0_100": composite,
            "internal_shell_ms": {
                "ready": median_internal(cold, "ready_ms"),
                "first_frame": median_internal(cold, "first_frame_ms"),
                "ipc_ready": median_internal(cold, "ipc_ready_ms"),
            },
        },
    }


def markdown(report: dict[str, object]) -> str:
    raw = report["raw"]
    normalized = report["normalized"]
    assert isinstance(raw, dict)
    assert isinstance(normalized, dict)
    composite = normalized.get("composite_score_0_100")
    composite_text = f"{composite:.2f}" if isinstance(composite, (int, float)) else "null"
    lines = ["# Nyxuri Shell Benchmark", "", f"Composite score: **{composite_text}/100**", ""]
    lines += ["## Raw values", "", "| Metric | Baseline p50 | Nyxuri cold p50 | Nyxuri cold p95 |", "|---|---:|---:|---:|"]
    baseline = raw["baseline"]
    cold = raw["cold_start"]
    assert isinstance(baseline, dict) and isinstance(cold, dict)
    for field in FIELDS:
        lines.append(f"| `{field}` | {baseline[field]['p50']} | {cold[field]['p50']} | {cold[field]['p95']} |")
    lines += ["", "## Normalized scores", "", "| Dimension | Ratio | Score |", "|---|---:|---:|"]
    ratios = normalized["ratios_shell_over_baseline"]
    scores = normalized["scores_0_100"]
    assert isinstance(ratios, dict) and isinstance(scores, dict)
    for name in sorted(scores):
        lines.append(f"| `{name}` | {ratios.get(name, '-') } | {scores[name]} |")
    return "\n".join(lines) + "\n"



def _sc(v: float | None) -> str:
    if v is None: return '#6b7280'
    if v >= 90: return '#10b981'
    if v >= 70: return '#f59e0b'
    if v >= 50: return '#ef4444'
    return '#991b1b'


def _dc(v: float | None) -> str:
    if v is None: return '#6b7280'
    if v > 5: return '#10b981'
    if v > 0: return '#84cc16'
    if v > -5: return '#f59e0b'
    return '#ef4444'


def _fnum(v: float | None, unit: str = '', dec: int = 1) -> str:
    if v is None: return 'N/A'
    if abs(v) >= 1_000_000: return f'{v/1_000_000:.{dec}f}M{unit}'
    if abs(v) >= 1_000: return f'{v/1_000:.{dec}f}K{unit}'
    return f'{v:.{dec}f}{unit}'


_CSS = (
    '*{margin:0;padding:0;box-sizing:border-box}'
    'body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,system-ui,sans-serif;'
    'background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#4c1d95 100%);'
    'min-height:100vh;padding:2rem;color:#1f2937}'
    '.wrap{max-width:1280px;margin:0 auto;background:#fff;border-radius:20px;'
    'box-shadow:0 24px 80px rgba(0,0,0,.45);overflow:hidden}'
    '.hdr{background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);'
    'padding:3rem 2rem;color:#fff;text-align:center}'
    '.hdr h1{font-size:2.25rem;font-weight:700;letter-spacing:-.025em;margin-bottom:.4rem}'
    '.hdr p{font-size:1rem;opacity:.65}'
    '.hero{text-align:center;padding:3rem 2rem 2rem;'
    'background:linear-gradient(180deg,#f8fafc 0%,#fff 100%)}'
    '.ring{display:inline-block;position:relative}'
    '.ring svg{display:block}'
    '.ring-val{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
    'font-size:2.75rem;font-weight:700}'
    '.hero-label{margin-top:.75rem;font-size:1.125rem;color:#6b7280;font-weight:500}'
    '.delta-badge{margin-top:.375rem;font-size:1.5rem;font-weight:600}'
    '.content{padding:2rem}'
    '.section{margin-bottom:3rem}'
    '.section-title{font-size:1.625rem;font-weight:700;color:#111827;'
    'border-bottom:3px solid #6366f1;padding-bottom:.5rem;margin-bottom:1.25rem}'
    '.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}'
    '.card{background:#f8fafc;border-radius:12px;padding:1.375rem 1.5rem;'
    'border:1px solid #e2e8f0;transition:box-shadow .2s,transform .2s}'
    '.card:hover{box-shadow:0 6px 20px rgba(0,0,0,.1);transform:translateY(-2px)}'
    '.card-label{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;'
    'color:#6b7280;font-weight:600;margin-bottom:.5rem}'
    '.card-val{font-size:1.875rem;font-weight:700;color:#111827;margin-bottom:.25rem}'
    '.card-desc{font-size:.8rem;color:#9ca3af}'
    '.group-title{font-size:1.125rem;font-weight:600;color:#374151;'
    'margin:1.5rem 0 .75rem;padding-left:.5rem;border-left:3px solid #818cf8}'
    '.bar-row{display:flex;align-items:center;padding:.5rem .625rem;'
    'background:#f9fafb;border-radius:8px;margin-bottom:.375rem;'
    'border:1px solid #f3f4f6;transition:background .15s}'
    '.bar-row:hover{background:#f0f9ff}'
    '.bar-name{flex:0 0 220px;font-size:.8rem;'
    'font-weight:500;color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}'
    '.bar-track{flex:1;margin:0 .875rem;height:18px;background:#e5e7eb;'
    'border-radius:9px;overflow:hidden}'
    '.bar-fill{height:100%;border-radius:9px;transition:width .35s ease}'
    '.bar-score{min-width:54px;text-align:right;font-weight:600;font-size:1rem}'
    '.bar-delta{min-width:56px;text-align:right;font-size:.8rem;font-weight:600;margin-left:.375rem}'
    '.rt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));'
    'gap:.875rem;margin-top:.75rem}'
    '.rt-item{padding:.875rem 1rem;background:#fff;border-radius:8px;'
    'border-left:4px solid #6366f1;box-shadow:0 1px 4px rgba(0,0,0,.06)}'
    '.rt-label{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;'
    'color:#6b7280;font-weight:600;margin-bottom:.25rem}'
    '.rt-val{font-size:1rem;font-weight:600;color:#111827}'
    '.footer{padding:1.5rem 2rem;text-align:center;background:#f8fafc;font-size:.8rem;color:#9ca3af}'
    '@media(max-width:640px){'
    'body{padding:.75rem}'
    '.hdr h1{font-size:1.5rem}'
    '.ring-val{font-size:2rem}'
    '.bar-name{flex:0 0 130px}'
    '.bar-track{margin:0 .5rem}'
    '}'
)


def html_report(
    report: dict[str, object],
    comparison: dict[str, object] | None = None,
    base_commit: str = '',
    head_commit: str = '',
) -> str:
    normalized = report.get('normalized') or {}
    raw = report.get('raw') or {}
    runtime = report.get('runtime') or {}
    if not isinstance(normalized, dict): normalized = {}
    if not isinstance(raw, dict): raw = {}
    if not isinstance(runtime, dict): runtime = {}

    composite = normalized.get('composite_score_0_100')
    cf = float(composite) if isinstance(composite, (int, float)) else 0.0
    scores_obj = normalized.get('scores_0_100') or {}
    if not isinstance(scores_obj, dict): scores_obj = {}
    scores: dict[str, object] = scores_obj

    comp_delta: float | None = None
    score_deltas: dict[str, float | None] = {}
    raw_delta: dict[str, dict[str, float | None]] = {}
    if comparison and isinstance(comparison, dict):
        cd = comparison.get('comparison')
        if isinstance(cd, dict):
            raw_cd = cd.get('composite_delta')
            comp_delta = float(raw_cd) if isinstance(raw_cd, (int, float)) else None
            sd = cd.get('score_delta')
            if isinstance(sd, dict):
                score_deltas = {
                    k: float(v) if isinstance(v, (int, float)) else None
                    for k, v in sd.items()
                }
            rd = cd.get('raw_delta')
            if isinstance(rd, dict):
                raw_delta = {k: v for k, v in rd.items() if isinstance(v, dict)}

    arc = 502.65 * cf / 100
    cc = _sc(cf)
    textra = f' — {base_commit[:8]}…{head_commit[:8]}' if base_commit and head_commit else ''

    dbadge = ''
    if comp_delta is not None:
        sign = '+' if comp_delta > 0 else ''
        dbadge = (
            '<div class="delta-badge" style="color:' + _dc(comp_delta) + ';">'
            + sign + f'{comp_delta:.2f}' + '</div>'
        )

    cold: dict[str, object] = {}
    _c = raw.get('cold_start')
    if isinstance(_c, dict):
        cold = _c

    def _p50(sec: object, field: str) -> float | None:
        if not isinstance(sec, dict): return None
        sub = sec.get(field)
        if not isinstance(sub, dict): return None
        vv = sub.get('p50')
        return float(vv) if isinstance(vv, (int, float)) else None

    def _rdspan(key: str) -> str:
        entry = raw_delta.get(key)
        if not entry: return ''
        d = entry.get('delta')
        if not isinstance(d, (int, float)): return ''
        s2 = '+' if d > 0 else ''
        col2 = '#ef4444' if d > 0 else '#10b981'
        return (
            '<span style="font-size:.85rem;color:' + col2 + ';margin-left:.5rem;">'
            + s2 + f'{d:.1f}' + '</span>'
        )

    startup_p50 = _p50(cold, 'startup_ms')
    rss_p50 = _p50(cold, 'steady.rss_kb')
    cpu_p50 = _p50(cold, 'cpu_ms')

    cards_html = ''
    for lbl, val, unit, desc, dh in [
        ('启动时间', startup_p50, 'ms', '冷启动 p50', _rdspan('cold_start.startup_ms')),
        ('稳态内存', rss_p50, 'KB', '稳态 RSS p50', _rdspan('cold_start.steady.rss_kb')),
        ('CPU 时间', cpu_p50, 'ms', '进程树 CPU p50', _rdspan('cold_start.cpu_ms')),
    ]:
        cards_html += (
            '<div class="card">'
            '<div class="card-label">' + lbl + '</div>'
            '<div class="card-val">' + _fnum(val, unit) + dh + '</div>'
            '<div class="card-desc">' + desc + '</div></div>'
        )

    GROUPS: list[tuple[str, list[str]]] = [
        ('性能', ['startup', 'cpu', 'user_cpu', 'system_cpu', 'cpu_util']),
        ('内存', ['rss', 'pss', 'private_memory', 'vm_peak', 'vm_hwm',
                   'rss_anon', 'rss_file', 'rss_shmem', 'cgroup_memory']),
        ('系统', ['process_count', 'fd_count', 'context_switches',
                   'page_faults', 'io_read', 'io_write']),
        ('可靠性', ['log_errors', 'log_warnings', 'compiled_empty',
                     'process_start_failures', 'success']),
        ('IPC', sorted(k for k in scores if isinstance(k, str) and k.startswith('ipc.'))),
        ('交互', sorted(k for k in scores if isinstance(k, str) and k.startswith('action.'))),
    ]

    bars_html = ''
    for gname, keys in GROUPS:
        present = [k for k in keys if k in scores]
        if not present:
            continue
        bars_html += '<h3 class="group-title">' + gname + '</h3>'
        def _score_value(key: str) -> float:
            value = scores[key]
            return float(value) if isinstance(value, (int, float)) else 0.0
        for k in sorted(
            present,
            key=_score_value,
            reverse=True,
        ):
            sv = scores[k]
            sf = float(sv) if isinstance(sv, (int, float)) else 0.0
            col = _sc(sf)
            w = min(100.0, max(0.0, sf))
            dv = score_deltas.get(k)
            dp = ''
            if dv is not None:
                s3 = '+' if dv > 0 else ''
                dp = (
                    '<span class="bar-delta" style="color:' + _dc(dv) + ';">'
                    + s3 + f'{dv:.1f}' + '</span>'
                )
            bars_html += (
                '<div class="bar-row">'
                '<span class="bar-name">' + k + '</span>'
                '<div class="bar-track">'
                '<div class="bar-fill" style="width:' + f'{w:.1f}' + '%;background:' + col + ';"></div>'
                '</div>'
                '<span class="bar-score" style="color:' + col + ';">' + f'{sf:.1f}' + '</span>'
                + dp + '</div>'
            )

    rt_html = ''.join(
        '<div class="rt-item">'
        '<div class="rt-label">' + lbl + '</div>'
        '<div class="rt-val">' + str(v) + '</div></div>'
        for lbl, v in [
            ('Quickshell', runtime.get('quickshell', 'N/A')),
            ('Wayland 后端', runtime.get('wayland_backend', 'N/A')),
            ('渲染器', runtime.get('renderer', 'N/A')),
            ('Qt Quick', runtime.get('qt_quick_backend', 'N/A')),
            ('测试轮数', str(runtime.get('runs', 'N/A'))),
            ('IPC 次数', str(runtime.get('ipc_runs', 'N/A'))),
        ]
    )

    title = 'Nyxuri Shell Benchmark' + textra
    return (
        '<!DOCTYPE html>'
        '<html lang="zh-CN"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>' + title + '</title>'
        '<style>' + _CSS + '</style>'
        '</head><body>'
        '<div class="wrap">'
        '<div class="hdr"><h1>' + title + '</h1>'
        '<p>性能测试报告</p></div>'
        '<div class="hero">'
        '<div class="ring">'
        '<svg width="180" height="180" viewBox="0 0 180 180">'
        '<circle cx="90" cy="90" r="80" fill="none" stroke="#e5e7eb" stroke-width="14"/>'
        '<circle cx="90" cy="90" r="80" fill="none" stroke="' + cc + '" stroke-width="14" '
        'stroke-dasharray="' + f'{arc:.2f}' + ' 502.65" stroke-linecap="round" '
        'transform="rotate(-90 90 90)"/>'
        '</svg>'
        '<div class="ring-val" style="color:' + cc + ';">' + f'{cf:.1f}' + '</div>'
        '</div>'
        '<div class="hero-label">综合得分（0 - 100）</div>'
        + dbadge
        + '</div>'
        '<div class="content">'
        '<div class="section">'
        '<h2 class="section-title">关键指标</h2>'
        '<div class="cards">' + cards_html + '</div></div>'
        '<div class="section">'
        '<h2 class="section-title">详细评分</h2>'
        + bars_html
        + '</div>'
        '<div class="section">'
        '<h2 class="section-title">运行环境</h2>'
        '<div class="rt-grid">' + rt_html + '</div></div>'
        '</div>'
        '<div class="footer">Generated by Nyxuri Shell Benchmark Suite</div>'
        '</div></body></html>'
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--html", action="store_true", help="Kept for compatibility; HTML is always generated")
    args = parser.parse_args()
    input_error: str | None = None
    try:
        loaded = json.loads(args.raw.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        loaded = {}
        input_error = f"invalid raw benchmark JSON: {error}"
    if not isinstance(loaded, dict):
        loaded = {}
        input_error = input_error or "invalid raw benchmark root: expected object"
    report = build_report(loaded)
    if input_error:
        report["input_error"] = input_error
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "benchmark.json").write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    (args.output / "benchmark.md").write_text(markdown(report), encoding="utf-8")
    (args.output / "benchmark.html").write_text(
        render_html(loaded, report),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
