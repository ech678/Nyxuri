#!/usr/bin/env python3
import re
import tomllib
import unittest
from pathlib import Path

SHELL_ROOT = Path(__file__).resolve().parents[1]
CATALOG = SHELL_ROOT / 'assets' / 'i18n' / 'zh_CN.toml'
SOURCE_DIRS = ('app', 'modules', 'shared')
ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '"': '"', "'": "'", '\\': '\\'}
CALL = re.compile(
    r'I18n\.(?:tr|t)\s*\(\s*(["\'])((?:\\.|(?!\1).)*)\1\s*(?:,\s*(["\'])((?:\\.|(?!\3).)*)\3)?',
    re.DOTALL,
)


def unescape(value):
    out = []
    index = 0
    while index < len(value):
        if value[index] == '\\' and index + 1 < len(value):
            out.append(ESCAPES.get(value[index + 1], '\\' + value[index + 1]))
            index += 2
        else:
            out.append(value[index])
            index += 1
    return ''.join(out)


def catalog():
    with CATALOG.open('rb') as handle:
        return tomllib.load(handle)


def collect_calls():
    calls = []
    for base in SOURCE_DIRS:
        for path in (SHELL_ROOT / base).rglob('*'):
            if path.suffix not in ('.qml', '.js'):
                continue
            text = path.read_text(encoding='utf-8', errors='ignore')
            for match in CALL.finditer(text):
                calls.append((
                    unescape(match.group(2)),
                    unescape(match.group(4)) if match.group(4) else '',
                    path.relative_to(SHELL_ROOT).as_posix(),
                ))
    return calls


class CatalogContracts(unittest.TestCase):
    def setUp(self):
        self.data = catalog()
        self.flat = {k: v for k, v in self.data.items() if not isinstance(v, dict)}
        self.contexts = {k: v for k, v in self.data.items() if isinstance(v, dict)}

    def test_every_referenced_string_resolves(self):
        missing = []
        for key, ctx, origin in collect_calls():
            if ctx and ctx in self.contexts and key in self.contexts[ctx]:
                continue
            if key in self.flat:
                continue
            missing.append((key, ctx, origin))
        self.assertEqual(missing, [], f'Unresolved translation keys: {missing[:10]}')

    def test_no_empty_translation_values(self):
        empty = [k for k, v in self.flat.items() if isinstance(v, str) and v == '']
        self.assertEqual(empty, [], f'Empty translations: {empty[:10]}')
        for name, block in self.contexts.items():
            for key, value in block.items():
                if isinstance(value, str) and value == '':
                    empty.append(f'{name}/{key}')
        self.assertEqual(empty, [], f'Empty context translations: {empty[:10]}')

    def test_catalog_has_no_legacy_brand(self):
        offenders = [k for k in self.flat if 'clavis' in k.lower()]
        for name, block in self.contexts.items():
            offenders.extend(f'{name}/{k}' for k in block if 'clavis' in k.lower())
        self.assertEqual(offenders, [], f'Legacy brand in catalog keys: {offenders[:10]}')

    def test_source_has_no_legacy_brand_in_translatable_strings(self):
        offenders = []
        for key, _ctx, origin in collect_calls():
            if 'clavis' in key.lower():
                offenders.append((origin, key))
        self.assertEqual(offenders, [], f'Legacy brand in translatable strings: {offenders[:10]}')

    def test_weather_condition_strings_are_translated(self):
        conditions = [
            'Clear sky', 'Mainly clear', 'Partly cloudy', 'Overcast', 'Fog', 'Drizzle',
            'Rain', 'Snow', 'Snow grains', 'Rain showers', 'Snow showers',
            'Thunderstorm', 'Thunderstorm with hail', 'Cloudy',
        ]
        missing = [name for name in conditions if name not in self.flat]
        self.assertEqual(missing, [], f'Untranslated weather conditions: {missing}')
        untranslated = [name for name in conditions if self.flat[name] == name]
        self.assertEqual(untranslated, [], f'Weather conditions left in English: {untranslated}')


if __name__ == '__main__':
    unittest.main()