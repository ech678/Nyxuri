"""Structural integrity: every msg("key") call has a TRANSLATIONS entry, no orphan keys.

Uses ast to parse all .py files — no runtime execution needed. Catches:
- msg("key") calls with no matching TRANSLATIONS entry (missing key)
- TRANSLATIONS entries never referenced by any code (orphan key)
"""

import ast
import re
import string
import tomllib
import unittest
from pathlib import Path

from tests.utils import TempEnv

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
    """Read declared keys independently of the runtime loader."""
    with (ENGINE_DIR / "translations.toml").open("rb") as source:
        return set(tomllib.load(source))


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

    The TOML catalog is outside this Python scan; declarations cannot make
    themselves appear referenced.
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
    """Both languages must accept the same arguments and resolve constants."""

    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_catalog_languages_and_arguments(self):
        from nyxniri.i18n import TRANSLATIONS
        formatter = string.Formatter()
        self.assertTrue(TRANSLATIONS)
        for key, entry in TRANSLATIONS.items():
            with self.subTest(key=key):
                self.assertEqual(set(entry), {"zh", "en"})
                fields = []
                for value in entry.values():
                    self.assertIsInstance(value, str)
                    names = {name for _, name, _, _ in formatter.parse(value) if name is not None}
                    self.assertTrue(all(name.isdecimal() for name in names), names)
                    fields.append(names)
                self.assertEqual(*fields)

    def test_language_switch_and_fallback(self):
        from nyxniri import i18n
        self.addCleanup(i18n.set_lang, i18n.get_lang())
        for language in ("zh", "en", "zh"):
            i18n.set_lang(language)
            self.assertEqual(i18n.msg("installed"), i18n.TRANSLATIONS["installed"][language])
            self.assertIn("sample", i18n.msg("preset_toast_applied", "sample", "example"))
        self.assertEqual(i18n.msg("unknown_key"), "unknown_key")
        self.assertEqual(i18n.msg("unknown_key", "sample"), "unknown_key (sample)")

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
