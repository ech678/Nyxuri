"""Contracts for the container-only feature matrix runner."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


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

    def test_missing_ipc_target_is_unavailable_not_a_pass(self):
        result = subprocess.CompletedProcess(
            ["qs"], 0, stdout=feature_matrix.TARGET_NOT_FOUND + "\n", stderr=""
        )
        row = feature_matrix.classify_ipc("control_center.open", result, "OK", 1.25)
        self.assertEqual(row["status"], "UNAVAILABLE")
        self.assertEqual(row["target_result"]["stdout"], feature_matrix.TARGET_NOT_FOUND)

    def test_unknown_ipc_target_rejection_accepts_target_not_found_reply(self):
        result = subprocess.CompletedProcess(
            ["qs"], 0, stdout=feature_matrix.TARGET_NOT_FOUND + "\n", stderr=""
        )
        self.assertTrue(feature_matrix._unknown_target_rejected(result))

        succeeded = subprocess.CompletedProcess(["qs"], 0, stdout="pong\n", stderr="")
        self.assertFalse(feature_matrix._unknown_target_rejected(succeeded))

    def test_report_summarizes_three_statuses_without_upgrading_partial(self):
        report = feature_matrix._report([
            {"id": "ok", "status": "PASS"},
            {"id": "partial", "status": "PARTIAL"},
            {"id": "visual", "status": "UNAVAILABLE"},
        ])
        self.assertEqual(report["status"], "PARTIAL")
        self.assertEqual(report["summary"], {
            "total": 3, "counts": {"PASS": 1, "PARTIAL": 1, "UNAVAILABLE": 1}
        })

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

    def test_unit_transition_timeout_keeps_matrix_reportable(self):
        with tempfile.TemporaryDirectory(prefix="nyxuri-feature-matrix-lifecycle-") as directory:
            home = Path(directory) / "home"
            home.mkdir()
            state_home = home / ".local/state"
            env = {"HOME": str(home), "XDG_STATE_HOME": str(state_home),
                   "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
                   "XDG_CACHE_HOME": str(home / ".cache")}
            account = SimpleNamespace(pw_uid=65534, pw_gid=65534)
            with patch.object(feature_matrix.pwd, "getpwnam", return_value=account), \
                 patch.object(feature_matrix.os, "chown"), \
                 patch.object(feature_matrix, "_run_unit_transition", side_effect=subprocess.TimeoutExpired("nyxuri", 20)):
                rows = feature_matrix._unit_lifecycle_rows(ROOT.parent, "qs", str(ROOT), env, ready=True)
        self.assertEqual(rows[0]["id"], "lifecycle.unit_off")
        self.assertEqual(rows[0]["status"], "PARTIAL")
        self.assertEqual(rows[1]["status"], "UNAVAILABLE")

    def test_unit_on_failure_records_recovery_attempt(self):
        with tempfile.TemporaryDirectory(prefix="nyxuri-feature-matrix-lifecycle-") as directory:
            state_home = Path(directory) / "state"
            home = Path(directory) / "home"
            home.mkdir()
            state_home = home / ".local/state"
            ledger_path = state_home / "nyxuri" / "state.json"
            ledger_path.parent.mkdir(parents=True)
            ledger_path.write_text("{}", encoding="utf-8")
            env = {"HOME": str(home), "XDG_STATE_HOME": str(state_home),
                   "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
                   "XDG_CACHE_HOME": str(home / ".cache")}
            account = SimpleNamespace(pw_uid=65534, pw_gid=65534)
            completed = subprocess.CompletedProcess(["nyxuri"], 0, "", "")
            reload_ok = subprocess.CompletedProcess(["qs"], 0, "OK\n", "")
            reload_fail = subprocess.CompletedProcess(["qs"], 1, "", "reload failed")
            with patch.object(feature_matrix.pwd, "getpwnam", return_value=account), \
                 patch.object(feature_matrix.os, "chown"), \
                 patch.object(feature_matrix, "_run_unit_transition", return_value=completed), \
                 patch.object(feature_matrix, "_ipc", side_effect=[(reload_ok, 1.0), (reload_fail, 1.0), (reload_ok, 1.0)]), \
                 patch.object(feature_matrix, "_wait_unit_state", return_value=True), \
                 patch.object(feature_matrix.json, "loads", side_effect=[{"plugins": {"shell.bar": {"state": "disabled"}}},
                                                                            {"plugins": {"shell.bar": {"state": "enabled"}}},
                                                                            {"plugins": {"shell.bar": {"state": "enabled"}}}]):
                rows = feature_matrix._unit_lifecycle_rows(ROOT.parent, "qs", str(ROOT), env, ready=True)
        self.assertEqual([row["status"] for row in rows], ["PASS", "PARTIAL"])
        self.assertEqual(rows[1]["recovery"]["status"], "PASS")

    def test_projection_lifecycle_writes_private_ledger_and_reports_reload_result(self):
        with tempfile.TemporaryDirectory(prefix="nyxuri-feature-matrix-projection-") as directory:
            state_home = Path(directory) / "home" / ".local/state"
            env = {"HOME": str(Path(directory) / "home"), "XDG_STATE_HOME": str(state_home)}
            reload_ok = subprocess.CompletedProcess(["qs"], 0, "OK\n", "")
            with patch.object(feature_matrix, "_ipc", return_value=(reload_ok, 1.0)), \
                 patch.object(feature_matrix, "_wait_unit_state", return_value=True):
                rows = feature_matrix._projection_lifecycle_rows("qs", str(ROOT), env, ready=True)
            ledger = json.loads((state_home / "nyxuri/state.json").read_text(encoding="utf-8"))
        self.assertEqual([row["status"] for row in rows], ["PASS", "PASS"])
        self.assertEqual(ledger["plugins"]["shell.bar"]["state"], "enabled")

    def test_live_census_uses_loaded_unit_ids_not_declared_ids(self):
        metrics = json.dumps({"qml_census": {"units": {
            "ids": ["shell.bar", "shell.dock"], "loaded_ids": ["shell.bar"]
        }}})
        result = subprocess.CompletedProcess(["qs"], 0, metrics, "")
        with patch.object(feature_matrix, "_ipc", return_value=(result, 1.0)):
            units = feature_matrix._qml_units("qs", str(ROOT), {})
        self.assertEqual(units, {"shell.bar"})


if __name__ == "__main__":
    unittest.main()
