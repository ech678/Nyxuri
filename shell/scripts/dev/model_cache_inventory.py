#!/usr/bin/env python3
"""Inventory QML model, image, and cache-related declarations.

This is deliberately a source audit.  It reports declarations and property
expressions found in QML files; it does not instantiate QML or infer the
runtime size, liveness, or eviction behaviour of a model or image cache.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Final


MODEL_TYPES: Final[tuple[str, ...]] = ("ListModel", "FolderListModel")
VIEW_TYPES: Final[tuple[str, ...]] = ("Repeater", "ListView", "GridView")
IMAGE_TYPES: Final[tuple[str, ...]] = ("Image", "IconImage", "AnimatedImage")
CANVAS_TYPES: Final[tuple[str, ...]] = ("Canvas",)
DECLARATION_TYPES: Final[tuple[str, ...]] = MODEL_TYPES + VIEW_TYPES + IMAGE_TYPES + CANVAS_TYPES

DECLARATION_RE: Final[re.Pattern[str]] = re.compile(
    r"(?m)(?:^|[{;\n])[ \t]*(?:component\s+[A-Za-z_]\w*\s*:\s*|"
    r"property\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?\s+[A-Za-z_]\w*\s*:\s*)?"
    r"(?P<kind>ListModel|FolderListModel|Repeater|ListView|GridView|"
    r"Image|IconImage|AnimatedImage|Canvas)\s*\{")
PROPERTY_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:(?:readonly\s+)?property\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?\s+)?"
    r"(?P<name>[A-Za-z_]\w*(?:\.[A-Za-z_]\w+)?)\s*:\s*(?P<value>.*?)\s*;?\s*$"
)
LAYER_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<name>layer\.(?:enabled|smooth|mipmap|effect|samples|sourceRect|textureSize))"
    r"\s*:\s*(?P<value>.*?)\s*;?\s*$"
)
SIGNAL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?P<name>(?:[A-Za-z_]*(?:max(?:imum)?|limit|capacity)[A-Za-z_]*|"
    r"capacity[A-Za-z_]\w*|cache(?:Size|Limit|Capacity|Count|Entries)?|"
    r"evict[A-Za-z_]\w*|eviction[A-Za-z_]\w*|prune[A-Za-z_]\w*|"
    r"removeAt|clear))\b", re.IGNORECASE
)

CACHE_HINT_NAMES: Final[frozenset[str]] = frozenset({
    "cache", "asynchronous", "retainWhileLoading", "sourceSize",
    "cacheBuffer", "reuseItems", "cacheLimit", "cacheSize", "cacheCapacity",
    "maximumCacheSize", "cachePath", "cacheDir", "cache_home",
})
IMAGE_SOURCE_NAMES: Final[frozenset[str]] = frozenset({"source", "sourceSize"})


def _strip_comments(text: str) -> str:
    """Blank comments while preserving line numbers and quoted strings."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(text):
        char = text[index]
        if quote:
            output.append(char)
            if char == "\\" and index + 1 < len(text):
                index += 1
                output.append(text[index])
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
            output.append(char)
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            output.extend(" " * (end - index))
            index = end
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = len(text) if end < 0 else end + 2
            output.extend("\n" if c == "\n" else " " for c in text[index:end])
            index = end
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _matching_brace(text: str, opening: int) -> int:
    depth = 0
    quote: str | None = None
    index = opening
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 2
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
                return index
        index += 1
    return -1


def _brace_delta(line: str) -> int:
    delta = 0
    quote: str | None = None
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == "{":
            delta += 1
        elif char == "}":
            delta -= 1
        index += 1
    return delta


def _properties(body: str) -> list[dict[str, object]]:
    """Return first-level property assignments in declaration order."""
    properties: list[dict[str, object]] = []
    depth = 0
    for line_number, line in enumerate(body.splitlines(), 1):
        if depth == 0:
            # QML permits compact declarations such as ``id: icon; source: url``.
            # Split only on semicolons here; quoted values are retained as-is.
            for segment in line.split(";"):
                match = PROPERTY_RE.match(segment)
                if match:
                    properties.append({"name": match.group("name"), "value": match.group("value").strip()})
        depth += _brace_delta(line)
    return properties


def _identifier(properties: list[dict[str, object]]) -> str | None:
    value = next((row["value"] for row in properties if row["name"] == "id"), None)
    return str(value) if value else None


def _declaration(path: Path, root: Path, source: str, match: re.Match[str]) -> dict[str, object]:
    kind = match.group("kind")
    opening = source.find("{", match.start(), match.end())
    closing = _matching_brace(source, opening)
    body = source[match.end():closing] if closing >= 0 else source[match.end():]
    properties = _properties(body)
    line = source.count("\n", 0, match.start("kind")) + 1
    result: dict[str, object] = {
        "kind": kind,
        "file": path.relative_to(root).as_posix(),
        "line": line,
        "owner": path.stem,
        "identifier": _identifier(properties),
        "properties": properties,
    }
    if kind in IMAGE_TYPES:
        result["image_sources"] = [row for row in properties if row["name"] in IMAGE_SOURCE_NAMES]
        result["cache_hints"] = [row for row in properties if row["name"] in CACHE_HINT_NAMES]
    elif kind in MODEL_TYPES + VIEW_TYPES:
        result["cache_hints"] = [row for row in properties if row["name"] in CACHE_HINT_NAMES]
    return result


def _capacity_signals(path: Path, root: Path, source: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line_number, line in enumerate(source.splitlines(), 1):
        for match in SIGNAL_RE.finditer(line):
            name = match.group("name")
            category = "eviction" if name.startswith(("evict", "eviction", "prune", "removeAt", "clear")) else "bound"
            findings.append({
                "name": name,
                "category": category,
                "file": path.relative_to(root).as_posix(),
                "line": line_number,
                "expression": line.strip(),
            })
    return findings


def _layer_declarations(path: Path, root: Path, source: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line_number, line in enumerate(source.splitlines(), 1):
        for match in LAYER_RE.finditer(line):
            findings.append({
                "kind": "layer",
                "name": match.group("name"),
                "file": path.relative_to(root).as_posix(),
                "line": line_number,
                "expression": match.group("value").strip().rstrip("}").rstrip(),
                "owner": path.stem,
            })
    return findings


def _qml_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.qml") if path.is_file())


def inventory(root: Path) -> dict[str, object]:
    """Build a stable static inventory rooted at ``root``."""
    declarations: list[dict[str, object]] = []
    capacity_signals: list[dict[str, object]] = []
    layers: list[dict[str, object]] = []
    source_files = 0
    for path in _qml_files(root):
        try:
            source = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        source_files += 1
        declarations.extend(_declaration(path, root, source, match) for match in DECLARATION_RE.finditer(source))
        capacity_signals.extend(_capacity_signals(path, root, source))
        layers.extend(_layer_declarations(path, root, source))

    declarations.sort(key=lambda row: (row["file"], row["line"], row["kind"], row["identifier"] or ""))
    capacity_signals.sort(key=lambda row: (row["file"], row["line"], row["name"]))
    layers.sort(key=lambda row: (row["file"], row["line"], row["name"]))
    models = [row for row in declarations if row["kind"] in MODEL_TYPES]
    views = [row for row in declarations if row["kind"] in VIEW_TYPES]
    images = [row for row in declarations if row["kind"] in IMAGE_TYPES]
    canvases = [row for row in declarations if row["kind"] in CANVAS_TYPES]
    image_sources: list[dict[str, object]] = []
    cache_hints: list[dict[str, object]] = []
    for row in images:
        hints = row.get("image_sources")
        if isinstance(hints, list):
            image_sources.extend(hint for hint in hints if isinstance(hint, dict))
    for row in declarations:
        hints = row.get("cache_hints")
        if isinstance(hints, list):
            cache_hints.extend(hint for hint in hints if isinstance(hint, dict))
    counts = {kind: sum(row["kind"] == kind for row in declarations) for kind in DECLARATION_TYPES}
    counts.update({
        "image_sources": len(image_sources),
        "cache_hints": len(cache_hints),
        "max_limit_eviction_signals": len(capacity_signals),
        "canvas": len(canvases),
        "layers": len(layers),
    })
    return {
        "schema": 1,
        "evidence": "static-source",
        "runtime_claims": False,
        "root": "qml-source",
        "source_files": source_files,
        "counts": counts,
        "declarations": declarations,
        "models": models,
        "views": views,
        "images": images,
        "canvas": canvases,
        "layers": layers,
        "image_sources": image_sources,
        "cache_hints": cache_hints,
        "max_limit_eviction_signals": capacity_signals,
    }


def markdown(document: dict[str, object]) -> str:
    """Render the inventory without implying runtime observations."""
    counts = document.get("counts", {})
    lines = [
        "# Nyxuri Shell Model/Image/Cache Inventory", "",
        "> Static source inventory only; no runtime model size, cache residency, or eviction claim is made.", "",
        f"Source files: **{document.get('source_files', 0)}**", "",
        "## Counts", "", "| Category | Count |", "|---|---:|",
    ]
    if isinstance(counts, dict):
        for key in (*DECLARATION_TYPES, "image_sources", "cache_hints", "max_limit_eviction_signals", "canvas", "layers"):
            lines.append(f"| `{key}` | {counts.get(key, 0)} |")
    lines.extend(["", "## Declarations", "", "| Kind | File | Line | Owner | ID |", "|---|---|---:|---|---|"])
    declarations = document.get("declarations", [])
    for row in declarations if isinstance(declarations, list) else []:
        if isinstance(row, dict):
            values = [row.get(key) for key in ("kind", "file", "line", "owner", "identifier")]
            lines.append("| " + " | ".join("-" if value is None else str(value).replace("|", "\\|") for value in values) + " |")
    lines.extend(["", "## Capacity And Eviction Signals", "", "| Category | Name | File | Line | Expression |", "|---|---|---|---:|---|"])
    signals = document.get("max_limit_eviction_signals", [])
    for row in signals if isinstance(signals, list) else []:
        if isinstance(row, dict):
            values = [row.get(key) for key in ("category", "name", "file", "line", "expression")]
            lines.append("| " + " | ".join("-" if value is None else str(value).replace("|", "\\|") for value in values) + " |")
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
    if args.format == "json":
        content = encoded
    elif args.format == "markdown":
        content = markdown(document)
    else:
        content = encoded + "\n" + markdown(document)
    if str(args.output) == "-":
        sys.stdout.write(content)
    else:
        _write(args.output, content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
