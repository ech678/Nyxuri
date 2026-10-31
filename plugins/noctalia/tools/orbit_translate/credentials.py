"""Native system-keyring access for provider API keys."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import unicodedata

from .config import ENV_NAME, SECRET_REFERENCE, ProviderConfig


class CredentialError(Exception):
    """Safe, user-facing keyring failure with no command output or secret data."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_KWALLET_NAME = "kdewallet"
_KWALLET_FOLDER = "Orbit Translate"
_SECRET_LABEL = "Orbit Translate provider key"
_STORE_TIMEOUT_SECONDS = 45
_LOOKUP_TIMEOUT_SECONDS = 8


def make_secret_reference(provider_id: str) -> str:
    """Choose the installed native backend and return a non-secret reference."""
    backend = "kwallet" if shutil.which("kwallet-query") else "secret-service" if shutil.which("secret-tool") else ""
    if not backend:
        raise CredentialError("未找到可用的系统钥匙串命令")
    safe_id = _reference_id(provider_id)
    return f"{backend}:{safe_id}"


def store_key(reference: str, value: str) -> None:
    """Store a key after an explicit caller action; never put it in argv."""
    backend, safe_id = _parse_reference(reference)
    _validate_key(value)
    command, stdin_value = _store_command(backend, safe_id, value)
    _run(command, stdin_value, _STORE_TIMEOUT_SECONDS, "无法写入系统钥匙串")


def resolve_key(provider: ProviderConfig) -> str:
    """Resolve configured environment/keyring credentials, or return empty."""
    api_key_env = getattr(provider, "api_key_env", "") or ""
    api_key_secret = getattr(provider, "api_key_secret", "") or ""
    if api_key_env and api_key_secret:
        raise CredentialError("Provider 不能同时配置环境变量和钥匙串凭据")
    if api_key_env:
        if not ENV_NAME.fullmatch(api_key_env):
            raise CredentialError("API Key 环境变量名无效")
        value = os.environ.get(api_key_env, "")
        if not value:
            raise CredentialError("未配置的 API Key 环境变量")
        _validate_key(value)
        return value
    if not api_key_secret:
        return ""

    backend, safe_id = _parse_reference(api_key_secret)
    command = _lookup_command(backend, safe_id)
    result = _run(command, None, _LOOKUP_TIMEOUT_SECONDS, "系统钥匙串中的凭据缺失、锁定或不可用")
    value = result.stdout.rstrip("\r\n")
    if not value:
        raise CredentialError("系统钥匙串中的凭据缺失、锁定或不可用")
    _validate_key(value)
    return value


def _reference_id(provider_id: str) -> str:
    if not isinstance(provider_id, str) or not provider_id:
        raise CredentialError("Provider 标识无效")
    if _SAFE_ID.fullmatch(provider_id):
        return provider_id
    return hashlib.sha256(provider_id.encode("utf-8")).hexdigest()


def _parse_reference(reference: str) -> tuple[str, str]:
    if not isinstance(reference, str) or not SECRET_REFERENCE.fullmatch(reference):
        raise CredentialError("钥匙串引用无效")
    backend, safe_id = reference.split(":", 1)
    return backend, safe_id


def _validate_key(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise CredentialError("API Key 不能为空")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise CredentialError("API Key 不能包含控制字符")


def _store_command(backend: str, safe_id: str, value: str) -> tuple[list[str], str]:
    if backend == "kwallet":
        # KDE documents kdewallet as the default wallet; kwallet-query creates
        # the app folder only on this explicit write operation.
        return (
            [
                "kwallet-query",
                "--write-password",
                safe_id,
                "--folder",
                _KWALLET_FOLDER,
                _KWALLET_NAME,
            ],
            value,
        )
    return (
        [
            "secret-tool",
            "store",
            f"--label={_SECRET_LABEL}",
            "application",
            "orbit-translate",
            "provider",
            safe_id,
        ],
        value,
    )


def _lookup_command(backend: str, safe_id: str) -> list[str]:
    if backend == "kwallet":
        return [
            "kwallet-query",
            "--read-password",
            safe_id,
            "--folder",
            _KWALLET_FOLDER,
            _KWALLET_NAME,
        ]
    return [
        "secret-tool",
        "lookup",
        "application",
        "orbit-translate",
        "provider",
        safe_id,
    ]


def _run(command: list[str], stdin_value: str | None, timeout: int, failure: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            input=stdin_value,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise CredentialError(failure) from None
    if result.returncode != 0:
        raise CredentialError(failure)
    return result
