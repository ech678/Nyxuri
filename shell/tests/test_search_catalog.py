"""Contracts for explicit search declarations and safe fixed action presets."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('search_catalog', ROOT/'scripts/dev/generate-search-catalog.py')
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.routes = {'schemaVersion': 1, 'routes': [dict(id='general', title='General', context='Settings', icon='settings', source='GeneralPage.qml', path=['general'], aliases=[])]}
        self.section = dict(id='general.section.language', route='general', title='Language', context='Settings', icon='language', aliases=['locale'])
        self.action = dict(id='clavis:spotlight:openMode:clipboard', category='clavis', name='Clipboard', target='spotlight', method='openMode', parameters=False,
            expression='spawn "qs" "-c" "clavis" "ipc" "call" "spotlight" "openMode" "clipboard"',
            search=dict(policy='include', title='Clipboard', description='Open clipboard history', context='Actions', icon='content_paste', args=['clipboard'], aliases=[], confirmation='none'))

    def compile(self, sections=None, actions=None):
        return compiler.compile_catalog(self.routes, sections if sections is not None else [('GeneralOverviewPage.qml', self.section)], actions if actions is not None else [self.action])

    def test_deterministic_public_output(self):
        result = self.compile()
        self.assertEqual(result['settings'][1]['path'], ['general'])
        self.assertEqual(result['actions'][0]['args'], ['clipboard'])
        self.assertEqual(compiler.render(result), compiler.render(copy.deepcopy(result)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'catalog.js'
            path.write_text(compiler.render(result))
            self.assertEqual(path.read_text(), compiler.render(result))

    def test_duplicate_missing_and_misdirected_declarations_rejected(self):
        with self.assertRaises(ValueError): self.compile([('GeneralOverviewPage.qml', self.section)]*2)
        with self.assertRaises(ValueError): self.compile([('Other.qml', self.section)])
        for field in ['id', 'title', 'context', 'icon', 'route']:
            bad = dict(self.section)
            del bad[field]
            with self.subTest(field=field), self.assertRaises(ValueError): self.compile([('GeneralOverviewPage.qml', bad)])
        self.section['route'] = 'unknown'
        with self.assertRaises(ValueError): self.compile()

    def test_routes_need_a_declared_navigation_host(self):
        self.routes['routes'].append(dict(id='general.child', title='Child', context='Settings', icon='settings', source='Child.qml', path=['general', 'child'], aliases=[]))
        self.compile()
        self.routes['routes'].append(dict(id='general.child.leaf', title='Leaf', context='Settings', icon='settings', source='Leaf.qml', path=['general', 'child', 'leaf'], aliases=[]))
        with self.assertRaises(ValueError): self.compile()

    def test_incomplete_unknown_and_unsafe_execution_rejected(self):
        for change in [{'parameters': True}, {'method': 'eval'}, {'expression': 'spawn-sh "evil"'}]:
            with self.subTest(change=change), self.assertRaises(ValueError): self.compile(actions=[dict(self.action, **change)])
        for args in [['unknown'], ['clipboard', '; reboot'], []]:
            action = copy.deepcopy(self.action)
            action['search']['args'] = args
            with self.subTest(args=args), self.assertRaises(ValueError): self.compile(actions=[action])
        action = copy.deepcopy(self.action)
        action.update(target='power-menu', method='open', expression='spawn "qs" "-c" "clavis" "ipc" "call" "power-menu" "open"')
        action['search']['args'] = []
        with self.assertRaises(ValueError): self.compile(actions=[action])
        action['search']['confirmation'] = 'power-menu'
        self.assertEqual(len(self.compile(actions=[action])['actions']), 1)

    def test_explicit_exclusions_and_non_clavis_actions(self):
        for policy in ['parameters', 'internal', 'alias', 'settings', 'unsafe']:
            excluded = dict(self.action, search={'policy': policy})
            self.assertEqual(self.compile(actions=[excluded])['actions'], [])
        self.assertEqual(self.compile(actions=[dict(self.action, category='niri')])['actions'], [])
        with self.assertRaises(ValueError): self.compile(actions=[dict(self.action, search={})])

    def test_shipped_catalog_is_valid_and_portable(self):
        catalog = compiler.load(ROOT)
        self.assertEqual({entry['path'][0] for entry in catalog['settings']}, {'account','general','wallpaper','theme','keystone','advanced'})
        self.assertNotIn(str(ROOT), json.dumps(catalog))
        self.assertEqual(len({entry['id'] for entry in catalog['settings']}), len(catalog['settings']))
        self.assertTrue(all(entry['target'] != 'control-center' for entry in catalog['actions']))
        self.assertTrue(all(entry['policy'] == 'include' for entry in catalog['actions']))


if __name__ == '__main__':
    unittest.main()
