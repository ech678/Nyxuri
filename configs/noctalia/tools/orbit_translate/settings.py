"""Validated, explicit configuration editing shared by the terminal interface."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time
import json
import math
import os
from pathlib import Path
import tempfile
import tomllib
from typing import cast

from .config import AppConfig, config_path, parse_config
from .credentials import make_secret_reference, store_key
from .providers import ProviderOutcome, translate_provider


class SettingsError(ValueError):
    """A local, safe editing or persistence error, without raw diagnostics."""


class SettingsDocument:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path).expanduser() if path is not None else config_path()
        try:
            self._baseline_bytes = self.path.read_bytes() if self.path.exists() else None
            self.data = tomllib.loads(self._baseline_bytes.decode("utf-8")) if self._baseline_bytes is not None else {"providers": []}
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise SettingsError("无法读取配置；原文件未改动") from exc
        parse_config(self.data)
        self.data.setdefault("providers", [])
        self._baseline_data = deepcopy(self.data)

    @property
    def providers(self) -> list[dict[str, object]]:
        return cast(list[dict[str, object]], self.data["providers"])

    @property
    def config(self) -> AppConfig:
        return parse_config(self.data)

    @property
    def dirty(self) -> bool:
        return self.data != self._baseline_data

    def _replace(self, candidate: dict[str, object]) -> None:
        parse_config(candidate)
        self.data = candidate

    def toggle(self, index: int) -> None:
        candidate = deepcopy(self.data)
        providers = cast(list[dict[str, object]], candidate["providers"])
        providers[index]["enabled"] = not bool(providers[index].get("enabled", False))
        self._replace(candidate)

    def put_provider(self, index: int | None, values: dict[str, object]) -> None:
        candidate = deepcopy(self.data)
        providers = cast(list[dict[str, object]], candidate["providers"])
        if index is None:
            providers.append(deepcopy(values))
        else:
            providers[index].update(deepcopy(values))
        self._replace(candidate)

    def delete_provider(self, index: int) -> None:
        candidate = deepcopy(self.data)
        cast(list[dict[str, object]], candidate["providers"]).pop(index)
        self._replace(candidate)

    def set_key(self, index: int, value: str) -> None:
        candidate = deepcopy(self.data)
        provider = cast(list[dict[str, object]], candidate["providers"])[index]
        reference = str(provider.get("api_key_secret") or make_secret_reference(str(provider["id"])))
        provider["api_key_secret"] = reference
        provider["api_key_env"] = ""
        parse_config(candidate)
        identity = (provider["id"], provider["type"], provider.get("base_url", ""))
        # Only the explicit key action writes a secret. Normal save never does.
        store_key(reference, value)
        # Keychain authorization can take time. Retain intervening toggles/name
        # edits, but never attach the key to a deleted or different endpoint.
        candidate = deepcopy(self.data)
        current = cast(list[dict[str, object]], candidate["providers"])
        matches = [item for item in current if (item["id"], item["type"], item.get("base_url", "")) == identity]
        if not matches:
            raise SettingsError("密钥已存入钥匙串，但渠道已变更；请重新选择渠道配置引用")
        matches[0]["api_key_secret"] = reference
        matches[0]["api_key_env"] = ""
        self._replace(candidate)

    def probe(
        self, index: int, text: str = "Hello world", source: str = "en", target: str = "zh-CN"
    ) -> ProviderOutcome:
        config = self.config
        if not isinstance(text, str) or not text.strip() or len(text) > config.max_chars:
            raise SettingsError("示例文本为空或超过字符限制")
        candidate = dict(self.data, source=source, target=target)
        parse_config(candidate)
        # An explicit probe may test a disabled provider, without enabling it.
        return translate_provider(config.providers[index], text.strip(), source, target, config.request_timeout_ms)

    def save(self) -> Path | None:
        parse_config(self.data)
        if not self.dirty:
            return None
        if self.path.is_symlink():
            raise SettingsError("配置是符号链接；请使用 --config 指定真实文件后保存")
        encoded = _dump_toml(self.data).encode("utf-8")
        if tomllib.loads(encoded.decode("utf-8")) != self.data:
            raise SettingsError("配置不能无损写回；原文件未改动")
        backup: Path | None = None
        temporary: Path | None = None
        try:
            self._check_unchanged()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self._baseline_bytes is not None:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                descriptor, filename = tempfile.mkstemp(prefix=f"{self.path.name}.backup-{stamp}-", dir=self.path.parent)
                backup = Path(filename)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(self._baseline_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
            descriptor, filename = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
            temporary = Path(filename)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            self._check_unchanged()
            os.replace(temporary, self.path)
            temporary = None
        except OSError as exc:
            raise SettingsError("无法安全保存配置；请检查文件权限") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self._baseline_bytes = encoded
        self._baseline_data = deepcopy(self.data)
        try:
            # fsync(file) does not persist the directory entry replaced above.
            descriptor = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise SettingsError("配置已替换，但目录同步失败；请保留备份并检查磁盘") from exc
        return backup

    def _check_unchanged(self) -> None:
        current = self.path.read_bytes() if self.path.exists() else None
        if current != self._baseline_bytes:
            raise SettingsError("配置已被其他程序修改；请退出并重新打开，避免覆盖")


def _toml_value(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        return repr(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return "{ " + ", ".join(f"{json.dumps(key, ensure_ascii=False)} = {_toml_value(item)}" for key, item in value.items()) + " }"
    raise SettingsError("配置包含不支持写回的值；原文件未改动")


def _dump_toml(data: dict[str, object]) -> str:
    lines = [f"{json.dumps(key, ensure_ascii=False)} = {_toml_value(value)}" for key, value in data.items() if key != "providers"]
    providers = cast(list[dict[str, object]], data.get("providers", []))
    if not providers:
        lines.append("providers = []")
    for provider in providers:
        lines.extend(("", "[[providers]]"))
        lines.extend(f"{json.dumps(key, ensure_ascii=False)} = {_toml_value(value)}" for key, value in provider.items())
    return "\n".join(lines) + "\n"
