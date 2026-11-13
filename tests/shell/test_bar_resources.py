"""Behavior checks for the M3 bar resource consumer and swap snapshot parser.

The tests execute production JavaScript with a controlled service boundary; they
cover lease transitions and /proc parsing, not Qt signal dispatch or rendering.
"""

import re
import shutil
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path

from tests.utils import TempEnv

ROOT = Path(__file__).resolve().parents[2]
MONITOR = (ROOT / "shell/plugins/bar/ResourceUsageMonitor.qml").read_text(encoding="utf-8")
SERVICE = (ROOT / "shell/services/SystemMonitorService.qml").read_text(encoding="utf-8")


def extract_function(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                signature = source[start:opening]
                signature = re.sub(r":\s*(?:void|bool|real|int)\s*$", " ", signature)
                return signature + source[opening:index + 1]
    raise ValueError("unterminated QML function " + name)


@unittest.skipUnless(shutil.which("node"), "node is required for isolated JS behavior tests")
class BarResourceBehaviorTests(unittest.TestCase):
    def run_node(self, source: str) -> None:
        with TempEnv() as env:
            with patch("subprocess.run", wraps=subprocess.run) as runner:
                result = subprocess.run(
                    ["node", "-e", source], cwd=env.home, capture_output=True,
                    text=True, check=False, timeout=10
                )
                self.assertEqual(runner.call_args.args[0], ["node", "-e", source])
                self.assertNotIn("shell", runner.call_args.kwargs)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_resource_monitor_acquires_only_while_visible_and_releases_on_hide(self):
        function = extract_function(MONITOR, "sync")
        script = """
const assert = require('node:assert/strict');
const calls = [];
const SystemMonitorService = {
  setConsumerModules: (owner, modules) => calls.push(['set', owner, modules.slice()]),
  clearConsumer: owner => calls.push(['clear', owner])
};
""" + function + """
const root = {ownerId:'shell.bar.resources', modules:['cpu','memory','disk'],
              monitoring:true, _holding:false, _heldOwner:'', _heldModules:'', _instanceId:'test'};
root.sync = sync;
root.sync();
assert.deepEqual(calls, [['set','shell.bar.resources:test',['cpu','memory','disk']]]);
root.sync();
assert.equal(calls.length, 1, 'same lease state must be idempotent');
root.monitoring = false;
root.sync();
assert.deepEqual(calls.at(-1), ['clear','shell.bar.resources:test']);
root.sync();
assert.equal(calls.length, 2, 'repeated hidden update must not double-release');
root.monitoring = true;
root.sync();
assert.equal(calls.at(-1)[0], 'set');
root.modules = ['memory']; root.sync();
assert.deepEqual(calls.at(-1), ['set','shell.bar.resources:test',['memory']]);
root.ownerId = 'replacement'; root.sync();
assert.deepEqual(calls.slice(-2), [['clear','shell.bar.resources:test'], ['set','replacement:test',['memory']]]);
root.ownerId = ''; root.sync();
assert.deepEqual(calls.at(-1), ['clear','replacement:test']);
assert.equal(root._holding, false);
"""
        self.run_node(script)

    def test_multi_output_consumers_receive_distinct_ids(self):
        self.run_node("""
const assert = require('node:assert/strict');
const root = {_consumerSequence: 0};
""" + extract_function(SERVICE, "allocateConsumerId") + """
assert.equal(allocateConsumerId('bar-resource'), 'bar-resource:1');
assert.equal(allocateConsumerId('bar-resource'), 'bar-resource:2');
assert.equal(allocateConsumerId('popup'), 'popup:3');
""")

    def test_swap_parser_handles_values_and_no_swap(self):
        function = extract_function(SERVICE, "_readSwapMeminfo")
        script = """
const assert = require('node:assert/strict');
const root = {swapTotalBytes:0, swapUsedBytes:0};
""" + function + """
root._readSwapMeminfo = _readSwapMeminfo;
root._readSwapMeminfo('MemTotal: 8000000 kB\\nSwapTotal: 2000000 kB\\nSwapFree: 750000 kB\\n');
assert.equal(root.swapTotalBytes, 2048000000);
assert.equal(root.swapUsedBytes, 1280000000);
root._readSwapMeminfo('MemTotal: 8000000 kB\\nSwapTotal: 0 kB\\nSwapFree: 0 kB\\n');
assert.equal(root.swapTotalBytes, 0);
assert.equal(root.swapUsedBytes, 0);
root._readSwapMeminfo('MemTotal: 8000000 kB\\n');
assert.equal(root.swapTotalBytes, 0);
assert.equal(root.swapUsedBytes, 0);
"""
        self.run_node(script)

    def test_bar_resources_use_the_shared_monitor_without_legacy_service(self):
        resources = (ROOT / "shell/plugins/bar/Resources.qml").read_text(encoding="utf-8")
        popup = (ROOT / "shell/plugins/bar/ResourcesPopup.qml").read_text(encoding="utf-8")
        self.assertIn('ownerId: "shell.bar.resources"', resources)
        self.assertIn('ownerId: "shell.bar.resources-popup"', popup)
        self.assertNotIn("ResourceUsage.", resources + popup)
        self.assertIn("SystemMonitorService.setConsumerModules", MONITOR)


if __name__ == "__main__":
    unittest.main()
