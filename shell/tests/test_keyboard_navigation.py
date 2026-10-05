#!/usr/bin/env python3
import re
import unittest
from pathlib import Path

SHELL_ROOT = Path(__file__).resolve().parents[1]
CONTROLS = SHELL_ROOT / 'shared' / 'controls'

FOCUSABLE = ('RippleButton.qml', 'IconButton.qml', 'SettingsRow.qml', 'SettingsActionRow.qml',
             'QuickToggleButton.qml', 'StyledSwitch.qml', 'MaterialSlider.qml',
             'MaterialTextField.qml', 'MaterialFilledTextField.qml', 'ActionButton.qml')
FOCUS_RING = ('RippleButton.qml', 'SettingsRow.qml', 'QuickToggleButton.qml', 'StyledSwitch.qml')


class KeyboardNavigationContracts(unittest.TestCase):
    def test_primary_controls_are_tab_reachable(self):
        missing = []
        for name in FOCUSABLE:
            text = (CONTROLS / name).read_text(encoding='utf-8')
            if not re.search(r'focusPolicy\s*:\s*Qt\.(StrongFocus|TabFocus)|activeFocusOnTab\s*:', text):
                missing.append(name)
        self.assertEqual(missing, [], f'Controls without keyboard focus: {missing}')

    def test_primary_controls_draw_a_focus_ring(self):
        missing = []
        for name in FOCUS_RING:
            text = (CONTROLS / name).read_text(encoding='utf-8')
            if 'visualFocus' not in text and 'activeFocus' not in text:
                missing.append(name)
            if 'colPrimary' not in text:
                missing.append(f'{name}:no-primary-outline')
        self.assertEqual(missing, [], f'Controls without a visible focus ring: {missing}')

    def test_focus_ring_uses_high_contrast_primary(self):
        text = (CONTROLS / 'RippleButton.qml').read_text(encoding='utf-8')
        block = text[text.index('border.color: Appearance.colors.colPrimary'):]
        self.assertIn('border.width: root.visualFocus ? 2 : 0', text)
        self.assertTrue(block)

    def test_accessible_names_are_declared(self):
        missing = []
        for name in FOCUSABLE:
            text = (CONTROLS / name).read_text(encoding='utf-8')
            if 'Accessible.name' not in text and 'Accessible.role' not in text:
                missing.append(name)
        self.assertEqual(missing, [], f'Controls without accessible metadata: {missing}')

    def test_decoration_is_hidden_from_screen_readers(self):
        for name in FOCUS_RING:
            text = (CONTROLS / name).read_text(encoding='utf-8')
            if 'Accessible.ignored' in text:
                self.assertIn('Accessible.ignored: true', text)

    def test_activation_keys_are_bound(self):
        for name in ('SettingsRow.qml', 'QuickToggleButton.qml'):
            text = (CONTROLS / name).read_text(encoding='utf-8')
            self.assertRegex(text, r'Keys\.onReturnPressed', f'{name} lacks Enter activation')
            self.assertRegex(text, r'Keys\.onSpacePressed', f'{name} lacks Space activation')


if __name__ == '__main__':
    unittest.main()