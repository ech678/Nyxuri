#!/usr/bin/env python3
import struct
import zlib
from pathlib import Path
import sys

directory = Path(sys.argv[1])
directory.mkdir(parents=True, exist_ok=True)
width, height = 4096, 3072
for image_index in range(12):
    path = directory / f"large-{image_index:03d}.png"
    compressor = zlib.compressobj(level=1)
    with path.open("wb") as image:
        image.write(b"\x89PNG\r\n\x1a\n")
        def chunk(kind, data):
            image.write(struct.pack(">I", len(data)) + kind + data
                        + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
        chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0))
        compressed = bytearray()
        rows = []
        for y_band in range(height // 32):
            row = bytearray(width * 3)
            for x in range(width):
                offset = x * 3
                row[offset:offset + 3] = bytes(((x // 32 + image_index * 17) % 256,
                                                (y_band + image_index * 29) % 256,
                                                ((x // 64 + y_band) + image_index * 11) % 256))
            rows.append(b"\0" + row)
        for y in range(height):
            compressed.extend(compressor.compress(rows[y // 32]))
        compressed.extend(compressor.flush())
        chunk(b"IDAT", compressed)
        chunk(b"IEND", b"")
