"""Cross-boundary regressions for public catalog presets and picker behavior."""

from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import curses
import gzip
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from orbit_translate import catalog, tui
from tests.test_translate_tui import FakeScreen


def _provider(provider_id: str, *, model: str = "fixture") -> catalog.CatalogProvider:
    return catalog.CatalogProvider(provider_id, provider_id, (), (
        catalog.CatalogModel(model, model, "", "openai_compatible", "https://example.test/v1"),
    ))


class PickerWorker:
    def __init__(self, providers: tuple[catalog.CatalogProvider, ...]):
        self.snapshot = catalog.CatalogSnapshot(providers, time.time())
        self.refreshed = 0
        self.replacement = None

    def open(self) -> None:
        pass

    def state(self) -> tui._CatalogWorkerState:
        return tui._CatalogWorkerState(self.snapshot, "ready")

    def refresh(self) -> bool:
        self.refreshed += 1
        if self.replacement is not None:
            self.snapshot = self.replacement
        return True


class PickerIntegrationTests(unittest.TestCase):
    def test_printable_r_searches_instead_of_refreshing(self) -> None:
        providers = (_provider("alpha"), _provider("router"))
        worker = PickerWorker(providers)
        selected = tui._choose_catalog_provider(FakeScreen(["r", "\n"]), worker)
        self.assertIs(selected, providers[1])
        self.assertEqual(worker.refreshed, 0)

    def test_control_r_refreshes_without_losing_query(self) -> None:
        providers = (_provider("alpha"), _provider("router"))
        worker = PickerWorker(providers)
        selected = tui._choose_catalog_provider(FakeScreen(["r", "\x12", "\n"]), worker)
        self.assertIs(selected, providers[1])
        self.assertEqual(worker.refreshed, 1)

    def test_idle_resize_and_navigation_do_not_repeat_search(self) -> None:
        providers = (_provider("alpha"), _provider("router"))
        worker = PickerWorker(providers)
        index = SimpleNamespace(search=Mock(return_value=providers))
        with patch("orbit_translate.tui._make_catalog_index", return_value=index):
            selected = tui._choose_catalog_provider(FakeScreen([curses.KEY_RESIZE, curses.KEY_DOWN, "\n"]), worker)
        self.assertIs(selected, providers[1])
        index.search.assert_called_once_with("", limit=100)

    def test_refreshed_provider_list_retains_selected_identity(self) -> None:
        old = (_provider("alpha"), _provider("zeta", model="old-model"))
        new = (_provider("beta"), _provider("zeta", model="new-model"))
        worker = PickerWorker(old)
        worker.replacement = catalog.CatalogSnapshot(new, time.time())
        selected = tui._choose_catalog_provider(FakeScreen([curses.KEY_DOWN, "\x12", "\n"]), worker)
        self.assertIs(selected, new[1])

    def test_idle_ticks_do_not_search_or_redraw(self) -> None:
        providers = (_provider("alpha"),)
        worker = PickerWorker(providers)
        index = SimpleNamespace(search=Mock(return_value=providers))
        with patch("orbit_translate.tui._make_catalog_index", return_value=index), \
                patch("orbit_translate.tui._draw_catalog_picker") as draw, \
                patch("orbit_translate.tui._get_key", side_effect=[curses.error(), curses.error(), "\x1b"]):
            self.assertIsNone(tui._choose_catalog_provider(FakeScreen(), worker))
        index.search.assert_called_once_with("", limit=100)
        draw.assert_called_once()


class CatalogBoundaryIntegrationTests(unittest.TestCase):
    def test_entry_and_settings_import_do_not_load_optional_catalog(self) -> None:
        entry = ENTRY
        code = (
            "import runpy,sys; "
            f"runpy.run_path({str(entry)!r}, run_name='fixture_import'); "
            "import orbit_translate.tui; "
            "assert 'orbit_translate.catalog' not in sys.modules"
        )
        result = subprocess.run(
            ["/usr/bin/python3", "-c", code],
            cwd=entry.parent, capture_output=True, timeout=4,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0)

    def test_openai_completions_shape_keeps_first_party_api_default(self) -> None:
        raw = {"openai": {"name": "OpenAI", "npm": "@ai-sdk/openai", "models": {
            "fixture": {"name": "Fixture", "modalities": {"input": ["text"], "output": ["text"]},
                        "provider": {"shape": "completions"}},
        }}}
        provider = catalog._project_catalog(raw)[0]
        self.assertEqual(provider.models[0].protocol, "openai_compatible")
        self.assertEqual(provider.models[0].base_url, "https://api.openai.com/v1")

    def test_text_capable_multimodal_model_remains_selectable(self) -> None:
        raw = {"google": {"name": "Google", "npm": "@ai-sdk/google", "models": {
            "gemini-fixture": {"name": "Gemini fixture", "modalities": {
                "input": ["text", "image", "audio", "video"], "output": ["text"],
            }},
            "audio-only": {"name": "Audio only", "modalities": {"input": ["audio"], "output": ["audio"]}},
        }}}
        models = catalog._project_catalog(raw)[0].models
        self.assertEqual(tuple(model.id for model in models), ("gemini-fixture",))

    def test_public_cache_retains_permission_notice(self) -> None:
        with tempfile.TemporaryDirectory(prefix="orbit-license-test-") as directory:
            path = Path(directory) / "catalog.gz"
            store = catalog.CatalogStore(path)
            store._write_cache(catalog.CatalogSnapshot((_provider("fixture"),), time.time()))
            payload = json.loads(gzip.decompress(path.read_bytes()))
        self.assertIn("Permission is hereby granted", payload.get("license_notice", ""))
        self.assertIn("Copyright (c) 2025 models.dev", payload.get("license_notice", ""))

    def test_cache_read_is_bounded_even_if_size_changes_after_stat(self) -> None:
        testcase = self

        class BoundedReader(BytesIO):
            def read(self, size: int = -1) -> bytes:
                testcase.assertEqual(size, catalog.MAX_WIRE_BYTES + 1)
                return super().read(size)
        with patch.object(Path, "stat", return_value=SimpleNamespace(st_size=1)), \
                patch.object(Path, "open", return_value=BoundedReader(b"invalid")):
            self.assertIsNone(catalog.CatalogStore(Path("unused-fixture.gz")).load_cached())
