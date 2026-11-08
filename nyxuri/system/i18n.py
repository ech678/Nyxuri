"""Bilingual i18n Engine: message lookup and text switching."""

import os
import tomllib
from pathlib import Path
from typing import Any, Dict

from nyxuri.system.env import CLI_CMD, Colors, PROJECT_NAME, STORAGE_NAME

_LOCALE_SOURCE: str = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG", "")
_CURRENT_LANG: str = "zh" if "zh" in _LOCALE_SOURCE.lower() else "en"


def get_lang() -> str:
    """Get currently selected language mode ('zh' or 'en')."""
    return _CURRENT_LANG


def set_lang(lang: str) -> None:
    """Set language mode ('zh' or 'en')."""
    global _CURRENT_LANG
    _CURRENT_LANG = "zh" if lang.startswith("zh") else "en"
    _MSG_CACHE.clear()


def text(zh: str, en: str) -> str:
    """Pick a one-off bilingual string by active language."""
    return zh if get_lang() == "zh" else en


def _load_translations() -> Dict[str, Dict[str, str]]:
    trans_file = Path(__file__).resolve().parent.parent / "translations.toml"
    if not trans_file.is_file():
        trans_file = Path(__file__).resolve().parent / "translations.toml"
    with trans_file.open("rb") as source:
        translations = tomllib.load(source)
    constants = {
        "PROJECT_NAME": PROJECT_NAME,
        "CLI_CMD": CLI_CMD,
        "STORAGE_NAME": STORAGE_NAME,
    }
    constants.update({
        f"Colors.{name}": value
        for name, value in vars(Colors).items()
        if name.isupper() and isinstance(value, str)
    })
    for entry in translations.values():
        for lang, template in entry.items():
            for name, value in constants.items():
                template = template.replace("{" + name + "}", value)
            entry[lang] = template
    return translations


TRANSLATIONS = _load_translations()
_MSG_CACHE: Dict[str, str] = {}


def msg(key: str, *args: Any) -> str:
    if not args:
        cached = _MSG_CACHE.get(key)
        if cached is not None:
            return cached
    lang = get_lang()
    entry = TRANSLATIONS.get(key)
    if not entry:
        result = key if not args else f"{key} ({', '.join(str(a) for a in args)})"
        if not args:
            _MSG_CACHE[key] = result
        return result
    template = entry.get(lang) or entry.get("en") or key
    if args:
        try:
            return template.format(*args)
        except Exception:
            return template
    _MSG_CACHE[key] = template
    return template
