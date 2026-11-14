#!/usr/bin/env python3
"""Emit a deterministic, source-only inventory of QML resource objects.

The report describes source declarations, not instantiated objects or runtime
state.  ``running`` and ``interval`` expressions are retained when they are
not literals so the inventory cannot accidentally make a runtime claim.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

RESOURCE_TYPES: Final[tuple[str, ...]] = ("Timer", "Process", "FileView", "Connections")
DECLARATION_RE: Final[re.Pattern[str]] = re.compile(
    r"(?m)(?:^|[{;\n])[ \t]*(?:component\s+[A-Za-z_]\w*\s*:\s*)?"
    r"(Timer|Process|FileView|Connections)\s*\{" )
PROPERTY_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(id|running|interval|repeat)\s*:\s*(.*?)\s*;?\s*$"
)


@dataclass(frozen=True, slots=True)
class ResourceEntry:
    """One statically declared QML resource object."""

    kind: str
    file: str
    line: int
    owner: str
    identifier: str | None
    default_running: bool | str | None
    interval: int | float | str | None
    repeat: bool | str | None

    def as_dict(self) -> dict[str, object]:
        """Return the JSON-compatible entry shape."""
        return asdict(self)


def _strip_comments(text: str) -> str:
    """Replace comments with whitespace while preserving line and quote data."""
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
            output.extend("\n" if char == "\n" else " " for char in text[index:end])
            index = end
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _matching_brace(text: str, opening: int) -> int:
    """Return the closing brace for ``opening`` or ``-1`` for malformed QML."""
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
    """Count braces in a comment-free source line, ignoring quoted strings."""
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


def _properties(body: str) -> dict[str, str]:
    """Read selected first-level properties from one QML object body."""
    values: dict[str, str] = {}
    depth = 0
    for line in body.splitlines():
        if depth == 0:
            match = PROPERTY_RE.match(line)
            if match and match.group(1) not in values:
                values[match.group(1)] = match.group(2).strip()
        depth += _brace_delta(line)
    return values


def _expression(value: str | None) -> bool | str | None:
    if value is None or value == "":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    return value


def _interval(value: str | None) -> int | float | str | None:
    """Parse a literal interval while retaining binding expressions."""
    if value is None or value == "":
        return None
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def _qml_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.qml") if path.is_file())


def inventory(root: Path) -> dict[str, object]:
    """Build a stable source inventory rooted at ``root``."""
    entries: list[ResourceEntry] = []
    source_files = 0
    for path in _qml_files(root):
        try:
            original = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        source_files += 1
        source = _strip_comments(original)
        for match in DECLARATION_RE.finditer(source):
            closing = _matching_brace(source, match.end() - 1)
            body = source[match.end():closing] if closing >= 0 else source[match.end():]
            props = _properties(body)
            entries.append(ResourceEntry(
                kind=match.group(1),
                file=path.relative_to(root).as_posix(),
                line=source.count("\n", 0, match.start(1)) + 1,
                owner=path.stem,
                identifier=props.get("id"),
                default_running=_expression(props.get("running")),
                interval=_interval(props.get("interval")),
                repeat=_expression(props.get("repeat")),
            ))
    entries.sort(key=lambda item: (item.file, item.line, item.kind, item.identifier or ""))
    counts = {kind: sum(entry.kind == kind for entry in entries) for kind in RESOURCE_TYPES}
    return {
        "schema": 1,
        "evidence": "static-source",
        "runtime_claims": False,
        "root": "qml-source",
        "source_files": source_files,
        "counts": counts,
        "resources": [entry.as_dict() for entry in entries],
    }


def markdown(document: dict[str, object]) -> str:
    """Render an inventory document as deterministic Markdown."""
    counts = document.get("counts", {})
    resources = document.get("resources", [])
    lines = ["# Nyxuri Shell QML Resource Inventory", "",
             "> Static source inventory only; it does not claim runtime instantiation or liveness.", "",
             f"Source files: **{document.get('source_files', 0)}**", "",
             "## Counts", "", "| Resource | Count |", "|---|---:|"]
    if isinstance(counts, dict):
        lines.extend(f"| `{kind}` | {counts.get(kind, 0)} |" for kind in RESOURCE_TYPES)
    lines += ["", "## Declarations", "", "| Kind | File | Line | Owner | ID | Default running | Interval | Repeat |",
              "|---|---|---:|---|---|---|---|---|"]
    if isinstance(resources, list):
        for row in resources:
            if not isinstance(row, dict):
                continue
            fields = ("kind", "file", "line", "owner", "identifier", "default_running", "interval", "repeat")
            values = [row.get(field) for field in fields]
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
        if str(args.output) == "-":
            sys.stdout.write(encoded)
        else:
            _write(args.output, encoded)
    elif args.format == "markdown":
        content = markdown(document)
        if str(args.output) == "-":
            sys.stdout.write(content)
        else:
            _write(args.output, content)
    elif str(args.output) == "-":
        sys.stdout.write(encoded + "\n" + markdown(document))
    else:
        output = args.output
        if output.suffix:
            _write(output.with_suffix(".json"), encoded)
            _write(output.with_suffix(".md"), markdown(document))
        else:
            _write(output / "resource-inventory.json", encoded)
            _write(output / "resource-inventory.md", markdown(document))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
