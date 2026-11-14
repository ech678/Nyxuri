"""Execute FontService's real JS and startup queue without a GUI.

Qt font enumeration and callLater are controlled substitutes. This covers the
model/queue behavior, not QML binding notifications or rendered font metrics.
"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv

ROOT = Path(__file__).resolve().parents[2]
FONT = (ROOT / "shell/services/FontService.qml").read_text(encoding="utf-8")
STARTUP = (ROOT / "shell/services/ShellStartupService.qml").read_text(encoding="utf-8")


def block(text, start):
    opening = text.index("{", start)
    depth = 0
    for end in range(opening, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                return text[opening:end + 1]
    raise ValueError("unclosed JavaScript block")


def function(text, name):
    start = text.index("function " + name + "(")
    signature = text[start:text.index("{", start)]
    return re.sub(r"\):\s*(?:bool|void)\s*$", ") ", signature) + block(text, start)


@unittest.skipUnless(shutil.which("node"), "node is needed for isolated JS behavior tests")
class FontStartupTests(unittest.TestCase):
    def run_js(self, steps):
        font_functions = ["familyAvailable", "resolveFirstAvailable", "isTechnicalFamily",
                          "refresh", "containsFamily", "setConfiguredFamily"]
        queue_functions = ["scheduleBackground", "cancelBackground", "_scheduleBackgroundPump",
                           "_runBackgroundTask", "_updateBackgroundMetric", "_logBackgroundTask", "recordRealFirstFrame"]
        declarations = []
        for name in ["_initialFamilyList", "_familySet", "_initialRefreshPending", "availableFamilies"]:
            expression = re.search(r"property (?:var|bool) " + name + r": (.+)", FONT).group(1)
            declarations.append("root." + name + " = " + expression + ";")
        handler = FONT.split("Component.onCompleted:", 1)[1].rsplit("}", 1)[0].strip()
        script = """
const assert = require('node:assert/strict');
const output = console.log.bind(console);
const logs = [];
console.log = (...args) => logs.push(args.join(' '));
let now = 1000;
Date.now = () => now;
let calls = 0;
let families = ['Zulu', 'Alpha', 'Alpha', ' Material ', '.Hidden', '',
                'Material Symbols Rounded', 'Google Sans Flex'];
const turns = [];
const Qt = {fontFamilies: () => { calls++; return families.slice(); },
            callLater: callback => turns.push(callback)};
const root = {technicalFamilies: ['Material'], bundledExpressiveFamily: 'Google Sans Flex',
              configuredUi: '', configuredMono: '', configuredNumeric: '', configuredExpressive: ''};
""" + "\n".join(declarations)
        for name in font_functions:
            script += "\n" + function(FONT, name) + "\nroot." + name + " = " + name + ";"
        script += """
const fontRoot = root;
const ShellStartupService = (() => {
const root = {_backgroundQueue: [], _backgroundTaskStates: {}, backgroundRunning: false,
              backgroundMetrics: [], _backgroundPumpScheduled: false, _destroyed: false,
              _backgroundTaskRunning: false, _realFirstFrameRecorded: false, realFirstFrameTimestampMs: 0,
              initTimestampMs: Date.now(), realFirstFrameSource: ''};
"""
        for name in queue_functions:
            script += "\n" + function(STARTUP, name) + "\nroot." + name + " = " + name + ";"
        script += "\nreturn root;\n})();\nconst complete = () => {" + handler + "};\n"
        script += "const drain = () => { ShellStartupService.recordRealFirstFrame('test-window'); while (turns.length) turns.shift()(); };\n"
        script += steps + "\noutput(JSON.stringify({ok: true}));\n"
        with TempEnv() as env:
            with patch("subprocess.run", wraps=subprocess.run) as runner:
                result = subprocess.run(["node", "-"], input=script, text=True, capture_output=True,
                                        check=False, cwd=env.home, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(runner.call_args.args[0], ["node", "-"])
                self.assertNotIn("shell", runner.call_args.kwargs)
        self.assertEqual(json.loads(result.stdout), {"ok": True}, result.stderr)

    def test_initial_roles_available_while_settings_model_waits(self):
        self.run_js("""
assert.equal(calls, 1);
assert.equal(root.familyAvailable('Alpha'), true);
assert.equal(root.resolveFirstAvailable(['Missing', 'Alpha'], 'fallback'), 'Alpha');
complete();
assert.deepEqual(root.availableFamilies, []);
assert.equal(root._initialRefreshPending, true);
assert.equal(ShellStartupService._backgroundTaskStates['font-options'], 'queued');
assert.equal(turns.length, 0);
assert.equal(calls, 1);
""")

    def test_queue_builds_filtered_sorted_model_once(self):
        self.run_js("""
complete(); complete();
assert.equal(turns.length, 0);
ShellStartupService.recordRealFirstFrame('window');
ShellStartupService.recordRealFirstFrame('duplicate');
assert.equal(ShellStartupService.realFirstFrameSource, 'window');
assert.equal(turns.length, 1);
drain();
assert.deepEqual(root.availableFamilies, ['Alpha', 'Google Sans Flex', 'Zulu']);
assert.equal(root._initialRefreshPending, false);
assert.equal(calls, 1);
assert.equal(ShellStartupService._backgroundTaskStates['font-options'], 'completed');
assert.equal(ShellStartupService.backgroundMetrics.length, 1);
assert.equal(ShellStartupService.backgroundMetrics[0].error, '');
assert.equal(ShellStartupService.backgroundRunning, false);
""")

    def test_early_font_validation_retains_original_acceptance(self):
        self.run_js("""
complete();
assert.equal(root.containsFamily(' Alpha '), true);
assert.equal(root.containsFamily('Material Symbols Rounded'), false);
assert.equal(root.containsFamily('Missing'), false);
assert.equal(root.setConfiguredFamily('ui', 'Alpha'), true);
const model = root.availableFamilies;
drain();
assert.equal(root.availableFamilies, model);
assert.equal(root.configuredUi, 'Alpha');
assert.equal(calls, 1);
""")

    def test_explicit_refresh_before_queue_avoids_duplicate_work(self):
        self.run_js("""
complete(); root.refresh();
const model = root.availableFamilies;
drain();
assert.equal(root.availableFamilies, model);
assert.equal(calls, 1);
""")

    def test_later_refresh_reenumerates_and_replaces_model(self):
        self.run_js("""
complete(); drain();
const old = root.availableFamilies;
families = ['New Font', 'Alpha'];
root.refresh();
assert.equal(calls, 2);
assert.notEqual(root.availableFamilies, old);
assert.deepEqual(old, ['Alpha', 'Google Sans Flex', 'Zulu']);
assert.deepEqual(root.availableFamilies, ['Alpha', 'New Font']);
assert.equal(root.familyAvailable('New Font'), true);
assert.equal(root.familyAvailable('Zulu'), false);
""")

    def test_select_label_survives_empty_to_populated_model(self):
        select = (ROOT / "shell/ui/SplitMenuButton.qml").read_text(encoding="utf-8")
        self.run_js(function(select, "labelFor") + """
let model = [];
const savedValue = 'Alpha';
complete();
assert.equal(labelFor(savedValue), savedValue);
drain();
model = root.availableFamilies.map(family => ({value: family, label: family}));
assert.equal(labelFor(savedValue), savedValue);
assert.equal(labelFor('Unavailable saved family'), 'Unavailable saved family');
assert.deepEqual(model.map(option => option.value), ['Alpha', 'Google Sans Flex', 'Zulu']);
""")

    def test_queue_is_gated_fifo_one_task_per_turn_and_recovers_after_failure(self):
        self.run_js("""
const order = [];
ShellStartupService.scheduleBackground('one', () => order.push(1));
ShellStartupService.scheduleBackground('bad', () => { order.push(2); throw Error('broken'); });
ShellStartupService.scheduleBackground('three', () => order.push(3));
assert.equal(turns.length, 0);
ShellStartupService.recordRealFirstFrame('window');
assert.equal(turns.length, 1);
turns.shift()(); assert.deepEqual(order, [1]); assert.equal(turns.length, 1);
turns.shift()(); assert.deepEqual(order, [1, 2]);
assert.equal(ShellStartupService._backgroundTaskStates.bad, 'failed'); assert.equal(turns.length, 1);
turns.shift()(); assert.deepEqual(order, [1, 2, 3]);
assert.equal(ShellStartupService.backgroundRunning, true);
turns.shift()(); assert.equal(ShellStartupService.backgroundRunning, false);
""")

    def test_task_timeline_and_logs_share_first_frame_clock(self):
        self.run_js("""
const service = ShellStartupService;
now = 1010;
service.scheduleBackground('timed', () => {
    assert.equal(service.backgroundMetrics[0].status, 'running');
    assert.equal(service.backgroundMetrics[0].started_ms, 35);
    assert.equal(service.backgroundMetrics[0].finished_ms, null);
    assert.equal(service._backgroundTaskStates.timed, 'running');
    assert.equal(service.scheduleBackground('timed', () => assert.fail('duplicate')), false);
    service._runBackgroundTask(); // Reentrant pumping must not run the next task.
    assert.equal(service.backgroundMetrics[1].status, 'scheduled');
    now = 1042;
});
now = 1012;
service.scheduleBackground('next', () => { now = 1050; });
assert.deepEqual(service.backgroundMetrics[0], {
    name: 'timed', status: 'scheduled', queued_ms: 10,
    started_ms: null, finished_ms: null, elapsed_ms: null, error: '', reason: ''
});
service._runBackgroundTask(); // Even direct calls cannot bypass the frame gate.
assert.equal(service.backgroundMetrics[0].started_ms, null);
assert.equal(logs.length, 0);
now = 1030;
service.recordRealFirstFrame('test-window');
const frameMs = service.realFirstFrameTimestampMs - service.initTimestampMs;
now = 1035;
turns.shift()();
assert.equal(service.backgroundMetrics[0].status, 'completed');
assert.equal(service.backgroundMetrics[0].started_ms >= frameMs, true);
assert.equal(service.backgroundMetrics[0].finished_ms, 42);
assert.equal(service.backgroundMetrics[0].elapsed_ms, 7);
assert.equal(service.scheduleBackground('timed', () => assert.fail('repeat')), false);
turns.shift()();
assert.equal(service.backgroundMetrics[1].started_ms, 42);
assert.equal(service.backgroundMetrics[1].finished_ms, 50);
assert.deepEqual(logs.slice(1), [
    '[ShellStartup] background-task started name="timed" elapsed_ms=35',
    '[ShellStartup] background-task completed name="timed" elapsed_ms=42',
    '[ShellStartup] background-task started name="next" elapsed_ms=42',
    '[ShellStartup] background-task completed name="next" elapsed_ms=50'
]);
drain();
assert.equal(service.backgroundRunning, false);
""")

    def test_failure_and_cancellation_are_terminal_auditable_attempts(self):
        self.run_js("""
const service = ShellStartupService;
service.scheduleBackground('bad', () => { now = 1020; throw ''; });
service.scheduleBackground('pending', () => assert.fail('cancelled callback'));
now = 1010;
service.recordRealFirstFrame('window');
turns.shift()();
assert.equal(service.backgroundMetrics[0].status, 'failed');
assert.equal(service.backgroundMetrics[0].started_ms, 10);
assert.equal(service.backgroundMetrics[0].finished_ms, 20);
assert.equal(service._backgroundTaskStates.bad, 'failed');
assert.equal(service.scheduleBackground('bad', () => assert.fail('cancelled retry')), true);
assert.equal(service.backgroundMetrics.length, 3);
now = 1025;
service.cancelBackground('shutdown\\nrequested');
const snapshot = JSON.stringify(service.backgroundMetrics);
now = 1030;
service.cancelBackground('second cancellation');
assert.equal(JSON.stringify(service.backgroundMetrics), snapshot);
for (const metric of service.backgroundMetrics.slice(1)) {
    assert.equal(metric.status, 'cancelled');
    assert.equal(metric.started_ms, null);
    assert.equal(metric.finished_ms, 25);
    assert.equal(metric.elapsed_ms, null);
    assert.equal(metric.reason, 'shutdown\\nrequested');
}
drain();
assert.equal(JSON.stringify(service.backgroundMetrics), snapshot);
assert.equal(service.backgroundRunning, false);
assert.deepEqual(logs.filter(line => line.includes('background-task')), [
    '[ShellStartup] background-task started name="bad" elapsed_ms=10',
    '[ShellStartup] background-task failed name="bad" elapsed_ms=20',
    '[ShellStartup] background-task cancelled name="pending" elapsed_ms=25 reason="shutdown\\\\nrequested"',
    '[ShellStartup] background-task cancelled name="bad" elapsed_ms=25 reason="shutdown\\\\nrequested"'
]);
""")

    def test_retry_failed_task_and_late_cancelled_pump(self):
        self.run_js("""
assert.equal(ShellStartupService.scheduleBackground('retry', () => { throw Error('x'); }), true);
assert.equal(ShellStartupService.scheduleBackground('retry', () => {}), false);
ShellStartupService.recordRealFirstFrame('window');
const late = turns.shift(); late();
assert.equal(ShellStartupService._backgroundTaskStates.retry, 'failed');
assert.equal(ShellStartupService.scheduleBackground('retry', () => {}), true);
const pending = turns.shift(); ShellStartupService.cancelBackground('shutdown'); pending();
assert.equal(ShellStartupService._backgroundTaskStates.retry, 'cancelled: shutdown');
assert.equal(ShellStartupService.scheduleBackground('later', () => {}), false);
assert.equal(ShellStartupService.backgroundMetrics.length, 2);
assert.equal(ShellStartupService.backgroundMetrics[0].status, 'failed');
assert.equal(ShellStartupService.backgroundMetrics[1].status, 'cancelled');
""")

    def test_teardown_cancels_pending_model_work(self):
        self.run_js("""
complete();
assert.equal(ShellStartupService._backgroundTaskStates['font-options'], 'queued');
ShellStartupService.cancelBackground('test teardown'); drain();
assert.equal(ShellStartupService._backgroundTaskStates['font-options'], 'cancelled: test teardown');
assert.deepEqual(root.availableFamilies, []);
assert.equal(root._initialRefreshPending, true);
assert.equal(ShellStartupService.backgroundMetrics.length, 1);
assert.equal(ShellStartupService.backgroundMetrics[0].status, 'cancelled');
assert.equal(calls, 1);
""")


if __name__ == "__main__":
    unittest.main()
