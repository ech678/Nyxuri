#!/usr/bin/env python3
"""Compare decoded PNG pixels without external image dependencies."""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


def decode_png(path: Path) -> tuple[int, int, int, bytes]:
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")

    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    offset = 8
    while offset < len(payload):
        length = struct.unpack_from(">I", payload, offset)[0]
        kind = payload[offset + 4:offset + 8]
        data = payload[offset + 8:offset + 8 + length]
        offset += length + 12
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", data)
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            break

    if bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
        raise ValueError(f"unsupported PNG format: depth={bit_depth}, type={color_type}, interlace={interlace}")
    assert width is not None and height is not None and color_type is not None
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(compressed)
    rows: list[bytes] = []
    previous = bytes(stride)
    for row_index in range(height):
        start = row_index * (stride + 1)
        filter_type = raw[start]
        encoded = raw[start + 1:start + 1 + stride]
        row = bytearray(stride)
        for index, value in enumerate(encoded):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                estimate = left + up - upper_left
                left_distance = abs(estimate - left)
                up_distance = abs(estimate - up)
                corner_distance = abs(estimate - upper_left)
                predictor = left if left_distance <= up_distance and left_distance <= corner_distance else (
                    up if up_distance <= corner_distance else upper_left
                )
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}")
            row[index] = (value + predictor) & 0xFF
        previous = bytes(row)
        rows.append(previous)
    return width, height, channels, b"".join(rows)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compare_png.py BASELINE OPTIMIZED", file=sys.stderr)
        return 2
    base = decode_png(Path(sys.argv[1]))
    optimized = decode_png(Path(sys.argv[2]))
    if base[:3] != optimized[:3]:
        print(f"WEATHER_CANVAS_PIXEL_MISMATCH dimensions_or_channels={base[:3]} vs {optimized[:3]}")
        return 1

    pixel_size = base[2]
    differing_pixels = 0
    differing_channels = 0
    max_delta = 0
    for offset in range(0, len(base[3]), pixel_size):
        deltas = [abs(a - b) for a, b in zip(base[3][offset:offset + pixel_size],
                                             optimized[3][offset:offset + pixel_size])]
        if any(deltas):
            differing_pixels += 1
            differing_channels += sum(delta != 0 for delta in deltas)
            max_delta = max(max_delta, *deltas)

    if differing_pixels:
        print("WEATHER_CANVAS_PIXEL_MISMATCH"
              f" dimensions={base[0]}x{base[1]} differing_pixels={differing_pixels}"
              f" differing_channels={differing_channels} max_channel_delta={max_delta}")
        return 1
    print("WEATHER_CANVAS_PIXEL_EQUIVALENT"
          f" dimensions={base[0]}x{base[1]} channels={pixel_size}"
          " differing_pixels=0 differing_channels=0 max_channel_delta=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
