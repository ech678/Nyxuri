#!/usr/bin/env python3
"""Extract the instrumented Canvas PNG data URL from one probe log."""

from __future__ import annotations

import base64
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: extract_png.py PROBE_LOG OUTPUT_PNG", file=sys.stderr)
        return 2
    log_path, output_path = map(Path, sys.argv[1:])
    marker = "WEATHER_CANVAS_PNG_DATA "
    matches = [line.split(marker, 1)[1].strip()
               for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
               if marker in line]
    if len(matches) != 1 or not matches[0].startswith("data:image/png;base64,"):
        print(f"WEATHER_CANVAS_PNG_EXTRACT_FAIL matches={len(matches)}", file=sys.stderr)
        return 1
    try:
        payload = base64.b64decode(matches[0].split(",", 1)[1], validate=True)
    except ValueError as error:
        print(f"WEATHER_CANVAS_PNG_EXTRACT_FAIL invalid_base64={error}", file=sys.stderr)
        return 1
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        print("WEATHER_CANVAS_PNG_EXTRACT_FAIL invalid_png_signature", file=sys.stderr)
        return 1
    output_path.write_bytes(payload)
    print(f"WEATHER_CANVAS_PNG_EXTRACT_PASS path={output_path} bytes={len(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
