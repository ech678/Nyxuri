"""Provider-neutral user-template registration primitives."""

import tempfile
import tomllib
import re
from pathlib import Path
from typing import Iterable


def validate(content: str) -> None:
    tomllib.loads(content)


def write_atomic(path: Path, content: str) -> None:
    validate(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp = Path(handle.name)
    temp.replace(path)


def remove_sections(content: str, sections: Iterable[str]) -> str:
    owned = set(sections)
    result: list[str] = []
    skip = False
    for line in content.splitlines():
        header = line.split("#", 1)[0].strip()
        if header.startswith("[") and header.endswith("]"):
            skip = header[1:-1] in owned
        if not skip:
            result.append(line)
    return "\n".join(result).rstrip() + "\n"


def set_section_key(content: str, section: str, key: str, value: str) -> str:
    """Set a string key in a TOML table while preserving surrounding text."""
    header = f"[{section}]"
    lines = content.splitlines()
    try:
        start = lines.index(header)
    except ValueError:
        return content
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].split("#", 1)[0].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = index
            break
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    assignment = f'{key} = "{escaped}"'
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index in range(start + 1, end):
        if pattern.match(lines[index]):
            lines[index] = assignment
            return "\n".join(lines).rstrip() + "\n"
    lines.insert(end, assignment)
    return "\n".join(lines).rstrip() + "\n"


def has_section(content: str, section: str) -> bool:
    """Check if a specific TOML table header exists in content."""
    target = f"[{section}]"
    for line in content.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped == target:
            return True
    return False


def add_section(content: str, section: str, items: dict[str, str] | None = None) -> str:
    """Ensure a TOML section exists with the given key-value string pairs."""
    header = f"[{section}]"
    lines = content.rstrip().splitlines() if content.strip() else []
    try:
        lines.index(header)
    except ValueError:
        if lines:
            lines.append("")
        lines.append(header)
        if items:
            for k, v in items.items():
                escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{k} = "{escaped}"')
        return "\n".join(lines).rstrip() + "\n"

    res = "\n".join(lines) + "\n"
    if items:
        for k, v in items.items():
            res = set_section_key(res, section, k, str(v))
    return res


def render_template(template: str, context: dict) -> str:
    """Interpolate {{ path.to.token }} placeholders using a dictionary context."""
    def _lookup(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        parts = expr.split(".")
        curr = context
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return match.group(0)
        return str(curr)

    pattern = re.compile(r"\{\{\s*([^{}\s]+)\s*\}\}")
    return pattern.sub(_lookup, template)
