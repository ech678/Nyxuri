#!/usr/bin/env python3
import re
import tomllib
import unittest
from pathlib import Path

SHELL_ROOT = Path(__file__).resolve().parents[1]
THEME = SHELL_ROOT / 'shared' / 'theme'
APPEARANCE = THEME / 'Appearance.qml'
TYPOGRAPHY = THEME / 'Typography.qml'
ANIMATIONS = THEME / 'Animations.qml'
METRICS = THEME / 'Metrics.qml'
SIZES = THEME / 'Sizes.qml'
FONTS = THEME / 'Fonts.qml'
I18N = SHELL_ROOT / 'assets' / 'i18n' / 'zh_CN.toml'

COLOR_PROP = re.compile(r'property\s+color\s+([A-Za-z0-9_]+)\s*:\s*"#([0-9A-Fa-f]{6,8})"')
PIXEL_SIZE = re.compile(r'readonly\s+property\s+int\s+pixelSize\s*:\s*(\d+)')
DURATION = re.compile(r'readonly\s+property\s+int\s+([A-Za-z0-9_]+)\s*:\s*(\d+)')
RADIUS = re.compile(r'property\s+int\s+([A-Za-z0-9_]+)\s*:\s*(\d+)')
MIN_RATIO = 3.0
DARK_BACKGROUNDS = ('colLayer0', 'colLayer1', 'colLayer2', 'colSurface', 'colBackground')


def hex_to_rgb(value):
    value = value[:6]
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_to_linear(channel):
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


class DesignTokenContracts(unittest.TestCase):
    def setUp(self):
        self.appearance = APPEARANCE.read_text(encoding='utf-8')
        self.typography = TYPOGRAPHY.read_text(encoding='utf-8')
        self.animations = ANIMATIONS.read_text(encoding='utf-8')
        self.fonts = FONTS.read_text(encoding='utf-8')

    def test_material_color_scheme_is_complete(self):
        colors = dict(COLOR_PROP.findall(self.appearance))
        required = (
            'm3primary', 'm3onPrimary', 'm3secondary', 'm3onSecondary',
            'm3tertiary', 'm3onTertiary', 'm3error', 'm3onError',
            'm3surface', 'm3onSurface', 'm3surfaceVariant', 'm3onSurfaceVariant',
            'm3background', 'm3onBackground', 'm3outline', 'm3outlineVariant',
        )
        missing = [name for name in required if name not in colors]
        self.assertEqual(missing, [], f'Missing Material color roles: {missing}')

    def test_text_on_surface_meets_contrast(self):
        colors = dict(COLOR_PROP.findall(self.appearance))
        pairs = (
            ('m3onSurface', 'm3surface'),
            ('m3onBackground', 'm3background'),
            ('m3onSurfaceVariant', 'm3surfaceVariant'),
            ('m3onPrimary', 'm3primary'),
            ('m3onError', 'm3error'),
        )
        failures = []
        for foreground, background in pairs:
            if foreground not in colors or background not in colors:
                failures.append(f'{foreground}/{background}: undefined')
                continue
            ratio = contrast(hex_to_rgb(colors[foreground]), hex_to_rgb(colors[background]))
            if ratio < MIN_RATIO:
                failures.append(f'{foreground}/{background}: {ratio:.2f}')
        self.assertEqual(failures, [], f'Contrast below {MIN_RATIO}: {failures}')

    def test_typography_roles_cover_material_scale(self):
        for role in ('displaySmall', 'headlineMedium', 'headlineSmall', 'titleLarge',
                     'titleMedium', 'titleSmall', 'bodyLarge', 'bodyMedium', 'bodySmall',
                     'labelLarge', 'labelMedium', 'labelSmall'):
            self.assertRegex(self.typography, r'property\s+QtObject\s+' + role + r'\b')

    def test_motion_durations_are_ordered(self):
        durations = {name: int(value) for name, value in DURATION.findall(self.animations)}
        self.assertIn('small', durations)
        self.assertIn('normal', durations)
        self.assertIn('large', durations)
        self.assertLess(durations['small'], durations['normal'])
        self.assertLess(durations['normal'], durations['large'])
        self.assertGreaterEqual(durations['small'], 80, 'Too fast to perceive')

    def test_motion_curves_are_normalized_bezier(self):
        block = self.animations[self.animations.index('curves: QtObject'):]
        curves = re.findall(r'readonly\s+property\s+var\s+([A-Za-z0-9_]+)\s*:\s*\[([^\]]+)\]', block)
        self.assertGreaterEqual(len(curves), 6, 'Expected a full motion curve set')
        for name, body in curves:
            values = [float(v) for v in body.split(',')]
            self.assertEqual(len(values) % 2, 0, f'Curve {name} must be x/y pairs')
            for index in range(0, len(values), 2):
                self.assertGreaterEqual(values[index], 0.0, f'Curve {name} x below 0')
                self.assertLessEqual(values[index], 1.0, f'Curve {name} x above 1')

    def test_font_roles_are_declared(self):
        for role in ('ui', 'mono', 'numeric', 'expressive'):
            self.assertRegex(self.fonts, r'property\s+string\s+' + role + r'\b')
        numeric = re.search(r'property\s+string\s+numeric\s*:\s*"([^"]+)"', self.fonts)
        self.assertIsNotNone(numeric)
        self.assertNotEqual(numeric.group(1), '', 'Numeric role must resolve to a family')

    def test_theme_module_files_exist(self):
        for name in ('Appearance.qml', 'Typography.qml', 'Animations.qml', 'Metrics.qml',
                     'Sizes.qml', 'Fonts.qml', 'Resources.qml'):
            self.assertTrue((THEME / name).is_file(), f'Missing theme module: {name}')


if __name__ == '__main__':
    unittest.main()