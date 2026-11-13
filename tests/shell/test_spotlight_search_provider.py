"""Execute Spotlight provider JS and handlers without a QML runtime.

Connection target reevaluation/delivery is modeled explicitly. These tests do
not establish Qt notify delivery, QObject destruction or QML import validity.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv

ROOT = Path(__file__).resolve().parents[2] / "shell"
PROVIDER = ROOT / "plugins/launcher/SpotlightSearchProvider.qml"


def function(source, name):
    start = source.index("function " + name + "(")
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


@unittest.skipUnless(shutil.which("node"), "Node required for provider JS behavior tests")
class TestSpotlightSearchProvider(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def run_steps(self, steps):
        source = PROVIDER.read_text()
        wallpaper_connection = next(block for block in source.split("    Connections {")[1:]
                                    if "function onWallpapersChanged()" in block)
        target = re.search(r"target:\s*([^\n]+)", wallpaper_connection).group(1)
        # Execute the real local-search algorithms; only unrelated domain data
        # and the Qt binding/signal scheduler are test doubles.
        local_search = (ROOT / "plugins/launcher/SpotlightLocalSearch.js").read_text()
        local_search = re.sub(r"^\.(?:pragma|import).*\n", "", local_search, flags=re.M)
        script = """
const assert = require('node:assert/strict');
const vm = require('node:vm');
const LocalSearch = {AppRanking: {appResults: () => []}};
vm.createContext(LocalSearch);
"""
        script += "vm.runInContext(" + json.dumps(local_search) + ", LocalSearch);\n"
        script += """
const ActionGateway = {wallpaperHost: null, externalDragActive: false};
let enabled = true;
const StateProjection = {isEnabled: unit => {assert.equal(unit, 'wallpaper'); return enabled;}};
const ApplicationService = {launcherApplications: []};
const UiPreferences = {spotlightAppOrder: 'name'};
const SpotlightAppUsage = {records: {}};
const SpotlightCatalog = {settings: [], actions: [], available: () => true};
const I18n = {tr: text => ({arg: () => text, toString: () => text})};
const Paths = {fileUrl: path => 'file://' + path};
let closed = 0, rebuilds = 0;
const root = {active: true, query: 'forest', filter: '', results: [],
              capacities: {apps: 6, wallpapers: 4}, retainedResultId: '', error: ''};
const scope = new Proxy(root, {
    has: (obj, key) => key in obj,
    get: (obj, key) => obj[key]
});
function closeRequested() { closed++; }
"""
        # with(scope) emulates unqualified QML property reads/writes in methods.
        for name in ("rebuild", "activate"):
            method = function(source, name)
            opening = method.index("{")
            script += method[:opening + 1] + " with(scope) {" + method[opening + 1:-1] + "}}\n"
        script += "root.rebuild = () => { rebuilds++; rebuild(); };\n"
        for name in ("onWallpaperHostChanged", "onWallpapersChanged", "onBusyChanged",
                     "onExternalDragActiveChanged"):
            script += function(source, name) + "\n"
        script += "function connectionTarget() { return " + target + "; }\n"
        script += """
function host(paths) {
    return {wallpapers: paths, busy: false, calls: [],
            basename: path => path.split('/').pop(), parentFolder: () => '/images',
            setWallpaper(path) { this.calls.push(path); return true; }};
}
function setHost(value) {
    ActionGateway.wallpaperHost = value;
    onWallpaperHostChanged();
}
function emit(sender, handler) {
    // Model Connections target switching; Qt's implementation is not tested.
    if (sender && sender === connectionTarget()) handler();
}
function rows() { return root.results.filter(row => row.provider === 'wallpapers'); }
"""
        script += steps + "\nconsole.log('ok');\n"
        with patch("subprocess.run", wraps=subprocess.run) as runner:
            result = subprocess.run(["node", "-"], input=script, text=True,
                                    capture_output=True, check=True, timeout=10, cwd=self.env.home)
        runner.assert_called_once_with(["node", "-"], input=script, text=True,
                                       capture_output=True, check=True, timeout=10, cwd=self.env.home)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_attach_list_change_replace_and_null_refresh_results(self):
        self.run_steps("""
root.rebuild(); assert.equal(rows().length, 0);
const first = host(['/images/forest-a.png']);
setHost(first); assert.equal(rows()[0].sourceId, first.wallpapers[0]);
first.wallpapers = ['/images/forest-b.png'];
emit(first, onWallpapersChanged);
assert.equal(rows()[0].sourceId, first.wallpapers[0]);
const oldId = rows()[0].id;
const second = host(['/images/forest-c.png']);
setHost(second); assert.equal(rows()[0].sourceId, second.wallpapers[0]);
assert.equal(activate(oldId), false);
const before = rebuilds;
emit(first, onWallpapersChanged); emit(first, onBusyChanged);
assert.equal(rebuilds, before);
const secondId = rows()[0].id;
setHost(null); assert.equal(connectionTarget(), null); assert.equal(rows().length, 0);
assert.equal(activate(secondId), false); assert.equal(closed, 0);
""")

    def test_busy_changes_preserve_refresh_and_activation_guard(self):
        self.run_steps("""
const current = host(['/images/forest.png']); setHost(current);
const id = rows()[0].id;
let before = rebuilds;
current.busy = true; emit(current, onBusyChanged);
assert.equal(rebuilds, before + 1);
assert.equal(activate(id), false); assert.equal(current.calls.length, 0);
before = rebuilds;
current.busy = false; emit(current, onBusyChanged);
assert.equal(rebuilds, before + 1);
assert.equal(activate(id), true); assert.equal(current.calls[0], current.wallpapers[0]);
assert.equal(closed, 1);
""")

    def test_inactive_and_dragging_defer_work_until_existing_refresh(self):
        self.run_steps("""
root.active = false;
const current = host(['/images/forest.png']); setHost(current);
emit(current, onWallpapersChanged); emit(current, onBusyChanged);
assert.equal(root.results.length, 0);
root.active = true; root.rebuild(); assert.equal(rows().length, 1);
ActionGateway.externalDragActive = true;
setHost(null); assert.equal(rows().length, 1);
ActionGateway.externalDragActive = false; onExternalDragActiveChanged();
assert.equal(rows().length, 0);
setHost(current); root.active = false; setHost(null);
root.active = true; root.rebuild(); assert.equal(rows().length, 0);
""")

    def test_removed_path_and_disabled_wallpaper_do_not_remain_results(self):
        self.run_steps("""
const current = host(['/images/forest.png']); setHost(current);
const id = rows()[0].id;
current.wallpapers = [];
assert.equal(activate(id), false); assert.equal(current.calls.length, 0);
emit(current, onWallpapersChanged); assert.equal(rows().length, 0);
current.wallpapers = ['/images/forest.png']; enabled = false;
emit(current, onWallpapersChanged); assert.equal(rows().length, 0);
""")
