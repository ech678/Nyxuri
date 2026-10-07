from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import gzip
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from urllib.error import URLError
from unittest.mock import patch

from orbit_translate.catalog import (
    CACHE_TTL_SECONDS,
    CATALOG_URL,
    MAX_RESULTS,
    CatalogError,
    CatalogIndex,
    CatalogModel,
    CatalogProvider,
    CatalogSnapshot,
    CatalogStore,
    preset_fields,
)


def _model(
    model_id: str,
    *,
    name: str | None = None,
    input_modalities: list[str] | None = None,
    output_modalities: list[str] | None = None,
    **values: object,
) -> dict[str, object]:
    return {
        "id": "different-canonical-id-is-ignored",
        "name": name or model_id,
        "family": "fixture-family",
        "description": "catalog-only description",
        "cost": {"input": 1},
        "headers": {"Authorization": "catalog-only-header"},
        "body": {"catalog-only-body": True},
        "modalities": {
            "input": input_modalities or ["text"],
            "output": output_modalities or ["text"],
        },
        **values,
    }


def _payload() -> dict[str, object]:
    return {
        "openai": {
            "name": "OpenAI",
            "npm": "@ai-sdk/openai",
            "env": ["OPENAI_API_KEY", "bad-name", "OPENAI_API_KEY"],
            "models": {
                "gpt-4o": _model("gpt-4o", name="GPT-4o", input_modalities=["text", "image"]),
                "gpt-4o-mini": _model(
                    "gpt-4o-mini",
                    name="GPT-4o mini",
                    provider={"shape": "completions", "api": "https://gateway.example/root/"},
                ),
                "gpt-4o-completions-default": _model(
                    "gpt-4o-completions-default",
                    provider={"shape": "completions"},
                ),
                "text-embedding-3-large": _model("text-embedding-3-large", output_modalities=["embedding"]),
                "special-embedding": _model("special-embedding", type="embedding"),
                "old-model": _model("old-model", status="deprecated"),
                "audio-model": _model("audio-model", input_modalities=["audio"]),
                "image-only": _model("image-only", input_modalities=["image"]),
                "audio-output": _model("audio-output", output_modalities=["audio"]),
            },
        },
        "anthropic": {
            "name": "Anthropic",
            "npm": "@ai-sdk/anthropic",
            "models": {"claude-fixture": _model("claude-fixture")},
        },
        "google": {
            "name": "Google",
            "npm": "@ai-sdk/google",
            "models": {"gemini-fixture": _model("gemini-fixture")},
        },
        "router": {
            "name": "Router",
            "npm": "@openrouter/ai-sdk-provider",
            "api": "https://openrouter.example/api/v1",
            "models": {"router/model:latest": _model("router/model:latest")},
        },
        "unknown": {
            "name": "Unknown SDK",
            "npm": "@vendor/unsupported-sdk",
            "api": "https://vendor.example/v1",
            "models": {"manual/model": _model("manual/model")},
        },
        "unsafe": {
            "name": "Unsafe URL",
            "npm": "@ai-sdk/openai-compatible",
            "api": "https://user:secret@unsafe.example/v1?token=hidden#part",
            "models": {"unsafe-model": _model("unsafe-model")},
        },
        "custom": {
            "name": "Custom Gateway",
            "npm": "@ai-sdk/openai-compatible",
            "api": "https://api.deepseek.example/root",
            "models": {
                "custom-default": _model("custom-default"),
                "custom-model-override": _model(
                    "custom-model-override",
                    provider={"npm": "@ai-sdk/anthropic", "api": "https://anthropic.example/messages"},
                ),
                "custom-unsafe-override": _model(
                    "custom-unsafe-override",
                    provider={"npm": "@ai-sdk/openai", "api": "https://a.example/?key=hidden"},
                ),
            },
        },
    }


class FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str] | None = None, url: str = CATALOG_URL):
        self.body = body
        self.headers = headers or {"Content-Encoding": "gzip"}
        self.url = url
        self.read_size: int | None = None

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return self.url

    def read(self, size: int) -> bytes:
        self.read_size = size
        return self.body[:size]


def _response(payload: object, headers: dict[str, str] | None = None) -> FakeResponse:
    return FakeResponse(gzip.compress(json.dumps(payload).encode("utf-8")), headers)


class CatalogStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.cache = Path(self.temporary.name) / "cache" / "models.json.gz"
        self.store = CatalogStore(self.cache)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_fetch_uses_fixed_url_gzip_header_and_bounded_timeout(self) -> None:
        response = _response(_payload())
        with patch("orbit_translate.catalog.urllib.request.urlopen", return_value=response) as urlopen:
            snapshot = self.store.refresh()

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, CATALOG_URL)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Accept-encoding"), "gzip")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 15)
        self.assertEqual(response.read_size, 8 * 1024 * 1024 + 1)
        self.assertEqual(len(snapshot.providers), 7)

    def test_compressed_body_is_bounded_before_and_after_inflation(self) -> None:
        response = FakeResponse(b"123456789", {"Content-Encoding": "gzip"})
        with patch("orbit_translate.catalog.MAX_WIRE_BYTES", 8), patch(
            "orbit_translate.catalog.urllib.request.urlopen", return_value=response
        ), self.assertRaises(CatalogError) as raised:
            self.store.refresh()
        self.assertIn("安全上限", str(raised.exception))

        response = FakeResponse(gzip.compress(b"x" * 101), {"Content-Encoding": "gzip"})
        with patch("orbit_translate.catalog.MAX_DECODED_BYTES", 100), patch(
            "orbit_translate.catalog.urllib.request.urlopen", return_value=response
        ), self.assertRaises(CatalogError) as raised:
            self.store.refresh()
        self.assertIn("安全上限", str(raised.exception))

    def test_content_length_and_redirect_are_rejected_without_remote_details(self) -> None:
        too_large = FakeResponse(
            gzip.compress(json.dumps(_payload()).encode()),
            {"Content-Length": str(1024), "Content-Encoding": "gzip"},
        )
        with patch("orbit_translate.catalog.MAX_WIRE_BYTES", 8), patch(
            "orbit_translate.catalog.urllib.request.urlopen", return_value=too_large
        ), self.assertRaises(CatalogError):
            self.store.refresh()
        self.assertIsNone(too_large.read_size)

        redirected = FakeResponse(gzip.compress(b"{}"), url="https://example.invalid/redirect")
        with patch("orbit_translate.catalog.urllib.request.urlopen", return_value=redirected), self.assertRaises(
            CatalogError
        ) as raised:
            self.store.refresh()
        self.assertNotIn("example.invalid", str(raised.exception))

    def test_malformed_response_and_network_diagnostics_are_local(self) -> None:
        malformed = FakeResponse(gzip.compress(b"not-json"))
        with patch("orbit_translate.catalog.urllib.request.urlopen", return_value=malformed), self.assertRaises(
            CatalogError
        ) as raised:
            self.store.refresh()
        self.assertNotIn("not-json", str(raised.exception))

        malformed_schema = FakeResponse(gzip.compress(b'{"provider":{"name":"Bad","models":"invalid"}}'))
        with patch(
            "orbit_translate.catalog.urllib.request.urlopen", return_value=malformed_schema
        ), self.assertRaises(CatalogError) as raised:
            self.store.refresh()
        self.assertNotIn("invalid", str(raised.exception))

        with patch(
            "orbit_translate.catalog.urllib.request.urlopen",
            side_effect=URLError("fixture-private-remote-diagnostic"),
        ), self.assertRaises(CatalogError) as raised:
            self.store.refresh()
        self.assertNotIn("fixture-private-remote-diagnostic", str(raised.exception))

    def test_projection_keeps_source_identity_text_models_and_public_fields_only(self) -> None:
        with patch("orbit_translate.catalog.urllib.request.urlopen", return_value=_response(_payload())):
            snapshot = self.store.refresh()
        providers = {provider.id: provider for provider in snapshot.providers}
        self.assertEqual(providers["openai"].env_names, ("OPENAI_API_KEY",))
        models = {model.id: model for model in providers["openai"].models}
        self.assertEqual(
            set(models),
            {"gpt-4o", "gpt-4o-mini", "gpt-4o-completions-default"},
        )
        self.assertEqual(models["gpt-4o"].id, "gpt-4o")
        self.assertEqual(models["gpt-4o"].name, "GPT-4o")
        self.assertEqual(models["gpt-4o"].protocol, "openai_responses")
        self.assertEqual(models["gpt-4o"].base_url, "https://api.openai.com/v1")
        self.assertEqual(models["gpt-4o-mini"].protocol, "openai_compatible")
        self.assertEqual(models["gpt-4o-mini"].base_url, "https://gateway.example/root/")
        self.assertEqual(models["gpt-4o-completions-default"].protocol, "openai_compatible")
        self.assertEqual(models["gpt-4o-completions-default"].base_url, "https://api.openai.com/v1")
        self.assertNotIn("cost", models["gpt-4o"].__slots__)

        cache_json = gzip.decompress(self.cache.read_bytes())
        raw_cache = json.loads(cache_json)
        self.assertEqual(raw_cache["source"], CATALOG_URL)
        self.assertEqual(raw_cache["license"], "MIT")
        self.assertIn("models.dev", raw_cache["attribution"])
        self.assertNotIn(b"catalog-only", cache_json)
        self.assertNotIn(b"description", cache_json)
        self.assertNotIn(b"headers", cache_json)
        self.assertEqual(os.stat(self.cache).st_mode & 0o777, 0o600)

    def test_protocol_mapping_overrides_and_unknowns(self) -> None:
        with patch("orbit_translate.catalog.urllib.request.urlopen", return_value=_response(_payload())):
            snapshot = self.store.refresh()
        providers = {provider.id: provider for provider in snapshot.providers}
        by_id = {
            provider_id: {model.id: model for model in provider.models}
            for provider_id, provider in providers.items()
        }
        self.assertEqual(by_id["anthropic"]["claude-fixture"].protocol, "anthropic")
        self.assertEqual(
            by_id["anthropic"]["claude-fixture"].base_url,
            "https://api.anthropic.com/v1",
        )
        self.assertEqual(by_id["google"]["gemini-fixture"].protocol, "gemini")
        self.assertEqual(
            by_id["google"]["gemini-fixture"].base_url,
            "https://generativelanguage.googleapis.com/v1beta",
        )
        self.assertEqual(by_id["router"]["router/model:latest"].protocol, "openai_compatible")
        self.assertEqual(
            by_id["router"]["router/model:latest"].base_url,
            "https://openrouter.example/api/v1",
        )
        self.assertEqual(by_id["unknown"]["manual/model"].protocol, "")
        self.assertEqual(by_id["unknown"]["manual/model"].base_url, "")
        self.assertEqual(by_id["custom"]["custom-default"].base_url, "https://api.deepseek.example/root")
        self.assertEqual(by_id["custom"]["custom-model-override"].protocol, "anthropic")
        self.assertEqual(
            by_id["custom"]["custom-model-override"].base_url,
            "https://anthropic.example/messages",
        )
        self.assertEqual(by_id["custom"]["custom-unsafe-override"].base_url, "")

    def test_unsafe_urls_never_enter_presets(self) -> None:
        payload = {
            "bad": {
                "name": "Bad",
                "npm": "@ai-sdk/openai-compatible",
                "models": {
                    "credential": _model("credential", provider={"api": "https://user:secret@api.example/v1"}),
                    "query": _model("query", provider={"api": "https://api.example/v1?token=secret"}),
                    "fragment": _model("fragment", provider={"api": "https://api.example/v1#part"}),
                    "empty-query": _model("empty-query", provider={"api": "https://api.example/v1?"}),
                    "empty-fragment": _model("empty-fragment", provider={"api": "https://api.example/v1#"}),
                    "scheme": _model("scheme", provider={"api": "file:///etc/passwd"}),
                    "invalid-port": _model("invalid-port", provider={"api": "https://api.example:99999/v1"}),
                },
            }
        }
        with patch("orbit_translate.catalog.urllib.request.urlopen", return_value=_response(payload)):
            snapshot = self.store.refresh()
        provider = snapshot.providers[0]
        for model in provider.models:
            with self.subTest(model=model.id):
                fields = preset_fields(provider, model)
                self.assertEqual(fields["type"], "openai_compatible")
                self.assertEqual(fields["base_url"], "")
                self.assertNotIn("secret", repr(fields))

    def test_cache_load_is_offline_and_ttl_is_exactly_24_hours(self) -> None:
        with patch("orbit_translate.catalog.time.time", return_value=10_000.0), patch(
            "orbit_translate.catalog.urllib.request.urlopen", return_value=_response(_payload())
        ):
            saved = self.store.refresh()
        self.assertIsNotNone(self.store.load_cached())
        with patch("orbit_translate.catalog.urllib.request.urlopen", side_effect=AssertionError("network used")):
            loaded = self.store.load_cached()
        self.assertIsNotNone(loaded)
        with patch("orbit_translate.catalog.time.time", return_value=10_000.0):
            self.assertFalse(saved.stale)
            self.assertFalse(loaded.stale)
        with patch("orbit_translate.catalog.time.time", return_value=10_000.0 + CACHE_TTL_SECONDS - 0.01):
            self.assertFalse(loaded.stale)
        with patch("orbit_translate.catalog.time.time", return_value=10_000.0 + CACHE_TTL_SECONDS):
            self.assertTrue(loaded.stale)

    def test_refresh_failure_preserves_existing_cache_and_write_failure_keeps_result(self) -> None:
        with patch("orbit_translate.catalog.urllib.request.urlopen", return_value=_response(_payload())):
            original = self.store.refresh()
        before = self.cache.read_bytes()
        with patch(
            "orbit_translate.catalog.urllib.request.urlopen",
            side_effect=URLError("private diagnostic"),
        ), self.assertRaises(CatalogError):
            self.store.refresh()
        self.assertEqual(self.cache.read_bytes(), before)
        self.assertEqual(self.store.load_cached(), original)

        with patch("orbit_translate.catalog.os.replace", side_effect=OSError("disk unavailable")), patch(
            "orbit_translate.catalog.urllib.request.urlopen", return_value=_response(_payload())
        ):
            fetched = self.store.refresh()
        self.assertEqual(fetched.providers[0].id, "anthropic")

    def test_malformed_cache_is_ignored(self) -> None:
        self.cache.parent.mkdir(parents=True)
        self.cache.write_bytes(gzip.compress(b"{}"))
        self.assertIsNone(self.store.load_cached())
        self.cache.write_bytes(b"not-gzip")
        self.assertIsNone(self.store.load_cached())


class CatalogSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.exact = CatalogModel("gpt-4o", "GPT-4o", "omni")
        self.prefix = CatalogModel("gpt-4o-mini", "GPT-4o mini", "omni")
        self.substring = CatalogModel("vendor-openai-chat", "Chat model", "OpenAI")
        self.fuzzy = CatalogModel("qwen3-coder", "Qwen 3 Coder", "coding")
        self.other = CatalogModel("sonnet", "Claude Sonnet", "anthropic")
        self.index = CatalogIndex((self.other, self.fuzzy, self.substring, self.prefix, self.exact))

    def test_exact_prefix_substring_and_subsequence_are_ordered(self) -> None:
        exact_results = self.index.search("GPT-4O")
        self.assertEqual(exact_results[0], self.exact)
        self.assertEqual(exact_results[1], self.prefix)

        substring_results = self.index.search("openai")
        self.assertEqual(substring_results[0], self.substring)

        subsequence_results = self.index.search("qwncoder")
        self.assertEqual(subsequence_results, (self.fuzzy,))

    def test_multiple_tokens_family_and_nfkc_casefold(self) -> None:
        self.assertEqual(self.index.search("QWEN CODER"), (self.fuzzy,))
        self.assertEqual(self.index.search("coding qwen"), (self.fuzzy,))
        self.assertEqual(self.index.search("ｇｐｔ ４ｏ")[0], self.exact)
        self.assertEqual(self.index.search("claude anthro"), (self.other,))

    def test_empty_and_bounded_queries_and_result_count(self) -> None:
        self.assertEqual(self.index.search(""), self.index.items)
        self.assertEqual(self.index.search("\u200b"), ())
        self.assertEqual(self.index.search("z" * 10_000), ())
        self.assertEqual(self.index.search("a " * 13), ())
        many = CatalogIndex(CatalogModel(f"model-{index:05}", "Model") for index in range(10_000))
        result = many.search("model", limit=MAX_RESULTS + 100)
        self.assertEqual(len(result), MAX_RESULTS)
        self.assertEqual(result[0].id, "model-00000")
        self.assertEqual(result[-1].id, "model-00099")
        self.assertEqual(many.search("model", limit=0), ())

    def test_deterministic_ties_and_preset_fields(self) -> None:
        duplicate_b = CatalogModel("same-b", "Shared", "family")
        duplicate_a = CatalogModel("same-a", "Shared", "family")
        first = CatalogIndex((duplicate_b, duplicate_a)).search("shared")
        second = CatalogIndex((duplicate_b, duplicate_a)).search("shared")
        self.assertEqual(first, second)
        self.assertEqual(tuple(item.id for item in first), ("same-a", "same-b"))
        provider = CatalogProvider("openai", "OpenAI", (), ())
        self.assertEqual(
            preset_fields(provider, CatalogModel("gpt-4o", "GPT-4o", protocol="openai_responses", base_url="https://api.openai.com/v1")),
            {
                "name": "OpenAI",
                "type": "openai_responses",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "catalog_provider": "openai",
            },
        )
        self.assertEqual(
            preset_fields(provider, CatalogModel("unknown", "Unknown", protocol="", base_url="")),
            {"name": "OpenAI", "type": "", "base_url": "", "model": "unknown", "catalog_provider": "openai"},
        )
        self.assertEqual(
            preset_fields(
                provider,
                CatalogModel("fixture", "Fixture", protocol="openai_compatible", base_url="https://user:secret@api.example/v1"),
            )["base_url"],
            "",
        )

    def test_preset_projection_is_cancel_neutral_and_does_not_mutate_records(self) -> None:
        provider = CatalogProvider("vendor", "Vendor", ("VENDOR_KEY",), ())
        model = CatalogModel("vendor/model", "Model", "family", "", "")
        before = (provider, model)
        fields = preset_fields(provider, model)
        self.assertEqual(fields, {"name": "Vendor", "type": "", "base_url": "", "model": "vendor/model", "catalog_provider": "vendor"})
        self.assertEqual((provider, model), before)


if __name__ == "__main__":
    unittest.main()
