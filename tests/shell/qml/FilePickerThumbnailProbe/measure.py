#!/usr/bin/env python3
import json
import subprocess
import sys
import time
from pathlib import Path

output, *command = sys.argv[1:]
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
samples = []
while process.poll() is None:
    parents = {}
    for proc in Path("/proc").iterdir():
        if proc.name.isdigit():
            try:
                stat = (proc / "stat").read_text().split()
                parents[int(proc.name)] = int(stat[3])
            except (OSError, ValueError, IndexError):
                pass
    descendants = {process.pid}
    while True:
        children = {pid for pid, parent in parents.items() if parent in descendants}
        updated = descendants | children
        if updated == descendants:
            break
        descendants = updated
    pss = private = 0
    for pid in descendants:
        try:
            fields = (Path("/proc") / str(pid) / "smaps_rollup").read_text().splitlines()
            values = {line.split(":", 1)[0]: int(line.split()[1]) for line in fields
                      if line.startswith(("Pss:", "Private_Clean:", "Private_Dirty:"))}
            pss += values.get("Pss", 0)
            private += values.get("Private_Clean", 0) + values.get("Private_Dirty", 0)
        except (OSError, ValueError, IndexError):
            pass
    samples.append({"elapsed_s": round(time.monotonic(), 3), "processes": sorted(descendants),
                    "pss_kib": pss, "private_kib": private})
    time.sleep(0.05)
stdout, _ = process.communicate()
Path(output).write_text(json.dumps({"exit_code": process.returncode, "samples": samples}, indent=2)
                        + "\n", encoding="utf-8")
print(stdout, end="")
if process.returncode:
    raise SystemExit(process.returncode)
