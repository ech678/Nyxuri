"""D-1 type-scale contract gates.

The single library-wide type scale is NexusStyle.font (commons/, pinned
value-by-value in test_preference_atoms.TestNexusStyleParity). These gates
keep it single: literal pixelSize values, the retired Typography singleton
and the retired end4 Appearance.font ladder may not come back. vendor/ trees
are frozen upstream reference copies and stay exempt, like references/.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL = REPO_ROOT / "shell"

RE_LITERAL = re.compile(r"(?:font\.)?pixelSize:\s*\d")
RE_TYPOGRAPHY = re.compile(r"\bTypography\.")
RE_END4_LADDER = re.compile(r"Appearance\.font\.pixelSize")


def qml_files() -> list[Path]:
    return [p for p in sorted(SHELL.rglob("*.qml")) if "vendor" not in p.parts]


class TestSingleTypeScale(unittest.TestCase):
    """One table everywhere: NexusStyle.font in commons/."""

    def test_nexusstyle_is_defined_exactly_once_in_commons(self):
        hits = list(SHELL.rglob("NexusStyle.qml"))
        self.assertEqual(hits, [SHELL / "commons" / "NexusStyle.qml"],
                         "NexusStyle must live exactly once, in the token home")

    def test_retired_typography_singleton_stays_deleted(self):
        self.assertFalse((SHELL / "commons" / "Typography.qml").exists(),
                         "Typography was retired by D-1; NexusStyle.font is the scale")
        offenders = [str(p) for p in qml_files() if RE_TYPOGRAPHY.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [], "Typography references must not come back")

    def test_end4_appearance_font_ladder_stays_retired(self):
        offenders = [f"{p}:{i + 1}" for p in qml_files()
                     for i, line in enumerate(p.read_text(encoding="utf-8").splitlines())
                     if RE_END4_LADDER.search(line)]
        self.assertEqual(offenders, [],
                         "bar type reads NexusStyle.font; the end4 ladder is gone")

    def test_no_literal_pixel_size_anywhere(self):
        offenders = [f"{p}:{i + 1}" for p in qml_files()
                     for i, line in enumerate(p.read_text(encoding="utf-8").splitlines())
                     if RE_LITERAL.search(line)]
        self.assertEqual(offenders, [],
                         "every pixelSize must flow from NexusStyle tokens "
                         "(type scale, mono or icon ladder)")

    def test_nexusstyle_consumers_import_commons(self):
        # NexusStyle lives in qs.commons (D-1 move from qs.ui). A consumer
        # without the exact import resolves nothing at runtime — the binding
        # dies with "NexusStyle is not defined" and geometry collapses (the
        # 2026-11-21 settings-page overlap: qs.commons.i18n is a different
        # module and must not substring-match this audit).
        offenders = []
        for path in qml_files():
            if path == SHELL / "commons" / "NexusStyle.qml":
                continue
            code_lines = [l for l in path.read_text(encoding="utf-8").splitlines()
                          if not l.lstrip().startswith("//")]
            uses = any("NexusStyle." in l for l in code_lines)
            has_import = any(re.match(r"\s*import qs\.commons\s*$", l) for l in code_lines)
            if uses and not has_import:
                offenders.append(str(path))
        self.assertEqual(offenders, [],
                         "NexusStyle consumers must import qs.commons (exact line)")


if __name__ == "__main__":
    unittest.main()
