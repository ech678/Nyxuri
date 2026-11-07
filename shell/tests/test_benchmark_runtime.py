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
_SCENARIOS_SPEC = importlib.util.spec_from_file_location(
    "benchmark_scenarios", ROOT / "scripts" / "dev" / "benchmark_scenarios.py"
)
if _SCENARIOS_SPEC is None or _SCENARIOS_SPEC.loader is None:
    raise RuntimeError("cannot load benchmark_scenarios")
scenarios = importlib.util.module_from_spec(_SCENARIOS_SPEC)
sys.modules["benchmark_scenarios"] = scenarios
_SCENARIOS_SPEC.loader.exec_module(scenarios)


class BenchmarkRuntimeTests(unittest.TestCase):
    def test_frame_profile_payload_accepts_qt_prefixed_debug_log(self):
        log = '\x1b[34m DEBUG\\x1b[97m qml\\x1b[0m: FRAME_PROFILE {"status":"available","frames":301}'

        self.assertEqual(
            scenarios._frame_profile_payload(log),
            {"status": "available", "frames": 301},
        )

    def test_frame_profile_probe_is_container_only_and_declares_partial_metrics(self):
        scenarios = (ROOT / "scripts" / "dev" / "benchmark_scenarios.py").read_text(encoding="utf-8")
        self.assertIn("def frame_profile_benchmark", scenarios)
        self.assertIn("Qt QQuickWindow.frameSwapped", scenarios)
        self.assertIn("weston_presentation_feedback", scenarios)
        self.assertIn('"status": "partial"', scenarios)
        self.assertNotIn('os.environ["DISPLAY"]', scenarios)

    def test_report_preserves_frame_profile_evidence(self):
        built = report.build_report({"frame_profile": {"probe": {"status": "partial"}}})
        self.assertEqual(built["raw"]["frame_profile"]["probe"]["status"], "partial")

    def test_qml_census_contract_is_live_and_tears_down_loader_records(self):
        startup = (ROOT / "services" / "ShellStartupService.qml").read_text(encoding="utf-8")
        slot = (ROOT / "app" / "SlotHost.qml").read_text(encoding="utf-8")
        self.assertIn("function registerQmlLoader", startup)
        self.assertIn("function unregisterQmlLoader", startup)
        self.assertIn('"qml_census": census', startup)
        self.assertIn("Component.onDestruction: ShellStartupService.unregisterQmlLoader", slot)
        self.assertIn("onItemChanged: ShellStartupService.updateQmlLoader", slot)

    def test_qml_census_registers_central_fileviews_and_picker_windows(self):
        startup = (ROOT / "services" / "ShellStartupService.qml").read_text(encoding="utf-8")
        state_projection = (ROOT / "services" / "StateProjection.qml").read_text(encoding="utf-8")
        plugin_settings = (ROOT / "services" / "PluginSettings.qml").read_text(encoding="utf-8")
        file_picker = (ROOT / "services" / "FilePickerWindow.qml").read_text(encoding="utf-8")

        self.assertIn('"windows": resourceCounts.window || 0', startup)
        self.assertIn('"fileviews": resourceCounts.fileview || 0', startup)
        for source, owner, object_name in (
            (state_projection, "StateProjection", "configFile"),
            (plugin_settings, "PluginSettings", "storeFile"),
        ):
            self.assertIn(
                f'ShellStartupService.registerQmlResource("{owner}", "fileview", {object_name})',
                source,
            )
            self.assertIn(
                f'ShellStartupService.unregisterQmlResource("{owner}", "fileview", {object_name})',
                source,
            )

        self.assertIn(
            'ShellStartupService.registerQmlResource("FilePickerWindow", "window", root)',
            file_picker,
        )
        self.assertIn(
            'ShellStartupService.unregisterQmlResource("FilePickerWindow", "window", root)',
            file_picker,
        )

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

    def test_live_telemetry_preserves_partial_loader_census_and_unknown_categories(self):
        with TempEnv():
            snapshot = runtime.parse_live_telemetry(
                '{"stage":"IPC_READY","qml_census":{"schema":1,"status":"partial",'
                '"units":{"loaded":2,"ids":["shell.bar","shell.keystone"]},'
                '"qml_resources":{"status":"partial","reason":"only loaders and delegates are instrumented",'
                '"counts":{"loaders":12,"delegates":5,"timers":null,"processes":null,'
                '"fileviews":null,"connections":null,"canvas":null,"layers":null,"windows":null}}}}',
                sampled_at_ms=9012,
            )

        self.assertEqual(snapshot["status"], "available")
        self.assertEqual(snapshot["qml_census"]["units"]["loaded"], 2)
        self.assertEqual(snapshot["qml_resources"]["status"], "partial")
        self.assertEqual(snapshot["qml_resources"]["counts"]["loaders"], 12)
        self.assertEqual(snapshot["qml_resources"]["counts"]["delegates"], 5)
        self.assertIsNone(snapshot["qml_resources"]["counts"]["timers"])

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

    def test_process_lifecycle_aggregates_observed_duration_relaunches_and_failures(self):
        with TempEnv():
            tracker = runtime.ProcessLifecycleTracker()
            tracker.observe((
                runtime.ProcessObservation(41, 100, "niri"),
                runtime.ProcessObservation(42, 200, "niri"),
            ), 50)
            tracker.observe((runtime.ProcessObservation(41, 100, "niri"),), 150)
            failures = (runtime.ProcessStartFailure(
                command="niri", category="required", reason="required_process_unavailable"
            ),)
            telemetry = tracker.report(failures)

        self.assertEqual(telemetry["launch_count"], 2)
        self.assertEqual(telemetry["restart_count"], 1)
        self.assertEqual(telemetry["failed_launch_count"], 1)
        processes = telemetry["processes"]
        self.assertEqual(
            [(row["pid"], row["observed_duration_ms"]) for row in processes],
            [(41, 100), (42, 0)],
        )
        self.assertTrue(all(row["duration_is_lower_bound"] for row in processes))
        self.assertTrue(all(row["owner"] is None for row in processes))
        self.assertEqual(telemetry["failed_launches"][0]["reason"], "required_process_unavailable")

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
