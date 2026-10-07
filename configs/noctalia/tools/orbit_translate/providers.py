"""Small, opt-in translation provider adapters.

The adapters intentionally keep the UI contract small: every remote or local
service returns one bounded, plain-text result. Provider-specific structured
responses are formatted here, outside GTK.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
import re
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .config import AI_PROVIDER_TYPES, ProviderConfig
from .credentials import CredentialError, resolve_key


MAX_RESPONSE_BYTES = 2_000_000
MAX_RESULT_CHARS = 12_000
GOOGLE_DEFAULT_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_DEFAULT_URL = "https://api.mymemory.translated.net/get"
DEEPL_DEFAULT_URL = "https://www2.deepl.com/jsonrpc"
BING_AUTH_URL = "https://edge.microsoft.com/translate/auth"
BING_TRANSLATE_URL = "https://api-edge.cognitive.microsofttranslator.com/translate"
BING_DICT_URL = "https://www.bing.com/api/v6/dictionarywords/search"
CAMBRIDGE_DICT_URL = "https://dictionary.cambridge.org/search/direct/"
LINGVA_DEFAULT_URL = "https://lingva.ml"
YANDEX_DEFAULT_URL = "https://translate.yandex.net/api/v1/tr.json/translate"
ECDICT_DEFAULT_URL = "https://pot-app.com/api/dict"
TRANSMART_DEFAULT_URL = "https://transmart.qq.com/api/imt"
TATOEBA_DEFAULT_URL = "https://tatoeba.org/eng/api_v0/search"
OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434"
BING_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42"
)


@dataclass(frozen=True)
class ProviderOutcome:
    provider_id: str
    provider_name: str
    text: str = ""
    error_category: str = ""
    error_message: str = ""

    @property
    def ok(self) -> bool:
        return not self.error_category


class ProviderError(Exception):
    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category
        self.message = message


def translate_provider(
    provider: ProviderConfig,
    text: str,
    source: str,
    target: str,
    timeout_ms: int,
) -> ProviderOutcome:
    try:
        translators = {
            "google": _translate_google,
            "libretranslate": _translate_libretranslate,
            "mymemory": _translate_mymemory,
            "command": _translate_command,
            "deepl": _translate_deepl,
            "bing": _translate_bing,
            "bing_dict": _translate_bing_dict,
            "cambridge_dict": _translate_cambridge_dict,
            "lingva": _translate_lingva,
            "yandex": _translate_yandex,
            "ecdict": _translate_ecdict,
            "transmart": _translate_transmart,
            "tatoeba": _translate_tatoeba,
        }
        translator = _AI_TRANSLATORS.get(provider.type) or translators.get(provider.type)
        if translator is None:
            raise ProviderError("configuration", "Provider 类型不支持")
        translated = translator(provider, text, source, target, timeout_ms)
        return ProviderOutcome(provider.id, provider.name, text=translated)
    except ProviderError as exc:
        return ProviderOutcome(
            provider.id,
            provider.name,
            error_category=exc.category,
            error_message=exc.message,
        )
    except (urllib.error.URLError, TimeoutError, subprocess.TimeoutExpired) as exc:
        category = "timeout" if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else "network"
        message = "请求超时" if category == "timeout" else "网络请求失败"
        return ProviderOutcome(provider.id, provider.name, error_category=category, error_message=message)
    except OSError:
        return ProviderOutcome(provider.id, provider.name, error_category="system", error_message="Provider 执行失败")
    except ValueError:
        return ProviderOutcome(provider.id, provider.name, error_category="parse", error_message="响应格式无效")
    except Exception:
        return ProviderOutcome(provider.id, provider.name, error_category="unknown", error_message="Provider 执行失败")


def _translate_google(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    request = urllib.request.Request(
        build_google_url(text, source, target, provider.base_url or GOOGLE_DEFAULT_URL),
        headers={"Accept": "application/json", "User-Agent": "orbit-translate/0.1"},
    )
    return extract_google_translation(_read_json(request, timeout_ms))


def build_google_url(text: str, source: str, target: str, base_url: str = GOOGLE_DEFAULT_URL) -> str:
    params = [
        ("dt", "at"),
        ("dt", "bd"),
        ("dt", "ex"),
        ("dt", "ld"),
        ("dt", "md"),
        ("dt", "qca"),
        ("dt", "rw"),
        ("dt", "rm"),
        ("dt", "ss"),
        ("dt", "t"),
        ("client", "gtx"),
        ("sl", source),
        ("tl", target),
        ("hl", target),
        ("ie", "UTF-8"),
        ("oe", "UTF-8"),
        ("otf", "1"),
        ("ssel", "0"),
        ("tsel", "0"),
        ("kc", "7"),
        ("q", text),
    ]
    return f"{base_url.rstrip('?&')}?{urllib.parse.urlencode(params)}"


def extract_google_translation(payload: object) -> str:
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        raise ProviderError("parse", "Google 响应格式无效")
    if len(payload) > 1 and payload[1]:
        dictionary: dict[str, object] = {"pronunciations": [], "explanations": [], "sentence": []}
        first = payload[0][1] if len(payload[0]) > 1 and isinstance(payload[0][1], list) else []
        if len(first) > 3 and isinstance(first[3], str) and first[3].strip():
            dictionary["pronunciations"] = [{"symbol": first[3].strip()}]
        explanations = []
        for item in payload[1]:
            if not isinstance(item, list) or not item:
                continue
            meanings = item[2] if len(item) > 2 and isinstance(item[2], list) else []
            values = [
                meaning[0].strip()
                for meaning in meanings
                if isinstance(meaning, list)
                and meaning
                and isinstance(meaning[0], str)
                and meaning[0].strip()
            ]
            if values:
                explanations.append({"trait": str(item[0]), "explains": values})
        dictionary["explanations"] = explanations
        examples = payload[13][0] if len(payload) > 13 and isinstance(payload[13], list) and payload[13] else []
        dictionary["sentence"] = [
            {"source": item[0]}
            for item in examples
            if isinstance(item, list) and item and isinstance(item[0], str)
        ]
        return format_dictionary_result(dictionary)
    parts: list[str] = []
    for segment in payload[0]:
        if isinstance(segment, list) and segment and isinstance(segment[0], str):
            parts.append(segment[0])
    return _require_result("".join(parts))


def _translate_mymemory(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    source_code = mymemory_language_code(source)
    target_code = mymemory_language_code(target)
    if len(text.encode("utf-8")) > 500:
        raise ProviderError("configuration", "MyMemory 单次文本最多 500 字节")
    request = urllib.request.Request(
        build_mymemory_url(text, source_code, target_code, provider.base_url or MYMEMORY_DEFAULT_URL),
        headers={"Accept": "application/json", "User-Agent": "orbit-translate/0.1"},
    )
    return extract_mymemory_text(_read_json(request, timeout_ms))


def build_mymemory_url(text: str, source: str, target: str, base_url: str = MYMEMORY_DEFAULT_URL) -> str:
    query = urllib.parse.urlencode({"q": text, "langpair": f"{source}|{target}", "mt": "1"})
    return f"{base_url.rstrip('?&')}?{query}"


def mymemory_language_code(language: str) -> str:
    value = language.strip()
    if not value or value.lower() == "auto":
        raise ProviderError("configuration", "MyMemory 需要明确的 source/target 语言")
    return value


def extract_mymemory_text(payload: object) -> str:
    if not isinstance(payload, dict) or str(payload.get("responseStatus")) != "200":
        raise ProviderError("remote", "MyMemory 返回错误")
    response_data = payload.get("responseData")
    if isinstance(response_data, dict):
        result = response_data.get("translatedText")
        if isinstance(result, str) and result.strip():
            return _require_result(result)
    matches = payload.get("matches")
    if isinstance(matches, list):
        for match in matches:
            if isinstance(match, dict):
                result = match.get("translation")
                if isinstance(result, str) and result.strip():
                    return _require_result(result)
    raise ProviderError("empty", "Provider 返回了空结果")


def _translate_libretranslate(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    api_key = _provider_key(provider)
    body: dict[str, str] = {"q": text, "source": libre_language_code(source), "target": libre_language_code(target), "format": "text"}
    if api_key:
        body["api_key"] = api_key
    request = urllib.request.Request(
        provider.base_url.rstrip("/") + "/translate",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    _mark_credentialed(request, bool(api_key))
    return extract_libretranslate_text(_read_json(request, timeout_ms))


def libre_language_code(language: str) -> str:
    if language.lower() == "auto":
        return "auto"
    return language.split("-", 1)[0].lower()


def extract_libretranslate_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "LibreTranslate 响应格式无效")
    result = payload.get("translatedText")
    if not isinstance(result, str) or not result.strip():
        if isinstance(payload.get("error"), str):
            raise ProviderError("remote", "LibreTranslate 返回错误")
        raise ProviderError("empty", "Provider 返回了空结果")
    return _require_result(result)


def _translate_openai(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    api_key = _provider_key(provider)
    body = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": f"Translate from {source} to {target}. Return only the translation."},
            {"role": "user", "content": text},
        ],
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        provider.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    _mark_credentialed(request, bool(api_key))
    return extract_openai_text(_read_json(request, timeout_ms))


def _provider_key(provider: ProviderConfig) -> str:
    try:
        return resolve_key(provider)
    except CredentialError as exc:
        raise ProviderError("configuration", str(exc)) from None


def _mark_credentialed(request: urllib.request.Request, credentialed: bool) -> None:
    if credentialed:
        request._orbit_has_credentials = True


def _translate_openai_responses(
    provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int
) -> str:
    api_key = _provider_key(provider)
    body = {
        "model": provider.model,
        "instructions": _translation_instruction(source, target),
        "input": text,
        "store": False,
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        provider.base_url.rstrip("/") + "/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    _mark_credentialed(request, bool(api_key))
    return extract_openai_responses_text(_read_json(request, timeout_ms))


def extract_openai_responses_text(payload: object) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get("output"), list):
        raise ProviderError("parse", "OpenAI Responses 响应格式无效")
    parts: list[str] = []
    for item in payload["output"]:
        if not isinstance(item, dict) or not isinstance(item.get("content"), list):
            continue
        for block in item["content"]:
            if (
                isinstance(block, dict)
                and block.get("type") == "output_text"
                and isinstance(block.get("text"), str)
                and block["text"].strip()
            ):
                parts.append(block["text"].strip())
    if not parts:
        raise ProviderError("empty", "Provider 返回了空结果")
    return _require_result("\n".join(parts))


def _translate_anthropic(
    provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int
) -> str:
    api_key = _provider_key(provider)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if api_key:
        headers["x-api-key"] = api_key
    body = {
        "model": provider.model,
        "system": _translation_instruction(source, target),
        "messages": [{"role": "user", "content": text}],
        "max_tokens": 4096,
    }
    request = urllib.request.Request(
        provider.base_url.rstrip("/") + "/messages",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    _mark_credentialed(request, bool(api_key))
    return extract_anthropic_text(_read_json(request, timeout_ms))


def extract_anthropic_text(payload: object) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
        raise ProviderError("parse", "Anthropic 响应格式无效")
    parts = [
        block["text"].strip()
        for block in payload["content"]
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
        and block["text"].strip()
    ]
    if not parts:
        raise ProviderError("empty", "Provider 返回了空结果")
    return _require_result("\n".join(parts))


def _translate_gemini(
    provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int
) -> str:
    api_key = _provider_key(provider)
    encoded_model = urllib.parse.quote(provider.model, safe="")
    endpoint = provider.base_url.rstrip("/") + f"/models/{encoded_model}:generateContent"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers["x-goog-api-key"] = api_key
    body = {
        "systemInstruction": {"parts": [{"text": _translation_instruction(source, target)}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    _mark_credentialed(request, bool(api_key))
    return extract_gemini_text(_read_json(request, timeout_ms))


def extract_gemini_text(payload: object) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list):
        raise ProviderError("parse", "Gemini 响应格式无效")
    parts: list[str] = []
    for candidate in payload["candidates"]:
        content = candidate.get("content") if isinstance(candidate, dict) else None
        values = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(values, list):
            continue
        for part in values:
            if (
                isinstance(part, dict)
                and part.get("thought") is not True
                and isinstance(part.get("text"), str)
                and part["text"].strip()
            ):
                parts.append(part["text"].strip())
    if not parts:
        raise ProviderError("empty", "Provider 返回了空结果")
    return _require_result("\n".join(parts))


def _translation_instruction(source: str, target: str) -> str:
    return f"Translate from {source} to {target}. Return only the translation."


def extract_openai_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "OpenAI-compatible 响应格式无效")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProviderError("parse", "OpenAI-compatible 响应格式无效")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ProviderError("parse", "OpenAI-compatible 响应格式无效")
    result = message.get("content")
    if not isinstance(result, str) or not result.strip():
        raise ProviderError("empty", "Provider 返回了空结果")
    return _require_result(result)


def _translate_command(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    result = subprocess.run(
        substitute_command(provider.command, text, source, target),
        capture_output=True,
        text=True,
        timeout=timeout_ms / 1000,
        check=False,
    )
    if result.returncode != 0:
        raise ProviderError("command", "命令 Provider 执行失败")
    return _require_result(result.stdout)


def substitute_command(command: tuple[str, ...], text: str, source: str, target: str) -> tuple[str, ...]:
    return tuple(item.replace("{text}", text).replace("{source}", source).replace("{target}", target) for item in command)


def _translate_deepl(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    request_id = _deepl_request_id()
    body = json.dumps(
        build_deepl_body(text, source, target, request_id=request_id),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if (request_id // 1000 + 5) % 29 == 0 or (request_id // 1000 + 3) % 13 == 0:
        body = body.replace('"method":"', '"method" : "')
    else:
        body = body.replace('"method":"', '"method": "')
    request = urllib.request.Request(
        provider.base_url or DEEPL_DEFAULT_URL,
        data=body.encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "orbit-translate/0.1"},
        method="POST",
    )
    return extract_deepl_translation(_read_json(request, timeout_ms))


def build_deepl_body(
    text: str,
    source: str,
    target: str,
    *,
    request_id: int = 100000000,
    timestamp: int | None = None,
) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "method": "LMT_handle_texts",
        "params": {
            "splitting": "newlines",
            "lang": {
                "source_lang_user_selected": deepl_language_code(source),
                "target_lang": deepl_language_code(target),
            },
            "texts": [{"text": text, "requestAlternatives": 3}],
            "timestamp": timestamp if timestamp is not None else _deepl_timestamp(text),
        },
        "id": request_id,
    }


def deepl_language_code(language: str) -> str:
    if language.strip().lower() == "auto":
        return "auto"
    return language.split("-", 1)[0].upper()


def extract_deepl_translation(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "DeepL 响应格式无效")
    result = payload.get("result")
    texts = result.get("texts") if isinstance(result, dict) else None
    first = texts[0] if isinstance(texts, list) and texts else None
    value = first.get("text") if isinstance(first, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ProviderError("remote" if payload.get("error") else "empty", "DeepL 返回了空结果")
    return _require_result(value)


def _translate_bing(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    token_request = urllib.request.Request(BING_AUTH_URL, headers={"Accept": "text/plain", "User-Agent": BING_USER_AGENT})
    token = _read_text(token_request, timeout_ms).strip()
    if not token:
        raise ProviderError("remote", "Bing 未返回访问令牌")
    request = urllib.request.Request(
        build_bing_url(text, source, target, provider.base_url or BING_TRANSLATE_URL),
        data=json.dumps([{"Text": text}], ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Referer": "https://www.bing.com/",
            "User-Agent": BING_USER_AGENT,
        },
        method="POST",
    )
    return extract_bing_translation(_read_json(request, timeout_ms))


def build_bing_url(text: str, source: str, target: str, base_url: str = BING_TRANSLATE_URL) -> str:
    params = [("to", bing_language_code(target)), ("api-version", "3.0"), ("includeSentenceLength", "true")]
    if source.strip().lower() != "auto":
        params.insert(0, ("from", bing_language_code(source)))
    return f"{base_url.rstrip('?&')}?{urllib.parse.urlencode(params)}"


def bing_language_code(language: str) -> str:
    value = language.strip()
    if not value or value.lower() == "auto":
        return "auto"
    lowered = value.lower()
    if lowered in {"zh-cn", "zh-hans", "zh_cn"}:
        return "zh-Hans"
    if lowered in {"zh-tw", "zh-hant", "zh_tw"}:
        return "zh-Hant"
    return value.split("-", 1)[0].lower()


def extract_bing_translation(payload: object) -> str:
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise ProviderError("parse", "Bing 响应格式无效")
    translations = payload[0].get("translations")
    first = translations[0] if isinstance(translations, list) and translations else None
    value = first.get("text") if isinstance(first, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ProviderError("empty", "Provider 返回了空结果")
    return _require_result(value)


def _translate_bing_dict(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    _require_lookup_text(text, "必应词典")
    detected_source = _dictionary_source(source, text)
    if detected_source == bing_language_code(target):
        return _require_result(text)
    request = urllib.request.Request(
        build_bing_dict_url(text, provider.base_url or BING_DICT_URL),
        headers={"Accept": "application/json", "User-Agent": BING_USER_AGENT},
    )
    return extract_bing_dictionary_text(_read_json(request, timeout_ms))


def build_bing_dict_url(text: str, base_url: str = BING_DICT_URL) -> str:
    query = urllib.parse.urlencode(
        {
            "q": text,
            "appid": "371E7B2AF0F9B84EC491D731DF90A55719C7D209",
            "mkt": "zh-cn",
            "pname": "bingdict",
        }
    )
    return f"{base_url.rstrip('?&')}?{query}"


def extract_bing_dictionary_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "Bing 词典响应格式无效")
    values = payload.get("value")
    entry = values[0] if isinstance(values, list) and values and isinstance(values[0], dict) else None
    groups = entry.get("meaningGroups") if entry else None
    if not isinstance(groups, list) or not groups:
        raise ProviderError("empty", "Bing 词典没有收录这个词")
    dictionary: dict[str, object] = {"pronunciations": [], "explanations": [], "associations": []}
    for group in groups:
        if not isinstance(group, dict):
            continue
        parts = group.get("partsOfSpeech")
        part = parts[0] if isinstance(parts, list) and parts and isinstance(parts[0], dict) else {}
        label = str(part.get("description") or part.get("name") or "")
        meaning = group.get("meanings")
        meaning = meaning[0] if isinstance(meaning, list) and meaning and isinstance(meaning[0], dict) else {}
        rich = meaning.get("richDefinitions")
        rich = rich[0] if isinstance(rich, list) and rich and isinstance(rich[0], dict) else {}
        fragments = rich.get("fragments")
        fragment_text = _fragment_texts(fragments)
        if not fragment_text:
            continue
        if label == "发音":
            dictionary["pronunciations"].append({"region": str(part.get("name") or ""), "symbol": fragment_text[0]})
        elif label == "变形":
            dictionary["associations"].extend(fragment_text)
        else:
            dictionary["explanations"].append({"trait": label, "explains": fragment_text})
    return format_dictionary_result(dictionary)


def _translate_cambridge_dict(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    if _dictionary_source(source, text) != "en" or not re.fullmatch(r"[A-Za-z][A-Za-z'’-]*", text.strip()):
        raise ProviderError("configuration", "剑桥词典仅支持英文单词")
    request = urllib.request.Request(
        build_cambridge_url(text, source, target, provider.base_url or CAMBRIDGE_DICT_URL),
        headers={"Accept": "text/html", "User-Agent": "orbit-translate/0.1"},
    )
    return extract_cambridge_dictionary_text(_read_text(request, timeout_ms))


def build_cambridge_url(text: str, source: str, target: str, base_url: str = CAMBRIDGE_DICT_URL) -> str:
    source_code = "english" if source.lower() == "auto" else cambridge_language_code(source)
    target_code = cambridge_language_code(target)
    query = urllib.parse.urlencode({"datasetsearch": f"{source_code}-{target_code}", "q": text})
    return f"{base_url.rstrip('?&')}?{query}"


def cambridge_language_code(language: str) -> str:
    values = {
        "en": "english",
        "en-us": "english-american",
        "en-gb": "english-british",
        "zh": "chinese",
        "zh-cn": "chinese-simplified",
        "zh-tw": "chinese-traditional",
    }
    return values.get(language.lower(), language.lower())


def extract_cambridge_dictionary_text(document: str) -> str:
    parser = _ClassTextParser({"entry-body__el", "region", "pron", "posgram", "dtrans-se", "dtrans"})
    parser.feed(document[:MAX_RESPONSE_BYTES])
    if not parser.values("entry-body__el"):
        raise ProviderError("empty", "剑桥词典没有收录这个词")
    translation_values = parser.values("dtrans-se") or parser.values("dtrans")
    traits = parser.values("posgram") or ["释义"] * len(translation_values)
    dictionary = {
        "pronunciations": [
            {"region": region, "symbol": symbol}
            for region, symbol in zip(parser.values("region"), parser.values("pron"))
        ],
        "explanations": [
            {"trait": trait, "explains": [definition]}
            for trait, definition in zip(traits, translation_values)
            if definition
        ],
    }
    return format_dictionary_result(dictionary)


def _translate_lingva(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    request = urllib.request.Request(
        build_lingva_url(text, source, target, provider.base_url or LINGVA_DEFAULT_URL),
        headers={"Accept": "application/json", "User-Agent": "orbit-translate/0.1"},
    )
    return extract_lingva_translation(_read_json(request, timeout_ms), text, target)


def build_lingva_url(text: str, source: str, target: str, base_url: str = LINGVA_DEFAULT_URL) -> str:
    root = base_url.rstrip("/")
    prefix = root if root.endswith("/api/v1") else root + "/api/v1"
    escaped = urllib.parse.quote(text.replace("/", "@@"), safe="")
    return f"{prefix}/{lingva_language_code(source)}/{lingva_language_code(target)}/{escaped}"


def lingva_language_code(language: str) -> str:
    lowered = language.lower()
    if lowered == "auto":
        return "auto"
    # Lingva uses Google's codes: zh is Simplified, zh_HANT Traditional (as in Pot).
    if lowered in {"zh-tw", "zh-hk", "zh-mo", "zh-hant"}:
        return "zh_HANT"
    return lowered.split("-", 1)[0]


def extract_lingva_translation(payload: object, text: str = "", target: str = "") -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "Lingva 响应格式无效")
    value = payload.get("translation")
    if not isinstance(value, str) or not value.strip():
        raise ProviderError("remote" if payload.get("error") else "empty", "Lingva 返回了空结果")
    result = value.replace("@@", "/")
    if text and _lingva_echoed(result, text, payload, target):
        raise ProviderError("empty", "Lingva 未返回译文")
    return _require_result(result)


def _lingva_echoed(result: str, text: str, payload: dict, target: str) -> bool:
    """Degraded instances answer 200 with the input unchanged for any target.

    An unchanged result is only accepted when Lingva detected the input as
    already being in the target language.
    """
    if " ".join(result.split()).casefold() != " ".join(text.split()).casefold():
        return False
    info = payload.get("info")
    detected = info.get("detectedSource") if isinstance(info, dict) else None
    if not isinstance(detected, str) or not target:
        return True
    return lingva_language_code(detected) != lingva_language_code(target)


def _translate_yandex(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    body = urllib.parse.urlencode(
        {"source_lang": yandex_language_code(source), "target_lang": yandex_language_code(target), "text": text}
    ).encode("utf-8")
    request = urllib.request.Request(
        build_yandex_url(provider.base_url or YANDEX_DEFAULT_URL),
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "orbit-translate/0.1"},
        method="POST",
    )
    return extract_yandex_translation(_read_json(request, timeout_ms))


def build_yandex_url(base_url: str = YANDEX_DEFAULT_URL, request_id: str | None = None) -> str:
    request_id = request_id or uuid.uuid4().hex
    query = urllib.parse.urlencode({"id": request_id + "-0-0", "srv": "android"})
    return f"{base_url.rstrip('?&')}?{query}"


def yandex_language_code(language: str) -> str:
    return language.split("-", 1)[0].lower() if language.lower() != "auto" else "auto"


def extract_yandex_translation(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "Yandex 响应格式无效")
    values = payload.get("text")
    value = values[0] if isinstance(values, list) and values else None
    if not isinstance(value, str) or not value.strip():
        raise ProviderError("remote" if payload.get("message") else "empty", "Yandex 返回了空结果")
    return _require_result(value)


def _translate_ecdict(provider: ProviderConfig, text: str, _source: str, _target: str, timeout_ms: int) -> str:
    _require_lookup_text(text, "ECDICT ")
    request = urllib.request.Request(
        provider.base_url or ECDICT_DEFAULT_URL,
        data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "orbit-translate/0.1"},
        method="POST",
    )
    return extract_ecdict_text(_read_json(request, timeout_ms))


def extract_ecdict_text(payload: object) -> str:
    if isinstance(payload, str):
        return _require_result(payload)
    if isinstance(payload, dict):
        for key in ("translation", "translatedText", "text"):
            if isinstance(payload.get(key), str) and payload[key].strip():
                return _require_result(payload[key])
        nested = payload.get("result") or payload.get("data")
        if isinstance(nested, dict):
            try:
                return format_dictionary_result(nested)
            except ProviderError:
                return extract_ecdict_text(nested)
        return format_dictionary_result(payload)
    raise ProviderError("parse", "ECDICT 响应格式无效")


def _translate_transmart(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    request = urllib.request.Request(
        provider.base_url or TRANSMART_DEFAULT_URL,
        data=json.dumps(build_transmart_body(text, source, target), ensure_ascii=False).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "orbit-translate/0.1"},
        method="POST",
    )
    return extract_transmart_translation(_read_json(request, timeout_ms))


def build_transmart_body(text: str, source: str, target: str) -> dict[str, object]:
    return {
        "header": {"fn": "auto_translation"},
        "type": "plain",
        "source": {"lang": transmart_language_code(source), "text_list": [text]},
        "target": {"lang": transmart_language_code(target)},
    }


def transmart_language_code(language: str) -> str:
    values = {
        "auto": "auto",
        "zh": "zh",
        "zh-cn": "zh",
        "zh-hans": "zh",
        "zh-tw": "zh-TW",
        "zh-hant": "zh-TW",
    }
    return values.get(language.lower(), language.split("-", 1)[0].lower())


def extract_transmart_translation(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "腾讯交互翻译响应格式无效")
    values = payload.get("auto_translation")
    if not isinstance(values, list):
        raise ProviderError("remote" if payload.get("error") or payload.get("message") else "empty", "腾讯交互翻译返回了空结果")
    result = "\n".join(value.strip() for value in values if isinstance(value, str) and value.strip())
    return _require_result(result)


def _translate_tatoeba(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    _require_lookup_text(text, "Tatoeba ")
    request = urllib.request.Request(
        build_tatoeba_url(text, source, target, provider.base_url or TATOEBA_DEFAULT_URL),
        headers={"Accept": "application/json", "User-Agent": "orbit-translate/0.1"},
    )
    return extract_tatoeba_text(_read_json(request, timeout_ms))


def build_tatoeba_url(text: str, source: str, target: str, base_url: str = TATOEBA_DEFAULT_URL) -> str:
    params = {
        "query": text,
        "from": tatoeba_language_code(source),
        "to": tatoeba_language_code(target),
        "has_audio": "no",
        "sort": "relevance",
    }
    return f"{base_url.rstrip('?&')}?{urllib.parse.urlencode(params)}"


def tatoeba_language_code(language: str) -> str:
    values = {
        "auto": "",
        "en": "eng",
        "en-us": "eng",
        "en-gb": "eng",
        "zh": "cmn",
        "zh-cn": "cmn",
        "zh-tw": "cmn",
        "ja": "jpn",
        "ko": "kor",
        "fr": "fra",
        "de": "deu",
        "es": "spa",
        "ru": "rus",
    }
    return values.get(language.lower(), language.lower())


def extract_tatoeba_text(payload: object) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ProviderError("parse", "Tatoeba 响应格式无效")
    lines: list[str] = []
    for result in payload["results"]:
        if not isinstance(result, dict) or not isinstance(result.get("text"), str):
            continue
        source = result["text"].strip()
        translations = result.get("translations") or result.get("translation")
        targets = _sentence_texts(translations)
        if source and targets:
            lines.append(f"原句：{source}\n译句：{' / '.join(targets[:3])}")
        if len(lines) >= 5:
            break
    return _require_result("\n\n".join(lines))


def _translate_ollama(provider: ProviderConfig, text: str, source: str, target: str, timeout_ms: int) -> str:
    api_key = _provider_key(provider)
    base_url = provider.base_url or OLLAMA_DEFAULT_URL
    if base_url.rstrip("/").endswith("/api/chat"):
        endpoint = base_url.rstrip("/")
    elif base_url.rstrip("/").endswith("/api"):
        endpoint = base_url.rstrip("/") + "/chat"
    else:
        endpoint = base_url.rstrip("/") + "/api/chat"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(build_ollama_body(text, source, target, provider.model), ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    _mark_credentialed(request, bool(api_key))
    return extract_ollama_text(_read_json(request, timeout_ms))


def build_ollama_body(text: str, source: str, target: str, model: str) -> dict[str, object]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": f"Translate from {source} to {target}. Return only the translation."},
            {"role": "user", "content": text},
        ],
        "stream": False,
    }


def extract_ollama_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "Ollama 响应格式无效")
    message = payload.get("message")
    value = message.get("content") if isinstance(message, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ProviderError("remote" if payload.get("error") else "empty", "Ollama 返回了空结果")
    return _require_result(value)


_AI_TRANSLATORS = dict(
    zip(
        AI_PROVIDER_TYPES,
        (_translate_openai, _translate_openai_responses, _translate_anthropic, _translate_gemini, _translate_ollama),
    )
)


def format_dictionary_result(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ProviderError("parse", "词典响应格式无效")
    lines: list[str] = []
    pronunciations = payload.get("pronunciations")
    if isinstance(pronunciations, list):
        values = []
        for item in pronunciations:
            if isinstance(item, dict):
                region = str(item.get("region") or "").strip()
                symbol = str(item.get("symbol") or "").strip()
                if symbol:
                    values.append(f"{region} {symbol}".strip())
        if values:
            lines.append("发音：" + "；".join(values))
    explanations = payload.get("explanations")
    if isinstance(explanations, list):
        for item in explanations:
            if not isinstance(item, dict):
                continue
            trait = str(item.get("trait") or "释义").strip()
            explains = item.get("explains")
            if isinstance(explains, str):
                values = [explains.strip()]
            elif isinstance(explains, list):
                values = [str(value).strip() for value in explains if str(value).strip()]
            else:
                values = []
            if values:
                lines.append(f"{trait}：{'；'.join(values)}")
    associations = payload.get("associations")
    if isinstance(associations, list):
        values = [str(value).strip() for value in associations if str(value).strip()]
        if values:
            lines.append("变形：" + "；".join(values))
    sentences = payload.get("sentence")
    if isinstance(sentences, list):
        values = []
        for item in sentences[:5]:
            if isinstance(item, dict):
                source = str(item.get("source") or "").strip()
                target = str(item.get("target") or "").strip()
                if source:
                    values.append(source if not target else f"{source} → {target}")
        if values:
            lines.append("例句：" + "\n".join(values))
    return _require_result("\n".join(lines))


class _ClassTextParser(HTMLParser):
    """Collect text from a few Cambridge class selectors without third-party HTML libs."""

    def __init__(self, selectors: set[str]):
        super().__init__(convert_charrefs=True)
        self._selectors = selectors
        self._stack: list[str] = []
        self._active: list[tuple[str, str, list[str]]] = []
        self._captured: dict[str, list[str]] = {selector: [] for selector in selectors}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack.append(tag)
        classes = set()
        for key, value in attrs:
            if key == "class" and value:
                classes.update(value.split())
        for selector in self._selectors & classes:
            self._active.append((tag, selector, []))

    def handle_data(self, data: str) -> None:
        for _tag, _selector, buffer in self._active:
            buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        completed = [item for item in self._active if item[0] == tag]
        self._active = [item for item in self._active if item[0] != tag]
        for _tag, selector, buffer in completed:
            value = re.sub(r"\s+", " ", "".join(buffer)).strip()
            if value:
                self._captured[selector].append(value)

    def values(self, selector: str) -> list[str]:
        return self._captured.get(selector, [])


def _dictionary_source(source: str, text: str) -> str:
    if source.lower() != "auto":
        return bing_language_code(source)
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh-Hans"
    return "en"


def _fragment_texts(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
            result.append(item["text"].strip())
    return result


def _sentence_texts(value: object) -> list[str]:
    result: list[str] = []
    if isinstance(value, list):
        for item in value:
            result.extend(_sentence_texts(item))
    elif isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            result.append(text.strip())
        else:
            for key in ("translations", "translation"):
                result.extend(_sentence_texts(value.get(key)))
    return result


def _require_result(value: str) -> str:
    result = value.strip()
    if not result:
        raise ProviderError("empty", "Provider 返回了空结果")
    if len(result) > MAX_RESULT_CHARS:
        return result[:MAX_RESULT_CHARS].rstrip() + "…"
    return result


def _deepl_request_id() -> int:
    return (int(time.time_ns() % 99999) + 100000) * 1000


def _deepl_timestamp(text: str) -> int:
    timestamp = int(time.time() * 1000)
    count = text.count("i")
    if count:
        count += 1
        return timestamp - (timestamp % count) + count
    return timestamp


def _read_text(request: urllib.request.Request, timeout_ms: int) -> str:
    payload = _read_bytes(request, timeout_ms)
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProviderError("parse", "远程响应编码无效") from exc


def _read_bytes(request: urllib.request.Request, timeout_ms: int) -> bytes:
    try:
        if getattr(request, "_orbit_has_credentials", False):
            response_context = urllib.request.build_opener(
                _CredentialRedirectHandler(),
                urllib.request.HTTPSHandler(context=_tls_context()),
            ).open(
                request,
                timeout=timeout_ms / 1000,
            )
        else:
            response_context = urllib.request.urlopen(
                request, timeout=timeout_ms / 1000, context=_tls_context()
            )
        with response_context as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ProviderError("http", "远程服务返回错误")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise ProviderError("http", "远程服务返回错误") from None
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ProviderError("parse", "远程响应过大")
    return payload


_TLS_LOCK = threading.Lock()
_TLS_CONTEXT: ssl.SSLContext | None = None


def _tls_context() -> ssl.SSLContext:
    """One verified client context per process instead of reloading CA files per request."""
    global _TLS_CONTEXT
    with _TLS_LOCK:
        if _TLS_CONTEXT is None:
            _TLS_CONTEXT = ssl.create_default_context()
        return _TLS_CONTEXT


_LOOKUP_MAX_WORDS = 4
_LOOKUP_MAX_CHARS = 48


def _require_lookup_text(text: str, label: str) -> None:
    """Dictionary/example services only answer words and short phrases.

    Rejecting sentences locally avoids a request that cannot produce a card
    and lets the loading state finish with the real translators.
    """
    stripped = text.strip()
    if (
        len(stripped) > _LOOKUP_MAX_CHARS
        or len(stripped.split()) > _LOOKUP_MAX_WORDS
        or re.search(r"[.!?;。！？；]\s*\S", stripped)
    ):
        raise ProviderError("configuration", f"{label}仅查询单词或短语")


class _CredentialRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep authenticated request data on its configured origin only."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if getattr(req, "_orbit_has_credentials", False):
            source_origin = _http_origin(req.full_url)
            target_origin = _http_origin(newurl)
            target = urllib.parse.urlsplit(newurl)
            if (
                source_origin is None
                or target_origin != source_origin
                or target.username is not None
                or target.password is not None
            ):
                return None
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and getattr(req, "_orbit_has_credentials", False):
            redirected._orbit_has_credentials = True
        return redirected


def _http_origin(url: str) -> tuple[str, str, int] | None:
    parsed = urllib.parse.urlsplit(url)
    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return None
    default_port = 443 if parsed.scheme.lower() == "https" else 80
    return parsed.scheme.lower(), hostname.lower(), port or default_port


def _read_json(request: urllib.request.Request, timeout_ms: int) -> object:
    try:
        return json.loads(_read_text(request, timeout_ms))
    except ProviderError:
        raise
    except json.JSONDecodeError as exc:
        raise ProviderError("parse", "远程响应格式无效") from exc
