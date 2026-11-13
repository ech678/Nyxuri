"""Execute production launcher JS and Loader bindings without starting a GUI.

The model supplies QML binding updates, Loader allocation/destruction and animation
completion. It does not prove Qt object destruction, image-cache reclamation,
first-frame geometry or Wayland focus; those require the isolated component probe.

Container probe plan (not run here): retain LauncherHost/window identity and IPC;
observe resultsLoaded, windowPhase, windowProgress and selected/mode/query/focus.
Assert loaded during opening/open/closing, no destruction until close cleanup,
then resultsLoaded=false and nested preview/delegate destruction. Reopen mid-exit
and after hidden in search/apps/clipboard/wallpapers/files/commands/web; check
first-frame geometry, keyboard focus, selection, image/delegate recreation and
routing. Repeat cycles and sample RSS/PSS 5s after close using the same profile
phases as baseline. QObject/image-cache and latency claims require those records.
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
WINDOW = REPO / "shell/plugins/launcher/LauncherWindow.qml"
HOST = REPO / "shell/plugins/launcher/LauncherHost.qml"


def block(text, marker):
    start = text.index("{", text.index(marker))
    depth = 1
    end = start + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def function(text, name):
    start = text.index("function " + name + "(")
    opening = text.index("{", start)
    # Host has QML parameter/return annotations, which Node cannot parse.
    signature = re.sub(r":\s*(?:string|void|bool)\b", "", text[start:opening])
    return signature + block(text[start:], "function " + name)


@unittest.skipUnless(shutil.which("node"), "Node required for launcher JS behavior tests")
class TestLauncherLifecycle(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)
        self.window = WINDOW.read_text()
        self.host = HOST.read_text()

    def run_steps(self, steps):
        methods = ["normalizedMode", "openSpotlight", "focusSpotlight", "requestClose",
                   "toggleWindow", "animateWindow", "animateRail", "openWebMode", "enterWeb",
                   "resultNavigationStep", "clipboardActivationAreaAt", "clipboardLayoutAt"]
        loader = self.window.split("id: resultsLoader", 1)[1]
        active = re.search(r"^\s*active:\s*(.+)$", loader, re.M).group(1)
        asynchronous = re.search(r"^\s*asynchronous:\s*(.+)$", loader, re.M).group(1)
        finished = block(self.window.split("id: windowAnimation", 1)[1], "onFinished:")
        script = """
const assert = require('node:assert/strict');
const events = [], later = [];
const Qt = {callLater: fn => later.push(fn)};
function flush() { while (later.length) later.shift()(); }
const ActionGateway = {externalDragActive: false};
const SpotlightSearchService = {
    cancelActivation() { events.push('cancel'); },
    openUrl(url) { events.push('url:' + url); }
};
const style = {windowOpenDuration: 200, windowCloseDuration: 150, railDuration: 100};
function makeWindow() {
    let retained = false, panel = null, serial = 0;
    const root = {windowPhase: 'hidden', visible: false, windowProgress: 0,
        railProgress: 0, webProgress: 0, query: '', pendingWebUrl: '',
        pendingSearchActivation: null, selectedResultIndex: -1, selectedResultId: '',
        controlHeld: false, modeRailExpanded: false, modeFocusIndex: -1};
    const session = {viewMode: 'search', tool: '', reset(mode) {
        events.push('reset:' + mode); this.viewMode = mode;
    }, enterTool(tool) { this.tool = tool; this.viewMode = tool; }};
    const searchBar = {focusInput() { assert.ok(panel); events.push('focus'); }};
    const clipboardProvider = {refresh() { events.push('clipboard'); }};
    const wallpaperProvider = {refresh() { events.push('wallpapers'); }};
    const windowAnimation = {stop() { this.running = false; }, restart() { this.running = true; }};
    const railAnimation = {stop() {}, restart() {}};
    function setLocalMode(mode) { session.viewMode = mode; }
    Object.defineProperties(root, {
        mode: {get: () => session.viewMode}, showing: {get: () => root.visible && root.windowPhase !== 'hidden'},
        spotlightModalActive: {get: () => panel ? panel.modalActive : false},
        panel: {get: () => panel}, resultsRetained: {get: () => retained, set(value) {
            retained = value;
            if (loaderActive() && !panel) {
                assert.equal(loaderAsync(), false);
                panel = {serial: ++serial, delegates: ['delegate'], preview: {image: 'image'},
                    modalActive: false, navigationStep: n => n,
                    clipboardActivationAreaAt: () => 'area', clipboardLayoutAt: () => 'layout'};
                events.push('load');
            } else if (!loaderActive() && panel) {
                assert.equal(root.windowPhase, 'hidden');
                assert.equal(root.visible, false);
                panel.delegates = []; panel.preview = null; panel = null;
                events.push('unload');
            }
        }}
    });
"""
        script += "function loaderActive() { return " + active + "; }\n"
        script += "function loaderAsync() { return " + asynchronous + "; }\n"
        # Nullable helpers resolve the current item in their real lexical scope.
        script += "let resultsPanel = null;\n"
        script += "\n".join(function(self.window, name) for name in methods)
        script += "\nObject.assign(root, {" + ",".join(methods) + "});\n"
        script += "root.finish = function() " + finished + ";\n"
        script += """
    root.resetClipboardAction = () => events.push('clipboard-reset');
    root.executeSearchActivation = activation => {
        events.push('activation:' + activation);
        if (activation === 'reopen') root.openSpotlight('apps');
    };
    root.setRailExpanded = value => { root.modeRailExpanded = value; };
    root.syncPanel = () => { resultsPanel = panel; };
    root.completeAnimation = () => { windowAnimation.running = false; root.finish(); };
    root.animation = windowAnimation;
    return root;
}
const win = makeWindow();
"""
        host_methods = ["toggleWindow", "openSpotlight", "openWebMode", "requestClose",
                        "runCommand", "normalizedMode"]
        script += "function makeHost() { let launcherItem = null; let active = false; const root = {initialMode: '', initialCommand: ''};\n"
        script += "\n".join(function(self.host, name) for name in host_methods)
        script += "\nObject.assign(root, {" + ",".join(host_methods) + "});\n"
        script += "function complete(window) " + block(self.host, "Component.onCompleted:") + "\n"
        script += """
Object.defineProperties(root, {
    active: {get: () => active, set(value) {
        active = value;
        if (active && !launcherItem) {
            launcherItem = makeWindow();
            launcherItem.runCommand = name => {
                launcherItem.openSpotlight(name === 'files' ? 'files' : 'commands'); return 'OK';
            };
            complete(launcherItem);
        }
    }},
    launcherItem: {get: () => launcherItem},
    windowPhase: {get: () => launcherItem ? launcherItem.windowPhase : 'hidden'}
});
return root;
}
"""
        bindings = {}
        for name in ["spotlightModalActive", "resultsPanelWidth", "resultsPanelHeight",
                     "wallpaperGridColumns", "wallpaperPreviewWidth"]:
            bindings[name] = re.search(r"readonly property \w+ " + name + r": (.+)",
                                       self.window).group(1)
        script += "const nullableBindings = " + json.dumps(bindings) + ";\n"
        script += steps + "\nconsole.log(JSON.stringify({ok:true}));\n"
        argv = ["node", "-"]
        with patch("subprocess.run", wraps=subprocess.run) as runner:
            out = subprocess.run(argv, input=script, text=True, capture_output=True,
                                 check=True, timeout=10, cwd=self.env.home)
        runner.assert_called_once_with(["node", "-"], input=script, text=True,
                                      capture_output=True, check=True, timeout=10,
                                      cwd=self.env.home)
        self.assertEqual(json.loads(out.stdout), {"ok": True})

    def test_open_close_keeps_panel_until_finished_and_cleanup_precedes_unload(self):
        self.run_steps("""
assert.equal(win.panel, null);
win.openSpotlight('clipboard');
assert.ok(win.panel.preview.image); assert.equal(win.windowPhase, 'opening');
flush(); assert.ok(events.indexOf('load') < events.indexOf('focus'));
win.completeAnimation(); assert.equal(win.windowPhase, 'open');
win.query = 'needle'; win.selectedResultIndex = 2; win.selectedResultId = 'entry';
win.requestClose(); const panel = win.panel;
assert.equal(win.windowPhase, 'closing'); assert.equal(win.visible, true);
assert.equal(win.query, 'needle'); assert.equal(win.panel, panel);
win.completeAnimation();
assert.equal(win.panel, null); assert.equal(win.query, '');
assert.equal(win.mode, 'search'); assert.equal(win.selectedResultIndex, -1);
assert.equal(win.selectedResultId, ''); assert.deepEqual(panel.delegates, []);
assert.equal(panel.preview, null);
assert.ok(events.indexOf('clipboard-reset') < events.indexOf('unload'));
assert.ok(events.indexOf('activation:null') < events.indexOf('unload'));
""")

    def test_reopen_during_closing_reverses_animation_without_destroying_panel(self):
        self.run_steps("""
win.openSpotlight('wallpapers'); win.completeAnimation(); const panel = win.panel;
win.windowProgress = 0.6; win.requestClose();
win.openSpotlight('files'); assert.equal(win.panel, panel);
assert.equal(win.animation.to, 1); assert.equal(win.animation.from, 0.6);
win.completeAnimation(); flush();
assert.equal(win.windowPhase, 'open'); assert.equal(win.mode, 'files');
assert.equal(events.includes('unload'), false);
""")

    def test_closed_reopen_restores_new_delegates_routing_and_focus(self):
        self.run_steps("""
for (const mode of ['apps', 'wallpapers', 'clipboard', 'files', 'commands', 'search']) {
    win.openSpotlight(mode); flush(); assert.equal(win.mode, mode);
    assert.equal(win.panel.delegates.length, 1); assert.ok(win.panel.preview);
    const serial = win.panel.serial;
    win.completeAnimation(); win.requestClose(); win.completeAnimation();
    assert.equal(win.panel, null);
    win.openSpotlight(mode); flush(); assert.equal(win.mode, mode);
    assert.equal(win.panel.serial, serial + 1); assert.ok(win.panel.preview);
    win.completeAnimation(); win.requestClose(); win.completeAnimation();
}
win.openWebMode(); flush(); assert.equal(win.mode, 'web'); assert.ok(win.panel);
assert.ok(events.filter(e => e === 'focus').length >= 13);
""")

    def test_activation_reopening_at_close_completion_cannot_unload_new_session(self):
        self.run_steps("""
win.openSpotlight('search'); win.completeAnimation(); const panel = win.panel;
win.pendingSearchActivation = 'reopen'; win.requestClose(); win.completeAnimation();
assert.equal(win.windowPhase, 'opening'); assert.equal(win.panel, panel);
assert.equal(win.mode, 'apps'); assert.equal(events.includes('unload'), false);
""")

    def test_drag_defers_close_and_unloaded_helpers_are_safe(self):
        self.run_steps("""
assert.equal(win.resultNavigationStep(1), 0);
assert.equal(win.clipboardActivationAreaAt(0), null);
assert.equal(win.clipboardLayoutAt(0), null);
ActionGateway.externalDragActive = true;
assert.equal(win.openSpotlight('apps'), false); assert.equal(win.panel, null);
ActionGateway.externalDragActive = false;
win.openSpotlight('apps'); win.completeAnimation();
win.syncPanel(); assert.equal(win.resultNavigationStep(1), 1);
assert.equal(win.clipboardActivationAreaAt(0), 'area');
ActionGateway.externalDragActive = true;
win.requestClose(); assert.equal(win.closeAfterDrag, true);
assert.equal(win.windowPhase, 'open'); assert.ok(win.panel);
""")

    def test_host_first_creation_and_subsequent_routing_keep_resident_window(self):
        self.run_steps("""
for (const first of ['toggle', 'clipboard', 'web', 'command']) {
    const host = makeHost();
    assert.equal(host.windowPhase, 'hidden'); assert.equal(host.launcherItem, null);
    if (first === 'toggle') host.toggleWindow();
    // Existing cold-host web route passes web to normalizedMode, which rejects it.
    else if (first === 'web') host.openWebMode();
    else if (first === 'command') assert.equal(host.runCommand('files'), 'EXECUTED');
    else host.openSpotlight(first);
    const window = host.launcherItem;
    assert.equal(host.windowPhase, 'opening'); assert.ok(window.panel);
    flush(); window.completeAnimation();
    assert.equal(window.mode, {toggle:'search', clipboard:'clipboard', web:'search', command:'files'}[first]);
    host.requestClose(); assert.ok(window.panel); window.completeAnimation();
    assert.equal(window.panel, null); assert.equal(host.active, true);
    host.openSpotlight('files'); flush();
    assert.equal(host.launcherItem, window); assert.equal(window.mode, 'files');
    assert.ok(window.panel); assert.equal(host.initialMode, 'files');
}
""")

    def test_unloaded_readonly_bindings_produce_typed_defaults_not_undefined(self):
        self.run_steps("""
const expected = {spotlightModalActive: false, resultsPanelWidth: 0,
    resultsPanelHeight: 0, wallpaperGridColumns: 1, wallpaperPreviewWidth: 0};
for (const [name, expression] of Object.entries(nullableBindings)) {
    assert.equal(new Function('resultsPanel', 'return ' + expression)(null), expected[name]);
}
""")

    def test_component_style_binding_uses_existing_window_style_object(self):
        component = self.window.split("sourceComponent: SpotlightResultsPanel {", 1)[1]
        binding = re.search(r"^\s*style:\s*(.+)$", component, re.M).group(1)
        alias = re.search(r"readonly property alias launcherStyle:\s*(\w+)", self.window).group(1)
        script = """
const assert = require('node:assert/strict');
const style = {panelDuration: 150, resultRadius: 20, appGridCellWidth: 96};
""" + "const root = {launcherStyle: " + alias + "};\n" + """
// The component itself starts with its QML default style=null. Resolve the
// production injection against the outer root, not that same-named property.
const component = {style: null};
""" + "component.style = (function() { return " + binding + "; }).call(component);\n" + """
assert.equal(component.style, style);
assert.equal(component.style.appGridCellWidth, 96);
assert.equal(component.style.panelDuration, 150);
console.log(JSON.stringify({ok:true}));
"""
        argv = ["node", "-"]
        with patch("subprocess.run", wraps=subprocess.run) as runner:
            out = subprocess.run(argv, input=script, text=True, capture_output=True,
                                 check=True, timeout=10, cwd=self.env.home)
        runner.assert_called_once_with(argv, input=script, text=True, capture_output=True,
                                      check=True, timeout=10, cwd=self.env.home)
        self.assertEqual(json.loads(out.stdout), {"ok": True})
