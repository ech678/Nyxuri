#!/usr/bin/env python3
"""Launch the Shell benchmark in a disposable Nix/Podman environment."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--ipc-runs", type=int, default=20)
    parser.add_argument("--keep-volume", action="store_true")
    parser.add_argument("--nix-volume")
    args = parser.parse_args()
    if shutil.which("podman") is None:
        raise SystemExit("podman is required; no system packages are installed by this runner")
    repo = Path(__file__).resolve().parents[3]
    output = args.output or Path(tempfile.gettempdir()) / (
        "nyxuri-shell-benchmark-" + datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    output.mkdir(parents=True, exist_ok=True)
    volume = args.nix_volume or "nyxuri-benchmark-nix-" + uuid.uuid4().hex[:12]
    created_volume = args.nix_volume is None
    if created_volume:
        subprocess.run(["podman", "volume", "create", volume], check=True, stdout=subprocess.DEVNULL)
    try:
        command = [
            "podman", "run", "--rm", "--name", "nyxuri-shell-benchmark",
            "-v", f"{volume}:/nix", "-v", f"{repo}:/workspace:ro",
            "-v", f"{output}:/results", "-w", "/workspace",
            "docker.io/nixos/nix:latest", "sh", "-lc",
            "nix-shell -p quickshell weston dbus qt6Packages.qt5compat python3 "
            "--run 'python3 /workspace/shell/scripts/dev/benchmark_scenarios.py "
            f"--output /results/raw.json --runs {args.runs} --ipc-runs {args.ipc_runs}'",
        ]
        subprocess.run(command, check=True)
    finally:
        if created_volume and not args.keep_volume:
            subprocess.run(["podman", "volume", "rm", volume], check=False, stdout=subprocess.DEVNULL)
    raw = output / "raw.json"
    if not raw.exists():
        raise SystemExit(f"benchmark did not produce {raw}")
    subprocess.run([
        "python3", str(repo / "shell/scripts/dev/benchmark_report.py"),
        str(raw), "--output", str(output),
    ], check=True)
    report = json.loads((output / "benchmark.json").read_text(encoding="utf-8"))
    normalized = report["normalized"]
    print(json.dumps({
        "output": str(output),
        "composite_score_0_100": normalized["composite_score_0_100"],
        "scores_0_100": normalized["scores_0_100"],
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
