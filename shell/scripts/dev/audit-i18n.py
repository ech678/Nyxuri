#!/usr/bin/env python3
"""Audit the zh_CN language pack against every qsTr() key the shell references.

`llms-wiki/i18n.md` requires that no key referenced from code is missing from the
pack, and that every pack entry carries a translation. Nothing checked either
rule, so a ported component could ship English-only strings indefinitely. This
walks the QML tree, decodes the escapes a QML literal carries, and reports both
directions:

  * keys referenced from code but absent from the pack  -> the pack is incomplete
  * pack entries no code references                     -> informational only

Only literal first arguments are collectable, so a key built at runtime cannot be
audited statically; those are out of scope rather than silently passed.
"""

from __future__ import annotations

import io
import os
import re
import sys
import tomllib

SHELL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PACK_PATH = os.path.join(SHELL_ROOT, "assets", "i18n", "zh_CN.toml")

# Two call styles coexist: I18n.tr()/I18n.t() is what the tree uses since the
# pure QML/JS runtime replaced QTranslator (R4-C-04), and qsTr() survives in a
# few places even though nothing installs a translator any more. Both are
# audited, otherwise the majority of keys would look unreferenced.
I18N_TR_RE = re.compile(r'I18n\.t(?:r)?\(\s*"((?:[^"\\]|\\.)*)"')
QS_TR_RE = re.compile(r'qsTr\(\s*"((?:[^"\\]|\\.)*)"')
QS_TRANSLATE_RE = re.compile(r'qsTranslate\(\s*"(?:[^"\\]|\\.)*"\s*,\s*"((?:[^"\\]|\\.)*)"')

SKIP_DIRS = {"build", ".git", "__pycache__", "references"}

# A QML string literal stores \n as two characters; the pack stores the real
# newline. Comparing the raw literal against the parsed TOML therefore reports
# every multi-line key as missing. Decode first.
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "'": "'"}


def decode_qml_literal(text: str) -> str:
    out = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] in _ESCAPES:
            out.append(_ESCAPES[text[index + 1]])
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def iter_qml_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in filenames:
            if filename.endswith(".qml"):
                yield os.path.join(dirpath, filename)


def collect_references(root: str):
    """Map relative path -> list of decoded keys found in that file."""
    references = {}
    for path in iter_qml_files(root):
        try:
            text = io.open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as error:
            print("warn: unreadable {}: {}".format(path, error), file=sys.stderr)
            continue
        raw_keys = (I18N_TR_RE.findall(text) + QS_TR_RE.findall(text) + QS_TRANSLATE_RE.findall(text))
        if raw_keys:
            references[os.path.relpath(path, root)] = [decode_qml_literal(key) for key in raw_keys]
    return references


def main() -> int:
    try:
        pack = tomllib.load(open(PACK_PATH, "rb"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        print("error: cannot read {}: {}".format(PACK_PATH, error), file=sys.stderr)
        return 2

    known = set(pack.keys())
    references = collect_references(SHELL_ROOT)

    all_keys = sorted({key for keys in references.values() for key in keys})
    missing = [key for key in all_keys if key not in known]
    orphans = sorted(key for key in known if key not in set(all_keys))

    print("qml files scanned   : {}".format(len(list(iter_qml_files(SHELL_ROOT)))))
    print("distinct qsTr keys  : {}".format(len(all_keys)))
    print("pack entries        : {}".format(len(known)))
    print("missing (code->pack): {}".format(len(missing)))
    print("unreferenced (pack) : {}".format(len(orphans)))

    if missing:
        # Grouped by file: the report has to be actionable, not a flat list.
        print()
        for path in sorted(references):
            hits = sorted({key for key in references[path] if key in set(missing)})
            if not hits:
                continue
            print("{}:".format(path))
            for key in hits:
                print("    {}".format(key))
        print()
        print("audit-i18n: FAILED")
        return 1

    print("audit-i18n: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
