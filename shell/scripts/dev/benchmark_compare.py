#!/usr/bin/env python3
"""Compare Nyxuri Shell benchmark results between two commits (or two existing report dirs).

Usage examples
--------------
# Run fresh benchmarks for two commits and compare:
  python3 shell/scripts/dev/benchmark_compare.py \
      --base <commit-a> --head <commit-b> --output /tmp/compare

# Compare two already-existing benchmark.json reports:
  python3 shell/scripts/dev/benchmark_compare.py \
      --base-report /tmp/run-a/benchmark.json \
      --head-report /tmp/run-b/benchmark.json \
      --output /tmp/compare

Outputs
-------
  <output>/comparison.json   machine-readable delta
  <output>/comparison.html   visual report (requires benchmark_report.html_report)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _run_benchmark(
    commit: str,
    output: Path,
    runs: int,
    ipc_runs: int,
    nix_volume: str | None,
) -> Path:
    """Checkout <commit> via git-worktree, run benchmark-shell.py, return benchmark.json."""
    worktree = output / f"worktree-{commit[:12]}"
    wt_out = output / f"bench-{commit[:12]}"
    wt_out.mkdir(parents=True, exist_ok=True)

    repo = Path(__file__).resolve().parents[3]
    # Create an isolated worktree so HEAD stays untouched.
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), commit],
        check=True,
    )
    try:
        script = worktree / "shell" / "scripts" / "dev" / "benchmark-shell.py"
        cmd = [
            sys.executable, str(script),
            "--output", str(wt_out),
            "--runs", str(runs),
            "--ipc-runs", str(ipc_runs),
        ]
        if nix_volume:
            cmd += ["--nix-volume", nix_volume]
        subprocess.run(cmd, check=True)
    finally:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
            check=False,
        )

    bj = wt_out / "benchmark.json"
    if not bj.exists():
        raise FileNotFoundError(f"benchmark.json not produced under {wt_out}")
    return bj


def _delta(
    base: dict[str, object],
    head: dict[str, object],
) -> dict[str, object]:
    """Produce a comparison dict: per-dimension score and raw deltas, composite delta."""

    def _float(d: object, key: str) -> float | None:
        if not isinstance(d, dict):
            return None
        v = d.get(key)
        return float(v) if isinstance(v, (int, float)) else None

    def _sub(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return a - b

    bn = base.get("normalized") or {}
    hn = head.get("normalized") or {}
    if not isinstance(bn, dict):
        bn = {}
    if not isinstance(hn, dict):
        hn = {}

    bs = bn.get("scores_0_100") or {}
    hs = hn.get("scores_0_100") or {}
    if not isinstance(bs, dict):
        bs = {}
    if not isinstance(hs, dict):
        hs = {}

    all_keys = sorted(set(bs) | set(hs))
    score_delta: dict[str, float | None] = {}
    for k in all_keys:
        bv = bs.get(k)
        hv = hs.get(k)
        bf = float(bv) if isinstance(bv, (int, float)) else None
        hf = float(hv) if isinstance(hv, (int, float)) else None
        score_delta[k] = _sub(hf, bf)

    composite_delta = _sub(
        _float(hn, "composite_score_0_100"),
        _float(bn, "composite_score_0_100"),
    )

    # Raw metric deltas for key fields (p50 values from cold_start).
    RAW_FIELDS = [
        "startup_ms", "cpu_ms", "user_cpu_ms",
        "steady.rss_kb", "steady.pss_kb",
        "peak.vm_peak_kb", "peak.vm_hwm_kb",
        "peak.context_switches", "peak.page_faults",
        "peak.io_read_bytes", "peak.io_write_bytes",
        "log_errors", "log_warnings",
    ]
    br = (base.get("raw") or {})
    hr = (head.get("raw") or {})
    if not isinstance(br, dict):
        br = {}
    if not isinstance(hr, dict):
        hr = {}

    bc = br.get("cold_start") or {}
    hc = hr.get("cold_start") or {}
    if not isinstance(bc, dict):
        bc = {}
    if not isinstance(hc, dict):
        hc = {}

    def _p50(sec: object, field: str) -> float | None:
        if not isinstance(sec, dict):
            return None
        parts = field.split(".", 1)
        if len(parts) == 1:
            sub = sec.get(field)
        else:
            outer = sec.get(parts[0])
            sub = outer.get(parts[1]) if isinstance(outer, dict) else None
        if not isinstance(sub, dict):
            return None
        v = sub.get("p50")
        return float(v) if isinstance(v, (int, float)) else None

    raw_delta: dict[str, object] = {}
    for field in RAW_FIELDS:
        bv2 = _p50(bc, field)
        hv2 = _p50(hc, field)
        raw_delta[f"cold_start.{field}"] = {
            "base": bv2,
            "head": hv2,
            "delta": _sub(hv2, bv2),
            "ratio": (hv2 / bv2 if bv2 and bv2 != 0 else None),
        }

    return {
        "composite_delta": composite_delta,
        "score_delta": score_delta,
        "raw_delta": raw_delta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--base", metavar="COMMIT",
                      help="base commit ref (run fresh benchmark)")
    mode.add_argument("--base-report", metavar="JSON", type=Path,
                      help="path to an existing benchmark.json for base")

    mode2 = parser.add_mutually_exclusive_group()
    mode2.add_argument("--head", metavar="COMMIT",
                       help="head commit ref (run fresh benchmark; default: HEAD)")
    mode2.add_argument("--head-report", metavar="JSON", type=Path,
                       help="path to an existing benchmark.json for head")

    parser.add_argument("--output", type=Path,
                        default=Path(tempfile.gettempdir()) / ("nyxuri-compare-" + uuid.uuid4().hex[:8]))
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--ipc-runs", type=int, default=20)
    parser.add_argument("--nix-volume", metavar="VOLUME",
                        help="reuse an existing podman Nix volume")
    args = parser.parse_args()

    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)

    # Resolve base report.
    if args.base_report:
        base_json = args.base_report
        base_commit = str(base_json.parent.name)
    elif args.base:
        print(f"[compare] Running benchmark for base={args.base} …", flush=True)
        base_json = _run_benchmark(args.base, output, args.runs, args.ipc_runs, args.nix_volume)
        base_commit = args.base
    else:
        parser.error("One of --base or --base-report is required")
        return 1

    # Resolve head report.
    if args.head_report:
        head_json = args.head_report
        head_commit = str(head_json.parent.name)
    else:
        head_ref = args.head or "HEAD"
        print(f"[compare] Running benchmark for head={head_ref} …", flush=True)
        head_json = _run_benchmark(head_ref, output, args.runs, args.ipc_runs, args.nix_volume)
        head_commit = head_ref

    base_report = json.loads(base_json.read_text(encoding="utf-8"))
    head_report = json.loads(head_json.read_text(encoding="utf-8"))

    comparison_data = {
        "base_commit": base_commit,
        "head_commit": head_commit,
        "base_report": base_report,
        "head_report": head_report,
        "comparison": _delta(base_report, head_report),
    }

    comp_out = output / "comparison.json"
    comp_out.write_text(json.dumps(comparison_data, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"[compare] Written: {comp_out}", flush=True)

    # HTML report.
    try:
        sys.path.insert(0, str(_HERE))
        from benchmark_report import html_report
        html = html_report(
            head_report,
            comparison=comparison_data,
            base_commit=base_commit,
            head_commit=head_commit,
        )
        html_out = output / "comparison.html"
        html_out.write_text(html, encoding="utf-8")
        print(f"[compare] Written: {html_out}", flush=True)
    except Exception as exc:
        print(f"[compare] WARNING: HTML report failed: {exc}", file=sys.stderr)

    comp_delta = comparison_data["comparison"].get("composite_delta")
    print(json.dumps({
        "output": str(output),
        "base_commit": base_commit,
        "head_commit": head_commit,
        "composite_delta": comp_delta,
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
