"""Contracts for the container-only feature matrix runner."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "feature_matrix.py"
SPEC = importlib.util.spec_from_file_location("feature_matrix", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
feature_matrix = importlib.util.module_from_spec(SPEC)
sys.modules["feature_matrix"] = feature_matrix
SPEC.loader.exec_module(feature_matrix)


class FeatureMatrixTests(unittest.TestCase):
    def test_expected_matchers_cover_structured_and_negative_values(self):
        self.assertTrue(feature_matrix._matches('{"stage":"READY"}', "json"))
        self.assertTrue(feature_matrix._matches("DEGRADED", "one_of:OK,DEGRADED"))
        self.assertTrue(feature_matrix._matches("", "any"))
        self.assertFalse(feature_matrix._matches("INVALID", "one_of:OK,DEGRADED"))

    def test_host_invocation_is_unavailable_and_never_starts_shell(self):
        with tempfile.TemporaryDirectory(prefix="nyxuri-feature-matrix-test-") as directory:
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(Path(directory) / "matrix.json"),
                 "--repo", str(ROOT), "--shell", str(ROOT)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(process.returncode, 1)
        self.assertIn('"container_only": true', process.stdout)
        self.assertIn('"status": "UNAVAILABLE"', process.stdout)

    def test_checked_in_fixture_rejects_malformed_config(self):
        rows = feature_matrix._fixture_probe(ROOT.parent)
        malformed = next(row for row in rows if row["id"] == "negative.malformed_config")
        self.assertEqual(malformed["status"], "PASS")
        self.assertNotEqual(malformed["malformed_returncode"], 0)


if __name__ == "__main__":
    unittest.main()
