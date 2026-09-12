"""Bilingual internationalization and translation engine with automatic fallbacks."""

import os
import tomllib
from pathlib import Path
from typing import Any, Dict

from nyxniri.constants import Colors, PROJECT_NAME

_CURRENT_LANG: str = "zh" if "zh" in os.environ.get("LANG", "").lower() or "zh" in os.environ.get("LC_ALL", "").lower() else "en"

def get_lang() -> str:
    """Get currently selected language mode ('zh' or 'en')."""
    return _CURRENT_LANG

def set_lang(lang: str) -> None:
    """Set language mode ('zh' or 'en')."""
    global _CURRENT_LANG
    _CURRENT_LANG = "zh" if lang.startswith("zh") else "en"
    _MSG_CACHE.clear()

def text(zh: str, en: str) -> str:
    """Pick a one-off bilingual string by active language.

    Escape hatch for diagnostic/status lines not worth a TRANSLATIONS entry
    (``msg()`` remains the default for keyed strings). Centralizes the per-module
    ``_text()`` copies that had spread across doctor/fcitx/greeter/gtktheme.
    """
    return zh if get_lang() == "zh" else en

def _load_translations() -> Dict[str, Dict[str, str]]:
    with Path(__file__).with_name("translations.toml").open("rb") as source:
        translations = tomllib.load(source)
    constants = {"PROJECT_NAME": PROJECT_NAME}
    constants.update({f"Colors.{name}": value for name, value in vars(Colors).items()
                      if name.isupper() and isinstance(value, str)})
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
