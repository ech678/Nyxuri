"""Bounded public models.dev catalog projection and local search."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import gzip
import heapq
from itertools import islice
import json
import math
import os
from pathlib import Path
import re
import socket
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import zlib
from urllib.parse import urlsplit

from .config import AI_PROVIDER_TYPES, CATALOG_PROVIDER_ID


CATALOG_URL = "https://models.dev/api.json"
CACHE_TTL_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT_SECONDS = 15
MAX_WIRE_BYTES = 8 * 1024 * 1024
MAX_DECODED_BYTES = 16 * 1024 * 1024
MAX_RESULTS = 100
MAX_QUERY_LENGTH = 128
MAX_QUERY_TOKENS = 12
MAX_PROVIDER_COUNT = 2048
MAX_MODELS_PER_PROVIDER = 20_000
MAX_TOTAL_MODELS = 100_000
MAX_INDEX_ITEMS = 100_000
_CACHE_VERSION = 1
_CACHE_LICENSE = "MIT"
_CACHE_ATTRIBUTION = "models.dev API; MIT License; Copyright 2025 models.dev"
_CACHE_LICENSE_NOTICE = '''MIT License

Copyright (c) 2025 models.dev

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")

_PROTOCOLS = frozenset(AI_PROVIDER_TYPES)
_SPECIALIZED_TYPES = frozenset(
    {
        "audio",
        "decision",
        "embedding",
        "embeddings",
        "image",
        "image_generation",
        "image-generation",
        "moderation",
        "rerank",
        "reranking",
        "speech",
        "transcription",
    }
)
_SDK_PROTOCOLS = {
    "@ai-sdk/openai": "openai_responses",
    "@ai-sdk/openai-compatible": "openai_compatible",
    "@openrouter/ai-sdk-provider": "openai_compatible",
    "@ai-sdk/anthropic": "anthropic",
    "@ai-sdk/google": "gemini",
}
_FIRST_PARTY = {
    "openai": ("openai_responses", "https://api.openai.com/v1"),
    "anthropic": ("anthropic", "https://api.anthropic.com/v1"),
    "google": ("gemini", "https://generativelanguage.googleapis.com/v1beta"),
}


class CatalogError(ValueError):
    """A safe, local catalog error; remote diagnostics are never included."""


@dataclass(frozen=True, slots=True)
class CatalogModel:
    id: str
    name: str
    family: str = ""
    protocol: str = ""
    base_url: str = ""


@dataclass(frozen=True, slots=True)
class CatalogProvider:
    id: str
    name: str
    env_names: tuple[str, ...]
    models: tuple[CatalogModel, ...]


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    providers: tuple[CatalogProvider, ...]
    fetched_at: float

    @property
    def stale(self) -> bool:
        return time.time() - self.fetched_at >= CACHE_TTL_SECONDS


def _cache_path() -> Path:
    cache_home = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache_home) / "orbit-translate" / "models-dev-v1.json.gz"


def _safe_text(value: object, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    if len(value) > maximum:
        return None
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for char in value):
        return None
    value = value.strip()
    if not value:
        return None
    return value


def _safe_base_url(value: object) -> str:
    url = _safe_text(value, 500)
    if url is None or any(char.isspace() or char == "\\" for char in url):
        return ""
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or "?" in url
        or "#" in url
        or parsed.query
        or parsed.fragment
    ):
        return ""
    return url


def _text_modalities(model: Mapping[str, object]) -> bool:
    modalities = model.get("modalities")
    if not isinstance(modalities, Mapping):
        return False
    incoming = modalities.get("input")
    outgoing = modalities.get("output")
    if (
        not isinstance(incoming, list)
        or not isinstance(outgoing, list)
        or len(incoming) > 32
        or len(outgoing) > 32
    ):
        return False
    inputs = {item.casefold() for item in incoming if isinstance(item, str) and len(item) <= 32}
    outputs = {item.casefold() for item in outgoing if isinstance(item, str) and len(item) <= 32}
    # Text translation does not use the additional modalities of a general LLM.
    return "text" in inputs and "text" in outputs


def _protocol_for(npm: object, shape: object, provider_id: str) -> str:
    package = npm.casefold() if isinstance(npm, str) and len(npm) <= 200 else ""
    shape_name = shape.casefold() if isinstance(shape, str) and len(shape) <= 32 else ""
    protocol = _SDK_PROTOCOLS.get(package, "")
    if package == "@ai-sdk/openai":
        if shape_name == "completions":
            return "openai_compatible"
        return "openai_responses"
    if protocol:
        return protocol
    # The catalog's first-party provider IDs are separately verified defaults.
    if not package:
        first_party = provider_id.casefold()
        if first_party == "openai" and shape_name == "completions":
            return "openai_compatible"
        return _FIRST_PARTY.get(first_party, ("", ""))[0]
    return ""


def _provider_projection(provider_id: str, raw: object) -> CatalogProvider | None:
    if not isinstance(raw, Mapping):
        return None
    safe_id = _safe_text(provider_id, 100)
    safe_name = _safe_text(raw.get("name", provider_id), 160)
    if safe_id is None or safe_name is None:
        return None

    raw_env = raw.get("env", ())
    env_names: list[str] = []
    if isinstance(raw_env, list):
        for env_name in raw_env[:32]:
            candidate = _safe_text(env_name, 80)
            if candidate and _ENV_NAME.fullmatch(candidate) and candidate not in env_names:
                env_names.append(candidate)

    raw_models = raw.get("models")
    if not isinstance(raw_models, Mapping):
        raise CatalogError("目录响应格式无效")
    if len(raw_models) > MAX_MODELS_PER_PROVIDER:
        raise CatalogError("目录条目数量超出安全上限")

    models: list[CatalogModel] = []
    provider_npm = raw.get("npm")
    provider_api_present = "api" in raw
    provider_api = raw.get("api")
    provider_shape = raw.get("shape")
    for model_id in sorted(raw_models):
        if not isinstance(model_id, str):
            continue
        model = raw_models[model_id]
        if not isinstance(model, Mapping) or not _text_modalities(model):
            continue
        status = model.get("status")
        model_type = model.get("type")
        safe_status = _safe_text(status, 64) if isinstance(status, str) else None
        safe_model_type = _safe_text(model_type, 64) if isinstance(model_type, str) else None
        if (
            (safe_status is not None and safe_status.casefold() == "deprecated")
            or model.get("deprecated") is True
            or (safe_model_type is not None and safe_model_type.casefold() in _SPECIALIZED_TYPES)
        ):
            continue
        safe_model_id = _safe_text(model_id, 120)
        safe_model_name = _safe_text(model.get("name", model_id), 200)
        if safe_model_id is None or safe_model_name is None:
            continue
        raw_family = _safe_text(model.get("family", ""), 120)
        family = raw_family or ""

        model_provider = model.get("provider")
        if not isinstance(model_provider, Mapping):
            model_provider = {}
        npm = model_provider.get("npm", provider_npm)
        shape = model_provider.get("shape", provider_shape)
        protocol = _protocol_for(npm, shape, safe_id)
        if protocol not in _PROTOCOLS:
            protocol = ""

        if "api" in model_provider:
            api_value = model_provider.get("api")
            api_present = True
        else:
            api_value = provider_api
            api_present = provider_api_present
        base_url = _safe_base_url(api_value) if api_present and protocol else ""
        if not api_present and protocol:
            first_party = _FIRST_PARTY.get(safe_id.casefold())
            is_openai_completions = safe_id.casefold() == "openai" and protocol == "openai_compatible"
            if first_party and (protocol == first_party[0] or is_openai_completions):
                base_url = first_party[1]

        models.append(CatalogModel(safe_model_id, safe_model_name, family, protocol, base_url))
    return CatalogProvider(safe_id, safe_name, tuple(env_names), tuple(models))


def _project_catalog(raw: object) -> tuple[CatalogProvider, ...]:
    if not isinstance(raw, Mapping) or not raw:
        raise CatalogError("目录响应格式无效")
    if len(raw) > MAX_PROVIDER_COUNT:
        raise CatalogError("目录条目数量超出安全上限")
    providers: list[CatalogProvider] = []
    total_models = 0
    for provider_id in sorted(raw):
        if not isinstance(provider_id, str):
            continue
        provider = _provider_projection(provider_id, raw[provider_id])
        if provider is None:
            continue
        total_models += len(provider.models)
        if total_models > MAX_TOTAL_MODELS:
            raise CatalogError("目录条目数量超出安全上限")
        providers.append(provider)
    if not providers:
        raise CatalogError("目录响应格式无效")
    return tuple(providers)


def _inflate_gzip(data: bytes, maximum: int) -> bytes:
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decoded = decompressor.decompress(data, maximum + 1)
        if len(decoded) > maximum or decompressor.unconsumed_tail:
            raise CatalogError("目录数据超出安全上限")
        decoded += decompressor.flush(maximum + 1 - len(decoded))
        if len(decoded) > maximum:
            raise CatalogError("目录数据超出安全上限")
        if not decompressor.eof or decompressor.unused_data:
            raise CatalogError("目录压缩数据无效")
        return decoded
    except CatalogError:
        raise
    except (OSError, zlib.error, ValueError):
        raise CatalogError("目录压缩数据无效") from None


def _read_json_bytes(data: bytes, *, compressed: bool) -> object:
    if len(data) > MAX_WIRE_BYTES:
        raise CatalogError("目录数据超出安全上限")
    decoded = _inflate_gzip(data, MAX_DECODED_BYTES) if compressed else data
    if len(decoded) > MAX_DECODED_BYTES:
        raise CatalogError("目录数据超出安全上限")
    try:
        return json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError, OverflowError):
        raise CatalogError("目录响应格式无效") from None


def _header(response: object, name: str) -> str:
    headers = getattr(response, "headers", None)
    if headers is not None:
        try:
            value = headers.get(name, "")
            if isinstance(value, str):
                return value
        except Exception:
            pass
    getheader = getattr(response, "getheader", None)
    if callable(getheader):
        try:
            value = getheader(name, "")
            return value if isinstance(value, str) else ""
        except Exception:
            pass
    return ""


def _fetch_payload() -> object:
    request = urllib.request.Request(
        CATALOG_URL,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "Orbit-Translate/1.0 (public model catalog)",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            final_url = response.geturl() if callable(getattr(response, "geturl", None)) else CATALOG_URL
            if final_url != CATALOG_URL:
                raise CatalogError("目录地址发生跳转")
            length = _header(response, "Content-Length").strip()
            if length.isdecimal() and int(length) > MAX_WIRE_BYTES:
                raise CatalogError("目录数据超出安全上限")
            body = response.read(MAX_WIRE_BYTES + 1)
            if not isinstance(body, bytes) or len(body) > MAX_WIRE_BYTES:
                raise CatalogError("目录数据超出安全上限")
            encoding = _header(response, "Content-Encoding").strip().casefold()
            if encoding in {"", "identity"}:
                compressed = body.startswith(b"\x1f\x8b")
            elif encoding == "gzip":
                compressed = True
            else:
                raise CatalogError("目录压缩格式不受支持")
    except CatalogError:
        raise
    except (TimeoutError, socket.timeout):
        raise CatalogError("目录请求超时") from None
    except urllib.error.HTTPError:
        raise CatalogError("目录服务暂不可用") from None
    except urllib.error.URLError:
        raise CatalogError("目录暂不可用") from None
    except OSError:
        raise CatalogError("目录暂不可用") from None
    except Exception:
        raise CatalogError("目录响应无效") from None
    return _read_json_bytes(body, compressed=compressed)


def _snapshot_from_cache(raw: object) -> CatalogSnapshot | None:
    if not isinstance(raw, Mapping):
        return None
    if (
        raw.get("version") != _CACHE_VERSION
        or raw.get("source") != CATALOG_URL
        or raw.get("license") != _CACHE_LICENSE
        or raw.get("attribution") != _CACHE_ATTRIBUTION
        or raw.get("license_notice") != _CACHE_LICENSE_NOTICE
    ):
        return None
    fetched_at = raw.get("fetched_at")
    raw_providers = raw.get("providers")
    if (
        isinstance(fetched_at, bool)
        or not isinstance(fetched_at, (int, float))
        or not isinstance(raw_providers, list)
        or not raw_providers
        or len(raw_providers) > MAX_PROVIDER_COUNT
    ):
        return None
    try:
        fetched_timestamp = float(fetched_at)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(fetched_timestamp) or fetched_timestamp < 0:
        return None
    providers: list[CatalogProvider] = []
    total_models = 0
    for item in raw_providers:
        if not isinstance(item, Mapping):
            return None
        provider_id = _safe_text(item.get("id"), 100)
        name = _safe_text(item.get("name"), 160)
        env_names_raw = item.get("env_names")
        models_raw = item.get("models")
        if (
            provider_id is None
            or name is None
            or not isinstance(env_names_raw, list)
            or not isinstance(models_raw, list)
            or len(models_raw) > MAX_MODELS_PER_PROVIDER
        ):
            return None
        env_names: list[str] = []
        for env_name in env_names_raw[:32]:
            safe_env = _safe_text(env_name, 80)
            if safe_env is None or not _ENV_NAME.fullmatch(safe_env):
                return None
            if safe_env not in env_names:
                env_names.append(safe_env)
        models: list[CatalogModel] = []
        for model in models_raw:
            if not isinstance(model, Mapping):
                return None
            model_id = _safe_text(model.get("id"), 120)
            model_name = _safe_text(model.get("name"), 200)
            family = model.get("family", "")
            protocol = model.get("protocol", "")
            base_url = model.get("base_url", "")
            if (
                model_id is None
                or model_name is None
                or not isinstance(family, str)
                or len(family) > 120
                or any(unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for char in family)
                or not isinstance(protocol, str)
                or protocol not in _PROTOCOLS | {""}
                or not isinstance(base_url, str)
                or (base_url and _safe_base_url(base_url) != base_url)
                or (not protocol and base_url)
            ):
                return None
            models.append(CatalogModel(model_id, model_name, family, protocol, base_url))
        total_models += len(models)
        if total_models > MAX_TOTAL_MODELS:
            return None
        providers.append(CatalogProvider(provider_id, name, tuple(env_names), tuple(models)))
    return CatalogSnapshot(tuple(providers), fetched_timestamp)


class CatalogStore:
    """Fetch and cache the normalized, public models.dev projection."""

    def __init__(self, cache_path: str | Path | None = None):
        self.cache_path = Path(cache_path) if cache_path is not None else _cache_path()

    def load_cached(self) -> CatalogSnapshot | None:
        try:
            if self.cache_path.stat().st_size > MAX_WIRE_BYTES:
                return None
            with self.cache_path.open("rb") as handle:
                data = handle.read(MAX_WIRE_BYTES + 1)
            if len(data) > MAX_WIRE_BYTES or not data.startswith(b"\x1f\x8b"):
                return None
            raw = _read_json_bytes(data, compressed=True)
            return _snapshot_from_cache(raw)
        except (OSError, CatalogError, ValueError):
            return None

    def refresh(self) -> CatalogSnapshot:
        raw = _fetch_payload()
        providers = _project_catalog(raw)
        snapshot = CatalogSnapshot(providers, time.time())
        self._write_cache(snapshot)
        return snapshot

    def _write_cache(self, snapshot: CatalogSnapshot) -> None:
        payload = {
            "version": _CACHE_VERSION,
            "source": CATALOG_URL,
            "license": _CACHE_LICENSE,
            "attribution": _CACHE_ATTRIBUTION,
            "license_notice": _CACHE_LICENSE_NOTICE,
            "fetched_at": snapshot.fetched_at,
            "providers": [
                {
                    "id": provider.id,
                    "name": provider.name,
                    "env_names": list(provider.env_names),
                    "models": [
                        {
                            "id": model.id,
                            "name": model.name,
                            "family": model.family,
                            "protocol": model.protocol,
                            "base_url": model.base_url,
                        }
                        for model in provider.models
                    ],
                }
                for provider in snapshot.providers
            ],
        }
        temporary: str | None = None
        descriptor: int | None = None
        try:
            decoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(decoded) > MAX_DECODED_BYTES:
                return
            compressed = gzip.compress(decoded, mtime=0)
            if len(compressed) > MAX_WIRE_BYTES:
                return
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=f".{self.cache_path.name}.", dir=self.cache_path.parent)
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(compressed)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.cache_path)
            temporary = None
            directory_fd = os.open(self.cache_path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # A valid fetched snapshot remains useful for this invocation even
            # when the optional cache cannot be written.
            return
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass


def _normalize_search_text(value: object, maximum: int = 512) -> str:
    try:
        text = str(value)[:maximum]
    except Exception:
        return ""
    return unicodedata.normalize("NFKC", text).casefold().strip()


def _search_tokens(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in value:
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current.clear()
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def _subsequence(needle: str, haystack: str) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    position = 0
    for char in needle:
        position = haystack.find(char, position)
        if position < 0:
            return False
        position += 1
    return True


def _record_value(item: object, key: str) -> object:
    if isinstance(item, Mapping):
        return item.get(key, "")
    try:
        return getattr(item, key, "")
    except Exception:
        return ""


class CatalogIndex:
    """Pre-index catalog IDs/names/families for bounded deterministic search."""

    def __init__(self, items: Iterable[object]):
        self.items = tuple(islice(items, MAX_INDEX_ITEMS))
        self._fields: tuple[tuple[tuple[str, ...], tuple[tuple[str, ...], ...], tuple[str, ...]], ...] = tuple(
            self._index_item(item) for item in self.items
        )

    @staticmethod
    def _index_item(item: object) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...], tuple[str, ...]]:
        values = tuple(_record_value(item, key) for key in ("id", "name", "family"))
        fields = tuple(_normalize_search_text(value)[:512] for value in values)
        tokens = tuple(_search_tokens(field) for field in fields)
        compact = tuple("".join(char for char in field if char.isalnum()) for field in fields)
        return fields, tokens, compact

    def search(self, query: str, limit: int = 100) -> tuple[object, ...]:
        if not isinstance(query, str):
            return ()
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            return ()
        result_limit = min(limit, MAX_RESULTS)
        normalized = _normalize_search_text(query, MAX_QUERY_LENGTH)[:MAX_QUERY_LENGTH]
        if not normalized:
            return self.items[:result_limit]
        query_tokens = _search_tokens(normalized)
        query_compact = "".join(char for char in normalized if char.isalnum())
        if not query_tokens or len(query_tokens) > MAX_QUERY_TOKENS or not query_compact:
            return ()

        def ranked() -> Iterable[tuple[tuple[object, ...], object]]:
            for index, item in enumerate(self.items):
                fields, tokens, compact = self._fields[index]
                rank: tuple[int, int] | None = None
                if any(field == normalized for field in fields if field):
                    rank = (0, 0)
                elif any(field.startswith(normalized) for field in fields if field):
                    rank = (1, 0)
                elif any(normalized in field for field in fields if field):
                    rank = (2, 0)
                elif any(field == query_compact for field in compact if field):
                    rank = (3, 0)
                elif any(field.startswith(query_compact) for field in compact if field):
                    rank = (4, 0)
                elif any(query_compact in field for field in compact if field):
                    rank = (5, 0)
                if rank is None:
                    categories: list[int] = []
                    for token in query_tokens:
                        category = 4
                        for field_tokens, field_compact in zip(tokens, compact):
                            if token in field_tokens:
                                category = min(category, 0)
                            elif any(value.startswith(token) for value in field_tokens):
                                category = min(category, 1)
                            elif any(token in value for value in field_tokens) or token in field_compact:
                                category = min(category, 2)
                            elif _subsequence(token, field_compact):
                                category = min(category, 3)
                        if category == 4:
                            break
                        categories.append(category)
                    if len(categories) == len(query_tokens):
                        rank = (6 + max(categories), sum(categories))
                    elif any(_subsequence(query_compact, value) for value in compact if value):
                        rank = (10, 0)
                if rank is not None:
                    fields, _, _ = self._fields[index]
                    tie = (fields[1], fields[0], fields[2], index)
                    yield ((rank[0], rank[1], *tie), item)

        return tuple(item for _, item in heapq.nsmallest(result_limit, ranked(), key=lambda pair: pair[0]))


def preset_fields(provider: CatalogProvider, model: CatalogModel) -> dict[str, str]:
    """Return only editable channel fields; callers keep new channels disabled."""

    protocol = model.protocol if model.protocol in _PROTOCOLS else ""
    return {
        "name": provider.name,
        "type": protocol,
        "base_url": _safe_base_url(model.base_url) if protocol else "",
        "model": model.id,
        "catalog_provider": provider.id if CATALOG_PROVIDER_ID.fullmatch(provider.id) else "",
    }
