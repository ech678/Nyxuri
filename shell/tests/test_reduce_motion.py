import re
import unittest
from pathlib import Path

SHELL_ROOT = Path(__file__).resolve().parents[1]
APPEARANCE = SHELL_ROOT / 'shared' / 'theme' / 'Appearance.qml'
PREFERENCES = SHELL_ROOT / 'app' / 'services' / 'UiPreferences.qml'
THEME = SHELL_ROOT / 'app' / 'services' / 'ThemeService.qml'
SOURCE_DIRS = ('app', 'modules', 'shared')
APPEARANCE_REF = re.compile(r'Appearance\.([A-Za-z_][A-Za-z0-9_]*)')
DECLARED = re.compile(r'\b(?:readonly\s+)?property\s+(?:bool|real|string|int|color|var|QtObject)\s+([A-Za-z_][A-Za-z0-9_]*)')
FUNCTION = re.compile(r'\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')


class ReduceMotionContracts(unittest.TestCase):
    def setUp(self):
        self.appearance = APPEARANCE.read_text(encoding='utf-8')
        self.preferences = PREFERENCES.read_text(encoding='utf-8')
        self.theme = THEME.read_text(encoding='utf-8')

    def test_appearance_declares_motion_api(self):
        self.assertIn('property bool reduceMotion', self.appearance)
        self.assertIn('readonly property bool animationsEnabled', self.appearance)
        self.assertIn('readonly property real motionScale', self.appearance)

    def test_animations_enabled_follows_reduce_motion(self):
        match = re.search(r'readonly\s+property\s+bool\s+animationsEnabled\s*:\s*(.+)', self.appearance)
        self.assertIsNotNone(match)
        self.assertIn('reduceMotion', match.group(1))

    def test_preferences_persist_reduce_motion(self):
        self.assertIn('property bool reduceMotion', self.preferences)
        self.assertIn('"reduceMotion": root.reduceMotion', self.preferences)
        self.assertIn('parsed.reduceMotion', self.preferences)

    def test_preferences_expose_setter(self):
        self.assertRegex(self.preferences, r'function\s+setReduceMotion\s*\(')
        self.assertRegex(self.preferences, r'function\s+toggleReduceMotion\s*\(')

    def test_theme_service_syncs_preference(self):
        self.assertIn('Appearance.reduceMotion = UiPreferences.reduceMotion', self.theme)
        self.assertIn('onReduceMotionChanged', self.theme)

    def test_no_dangling_appearance_members(self):
        declared = set(DECLARED.findall(self.appearance)) | set(FUNCTION.findall(self.appearance))
        dangling = set()
        for base in SOURCE_DIRS:
            for path in (SHELL_ROOT / base).rglob('*'):
                if path.suffix not in ('.qml', '.js'):
                    continue
                if path == APPEARANCE:
                    continue
                text = path.read_text(encoding='utf-8', errors='ignore')
                for member in APPEARANCE_REF.findall(text):
                    if member not in declared:
                        dangling.add(f'{path.relative_to(SHELL_ROOT).as_posix()}:{member}')
        self.assertEqual(sorted(dangling), [], f'Appearance members referenced but not declared: {sorted(dangling)}')


if __name__ == '__main__':
    unittest.main()