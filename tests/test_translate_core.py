from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import json
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import patch

from orbit_translate.capture import CaptureError, capture_primary, normalize_text
from orbit_translate.config import ConfigError, ProviderConfig, parse_config
from orbit_translate.engine import ResultRelay
from orbit_translate.geometry import PanelPlacement, center_panel, clamp_panel, place_panel
from orbit_translate.providers import (
    ProviderOutcome,
    build_bing_dict_url,
    build_bing_url,
    build_cambridge_url,
    build_deepl_body,
    build_google_url,
    build_lingva_url,
    build_mymemory_url,
    build_ollama_body,
    build_tatoeba_url,
    build_transmart_body,
    build_yandex_url,
    extract_bing_dictionary_text,
    extract_bing_translation,
    extract_cambridge_dictionary_text,
    extract_deepl_translation,
    extract_ecdict_text,
    extract_google_translation,
    extract_libretranslate_text,
    extract_lingva_translation,
    extract_mymemory_text,
    extract_ollama_text,
    extract_openai_text,
    extract_tatoeba_text,
    extract_transmart_translation,
    extract_yandex_translation,
    deepl_language_code,
    libre_language_code,
    mymemory_language_code,
    ProviderError,
    substitute_command,
    translate_provider,
)


class CaptureTests(unittest.TestCase):
    def test_capture_reads_primary_without_newline(self) -> None:
        calls = []

        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout=b" hello ")

        self.assertEqual(normalize_text("hello", max_chars=20), "hello")
        self.assertEqual(capture_primary(350, 20, runner=runner), "hello")
        self.assertEqual(calls[0][0], ["wl-paste", "--primary", "--no-newline"])

    def test_normalize_text_strips_and_limits_characters(self) -> None:
        self.assertEqual(normalize_text("  hello\n", max_chars=20), "hello")
        self.assertEqual(normalize_text("abcdef", max_chars=5), "ab...")

    def test_normalize_text_rejects_empty_selection(self) -> None:
        with self.assertRaises(CaptureError):
            normalize_text(" \n\t", max_chars=20)


class ConfigTests(unittest.TestCase):
    def test_flat_config_values_are_parsed(self) -> None:
        config = parse_config(
            {
                "capture_timeout_ms": 250,
                "request_timeout_ms": 5000,
                "max_chars": 1200,
                "capture_primary": False,
                "max_cards": 12,
            }
        )
        self.assertEqual(config.capture_timeout_ms, 250)
        self.assertEqual(config.request_timeout_ms, 5000)
        self.assertEqual(config.max_chars, 1200)
        self.assertFalse(config.capture_primary)
        self.assertEqual(config.max_cards, 12)

    def test_api_key_literal_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            parse_config(
                {
                    "providers": [
                        {
                            "id": "openai",
                            "name": "OpenAI",
                            "type": "openai_compatible",
                            "base_url": "https://example.com/v1",
                            "model": "test",
                            "api_key": "secret",
                        }
                    ]
                }
            )

    def test_libretranslate_provider_is_configurable(self) -> None:
        config = parse_config(
            {
                "providers": [
                    {
                        "id": "libre",
                        "name": "LibreTranslate",
                        "type": "libretranslate",
                        "enabled": True,
                        "base_url": "http://127.0.0.1:5000",
                    }
                ]
            }
        )
        self.assertEqual(config.providers[0].type, "libretranslate")

    def test_mymemory_provider_is_configurable(self) -> None:
        config = parse_config(
            {
                "providers": [
                    {
                        "id": "mymemory",
                        "name": "MyMemory",
                        "type": "mymemory",
                        "enabled": True,
                    }
                ]
            }
        )
        self.assertEqual(config.providers[0].type, "mymemory")

    def test_pot_free_provider_types_are_configurable(self) -> None:
        provider_values = [
            {"id": "deepl", "type": "deepl"},
            {"id": "bing", "type": "bing"},
            {"id": "bing-dict", "type": "bing_dict"},
            {"id": "cambridge", "type": "cambridge_dict"},
            {"id": "lingva", "type": "lingva", "base_url": "https://lingva.ml"},
            {"id": "yandex", "type": "yandex"},
            {"id": "ecdict", "type": "ecdict"},
            {"id": "transmart", "type": "transmart"},
            {"id": "tatoeba", "type": "tatoeba"},
            {"id": "ollama", "type": "ollama", "model": "gemma:2b"},
        ]
        config = parse_config({"providers": provider_values})
        self.assertEqual([provider.type for provider in config.providers], [value["type"] for value in provider_values])


class ProviderTests(unittest.TestCase):
    def test_command_substitution_keeps_user_text_as_one_argument(self) -> None:
        args = substitute_command(
            ["translator", "--text", "{text}"],
            "a; rm -rf /",
            "en",
            "zh-CN",
        )
        self.assertEqual(args, ("translator", "--text", "a; rm -rf /"))

    def test_google_url_contains_encoded_query(self) -> None:
        url = build_google_url("hello world", "auto", "zh-CN")
        self.assertIn("q=hello+world", url)
        self.assertIn("tl=zh-CN", url)
        self.assertTrue(build_google_url("hello", "en", "zh", "https://mirror.test").startswith("https://mirror.test?"))

    def test_mymemory_url_contains_language_pair(self) -> None:
        url = build_mymemory_url("hello world", "en", "zh-CN")
        self.assertIn("q=hello+world", url)
        self.assertIn("langpair=en%7Czh-CN", url)

    def test_mymemory_response_and_language_code(self) -> None:
        self.assertEqual(
            extract_mymemory_text(
                {"responseStatus": 200, "responseData": {"translatedText": "  你好 "}}
            ),
            "你好",
        )
        self.assertEqual(mymemory_language_code("en-US"), "en-US")
        with self.assertRaises(ProviderError):
            mymemory_language_code("auto")

    def test_mymemory_provider_request(self) -> None:
        provider = ProviderConfig(
            id="mymemory",
            name="MyMemory",
            type="mymemory",
            enabled=True,
        )

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return b'{"responseStatus":200,"responseData":{"translatedText":"\xe4\xbd\xa0\xe5\xa5\xbd"}}'

        with patch("orbit_translate.providers.urllib.request.urlopen", return_value=Response()) as urlopen:
            outcome = translate_provider(provider, "hello", "en", "zh-CN", 5000)

        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.text, "你好")
        request = urlopen.call_args.args[0]
        self.assertIn("langpair=en%7Czh-CN", request.full_url)

    def test_libretranslate_request_uses_two_letter_codes(self) -> None:
        provider = ProviderConfig(
            id="libre",
            name="LibreTranslate",
            type="libretranslate",
            enabled=True,
            base_url="http://127.0.0.1:5000",
        )

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return b'{"translatedText":"\xe4\xbd\xa0\xe5\xa5\xbd"}'

        with patch("orbit_translate.providers.urllib.request.urlopen", return_value=Response()) as urlopen:
            outcome = translate_provider(provider, "hello", "en-US", "zh-CN", 5000)

        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.text, "你好")
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data)["source"], "en")
        self.assertEqual(json.loads(request.data)["target"], "zh")

    def test_libretranslate_response_and_language_code(self) -> None:
        self.assertEqual(extract_libretranslate_text({"translatedText": "你好"}), "你好")
        self.assertEqual(libre_language_code("en-US"), "en")
        self.assertEqual(libre_language_code("auto"), "auto")

    def test_openai_response_segments_are_joined(self) -> None:
        payload = json.dumps({"choices": [{"message": {"content": "  one\n two "}}]})
        self.assertEqual(extract_openai_text(json.loads(payload)), "one\n two")

    def test_google_dictionary_response_is_formatted(self) -> None:
        payload = [[['hello', '你好', None, None], ['hello', '你好', None, '/həˈləʊ/']], [["名词", None, [["问候"]]]], None, None, None, None, None, None, None, None, None, None, None, [["Hello there"]]]
        result = extract_google_translation(payload)
        self.assertIn("发音：/həˈləʊ/", result)
        self.assertIn("名词：问候", result)

    def test_deepl_payload_and_response(self) -> None:
        body = build_deepl_body("hello", "en-US", "zh-CN", request_id=123, timestamp=456)
        self.assertEqual(body["params"]["lang"], {"source_lang_user_selected": "EN", "target_lang": "ZH"})
        self.assertEqual(extract_deepl_translation({"result": {"texts": [{"text": "你好"}]}}), "你好")
        self.assertEqual(deepl_language_code("auto"), "auto")

    def test_bing_url_and_response(self) -> None:
        url = build_bing_url("hello", "en-US", "zh-CN", "https://example.test/translate")
        self.assertIn("from=en", url)
        self.assertIn("to=zh-Hans", url)
        self.assertEqual(extract_bing_translation([{"translations": [{"text": "你好"}]}]), "你好")

    def test_dictionary_urls_encode_text(self) -> None:
        self.assertIn("q=hello+world", build_bing_dict_url("hello world"))
        self.assertIn("datasetsearch=english-chinese-simplified", build_cambridge_url("hello", "en", "zh-CN"))
        self.assertIn("hello%40%40world", build_lingva_url("hello/world", "en", "zh-CN"))

    def test_lookup_services_skip_sentences_without_network(self) -> None:
        sentence = "Hello world. How are you today?"
        with patch("orbit_translate.providers.urllib.request.urlopen") as urlopen:
            for provider_type in ("bing_dict", "ecdict", "tatoeba"):
                provider = parse_config({"providers": [{"id": provider_type, "type": provider_type}]}).providers[0]
                outcome = translate_provider(provider, sentence, "en", "zh-CN", 5000)
                self.assertEqual(outcome.error_category, "configuration")
        urlopen.assert_not_called()

    def test_https_requests_share_one_verified_context(self) -> None:
        provider = parse_config({"providers": [{"id": "lingva", "type": "lingva"}]}).providers[0]
        with patch("orbit_translate.providers.urllib.request.urlopen", side_effect=urllib.error.URLError("offline fixture")) as urlopen:
            translate_provider(provider, "hi", "en", "zh-CN", 5000)
            translate_provider(provider, "hi", "en", "zh-CN", 5000)
        first, second = (call.kwargs["context"] for call in urlopen.call_args_list)
        self.assertIs(first, second)
        self.assertTrue(first.check_hostname)

    def test_lingva_maps_traditional_chinese_like_pot(self) -> None:
        self.assertTrue(build_lingva_url("hi", "en", "zh-CN").endswith("/api/v1/en/zh/hi"))
        self.assertTrue(build_lingva_url("hi", "auto", "zh-TW").endswith("/api/v1/auto/zh_HANT/hi"))

    def test_lingva_echo_of_untranslated_input_is_a_failure(self) -> None:
        echo = {"translation": "Hello world", "info": {"detectedSource": "en"}}
        with self.assertRaises(ProviderError) as raised:
            extract_lingva_translation(echo, "Hello  world", "zh-CN")
        self.assertEqual(raised.exception.category, "empty")
        with self.assertRaises(ProviderError):
            extract_lingva_translation({"translation": "Hello world"}, "Hello world", "zh-CN")
        same_language = {"translation": "你好世界", "info": {"detectedSource": "zh"}}
        self.assertEqual(extract_lingva_translation(same_language, "你好世界", "zh-CN"), "你好世界")
        translated = {"translation": "你好世界", "info": {"detectedSource": "en"}}
        self.assertEqual(extract_lingva_translation(translated, "Hello world", "zh-CN"), "你好世界")

    def test_bing_dictionary_response_is_formatted(self) -> None:
        payload = {
            "value": [{
                "meaningGroups": [
                    {"partsOfSpeech": [{"description": "发音", "name": "美式"}], "meanings": [{"richDefinitions": [{"fragments": [{"text": "/həˈloʊ/"}]}]}]},
                    {"partsOfSpeech": [{"description": "快速释义", "name": "动词"}], "meanings": [{"richDefinitions": [{"fragments": [{"text": "问候"}]}]}]},
                ]
            }]
        }
        result = extract_bing_dictionary_text(payload)
        self.assertIn("发音：美式 /həˈloʊ/", result)
        self.assertIn("快速释义：问候", result)

    def test_cambridge_dictionary_html_is_formatted(self) -> None:
        html = '<div class="pr entry-body__el"><span class="region">UK</span><span class="pron">/həˈləʊ/</span><span class="posgram">verb</span><span class="dtrans-se">问候</span></div>'
        result = extract_cambridge_dictionary_text(html)
        self.assertIn("发音：UK /həˈləʊ/", result)
        self.assertIn("verb：问候", result)

    def test_remaining_pot_response_shapes_are_formatted(self) -> None:
        self.assertEqual(extract_lingva_translation({"translation": "你好@@世界"}), "你好/世界")
        self.assertEqual(extract_yandex_translation({"text": ["你好"]}), "你好")
        self.assertEqual(extract_transmart_translation({"auto_translation": ["你好", "世界"]}), "你好\n世界")
        self.assertEqual(extract_ollama_text({"message": {"content": "你好"}}), "你好")
        self.assertIn("释义：你好", extract_ecdict_text({"explanations": [{"trait": "释义", "explains": ["你好"]}]}))

    def test_tatoeba_and_ollama_requests(self) -> None:
        url = build_tatoeba_url("hello", "en", "zh-CN")
        self.assertIn("from=eng", url)
        self.assertIn("to=cmn", url)
        result = extract_tatoeba_text({"results": [{"text": "Hello.", "translations": [[{"text": "你好。"}]]}]})
        self.assertIn("原句：Hello.", result)
        self.assertIn("译句：你好。", result)
        body = build_ollama_body("hello", "en", "zh-CN", "gemma:2b")
        self.assertFalse(body["stream"])
        self.assertEqual(body["model"], "gemma:2b")
        self.assertEqual(build_transmart_body("hello", "en-US", "zh-CN")["target"], {"lang": "zh"})

    def test_yandex_url_has_android_request_id(self) -> None:
        url = build_yandex_url("https://example.test/translate", request_id="abc")
        self.assertIn("id=abc-0-0", url)
        self.assertIn("srv=android", url)


class ResultRelayTests(unittest.TestCase):
    def test_relay_buffers_until_attached_then_forwards(self) -> None:
        relay = ResultRelay()
        first = ProviderOutcome("a", "A", text="一")
        second = ProviderOutcome("b", "B", text="二")
        relay(first)
        received: list[ProviderOutcome] = []
        relay.attach(received.append)
        relay(second)
        self.assertEqual(received, [first, second])

    def test_max_parallel_allows_all_typical_channels(self) -> None:
        self.assertEqual(parse_config({}).max_parallel, 8)
        self.assertEqual(parse_config({"max_parallel": 16}).max_parallel, 16)
        with self.assertRaises(ConfigError):
            parse_config({"max_parallel": 17})


class GeometryTests(unittest.TestCase):
    def test_panel_opens_below_pointer_with_leading_corner_under_cursor(self) -> None:
        self.assertEqual(
            place_panel(600, 300, 1920, 1080, 340, 300),
            PanelPlacement(580, 316, False, 752),
        )

    def test_panel_stays_below_when_comfortable_height_fits(self) -> None:
        placement = place_panel(600, 700, 1920, 1080, 340, 300)
        self.assertFalse(placement.above)
        self.assertEqual((placement.y, placement.max_height), (716, 352))

    def test_panel_flips_above_and_anchors_bottom_near_screen_bottom(self) -> None:
        self.assertEqual(
            place_panel(1900, 1040, 1920, 1080, 340, 300),
            PanelPlacement(1568, 1024, True, 1012),
        )

    def test_short_room_on_both_sides_prefers_the_larger_side(self) -> None:
        self.assertFalse(place_panel(100, 200, 1920, 480, 340, 300).above)
        self.assertTrue(place_panel(100, 280, 1920, 480, 340, 300).above)

    def test_panel_clamps_at_surface_origin(self) -> None:
        self.assertEqual(place_panel(0, 0, 1920, 1080, 340, 300), PanelPlacement(12, 16, False, 1052))

    def test_center_fallback_sits_in_upper_middle(self) -> None:
        self.assertEqual(center_panel(1920, 1080, 340, 400), PanelPlacement(790, 270, False, 798))

    def test_clamp_keeps_panel_inside_surface(self) -> None:
        self.assertEqual(clamp_panel(1800, 900, 340, 300, 1920, 1080, 0), (1580, 780))


if __name__ == "__main__":
    unittest.main()
