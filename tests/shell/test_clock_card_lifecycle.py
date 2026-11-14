"""Execute clock-card bindings/handlers in Node, without starting a QML runtime.

The event harness models QML binding reevaluation and triggeredOnStart; actual
QObject delivery, visibility propagation and destruction still need a container.
"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv

REPO = Path(__file__).resolve().parents[2]
CARD = REPO / "shell/services/SystemClockCard.qml"
COOKIE = REPO / "shell/services/SidebarCookieClock.qml"


def expression(source, name):
    """Read an actual single-line QML binding, not a test-side implementation."""
    match = re.search(r"^\s*" + re.escape(name) + r":\s*(.+)$", source, re.M)
    if not match:
        raise ValueError(name)
    return match.group(1)


def function(source, name):
    start = source.index("function " + name + "(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


@unittest.skipUnless(shutil.which("node"), "Node is required for QML JavaScript behavior tests")
class TestClockCardLifecycle(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)
        self.card = CARD.read_text()
        self.cookie = COOKIE.read_text()

    def run_steps(self, steps):
        # Extract each Timer separately: the cookie's root refers to its own item.
        card_timer = self.card.split("    Timer {", 1)[1].split("    Connections {", 1)[0]
        cookie_timer = self.cookie.split("    Timer {", 1)[1].split("    // Service-tier", 1)[0]
        cookie_item = self.card.split("    SidebarCookieClock {", 1)[1].split("    Item {", 1)[0]
        script = """
const assert = require('node:assert/strict');
const NativeDate = Date;
let now = NativeDate.parse('2026-11-12T23:59:59Z');
global.Date = class extends NativeDate {
    constructor(...args) { super(...(args.length ? args : [now])); }
};
process.env.TZ = 'UTC';
const UiPreferences = {sidebarClockStyle: 'digital', useTwelveHourClock: false};
const root = {active: true, currentTime: new Date()};
const cookieClock = {active: false, visible: false, currentTime: new Date()};
"""
        script += function(self.card, "onCurrentTimeChanged") + "\n"
        script += "function parentRunning() { return " + expression(card_timer, "running") + "; }\n"
        script += "function cookieActive() { const visible = cookieClock.visible; return " + expression(cookie_item, "active") + "; }\n"
        script += "function cookieVisible() { return " + expression(cookie_item, "visible") + "; }\n"
        script += "function parentTick() { " + expression(card_timer, "onTriggered") + "; }\n"
        # Execute the child's existing tick with its original root context.
        script += "function childTick() { const root = cookieClock; " + expression(cookie_timer, "onTriggered") + "; onCurrentTimeChanged(); }\n"
        script += "const parentStartsImmediately = " + expression(card_timer, "triggeredOnStart") + ";\n"
        script += "const childStartsImmediately = " + expression(cookie_timer, "triggeredOnStart") + ";\n"
        script += "function childRunning() { const root = cookieClock; return " + expression(cookie_timer, "running") + "; }\n"
        script += """
function rebind() {
    const wasParent = parentRunning();
    const wasChild = childRunning();
    cookieClock.visible = cookieVisible();
    cookieClock.active = cookieActive();
    if (!wasChild && childRunning() && childStartsImmediately) childTick();
    if (!wasParent && parentRunning() && parentStartsImmediately) parentTick();
}
function setMode(mode) { UiPreferences.sidebarClockStyle = mode; rebind(); }
function setActive(active) {
    const wasParent = parentRunning();
    root.active = active;
    rebind();
    if (!wasParent && parentRunning() && parentStartsImmediately) parentTick();
}
function tick() {
    if (parentRunning()) parentTick();
    if (childRunning()) childTick();
}
function timerCount() { return Number(parentRunning()) + Number(childRunning()); }
"""
        script += steps + "\nconsole.log(JSON.stringify({ok: true}));\n"
        argv = ["node", "-"]
        with patch("subprocess.run", wraps=subprocess.run) as runner:
            result = subprocess.run(argv, input=script, text=True, capture_output=True,
                                    check=True, timeout=10, cwd=self.env.home)
        runner.assert_called_once_with(["node", "-"], input=script, text=True,
                                       capture_output=True, check=True, timeout=10,
                                       cwd=self.env.home)
        self.assertEqual(json.loads(result.stdout), {"ok": True})

    def test_only_one_ticker_per_active_card_in_both_styles(self):
        self.run_steps("""
assert.equal(timerCount(), 1);
setMode('cookie');
assert.equal(parentRunning(), false);
assert.equal(timerCount(), 1);
setMode('digital');
assert.equal(childRunning(), false);
assert.equal(timerCount(), 1);
""")

    def test_switching_modes_refreshes_immediately(self):
        self.run_steps("""
now += 3600000;
setMode('cookie');
assert.equal(root.currentTime.getTime(), now);
now += 3600000;
setMode('digital');
assert.equal(root.currentTime.getTime(), now);
""")

    def test_inactive_card_has_no_ticks_and_reactivation_is_immediate(self):
        self.run_steps("""
for (const style of ['digital', 'cookie']) {
    setMode(style);
    setActive(false);
    const saved = root.currentTime.getTime();
    now += 86400000;
    tick();
    assert.equal(timerCount(), 0);
    assert.equal(root.currentTime.getTime(), saved);
    setActive(true);
    assert.equal(timerCount(), 1);
    assert.equal(root.currentTime.getTime(), now);
}
""")

    def test_late_child_signal_cannot_overwrite_digital_or_inactive_card(self):
        self.run_steps("""
setMode('cookie');
setMode('digital');
const saved = root.currentTime;
cookieClock.currentTime = new Date(0);
onCurrentTimeChanged();
assert.equal(root.currentTime, saved);
setMode('cookie');
setActive(false);
const inactive = root.currentTime;
cookieClock.currentTime = new Date(0);
onCurrentTimeChanged();
assert.equal(root.currentTime, inactive);
""")

    def test_midnight_and_clock_jumps_refresh_on_next_existing_tick(self):
        self.run_steps("""
for (const style of ['digital', 'cookie']) {
    setMode(style);
    for (const time of ['2026-11-13T00:00:00Z', '2026-10-01T01:02:03Z',
                        '2027-01-01T13:59:00Z']) {
        now = NativeDate.parse(time);
        tick();
        assert.equal(root.currentTime.getTime(), now);
        assert.equal(root.currentTime.getDate(), new NativeDate(now).getDate());
    }
}
""")

    def test_timezone_change_is_read_by_both_existing_tickers(self):
        self.run_steps("""
now = NativeDate.parse('2026-11-13T02:00:00Z');
for (const style of ['digital', 'cookie']) {
    process.env.TZ = 'UTC';
    setMode(style); tick();
    assert.equal(root.currentTime.getHours(), 2);
    process.env.TZ = 'America/New_York';
    tick();
    assert.equal(root.currentTime.getHours(), 21);
    assert.equal(root.currentTime.getDate(), 12);
}
""")

    def test_clock_preferences_and_language_are_not_latched_to_ticks(self):
        # Evaluate the real presentation bindings with changed dependencies and
        # no tick. This is JS coverage, not proof of Qt dependency tracking.
        hour_text = self.card.split("readonly property string hourText: ", 1)[1].split(
            "    readonly property string minuteText:", 1)[0].strip()
        date_text = self.card.split("readonly property string dateText: ", 1)[1].split(
            "    function topOffset", 1)[0].strip()
        hour_text = " ".join(hour_text.splitlines())
        date_text = " ".join(date_text.splitlines())
        self.run_steps("""
now = NativeDate.parse('2026-11-13T14:05:00Z'); tick();
const currentTime = root.currentTime;
const hour24 = currentTime.getHours();
const hour12 = ((hour24 + 11) % 12) + 1;
const I18nService = {language: 'en'};
const Qt = {locale: () => 'en'};
const DateFormat = {compactDate: (date, language) => language + ':' + date.getDate()};
const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
""" + "function hourText() { return " + hour_text + "; }\n"
            + "function dateText() { return " + date_text + "; }\n" + """
assert.equal(hourText(), '14');
UiPreferences.useTwelveHourClock = true;
assert.equal(hourText(), '02');
assert.equal(dateText(), 'Fri · 13 Nov');
I18nService.language = 'zh_CN';
assert.equal(dateText(), 'zh_CN:13');
assert.equal(root.currentTime.getTime(), now);
""")
