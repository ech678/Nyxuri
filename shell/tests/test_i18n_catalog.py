#!/usr/bin/env python3
"""Shell i18n dictionary integrity gates.

Replaces the unwired dev/audit-i18n.py script with enforced contracts:

  1. No dead global keys — every top-level zh_CN.toml key must appear in the
     source corpus (QML/JS/PY/JSON/SH under shell/ plus engine/tests). Keys
     produced dynamically (card names, unit labels) live in catalog files the
     corpus already contains, so substring matching stays sound.
  2. No dead sections — a [Section] must either have a backing file in the
     tree or its name must be referenced somewhere (dynamic context use).
  3. Every literal I18n.tr/qsTr call resolves — the key exists globally or in
     the call's context section (Translations.js lookup order), so no ported
     component can ship English-only strings indefinitely.

Root cause history: 164 dead keys from sealed domains (cloud backup, weather
map, awww, lyrics) accumulated silently because nothing checked either
direction.
"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL_DIR = REPO_ROOT / "shell"
ZH_PATH = SHELL_DIR / "app" / "i18n" / "zh_CN.toml"

_CORPUS_DIRS = (
    SHELL_DIR / "app",
    SHELL_DIR / "units",
    SHELL_DIR / "shared",
    SHELL_DIR / "scripts",
    SHELL_DIR / "tests",
    SHELL_DIR / "archive",
    REPO_ROOT / "tests",
    REPO_ROOT / "nyxuri",
)
_CORPUS_SUFFIXES = (".qml", ".js", ".py", ".json", ".sh")

_CALL_RE = re.compile(
    r'(?:I18n|Trans)\.(?:tr|t)\(\s*"((?:[^"\\]|\\.)*)"(?:\s*,\s*"((?:[^"\\]|\\.)*)")?'
    r'|\bqsTr(?:late)?\(\s*"((?:[^"\\]|\\.)*)"(?:\s*,\s*"((?:[^"\\]|\\.)*)")?'
)
_KEY_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"')

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "'": "'"}


def _decode(raw: str) -> str:
    out, i = [], 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            out.append(_ESCAPES.get(raw[i + 1], raw[i + 1]))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _corpus() -> str:
    chunks = []
    for directory in _CORPUS_DIRS:
        for suffix in _CORPUS_SUFFIXES:
            for path in directory.rglob(f"*{suffix}"):
                if "__pycache__" in path.parts or "references" in path.parts:
                    continue
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def _type_stems() -> set:
    stems = set()
    for sub in ("app", "units", "shared", "archive"):
        for suffix in (".qml", ".js"):
            for path in (SHELL_DIR / sub).rglob(f"*{suffix}"):
                if "__pycache__" not in path.parts:
                    stems.add(path.stem)
    return stems


class I18nCatalogIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(ZH_PATH, "rb") as f:
            cls.data = tomllib.load(f)
        cls.globals = {k: v for k, v in cls.data.items() if not isinstance(v, dict)}
        cls.sections = {k: v for k, v in cls.data.items() if isinstance(v, dict)}
        cls.corpus = _corpus()
        cls.stems = _type_stems()

    def test_no_dead_global_keys(self):
        # Match BOTH the decoded key and its escaped literal form: a QML call
        # site carries "a\nb" as backslash-n, so searching only the decoded
        # text once misjudged 18 live keys as dead and purged them.
        def alive(key: str) -> bool:
            if key in self.corpus:
                return True
            escaped = key.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
            return escaped in self.corpus

        dead = sorted(k for k in self.globals if not alive(k))
        self.assertEqual(dead, [], "zh_CN.toml global keys with zero consumers (sealed-domain residue)")

    def test_no_dead_sections(self):
        dead = []
        for name in sorted(self.sections):
            has_file = name in self.stems
            referenced = re.search(r"\b" + re.escape(name) + r"\b", self.corpus) is not None
            if not has_file and not referenced:
                dead.append(name)
        self.assertEqual(dead, [], "zh_CN.toml sections whose component is gone and name is unreferenced")

    def test_literal_calls_resolve(self):
        missing = []
        for match in _CALL_RE.finditer(self.corpus):
            key_raw = match.group(1) or match.group(3)
            ctx_raw = match.group(2) or match.group(4)
            key = _decode(key_raw)
            if not key:
                continue
            ctx = _decode(ctx_raw) if ctx_raw else ""
            in_ctx = ctx in self.sections and key in self.sections[ctx]
            if not in_ctx and key not in self.globals:
                missing.append(f"{key!r}" + (f" (ctx {ctx!r})" if ctx else ""))
        self.assertEqual(missing, [], "Literal I18n.tr/qsTr keys with no dictionary entry "
                                      "(component would render English forever)")


if __name__ == "__main__":
    unittest.main()
