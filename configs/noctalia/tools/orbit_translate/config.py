"""Configuration loading and validation for Orbit Translate."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tomllib
from urllib.parse import urlparse


AI_PROVIDER_TYPES = (
    "openai_compatible",
    "openai_responses",
    "anthropic",
    "gemini",
    "ollama",
)
SUPPORTED_PROVIDER_TYPES = frozenset(
    {
        "google",
        "libretranslate",
        "mymemory",
        "command",
        "deepl",
        "bing",
        "bing_dict",
        "cambridge_dict",
        "lingva",
        "yandex",
        "ecdict",
        "transmart",
        "tatoeba",
    }
    | set(AI_PROVIDER_TYPES)
)
ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
SECRET_REFERENCE = re.compile(r"^(?:kwallet|secret-service):[A-Za-z0-9._-]{1,128}$")
CATALOG_PROVIDER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class ConfigError(ValueError):
    """Raised when the user configuration cannot be used safely."""


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    name: str
    type: str
    enabled: bool
    base_url: str = ""
    model: str = ""
    api_key_env: str = ""
    api_key_secret: str = ""
    command: tuple[str, ...] = ()
    catalog_provider: str = ""


@dataclass(frozen=True)
class AppConfig:
    source: str = "auto"
    target: str = "zh-CN"
    capture_timeout_ms: int = 350
    request_timeout_ms: int = 6000
    max_chars: int = 8000
    max_parallel: int = 8
    dismiss_after_ms: int = 12000
    capture_primary: bool = True
    max_cards: int = 4
    show_source: bool = True
    auto_copy: bool = False
    providers: tuple[ProviderConfig, ...] = ()


def config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / "noctalia" / "tools" / "orbit-translate__custom__.toml"


def default_config() -> AppConfig:
    return AppConfig()


def load_config(path: str | Path | None = None) -> AppConfig:
    path_obj = Path(path) if path is not None else config_path()
    if not path_obj.exists():
        return default_config()
    try:
        with path_obj.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"配置文件格式错误: {path_obj.name}") from exc
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件: {path_obj.name}") from exc
    return parse_config(raw)


def parse_config(raw: dict[str, object]) -> AppConfig:
    if not isinstance(raw, dict):
        raise ConfigError("配置根节点必须是对象")
    providers_raw = raw.get("providers", [])
    if not isinstance(providers_raw, list):
        raise ConfigError("providers 必须是数组")

    providers: list[ProviderConfig] = []
    seen_ids: set[str] = set()
    for index, value in enumerate(providers_raw, start=1):
        if not isinstance(value, dict):
            raise ConfigError(f"第 {index} 个 Provider 必须是对象")
        provider = _parse_provider(value, index)
        if provider.id in seen_ids:
            raise ConfigError(f"Provider id 重复: {provider.id}")
        seen_ids.add(provider.id)
        providers.append(provider)

    return AppConfig(
        source=_text(raw, "source", "auto", 32),
        target=_text(raw, "target", "zh-CN", 32),
        capture_timeout_ms=_integer(raw, "capture_timeout_ms", 350, 100, 5000),
        request_timeout_ms=_integer(raw, "request_timeout_ms", 6000, 500, 120000),
        max_chars=_integer(raw, "max_chars", 8000, 1, 50000),
        max_parallel=_integer(raw, "max_parallel", 8, 1, 16),
        dismiss_after_ms=_integer(raw, "dismiss_after_ms", 12000, 1000, 120000),
        capture_primary=_boolean(raw, "capture_primary", True),
        max_cards=_integer(raw, "max_cards", 4, 1, 16),
        show_source=_boolean(raw, "show_source", True),
        auto_copy=_boolean(raw, "auto_copy", False),
        providers=tuple(providers),
    )


def _parse_provider(value: dict[str, object], index: int) -> ProviderConfig:
    provider_id = _text(value, "id", "", 64, allow_empty=True).strip()
    name = _text(value, "name", provider_id, 80).strip()
    provider_type = _text(value, "type", "", 40).strip()
    if not provider_id:
        raise ConfigError(f"第 {index} 个 Provider 缺少 id")
    if not provider_type:
        raise ConfigError(f"Provider {provider_id} 缺少 type")
    if provider_type not in SUPPORTED_PROVIDER_TYPES:
        supported = ", ".join(sorted(SUPPORTED_PROVIDER_TYPES))
        raise ConfigError(f"Provider {provider_id} 类型不支持，可用类型: {supported}")
    if "api_key" in value:
        raise ConfigError(f"Provider {provider_id} 不允许直接配置 api_key，请使用 api_key_env 或 api_key_secret")

    api_key_env = _text(value, "api_key_env", "", 80, allow_empty=True).strip()
    if api_key_env and not ENV_NAME.fullmatch(api_key_env):
        raise ConfigError(f"Provider {provider_id} 的 api_key_env 不是合法环境变量名")
    api_key_secret = _text(value, "api_key_secret", "", 160, allow_empty=True).strip()
    if api_key_secret and not SECRET_REFERENCE.fullmatch(api_key_secret):
        raise ConfigError(f"Provider {provider_id} 的 api_key_secret 引用无效")
    if api_key_env and api_key_secret:
        raise ConfigError(f"Provider {provider_id} 不能同时配置 api_key_env 和 api_key_secret")

    catalog_provider = _text(value, "catalog_provider", "", 80, allow_empty=True)
    if catalog_provider and not CATALOG_PROVIDER_ID.fullmatch(catalog_provider):
        raise ConfigError(f"Provider {provider_id} 的目录提供商 ID 无效")

    base_url = _text(value, "base_url", "", 500, allow_empty=True).strip()
    url_provider_types = {
        "google",
        "libretranslate",
        "mymemory",
        "deepl",
        "bing",
        "bing_dict",
        "cambridge_dict",
        "lingva",
        "yandex",
        "ecdict",
        "transmart",
        "tatoeba",
    } | set(AI_PROVIDER_TYPES)
    if provider_type in url_provider_types and base_url:
        try:
            parsed = urlparse(base_url)
        except ValueError as exc:
            if provider_type in AI_PROVIDER_TYPES:
                raise ConfigError(f"Provider {provider_id} 的 base_url 必须是有效的 http 或 https URL") from exc
            raise
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError(f"Provider {provider_id} 的 base_url 必须是 http 或 https URL")
        if provider_type in AI_PROVIDER_TYPES:
            try:
                hostname = parsed.hostname
                parsed.port
            except ValueError as exc:
                raise ConfigError(f"Provider {provider_id} 的 base_url 必须是有效的 http 或 https URL") from exc
            if not hostname:
                raise ConfigError(f"Provider {provider_id} 的 base_url 必须是有效的 http 或 https URL")
            if (
                parsed.username is not None
                or parsed.password is not None
                or "?" in base_url
                or "#" in base_url
            ):
                raise ConfigError(f"Provider {provider_id} 的 AI base_url 不能包含凭据、查询参数或片段")

    if provider_type in AI_PROVIDER_TYPES:
        if not base_url and provider_type != "ollama":
            raise ConfigError(f"Provider {provider_id} 缺少 base_url")
        model = _text(value, "model", "", 120).strip()
        if not model:
            raise ConfigError(f"Provider {provider_id} 缺少 model")
    elif provider_type == "libretranslate":
        if not base_url:
            raise ConfigError(f"Provider {provider_id} 缺少 base_url")
        model = ""
    else:
        model = ""

    command_raw = value.get("command", [])
    command: tuple[str, ...] = ()
    if provider_type == "command":
        if not isinstance(command_raw, list) or not command_raw or not all(
            isinstance(item, str) and item for item in command_raw
        ):
            raise ConfigError(f"Provider {provider_id} 的 command 必须是非空字符串数组")
        command = tuple(command_raw)
        if "{text}" not in command:
            raise ConfigError(f"Provider {provider_id} 的 command 必须包含 {{text}} 参数")

    return ProviderConfig(
        id=provider_id,
        name=name or provider_id,
        type=provider_type,
        enabled=_boolean(value, "enabled", False),
        base_url=base_url,
        model=model,
        api_key_env=api_key_env,
        api_key_secret=api_key_secret,
        command=command,
        catalog_provider=catalog_provider,
    )


def _text(
    section: dict[str, object],
    key: str,
    default: str,
    max_length: int,
    allow_empty: bool = False,
) -> str:
    value = section.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(f"{key} 必须是字符串")
    if (not allow_empty and not value) or len(value) > max_length:
        raise ConfigError(f"{key} 长度无效")
    return value


def _integer(section: dict[str, object], key: str, default: int, minimum: int, maximum: int) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ConfigError(f"{key} 必须是 {minimum} 到 {maximum} 之间的整数")
    return value


def _boolean(section: dict[str, object], key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} 必须是布尔值")
    return value
