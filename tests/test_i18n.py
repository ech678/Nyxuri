"""Structural integrity: every msg("key") call has a TRANSLATIONS entry, no orphan keys.

Uses ast to parse all .py files — no runtime execution needed. Catches:
- msg("key") calls with no matching TRANSLATIONS entry (missing key)
- TRANSLATIONS entries never referenced by any code (orphan key)
"""

import ast
import os
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = REPO_ROOT / "nyxniri"


def _collect_msg_calls() -> set:
    """Find all msg("key") / msg('key') string-literal calls across all .py files."""
    keys = set()
    for py_file in ENGINE_DIR.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "msg":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    keys.add(node.args[0].value)
    return keys


def _collect_translation_keys() -> set:
    """Find all keys in the TRANSLATIONS dict in i18n.py."""
    i18n_file = ENGINE_DIR / "i18n.py"
    tree = ast.parse(i18n_file.read_text(encoding="utf-8"), filename=str(i18n_file))
    for node in ast.walk(tree):
        # Handle both plain Assign and AnnAssign (TRANSLATIONS: Dict[...] = {...})
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "TRANSLATIONS":
            if isinstance(node.value, ast.Dict):
                return {
                    k.value for k in node.value.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                }
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TRANSLATIONS":
                    if isinstance(node.value, ast.Dict):
                        return {
                            k.value for k in node.value.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        }
    return set()


# Also collect prompt_confirm("key") calls — these also need TRANSLATIONS entries
def _collect_prompt_confirm_calls() -> set:
    """Find all prompt_confirm("key") string-literal calls."""
    keys = set()
    for py_file in ENGINE_DIR.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "prompt_confirm"):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    keys.add(node.args[0].value)
    return keys


# Key prefixes built at runtime via f-strings (AST scan cannot see them).
# Must point at the construction site when adding a new prefix.
DYNAMIC_KEY_PREFIXES = (
    "app_",         # nyxniri/deps.py: msg(f"app_{app.replace('-', '_')}")
    "apps_cat_",    # nyxniri/deps.py: msg(f"apps_cat_{cat}")
    "preset_src_",  # nyxniri/deploy/preset.py: msg(f"preset_src_{source}")
)


def _collect_all_referenced_keys() -> set:
    """Find all string constants in .py files that match i18n key naming and exist in TRANSLATIONS.

    This catches direct msg("key") calls, indirect title_key/hint_key passed to TUI components,
    and any other string literal that happens to be an i18n key.

    i18n.py itself is excluded: the TRANSLATIONS dict literal contains every key
    as a string constant, so scanning it makes every key self-referencing and the
    orphan check vacuous.
    """
    import re
    key_pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    candidates = set()
    for py_file in ENGINE_DIR.rglob("*.py"):
        if py_file.name == "i18n.py":
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value
                if key_pattern.match(val) and len(val) > 3:
                    candidates.add(val)
    return candidates


class TestI18nKeyIntegrity(unittest.TestCase):
    """Verify i18n key completeness: no missing keys, no orphan keys."""

    @classmethod
    def setUpClass(cls):
        cls.translation_keys = _collect_translation_keys()
        cls.all_referenced = _collect_all_referenced_keys() & cls.translation_keys
        cls.msg_keys = _collect_msg_calls()
        cls.prompt_keys = _collect_prompt_confirm_calls()

    def test_no_missing_keys(self):
        """Every msg("key") / prompt_confirm("key") call must have a TRANSLATIONS entry."""
        direct_refs = self.msg_keys | self.prompt_keys
        missing = direct_refs - self.translation_keys
        self.assertEqual(missing, set(),
                         f"Missing i18n keys (referenced in code but not in TRANSLATIONS): {sorted(missing)}")

    def test_no_orphan_keys(self):
        """Every TRANSLATIONS entry should be referenced somewhere in the codebase.

        Orphan keys indicate a feature was removed but its i18n entries were not cleaned up.
        References can be direct msg("key") calls or indirect (title_key/hint_key passed
        to TUI components that call msg() internally). Keys whose prefix is listed in
        DYNAMIC_KEY_PREFIXES are constructed at runtime and exempt from this check.
        """
        def _is_dynamic(key: str) -> bool:
            return any(key.startswith(p) for p in DYNAMIC_KEY_PREFIXES)

        orphans = {k for k in (self.translation_keys - self.all_referenced)
                   if not _is_dynamic(k)}

        self.assertEqual(orphans, set(),
                         f"Orphan i18n keys (defined in TRANSLATIONS but never referenced): {sorted(orphans)}")


class TestTemplateSubstitution(unittest.TestCase):
    """Runtime guard: templated entries must actually substitute their args.

    Every placeholder entry is written as an f-string so the loader collapses
    ``{{0}}`` -> ``{0}``; ``msg()`` then substitutes via ``.format()``. A plain
    string accidentally carrying ``{{0}}`` survives as literal braces and
    ``.format()`` emits a literal ``{0}`` (arg dropped). Asserts no runtime
    value still contains ``{{`` or ``}}`` — catches that whole class of mistake.
    """

    def test_no_double_brace_residual(self):
        from nyxniri.i18n import TRANSLATIONS
        offenders = []
        for key, entry in TRANSLATIONS.items():
            for lang, val in entry.items():
                if "{{" in val or "}}" in val:
                    offenders.append(f"{key}[{lang}] = {val!r}")
        self.assertEqual(
            offenders, [],
            f"Templated entries still carrying literal braces (forgot f-prefix?): {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
