#!/usr/bin/env python3
"""Launch the Shell benchmark in a disposable Nix/Podman environment."""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from benchmark_scenarios import PROFILE_CHOICES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--ipc-runs", type=int, default=20)
    parser.add_argument("--steady-seconds", type=float, default=600.0)
    parser.add_argument("--reclaim-cycles", type=int, default=100)
    parser.add_argument("--reclaim-close-wait", type=float, default=0.1)
    parser.add_argument("--quickshell-channel", choices=("old", "new"), default="new")
    parser.add_argument(
        "--profile", choices=PROFILE_CHOICES, action="append", dest="profiles",
        help="Benchmark profile; repeat to select several (default: default-full).",
    )
    parser.add_argument("--keep-volume", action="store_true")
    parser.add_argument("--nix-volume")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.profiles = args.profiles or ["default-full"]
    if len(set(args.profiles)) != len(args.profiles):
        parser.error("--profile cannot be repeated with the same value")
    return args


def main() -> int:
    args = parse_args()
    if args.runs < 2 or args.ipc_runs < 1:
        raise SystemExit("--runs must be >= 2 and --ipc-runs must be >= 1")
    if shutil.which("podman") is None:
        raise SystemExit("podman is required; no system packages are installed by this runner")
    repo = Path(__file__).resolve().parents[3]
    git_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    git_dirty = bool(subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    ).stdout.strip())
    output = (args.output or Path(tempfile.gettempdir()) / (
        "nyxuri-shell-benchmark-" + datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    )).resolve()
    output.mkdir(parents=True, exist_ok=True)
    volume = args.nix_volume or "nyxuri-benchmark-nix-" + uuid.uuid4().hex[:12]
    created_volume = args.nix_volume is None
    if created_volume:
        subprocess.run(["podman", "volume", "create", volume], check=True, stdout=subprocess.DEVNULL)
    try:
        command = [
            "podman", "run", "--rm", "--name", "nyxuri-shell-benchmark",
            "--pid=private", "--ipc=private", "--uts=private",
            "--security-opt=no-new-privileges", "--cap-drop=all",
            # Rootless Nix populates the persistent /nix volume by changing
            # ownership and mode bits. Keep the default-deny profile and add
            # only the capabilities needed for that bootstrap operation.
            "--cap-add=CHOWN", "--cap-add=FOWNER", "--cap-add=DAC_OVERRIDE",
            "--cap-add=SETUID", "--cap-add=SETGID",
            "--tmpfs", "/tmp", "--tmpfs", "/run", "--tmpfs", "/root",
            "-e", f"NYXURI_BENCHMARK_GIT_SHA={git_sha}",
            "-e", f"NYXURI_BENCHMARK_GIT_DIRTY={'1' if git_dirty else '0'}",
            "-e", f"NYXURI_QUICKSHELL_CHANNEL={args.quickshell_channel}",
            "-v", f"{volume}:/nix", "-v", f"{repo}:/workspace:ro",
            "-v", f"{output}:/results", "-w", "/workspace",
            "docker.io/nixos/nix@sha256:d078d7153763895fce17c5fbbdeb86fcfcac414ca0ba875d413c1df57be19931",
            "sh", "-lc",
            "nix-shell /workspace/shell/scripts/dev/benchmark-shell.nix "
            f"--argstr quickshellChannel {args.quickshell_channel} "
            "--run 'mkdir -p /tmp/nyxuri-runtime && chmod 700 /tmp/nyxuri-runtime && "
            "export XDG_RUNTIME_DIR=/tmp/nyxuri-runtime && "
            "NYXURI_CONTAINER=1 dbus-run-session "
            "--config-file=/workspace/shell/scripts/dev/benchmark-dbus-session.conf -- "
            "python3 /workspace/shell/scripts/dev/benchmark_scenarios.py "
            + " ".join(f"--profile {profile}" for profile in args.profiles) + " "
            f"--output /results/raw.json --runs {args.runs} --ipc-runs {args.ipc_runs} "
            f"--steady-seconds {args.steady_seconds} --reclaim-cycles {args.reclaim_cycles} "
            f"--reclaim-close-wait {args.reclaim_close_wait} && "
            "NYXURI_CONTAINER=1 python3 /workspace/shell/scripts/dev/benchmark_compatibility.py "
            f"--output /results/compatibility-{args.quickshell_channel}.json "
            f"--channel {args.quickshell_channel} --runs 1 && "
            "NYXURI_CONTAINER=1 python3 /workspace/shell/scripts/dev/feature_matrix.py "
            "--output /results/feature-matrix.json --repo /workspace --shell /workspace/shell "
            "|| test -s /results/feature-matrix.json'",
        ]
        subprocess.run(command, check=True)
    finally:
        if created_volume and not args.keep_volume:
            subprocess.run(["podman", "volume", "rm", volume], check=False, stdout=subprocess.DEVNULL)
    raw = output / "raw.json"
    if not raw.exists():
        raise SystemExit(f"benchmark did not produce {raw}")
    channel_compatibility = output / f"compatibility-{args.quickshell_channel}.json"
    if channel_compatibility.exists():
        shutil.copy2(channel_compatibility, output / "compatibility.json")
    subprocess.run([
        "python3", str(repo / "shell/scripts/dev/benchmark_report.py"),
        str(raw), "--output", str(output),
    ], check=True)
    report = json.loads((output / "benchmark.json").read_text(encoding="utf-8"))
    normalized = report.get("normalized", {})
    if not isinstance(normalized, dict):
        normalized = {}
    print(json.dumps({
        "output": str(output),
        "profiles": args.profiles,
        "composite_score_0_100": normalized.get("composite_score_0_100"),
        "scores_0_100": normalized.get("scores_0_100", {}),
        "profile_summaries": normalized.get("profiles", {}),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
