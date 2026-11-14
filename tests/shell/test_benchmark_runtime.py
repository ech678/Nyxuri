"""Focused contracts for runtime benchmark telemetry and failure gating."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time as wallclock
import unittest

_REAL_SLEEP = wallclock.sleep
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch

from tests.utils import TempEnv


ROOT = Path(__file__).resolve().parents[2] / "shell"
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
_RUNNER_SPEC = importlib.util.spec_from_file_location(
    "benchmark_shell", ROOT / "scripts" / "dev" / "benchmark-shell.py"
)
if _RUNNER_SPEC is None or _RUNNER_SPEC.loader is None:
    raise RuntimeError("cannot load benchmark-shell")
runner = importlib.util.module_from_spec(_RUNNER_SPEC)
sys.modules["benchmark_shell"] = runner
_RUNNER_SPEC.loader.exec_module(runner)
_COMPATIBILITY_SPEC = importlib.util.spec_from_file_location(
    "benchmark_compatibility", ROOT / "scripts" / "dev" / "benchmark_compatibility.py"
)
if _COMPATIBILITY_SPEC is None or _COMPATIBILITY_SPEC.loader is None:
    raise RuntimeError("cannot load benchmark_compatibility")
compatibility = importlib.util.module_from_spec(_COMPATIBILITY_SPEC)
sys.modules["benchmark_compatibility"] = compatibility
_COMPATIBILITY_SPEC.loader.exec_module(compatibility)


class CompositorStartupTests(unittest.TestCase):
    def test_layer_shell_compositor_uses_private_socket_and_fixed_mode(self):
        with TempEnv() as isolated:
            env = {"XDG_RUNTIME_DIR": str(isolated.home), "WAYLAND_DISPLAY": "unused"}
            process = Mock()
            def launch(*args, **kwargs):
                (isolated.home / "wayland-7").touch()
                return process
            with patch.dict(os.environ, {"NYXURI_CONTAINER": "1"}), patch.object(
                runtime.subprocess, "Popen", side_effect=launch
            ) as popen:
                self.assertIs(runtime.start_compositor(env, isolated.home), process)
            self.assertEqual(popen.call_args.args[0],
                             ["sway", "--unsupported-gpu", "-c", str(isolated.home / "sway.conf")])
            self.assertNotIn("shell", popen.call_args.kwargs)
            self.assertEqual(popen.call_args.kwargs["env"]["WLR_BACKENDS"], "headless")
            self.assertEqual(env["WAYLAND_DISPLAY"], "wayland-7")
            self.assertIn("1280x720@60Hz", (isolated.home / "sway.conf").read_text())


class BenchmarkRuntimeTests(unittest.TestCase):
    def test_profile_cli_defaults_to_full_and_accepts_each_named_profile(self):
        help_text = runner.build_parser().format_help()
        for profile in ("empty-shellroot", "minimal-nyxuri", "default-full"):
            self.assertIn(profile, help_text)

        defaults = runner.parse_args([])
        self.assertEqual(defaults.profiles, ["default-full"])
        selected = runner.parse_args([
            "--profile", "empty-shellroot", "--profile", "minimal-nyxuri",
        ])
        self.assertEqual(selected.profiles, ["empty-shellroot", "minimal-nyxuri"])

        scenario_help = scenarios.build_parser().format_help()
        for profile in ("empty-shellroot", "minimal-nyxuri", "default-full"):
            self.assertIn(profile, scenario_help)
        scenario_defaults = scenarios.parse_args(["--output", "/tmp/benchmark-raw.json"])
        self.assertEqual(scenario_defaults.profiles, ["default-full"])

    def test_profile_cli_rejects_unknown_and_duplicate_profiles(self):
        for argv in (
            ["--profile", "not-a-profile"],
            ["--profile", "default-full", "--profile", "default-full"],
        ):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    runner.parse_args(argv)
            self.assertEqual(raised.exception.code, 2)

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                scenarios.parse_args(["--output", "/tmp/benchmark-raw.json", "--profile", "not-a-profile"])
        self.assertEqual(raised.exception.code, 2)
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                scenarios.parse_args([
                    "--output", "/tmp/benchmark-raw.json",
                    "--profile", "empty-shellroot", "--profile", "empty-shellroot",
                ])
        self.assertEqual(raised.exception.code, 2)

    def test_profile_metadata_records_empty_and_minimal_runtime_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shell_root = root / "shell"
            shell_root.mkdir()
            (shell_root / "shell.qml").write_text(
                "import Quickshell\nShellRoot {}\n", encoding="utf-8"
            )
            for name in ("bar", "dock"):
                plugin = shell_root / "plugins" / name
                plugin.mkdir(parents=True)
                (plugin / "manifest.toml").write_text("name = 'fixture'\n", encoding="utf-8")
            profiles = root / "profiles"

            empty = scenarios.profile_metadata("empty-shellroot", shell_root, profiles)
            minimal = scenarios.profile_metadata("minimal-nyxuri", shell_root, profiles)
            full = scenarios.profile_metadata("default-full", shell_root, profiles)

            empty_source = Path(str(empty["config_path"])) / "shell.qml"
            self.assertEqual(empty_source.read_text(encoding="utf-8"), "import Quickshell\nShellRoot {}\n")
            self.assertNotIn("IpcHandler", empty_source.read_text(encoding="utf-8"))
            self.assertEqual(empty["ipc_status"], "unavailable")
            self.assertEqual(empty["unit_actions_status"], "unavailable")
            self.assertEqual(minimal["profile_id"], "minimal-nyxuri")
            self.assertEqual(minimal["config_path"], str(shell_root))
            self.assertEqual(minimal["disabled_unit_ids"], ["shell.bar", "shell.dock"])
            self.assertEqual(minimal["ipc_status"], "available")
            self.assertEqual(minimal["unit_actions_status"], "unavailable")
            self.assertEqual(full["profile_id"], "default-full")
            self.assertEqual(full["config_path"], str(shell_root))
            self.assertEqual(full["disabled_unit_ids"], [])
            self.assertEqual(full["unit_actions_status"], "available")
            full_contract = scenarios.default_full_profile_contract(
                full, empty, scenarios.ipc_reference_metadata(root / "ipc-reference")
            )
            raw_full = json.loads(json.dumps(full_contract))
            self.assertEqual(raw_full["baseline_reference"]["profile_id"], "empty-shellroot")
            self.assertEqual(
                raw_full["ipc_reference"]["profile_id"], "benchmark-ipc-reference"
            )
            self.assertEqual(
                raw_full["baseline_reference"]["identity"]["config_kind"],
                "generated_shellroot_without_handlers",
            )
            self.assertNotEqual(
                raw_full["ipc_reference"]["profile_id"],
                raw_full["baseline_reference"]["profile_id"],
            )

            ledger = scenarios.write_disabled_unit_ledger(
                root / "state", tuple(minimal["disabled_unit_ids"])
            )
            payload = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(payload, {
                "plugins": {
                    "shell.bar": {"state": "disabled"},
                    "shell.dock": {"state": "disabled"},
                }
            })

            scenario_args = scenarios.parse_args([
                "--output", str(root / "raw.json"), "--runs", "2",
            ])
            base_environment = {
                "HOME": str(root / "home"),
                "XDG_CACHE_HOME": str(root / "cache"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
                "XDG_STATE_HOME": str(root / "state-base"),
            }
            with (
                patch.object(scenarios, "WORKSPACE_SHELL_ROOT", shell_root),
                patch.object(scenarios, "startup_samples", return_value={"cold_start": [], "warm_start": []}),
            ):
                empty_record = scenarios.run_isolated_profile(
                    "empty-shellroot", scenario_args, base_environment, root / "profiles",
                )
            raw_profile = json.loads(json.dumps({"profiles": {"empty-shellroot": empty_record}}))
            self.assertEqual(
                raw_profile["profiles"]["empty-shellroot"]["identity"]["profile_id"],
                "empty-shellroot",
            )
            self.assertEqual(
                raw_profile["profiles"]["empty-shellroot"]["ipc"],
                {"status": "unavailable", "reason": "empty_shellroot_declares_no_ipc_handler"},
            )

            with (
                patch.object(scenarios, "WORKSPACE_SHELL_ROOT", shell_root),
                patch.object(scenarios, "startup_samples", return_value={"cold_start": [], "warm_start": []}),
                patch.object(scenarios, "ipc_benchmark", return_value={"metrics": {"errors": 0}}),
                patch.object(scenarios, "steady_state_benchmark", return_value={"status": "available"}),
            ):
                minimal_record = scenarios.run_isolated_profile(
                    "minimal-nyxuri", scenario_args, base_environment, root / "profiles",
                )
            raw_minimal = json.loads(json.dumps({"profiles": {"minimal-nyxuri": minimal_record}}))
            self.assertEqual(
                raw_minimal["profiles"]["minimal-nyxuri"]["identity"]["disabled_unit_ids"],
                ["shell.bar", "shell.dock"],
            )
            self.assertEqual(raw_minimal["profiles"]["minimal-nyxuri"]["ipc"]["status"], "available")
            self.assertEqual(
                raw_minimal["profiles"]["minimal-nyxuri"]["actions"],
                {"status": "unavailable", "reason": "all_first_party_units_disabled_by_profile"},
            )
            state_home = root / "state-base" / "minimal-nyxuri"
            for suffix in ("", "-0", "-1", "-2"):
                isolated_ledger = Path(f"{state_home}{suffix}") / "nyxuri" / "state.json"
                self.assertEqual(
                    json.loads(isolated_ledger.read_text(encoding="utf-8")),
                    payload,
                )

    def test_cgroup_memory_zero_missing_and_positive_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "proc" / "123"
            cgroup = root / "cgroup"
            proc.mkdir(parents=True)
            cgroup.mkdir()
            (proc / "cgroup").write_text("0::/scope\n", encoding="utf-8")
            group = cgroup / "scope"
            group.mkdir()
            (group / "memory.current").write_text("0\n", encoding="utf-8")
            (group / "memory.peak").write_text("8192\n", encoding="utf-8")

            current, peak = runtime._cgroup_memory(proc, cgroup)

        self.assertIsNone(current)
        self.assertEqual(peak, 8)

    def test_cgroup_memory_missing_files_are_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "proc" / "123"
            cgroup = root / "cgroup"
            proc.mkdir(parents=True)
            cgroup.mkdir()
            (proc / "cgroup").write_text("0::scope\n", encoding="utf-8")
            (cgroup / "scope").mkdir()

            current, peak = runtime._cgroup_memory(proc, cgroup)

        self.assertIsNone(current)
        self.assertIsNone(peak)

    def test_cgroup_memory_aggregation_ignores_none_and_keeps_all_none(self):
        def sample(current, peak):
            return runtime.ProcessSample(*([1] * 28), current, peak)

        mixed = [sample(None, None), sample(12, 20)]
        summary = runtime._sample_stat(mixed)
        peak = runtime._sample_peak(mixed)
        self.assertIsNotNone(summary)
        self.assertIsNotNone(peak)
        assert summary is not None
        assert peak is not None
        self.assertEqual(summary.cgroup_memory_current_kb, 12)
        self.assertEqual(summary.cgroup_memory_peak_kb, 20)
        self.assertEqual(peak.cgroup_memory_current_kb, 12)
        self.assertEqual(peak.cgroup_memory_peak_kb, 20)

        unavailable = runtime._sample_stat([sample(None, None)])
        unavailable_peak = runtime._sample_peak([sample(None, None)])
        assert unavailable is not None
        assert unavailable_peak is not None
        self.assertIsNone(unavailable.cgroup_memory_current_kb)
        self.assertIsNone(unavailable.cgroup_memory_peak_kb)
        self.assertIsNone(unavailable_peak.cgroup_memory_current_kb)
        self.assertIsNone(unavailable_peak.cgroup_memory_peak_kb)

    def _run_baseline_with_log(self, log_text):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_dir = root / "logs"
            log_dir.mkdir()

            class FakeProcess:
                pid = 12345
                returncode = None

                def poll(self):
                    return self.returncode

            def start_process(*_args, stdout, **_kwargs):
                stdout.write(log_text)
                stdout.flush()
                return FakeProcess()

            monotonic_ns = [1_000_000_000]
            if "REAL_FIRST_FRAME" in log_text:
                monotonic_ns.append(1_045_000_000)
            with (
                TempEnv(),
                patch.object(runtime.subprocess, "Popen", side_effect=start_process),
                patch.object(runtime, "_process_tree", return_value=None),
                patch.object(
                    runtime, "_terminate",
                    side_effect=lambda process: setattr(process, "returncode", 0),
                ),
                patch.object(runtime.time, "monotonic", side_effect=[0.0, 0.1, 0.2, 2.3, 2.4]),
                patch.object(runtime.time, "monotonic_ns", side_effect=monotonic_ns),
                patch.object(runtime.time, "sleep"),
            ):
                return runtime._run_process(
                    kind="baseline", run_number=1, environment={},
                    baseline_dir=root, log_dir=log_dir,
                )

    def _run_live_marker_script(self, body, *, release_partial=False):
        """Run the real polling loop against a short, independently scheduled child."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_dir = root / "logs"
            log_dir.mkdir()
            original_popen = runtime.subprocess.Popen
            log_path = log_dir / "baseline-1.log"
            child_holder = {}

            class PartialGate:
                def __init__(self, process):
                    self.process = process
                    self.released = False

                def poll(self):
                    if release_partial and not self.released and log_path.exists():
                        if log_path.read_text(encoding="utf-8", errors="replace") == "Configuration Loaded":
                            assert self.process.stdin is not None
                            self.process.stdin.write("\\n")
                            self.process.stdin.flush()
                            self.released = True
                    return self.process.poll()

                def __getattr__(self, name):
                    return getattr(self.process, name)

            def start_process(_command, *, stdout, stderr, start_new_session, text, **_kwargs):
                process = original_popen(
                    [sys.executable, "-u", "-c", body],
                    stdin=subprocess.PIPE,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=start_new_session,
                    text=text,
                )
                child_holder["process"] = process
                return PartialGate(process)

            virtual_time = [0.0]
            monotonic_ns = [1_000_000_000]

            def monotonic():
                virtual_time[0] += 0.1
                return virtual_time[0]

            def monotonic_clock_ns():
                monotonic_ns[0] += 45_000_000
                return monotonic_ns[0]

            with (
                patch.object(runtime.subprocess, "Popen", side_effect=start_process),
                patch.object(runtime, "_process_tree", return_value=None),
                patch.object(runtime.time, "monotonic", side_effect=monotonic),
                patch.object(runtime.time, "monotonic_ns", side_effect=monotonic_clock_ns),
                patch.object(runtime.time, "sleep", side_effect=lambda seconds: _REAL_SLEEP(0.001)),
            ):
                result = runtime._run_process(
                    kind="baseline", run_number=1, environment={},
                    baseline_dir=root, log_dir=log_dir,
                )
                child = child_holder.get("process")
                if child is not None and child.stdin is not None:
                    child.stdin.close()
                return result

    def test_live_child_marker_is_observed_while_process_is_running(self):
        result = self._run_live_marker_script(
            "import os, sys\nos.write(1, b'Configuration Loaded\\n')\n"
            "os.write(1, b'[ShellStartup] REAL_FIRST_FRAME source: live\\n')\n"
            "sys.stdin.buffer.read(1)\n"
        )
        self.assertIsNotNone(result.real_first_frame_wall_ms)
        self.assertEqual(result.real_first_frame_source, "live")
        self.assertEqual(result.real_first_frame_status, "available")

    def test_live_child_marker_first_visible_only_after_exit_has_null_wall_time(self):
        result = self._run_live_marker_script(
            "import os, signal, sys\n"
            "os.write(1, b'Configuration Loaded\\n')\n"
            "def done(_signum, _frame):\n"
            "    os.write(1, b'[ShellStartup] REAL_FIRST_FRAME source: exit\\n')\n"
            "    os._exit(0)\n"
            "signal.signal(signal.SIGTERM, done)\n"
            "sys.stdin.buffer.read(1)\n"
        )
        self.assertIsNone(result.real_first_frame_wall_ms)
        self.assertEqual(result.real_first_frame_source, "exit")
        self.assertEqual(result.real_first_frame_status, "observed_after_exit")

    def test_live_child_incomplete_line_is_recognized_after_newline(self):
        result = self._run_live_marker_script(
            "import os, sys\n"
            "os.write(1, b'Configuration Loaded')\n"
            "sys.stdin.buffer.read(1)\n"
            "os.write(1, b'\\n')\n"
            "os.write(1, b'[ShellStartup] REAL_FIRST_FRAME source: completed\\n')\n"
            "sys.stdin.buffer.read(1)\n",
            release_partial=True,
        )
        self.assertTrue(result.marker)
        self.assertEqual(result.real_first_frame_source, "completed")
        self.assertEqual(result.real_first_frame_status, "available")

    def test_live_child_without_or_with_legacy_marker_is_unavailable(self):
        for marker in (b"", b"[ShellStartup] Stage transition -> FIRST_FRAME (elapsed: 1ms)\n"):
            with self.subTest(marker=marker):
                result = self._run_live_marker_script(
                    "import os, sys\n"
                    f"os.write(1, {marker!r})\n"
                    "sys.stdin.buffer.read(1)\n"
                )
                self.assertIsNone(result.real_first_frame_wall_ms)
                self.assertIsNone(result.real_first_frame_source)
                self.assertEqual(result.real_first_frame_status, "unavailable")

    def test_run_process_records_first_real_frame_with_runner_monotonic_clock(self):
        result = self._run_baseline_with_log(
            "Configuration Loaded\n"
            "[ShellStartup] REAL_FIRST_FRAME source: QQuickWindow.frameSwapped "
            "(elapsed: 27ms)\n"
        )

        self.assertEqual(result.real_first_frame_wall_ms, 45.0)
        self.assertEqual(result.real_first_frame_source, "QQuickWindow.frameSwapped")
        self.assertEqual(result.real_first_frame_status, "available")
        self.assertIsNone(result.internal_ms.get("real_first_frame_ms"))

    def test_run_process_marks_missing_real_first_frame_unavailable(self):
        result = self._run_baseline_with_log("Configuration Loaded\n")

        self.assertIsNone(result.real_first_frame_wall_ms)
        self.assertIsNone(result.real_first_frame_source)
        self.assertEqual(result.real_first_frame_status, "unavailable")

    def test_run_process_ignores_legacy_first_frame_marker(self):
        result = self._run_baseline_with_log(
            "Configuration Loaded\n"
            "[ShellStartup] Stage transition -> FIRST_FRAME (elapsed: 11ms)\n"
        )

        self.assertIsNone(result.real_first_frame_wall_ms)
        self.assertIsNone(result.real_first_frame_source)
        self.assertEqual(result.real_first_frame_status, "unavailable")

    def test_real_first_frame_parser_uses_explicit_event_and_keeps_legacy_separate(self):
        log = (
            "[ShellStartup] Stage transition -> FIRST_FRAME (elapsed: 11ms)\\n"
            "[ShellStartup] REAL_FIRST_FRAME source: QQuickWindow.frameSwapped "
            "(elapsed: 27ms)\\n"
        )
        parsed = scenarios.parse_real_first_frame(log)
        self.assertEqual(parsed["real_first_frame_ms"], 27.0)
        self.assertEqual(parsed["real_first_frame_source"], "QQuickWindow.frameSwapped")
        self.assertNotIn("real_first_frame_status", parsed)
        self.assertNotIn("real_first_frame_wall_status", parsed)

    def test_real_first_frame_parser_marks_missing_event_unavailable(self):
        parsed = scenarios.parse_real_first_frame(
            "[ShellStartup] Stage transition -> FIRST_FRAME (elapsed: 11ms)\\n"
        )
        self.assertIsNone(parsed["real_first_frame_ms"])
        self.assertIsNone(parsed["real_first_frame_source"])
        self.assertNotIn("real_first_frame_status", parsed)

    def _startup_record_fixture(self, log_text, *, wall_ms, source, status):
        run = runtime.RunResult(
            marker=True, startup_ms=10.0,
            real_first_frame_wall_ms=wall_ms,
            real_first_frame_source=source, real_first_frame_status=status,
            internal_ms={"first_frame_ms": 11.0}, steady=None, peak=None,
            cpu_ms=None, user_cpu_ms=None, system_cpu_ms=None, cpu_util_percent=None,
            log_errors=0, log_warnings=0, fatal_log_count=0, compiled_empty=0,
            process_start_failures=0, optional_process_start_failures=0,
            required_process_start_failures=0, unattributed_process_start_failures=0,
            process_start_failure_details=(), process_lifecycle={}, live_telemetry=None,
            exit_code=0, startup_valid=True, sample_valid=True,
            controlled_shutdown=True, success=True, log_path="/results/startup.log",
        )
        with TempEnv(), patch.object(Path, "read_text", autospec=True, return_value=log_text) as read:
            record = scenarios._startup_record(run, "empty-shellroot")
            read.assert_called_once_with(Path("/results/startup.log"), errors="replace")
        self.assertEqual(record["profile_id"], "empty-shellroot")
        self.assertEqual(record["log_path"], "startup.log")
        return record

    def test_startup_record_keeps_post_exit_wall_status_with_qml_marker(self):
        record = self._startup_record_fixture(
            "[ShellStartup] REAL_FIRST_FRAME source: qml-frame (elapsed: 27ms)\n",
            wall_ms=None, source="runner-post-exit", status="observed_after_exit",
        )
        self.assertEqual(record["real_first_frame_ms"], 27.0)
        self.assertEqual(record["real_first_frame_source"], "qml-frame")
        self.assertIsNone(record["real_first_frame_wall_ms"])
        self.assertEqual(record["real_first_frame_wall_source"], "runner-post-exit")
        self.assertEqual(record["real_first_frame_wall_status"], "observed_after_exit")
        self.assertEqual(record["real_first_frame_status"], "observed_after_exit")

    def test_startup_record_keeps_live_wall_observation_separate_from_qml(self):
        for log_text, qml_ms, qml_source in (
            ("[ShellStartup] REAL_FIRST_FRAME source: qml-frame (elapsed: 27ms)\n", 27.0, "qml-frame"),
            ("Configuration Loaded\n", None, None),
        ):
            with self.subTest(log_text=log_text):
                record = self._startup_record_fixture(
                    log_text, wall_ms=45.0, source="runner-live", status="available",
                )
                self.assertEqual(record["real_first_frame_ms"], qml_ms)
                self.assertEqual(record["real_first_frame_source"], qml_source)
                self.assertEqual(record["real_first_frame_wall_ms"], 45.0)
                self.assertEqual(record["real_first_frame_wall_source"], "runner-live")
                self.assertEqual(record["real_first_frame_wall_status"], "available")
                self.assertEqual(record["real_first_frame_status"], "available")

    def test_startup_record_without_baseline_marker_is_unavailable(self):
        record = self._startup_record_fixture(
            "Configuration Loaded\n"
            "[ShellStartup] Stage transition -> FIRST_FRAME (elapsed: 11ms)\n",
            wall_ms=None, source=None, status="unavailable",
        )
        for field in ("real_first_frame_ms", "real_first_frame_source",
                      "real_first_frame_wall_ms", "real_first_frame_wall_source"):
            self.assertIsNone(record[field])
        self.assertEqual(record["real_first_frame_wall_status"], "unavailable")
        self.assertEqual(record["real_first_frame_status"], "unavailable")

    def test_report_excludes_post_exit_and_nonavailable_wall_values(self):
        with TempEnv():
            built = report.build_report({
                "baseline": [{"real_first_frame_wall_status": "unavailable"}],
                "cold_start": [
                    {"real_first_frame_wall_ms": 45.0, "real_first_frame_wall_status": "available"},
                    {"real_first_frame_ms": 27.0, "real_first_frame_wall_ms": None,
                     "real_first_frame_wall_status": "observed_after_exit"},
                    {"real_first_frame_wall_ms": 999.0,
                     "real_first_frame_wall_status": "observed_after_exit"},
                    {"real_first_frame_wall_ms": 888.0, "real_first_frame_wall_status": "unavailable"},
                    {"real_first_frame_wall_ms": 777.0},
                    {"real_first_frame_wall_ms": None, "real_first_frame_wall_status": "available"},
                ],
                "warm_start": [{"real_first_frame_wall_status": "observed_after_exit"}],
            })
        summary = built["raw"]["cold_start"]
        self.assertEqual(summary["real_first_frame_wall_ms"], {
            "n": 1, "p50": 45.0, "p95": 45.0, "p99": 45.0, "min": 45.0, "max": 45.0,
        })
        self.assertEqual(summary["real_first_frame_wall_observations"], {
            "available": 2, "unavailable": 1, "observed_after_exit": 2,
        })
        self.assertEqual(summary["real_first_frame_ms"]["p50"], 27.0)
        self.assertEqual(built["normalized"]["internal_shell_ms"]["real_first_frame_wall"], 45.0)
        self.assertEqual(built["raw"]["warm_start"]["real_first_frame_wall_ms"]["n"], 0)
        self.assertIsNone(built["raw"]["baseline"]["real_first_frame_wall_ms"]["p50"])

    def test_report_summarizes_real_first_frame_without_replacing_legacy_field(self):
        built = report.build_report({
            "baseline": [],
            "cold_start": [{
                "real_first_frame_ms": 27.0,
                "real_first_frame_wall_ms": 45.0,
                "real_first_frame_wall_status": "available",
                "internal_ms": {"first_frame_ms": 11.0},
            }],
            "warm_start": [],
        })
        self.assertEqual(
            built["raw"]["cold_start"]["real_first_frame_ms"]["p50"], 27.0
        )
        self.assertEqual(
            built["normalized"]["internal_shell_ms"]["first_frame"], 11.0
        )
        self.assertEqual(
            built["normalized"]["internal_shell_ms"]["real_first_frame"], 27.0
        )
        self.assertEqual(
            built["raw"]["cold_start"]["real_first_frame_wall_ms"]["p50"], 45.0
        )
        self.assertEqual(
            built["normalized"]["internal_shell_ms"]["real_first_frame_wall"], 45.0
        )

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

    def test_report_preserves_profile_only_data_and_explicit_unavailable_metrics(self):
        raw = {
            "schema": 3,
            "selected_profiles": ["minimal-nyxuri"],
            "runtime": {"runs": 2, "ipc_runs": 1},
            "profiles": {
                "minimal-nyxuri": {
                    "identity": {
                        "profile_id": "minimal-nyxuri",
                        "meaning": "Production host with all first-party units disabled.",
                        "ipc_status": "available",
                        "unit_actions_unavailable_reason": "all_first_party_units_disabled_by_profile",
                    },
                    "startup": {
                        "cold_start": [{
                            "startup_ms": 245.5,
                            "internal_ms": {"first_frame_ms": 190.0},
                            "success": True,
                        }],
                        "warm_start": [],
                    },
                    "ipc": {"status": "available", "shell": {"stage": {"p50_ms": 1.2}}},
                    "actions": {
                        "status": "unavailable",
                        "reason": "all_first_party_units_disabled_by_profile",
                    },
                    "long_steady_state": {
                        "status": "unavailable",
                        "reason": "not_requested",
                    },
                    "reclamation": {
                        "status": "unavailable",
                        "reason": "all_first_party_units_disabled_by_profile",
                    },
                    "frame_profile": {
                        "status": "unavailable",
                        "reason": "standalone_frame_probe_does_not_execute_this_profile",
                    },
                }
            },
        }

        built = report.build_report(raw)
        profile = built["raw"]["profiles"]["minimal-nyxuri"]
        normalized = built["normalized"]["profiles"]["minimal-nyxuri"]

        self.assertEqual(profile["startup"]["cold_start"]["summary"]["startup_ms"]["p50"], 245.5)
        self.assertEqual(profile["startup"]["cold_start"]["runs"], 1)
        self.assertEqual(profile["startup"]["warm_start"]["status"], "unavailable")
        self.assertEqual(profile["ipc"]["status"], "available")
        self.assertEqual(profile["actions"]["status"], "unavailable")
        self.assertEqual(
            profile["actions"]["reason"], "all_first_party_units_disabled_by_profile"
        )
        self.assertIsNone(normalized["composite_score_0_100"])
        self.assertEqual(normalized["status"], "unavailable")
        self.assertIn("minimal-nyxuri", report.markdown(built))
        html = report.render_html(raw, built)
        self.assertIn("Profile summaries", html)
        self.assertIn("all_first_party_units_disabled_by_profile", html)
        self.assertIn(">N/A</strong>", html)

    def test_report_keeps_empty_startup_baseline_separate_from_ipc_reference(self):
        raw = {
            "selected_profiles": ["default-full"],
            "baseline": [{"startup_ms": 30.0}],
            "cold_start": [{"startup_ms": 60.0}],
            "warm_start": [],
            "ipc": {"baseline": {"ping": {"p50_ms": 1.0}}, "shell": {}},
            "profiles": {
                "default-full": {
                    "identity": {"profile_id": "default-full"},
                    "baseline_reference": {
                        "profile_id": "empty-shellroot",
                        "identity": {"config_kind": "generated_shellroot_without_handlers"},
                    },
                    "ipc_reference": {
                        "profile_id": "benchmark-ipc-reference",
                        "meaning": "Single handler for IPC calibration only.",
                    },
                    "raw_paths": {"baseline": "$.baseline", "cold_start": "$.cold_start"},
                }
            },
        }

        profile = report.build_report(raw)["raw"]["profiles"]["default-full"]

        self.assertEqual(profile["startup"]["baseline"]["profile_id"], "empty-shellroot")
        self.assertEqual(
            profile["startup"]["baseline"]["identity"]["config_kind"],
            "generated_shellroot_without_handlers",
        )
        self.assertEqual(profile["ipc_reference"]["profile_id"], "benchmark-ipc-reference")
        self.assertNotEqual(
            profile["startup"]["baseline"]["profile_id"],
            profile["ipc_reference"]["profile_id"],
        )

    def test_compatibility_cli_rejects_direct_host_invocation_before_qs_lookup(self):
        stderr = io.StringIO()
        with (
            patch.dict("os.environ", {"NYXURI_CONTAINER": "0"}),
            patch.object(sys, "argv", ["benchmark_compatibility.py", "--output", "/tmp/compat.json"]),
            patch.object(
                compatibility.shutil, "which", side_effect=AssertionError("qs lookup bypassed container gate")
            ) as which,
            redirect_stderr(stderr),
        ):
            with self.assertRaises(SystemExit) as raised:
                compatibility.main()

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("private container", stderr.getvalue())
        which.assert_not_called()

    def test_benchmark_environment_is_allowlisted_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            qml_root = Path(directory) / "qt-qml"
            qml_root.mkdir()
            with patch.dict(
                "os.environ",
                {
                    "PATH": "/nix/var/nix/profiles/default/bin",
                    "HOME": "/host/home",
                    "DISPLAY": ":99",
                    "SSH_AUTH_SOCK": "/host/agent.sock",
                    "WAYLAND_DISPLAY": "host-wayland",
                    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
                },
                clear=True,
            ):
                isolated = scenarios.environment(qml_root=qml_root)

        self.assertEqual(isolated["HOME"], "/tmp/nyxuri-home")
        self.assertNotIn("DISPLAY", isolated)
        self.assertNotIn("SSH_AUTH_SOCK", isolated)
        self.assertEqual(isolated["WAYLAND_DISPLAY"], "nyxuri-benchmark-wayland")
        self.assertNotIn("DBUS_SESSION_BUS_ADDRESS", isolated)
        self.assertEqual(isolated["LANG"], "C.UTF-8")
        self.assertEqual(isolated["TZ"], "UTC")
        self.assertEqual(isolated["PYTHONHASHSEED"], "0")
        self.assertEqual(isolated["QT_HASH_SEED"], "0")

    def test_environment_fingerprint_declares_container_scope_and_unavailable_display_mode(self):
        fingerprint = scenarios.container_environment_fingerprint(
            {
                "HOME": "/tmp/nyxuri-home",
                "XDG_RUNTIME_DIR": "/tmp/nyxuri-runtime",
                "XDG_CACHE_HOME": "/tmp/nyxuri-cache",
                "XDG_CONFIG_HOME": "/tmp/nyxuri-config",
                "XDG_DATA_HOME": "/tmp/nyxuri-data",
                "XDG_STATE_HOME": "/tmp/nyxuri-state",
                "WAYLAND_DISPLAY": "nyxuri-benchmark-wayland",
                "QT_QUICK_BACKEND": "software",
                "QSG_RHI_BACKEND": "software",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "LC_CTYPE": "C.UTF-8",
                "LANGUAGE": "C",
                "TZ": "UTC",
                "PYTHONHASHSEED": "0",
                "QT_HASH_SEED": "0",
                "SOURCE_DATE_EPOCH": "0",
            },
            {"container_digest": "sha256:test", "weston_backend": "headless", "renderer": "pixman"},
        )
        self.assertEqual(fingerprint["scope"], "container-process-tree")
        self.assertEqual(fingerprint["proc_scope"], "private-pid-namespace")
        self.assertEqual(fingerprint["screen"]["status"], "unavailable")
        self.assertEqual(fingerprint["timezone"], "UTC")
        self.assertEqual(fingerprint["random_seed"]["QT_HASH_SEED"], "0")
        self.assertEqual(fingerprint["container_digest"], "sha256:test")

    def test_qml_census_contract_is_live_and_tears_down_loader_records(self):
        startup = (ROOT / "services" / "ShellStartupService.qml").read_text(encoding="utf-8")
        self.assertIn("function registerQmlLoader", startup)
        self.assertIn("function unregisterQmlLoader", startup)
        self.assertIn('"qml_census": census', startup)
        shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
        self.assertIn("Repeater", shell)
        self.assertIn("delegate: Loader", shell)

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

    def test_live_telemetry_preserves_registered_timer_process_running_states(self):
        with TempEnv():
            snapshot = runtime.parse_live_telemetry(
                '{"stage":"READY","qml_resources":{"counts":{"loaders":1,"timers":1,'
                '"processes":1,"fileviews":0,"connections":0,"delegates":1,'
                '"canvas":2,"layers":1,"windows":0},"states":{'
                '"timer":{"total":1,"running":1,"stopped":0,"unknown":0},'
                '"process":{"total":1,"running":0,"stopped":1,"unknown":0}},'
                '"state_owners":{"ResourceProbe":{"timer":{"total":1,"running":1,'
                '"stopped":0,"unknown":0},"process":{"total":1,"running":0,'
                '"stopped":1,"unknown":0}}}}}',
                sampled_at_ms=6789,
            )

        resources = snapshot["qml_resources"]
        self.assertEqual(resources["status"], "available")
        self.assertEqual(resources["states_status"], "available")
        self.assertEqual(resources["states"]["timer"]["running"], 1)
        self.assertEqual(resources["states"]["process"]["stopped"], 1)
        self.assertEqual(resources["state_owners"]["ResourceProbe"]["timer"]["total"], 1)

    def test_live_telemetry_does_not_upgrade_invalid_running_states_to_available(self):
        with TempEnv():
            snapshot = runtime.parse_live_telemetry(
                '{"qml_resources":{"counts":{"loaders":1,"timers":1,'
                '"processes":1,"fileviews":0,"connections":0,"delegates":1,'
                '"canvas":2,"layers":1,"windows":0},"states":{'
                '"timer":{"total":1,"running":2,"stopped":0,"unknown":0},'
                '"process":{"total":1,"running":0,"stopped":0,"unknown":2}}}}',
                sampled_at_ms=6790,
            )

        resources = snapshot["qml_resources"]
        self.assertEqual(resources["states_status"], "invalid")
        self.assertEqual(resources["status"], "invalid")
        self.assertEqual(resources["reason"], "invalid_resource_running_states")
        self.assertIsNone(resources["states"]["timer"])
        self.assertIsNone(resources["states"]["process"])

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
