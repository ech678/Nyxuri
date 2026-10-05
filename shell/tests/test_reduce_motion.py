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
        self.animations = (SHELL_ROOT / 'shared' / 'theme' / 'Animations.qml').read_text(encoding='utf-8')

    def test_appearance_declares_motion_api(self):
        self.assertIn('property bool reduceMotion', self.appearance)
        self.assertIn('readonly property bool animationsEnabled', self.appearance)
        self.assertIn('readonly property real motionScale', self.appearance)

    def test_animations_enabled_follows_reduce_motion(self):
        match = re.search(r'readonly\s+property\s+bool\s+animationsEnabled\s*:\s*(.+)', self.appearance)
        self.assertIsNotNone(match)
        self.assertIn('effectiveReduceMotion', match.group(1))
        self.assertIn('readonly property bool effectiveReduceMotion', self.appearance)

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

    def test_motion_scale_reaches_literal_durations(self):
        self.assertRegex(self.appearance, r'function\s+motionDuration\s*\(')
        self.assertRegex(self.appearance, r'function\s+motionLoopDuration\s*\(')
        scaled = re.search(r'function\s+motionDuration\s*\([^)]*\)\s*\{([^}]*)\}', self.appearance)
        self.assertIsNotNone(scaled)
        self.assertIn('effectiveMotionScale', scaled.group(1))
        self.assertIn('effectiveMotionScale', self.appearance)

    def test_no_literal_animation_durations_remain(self):
        offenders = []
        opening = re.compile(r'\b(NumberAnimation|ColorAnimation|PauseAnimation|PropertyAnimation|'
                             r'RotationAnimation|Vector3dAnimation|SpringAnimation|SmoothedAnimation|'
                             r'AnchorAnimation)\s*\{')
        literal = re.compile(r'\bduration:\s*\d+\b')
        for base in SOURCE_DIRS:
            for path in (SHELL_ROOT / base).rglob('*.qml'):
                lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
                depth = 0
                for index, line in enumerate(lines):
                    if depth > 0:
                        if literal.search(line):
                            offenders.append(f'{path.relative_to(SHELL_ROOT).as_posix()}:{index + 1}')
                        depth += line.count('{') - line.count('}')
                        continue
                    if opening.search(line):
                        if literal.search(line):
                            offenders.append(f'{path.relative_to(SHELL_ROOT).as_posix()}:{index + 1}')
                        depth = line.count('{') - line.count('}')
        self.assertEqual(sorted(offenders), [], f'Literal durations bypass motion scaling: {sorted(offenders)}')

    def test_looping_animations_do_not_scale_to_zero(self):
        self.assertNotIn('reduceMotion', re.search(r'function\s+motionLoopDuration\s*\([^)]*\)\s*\{([^}]*)\}',
                                                  self.appearance).group(1))
        offenders = []
        for base in SOURCE_DIRS:
            for path in (SHELL_ROOT / base).rglob('*.qml'):
                text = path.read_text(encoding='utf-8', errors='ignore')
                if 'Animation.Infinite' in text and 'motionDuration(' in text:
                    offenders.append(path.relative_to(SHELL_ROOT).as_posix())
        self.assertEqual(sorted(offenders), [], f'Infinite loops must not use scaled durations: {sorted(offenders)}')

    def test_keystone_motion_scales_with_preference(self):
        keystone = (SHELL_ROOT / 'modules' / 'keystone' / 'KeystoneMotion.qml').read_text(encoding='utf-8')
        for name in ('expandingDuration', 'shrinkingDuration', 'radiusDuration', 'hoverDuration',
                     'audioExpandDuration', 'audioContentEnterDuration', 'audioContentExitDuration',
                     'audioCollapseDuration'):
            match = re.search(r'readonly\s+property\s+int\s+' + name + r'\s*:\s*(.+)', keystone)
            self.assertIsNotNone(match, f'KeystoneMotion.{name} is missing')
            self.assertIn('motionDuration', match.group(1), f'{name} bypasses motion scaling')

    def test_keystone_curves_live_in_the_token_layer(self):
        keystone = (SHELL_ROOT / 'modules' / 'keystone' / 'KeystoneMotion.qml').read_text(encoding='utf-8')
        self.assertIn('Animations.curves.keystoneExpand', keystone)
        self.assertIn('Animations.curves.keystoneCollapse', keystone)
        self.assertIn('keystoneExpand', self.animations)
        self.assertIn('keystoneCollapse', self.animations)

    def test_dock_motion_scales_with_preference(self):
        offenders = []
        for path in (SHELL_ROOT / 'modules' / 'dock').rglob('*.qml'):
            text = path.read_text(encoding='utf-8', errors='ignore')
            for line in text.split('\n'):
                if re.search(r'duration:\s*DockMotion\.(enter|exit|reflow)Duration', line):
                    offenders.append(path.name)
                if re.search(r'\.duration\s*=\s*retiring\s*\?\s*DockMotion', line):
                    offenders.append(path.name)
        self.assertEqual(sorted(set(offenders)), [], f'Dock durations bypass scaling: {sorted(set(offenders))}')

    def test_no_raw_animation_durations_object_is_consumed(self):
        offenders = []
        for base in SOURCE_DIRS:
            for path in (SHELL_ROOT / base).rglob('*.qml'):
                text = path.read_text(encoding='utf-8', errors='ignore')
                if 'Animations.durations.' not in text:
                    continue
                if 'Appearance.motionDuration' not in text:
                    offenders.append(path.relative_to(SHELL_ROOT).as_posix())
        self.assertEqual(offenders, [], f'Raw duration tokens bypass scaling: {offenders}')

    def test_ripple_uses_a_scaled_duration(self):
        self.assertRegex(self.appearance, r'rippleDuration\s*:\s*Appearance\.motionDuration\(')

    def test_color_transition_is_gated_for_first_paint(self):
        self.assertIn('property bool colorTransitionEnabled', self.appearance)
        self.assertIn('enabled: Appearance.colorTransitionEnabled', self.appearance)
        self.assertIn('Appearance.colorTransitionEnabled = false', self.theme)
        self.assertIn('Appearance.colorTransitionEnabled = true', self.theme)

    def test_surface_entrances_are_scaled(self):
        for relative, token in (
            ('modules/osd/OsdSurface.qml', 'revealProgress'),
            ('modules/notifications/NotificationPopupHost.qml', 'revealProgress'),
            ('modules/lock/DefaultLockContent.qml', 'entranceProgress'),
            ('modules/switcher/WindowSwitcherSurface.qml', 'revealProgress'),
            ('modules/regionselector/RegionSelectionWindow.qml', 'revealProgress'),
        ):
            text = (SHELL_ROOT / relative).read_text(encoding='utf-8')
            self.assertIn(token, text, f'{relative} lacks {token}')
            self.assertIn('Appearance.animationsEnabled', text, f'{relative} ignores reduce motion')

    def test_material_symbol_fill_morphs_instead_of_snapping(self):
        symbol = (SHELL_ROOT / 'shared' / 'controls' / 'MaterialSymbol.qml').read_text(encoding='utf-8')
        self.assertIn('Behavior on fill', symbol)
        self.assertIn('Appearance.animationsEnabled', symbol)
        self.assertRegex(symbol, r'Behavior\s+on\s+fill\s*\{[^}]*expressiveDefaultEffects')

    def test_workspace_size_and_color_share_tokens(self):
        text = (SHELL_ROOT / 'modules' / 'bar' / 'workspaces' / 'Workspaces.qml').read_text(encoding='utf-8')
        self.assertIn('Appearance.animation.elementMoveFast.duration', text)
        self.assertIn('Appearance.animation.expressiveFastEffects.duration', text)


if __name__ == '__main__':
    unittest.main()