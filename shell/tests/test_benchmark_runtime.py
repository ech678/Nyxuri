"""Focused contracts for runtime benchmark telemetry and failure gating."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.utils import TempEnv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "dev"))
_RUNTIME_PATH = ROOT / "scripts" / "dev" / "benchmark_runtime.py"
_SPEC = importlib.util.spec_from_file_location("benchmark_runtime", _RUNTIME_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load {_RUNTIME_PATH}")
runtime = importlib.util.module_from_spec(_SPEC)
sys.modules["benchmark_runtime"] = runtime
_SPEC.loader.exec_module(runtime)
_REPORT_SPEC = importlib.util.spec_from_file_location(
    "benchmark_report", ROOT / "scripts" / "dev" / "benchmark_report.py"
)
if _REPORT_SPEC is None or _REPORT_SPEC.loader is None:
    raise RuntimeError("cannot load benchmark_report")
report = importlib.util.module_from_spec(_REPORT_SPEC)
sys.modules["benchmark_report"] = report
_REPORT_SPEC.loader.exec_module(report)


class BenchmarkRuntimeTests(unittest.TestCase):
    def test_live_telemetry_marks_unexposed_qml_counts_unavailable(self):
        with TempEnv():
            snapshot = runtime.parse_live_telemetry(
                '{"stage":"IPC_READY","elapsed_ms":420,"background_queue":2}',
                sampled_at_ms=1234,
            )

        self.assertEqual(snapshot["status"], "available")
        self.assertEqual(snapshot["startup_metrics"]["stage"], "IPC_READY")
        self.assertEqual(snapshot["sampled_at_ms"], 1234)
        self.assertEqual(snapshot["qml_resources"]["status"], "unavailable")
        self.assertIsNone(snapshot["qml_resources"]["counts"]["loaders"])
        self.assertIsNone(snapshot["qml_resources"]["counts"]["delegates"])

    def test_live_telemetry_accepts_a_complete_runtime_resource_snapshot(self):
        with TempEnv():
            snapshot = runtime.parse_live_telemetry(
                '{"stage":"READY","qml_resources":{"loaders":4,"timers":7,'
                '"processes":1,"fileviews":2,"connections":3,"delegates":9,'
                '"canvas":2,"layers":5,"windows":1}}',
                sampled_at_ms=5678,
            )

        self.assertEqual(snapshot["qml_resources"]["status"], "available")
        self.assertEqual(snapshot["qml_resources"]["counts"]["loaders"], 4)
        self.assertEqual(snapshot["qml_resources"]["counts"]["delegates"], 9)
        self.assertEqual(snapshot["qml_resources"]["counts"]["windows"], 1)

    def test_process_failures_are_classified_per_command_and_fail_closed(self):
        with TempEnv():
            failures = runtime.classify_process_start_failures(
                'Process failed to start: No such file or directory\n'
                'Command: QList("key", "-s")\n'
                'Process failed to start: No such file or directory\n'
                'Command: QList("/usr/bin/niri", "msg")\n'
                'Process failed to start: No such file or directory\n'
                'No command details were emitted\n'
            )

        self.assertEqual(
            [(failure.command, failure.category) for failure in failures],
            [("key", "optional"), ("niri", "required"), (None, "unattributed")],
        )
        self.assertEqual(runtime.process_failure_counts(failures), {
            "process_start_failures": 3,
            "optional_process_start_failures": 1,
            "required_process_start_failures": 2,
            "unattributed_process_start_failures": 1,
        })
        self.assertTrue(runtime.has_required_process_failures(failures))

    def test_optional_failures_do_not_block_success_gate(self):
        with TempEnv():
            optional = runtime.classify_process_start_failures(
                'Process failed to start: No such file or directory\n'
                'Command: QList("ddcutil", "getvcp")\n'
            )

        self.assertFalse(runtime.has_required_process_failures(optional))

    def test_live_telemetry_uses_the_private_shell_metrics_ipc_target(self):
        result = Mock(returncode=0, stdout='{"stage":"IPC_READY"}', stderr="")
        with TempEnv(), patch.object(runtime.subprocess, "run", return_value=result) as run:
            snapshot = runtime._capture_live_telemetry(
                {"XDG_RUNTIME_DIR": "/tmp/isolated-runtime"}, "/workspace/shell"
            )

        self.assertEqual(
            run.call_args.args[0],
            ["qs", "-p", "/workspace/shell", "ipc", "call", "shell", "metrics"],
        )
        self.assertEqual(snapshot["status"], "available")
        self.assertEqual(snapshot["qml_resources"]["status"], "unavailable")

    def test_report_summarizes_unattributed_process_failures(self):
        with TempEnv():
            summary = report.summarize([{"unattributed_process_start_failures": 2}])

        self.assertEqual(summary["unattributed_process_start_failures"]["p50"], 2)


if __name__ == "__main__":
    unittest.main()
