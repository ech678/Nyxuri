from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import json
from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

from orbit_translate.config import AI_PROVIDER_TYPES, ConfigError, ProviderConfig, parse_config
from orbit_translate.providers import (
    ProviderError,
    _CredentialRedirectHandler,
    extract_anthropic_text,
    extract_gemini_text,
    extract_openai_responses_text,
    translate_provider,
)


class JsonResponse:
    status = 200

    def __init__(self, payload: object):
        self.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self) -> JsonResponse:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def read(self, _limit: int) -> bytes:
        return self.payload


class AiConfigTests(unittest.TestCase):
    def test_ai_provider_tuple_is_the_five_supported_ai_types(self) -> None:
        self.assertEqual(
            AI_PROVIDER_TYPES,
            ("openai_compatible", "openai_responses", "anthropic", "gemini", "ollama"),
        )

    def test_ai_protocols_require_model_and_non_ollama_base_url(self) -> None:
        for provider_type in AI_PROVIDER_TYPES:
            with self.subTest(provider_type=provider_type):
                missing_model = {"id": "test", "type": provider_type}
                if provider_type != "ollama":
                    missing_model["base_url"] = "https://api.example/v1"
                with self.assertRaises(ConfigError):
                    parse_config({"providers": [missing_model]})
                if provider_type != "ollama":
                    with self.assertRaises(ConfigError):
                        parse_config(
                            {"providers": [{"id": "test", "type": provider_type, "model": "model"}]}
                        )

    def test_ai_base_urls_reject_credentials_query_and_fragment(self) -> None:
        invalid_urls = (
            "https://user:password@api.example/v1",
            "https://api.example/v1?token=x",
            "https://api.example/v1#section",
            "https://api.example/v1?",
            "https://api.example/v1#",
            "https://[invalid/v1",
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ConfigError):
                parse_config(
                    {
                        "providers": [
                            {
                                "id": "ai",
                                "type": "openai_responses",
                                "base_url": url,
                                "model": "test-model",
                            }
                        ]
                    }
                )

    def test_ollama_keeps_its_local_base_url_default(self) -> None:
        config = parse_config(
            {"providers": [{"id": "ollama", "type": "ollama", "model": "gemma:2b"}]}
        )
        self.assertEqual(config.providers[0].base_url, "")

    def test_secret_reference_and_environment_reference_are_exclusive(self) -> None:
        base = {"id": "libre", "type": "libretranslate", "base_url": "http://localhost:5000"}
        configured = parse_config({"providers": [{**base, "api_key_secret": "kwallet:libre"}]})
        self.assertEqual(configured.providers[0].api_key_secret, "kwallet:libre")
        with self.assertRaises(ConfigError):
            parse_config({"providers": [{**base, "api_key_secret": "file:libre"}]})
        with self.assertRaises(ConfigError):
            parse_config(
                {"providers": [{**base, "api_key_env": "LIBRE_KEY", "api_key_secret": "kwallet:libre"}]}
            )


class AiProviderRequestTests(unittest.TestCase):
    def _provider(self, provider_type: str, base_url: str, model: str) -> ProviderConfig:
        return parse_config(
            {
                "providers": [
                    {
                        "id": "ai",
                        "name": "AI",
                        "type": provider_type,
                        "enabled": True,
                        "base_url": base_url,
                        "model": model,
                        "api_key_env": "ORBIT_TEST_API_KEY",
                    }
                ]
            }
        ).providers[0]

    def _request_outcome(self, provider: ProviderConfig, response_payload: object):
        captured: dict[str, object] = {}

        class Opener:
            def open(self, request: Request, timeout: float):
                captured["request"] = request
                captured["timeout"] = timeout
                return JsonResponse(response_payload)

        with (
            patch.dict("os.environ", {"ORBIT_TEST_API_KEY": "key-for-tests"}),
            patch("orbit_translate.providers.urllib.request.build_opener", return_value=Opener()) as opener,
            patch("orbit_translate.providers.urllib.request.urlopen") as urlopen,
        ):
            outcome = translate_provider(provider, "你好，世界 🌍", "zh-CN", "en", 2500)
        self.assertTrue(outcome.ok, outcome.error_message)
        opener.assert_called_once()
        self.assertIsInstance(opener.call_args.args[0], _CredentialRedirectHandler)
        urlopen.assert_not_called()
        return captured["request"]

    @staticmethod
    def _body(request: Request) -> dict[str, object]:
        return json.loads(request.data.decode("utf-8"))

    @staticmethod
    def _headers(request: Request) -> dict[str, str]:
        return {key.lower(): value for key, value in request.header_items()}

    def test_openai_responses_request_and_text_extraction(self) -> None:
        response = {
            "output": [
                {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "hidden"}]},
                {"type": "message", "content": [{"type": "output_text", "text": "Hello 🌍"}]},
            ]
        }
        request = self._request_outcome(
            self._provider("openai_responses", "https://api.example/v1", "gpt-test"), response
        )
        self.assertEqual(request.full_url, "https://api.example/v1/responses")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            self._body(request),
            {
                "model": "gpt-test",
                "instructions": "Translate from zh-CN to en. Return only the translation.",
                "input": "你好，世界 🌍",
                "store": False,
            },
        )
        self.assertEqual(self._headers(request)["authorization"], "Bearer key-for-tests")
        self.assertNotIn("key-for-tests", repr(self._provider("openai_responses", "https://api.example/v1", "gpt-test")))
        self.assertEqual(extract_openai_responses_text(response), "Hello 🌍")

    def test_anthropic_messages_request_uses_text_blocks(self) -> None:
        response = {
            "content": [
                {"type": "tool_use", "id": "ignored", "input": {}},
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": "🌍"},
            ]
        }
        request = self._request_outcome(
            self._provider("anthropic", "https://api.example/v1", "claude-test"), response
        )
        self.assertEqual(request.full_url, "https://api.example/v1/messages")
        self.assertEqual(
            self._body(request),
            {
                "model": "claude-test",
                "system": "Translate from zh-CN to en. Return only the translation.",
                "messages": [{"role": "user", "content": "你好，世界 🌍"}],
                "max_tokens": 4096,
            },
        )
        headers = self._headers(request)
        self.assertEqual(headers["x-api-key"], "key-for-tests")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        self.assertEqual(extract_anthropic_text(response), "Hello\n🌍")

    def test_gemini_request_uses_header_and_ignores_thought_parts(self) -> None:
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "internal", "thought": True},
                            {"text": "Hello 🌍"},
                        ]
                    }
                }
            ]
        }
        request = self._request_outcome(
            self._provider("gemini", "https://generative.example/v1beta", "gemini-2.5/flash"), response
        )
        self.assertEqual(
            request.full_url,
            "https://generative.example/v1beta/models/gemini-2.5%2Fflash:generateContent",
        )
        self.assertEqual(
            self._body(request),
            {
                "systemInstruction": {
                    "parts": [{"text": "Translate from zh-CN to en. Return only the translation."}]
                },
                "contents": [{"role": "user", "parts": [{"text": "你好，世界 🌍"}]}],
            },
        )
        headers = self._headers(request)
        self.assertEqual(headers["x-goog-api-key"], "key-for-tests")
        self.assertNotIn("key-for-tests", request.full_url)
        self.assertEqual(extract_gemini_text(response), "Hello 🌍")

    def test_existing_openai_compatible_request_remains_supported(self) -> None:
        payload = {"choices": [{"message": {"content": "  Hello 🌍  "}}]}
        request = self._request_outcome(
            self._provider("openai_compatible", "https://api.example/v1", "chat-test"), payload
        )
        self.assertEqual(request.full_url, "https://api.example/v1/chat/completions")
        self.assertEqual(
            self._body(request),
            {
                "model": "chat-test",
                "messages": [
                    {"role": "system", "content": "Translate from zh-CN to en. Return only the translation."},
                    {"role": "user", "content": "你好，世界 🌍"},
                ],
            },
        )
        self.assertEqual(self._headers(request)["authorization"], "Bearer key-for-tests")

    def test_empty_and_malformed_protocol_responses_fail_safely(self) -> None:
        with self.assertRaises(ProviderError):
            extract_openai_responses_text({"output": []})
        with self.assertRaises(ProviderError):
            extract_openai_responses_text({"output": [{"content": [{"type": "reasoning", "text": "secret"}]}]})
        with self.assertRaises(ProviderError):
            extract_openai_responses_text({"output": "bad"})
        with self.assertRaises(ProviderError):
            extract_anthropic_text({"content": [{"type": "image", "source": {}}]})
        with self.assertRaises(ProviderError):
            extract_gemini_text({"candidates": [{"content": {"parts": [{"thought": True, "text": "private"}]}}]})
        with self.assertRaises(ProviderError):
            extract_gemini_text({"candidates": None})

    def test_missing_secret_key_is_a_safe_provider_failure(self) -> None:
        provider = parse_config(
            {
                "providers": [
                    {
                        "id": "ai",
                        "type": "openai_responses",
                        "base_url": "https://api.example/v1",
                        "model": "test-model",
                        "api_key_secret": "kwallet:ai",
                    }
                ]
            }
        ).providers[0]
        failure = SimpleNamespace(returncode=2, stdout="", stderr="private secret-value output")
        with (
            patch("orbit_translate.credentials.subprocess.run", return_value=failure),
            patch("orbit_translate.providers.urllib.request.build_opener") as build_opener,
        ):
            outcome = translate_provider(provider, "input", "en", "zh", 1000)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.error_category, "configuration")
        self.assertNotIn("secret-value", outcome.error_message)
        build_opener.assert_not_called()
        self.assertNotIn("secret-value", repr(provider))

    def test_libretranslate_resolves_secret_reference_for_its_body(self) -> None:
        provider = parse_config(
            {
                "providers": [
                    {
                        "id": "libre",
                        "type": "libretranslate",
                        "base_url": "https://libre.example",
                        "api_key_secret": "kwallet:libre",
                    }
                ]
            }
        ).providers[0]
        captured: dict[str, Request] = {}

        class Opener:
            def open(self, request: Request, timeout: float):
                captured["request"] = request
                return JsonResponse({"translatedText": "Hello"})

        with (
            patch("orbit_translate.providers.resolve_key", return_value="secret-for-test"),
            patch("orbit_translate.providers.urllib.request.build_opener", return_value=Opener()) as opener,
        ):
            outcome = translate_provider(provider, "你好", "zh-CN", "en", 2000)
        self.assertTrue(outcome.ok)
        request = captured["request"]
        self.assertEqual(json.loads(request.data.decode("utf-8"))["api_key"], "secret-for-test")
        self.assertTrue(request._orbit_has_credentials)
        self.assertIsInstance(opener.call_args.args[0], _CredentialRedirectHandler)

    def test_ollama_local_default_and_request_contract_remain(self) -> None:
        provider = parse_config(
            {"providers": [{"id": "ollama", "type": "ollama", "model": "gemma:2b"}]}
        ).providers[0]
        captured: dict[str, Request] = {}

        def open_request(request: Request, timeout: float, **_kwargs):
            captured["request"] = request
            return JsonResponse({"message": {"content": "Hello"}})

        with patch("orbit_translate.providers.urllib.request.urlopen", side_effect=open_request):
            outcome = translate_provider(provider, "你好", "zh-CN", "en", 2000)
        self.assertTrue(outcome.ok)
        self.assertEqual(captured["request"].full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(
            json.loads(captured["request"].data.decode("utf-8")),
            {
                "model": "gemma:2b",
                "messages": [
                    {"role": "system", "content": "Translate from zh-CN to en. Return only the translation."},
                    {"role": "user", "content": "你好"},
                ],
                "stream": False,
            },
        )

    def test_http_server_error_body_is_not_returned_to_provider_outcome(self) -> None:
        provider = self._provider("openai_responses", "https://api.example/v1", "gpt-test")

        class Opener:
            def open(self, request: Request, timeout: float):
                raise HTTPError(
                    request.full_url,
                    500,
                    "failure includes hidden-key",
                    {},
                    BytesIO(b"failure response contains hidden-key"),
                )

        with (
            patch.dict("os.environ", {"ORBIT_TEST_API_KEY": "hidden-key"}),
            patch("orbit_translate.providers.urllib.request.build_opener", return_value=Opener()),
        ):
            outcome = translate_provider(provider, "input", "en", "zh", 2000)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.error_category, "http")
        self.assertNotIn("hidden-key", outcome.error_message)


class CredentialRedirectTests(unittest.TestCase):
    def test_credentialed_requests_block_cross_origin_and_keep_same_origin_guard(self) -> None:
        request = Request("https://api.example/v1", headers={"Authorization": "Bearer hidden"})
        request._orbit_has_credentials = True
        handler = _CredentialRedirectHandler()
        cross_origin = handler.redirect_request(
            request,
            None,
            307,
            "Temporary Redirect",
            {},
            "https://attacker.example/collect",
        )
        self.assertIsNone(cross_origin)
        same_origin = handler.redirect_request(
            request,
            None,
            307,
            "Temporary Redirect",
            {},
            "https://api.example/v1-next",
        )
        self.assertIsNotNone(same_origin)
        self.assertTrue(same_origin._orbit_has_credentials)
        self.assertIsNone(
            handler.redirect_request(
                request,
                None,
                307,
                "Temporary Redirect",
                {},
                "https://user:pass@api.example/redirect",
            )
        )


if __name__ == "__main__":
    unittest.main()
