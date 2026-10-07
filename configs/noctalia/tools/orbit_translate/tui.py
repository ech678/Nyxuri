"""Small stdlib-only terminal editor for Orbit Translate settings."""

from __future__ import annotations

import curses
from dataclasses import dataclass
import queue
import threading
import unicodedata
from typing import Callable
from urllib.parse import urlsplit

from .config import AI_PROVIDER_TYPES
from .settings import SettingsDocument, SettingsError
from .tui_style import TerminalStyle, load_terminal_style


_KEY_MASK = "********"
_PREVIEW_LIMIT = 320
_PROTOCOL_LABELS = {
    "openai_compatible": "OpenAI Chat Completions",
    "openai_responses": "OpenAI Responses",
    "anthropic": "Anthropic Messages",
    "gemini": "Gemini GenerateContent",
    "ollama": "Ollama",
}
_ERROR_STATUS = {
    "timeout": "请求超时",
    "network": "网络不可达",
    "configuration": "Provider 配置未完成",
    "parse": "返回内容无法识别",
    "empty": "Provider 未返回译文",
    "remote": "服务拒绝了请求",
    "http": "服务拒绝了请求",
    "system": "Provider 执行失败",
    "unknown": "测试失败",
}
_CANCEL = object()
_UNCHANGED = object()
_ACTION_KEYS = ("toggle", "edit", "add", "catalog", "key", "test", "delete", "save", "help", "quit")
_TITLE_ICON = "󰗊"
_KV_WIDTH = 6
_ACTION_HINTS = {
    "toggle": ("Space", "启停"),
    "edit": ("e", "编辑"),
    "add": ("a", "新增"),
    "catalog": ("m", "模型"),
    "key": ("K", "钥匙串"),
    "test": ("t", "测试"),
    "delete": ("d", "删除"),
    "save": ("s", "保存"),
    "help": ("?", "帮助"),
    "quit": ("q", "退出"),
}
_ACTION_LABELS = {
    "toggle": "␠切换",
    "edit": "e编辑",
    "add": "a新增",
    "catalog": "m目录",
    "key": "K密钥",
    "test": "t测试",
    "delete": "d删除",
    "save": "s保存",
    "help": "?帮助",
    "quit": "q退出",
}


def display_width(value: str) -> int:
    """Return terminal columns used by text, counting wide CJK characters."""

    return sum(
        0 if unicodedata.combining(char) or unicodedata.category(char) in {"Cf", "Mn", "Me"}
        else 2 if unicodedata.east_asian_width(char) in {"F", "W"}
        else 1
        for char in value
    )


def clip_columns(value: str, columns: int) -> str:
    """Clip display text without splitting a wide terminal character."""

    if columns <= 0:
        return ""
    value = _safe_text(value)
    result: list[str] = []
    used = 0
    for char in value:
        width = display_width(char)
        if used + width > columns:
            break
        result.append(char)
        used += width
    return "".join(result)


def _wrap_columns(value: object, columns: int) -> list[str]:
    """Wrap sanitized text without splitting wide terminal cells."""

    if columns <= 0:
        return []
    raw = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    paragraphs = [
        "".join(char for char in paragraph if unicodedata.category(char) != "Cc")
        for paragraph in raw.split("\n")
    ]
    lines: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        used = 0
        for word in words:
            word_width = display_width(word)
            if line and used + 1 + word_width <= columns:
                line += " " + word
                used += 1 + word_width
                continue
            if line:
                lines.append(line)
                line, used = "", 0
            for char in word:
                char_width = display_width(char)
                if line and used + char_width > columns:
                    lines.append(line)
                    line, used = "", 0
                if char_width <= columns:
                    line += char
                    used += char_width
        if line:
            lines.append(line)
    return lines or [""]


def _tail_columns(value: str, columns: int) -> str:
    """Return the visible end of an edited value within a cell-width budget."""

    if columns <= 0:
        return ""
    result: list[str] = []
    used = 0
    for char in reversed(_safe_text(value)):
        width = display_width(char)
        if used + width > columns:
            break
        result.append(char)
        used += width
    return "".join(reversed(result))


def _input_view_text(label: str, value: str) -> str:
    if "Base URL" in label:
        if not value:
            return ""
        scheme_end = value.find("://")
        if scheme_end < 0:
            return "URL 输入中"
        remainder = value[scheme_end + 3:]
        authority = remainder.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        if "/" not in remainder and "@" not in authority:
            return "URL 输入中"
        return safe_url(value)
    return _safe_text(value)


def safe_url(value: str) -> str:
    """Hide URL userinfo, query parameters, and fragments before display."""

    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "地址已配置"
        hostname = parsed.hostname
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"
        try:
            port = f":{parsed.port}" if parsed.port is not None else ""
        except ValueError:
            port = ""
        return _safe_text(f"{parsed.scheme}://{hostname}{port}{parsed.path}")
    except (TypeError, ValueError):
        return "地址已配置"


def _safe_text(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return "".join(char for char in text if unicodedata.category(char) != "Cc")


def _put(
    screen: object,
    row: int,
    column: int,
    value: str,
    width: int,
    style: int = 0,
) -> None:
    rows, columns = screen.getmaxyx()
    if row < 0 or row >= rows or column < 0 or column >= columns - 1:
        return
    clipped = clip_columns(value, min(width, columns - column - 1))
    if not clipped:
        return
    try:
        if style:
            try:
                screen.addstr(row, column, clipped, style)
            except TypeError:
                # Lightweight fake screens used by callers may expose only addstr(y, x, text).
                screen.addstr(row, column, clipped)
        else:
            screen.addstr(row, column, clipped)
    except curses.error:
        # ncurses may reject a write ending exactly on the lower-right cell.
        pass


def _style(styles: TerminalStyle | None, role: str) -> int:
    return getattr(styles, role, 0) if styles is not None else 0


def _put_segments(
    screen: object,
    row: int,
    column: int,
    segments: list[tuple[str, int]],
    width: int,
) -> int:
    """Write styled segments left to right within ``width`` columns."""

    used = 0
    for text, style in segments:
        if used >= width or not text:
            continue
        _put(screen, row, column + used, text, width - used, style)
        used += min(display_width(_safe_text(text)), width - used)
    return used


def _rule(screen: object, row: int, left: int, width: int, styles: TerminalStyle | None) -> None:
    if width > 0:
        _put(screen, row, left, "─" * width, width, _style(styles, "border"))


def _section(title: str) -> str:
    return f"── {title} ──"


def _draw_panel(
    screen: object,
    top: int,
    left: int,
    height: int,
    width: int,
    title: str,
    styles: TerminalStyle | None,
) -> None:
    """Rounded NyxURI dialog frame with the title set into the top border."""

    if height < 2 or width < 2:
        return
    rows, columns = screen.getmaxyx()
    width = min(width, columns - left)
    height = min(height, rows - top)
    if width < 2 or height < 2:
        return
    border = _style(styles, "border")
    _put(screen, top, left, "╭" + "─" * (width - 2) + "╮", width, border)
    for row in range(top + 1, top + height - 1):
        _put(screen, row, left, "│", 1, border)
        _put(screen, row, left + width - 1, "│", 1, border)
    _put(screen, top + height - 1, left, "╰" + "─" * (width - 2) + "╯", width, border)
    label = clip_columns(f" {title} ", max(0, width - 6))
    if label.strip():
        _put(screen, top, left + 3, label, width - 6, _style(styles, "title"))


def _dialog_lines(paragraphs: list[str], width: int) -> list[str]:
    """Wrap dialog paragraphs, keeping list indentation (``"  2. …"``) aligned."""

    lines: list[str] = []
    for paragraph in paragraphs:
        indent = paragraph[: len(paragraph) - len(paragraph.lstrip(" "))]
        wrapped = _wrap_columns(paragraph, max(1, width - len(indent)))
        lines.extend(indent + line if line else line for line in wrapped)
    return lines


def _draw_centered_dialog(
    screen: object,
    title: str,
    paragraphs: list[str],
    footer: str,
    styles: TerminalStyle | None,
) -> tuple[int, int, int, int, list[str]]:
    rows, columns = screen.getmaxyx()
    try:
        screen.clearok(True)
    except (AttributeError, curses.error):
        pass
    screen.erase()
    width = max(1, min(columns, max(30, min(columns - 2, 68))))
    inner_width = max(1, width - 4)
    content = _dialog_lines(paragraphs, inner_width)
    content_height = max(1, min(len(content), max(1, rows - 4)))
    height = min(rows, max(4, content_height + 4))
    top = max(0, (rows - height) // 2)
    left = max(0, (columns - width) // 2)
    _draw_panel(screen, top, left, height, width, title, styles)
    visible = content[: max(0, height - 4)]
    for offset, line in enumerate(visible):
        if line.startswith("❯ "):
            _put_segments(
                screen, top + 2 + offset, left + 2,
                [("❯ ", _style(styles, "title")), (line[2:], _style(styles, "strong"))],
                width - 4,
            )
        else:
            _put(screen, top + 2 + offset, left + 2, line, width - 4, _style(styles, "text"))
    _put(screen, top + height - 2, left + 2, footer, width - 4, _style(styles, "subtle"))
    screen.refresh()
    return top, left, height, width, visible


def _provider_value(provider: dict[str, object], key: str, default: object = "") -> object:
    value = provider.get(key, default)
    return default if value is None else value


def _auth_marker(provider: dict[str, object]) -> str:
    if _provider_value(provider, "api_key_secret") or _provider_value(provider, "api_key_env"):
        return f"认证 {_KEY_MASK}"
    return "无认证"


def _provider_line(provider: dict[str, object]) -> str:
    name = _safe_text(_provider_value(provider, "name", "未命名渠道"))
    provider_type = _safe_text(_provider_value(provider, "type", "未知类型"))
    enabled = "启用" if bool(_provider_value(provider, "enabled", False)) else "停用"
    return f"[{enabled}] {name} · {provider_type} · {_auth_marker(provider)}"


@dataclass(frozen=True)
class _Job:
    kind: str
    values: tuple[object, ...]


@dataclass(frozen=True)
class _Completion:
    kind: str
    succeeded: bool
    result: object = None
    provider_index: int | None = None


class _OperationWorker:
    """Serialize keychain and network work away from the curses thread."""

    def __init__(self, document: SettingsDocument):
        self._document = document
        self._jobs: queue.Queue[_Job | None] = queue.Queue(maxsize=1)
        self._completed: queue.Queue[_Completion] = queue.Queue(maxsize=1)
        self._busy = False
        self._kind: str | None = None
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._work, name="orbit-settings-io", daemon=True)
        self._thread.start()

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._busy

    @property
    def kind(self) -> str | None:
        with self._lock:
            return self._kind

    def submit(self, kind: str, *values: object) -> bool:
        with self._lock:
            if self._busy:
                return False
            self._busy = True
            self._kind = kind
            try:
                self._jobs.put_nowait(_Job(kind, tuple(values)))
            except queue.Full:
                self._busy = False
                self._kind = None
                return False
        return True

    def poll(self) -> _Completion | None:
        try:
            completion = self._completed.get_nowait()
        except queue.Empty:
            return None
        with self._lock:
            self._busy = False
            self._kind = None
        return completion

    def stop(self) -> None:
        self._stopped.set()
        try:
            self._jobs.put_nowait(None)
        except queue.Full:
            # The worker checks _stopped immediately after its in-flight job.
            pass

    def _work(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                return
            provider_index = (
                job.values[0]
                if job.kind == "probe" and job.values and isinstance(job.values[0], int)
                else None
            )
            try:
                if job.kind == "probe":
                    result = self._document.probe(*job.values)
                elif job.kind == "set-key":
                    self._document.set_key(*job.values)
                    result = None
                else:
                    result = None
                completion = _Completion(job.kind, True, result, provider_index)
            except Exception:
                # Exceptions can contain URLs, request bodies, or credentials.
                completion = _Completion(job.kind, False, provider_index=provider_index)
            try:
                self._completed.put_nowait(completion)
            except queue.Full:
                pass
            # Do not keep the last job's key or sample text in the idle worker.
            job = None
            if self._stopped.is_set():
                return


def _get_key(screen: object) -> object:
    reader = getattr(screen, "get_wch", None)
    return reader() if callable(reader) else screen.getch()


def _prompt(
    screen: object,
    label: str,
    *,
    default: str = "",
    limit: int = 300,
    styles: TerminalStyle | None = None,
    dialog_title: str | None = None,
) -> str | None:
    return _read_input_dialog(
        screen,
        label,
        default=default,
        limit=limit,
        secret=False,
        styles=styles,
        dialog_title=dialog_title or f"设置 · {label}",
    )


def _read_input_dialog(
    screen: object,
    label: str,
    *,
    default: str,
    limit: int,
    secret: bool,
    styles: TerminalStyle | None,
    dialog_title: str = "输入设置",
) -> str | None:
    value = list(default)
    if secret:
        try:
            curses.noecho()
        except curses.error:
            pass
    redraw = True
    while True:
        if redraw:
            top, left, height, width, _visible = _draw_centered_dialog(
                screen,
                dialog_title,
                [label, ""],
                "Enter 确认 · Esc 取消",
                styles,
            )
            input_row = top + height - 3
            label_fits = len(_wrap_columns(label, max(1, width - 4))) <= max(0, height - 5)
            input_width = max(1, width - 8)
            shown = _KEY_MASK if secret else _input_view_text(label, "".join(value))
            visible_tail = _tail_columns(shown, max(1, input_width - 2))
            if not secret and display_width(shown) > display_width(visible_tail):
                visible_tail = "…" + _tail_columns(shown, max(1, input_width - 3))
            if label_fits:
                _put_segments(
                    screen, input_row, left + 2,
                    [("❯ ", _style(styles, "title")), (visible_tail, _style(styles, "strong"))],
                    width - 4,
                )
            else:
                _put(screen, input_row, left + 2, "请放大窗口以读完说明", width - 4, _style(styles, "warn"))
            try:
                screen.move(input_row, min(left + width - 3, left + 4 + display_width(visible_tail)))
            except (AttributeError, curses.error):
                pass
            screen.refresh()
            redraw = False
        try:
            key = _get_key(screen)
        except (curses.error, OSError):
            continue
        if key == curses.KEY_RESIZE:
            redraw = True
            continue
        if key in (27, "\x1b"):
            return None
        if not label_fits:
            # Never confirm a truncated destructive/keychain warning.
            continue
        if key in (10, 13, "\n", "\r"):
            return "".join(value)
        if key in (curses.KEY_BACKSPACE, 8, 127, "\b", "\x7f"):
            if value:
                value.pop()
                redraw = True
            continue
        if key in (21, "\x15"):
            value.clear()
            redraw = True
            continue
        if isinstance(key, str) and len(key) == 1 and key.isprintable():
            if len(value) < limit:
                value.append(key)
                redraw = True
        elif isinstance(key, int) and 0 <= key <= 255:
            char = chr(key)
            if char.isprintable() and len(value) < limit:
                value.append(char)
                redraw = True


def _prompt_secret(
    screen: object,
    label: str,
    *,
    limit: int = 4096,
    styles: TerminalStyle | None = None,
) -> str | None:
    try:
        return _read_input_dialog(
            screen,
            label,
            default="",
            limit=limit,
            secret=True,
            styles=styles,
            dialog_title=f"钥匙串 · {label}",
        )
    finally:
        try:
            # wrapper restores terminal state at exit; keep manual prompts
            # and navigation in noecho mode for the rest of this session.
            curses.noecho()
        except curses.error:
            pass


def _confirm(
    screen: object,
    prompt: str,
    *,
    default: bool = False,
    styles: TerminalStyle | None = None,
) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        value = _prompt(screen, prompt + suffix, limit=1, styles=styles, dialog_title="确认操作")
        if value is None:
            return False
        answer = value.strip().lower()
        if not answer:
            return default
        if answer in {"y", "是"}:
            return True
        if answer in {"n", "否"}:
            return False


def _select_protocol(
    screen: object,
    *,
    default: str | None = None,
    notice: str = "",
    styles: TerminalStyle | None = None,
) -> str | None:
    selected = AI_PROVIDER_TYPES.index(default) if default in AI_PROVIDER_TYPES else 0
    redraw = True
    while True:
        if redraw:
            paragraphs = []
            if default in AI_PROVIDER_TYPES:
                paragraphs.append("当前：" + _PROTOCOL_LABELS.get(default, default))
            if notice:
                paragraphs.extend(notice.splitlines())
            paragraphs.append("方向键选择 · 数字直达 · Enter 确认 · Esc 取消")
            for index, provider_type in enumerate(AI_PROVIDER_TYPES):
                label = _PROTOCOL_LABELS.get(provider_type, provider_type)
                marker = "❯ " if index == selected else "  "
                paragraphs.append(f"{marker}{index + 1}. {label}")
            footer = "Enter 保留当前协议" if default in AI_PROVIDER_TYPES else "Enter 选择协议"
            top, left, height, width, _visible = _draw_centered_dialog(screen, "选择 AI 协议", paragraphs, footer, styles)
            options_fit = len(_dialog_lines(paragraphs, max(1, width - 4))) <= height - 4
            if not options_fit:
                _put(screen, top + height - 2, left + 2, "请放大窗口 · Esc 取消", width - 4, _style(styles, "warn"))
                screen.refresh()
            redraw = False
        try:
            key = _get_key(screen)
        except (curses.error, OSError):
            continue
        if key == curses.KEY_RESIZE:
            redraw = True
            continue
        if key in (27, "\x1b"):
            return None
        if not options_fit:
            continue
        if key in (curses.KEY_UP, ord("k"), "k"):
            next_selected = max(0, selected - 1)
            redraw = redraw or next_selected != selected
            selected = next_selected
            continue
        if key in (curses.KEY_DOWN, ord("j"), "j"):
            next_selected = min(len(AI_PROVIDER_TYPES) - 1, selected + 1)
            redraw = redraw or next_selected != selected
            selected = next_selected
            continue
        if key in (10, 13, "\n", "\r", getattr(curses, "KEY_ENTER", -1)):
            return AI_PROVIDER_TYPES[selected]
        if isinstance(key, str) and key.isdigit():
            index = int(key)
        elif isinstance(key, int) and ord("0") <= key <= ord("9"):
            index = key - ord("0")
        else:
            continue
        if 1 <= index <= len(AI_PROVIDER_TYPES):
            return AI_PROVIDER_TYPES[index - 1]


@dataclass(frozen=True)
class _CatalogWorkerState:
    snapshot: object | None
    phase: str


class _CatalogWorker:
    """Load the optional public catalog once, away from the curses thread."""

    def __init__(self, store_factory: Callable[[], object] | None = None):
        self._store_factory = store_factory
        self._store: object | None = None
        self._jobs: queue.Queue[str | None] = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._started = False
        self._snapshot: object | None = None
        self._phase = "idle"

    def open(self) -> None:
        """Start the cache read and initial load only on the first `m` action."""

        with self._lock:
            if self._started:
                return
            self._started = True
            self._phase = "loading"
            thread = threading.Thread(
                target=self._work,
                name="orbit-settings-catalog",
                daemon=True,
            )
            thread.start()
            self._jobs.put_nowait("open")

    def state(self) -> _CatalogWorkerState:
        with self._lock:
            return _CatalogWorkerState(self._snapshot, self._phase)

    def refresh(self) -> bool:
        """Request one refresh; never overlap an existing catalog operation."""

        self.open()
        with self._lock:
            if self._phase in {"loading", "refreshing"}:
                return False
            self._phase = "refreshing"
            try:
                self._jobs.put_nowait("refresh")
            except queue.Full:
                self._phase = "error"
                return False
        return True

    def stop(self) -> None:
        self._stop_requested.set()
        try:
            self._jobs.put_nowait(None)
        except queue.Full:
            # The current operation checks the stop flag before taking another job.
            pass

    def _get_store(self) -> object:
        if self._store is None:
            factory = self._store_factory
            if factory is None:
                # Keep even importing the catalog module behind the explicit m action.
                from .catalog import CatalogStore

                factory = CatalogStore
            self._store = factory()
        return self._store

    def _publish(self, *, snapshot: object = _UNCHANGED, phase: str) -> None:
        with self._lock:
            if snapshot is not _UNCHANGED:
                self._snapshot = snapshot
            self._phase = phase

    def _load(self) -> None:
        try:
            cached = self._get_store().load_cached()
        except Exception:
            cached = None
        if cached is not None:
            self._publish(snapshot=cached, phase="ready")
            if not bool(getattr(cached, "stale", True)):
                return
        if self._stop_requested.is_set():
            return
        self._publish(phase="refreshing")
        self._refresh()

    def _refresh(self) -> None:
        try:
            snapshot = self._get_store().refresh()
        except Exception:
            # Never display exception text: transport errors may contain remote data.
            self._publish(phase="error")
        else:
            self._publish(snapshot=snapshot, phase="ready")

    def _work(self) -> None:
        while not self._stop_requested.is_set():
            job = self._jobs.get()
            if job is None or self._stop_requested.is_set():
                return
            if job == "open":
                self._load()
            elif job == "refresh":
                self._refresh()


def _catalog_status(state: _CatalogWorkerState) -> str:
    snapshot = state.snapshot
    stale = bool(getattr(snapshot, "stale", False)) if snapshot is not None else False
    if state.phase == "loading":
        return "正在读取本地目录缓存…"
    if state.phase == "refreshing":
        if snapshot is None:
            return "正在获取公共目录；Esc 可取消选择"
        return "后台刷新中，当前继续使用过期缓存" if stale else "后台刷新中，当前目录可继续使用"
    if state.phase == "error":
        if snapshot is not None:
            return "目录刷新失败；继续使用缓存（离线可用）"
        return "目录不可用；Ctrl-R 重试，Esc 返回后按 a 手动添加"
    if snapshot is not None and stale:
        return "使用过期缓存；离线时仍可搜索，Ctrl-R 刷新"
    if snapshot is not None:
        return "目录已就绪；Ctrl-R 刷新"
    return "目录尚未载入；Ctrl-R 重试或 Esc 退出"


def _catalog_item_line(item: object, *, kind: str) -> str:
    name = _safe_text(getattr(item, "name", ""))
    item_id = _safe_text(getattr(item, "id", ""))
    if kind == "provider":
        models = getattr(item, "models", ())
        return f"{name} · {item_id} · {len(models)} 个文本模型"
    family = _safe_text(getattr(item, "family", ""))
    protocol = _safe_text(getattr(item, "protocol", ""))
    detail = " · ".join(value for value in (family, protocol) if value)
    return f"{name} · {item_id}" + (f" · {detail}" if detail else "")


def _catalog_item_detail(item: object | None, *, kind: str) -> str:
    if item is None:
        return ""
    item_id = _safe_text(getattr(item, "id", ""))
    if kind == "provider":
        protocol = _safe_text(getattr(item, "protocol", ""))
        return f"ID：{item_id}" + (f" · 目录协议：{protocol}" if protocol else "")
    base_url = safe_url(str(getattr(item, "base_url", "")))
    return " · ".join(
        value for value in (
            f"ID：{item_id}",
            _safe_text(getattr(item, "family", "")),
            _safe_text(getattr(item, "protocol", "")),
            base_url,
        ) if value
    )


def _draw_catalog_picker(
    screen: object,
    *,
    kind: str,
    query: str,
    items: tuple[object, ...],
    results: tuple[object, ...],
    selected: int,
    state: _CatalogWorkerState,
    styles: TerminalStyle | None = None,
) -> int:
    rows, columns = screen.getmaxyx()
    screen.erase()
    width = columns - 1
    title = "选择 models.dev 提供商" if kind == "provider" else "选择文本模型"
    _put_segments(screen, 0, 1, [(_TITLE_ICON + " ", _style(styles, "key")), (title, _style(styles, "title"))], width - 1)
    _put(screen, 1, 1, _catalog_status(state), width - 1, _style(styles, "muted"))
    count = f"匹配 {len(results)} / {len(items)}"
    count_width = display_width(count)
    search_width = max(1, width - 1 - (count_width + 2 if width - 1 > count_width + 12 else 0))
    _put_segments(
        screen, 2, 1,
        [("❯ ", _style(styles, "title")), ("搜索：" + query, _style(styles, "strong"))],
        search_width,
    )
    if search_width < width - 1:
        _put(screen, 2, width - count_width, count, count_width, _style(styles, "subtle"))
    _rule(screen, 3, 0, width, styles)

    start = 4
    available = max(0, rows - 7)
    selected = min(max(0, selected), max(0, len(results) - 1))
    scroll = max(0, selected - available + 1) if available and selected >= available else 0
    if available:
        for offset, item in enumerate(results[scroll:scroll + available]):
            chosen = scroll + offset == selected
            _put_segments(
                screen,
                start + offset,
                1,
                [
                    ("❯ " if chosen else "  ", _style(styles, "title")),
                    (
                        _catalog_item_line(item, kind=kind),
                        _style(styles, "strong") if chosen else _style(styles, "text"),
                    ),
                ],
                width - 1,
            )
    _rule(screen, rows - 3, 0, width, styles)
    detail = _catalog_item_detail(results[selected], kind=kind) if results else ""
    if not results:
        if state.snapshot is None:
            empty = "等待公共目录载入；Ctrl-R 刷新，Esc 取消"
        elif query:
            empty = "没有匹配项；继续输入或按 Ctrl-U 清空"
        else:
            empty = "没有可用的文本模型；Esc 返回后按 a 手动添加"
        _put(screen, rows - 2, 1, empty, width - 1, _style(styles, "muted"))
    else:
        _put(screen, rows - 2, 1, detail, width - 1, _style(styles, "muted"))
    _draw_hints(
        screen,
        rows - 1,
        1,
        (("↑/↓", "移动"), ("输入", "筛选"), ("Ctrl-U", "清空"), ("Enter", "选择"), ("Ctrl-R", "刷新"), ("Esc", "取消")),
        width - 1,
        styles,
    )
    screen.refresh()
    return scroll


def _choose_catalog_record(
    screen: object,
    worker: _CatalogWorker,
    *,
    kind: str,
    items: object | None = None,
    styles: TerminalStyle | None = None,
) -> object | None:
    from .catalog import MAX_QUERY_LENGTH, MAX_RESULTS

    if kind == "provider":
        worker.open()
    query = ""
    selected = 0
    frozen_items: tuple[object, ...] | None = tuple(items) if items is not None else None
    index: object | None = None
    snapshot: object | None = None
    results: tuple[object, ...] = ()
    searched_query: str | None = None
    rendered_frame: object = None
    while True:
        state = worker.state()
        selected_id = None
        if kind == "provider" and state.snapshot is not None and state.snapshot is not snapshot:
            # Update the browsable directory while retaining the highlighted provider ID.
            if results:
                selected_id = getattr(results[selected], "id", None)
            snapshot = state.snapshot
            frozen_items = tuple(getattr(state.snapshot, "providers", ()))
            index = None
            searched_query = None
        if index is None and frozen_items is not None:
            index = _make_catalog_index(frozen_items)
        if index is not None and query != searched_query:
            try:
                results = index.search(query, limit=MAX_RESULTS)
            except Exception:
                results = ()
            searched_query = query
            if selected_id is not None:
                selected = next(
                    (position for position, item in enumerate(results) if getattr(item, "id", None) == selected_id),
                    0,
                )
        selected = min(selected, max(0, len(results) - 1))
        frame = (query, selected, id(state.snapshot), state.phase, screen.getmaxyx())
        if frame != rendered_frame:
            _draw_catalog_picker(
                screen,
                kind=kind,
                query=query,
                items=frozen_items or (),
                results=results,
                selected=selected,
                state=state,
                styles=styles,
            )
            rendered_frame = frame
        try:
            key = _get_key(screen)
        except (curses.error, OSError):
            continue
        if key == curses.KEY_RESIZE:
            continue
        if key in (27, "\x1b"):
            return None
        if key in (curses.KEY_UP, 16, "\x10"):
            selected = max(0, selected - 1)
            continue
        if key in (curses.KEY_DOWN, 14, "\x0e"):
            selected = min(max(0, len(results) - 1), selected + 1)
            continue
        if key in (curses.KEY_BACKSPACE, 8, 127, "\b", "\x7f"):
            query = query[:-1]
            selected = 0
            continue
        if key in (21, "\x15"):
            query = ""
            selected = 0
            continue
        if key in (18, "\x12"):
            worker.refresh()
            continue
        if key in (10, 13, "\n", "\r", getattr(curses, "KEY_ENTER", -1)):
            if results:
                return results[selected]
            continue
        char = key if isinstance(key, str) else chr(key) if isinstance(key, int) and 32 <= key <= 255 else ""
        if len(char) == 1 and char.isprintable() and len(query) < MAX_QUERY_LENGTH:
            query += char
            selected = 0


def _make_catalog_index(items: tuple[object, ...]) -> object:
    from .catalog import CatalogIndex

    return CatalogIndex(items)


def _choose_catalog_provider(
    screen: object,
    worker: _CatalogWorker,
    styles: TerminalStyle | None = None,
) -> object | None:
    return _choose_catalog_record(screen, worker, kind="provider", styles=styles)


def _choose_catalog_model(
    screen: object,
    provider: object,
    worker: _CatalogWorker,
    styles: TerminalStyle | None = None,
) -> object | None:
    # The provider object is frozen from the selected snapshot for this entire model search.
    return _choose_catalog_record(
        screen,
        worker,
        kind="model",
        items=tuple(getattr(provider, "models", ())),
        styles=styles,
    )


def _review_catalog_preset(
    screen: object,
    provider: object,
    model: object,
    styles: TerminalStyle | None = None,
) -> tuple[dict[str, object] | None, str]:
    from .catalog import preset_fields

    suggested = preset_fields(provider, model)
    suggested_name = _safe_text(suggested.get("name", ""))[:80]
    suggested_type = str(suggested.get("type", ""))
    suggested_url = _safe_text(suggested.get("base_url", ""))
    suggested_model = _safe_text(suggested.get("model", ""))

    name = _prompt(screen, "渠道名称（最多 80 字符）", default=suggested_name, limit=80, styles=styles)
    if name is None:
        return None, "已取消预设确认；配置未修改"

    known_protocol = suggested_type in AI_PROVIDER_TYPES
    notice = ""
    if not known_protocol:
        notice = (
            "目录协议不受支持；请确认兼容协议并核对 Base URL。\n"
            "AWS/Azure/Vertex 专用认证本工具不支持。"
        )
    provider_type = _select_protocol(
        screen,
        default=suggested_type if known_protocol else None,
        notice=notice,
        styles=styles,
    )
    if provider_type is None:
        return None, "已取消预设确认；配置未修改"

    base_url_required = not known_protocol or provider_type != "ollama"
    base_url_label = (
        "兼容服务 Base URL（必填）"
        if base_url_required
        else "Ollama Base URL（可留空使用本地默认地址）"
    )
    base_url = _prompt(screen, base_url_label, default=suggested_url, limit=500, styles=styles)
    if base_url is None:
        return None, "已取消预设确认；配置未修改"
    model_id = _prompt(screen, "Model ID", default=suggested_model, limit=120, styles=styles)
    if model_id is None:
        return None, "已取消预设确认；配置未修改"
    if not name.strip() or not model_id.strip():
        return None, "渠道名称和 Model ID 不能为空；配置未修改"
    if base_url_required and not base_url.strip():
        return None, "所选协议需要兼容 Base URL；配置未修改"
    return (
        {
            "name": name.strip(),
            "type": provider_type,
            "base_url": base_url.strip(),
            "model": model_id.strip(),
            "catalog_provider": suggested.get("catalog_provider", ""),
        },
        "",
    )


def _add_catalog_provider(
    screen: object,
    document: SettingsDocument,
    worker: _CatalogWorker,
    styles: TerminalStyle | None = None,
) -> str:
    provider = _choose_catalog_provider(screen, worker, styles)
    if provider is None:
        if worker.state().snapshot is None and worker.state().phase == "error":
            return "目录离线且没有可用缓存；未修改配置，可按 a 手动添加"
        return "已取消模型目录选择；配置未修改"
    model = _choose_catalog_model(screen, provider, worker, styles)
    if model is None:
        return "已取消模型选择；配置未修改"
    fields, message = _review_catalog_preset(screen, provider, model, styles)
    if fields is None:
        return message
    fields.update({"id": _new_id(document.providers), "enabled": False})
    try:
        document.put_provider(None, fields)
    except Exception:
        return "预设不符合现有渠道配置校验；配置未修改，请按 a 手动配置"
    return "已新增停用渠道；认证需通过现有 K/环境变量操作设置，按 s 显式保存"


def _ask_value(
    screen: object,
    label: str,
    *,
    current: str = "",
    limit: int = 300,
    styles: TerminalStyle | None = None,
) -> object:
    shown = safe_url(current) if label == "Base URL" else _KEY_MASK if label == "认证环境变量名" and current else _safe_text(current)
    suffix = f"（当前：{shown}；留空保持，输入 - 清除）" if shown else "（留空保持，输入 - 清除）"
    entered = _prompt(screen, label + suffix, limit=limit, styles=styles)
    if entered is None:
        return _CANCEL
    if not entered:
        return _UNCHANGED
    return "" if entered == "-" else entered


def _new_id(providers: list[dict[str, object]]) -> str:
    existing = {str(provider.get("id", "")) for provider in providers}
    number = 1
    while f"ai-{number}" in existing:
        number += 1
    return f"ai-{number}"


def _add_provider(
    screen: object,
    document: SettingsDocument,
    styles: TerminalStyle | None = None,
) -> str:
    provider_type = _select_protocol(screen, styles=styles)
    if provider_type is None:
        return "已取消新增渠道"
    name = _prompt(screen, "渠道名称", limit=80, styles=styles)
    if name is None:
        return "已取消新增渠道"
    base_url = _prompt(screen, "Base URL", limit=500, styles=styles)
    if base_url is None:
        return "已取消新增渠道"
    model = _prompt(screen, "Model 名称", limit=120, styles=styles)
    if model is None:
        return "已取消新增渠道"
    api_key_env = _prompt(screen, "认证环境变量名（可留空）", limit=80, styles=styles)
    if api_key_env is None:
        return "已取消新增渠道"
    if not name.strip() or not model.strip() or (provider_type != "ollama" and not base_url.strip()):
        return "名称和 Model 不能为空（Ollama 的 Base URL 可留空）"
    values: dict[str, object] = {
        "id": _new_id(document.providers),
        "type": provider_type,
        "name": name.strip(),
        "base_url": base_url.strip(),
        "model": model.strip(),
        "enabled": False,
    }
    if api_key_env.strip():
        values["api_key_env"] = api_key_env.strip()
    document.put_provider(None, values)
    return "已新增停用渠道；按 K 可安全写入 Key"


def _edit_provider(
    screen: object,
    document: SettingsDocument,
    index: int,
    styles: TerminalStyle | None = None,
) -> str:
    provider = document.providers[index]
    values: dict[str, object] = {}
    for key, label, limit in (
        ("name", "Name", 80),
        ("base_url", "Base URL", 500),
        ("model", "Model", 120),
        ("api_key_env", "认证环境变量名", 80),
    ):
        current = str(_provider_value(provider, key, ""))
        edited = _ask_value(screen, label, current=current, limit=limit, styles=styles)
        if edited is _CANCEL:
            return "已取消编辑"
        if edited is _UNCHANGED:
            continue
        values[key] = edited.strip() if isinstance(edited, str) else edited
        if key == "api_key_env" and edited:
            values["api_key_secret"] = ""
    if not values:
        return "没有修改渠道信息"
    document.put_provider(index, values)
    return "渠道信息已修改；使用 s 保存配置"


def _result_status(completion: _Completion) -> tuple[str, str]:
    if not completion.succeeded:
        return "操作失败；敏感错误详情已隐藏", ""
    if completion.kind == "set-key":
        return (
            "Key 已立即写入系统钥匙串；TOML 引用仍需保存。放弃配置不会撤销已轮换的 Key。",
            "",
        )
    outcome = completion.result
    if not bool(getattr(outcome, "ok", False)):
        category = str(getattr(outcome, "error_category", "unknown"))
        return _ERROR_STATUS.get(category, "测试失败"), ""
    translated = _safe_text(getattr(outcome, "text", ""))
    if not translated:
        return "Provider 未返回译文", ""
    return "测试可达，译文预览：", clip_columns(translated, _PREVIEW_LIMIT)


def _completion_status_for_selection(
    completion: _Completion,
    selected: int,
) -> tuple[str, str, int | None]:
    if completion.kind == "probe" and completion.provider_index is not None:
        if completion.provider_index != selected:
            return "示例测试已完成；当前选择不同，未显示结果", "", None
        status, preview = _result_status(completion)
        return status, preview, completion.provider_index
    status, preview = _result_status(completion)
    return status, preview, None


def _render(
    screen: object,
    document: SettingsDocument,
    selected: int,
    status: str,
    preview: str,
    busy: bool,
    scroll: int,
    focus_area: str = "channels",
    focus_action: int = 0,
    styles: TerminalStyle | None = None,
) -> int:
    rows, columns = screen.getmaxyx()
    screen.erase()
    if rows < 9 or columns < 25:
        _put(screen, 0, 0, "终端太小，请放大窗口；按 q 退出", columns - 1, _style(styles, "muted"))
        screen.refresh()
        return 0

    providers = document.providers
    selected = min(max(selected, 0), max(0, len(providers) - 1))
    enabled_count = sum(bool(_provider_value(provider, "enabled", False)) for provider in providers)
    _draw_heading(screen, columns, bool(document.dirty), enabled_count, len(providers), styles)
    _rule(screen, 1, 0, columns - 1, styles)

    # Footer, bottom-up: action hints, a quiet rule, then up to two status lines.
    action_rows = _action_rows(columns, focus_action, focus_area == "actions")
    action_top = rows - len(action_rows)
    rule_row = action_top - 1
    footer_top = max(3, rule_row - 2)
    status_text = _safe_text(status) if status else ""
    if preview:
        status_text += ("  ·  " if status_text else "") + _safe_text(preview)
    if status_text:
        marker = ("◌ " if busy else "▸ ", _style(styles, "warn" if busy else "key"))
        for offset, line in enumerate(_wrap_columns(status_text, columns - 4)[:2]):
            row = footer_top + offset
            if row < rule_row:
                _put_segments(
                    screen, row, 1,
                    [marker if offset == 0 else ("  ", 0), (line, _style(styles, "text"))],
                    columns - 2,
                )
    _rule(screen, rule_row, 0, columns - 1, styles)
    _draw_actions(screen, action_rows, action_top, focus_area == "actions", focus_action, styles)

    body_start = 2
    body_end = max(body_start, footer_top)
    body_height = body_end - body_start
    list_focused = focus_area == "channels"
    current = providers[selected] if providers else None
    if columns >= 84:
        left_width = max(28, min(38, columns // 3))
        _draw_list_heading(screen, body_start, 1, len(providers), enabled_count, left_width - 2, styles)
        for row in range(body_start, body_end):
            _put(screen, row, left_width, "│", 1, _style(styles, "border"))
        list_start = body_start + 1
        list_capacity = max(1, body_end - list_start)
        scroll = _scroll_to(selected, scroll, list_capacity)
        if not providers:
            _put(screen, list_start, 1, "  暂无渠道", left_width - 2, _style(styles, "muted"))
        for offset, index in enumerate(range(scroll, min(len(providers), scroll + list_capacity))):
            _draw_channel_row(
                screen, list_start + offset, 1, providers[index],
                index == selected, list_focused, left_width - 2, styles,
            )
        _draw_provider_details(screen, current, left_width + 2, body_start, body_end, columns, styles)
    elif body_height >= 4:
        _draw_list_heading(screen, body_start, 1, len(providers), enabled_count, columns - 2, styles)
        list_capacity = max(1, min(len(providers), max(1, (body_height - 2) // 2)))
        list_start = body_start + 1
        scroll = _scroll_to(selected, scroll, list_capacity)
        if not providers:
            _put(screen, list_start, 1, "暂无渠道；按 a 新增或 m 搜索目录", columns - 2, _style(styles, "muted"))
        for offset, index in enumerate(range(scroll, min(len(providers), scroll + list_capacity))):
            _draw_channel_row(
                screen, list_start + offset, 1, providers[index],
                index == selected, list_focused, columns - 2, styles,
            )
        detail_start = min(body_end - 1, list_start + list_capacity)
        _draw_provider_details(screen, current, 1, detail_start, body_end, columns, styles)
    elif current is not None:
        _draw_channel_row(screen, body_start, 1, current, True, list_focused, columns - 2, styles)
    else:
        _put(screen, body_start, 1, "暂无渠道；按 a 新增", columns - 2, _style(styles, "muted"))
    screen.refresh()
    return scroll


def _scroll_to(selected: int, scroll: int, capacity: int) -> int:
    if selected < scroll:
        return selected
    if selected >= scroll + capacity:
        return selected - capacity + 1
    return scroll


def _draw_heading(
    screen: object,
    columns: int,
    dirty: bool,
    enabled_count: int,
    total: int,
    styles: TerminalStyle | None,
) -> None:
    """Title left, save state and enabled count right; state always survives."""

    width = columns - 1
    state = ("◆ 未保存", _style(styles, "warn")) if dirty else ("● 已保存", _style(styles, "accent"))
    count = (f"{enabled_count}/{total} 启用", _style(styles, "subtle"))
    title_options = (
        [(_TITLE_ICON + " ", _style(styles, "key")), ("Orbit Translate 设置", _style(styles, "title"))],
        [("Translate", _style(styles, "title"))],
    )
    right_options = ([state, ("  ", 0), count], [state])
    for title in title_options:
        for right in right_options:
            title_width = sum(display_width(text) for text, _style_value in title)
            right_width = sum(display_width(text) for text, _style_value in right)
            if 1 + title_width + 2 + right_width + 1 <= width:
                _put_segments(screen, 0, 1, title, title_width)
                _put_segments(screen, 0, width - right_width - 1, right, right_width)
                return
    _put_segments(screen, 0, 0, [state], width)


def _draw_list_heading(
    screen: object,
    row: int,
    left: int,
    total: int,
    enabled_count: int,
    width: int,
    styles: TerminalStyle | None,
) -> None:
    _put_segments(
        screen, row, left,
        [(_section("渠道"), _style(styles, "title")), (f"  {enabled_count}/{total}", _style(styles, "subtle"))],
        width,
    )


def _draw_channel_row(
    screen: object,
    row: int,
    left: int,
    provider: dict[str, object],
    selected: bool,
    focused: bool,
    width: int,
    styles: TerminalStyle | None,
) -> None:
    """NyxURI list row: ``❯`` pointer, ``[✓]``/``[ ]`` state, then the name."""

    enabled = bool(_provider_value(provider, "enabled", False))
    name = _safe_text(_provider_value(provider, "name", "未命名渠道"))
    if selected:
        pointer = ("❯ ", _style(styles, "title" if focused else "subtle"))
        name_style = _style(styles, "strong")
    else:
        pointer = ("  ", 0)
        name_style = _style(styles, "text" if enabled else "muted")
    check = ("[✓] ", _style(styles, "accent")) if enabled else ("[ ] ", _style(styles, "subtle"))
    _put_segments(screen, row, left, [pointer, check, (name, name_style)], width)


def _provider_list_label(provider: dict[str, object]) -> str:
    enabled = "[✓]" if bool(_provider_value(provider, "enabled", False)) else "[ ]"
    return f"{enabled} {_safe_text(_provider_value(provider, 'name', '未命名渠道'))}"


def _action_rows(
    columns: int,
    focus_action: int,
    focused: bool,
) -> list[list[tuple[int, str, int]]]:
    available = max(1, columns - 2)
    compact = columns < 48
    rows: list[list[tuple[int, str, int]]] = [[]]
    used = 0
    for index, action in enumerate(_ACTION_KEYS):
        if compact:
            label = _ACTION_LABELS[action]
        else:
            key, text = _ACTION_HINTS[action]
            label = f"[{key}] {text}"
        width = display_width(label)
        needed = width + (2 if focused and index == focus_action else 0)
        gap = 2 if rows[-1] else 0
        if rows[-1] and used + gap + needed > available:
            rows.append([])
            used = 0
            gap = 0
        rows[-1].append((index, label, width))
        used += gap + needed
    return rows


def _draw_actions(
    screen: object,
    action_rows: list[list[tuple[int, str, int]]],
    top: int,
    focused: bool,
    focus_action: int,
    styles: TerminalStyle | None,
) -> None:
    """Footer hints: ``[key]`` in primary, label subtle, focus as ``‹…›``."""

    for offset, actions in enumerate(action_rows):
        column = 1
        row = top + offset
        for action_index, label, width in actions:
            if focused and action_index == focus_action:
                _put(screen, row, column, f"‹{label}›", width + 2, _style(styles, "focus"))
                column += width + 2 + 2
                continue
            key, bracket, text = label.partition("]")
            if bracket:
                _put_segments(
                    screen, row, column,
                    [(key + bracket, _style(styles, "key")), (text, _style(styles, "muted"))],
                    width,
                )
            else:
                _put(screen, row, column, label, width, _style(styles, "muted"))
            column += width + 2


def _draw_hints(
    screen: object,
    row: int,
    left: int,
    hints: tuple[tuple[str, str], ...],
    width: int,
    styles: TerminalStyle | None,
) -> None:
    segments: list[tuple[str, int]] = []
    for key, text in hints:
        if segments:
            segments.append(("  ", 0))
        segments.extend(((f"[{key}]", _style(styles, "key")), (f" {text}", _style(styles, "muted"))))
    _put_segments(screen, row, left, segments, width)


def _provider_detail_lines(provider: dict[str, object] | None, width: int) -> list[tuple[str, str, str]]:
    """Return ``(key, value, role)`` rows; values wrap beside a fixed key column."""

    if provider is None:
        return [("", "尚未选择渠道", "muted"), ("", "按 a 手动新增，或按 m 搜索公共模型目录", "subtle")]
    name = _safe_text(_provider_value(provider, "name", "未命名渠道"))
    provider_type = _safe_text(_provider_value(provider, "type", "未知类型"))
    enabled = bool(_provider_value(provider, "enabled", False))
    type_label = _PROTOCOL_LABELS.get(provider_type, "本地命令" if provider_type == "command" else provider_type)
    authenticated = bool(_provider_value(provider, "api_key_secret") or _provider_value(provider, "api_key_env"))
    rows = [
        ("", name, "strong"),
        ("状态", "[✓] 已启用" if enabled else "[ ] 已停用", "accent" if enabled else "subtle"),
        ("协议", type_label, "text"),
        ("认证", _KEY_MASK if authenticated else "无认证", "text" if authenticated else "muted"),
    ]
    base_url = safe_url(str(_provider_value(provider, "base_url", "")))
    if base_url:
        rows.append(("地址", base_url, "text"))
    model = _safe_text(_provider_value(provider, "model", ""))
    if model:
        rows.append(("模型", model, "text"))
    lines: list[tuple[str, str, str]] = []
    for key, value, role in rows:
        value_width = max(1, width - (_KV_WIDTH if key else 0))
        for index, part in enumerate(_wrap_columns(value, value_width)):
            lines.append((key if index == 0 else (" " if key else ""), part, role))
    return lines


def _draw_provider_details(
    screen: object,
    provider: dict[str, object] | None,
    left: int,
    top: int,
    bottom: int,
    columns: int,
    styles: TerminalStyle | None,
) -> None:
    width = max(1, columns - left - 2)
    _put(screen, top, left, _section("渠道详情"), width, _style(styles, "title"))
    for offset, (key, value, role) in enumerate(_provider_detail_lines(provider, width), start=1):
        row = top + offset
        if row >= bottom:
            break
        if key:
            _put(screen, row, left, key.strip(), _KV_WIDTH, _style(styles, "subtle"))
            _put(screen, row, left + _KV_WIDTH, value, width - _KV_WIDTH, _style(styles, role))
        else:
            _put(screen, row, left, value, width, _style(styles, role))


def _show_help(screen: object, styles: TerminalStyle | None = None) -> None:
    paragraphs = [
        "↑/↓ 或 j/k 选择渠道；Space 启用或停用。Tab/Shift-Tab 切换渠道区与操作栏，←/→ 选择操作，Enter 执行；在渠道列表按 Enter 编辑。",
        "e 编辑，a 手动新增，m 搜索 models.dev，t 用示例文本测试。测试在后台进行，不读取剪贴板，也不保存历史。",
        "启用/停用、编辑、新增、删除和模型目录选择只改当前配置；按 s 并确认后才保存。保存会创建备份。",
        "K 输入 Key 时始终只显示固定掩码。确认后会立即写入系统钥匙串；这项写入独立于 TOML 保存，放弃配置不能撤销轮换。",
        "认证环境变量名和钥匙串引用不会显示。Base URL 只显示主机与路径，不显示 userinfo、查询参数或片段。q 或 Esc 退出；未保存内容会先询问。",
    ]
    _draw_centered_dialog(screen, "Orbit Translate 帮助", paragraphs, "按任意键返回 · Esc 关闭", styles)
    while True:
        try:
            key = _get_key(screen)
        except (curses.error, OSError):
            continue
        if key == curses.KEY_RESIZE:
            _draw_centered_dialog(screen, "Orbit Translate 帮助", paragraphs, "按任意键返回 · Esc 关闭", styles)
            continue
        return


def _confirm_quit(
    screen: object,
    document: SettingsDocument,
    worker: _OperationWorker,
    key_written: bool,
    selected: int,
    styles: TerminalStyle | None = None,
) -> tuple[bool, bool, str, str, int | None]:
    completion = worker.poll()
    status, preview = ("", "")
    status_target = None
    if completion is not None:
        status, preview, status_target = _completion_status_for_selection(completion, selected)
        key_written = key_written or (completion.kind == "set-key" and completion.succeeded)

    question_parts: list[str] = []
    if document.dirty:
        question_parts.append("丢弃未保存的配置变更")
    if worker.busy:
        if worker.kind == "set-key":
            question_parts.append("当前钥匙串写入可能被中断，若已完成其配置引用也会丢弃")
        else:
            question_parts.append("当前示例测试将停止等待")
    if key_written:
        question_parts.append("已写入钥匙串的 Key 不会恢复")
    if question_parts and not _confirm(screen, "并且".join(question_parts) + "；退出？", styles=styles):
        return False, key_written, status, preview, status_target
    return True, key_written, status, preview, status_target


def _main_frame_signature(
    screen: object,
    document: SettingsDocument,
    selected: int,
    status: str,
    preview: str,
    busy: bool,
    scroll: int,
    focus_area: str,
    focus_action: int,
) -> tuple[object, ...]:
    providers = tuple(
        (
            _provider_line(provider),
            safe_url(str(_provider_value(provider, "base_url", ""))),
            _safe_text(_provider_value(provider, "model", "")),
        )
        for provider in document.providers
    )
    return (
        screen.getmaxyx(),
        providers,
        bool(document.dirty),
        selected,
        status,
        preview,
        busy,
        scroll,
        focus_area,
        focus_action,
    )


def _run_screen(screen: object, document: SettingsDocument) -> int:
    styles = load_terminal_style()
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        screen.keypad(True)
        screen.timeout(100)
    except (AttributeError, curses.error):
        pass
    try:
        set_escdelay = getattr(curses, "set_escdelay", None)
        if callable(set_escdelay):
            set_escdelay(25)
    except curses.error:
        pass
    worker = _OperationWorker(document)
    selected = 0
    scroll = 0
    status = "选择渠道；按 t 测试示例文本"
    preview = ""
    status_target: int | None = None
    key_written = False
    catalog_worker: _CatalogWorker | None = None
    focus_area = "channels"
    focus_action = 0
    rendered_frame: tuple[object, ...] | None = None

    while True:
        completion = worker.poll()
        if completion is not None:
            status, preview, status_target = _completion_status_for_selection(completion, selected)
            key_written = key_written or (completion.kind == "set-key" and completion.succeeded)

        rows, columns = screen.getmaxyx()
        providers = document.providers
        if providers:
            selected = min(max(selected, 0), len(providers) - 1)
        else:
            selected = 0
        signature = _main_frame_signature(
            screen, document, selected, status, preview, worker.busy, scroll, focus_area, focus_action
        )
        if signature != rendered_frame:
            if rows < 9 or columns < 25:
                scroll = _render(screen, document, selected, "", "", worker.busy, scroll, styles=styles)
            else:
                scroll = _render(
                    screen,
                    document,
                    selected,
                    status,
                    preview,
                    worker.busy,
                    scroll,
                    focus_area,
                    focus_action,
                    styles,
                )
            rendered_frame = _main_frame_signature(
                screen, document, selected, status, preview, worker.busy, scroll, focus_area, focus_action
            )

        try:
            key = _get_key(screen)
        except (curses.error, OSError):
            continue
        if key in (-1, curses.KEY_RESIZE):
            continue
        if key in (getattr(curses, "KEY_BTAB", -2), "\x1b[Z"):
            if focus_area == "channels":
                focus_area = "actions"
                focus_action = len(_ACTION_KEYS) - 1
            else:
                focus_area = "channels"
            continue
        if key in (9, "\t"):
            if focus_area == "channels":
                focus_area = "actions"
                focus_action = 0
            else:
                focus_area = "channels"
            continue
        if key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            if focus_area == "channels":
                focus_area = "actions"
                focus_action = len(_ACTION_KEYS) - 1 if key == curses.KEY_LEFT else 0
            else:
                delta = -1 if key == curses.KEY_LEFT else 1
                focus_action = (focus_action + delta) % len(_ACTION_KEYS)
            continue
        if key in (curses.KEY_UP, ord("k"), "k"):
            previous_selected = selected
            if providers:
                selected = max(0, selected - 1)
            if selected != previous_selected and status_target is not None:
                status = (
                    "测试仍在后台进行"
                    if worker.busy and worker.kind == "probe"
                    else "选择渠道；按 t 测试示例文本"
                )
                preview = ""
                status_target = None
            focus_area = "channels"
            continue
        if key in (curses.KEY_DOWN, ord("j"), "j"):
            previous_selected = selected
            if providers:
                selected = min(len(providers) - 1, selected + 1)
            if selected != previous_selected and status_target is not None:
                status = (
                    "测试仍在后台进行"
                    if worker.busy and worker.kind == "probe"
                    else "选择渠道；按 t 测试示例文本"
                )
                preview = ""
                status_target = None
            focus_area = "channels"
            continue
        if key in (ord("q"), "q", 27, "\x1b"):
            allowed, key_written, quit_status, quit_preview, quit_target = _confirm_quit(
                screen, document, worker, key_written, selected, styles
            )
            rendered_frame = None
            if not allowed:
                if quit_status:
                    status, preview = quit_status, quit_preview
                    status_target = quit_target
                continue
            worker.stop()
            if catalog_worker is not None:
                catalog_worker.stop()
            return 0

        action = None
        if key in (10, 13, "\n", "\r", getattr(curses, "KEY_ENTER", -1)):
            action = "edit" if focus_area == "channels" else _ACTION_KEYS[focus_action]
        else:
            char = key if isinstance(key, str) else chr(key) if isinstance(key, int) and 0 <= key <= 255 else ""
            action = {
                " ": "toggle",
                "e": "edit",
                "a": "add",
                "m": "catalog",
                "K": "key",
                "t": "test",
                "d": "delete",
                "s": "save",
                "?": "help",
            }.get(char)
        if action is None:
            continue
        # Every action may open a dialog or replace the screen with a picker.
        rendered_frame = None
        if action not in {"help", "quit"}:
            status_target = None
        if action == "quit":
            allowed, key_written, quit_status, quit_preview, quit_target = _confirm_quit(
                screen, document, worker, key_written, selected, styles
            )
            if allowed:
                worker.stop()
                if catalog_worker is not None:
                    catalog_worker.stop()
                return 0
            if quit_status:
                status, preview = quit_status, quit_preview
                status_target = quit_target
            continue
        if worker.busy and action in {"toggle", "add", "catalog", "edit", "key", "delete", "test", "save"}:
            status, preview = "当前操作完成前，渠道修改和保存暂不可用", ""
            continue
        if action == "toggle" and providers:
            try:
                document.toggle(selected)
                status, preview = "渠道状态已修改；使用 s 保存配置", ""
            except Exception:
                status, preview = "无法修改渠道状态", ""
            continue
        if action == "toggle":
            status, preview = "暂无渠道可切换；按 a 新增或按 m 搜索目录", ""
            continue
        if action == "edit" and providers:
            try:
                status = _edit_provider(screen, document, selected, styles)
                preview = ""
            except Exception:
                status, preview = "无法修改渠道信息", ""
            continue
        if action == "edit":
            status, preview = "暂无渠道可编辑；按 a 新增或按 m 搜索目录", ""
            continue
        if action == "add":
            before_count = len(document.providers)
            try:
                status = _add_provider(screen, document, styles)
                preview = ""
                if len(document.providers) > before_count:
                    selected = len(document.providers) - 1
            except Exception:
                status, preview = "无法新增渠道，请检查配置字段", ""
            continue
        if action == "catalog":
            if catalog_worker is None:
                catalog_worker = _CatalogWorker()
            provider_count = len(document.providers)
            try:
                status = _add_catalog_provider(screen, document, catalog_worker, styles)
                preview = ""
                if len(document.providers) > provider_count:
                    selected = len(document.providers) - 1
            except Exception:
                status, preview = "模型目录选择失败；现有配置未改变", ""
            continue
        if action == "key" and providers:
            secret = _prompt_secret(screen, "输入 API Key（固定掩码，不回显）", styles=styles)
            if secret is None:
                status, preview = "已取消 Key 写入", ""
            elif not secret:
                status, preview = "Key 不能为空", ""
            elif worker.submit("set-key", selected, secret):
                status, preview = "正在写入钥匙串；界面仍可继续操作", ""
                secret = ""
            else:
                status, preview = "已有钥匙串或网络操作正在执行", ""
            continue
        if action == "key":
            status, preview = "暂无渠道可设置 Key", ""
            continue
        if action == "delete" and providers:
            if _confirm(screen, f"删除渠道“{_safe_text(providers[selected].get('name', ''))}”？", styles=styles):
                try:
                    document.delete_provider(selected)
                    selected = max(0, selected - 1)
                    status, preview = "渠道已删除；使用 s 保存配置", ""
                except Exception:
                    status, preview = "无法删除渠道", ""
            continue
        if action == "delete":
            status, preview = "暂无渠道可删除", ""
            continue
        if action == "test" and providers:
            sample = _prompt(screen, "示例文本", default="Hello world", limit=2000, styles=styles)
            if sample is None:
                status, preview = "已取消测试", ""
                continue
            configured_source = str(document.config.source)
            source = _prompt(
                screen,
                "来源语言",
                default="en" if configured_source == "auto" else configured_source,
                limit=32,
                styles=styles,
            )
            if source is None:
                status, preview = "已取消测试", ""
                continue
            target = _prompt(screen, "目标语言", default=str(document.config.target), limit=32, styles=styles)
            if target is None:
                status, preview = "已取消测试", ""
                continue
            if not sample.strip() or not source.strip() or not target.strip():
                status, preview = "示例文本和语言不能为空", ""
            elif worker.submit("probe", selected, sample, source, target):
                status, preview = "正在测试当前渠道（不读取剪贴板、不保存历史）", ""
                status_target = selected
            else:
                status, preview = "已有钥匙串或网络操作正在执行", ""
            continue
        if action == "test":
            status, preview = "暂无渠道可测试", ""
            continue
        if action == "save":
            if not document.dirty:
                status, preview = "配置没有未保存的修改", ""
                continue
            if not _confirm(screen, "保存当前配置？", styles=styles):
                status = "已取消保存"
                continue
            try:
                backup = document.save()
                status = "配置已保存并创建备份" if backup is not None else "配置已保存（此前不存在文件）"
            except SettingsError as exc:
                status = _safe_text(exc)
            except Exception:
                status = "保存失败；敏感错误详情已隐藏"
            preview = ""
            continue
        if action == "help":
            _show_help(screen, styles)
            continue


def run_settings_tui(config_path: str | None = None) -> int:
    """Run the settings screen; loading failures never emit a traceback."""

    try:
        document = SettingsDocument(config_path)
    except Exception:
        import sys

        print("无法读取设置配置；请检查配置文件格式和权限。", file=sys.stderr)
        return 1
    try:
        return curses.wrapper(lambda screen: _run_screen(screen, document))
    except (curses.error, OSError):
        import sys

        print("无法启动终端设置界面。", file=sys.stderr)
        return 1


__all__ = [
    "clip_columns",
    "display_width",
    "run_settings_tui",
    "safe_url",
]
