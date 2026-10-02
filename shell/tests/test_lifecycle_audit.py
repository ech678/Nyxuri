"""Unit tests for Nyxuri Shell lifecycle and side-effect auditor (audit-lifecycle.py)."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

# Load audit-lifecycle module dynamically
script_path = Path(__file__).resolve().parent.parent / "scripts" / "dev" / "audit-lifecycle.py"
spec = importlib.util.spec_from_file_location("audit_lifecycle", script_path)
audit = importlib.util.module_from_spec(spec)
sys.modules["audit_lifecycle"] = audit
spec.loader.exec_module(audit)


class TestLifecycleAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell_root = Path(__file__).resolve().parent.parent
        cls.fixtures_dir = cls.shell_root / "tests" / "fixtures" / "lifecycle"

    def test_clean_fixture_passes(self):
        clean_file = self.fixtures_dir / "valid" / "CleanComponent.qml"
        self.assertTrue(clean_file.is_file(), f"Fixture missing: {clean_file}")
        violations = audit.check_file_violations(clean_file, self.shell_root, force=True)
        self.assertEqual(violations, [], f"Expected clean fixture to pass, got: {violations}")

    def test_life001_missing_owner(self):
        target = self.fixtures_dir / "invalid" / "life001_missing_owner.qml"
        violations = audit.check_file_violations(target, self.shell_root, force=True)
        codes = [v.code for v in violations]
        self.assertIn("LIFE001", codes)
        v = next(v for v in violations if v.code == "LIFE001")
        self.assertEqual(v.line_number, 8)
        self.assertIn("Missing resource owner", v.message)

    def test_life002_missing_teardown(self):
        target = self.fixtures_dir / "invalid" / "life002_missing_teardown.qml"
        violations = audit.check_file_violations(target, self.shell_root, force=True)
        codes = [v.code for v in violations]
        self.assertIn("LIFE002", codes)
        v = next(v for v in violations if v.code == "LIFE002")
        self.assertIn(v.line_number, (7, 14))
        self.assertIn("Missing destruction/teardown path", v.message)

    def test_life003_shared_sideeffects(self):
        target = self.fixtures_dir / "invalid" / "life003_shared_sideeffect.qml"
        violations = audit.check_file_violations(target, self.shell_root, force=True, is_shared_override=True)
        codes = [v.code for v in violations]
        self.assertIn("LIFE003", codes)
        life003_list = [v for v in violations if v.code == "LIFE003"]
        messages = " ".join(v.message for v in life003_list)
        self.assertIn("Process is prohibited in shared/", messages)
        self.assertIn("importing services is prohibited in shared/", messages)

    def test_life004_direct_exec(self):
        target = self.fixtures_dir / "invalid" / "life004_direct_exec.qml"
        violations = audit.check_file_violations(target, self.shell_root, force=True)
        codes = [v.code for v in violations]
        self.assertIn("LIFE004", codes)
        v = next(v for v in violations if v.code == "LIFE004")
        self.assertEqual(v.line_number, 8)
        self.assertIn("Direct external command", v.message)

    def test_life005_no_fallback(self):
        target = self.fixtures_dir / "invalid" / "life005_no_fallback.qml"
        violations = audit.check_file_violations(target, self.shell_root, force=True)
        codes = [v.code for v in violations]
        self.assertIn("LIFE005", codes)
        v = next(v for v in violations if v.code == "LIFE005")
        self.assertEqual(v.line_number, 2)
        self.assertIn("Optional dependency without fallback", v.message)

    def test_life006_visible_only(self):
        target = self.fixtures_dir / "invalid" / "life006_visible_only.qml"
        violations = audit.check_file_violations(target, self.shell_root, force=True)
        codes = [v.code for v in violations]
        self.assertIn("LIFE006", codes)
        v = next(v for v in violations if v.code == "LIFE006")
        self.assertEqual(v.line_number, 9)
        self.assertIn("Deactivation only via visible", v.message)

    def test_excluded_paths(self):
        self.assertTrue(audit.is_path_excluded("references/clavis-15403b9/AppShell.qml"))
        self.assertTrue(audit.is_path_excluded("vendor/somelib/Module.qml"))
        self.assertTrue(audit.is_path_excluded("tests/fixtures/lifecycle/invalid/life001.qml"))
        self.assertTrue(audit.is_path_excluded("build/qml/Module.qml"))
        self.assertTrue(audit.is_path_excluded("generated/SearchCatalog.js"))
        self.assertFalse(audit.is_path_excluded("app/services/SystemMonitorService.qml"))
        self.assertFalse(audit.is_path_excluded("modules/bar/Bar.qml"))
        self.assertFalse(audit.is_path_excluded("shared/controls/RippleButton.qml"))
        self.assertFalse(audit.is_path_excluded("native/fallback/Clavis/Cava/CavaProvider.qml"))

        vendor_fixture = self.fixtures_dir / "excluded" / "vendor" / "IgnoredVendor.qml"
        violations = audit.check_file_violations(vendor_fixture, self.shell_root, force=False)
        self.assertEqual(violations, [], "Excluded vendor files must be ignored without force flag")

    def test_stable_sorting(self):
        v1 = audit.AuditViolation("LIFE002", "modules/b.qml", 20, "msg2")
        v2 = audit.AuditViolation("LIFE001", "modules/b.qml", 10, "msg1")
        v3 = audit.AuditViolation("LIFE004", "app/a.qml", 5, "msg0")
        sorted_list = sorted([v1, v2, v3], key=lambda v: v.to_tuple())
        self.assertEqual(sorted_list, [v3, v2, v1])

    def test_inventory_extraction(self):
        clean_file = self.fixtures_dir / "valid" / "CleanComponent.qml"
        entries = audit.build_inventory_entry(clean_file, self.shell_root)
        self.assertEqual(entries, [], "Fixtures are excluded from inventory")

        app_shell = self.shell_root / "app" / "AppShell.qml"
        entries = audit.build_inventory_entry(app_shell, self.shell_root)
        types = [e["resource_type"] for e in entries]
        self.assertIn("NativeConsumer", types)
        self.assertIn("ExternalCommand", types)


if __name__ == "__main__":
    unittest.main()
