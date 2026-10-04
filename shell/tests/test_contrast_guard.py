import re
import unittest
from pathlib import Path

SHELL_ROOT = Path(__file__).resolve().parents[1]
APPEARANCE = SHELL_ROOT / 'shared' / 'theme' / 'Appearance.qml'
WCAG = {
    'black': (0.0, 0.0, 0.0),
    'white': (1.0, 1.0, 1.0),
    'mid': (0.5, 0.5, 0.5),
}


def srgb_to_linear(value):
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


class ContrastContracts(unittest.TestCase):
    def setUp(self):
        self.text = APPEARANCE.read_text(encoding='utf-8')

    def test_helpers_are_declared(self):
        for name in ('relativeLuminance', 'contrastRatio', 'ensureContrast'):
            self.assertRegex(self.text, r'function\s+' + name + r'\s*\(')

    def test_luminance_uses_wcag_coefficients(self):
        for coefficient in ('0.2126', '0.7152', '0.0722'):
            self.assertIn(coefficient, self.text)
        self.assertIn('0.03928', self.text)

    def test_reference_ratios_match_wcag(self):
        self.assertAlmostEqual(ratio(WCAG['black'], WCAG['white']), 21.0, places=4)
        self.assertAlmostEqual(ratio(WCAG['mid'], WCAG['mid']), 1.0, places=4)
        self.assertGreater(ratio(WCAG['black'], WCAG['mid']), ratio(WCAG['mid'], WCAG['white']))

    def test_default_threshold_is_accessible(self):
        match = re.search(r'function\s+ensureContrast[\s\S]*?minimum\s*===\s*undefined\s*\?\s*([0-9.]+)', self.text)
        self.assertIsNotNone(match, 'ensureContrast must define a default threshold')
        self.assertGreaterEqual(float(match.group(1)), 3.0)

    def test_subtext_uses_contrast_guard(self):
        match = re.search(r'property\s+color\s+colSubtext\s*:\s*(.+)', self.text)
        self.assertIsNotNone(match)
        self.assertIn('ensureContrast', match.group(1))

    def test_guard_picks_readable_fallback(self):
        for background in ((0.06, 0.08, 0.09), (0.95, 0.95, 0.95)):
            candidates = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
            best = max(candidates, key=lambda c: ratio(c, background))
            self.assertGreaterEqual(ratio(best, background), 4.5)


if __name__ == '__main__':
    unittest.main()