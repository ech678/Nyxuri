import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from nyxuri_shell.color import hex_of, rgb_to_lstar, rgb_to_oklch

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".avif")
VIDEO_EXT = (".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4v")
SAMPLE_EDGE = 64
FFMPEG_TIMEOUT = 20


@dataclass(frozen=True)
class SourceColor:
    rgb: Tuple[int, int, int]
    population: float
    chroma: float
    lstar: float

    @property
    def hex(self) -> str:
        return hex_of(self.rgb)


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXT


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXT


def _run(cmd: List[str], timeout: int = FFMPEG_TIMEOUT) -> Optional[bytes]:
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if res.returncode != 0 or not res.stdout:
        return None
    return res.stdout


def decode_rgb(path: Path, edge: int = SAMPLE_EDGE) -> Optional[bytes]:
    if not shutil.which("ffmpeg"):
        return None
    seek = ["-ss", "0.5"] if is_video(path) else []
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        *seek, "-i", str(path),
        "-frames:v", "1",
        "-vf", f"scale={edge}:{edge}:force_original_aspect_ratio=decrease",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    return _run(cmd)


def _quantize(data: bytes, bits: int = 5) -> Tuple[List[Tuple[int, int, int]], List[int]]:
    shift = 8 - bits
    keys: dict = {}
    order: List[Tuple[int, int, int]] = []
    counts: List[int] = []
    for i in range(0, len(data) - 2, 3):
        k = (data[i] >> shift, data[i + 1] >> shift, data[i + 2] >> shift)
        idx = keys.get(k)
        if idx is None:
            keys[k] = len(order)
            order.append(((k[0] << shift) | (1 << (shift - 1)),
                          (k[1] << shift) | (1 << (shift - 1)),
                          (k[2] << shift) | (1 << (shift - 1))))
            counts.append(1)
        else:
            counts[idx] += 1
    return order, counts


def extract_source_colors(data: bytes, top: int = 8) -> List[SourceColor]:
    palette, counts = _quantize(data)
    if not palette:
        return []
    total = sum(counts) or 1
    scored: List[Tuple[float, int]] = []
    for idx, count in enumerate(counts):
        rgb = palette[idx]
        _, chroma, _ = rgb_to_oklch(rgb)
        lstar = rgb_to_lstar(rgb)
        pop = count / total
        usable = 20.0 <= lstar <= 90.0
        if not usable:
            continue
        score = pop * (0.35 + chroma * 6.0)
        scored.append((score, idx))
    scored.sort(reverse=True)

    picked: List[SourceColor] = []
    for _, idx in scored:
        rgb = palette[idx]
        _, chroma, hue = rgb_to_oklch(rgb)
        lstar = rgb_to_lstar(rgb)
        if any(
            abs(hue - rgb_to_oklch(c.rgb)[2]) < 25.0
            and abs(chroma - c.chroma) < 0.05
            for c in picked
        ):
            continue
        picked.append(SourceColor(rgb, counts[idx] / total, chroma, lstar))
        if len(picked) >= top:
            break

    if not picked:
        for _, idx in scored[:top]:
            rgb = palette[idx]
            _, chroma, _ = rgb_to_oklch(rgb)
            picked.append(SourceColor(rgb, counts[idx] / total, chroma, rgb_to_lstar(rgb)))
    return picked


def best_source_color(colors: Iterable[SourceColor]) -> Optional[SourceColor]:
    best: Optional[SourceColor] = None
    best_score = -1.0
    for c in colors:
        score = c.population * (0.3 + c.chroma * 8.0)
        if score > best_score:
            best_score = score
            best = c
    return best


def pick_from_file(path: Path) -> Optional[SourceColor]:
    data = decode_rgb(path)
    if not data:
        return None
    return best_source_color(extract_source_colors(data))


def scan_directory(root: Path, limit: int = 500) -> List[Path]:
    if not root.is_dir():
        return []
    found: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            p = Path(dirpath) / name
            if is_image(p) or is_video(p):
                found.append(p)
                if len(found) >= limit:
                    return found
    return found


def thumbnail(path: Path, dest: Path, size: int = 256) -> bool:
    if not shutil.which("ffmpeg"):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    seek = ["-ss", "0.5"] if is_video(path) else []
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *seek, "-i", str(path),
        "-frames:v", "1",
        "-vf", f"scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size}",
        str(dest),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return res.returncode == 0 and dest.is_file()


def _self_check() -> List[str]:
    problems: List[str] = []
    tmp = Path(tempfile.mkdtemp())
    try:
        if shutil.which("ffmpeg"):
            png = tmp / "solid.png"
            made = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-f", "lavfi", "-i", "color=c=0x6750A4:s=64x64:d=1",
                 "-frames:v", "1", str(png)],
                capture_output=True, timeout=FFMPEG_TIMEOUT, check=False,
            )
            if made.returncode == 0:
                color = pick_from_file(png)
                if color is None:
                    problems.append("solid png produced no color")
                else:
                    r, g, b = color.rgb
                    if abs(r - 0x67) > 12 or abs(g - 0x50) > 12 or abs(b - 0xA4) > 12:
                        problems.append(f"solid color drift: {color.hex}")

        raw = bytes([0x67, 0x50, 0xA4] * 100)
        colors = extract_source_colors(raw)
        if not colors:
            problems.append("raw decode produced no colors")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)
    print("ok")
