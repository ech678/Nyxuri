#!/usr/bin/env python3
"""Measure matched 2,000-row NotificationService loads in a private container."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from typing import Literal, TypedDict


class Fixture(TypedDict):
    notificationId: int
    localKind: str
    filePath: str
    appIcon: str
    appName: str
    body: str
    desktopEntry: str
    image: str
    receivedAt: int
    summary: str
    urgency: int


class MemorySample(TypedDict):
    pid: int
    pss_kb: int
    private_kb: int
    rss_kb: int
    status_rss_kb: int


class ProfileSample(MemorySample):
    sample_index: int


class ProfileResult(TypedDict):
    schema: int
    mode: str
    history_count: int
    baseline_source: str
    fixture_schema: list[str]
    readiness: dict[str, bool | int]
    samples: list[ProfileSample]


class Metrics(TypedDict):
    pss_kb: float
    private_kb: float
    rss_kb: float


def fixture(count: int) -> list[Fixture]:
    return [
        {
            "notificationId": 1000000 + index,
            "localKind": "",
            "filePath": "",
            "appIcon": "/tmp/notification-fixture/icon.svg",
            "appName": "Representative Application",
            "body": "B" * 256,
            "desktopEntry": "representative-application.desktop",
            "image": "/tmp/notification-fixture/image.png",
            "receivedAt": 1762548900000 + index,
            "summary": "Representative notification summary",
            "urgency": 1,
        }
        for index in range(count)
    ]


def sample_process(pid: int) -> MemorySample:
    status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    values = {line.split(":", 1)[0]: int(line.split()[1]) for line in status.splitlines()
              if line.startswith(("VmRSS:",))}
    pss = private = rss = 0
    for line in Path(f"/proc/{pid}/smaps_rollup").read_text(encoding="utf-8").splitlines():
        if line.startswith("Pss:"):
            pss = int(line.split()[1])
        elif line.startswith("Rss:"):
            rss = int(line.split()[1])
        elif line.startswith(("Private_Clean:", "Private_Dirty:")):
            private += int(line.split()[1])
    return {"pid": pid, "pss_kb": pss, "private_kb": private, "rss_kb": rss,
            "status_rss_kb": values.get("VmRSS", 0)}


def run_case(workspace: Path, output: Path, mode: Literal["baseline", "candidate"],
             baseline_source: str) -> ProfileResult:
    root = Path("/tmp") / f"notification-connections-{mode}"
    shutil.rmtree(root, ignore_errors=True)
    shell = root / "shell"
    shutil.copytree(workspace / "shell", shell)
    if mode == "baseline":
        (shell / "services/NotificationService.qml").write_text(baseline_source, encoding="utf-8")
    (shell / "shell.qml").write_text(
        (workspace / "shell/tests/qml/NotificationConnectionsProbe/shell.qml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    xdg = {name: root / name.lower() for name in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                                                  "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR")}
    for path in xdg.values():
        path.mkdir(parents=True, exist_ok=True)
    xdg["XDG_RUNTIME_DIR"].chmod(0o700)
    state = xdg["XDG_STATE_HOME"] / "nyxuri/notifications"
    state.mkdir(parents=True)
    records = fixture(2000)
    (state / "notifications.json").write_text(json.dumps(records, separators=(",", ":")), encoding="utf-8")

    qt5compat = next(Path("/nix/store").glob("*qt5compat-*/lib/qt-6/qml"), None)
    if qt5compat is None:
        raise RuntimeError("qt5compat QML import path is unavailable")
    wayland = f"notification-connections-{mode}-wayland"
    environment = os.environ.copy()
    environment.update({key: str(value) for key, value in xdg.items()})
    environment.update({
        "NYXURI_SHELL_STATE_HOME": str(xdg["XDG_STATE_HOME"] / "nyxuri"),
        "WAYLAND_DISPLAY": wayland,
        "QT_QPA_PLATFORM": "wayland",
        "QT_QUICK_BACKEND": "software",
        "QSG_RHI_BACKEND": "software",
        "QML_IMPORT_PATH": f"{shell / 'tests/qml'}:{shell}:{qt5compat}:{shell / 'ui/shapes'}",
        "QML2_IMPORT_PATH": f"{shell / 'tests/qml'}:{shell}:{qt5compat}:{shell / 'ui/shapes'}",
        "NOTIFICATION_CONNECTIONS_PROFILE": "1",
    })

    weston_log = output / f"{mode}-weston.log"
    qs_log = output / f"{mode}-quickshell.log"
    with weston_log.open("w", encoding="utf-8") as stream:
        weston = subprocess.Popen(
            ["weston", "--backend=headless", "--renderer=pixman", "--no-config",
             f"--socket={wayland}", "--idle-time=0"],
            stdout=stream, stderr=subprocess.STDOUT, env=environment,
        )
    qs = None
    try:
        socket = xdg["XDG_RUNTIME_DIR"] / wayland
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not socket.exists():
            if weston.poll() is not None:
                raise RuntimeError(f"Weston exited {weston.returncode}; see {weston_log}")
            time.sleep(0.05)
        if not socket.exists():
            raise RuntimeError(f"Weston readiness socket missing; see {weston_log}")

        with qs_log.open("w", encoding="utf-8") as stream:
            qs = subprocess.Popen(["qs", "-p", str(shell), "--no-duplicate"],
                                  stdout=stream, stderr=subprocess.STDOUT, env=environment)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                stream.flush()
                log = qs_log.read_text(encoding="utf-8", errors="replace")
                if "NOTIFICATION_PROFILE_READY {\"ready\":true,\"count\":2000}" in log:
                    break
                if qs.poll() is not None:
                    raise RuntimeError(f"Quickshell exited {qs.returncode} before readiness; see {qs_log}")
                time.sleep(0.05)
            else:
                raise RuntimeError(f"history readiness/count marker missing; see {qs_log}")

            time.sleep(1.5)
            samples: list[ProfileSample] = []
            for index in range(7):
                try:
                    sample = sample_process(qs.pid)
                except (FileNotFoundError, ProcessLookupError):
                    raise RuntimeError("Quickshell process disappeared during sampling") from None
                samples.append({"sample_index": index, **sample})
                if index < 6:
                    time.sleep(0.5)
    finally:
        if qs is not None and qs.poll() is None:
            qs.send_signal(signal.SIGTERM)
            try:
                qs.wait(timeout=5)
            except subprocess.TimeoutExpired:
                qs.kill()
                qs.wait(timeout=2)
        weston.send_signal(signal.SIGTERM)
        try:
            weston.wait(timeout=5)
        except subprocess.TimeoutExpired:
            weston.kill()
            weston.wait(timeout=2)

    result: ProfileResult = {
        "schema": 1,
        "mode": mode,
        "history_count": len(records),
        "baseline_source": "git HEAD NotificationService.qml",
        "fixture_schema": list(records[0]),
        "readiness": {"ready": True, "count": 2000},
        "samples": samples,
    }
    (output / f"{mode}-raw.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("/workspace"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    baseline = subprocess.run(
        ["git", "-C", str(args.workspace), "show", "HEAD:shell/services/NotificationService.qml"],
        check=True, capture_output=True, text=True,
    ).stdout
    sys.path.insert(0, str(args.workspace / "shell/scripts/dev"))
    results = [run_case(args.workspace, args.output, mode, baseline)
               for mode in ("baseline", "candidate")]
    summaries: dict[str, Metrics] = {}
    for result in results:
        rows = result["samples"]
        summaries[result["mode"]] = {
            "pss_kb": round(sum(row["pss_kb"] for row in rows) / len(rows), 1),
            "private_kb": round(sum(row["private_kb"] for row in rows) / len(rows), 1),
            "rss_kb": round(sum(row["rss_kb"] for row in rows) / len(rows), 1),
        }
    comparison = {
        "history_count": 2000,
        "readiness_equal": results[0]["readiness"] == results[1]["readiness"],
        "fixture_schema_equal": results[0]["fixture_schema"] == results[1]["fixture_schema"],
        "baseline": summaries["baseline"],
        "candidate": summaries["candidate"],
        "delta_kb_candidate_minus_baseline": {
            key: round(summaries["candidate"][key] - summaries["baseline"][key], 1)
            for key in summaries["baseline"]
        },
    }
    (args.output / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, separators=(",", ":")))
    return 0 if comparison["readiness_equal"] and comparison["fixture_schema_equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
