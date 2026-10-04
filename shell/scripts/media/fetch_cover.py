#!/usr/bin/env python3
"""Download a remote cover and hand back a local path the palette can read.

Why this exists: MPRIS `artUrl` is frequently a remote URL — `kugou-tui`
reports `http://imge.kugou.com/...`, browser players report blob or http
URLs. The native palette extractor (`native/src/media_palette_backend.cpp`)
only decodes local files: its `loadImage` returns an empty QImage for
anything with a non-local scheme, so cover-driven theming silently degrades
to the fallback colour and never explains why.

Rather than teach the C++ loader about the network — which would put a
blocking HTTP fetch inside a synchronous singleton call and stall the shell
— this script does the fetch out of process and caches the result, so the
palette keeps receiving the local paths it already understands.

    usage: fetch_cover.py <artUrl> [--refresh]
    stdout: {"path": "/abs/path.jpg", "source": "cache"|"network"|"none",
             "bytes": N, "reason": "..."}

Design constraints, all inherited from the lyric fetcher for consistency:

  * Pure standard library. No requests, no Qt, no curl subprocess.
  * Always exits 0 with a parseable JSON document. A cover is decoration;
    it must never be able to fail a caller or wedge the shell.
  * Content-addressed cache keyed on the URL, so the same cover is fetched
    once no matter how many times a track is replayed. The extension is
    taken from the response, not the URL, because Kugou serves `.jpg` URLs
    that are sometimes actually PNG.
  * Size-capped. A cover is decoration, and an unbounded read from a
    third-party host is a trivial way to fill a disk.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from nyxuri_paths import NyxuriPaths  # noqa: E402

CACHE_SUBDIR = "covers"

# Generous enough for a 1000x1000 PNG, small enough that a hostile or broken
# endpoint cannot exhaust memory or disk.
MAX_BYTES = 8 * 1024 * 1024

# Covers are cosmetic; the card should never wait on one.
TIMEOUT_SECONDS = 6

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

# Magic-number sniffing. The URL's extension is not trustworthy: Kugou's
# `/stdmusic/400/....jpg` endpoints have been observed returning PNG bytes,
# and Qt picks its decoder from the content, not the name — but the palette
# needs a stable extension to re-find the file, so we normalise here.
_MAGIC = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"RIFF", ".webp"),
)


def emit(path: str, source: str, size: int, reason: str = "") -> int:
    json.dump(
        {"path": path, "source": source, "bytes": size, "reason": reason},
        sys.stdout,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


def cache_dir() -> Path:
    return NyxuriPaths.from_environment().cache_home / CACHE_SUBDIR


def cache_key(url: str) -> str:
    # The URL alone identifies the image. Including the host in the hash
    # input would be redundant since the URL already carries it.
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def sniff_extension(payload: bytes) -> str:
    for magic, ext in _MAGIC:
        if payload.startswith(magic):
            # RIFF is shared by WAV/AVI too, so confirm the WEBP form.
            if ext == ".webp" and payload[8:12] != b"WEBP":
                continue
            return ext
    return ""


def find_cached(directory: Path, key: str) -> Path | None:
    # The extension is part of the stored name, so glob rather than guess.
    for candidate in directory.glob(key + ".*"):
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def http_get(url: str) -> tuple[bytes, str]:
    """Returns (body, error). Body is empty on failure."""
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    if not host:
        return b"", "no host in url"

    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    encrypted = parsed.scheme == "https"
    port = parsed.port or (443 if encrypted else 80)
    connection_type = HTTPSConnection if encrypted else HTTPConnection

    connection = connection_type(host, port, timeout=TIMEOUT_SECONDS)
    try:
        connection.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept": "image/*"})
        response = connection.getresponse()
        if response.status != 200:
            return b"", "http %d" % response.status

        # Read one byte past the cap so an over-large body is detectable
        # rather than silently truncated into a corrupt image.
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            return b"", "exceeds %d bytes" % MAX_BYTES
        return body, ""
    except Exception as error:  # noqa: BLE001 — any failure is just "no cover"
        return b"", type(error).__name__
    finally:
        try:
            connection.close()
        except Exception:
            pass


def main() -> int:
    argv = [a for a in sys.argv[1:] if a != "--refresh"]
    url = argv[0].strip() if argv else ""
    if not url:
        return emit("", "none", 0, "no url")

    # Only http(s) reaches the network. A file:// or bare path is already
    # local, and the palette can read it directly — echoing it back saves a
    # pointless copy and keeps this script's contract simple.
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme in ("", "file"):
        return emit(url, "none", 0, "already local")

    if parsed.scheme not in ("http", "https"):
        return emit("", "none", 0, "unsupported scheme %s" % parsed.scheme)

    directory = cache_dir()
    key = cache_key(url)

    cached = find_cached(directory, key)
    if cached is not None:
        return emit(str(cached), "cache", cached.stat().st_size)

    body, error = http_get(url)
    if not body:
        return emit("", "none", 0, error)

    extension = sniff_extension(body)
    if not extension:
        return emit("", "none", 0, "not a recognised image")

    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (key + extension)
        # Write to a temporary name then rename, so a reader never observes a
        # half-written file. Same-directory rename is atomic on the platforms
        # this ships on.
        temporary = directory / (key + extension + ".part")
        temporary.write_bytes(body)
        temporary.replace(target)
    except Exception as error:  # noqa: BLE001
        return emit("", "none", 0, "write failed: %s" % type(error).__name__)

    return emit(str(target), "network", len(body))


if __name__ == "__main__":
    raise SystemExit(main())
