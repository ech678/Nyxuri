'''Behavior tests for the weather consumer lease (A3), the config version-stamp
gate (A2) and the weather disk-cache decoder.

The real QML function/handler text is cut out of the .qml source and executed
under node against mock objects; nothing here pattern-matches source to claim
behavior. Quickshell types (Loader, FileView, Process) are not exercised: that
needs the isolated container.'''

import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVICES = REPO / 'shell' / 'services'
WEATHER_SERVICE = SERVICES / 'WeatherService.qml'
WEATHER_BACKEND = SERVICES / 'weather' / 'WeatherBackend.qml'


def balanced(text, start, open_ch, close_ch):
    '''Slice from the first open_ch at/after start through its matching close_ch.'''
    i = text.index(open_ch, start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == open_ch:
            depth += 1
        elif text[j] == close_ch:
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    raise ValueError('unbalanced ' + open_ch)


def function_source(path, name):
    text = Path(path).read_text(encoding='utf-8')
    idx = text.index('function ' + name + '(')
    return text[idx:text.index('{', idx)] + balanced(text, idx, '{', '}')


def run_node(script):
    out = subprocess.run(['node', '-'], input=script, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


class TestWeatherLease(unittest.TestCase):
    def test_allocated_ids_are_unique_for_same_consumer_kind(self):
        script = ('const root = {_leaseSequence: 0}; '
                  + function_source(WEATHER_SERVICE, 'allocateLeaseId')
                  + ' console.log(JSON.stringify([allocateLeaseId("bar"), allocateLeaseId("bar")]));')
        self.assertEqual(run_node(script), ['bar:1', 'bar:2'])

    '''WeatherService.acquire/release: string-owner lease set, leaseCount gates the backend.'''

    def run_steps(self, steps):
        script = ('const root = {_leaseOwners: {}, leaseCount: 0}; '
                  + function_source(WEATHER_SERVICE, 'allocateLeaseId') + ' '
                  + function_source(WEATHER_SERVICE, 'acquire') + ' '
                  + function_source(WEATHER_SERVICE, 'release') + ' '
                  + 'const steps = ' + json.dumps(steps) + '; const counts = []; '
                  + 'for (const [op, owner] of steps) { (op === "acquire" ? acquire : release)(owner); counts.push(root.leaseCount); } '
                  + 'console.log(JSON.stringify({counts: counts, owners: Object.keys(root._leaseOwners).sort()}));')
        return run_node(script)

    def test_repeated_acquire_of_same_owner_is_idempotent(self):
        r = self.run_steps([['acquire', 'a'], ['acquire', 'a'], ['acquire', 'a']])
        self.assertEqual(r['counts'], [1, 1, 1])
        self.assertEqual(r['owners'], ['a'])

    def test_empty_and_null_owners_never_hold_a_lease(self):
        r = self.run_steps([['acquire', ''], ['acquire', None]])
        self.assertEqual(r['counts'], [0, 0])
        self.assertEqual(r['owners'], [])

    def test_multiple_consumers_keep_backend_alive_until_last_release(self):
        r = self.run_steps([['acquire', 'a'], ['acquire', 'b'], ['release', 'a'],
                            ['release', 'a'], ['release', 'b']])
        # b still holds after a is released (twice: the second is a no-op).
        self.assertEqual(r['counts'], [1, 2, 1, 1, 0])
        self.assertEqual(r['owners'], [])

    def test_release_of_unknown_owner_is_a_noop(self):
        r = self.run_steps([['acquire', 'a'], ['release', 'ghost'], ['release', None]])
        self.assertEqual(r['counts'], [1, 1, 1])
        self.assertEqual(r['owners'], ['a'])

    def test_reacquire_after_full_release_counts_again(self):
        r = self.run_steps([['acquire', 'a'], ['release', 'a'], ['acquire', 'a']])
        self.assertEqual(r['counts'], [1, 0, 1])

    def test_owner_map_is_replaced_not_mutated(self):
        # QML property bindings on _leaseOwners only fire on a new object.
        script = ('const root = {_leaseOwners: {}, leaseCount: 0}; '
                  + function_source(WEATHER_SERVICE, 'allocateLeaseId') + ' '
                  + function_source(WEATHER_SERVICE, 'acquire') + ' '
                  + function_source(WEATHER_SERVICE, 'release') + ' '
                  + 'const m0 = root._leaseOwners; acquire("a"); const m1 = root._leaseOwners; release("a"); const m2 = root._leaseOwners; '
                  + 'console.log(JSON.stringify({acq: m0 !== m1, rel: m1 !== m2, m1HasA: m1.a === true}));')
        r = run_node(script)
        self.assertEqual(r, {'acq': True, 'rel': True, 'm1HasA': True})


NOW = 1700000000000
MAX_AGE = 6 * 3600 * 1000


def payload(**over):
    data = {'schemaVersion': 1, 'savedAt': NOW - 1000, 'locationKey': '31.23,121.47',
            'forecast': {'current': {'temperature_2m': 1}}}
    data.update(over)
    return json.dumps(data)


def decode_all(cases):
    src = (function_source(WEATHER_BACKEND, 'locationKey') + ' '
           + function_source(WEATHER_BACKEND, 'cacheCoordinates') + ' '
           + function_source(WEATHER_BACKEND, 'decodeCache'))
    script = ('const root = {cacheMaxAgeMs: ' + str(MAX_AGE) + '}; ' + src + ' '
              + 'root.locationKey = locationKey; root.cacheCoordinates = cacheCoordinates; '
              + 'const cases = ' + json.dumps(cases) + '; const out = {}; '
              + 'for (const k of Object.keys(cases)) { out[k] = decodeCache(cases[k], ' + str(NOW) + ') !== null; } '
              + 'console.log(JSON.stringify(out));')
    return run_node(script)


class TestWeatherCacheDecode(unittest.TestCase):
    '''WeatherBackend.decodeCache: corrupt / wrong-version / expired caches are ignored.'''

    def test_fresh_valid_cache_is_accepted(self):
        self.assertTrue(decode_all({'ok': payload()})['ok'])

    def test_invalid_payloads_are_ignored(self):
        cases = {
            'corrupt json': '{oops',
            'empty text': '',
            'json array': '[]',
            'wrong schemaVersion': payload(schemaVersion=2),
            'future savedAt': payload(savedAt=NOW + 3600000),
            'savedAt string': payload(savedAt='x'),
            'no forecast.current': payload(forecast={}),
            'forecast null': payload(forecast=None),
            'empty locationKey': payload(locationKey=''),
        }
        result = decode_all(cases)
        for name in cases:
            with self.subTest(name):
                self.assertFalse(result[name])

    def test_age_boundary(self):
        result = decode_all({
            'inside': payload(savedAt=NOW - MAX_AGE + 5000),
            'past': payload(savedAt=NOW - MAX_AGE - 5000),
        })
        self.assertTrue(result['inside'])
        self.assertFalse(result['past'])

    def test_location_key_rounds_to_two_decimals(self):
        src = function_source(WEATHER_BACKEND, 'locationKey')
        keys = run_node(src + ' console.log(JSON.stringify([locationKey(31.2304, 121.4737), '
                        'locationKey(31.2349, 121.4701), locationKey(31.30, 121.4737)]));')
        self.assertEqual(keys[0], '31.23,121.47')
        self.assertEqual(keys[0], keys[1])
        self.assertNotEqual(keys[0], keys[2])

    def run_startup(self, text, loaded=True, manual=None):
        # Execute the actual refresh/cache functions with observable QML-like
        # properties and FileView completion. Network and timer effects are
        # mocked, but their ordering and coordinates come from the real logic.
        funcs = ['locationKey', 'cacheCoordinates', 'decodeCache', 'restoreCache',
                 'finishCacheLoad', 'refresh']
        sources = {name: function_source(WEATHER_BACKEND, name) for name in funcs}
        manual_setup = ('plugin.hasManualLocation = true; plugin.latitude = %s; plugin.longitude = %s;'
                        % (manual[0], manual[1])) if manual else ''
        script = '''
const events = [];
Date.now = () => %s;
const root = {cacheLoadComplete: false, cacheRestored: false, cachedKey: "",
              cacheMaxAgeMs: %s};
const plugin = {loading: false, hasValidData: false, hasManualLocation: false,
                latitude: 0, longitude: 0, locationName: "", lastUpdated: "",
                status: "unavailable", errorMessage: "", cachedForecastData: null,
                cachedAirData: null, currentAirQuality: null,
                processData: function () { events.push("restore-data"); this.hasValidData = true; }};
const refreshTimer = {start: function () { events.push("timer-start"); }};
function fetchWeather() { events.push(["weather-request", plugin.latitude, plugin.longitude]); }
function XMLHttpRequest() {
  this.open = function (method, url) { this.url = url; };
  this.send = function () { events.push(["ip-request", this.url]); };
}
%s
%s
%s
with (plugin) { %s plugin.refresh = refresh; }
%s
%s
root.locationKey = locationKey;
root.cacheCoordinates = cacheCoordinates;
root.decodeCache = decodeCache;
root.restoreCache = restoreCache;
root.finishCacheLoad = finishCacheLoad;
%s
plugin.refresh();
const beforeLoad = events.slice();
root.finishCacheLoad(%s, %s);
console.log(JSON.stringify({events: events, beforeLoad: beforeLoad,
  coords: [plugin.latitude, plugin.longitude], valid: plugin.hasValidData,
  restored: root.cacheRestored, complete: root.cacheLoadComplete}));
''' % (NOW, MAX_AGE, sources['locationKey'], sources['cacheCoordinates'], sources['decodeCache'],
       sources['refresh'], sources['restoreCache'], sources['finishCacheLoad'], manual_setup,
       json.dumps(text), 'true' if loaded else 'false')
        return run_node(script)

    def test_refresh_waits_for_async_cache_restore_and_uses_cached_auto_location(self):
        cached = payload(locationKey='31.23,121.47', latitude=31.2304, longitude=121.4737)
        result = self.run_startup(cached)
        self.assertEqual(result['beforeLoad'], [])
        self.assertEqual(result['events'][:3], ['restore-data', 'timer-start',
                                                ['weather-request', 31.2304, 121.4737]])
        self.assertEqual(result['coords'], [31.2304, 121.4737])
        self.assertTrue(result['valid'])
        self.assertTrue(result['restored'])

    def test_manual_location_rejects_other_place_cache_before_refresh(self):
        result = self.run_startup(payload(), manual=(35.68, 139.69))
        self.assertEqual(result['beforeLoad'], [])
        self.assertNotIn('restore-data', result['events'])
        self.assertEqual(result['events'], ['timer-start', ['weather-request', 35.68, 139.69]])
        self.assertFalse(result['valid'])
        self.assertFalse(result['restored'])

    def test_corrupt_or_missing_cache_is_ignored_then_cold_refresh_starts(self):
        for text, loaded in (('{broken', True), ('', False)):
            with self.subTest(text=text, loaded=loaded):
                result = self.run_startup(text, loaded=loaded)
                self.assertEqual(result['beforeLoad'], [])
                self.assertFalse(result['valid'])
                self.assertFalse(result['restored'])
                self.assertTrue(result['complete'])
                self.assertEqual(result['events'][0], 'timer-start')
                self.assertEqual(result['events'][1][0], 'ip-request')


import os
from tests.utils import TempEnv

CONFIG_SERVICE = SERVICES / 'ConfigService.qml'
STAMP = '# nyxuri-config-schema: 2'


def config_src():
    return CONFIG_SERVICE.read_text(encoding='utf-8')


def probe_decides(text):
    '''Run the real configProbe.onLoaded body against a given file text.'''
    src = config_src()
    start = src.index('id: configProbe')
    body = balanced(src, src.index('onLoaded:', start), '{', '}')
    script = ('const root = {storeReady: false}; const initProcess = {running: false}; '
              + 'const configProbe = {text: () => ' + json.dumps(text) + '}; '
              + '(function () ' + body + ')(); '
              + 'console.log(JSON.stringify({fast: root.storeReady, migrate: initProcess.running}));')
    return run_node(script)


def init_argv(config_dir, state_home):
    '''Evaluate the real initProcess.command array with Paths pointed at temp dirs.'''
    src = config_src()
    start = src.index('id: initProcess')
    arr = balanced(src, src.index('command:', start), '[', ']')
    paths = {'systemScriptsDir': str(REPO / 'shell' / 'scripts' / 'system'),
             'configHome': str(config_dir), 'stateHome': str(state_home)}
    return run_node('const Paths = ' + json.dumps(paths) + '; console.log(JSON.stringify(' + arr + '));')


def save_text():
    '''Run the real saveNow() and return the text it hands to configFile.setText.'''
    script = ('const root = {storeReady: true, loading: false, savePending: false, rawConfig: {}, lastError: null}; '
              + 'const Toml = {stringify: () => ' + json.dumps('[theme]') + '}; '
              + 'let written = null; const configFile = {setText: t => { written = t; }}; '
              + function_source(CONFIG_SERVICE, 'saveNow') + ' saveNow(); '
              + 'console.log(JSON.stringify(written));')
    return run_node(script)


class TestConfigVersionStamp(unittest.TestCase):
    '''A2: stamped current config.toml skips the interpreter; anything else migrates.'''

    def test_stamped_current_config_takes_fast_path(self):
        r = probe_decides(STAMP + '\n[theme]\nmode = 1\n')
        self.assertEqual(r, {'fast': True, 'migrate': False})

    def test_missing_stamp_runs_migration(self):
        for text in ('[theme]\nmode = 1\n', ''):
            with self.subTest(text=text):
                self.assertEqual(probe_decides(text), {'fast': False, 'migrate': True})

    def test_stamp_with_keystone_section_still_migrates(self):
        for text in (STAMP + '\n[keystone]\nstyle = 1\n', STAMP + '\n[keystone.media]\nx = 1\n'):
            with self.subTest(text=text):
                self.assertEqual(probe_decides(text), {'fast': False, 'migrate': True})

    def test_save_writes_a_stamp_the_probe_accepts(self):
        written = save_text()
        self.assertIn(STAMP, written)
        self.assertEqual(probe_decides(written), {'fast': True, 'migrate': False})


class TestMigrateScriptViaInitArgv(unittest.TestCase):
    '''Runs the real migrate_config.py with the argv array ConfigService builds.'''

    def run_real(self, ctx, text):
        cfg = ctx.home / '.config' / 'nyxuri'
        state = ctx.home / '.local' / 'state' / 'nyxuri'
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / 'config.toml').write_text(text, encoding='utf-8')
        argv = init_argv(cfg, state)
        res = subprocess.run(argv, capture_output=True, text=True, check=True)
        return argv, cfg, state, res

    def test_argv_is_an_array_with_expected_shape(self):
        with TempEnv() as ctx:
            argv, cfg, state, res = self.run_real(ctx, '[theme]\nmode = 1\n')
            script = REPO / 'shell' / 'scripts' / 'system' / 'migrate_config.py'
            self.assertEqual(argv, ['python3', str(script), '--config-dir', str(cfg),
                                    '--state-file', str(state / 'state.json'), '--cleanup'])
            self.assertIsInstance(json.loads(res.stdout), dict)

    def test_unstamped_keystone_is_renamed_and_stamp_comes_from_save(self):
        with TempEnv() as ctx:
            text = '[theme]\nmode = 1\n\n[keystone]\nlongShowNames = false\n\n[keystone.media]\nx = 1\n'
            argv, cfg, state, res = self.run_real(ctx, text)
            after = (cfg / 'config.toml').read_text(encoding='utf-8')
            self.assertIn('[island]', after)
            self.assertIn('[island.media]', after)
            self.assertIn('longShowNames = false', after)
            self.assertNotIn('[keystone', after)
            # The script does not write the stamp; saveNow does, after this exit.
            self.assertNotIn(STAMP, after)
            self.assertEqual(probe_decides(after), {'fast': False, 'migrate': True})
            header = save_text().rsplit('[theme]', 1)[0]
            self.assertEqual(probe_decides(header + after), {'fast': True, 'migrate': False})

    def test_stamped_keystone_is_renamed_and_keeps_its_stamp(self):
        with TempEnv() as ctx:
            text = STAMP + '\n[keystone]\nstyle = 1\n'
            argv, cfg, state, res = self.run_real(ctx, text)
            after = (cfg / 'config.toml').read_text(encoding='utf-8')
            self.assertIn(STAMP, after)
            self.assertIn('[island]', after)
            self.assertNotIn('[keystone', after)
            self.assertEqual(probe_decides(after), {'fast': True, 'migrate': False})


if __name__ == '__main__':
    unittest.main()
