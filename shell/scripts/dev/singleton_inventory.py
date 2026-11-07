#!/usr/bin/env python3
"""Build a deterministic, source-only QML singleton/consumer inventory.

This is a lexical inventory, not a QML evaluator.  It records singleton
declarations, imports, static references, and resource names touched from
``Component.onCompleted`` handlers.  In particular, ``runtime_claims`` is
always false: a declaration is not evidence that a QML object was created.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


SIDE_EFFECT_KINDS: Final[tuple[str, ...]] = ("Timer", "Process", "FileView", "Socket", "Loader")
IMPORT_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*import\s+([^\s;]+)(?:\s+[0-9]+(?:\.[0-9]+)?)?(?:\s+as\s+([A-Za-z_]\w*))?"
)
PRAGMA_RE: Final[re.Pattern[str]] = re.compile(r"^\s*pragma\s+Singleton\b")
OBJECT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?m)(?:^|[{;\n])[ \t]*(?:component\s+[A-Za-z_]\w*\s*:\s*)?"
    r"(Timer|Process|FileView|Socket|Loader)\s*\{"
)
HANDLER_RE: Final[re.Pattern[str]] = re.compile(r"Component\.onCompleted\s*:")
QMLDIR_RE: Final[re.Pattern[str]] = re.compile(r"^\s*singleton\s+([A-Za-z_]\w*)\s+([^\s#]+)")


@dataclass(frozen=True, slots=True)
class SourceFile:
    path: Path
    relative: str
    text: str
    imports: tuple[dict[str, object], ...]


def _strip_comments(text: str) -> str:
    """Blank comments without changing line positions or string contents."""
    result: list[str] = []
    i = 0
    quote: str | None = None
    while i < len(text):
        char = text[i]
        if quote:
            result.append(char)
            if char == "\\" and i + 1 < len(text):
                i += 1
                result.append(text[i])
            elif char == quote:
                quote = None
            i += 1
            continue
        if char in "'\"`":
            quote = char
            result.append(char)
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            result.extend(" " for _ in range(end - i))
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = len(text) if end < 0 else end + 2
            result.extend("\n" if c == "\n" else " " for c in text[i:end])
            i = end
        else:
            result.append(char)
            i += 1
    return "".join(result)


def _matching_brace(text: str, opening: int) -> int:
    depth = 0
    quote: str | None = None
    i = opening
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == quote:
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _line(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _imports(text: str) -> tuple[dict[str, object], ...]:
    found: list[dict[str, object]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        match = IMPORT_RE.match(raw)
        if not match:
            continue
        row: dict[str, object] = {"module": match.group(1), "line": number}
        if match.group(2):
            row["alias"] = match.group(2)
        found.append(row)
    return tuple(found)


def _qml_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.qml") if path.is_file())


def _source_files(root: Path) -> list[SourceFile]:
    sources: list[SourceFile] = []
    for path in _qml_files(root):
        try:
            text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        sources.append(SourceFile(path, path.relative_to(root).as_posix(), text, _imports(text)))
    return sources


def _qmldir_aliases(root: Path) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for path in sorted(root.rglob("qmldir")):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for raw in lines:
            match = QMLDIR_RE.match(raw)
            if match:
                target = (path.parent / match.group(2)).resolve()
                try:
                    aliases[match.group(1)] = target.relative_to(root.resolve()).as_posix()
                except ValueError:
                    continue
    return aliases


def _object_ids(text: str) -> list[tuple[str, str, int]]:
    objects: list[tuple[str, str, int]] = []
    for match in OBJECT_RE.finditer(text):
        closing = _matching_brace(text, match.end() - 1)
        body = text[match.end():closing] if closing >= 0 else text[match.end():]
        id_match = re.search(r"(?m)^\s*id\s*:\s*([A-Za-z_]\w*)\b", body)
        if id_match:
            objects.append((id_match.group(1), match.group(1), _line(text, match.start(1))))
    return objects


def _handler_bodies(text: str) -> list[tuple[int, str]]:
    handlers: list[tuple[int, str]] = []
    for match in HANDLER_RE.finditer(text):
        cursor = match.end()
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor < len(text) and text[cursor] == "{":
            closing = _matching_brace(text, cursor)
            body = text[cursor + 1:closing] if closing >= 0 else text[cursor + 1:]
        else:
            end = text.find("\n", cursor)
            end = len(text) if end < 0 else end
            body = text[cursor:end]
        handlers.append((_line(text, match.start()), body))
    return handlers


def _side_effects(text: str) -> list[dict[str, object]]:
    objects = _object_ids(text)
    effects: list[dict[str, object]] = []
    for handler_line, body in _handler_bodies(text):
        for identifier, kind, _ in objects:
            for match in re.finditer(rf"\b{re.escape(identifier)}\b", body):
                # A resource id is evidence of a handler reference.  Keep the
                # first operation token when one exists for useful review.
                suffix = body[match.end():match.end() + 80]
                operation = None
                op_match = re.match(r"\s*\.\s*([A-Za-z_]\w*)", suffix)
                if op_match:
                    operation = op_match.group(1)
                row: dict[str, object] = {"kind": kind, "identifier": identifier, "line": handler_line}
                if operation:
                    row["operation"] = operation
                effects.append(row)
        for kind in SIDE_EFFECT_KINDS:
            if re.search(rf"\b{kind}\s*\{{", body):
                effects.append({"kind": kind, "line": handler_line, "source": "declaration"})
    effects.sort(key=lambda row: (int(str(row["line"])), str(row["kind"]), str(row.get("identifier", "")), str(row.get("operation", ""))))
    unique: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for row in effects:
        key = tuple(sorted(row.items()))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def inventory(root: Path) -> dict[str, object]:
    """Return a stable source inventory rooted at ``root``."""
    root = root.resolve()
    sources = _source_files(root)
    aliases = _qmldir_aliases(root)
    singleton_rows: list[dict[str, object]] = []
    singleton_names: dict[str, str] = {}
    for source in sources:
        if not any(PRAGMA_RE.match(line) for line in source.text.splitlines()):
            continue
        name = Path(source.relative).stem
        singleton_names[name] = source.relative
        singleton_rows.append({
            "name": name,
            "file": source.relative,
            "line": next(i for i, line in enumerate(source.text.splitlines(), 1) if PRAGMA_RE.match(line)),
            "imports": list(source.imports),
            "consumers": [],
            "side_effects": _side_effects(source.text),
        })
    for name, relative in aliases.items():
        singleton_names.setdefault(name, relative)
    for row in singleton_rows:
        name = str(row["name"])
        declaration_file = str(row["file"])
        consumers: list[dict[str, object]] = []
        token = re.compile(rf"\b{re.escape(name)}\b")
        for source in sources:
            if source.relative == declaration_file:
                continue
            for match in token.finditer(source.text):
                consumers.append({"file": source.relative, "line": _line(source.text, match.start()), "reference": name})
        row["consumers"] = consumers
    singleton_rows.sort(key=lambda row: (str(row["file"]), int(str(row["line"])), str(row["name"])))
    return {
        "schema": 1,
        "evidence": "static-source",
        "runtime_claims": False,
        "root": "qml-source",
        "source_files": len(sources),
        "singleton_count": len(singleton_rows),
        "qmldir_aliases": [{"name": name, "file": aliases[name]} for name in sorted(aliases)],
        "singletons": singleton_rows,
    }


def markdown(document: dict[str, object]) -> str:
    lines = [
        "# Nyxuri Shell QML Singleton Inventory", "",
        "> Static source inventory only; it does not claim runtime instantiation or liveness.", "",
        f"Source files: **{document.get('source_files', 0)}**  ",
        f"Singletons: **{document.get('singleton_count', 0)}**  ",
        f"Runtime claims: **{str(document.get('runtime_claims', False)).lower()}**", "",
        "## Singletons", "",
        "| Name | File | Line | Imports | Consumers | onCompleted side effects |",
        "|---|---|---:|---:|---:|---:|",
    ]
    singleton_rows = document.get("singletons", [])
    for row in singleton_rows if isinstance(singleton_rows, list) else []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| `{row.get('name', '-')}` | `{row.get('file', '-')}` | {row.get('line', '-')} | "
            f"{len(row.get('imports', [])) if isinstance(row.get('imports', []), list) else 0} | "
            f"{len(row.get('consumers', [])) if isinstance(row.get('consumers', []), list) else 0} | "
            f"{len(row.get('side_effects', [])) if isinstance(row.get('side_effects', []), list) else 0} |"
        )
    lines.extend(["", "## Consumer references", "", "| Singleton | Consumer file | Line | Reference |", "|---|---|---:|---|"])
    for row in singleton_rows if isinstance(singleton_rows, list) else []:
        if not isinstance(row, dict):
            continue
        consumers = row.get("consumers", [])
        for consumer in consumers if isinstance(consumers, list) else []:
            if isinstance(consumer, dict):
                lines.append(f"| `{row.get('name', '-')}` | `{consumer.get('file', '-')}` | {consumer.get('line', '-')} | `{consumer.get('reference', '-')}` |")
    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("--root", dest="root_option", type=Path)
    parser.add_argument("--format", choices=("json", "markdown", "both"), default="json")
    parser.add_argument("--output", type=Path, default=Path("-"))
    args = parser.parse_args(argv)
    root = args.root_option or args.root
    if root is None:
        parser.error("a QML root is required")
    document = inventory(root)
    encoded = json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    rendered = markdown(document)
    if args.format == "json":
        if str(args.output) == "-":
            sys.stdout.write(encoded)
        else:
            _write(args.output, encoded)
    elif args.format == "markdown":
        if str(args.output) == "-":
            sys.stdout.write(rendered)
        else:
            _write(args.output, rendered)
    elif str(args.output) == "-":
        sys.stdout.write(encoded + "\n" + rendered)
    elif args.output.suffix:
        _write(args.output.with_suffix(".json"), encoded)
        _write(args.output.with_suffix(".md"), rendered)
    else:
        _write(args.output / "singleton-inventory.json", encoded)
        _write(args.output / "singleton-inventory.md", rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
