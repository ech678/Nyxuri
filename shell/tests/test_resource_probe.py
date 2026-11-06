"""Focused tests for the container resource probe and report."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = ROOT / "scripts" / "dev" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = _load("resource_probe")
report = _load("resource_report")


class ResourceProbeTests(unittest.TestCase):
    def test_scan_qml_resources_keeps_static_counts_per_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Main.qml").write_text(
                "pragma Singleton\nTimer { }\nProcess { }\nLoader { }\nCanvas { }\n",
                encoding="utf-8",
            )
            (root / "Other.js").write_text("// no runtime objects\n", encoding="utf-8")

            inventory = probe.scan_qml_resources(root)

        self.assertEqual(inventory["qml_js_files"], 2)
        self.assertEqual(inventory["counts"]["singletons"], 1)
        self.assertEqual(inventory["counts"]["timers"], 1)
        self.assertEqual(inventory["counts"]["processes"], 1)
        self.assertEqual(inventory["counts"]["loaders"], 1)
        self.assertEqual(inventory["counts"]["canvas"], 1)
        self.assertEqual(inventory["by_file"][0]["file"], "Main.qml")

    def test_sample_process_tree_observes_current_container_process(self):
        snapshot = probe.sample_process_tree(os.getpid())

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertGreaterEqual(snapshot.process_count, 1)
        self.assertGreaterEqual(snapshot.thread_count, 1)
        self.assertGreaterEqual(snapshot.rss_kb, 1)
        self.assertGreaterEqual(snapshot.user_cpu_ticks + snapshot.system_cpu_ticks, 0)

    def test_report_preserves_missing_values_and_computes_growth(self):
        summary = report.summarize({
            "schema": 1,
            "runtime": {"samples": [
                {"rss_kb": 10, "pss_kb": 8, "process_count": 1, "fd_count": 4},
                {"rss_kb": 13, "pss_kb": 9, "process_count": 2, "fd_count": 5},
            ]},
        })

        self.assertEqual(summary["sample_count"], 2)
        self.assertEqual(summary["resource_metrics"]["rss_kb"]["delta"], 3)
        self.assertEqual(summary["growth"]["process_count"], 1)
        self.assertIsNone(summary["resource_metrics"]["cgroup_memory_current_kb"]["median"])


if __name__ == "__main__":
    unittest.main()
