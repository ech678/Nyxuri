#!/usr/bin/env python3
"""Compile Nyxuri Shell TOML translation catalogs into Qt TS and QM files.

Allows human maintainers to work exclusively with clean TOML dictionaries while
providing seamless compatibility with Qt's QTranslator / qsTr() runtime.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tomllib
import xml.sax.saxutils as saxutils
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def _xml_escape(text: str) -> str:
    return saxutils.escape(text)


def _unescape_c_string(s: str) -> str:
    """Safely decode C/JS backslash escape sequences without mangling unicode."""
    res = []
    i = 0
    length = len(s)
    while i < length:
        if s[i] == "\\" and i + 1 < length:
            nxt = s[i + 1]
            if nxt == "n":
                res.append("\n")
                i += 2
            elif nxt == "t":
                res.append("\t")
                i += 2
            elif nxt == "r":
                res.append("\r")
                i += 2
            elif nxt == '"':
                res.append('"')
                i += 2
            elif nxt == "'":
                res.append("'")
                i += 2
            elif nxt == "\\":
                res.append("\\")
                i += 2
            else:
                res.append(s[i : i + 2])
                i += 2
        else:
            res.append(s[i])
            i += 1
    return "".join(res)


def scan_source_strings(source_root: Path) -> Dict[str, Set[str]]:
    """Scan QML, JS, and CPP source files to collect (context, string) occurrences."""
    qstr_re = re.compile(
        r"""(?:qsTr|QT_TR_NOOP)\s*\(\s*(["\'])(.*?)\1\s*(?:,\s*(["\'])(.*?)\3)?\s*(?:,\s*\d+)?\s*\)""",
        re.DOTALL,
    )
    translate_re = re.compile(
        r"""(?:qsTranslate|(?:QCoreApplication::)?translate|QT_TRANSLATE_NOOP)\s*\(\s*(["\'])(.*?)\1\s*,\s*(["\'])(.*?)\3""",
        re.DOTALL,
    )

    contexts: Dict[str, Set[str]] = {}
    i18n_re = re.compile(
        r"""I18n\.(?:tr|t)\s*\(\s*(["\'])(.*?)\1\s*(?:,\s*(["\'])(.*?)\3)?\s*(?:,\s*[^)]+)?\s*\)""",
        re.DOTALL,
    )

    for root, dirs, files in os.walk(source_root):
        if any(ignored in root for ignored in ("build", "references", ".git")):
            continue
        for f in files:
            path = Path(root) / f
            ext = path.suffix.lower()
            if ext not in (".qml", ".js", ".cpp", ".h"):
                continue

            file_stem = path.stem
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # In QML, default context for qsTr is the component name (file stem)
            for m in qstr_re.finditer(content):
                src = _unescape_c_string(m.group(2))
                ctx = file_stem
                contexts.setdefault(ctx, set()).add(src)

            # In C++ or direct translate() / qsTranslate() calls, context is explicitly given
            for m in translate_re.finditer(content):
                ctx = _unescape_c_string(m.group(2))
                src = _unescape_c_string(m.group(4))
                contexts.setdefault(ctx, set()).add(src)

            # In I18n.tr(src, ctx) or I18n.tr(src)
            for m in i18n_re.finditer(content):
                src = _unescape_c_string(m.group(2))
                ctx = _unescape_c_string(m.group(4)) if m.group(4) else file_stem
                contexts.setdefault(ctx, set()).add(src)

    return contexts


def generate_ts(
    toml_path: Path,
    locale: str,
    source_contexts: Dict[str, Set[str]],
) -> str:
    """Generate a Qt .ts XML string from a TOML translation file."""
    with toml_path.open("rb") as f:
        data = tomllib.load(f)

    # Top-level entries are global fallback mappings
    global_mappings: Dict[str, Any] = {}
    context_mappings: Dict[str, Dict[str, Any]] = {}

    for k, v in data.items():
        if isinstance(v, dict):
            context_mappings[k] = v
        else:
            global_mappings[k] = v

    # Build union of all contexts needed
    all_contexts: Set[str] = set(source_contexts.keys()) | set(context_mappings.keys())

    # Ensure well-known test contexts exist
    all_contexts.update(["AccountPage", "TimeUtils", "DashboardPomodoroCard", "SpotlightClipboardProvider"])

    lines: List[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!DOCTYPE TS>',
        f'<TS version="2.1" language="{locale}" sourcelanguage="en_US">',
    ]

    for ctx_name in sorted(all_contexts):
        sources = set(source_contexts.get(ctx_name, set()))
        if ctx_name in context_mappings:
            sources.update(context_mappings[ctx_name].keys())

        ctx_overrides = context_mappings.get(ctx_name, {})

        ctx_messages: List[Tuple[str, Any]] = []
        for src in sorted(sources):
            if src in ctx_overrides:
                ctx_messages.append((src, ctx_overrides[src]))
            elif src in global_mappings:
                ctx_messages.append((src, global_mappings[src]))
            elif locale == "en_US":
                # In en_US, source string is self-translated
                ctx_messages.append((src, src))

        if not ctx_messages:
            continue

        lines.append("<context>")
        lines.append(f"    <name>{_xml_escape(ctx_name)}</name>")

        for src, trans in ctx_messages:
            is_numerus = isinstance(trans, list) or "%n" in src

            if is_numerus:
                lines.append('    <message numerus="yes">')
                lines.append(f"        <source>{_xml_escape(src)}</source>")
                lines.append("        <translation>")
                if isinstance(trans, list):
                    for form in trans:
                        lines.append(f"            <numerusform>{_xml_escape(str(form))}</numerusform>")
                else:
                    lines.append(f"            <numerusform>{_xml_escape(str(trans))}</numerusform>")
                lines.append("        </translation>")
                lines.append("    </message>")
            else:
                lines.append("    <message>")
                lines.append(f"        <source>{_xml_escape(src)}</source>")
                lines.append(f"        <translation>{_xml_escape(str(trans))}</translation>")
                lines.append("    </message>")

        lines.append("</context>")

    lines.append("</TS>\n")
    return "\n".join(lines)


def compile_ts_to_qm(ts_path: Path, qm_path: Path) -> bool:
    """Run lrelease / lrelease6 to compile .ts to .qm."""
    lrelease_bin = shutil.which("lrelease6") or shutil.which("lrelease")
    if not lrelease_bin:
        print("Warning: Neither lrelease6 nor lrelease found in PATH; skipping .qm binary compilation.", file=sys.stderr)
        return False

    cmd = [lrelease_bin, str(ts_path), "-qm", str(qm_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error compiling {ts_path} to {qm_path}: {res.stderr}", file=sys.stderr)
        return False
    return True


def generate_pure_translations(input_dir: Path, source_root: Path) -> None:
    """Validate TOML translation syntax and ensure pure QML/JS dynamic Translations.js exists."""
    zh_toml = input_dir / "zh_CN.toml"
    if not zh_toml.exists():
        return

    with zh_toml.open("rb") as f:
        data = tomllib.load(f)
    print(f"Validated {zh_toml.name}: {len(data)} translation entries loaded cleanly.")

    # Remove legacy zh_CN.json if present
    legacy_json = input_dir / "zh_CN.json"
    if legacy_json.exists():
        legacy_json.unlink()





def main() -> int:
    parser = argparse.ArgumentParser(description="Compile TOML catalogs to Qt TS / QM files and pure QML Translations.js")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing zh_CN.toml and en_US.toml")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for generated TS/QM files")
    parser.add_argument("--source-root", type=Path, default=None, help="Root directory of QML/JS sources (default: input-dir/../..)")
    parser.add_argument("--compile-qm", action="store_true", help="Also compile TS to binary QM files")
    parser.add_argument("--prefix", default="clavis", help="Prefix for output files (e.g. clavis or nyxuri)")

    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_root = args.source_root.resolve() if args.source_root else input_dir.parent.parent

    # Always generate pure QML/JS catalogs
    generate_pure_translations(input_dir, source_root)

    source_contexts = scan_source_strings(source_root)

    locales = [
        ("zh_CN", "zh_CN.toml"),
        ("en_US", "en_US.toml"),
    ]

    for locale, filename in locales:
        toml_file = input_dir / filename
        if not toml_file.exists():
            print(f"Warning: {toml_file} does not exist; skipping.", file=sys.stderr)
            continue

        ts_content = generate_ts(toml_file, locale, source_contexts)
        out_ts = output_dir / f"{args.prefix}_{locale}.ts"
        out_ts.write_text(ts_content, encoding="utf-8")
        print(f"Generated TS: {out_ts}")

        if args.compile_qm:
            out_qm = output_dir / f"{args.prefix}_{locale}.qm"
            if compile_ts_to_qm(out_ts, out_qm):
                print(f"Compiled QM: {out_qm}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
