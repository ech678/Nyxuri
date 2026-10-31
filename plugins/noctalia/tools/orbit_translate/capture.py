"""Wayland PRIMARY Selection capture."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class CaptureError(Exception):
    category: str
    message: str

    def __str__(self) -> str:
        return self.message


def normalize_text(text: str, max_chars: int) -> str:
    if max_chars < 1:
        raise CaptureError("invalid", "文本长度上限无效")
    normalized = text.strip()
    if not normalized:
        raise CaptureError("empty", "没有读取到选中文本")
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return normalized[:max_chars]
    return normalized[: max_chars - 3].rstrip() + "..."


def capture_primary(timeout_ms: int, max_chars: int, runner=None) -> str:
    run = runner or subprocess.run
    try:
        result = run(
            ["wl-paste", "--primary", "--no-newline"],
            capture_output=True,
            timeout=timeout_ms / 1000,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CaptureError("missing_dependency", "找不到 wl-paste，请安装 wl-clipboard") from exc
    except subprocess.TimeoutExpired as exc:
        raise CaptureError("timeout", "读取选区超时") from exc
    except OSError as exc:
        raise CaptureError("system", "读取选区失败") from exc

    if result.returncode != 0:
        raise CaptureError("empty", "当前没有可用的 PRIMARY 选区")
    output = result.stdout
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    if not isinstance(output, str):
        raise CaptureError("invalid", "选区内容格式无效")
    return normalize_text(output, max_chars)
