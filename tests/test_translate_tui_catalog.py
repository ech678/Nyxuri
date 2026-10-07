from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import curses
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orbit_translate.catalog import (
    CACHE_TTL_SECONDS,
    CatalogModel,
    CatalogProvider,
    CatalogSnapshot,
)
from orbit_translate.tui import (
    _CatalogWorker,
    _CatalogWorkerState,
    _add_catalog_provider,
    _catalog_status,
    _choose_catalog_model,
    _choose_catalog_provider,
    _draw_catalog_picker,
    _run_screen,
    display_width,
)


class FakeScreen:
    def __init__(self, keys: list[object] | None = None, *, rows: int = 18, columns: int = 72):
        self.keys = list(keys or [])
        self.rows = rows
        self.columns = columns
        self.history: list[str] = []
        self.writes: list[tuple[int, int, str]] = []

    def getmaxyx(self) -> tuple[int, int]:
        return self.rows, self.columns

    def keypad(self, _enabled: bool) -> None:
        pass

    def timeout(self, _milliseconds: int) -> None:
        pass

    def erase(self) -> None:
        pass

    def addstr(self, row: int, column: int, value: str) -> None:
        self.history.append(value)
        self.writes.append((row, column, value))

    def move(self, _row: int, _column: int) -> None:
        pass

    def clrtoeol(self) -> None:
        pass

    def refresh(self) -> None:
        pass

    def get_wch(self) -> object:
        if not self.keys:
            raise curses.error("no fixture input")
        key = self.keys.pop(0)
        if key == curses.KEY_RESIZE:
            self.rows, self.columns = 9, 28
        return key


class FakeDocument:
    def __init__(self, providers: list[dict[str, object]] | None = None):
        self.providers = providers if providers is not None else []
        self.dirty = False
        self.saved = 0
        self.key_calls = 0
        self.probe_calls = 0
        self.config = SimpleNamespace(source="en", target="zh-CN", request_timeout_ms=500)

    def put_provider(self, index: int | None, values: dict[str, object]) -> None:
        if index is None:
            self.providers.append(dict(values))
        else:
            self.providers[index].update(values)
        self.dirty = True

    def save(self) -> None:
        self.saved += 1
        self.dirty = False


class StaticCatalogWorker:
    def __init__(self, snapshot: CatalogSnapshot):
        self.snapshot = snapshot
        self.phase = "ready"
        self.open_calls = 0
        self.refresh_calls = 0

    def open(self) -> None:
        self.open_calls += 1

    def state(self) -> _CatalogWorkerState:
        return _CatalogWorkerState(self.snapshot, self.phase)

    def refresh(self) -> bool:
        self.refresh_calls += 1
        return True

    def stop(self) -> None:
        pass


class FakeStore:
    def __init__(
        self,
        cached: CatalogSnapshot | None,
        result: CatalogSnapshot | None = None,
        *,
        failure: Exception | None = None,
        release: threading.Event | None = None,
    ):
        self.cached = cached
        self.result = result
        self.failure = failure
        self.release = release
        self.refresh_started = threading.Event()
        self.refresh_calls = 0
        self._lock = threading.Lock()

    def load_cached(self) -> CatalogSnapshot | None:
        return self.cached

    def refresh(self) -> CatalogSnapshot:
        with self._lock:
            self.refresh_calls += 1
        self.refresh_started.set()
        if self.release is not None:
            self.release.wait(timeout=2)
        if self.failure is not None:
            raise self.failure
        assert self.result is not None
        return self.result


def wait_for_state(worker: _CatalogWorker, phase: str, timeout: float = 1) -> _CatalogWorkerState:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = worker.state()
        if state.phase == phase:
            return state
        time.sleep(0.005)
    raise AssertionError(f"catalog worker did not reach {phase}: {worker.state()}")


def sample_snapshot(*, fetched_at: float | None = None, provider: CatalogProvider | None = None) -> CatalogSnapshot:
    model = CatalogModel("fixture-model", "Fixture Model", "fixture", "openai_compatible", "https://api.example/v1")
    candidate = provider or CatalogProvider("fixture", "Fixture Provider", (), (model,))
    return CatalogSnapshot((candidate,), fetched_at if fetched_at is not None else time.time())


class CatalogWorkerTests(unittest.TestCase):
    def test_fresh_cache_is_loaded_without_network_until_explicit_refresh(self) -> None:
        cached = sample_snapshot()
        refreshed = sample_snapshot(provider=CatalogProvider("new", "New Provider", (), ()))
        store = FakeStore(cached, refreshed)
        worker = _CatalogWorker(lambda: store)
        try:
            worker.open()
            state = wait_for_state(worker, "ready")
            self.assertIs(state.snapshot, cached)
            self.assertEqual(store.refresh_calls, 0)

            screen = FakeScreen(["\x12", "\x1b"])
            self.assertIsNone(_choose_catalog_provider(screen, worker))
            deadline = time.monotonic() + 1
            while store.refresh_calls == 0 and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertEqual(store.refresh_calls, 1)
            self.assertIn("目录已就绪", "".join(screen.history))
        finally:
            worker.stop()

    def test_stale_cache_is_selectable_while_slow_refresh_runs(self) -> None:
        cached = sample_snapshot(fetched_at=time.time() - CACHE_TTL_SECONDS - 1)
        release = threading.Event()
        store = FakeStore(cached, sample_snapshot(), release=release)
        worker = _CatalogWorker(lambda: store)
        try:
            worker.open()
            self.assertTrue(store.refresh_started.wait(timeout=1))
            state = worker.state()
            self.assertIs(state.snapshot, cached)
            self.assertEqual(state.phase, "refreshing")

            screen = FakeScreen(["\n"])
            began = time.monotonic()
            chosen = _choose_catalog_provider(screen, worker)
            self.assertLess(time.monotonic() - began, 0.2)
            self.assertIs(chosen, cached.providers[0])
            self.assertIn("过期缓存", "".join(screen.history))
        finally:
            release.set()
            worker.stop()

    def test_failed_refresh_keeps_cached_snapshot_and_hides_exception(self) -> None:
        cached = sample_snapshot(fetched_at=time.time() - CACHE_TTL_SECONDS - 1)
        secret_detail = "https://user:private-token@example.test/private"
        store = FakeStore(cached, failure=RuntimeError(secret_detail))
        worker = _CatalogWorker(lambda: store)
        try:
            worker.open()
            state = wait_for_state(worker, "error")
            self.assertIs(state.snapshot, cached)
            status = _catalog_status(state)
            self.assertIn("离线可用", status)
            self.assertNotIn("private-token", status)
            self.assertNotIn("example.test", status)
        finally:
            worker.stop()

    def test_cancel_and_reopen_reuse_one_inflight_fetch(self) -> None:
        release = threading.Event()
        store = FakeStore(None, sample_snapshot(), release=release)
        worker = _CatalogWorker(lambda: store)
        try:
            worker.open()
            self.assertTrue(store.refresh_started.wait(timeout=1))
            for _ in range(2):
                screen = FakeScreen(["\x1b"])
                began = time.monotonic()
                self.assertIsNone(_choose_catalog_provider(screen, worker))
                self.assertLess(time.monotonic() - began, 0.2)
            self.assertEqual(store.refresh_calls, 1)
        finally:
            release.set()
            worker.stop()


class CatalogPickerTests(unittest.TestCase):
    def test_catalog_worker_is_not_created_without_m(self) -> None:
        document = FakeDocument()
        screen = FakeScreen(["q"])
        with patch("orbit_translate.tui._CatalogWorker") as make_worker:
            self.assertEqual(_run_screen(screen, document), 0)
        make_worker.assert_not_called()

    def test_cancelled_picker_preserves_settings_selection_and_config(self) -> None:
        document = FakeDocument(
            [
                {"id": "first", "name": "First", "type": "mymemory", "enabled": False},
                {"id": "second", "name": "Second", "type": "mymemory", "enabled": False},
            ],
        )
        worker = StaticCatalogWorker(sample_snapshot())
        screen = FakeScreen([curses.KEY_DOWN, "m", "\x1b", "q"])
        with patch("orbit_translate.tui._CatalogWorker", return_value=worker):
            self.assertEqual(_run_screen(screen, document), 0)
        self.assertFalse(document.dirty)
        row_four = "".join(value for row, _col, value in screen.writes if row == 4)
        self.assertIn("❯ [ ] Second", row_four)

    def test_printable_jk_filter_and_resize_preserve_query(self) -> None:
        first = CatalogProvider("alpha", "Alpha", (), ())
        second = CatalogProvider("key-provider", "Key Provider", (), ())
        worker = StaticCatalogWorker(CatalogSnapshot((first, second), time.time()))
        screen = FakeScreen(["k", "e", curses.KEY_RESIZE, "\n"])
        self.assertIs(_choose_catalog_provider(screen, worker), second)
        self.assertIn("搜索：ke", "".join(screen.history))

        screen = FakeScreen(["j", "k", curses.KEY_RESIZE, "\x1b"])
        self.assertIsNone(_choose_catalog_provider(screen, worker))
        self.assertIn("搜索：jk", "".join(screen.history))

        screen = FakeScreen(["x", 21, "k", "\n"])
        self.assertIs(_choose_catalog_provider(screen, worker), second)
        self.assertIn("搜索：x", "".join(screen.history))

    def test_arrow_and_control_navigation_select_exact_model(self) -> None:
        models = (
            CatalogModel("first", "First", "family", "openai_compatible", "https://api.example/v1"),
            CatalogModel("second", "Second", "family", "openai_compatible", "https://api.example/v1"),
        )
        provider = CatalogProvider("fixture", "Fixture", (), models)
        worker = StaticCatalogWorker(CatalogSnapshot((provider,), time.time()))
        screen = FakeScreen([curses.KEY_DOWN, "\x10", "\n"])
        self.assertIs(_choose_catalog_model(screen, provider, worker), models[0])

    def test_selected_provider_remains_frozen_when_worker_snapshot_changes(self) -> None:
        old_model = CatalogModel("old-model", "Old", "", "openai_compatible", "https://old.example/v1")
        old_provider = CatalogProvider("fixture", "Old Provider", (), (old_model,))
        new_model = CatalogModel("new-model", "New", "", "openai_compatible", "https://new.example/v1")
        new_provider = CatalogProvider("fixture", "New Provider", (), (new_model,))
        worker = StaticCatalogWorker(CatalogSnapshot((old_provider,), time.time()))
        selected = _choose_catalog_provider(FakeScreen(["\n"]), worker)
        self.assertIs(selected, old_provider)

        worker.snapshot = CatalogSnapshot((new_provider,), time.time())
        model = _choose_catalog_model(FakeScreen(["\n"]), selected, worker)
        self.assertIs(model, old_model)

    def test_remote_unicode_is_sanitized_and_clipped_to_terminal_columns(self) -> None:
        provider = CatalogProvider("id\x1b[31m", "服务你好" + "界" * 40, (), ())
        snapshot = CatalogSnapshot((provider,), time.time())
        screen = FakeScreen(rows=12, columns=28)
        _draw_catalog_picker(
            screen,
            kind="provider",
            query="中文",
            items=(provider,),
            results=(provider,),
            selected=0,
            state=_CatalogWorkerState(snapshot, "ready"),
        )
        self.assertNotIn("\x1b", "".join(screen.history))
        for _row, _column, value in screen.writes:
            self.assertLessEqual(display_width(value), screen.columns - 1)

    def test_unknown_protocol_requires_explicit_compatible_gateway_and_stays_disabled(self) -> None:
        model = CatalogModel("gateway-model", "Gateway Model", "family", "", "")
        provider = CatalogProvider("custom-sdk", "Custom SDK", ("PRIVATE_KEY_NAME",), (model,))
        worker = StaticCatalogWorker(CatalogSnapshot((provider,), time.time()))
        document = FakeDocument()
        screen = FakeScreen(
            [
                "\n",  # provider
                "\n",  # model
                "\n",  # generated name
                "1",  # explicit supported protocol selection
                *"https://gateway.example/v1",
                "\n",
                "\n",  # model ID
            ],
        )
        message = _add_catalog_provider(screen, document, worker)
        self.assertIn("停用", message)
        self.assertIn("不受支持", "".join(screen.history))
        self.assertIn("AWS/Azure/Vertex", "".join(screen.history))
        added = document.providers[0]
        self.assertEqual(added["type"], "openai_compatible")
        self.assertEqual(added["base_url"], "https://gateway.example/v1")
        self.assertEqual(added["model"], "gateway-model")
        self.assertEqual(added["catalog_provider"], "custom-sdk")
        self.assertFalse(added["enabled"])
        self.assertNotIn("api_key_env", added)
        self.assertNotIn("api_key_secret", added)
        self.assertEqual(document.key_calls, 0)
        self.assertEqual(document.probe_calls, 0)
        self.assertEqual(document.saved, 0)

        missing_url_document = FakeDocument()
        missing_url_screen = FakeScreen(["\n", "\n", "\n", "1", "\n", "\n"])
        message = _add_catalog_provider(missing_url_screen, missing_url_document, worker)
        self.assertIn("需要兼容 Base URL", message)
        self.assertEqual(missing_url_document.providers, [])

        ollama_document = FakeDocument()
        ollama_screen = FakeScreen(["\n", "\n", "\n", "5", "\n", "\n"])
        message = _add_catalog_provider(ollama_screen, ollama_document, worker)
        self.assertIn("需要兼容 Base URL", message)
        self.assertEqual(ollama_document.providers, [])

    def test_generated_name_is_bounded_and_known_protocol_is_reviewable(self) -> None:
        model = CatalogModel("fixture-model", "Fixture Model", "", "openai_responses", "https://api.example/v1")
        provider = CatalogProvider("fixture", "P" * 120, (), (model,))
        worker = StaticCatalogWorker(CatalogSnapshot((provider,), time.time()))
        document = FakeDocument()
        screen = FakeScreen(["\n", "\n", "\n", "\n", "\n", "\n"])
        _add_catalog_provider(screen, document, worker)
        self.assertEqual(len(document.providers[0]["name"]), 80)
        self.assertEqual(document.providers[0]["type"], "openai_responses")

    def test_m_creates_only_a_disabled_draft_and_manual_a_path_still_works(self) -> None:
        model = CatalogModel("fixture-model", "Fixture Model", "", "openai_compatible", "https://api.example/v1")
        provider = CatalogProvider("fixture", "Fixture Provider", (), (model,))
        worker = StaticCatalogWorker(CatalogSnapshot((provider,), time.time()))
        document = FakeDocument()
        screen = FakeScreen(["m", "\n", "\n", "\n", "\n", "\n", "\n", "q", "y", "\n"])
        with patch("orbit_translate.tui._CatalogWorker", return_value=worker):
            self.assertEqual(_run_screen(screen, document), 0)
        self.assertEqual(worker.open_calls, 1)
        self.assertFalse(document.providers[0]["enabled"])
        self.assertEqual(document.saved, 0)
        self.assertEqual(document.key_calls, 0)
        self.assertEqual(document.probe_calls, 0)
        self.assertIn("丢弃未保存的配置变更", "".join(screen.history))

        manual = FakeDocument()
        screen = FakeScreen(
            [
                "a", "1", *"Manual AI", "\n", *"https://manual.example/v1", "\n",
                *"manual-model", "\n", "\n", "q", "y", "\n",
            ],
        )
        with patch("orbit_translate.tui._CatalogWorker") as make_worker:
            self.assertEqual(_run_screen(screen, manual), 0)
        make_worker.assert_not_called()
        self.assertEqual(manual.providers[0]["name"], "Manual AI")
        self.assertEqual(manual.providers[0]["type"], "openai_compatible")
        self.assertEqual(manual.providers[0]["model"], "manual-model")
        self.assertFalse(manual.providers[0]["enabled"])


if __name__ == "__main__":
    unittest.main()
