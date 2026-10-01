#!/usr/bin/env python3
"""Compile explicit settings declarations and shortcut action search policy.

Only the dedicated, single-line SettingsSearchAnchor.declaration JSON literal
is read from QML. We never infer a route from an arbitrary title or UI layout.
"""
import argparse
import json
from pathlib import Path
import re

DECLARATION = re.compile(r"^\s*declaration:\s*'([^'\n]+)'\s*$", re.MULTILINE)
POLICIES = {'include', 'alias', 'settings', 'parameters', 'internal', 'unsafe'}
DISPATCH = {
    ('lock', 'open'): [[]],
    ('spotlight', 'search'): [[]],
    ('spotlight', 'web'): [[]],
    ('spotlight', 'files'): [[]],
    ('spotlight', 'openMode'): [['apps'], ['clipboard'], ['wallpapers']],
    ('wallpaper', 'clear'): [[]],
    ('wallpaper', 'previous'): [[]],
    ('wallpaper', 'next'): [[]],
    ('wallpaper', 'random'): [[]],
    ('keystone', 'cancelRecord'): [[]],
    ('keystone', 'closeAllOthers'): [[]],
    ('keystone', 'dashboard'): [[]],
    ('keystone', 'hub'): [[]],
    ('keystone', 'lyrics'): [[]],
    ('keystone', 'tools'): [[]],
    ('sidebar', 'open'): [['dashboard'], ['quicksettings']],
    ('sidebar', 'toggle'): [['weather'], ['drawer']],
    ('shortcut-map', 'open'): [[]],
    ('power-menu', 'open'): [[]],
}
AVAILABILITY = {'always', 'awww', 'clavis-wallpaper', 'wallpaper-idle', 'keystone', 'keyboard-lock', 'dock-previews'}


def required(entry, fields):
    for field in fields:
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ValueError(f'Missing {field}: {entry.get("id")}')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.:-]*', entry['id']):
        raise ValueError(f'Invalid stable ID: {entry["id"]}')
    if not isinstance(entry.get('aliases'), list) or not all(isinstance(x, str) for x in entry['aliases']):
        raise ValueError(f'Invalid aliases: {entry["id"]}')
    if entry.get('availability', 'always') not in AVAILABILITY:
        raise ValueError(f'Unknown availability: {entry["id"]}')


def compile_catalog(route_document, declarations, actions):
    if route_document.get('schemaVersion') != 1:
        raise ValueError('Unsupported settings schema')
    routes = route_document['routes']
    by_id = {}
    for route in routes:
        required(route, ['id', 'title', 'context', 'icon', 'source'])
        if route['id'] in by_id or route['path'] != route['id'].split('.'):
            raise ValueError(f'Duplicate ID or invalid route path: {route["id"]}')
        if '/' in route['source'] or not route['source'].endswith('.qml'):
            raise ValueError('Page sources must be local QML filenames')
        by_id[route['id']] = route
    for route in routes:
        if len(route['path']) > 1:
            parent = '.'.join(route['path'][:-1])
            if parent not in by_id or parent not in {'general', 'keystone', 'general.displays'}:
                raise ValueError(f'Unknown navigation host: {route["id"]}')
    settings = [dict(r, route=r['id'], anchor=False) for r in routes]
    ids = set(by_id)
    for source, entry in declarations:
        required(entry, ['id', 'route', 'title', 'context', 'icon'])
        if entry['id'] in ids or entry['route'] not in by_id:
            raise ValueError(f'Duplicate ID or unknown route: {entry["id"]}')
        route = by_id[entry['route']]
        # The General overview lives in its explicitly declared nested host.
        expected = 'GeneralOverviewPage.qml' if entry['route'] == 'general' else route['source']
        if source != expected:
            raise ValueError(f'Declaration belongs to {expected}, not {source}')
        ids.add(entry['id'])
        settings.append(dict(entry, source=source, path=route['path'], anchor=True))
    selected = []
    action_ids = set()
    for action in actions:
        if action['category'] != 'clavis':
            continue
        if action['id'] in action_ids:
            raise ValueError('Duplicate action ID')
        action_ids.add(action['id'])
        search = action.get('search', {})
        if search.get('policy') not in POLICIES:
            raise ValueError(f'Missing explicit search policy: {action["id"]}')
        if search['policy'] != 'include':
            continue
        entry = dict(search, id=action['id'], target=action['target'], method=action['method'])
        required(entry, ['id', 'title', 'description', 'context', 'icon'])
        args = search.get('args')
        if action['parameters'] or args not in DISPATCH.get((entry['target'], entry['method']), []):
            raise ValueError(f'Incomplete or unapproved action: {entry["id"]}')
        if entry.get('confirmation') not in ('none', 'power-menu'):
            raise ValueError(f'Invalid confirmation: {entry["id"]}')
        if entry['target'] == 'power-menu' and entry['confirmation'] != 'power-menu':
            raise ValueError('Power actions must open the existing confirmation UI')
        # Check fixed argv against the existing shortcut declaration, never run it.
        expected = 'spawn ' + ' '.join(json.dumps(v) for v in ['qs', '-c', 'clavis', 'ipc', 'call', entry['target'], entry['method'], *args])
        if action['expression'] != expected:
            raise ValueError(f'Fixed arguments disagree with shortcut: {entry["id"]}')
        selected.append(entry)
    return {'schemaVersion': 1, 'routes': routes, 'settings': settings, 'actions': selected}


def render(catalog):
    data = json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True)
    lines = ['// Generated by scripts/dev/generate-search-catalog.py. Do not edit.', '.pragma library', '', 'var catalog = '+data+';', '', 'function title(id) {', '    switch (id) {']
    for entry in catalog['settings'] + catalog['actions']:
        lines.append('    case '+json.dumps(entry['id'])+': return qsTranslate('+json.dumps(entry['context'])+', '+json.dumps(entry['title'])+');')
    lines += ['    default: return "";', '    }', '}', '', 'function description(id) {', '    switch (id) {']
    for entry in catalog['actions']:
        lines.append('    case '+json.dumps(entry['id'])+': return qsTranslate('+json.dumps(entry['context'])+', '+json.dumps(entry['description'])+');')
    lines += ['    default: return "";', '    }', '}', '']
    return '\n'.join(lines)


def load(root):
    routes = json.loads((root/'Common/settings-routes.json').read_text())
    page_dir = root/'Modules/ControlCenter'
    for route in routes['routes']:
        if not (page_dir/route['source']).is_file():
            raise ValueError(f'Missing page: {route["source"]}')
    declarations = []
    for path in sorted(page_dir.glob('*.qml')):
        declarations.extend((path.name, json.loads(value)) for value in DECLARATION.findall(path.read_text()))
    actions = json.loads((root/'scripts/system/niri-actions.json').read_text())
    return compile_catalog(routes, declarations, actions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    content = render(load(args.root))
    output = args.output or args.root/'Common/generated/SearchCatalog.js'
    if args.check:
        if not output.is_file() or output.read_text() != content:
            raise SystemExit('Search catalog is stale; run generate-search-catalog.py')
    elif not output.is_file() or output.read_text() != content:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content)


if __name__ == '__main__':
    main()
