#!/usr/bin/env python3
import re
import unittest
from pathlib import Path

SHELL_ROOT = Path(__file__).resolve().parents[1]
APPEARANCE = SHELL_ROOT / 'shared' / 'theme' / 'Appearance.qml'
PREFERENCES = SHELL_ROOT / 'app' / 'services' / 'UiPreferences.qml'
THEME = SHELL_ROOT / 'app' / 'services' / 'ThemeService.qml'
PAGE = SHELL_ROOT / 'modules' / 'settings' / 'AccessibilityPage.qml'
ROUTES = SHELL_ROOT / 'modules' / 'settings' / 'settings-routes.json'


class AccessibilityContracts(unittest.TestCase):
    def setUp(self):
        self.appearance = APPEARANCE.read_text(encoding='utf-8')
        self.preferences = PREFERENCES.read_text(encoding='utf-8')
        self.theme = THEME.read_text(encoding='utf-8')
        self.page = PAGE.read_text(encoding='utf-8')
        self.routes = ROUTES.read_text(encoding='utf-8')

    def test_appearance_exposes_readability_knobs(self):
        for token in ('property real fontScale', 'property bool highContrast',
                      'property bool reduceTransparency', 'property bool lowPowerMode'):
            self.assertIn(token, self.appearance, f'Missing {token}')

    def test_high_contrast_raises_the_floor(self):
        self.assertIn('minTextContrast', self.appearance)
        self.assertRegex(self.appearance, r'minTextContrast\s*:\s*highContrast\s*\?\s*7\s*:\s*4\.5')

    def test_font_scale_is_applied_to_the_type_ramp(self):
        self.assertIn('function scaledFont', self.appearance)
        typography = (SHELL_ROOT / 'shared' / 'theme' / 'Typography.qml').read_text(encoding='utf-8')
        self.assertIn('Appearance.fontScale', typography)

    def test_reduce_transparency_collapses_alpha(self):
        for token in ('effectiveBackgroundTransparency', 'effectiveContentTransparency'):
            self.assertIn(token, self.appearance)
        self.assertNotIn('root.contentTransparency)', self.appearance.split('colors: QtObject')[1])

    def test_low_power_mode_implies_reduced_motion(self):
        self.assertRegex(self.appearance, r'effectiveReduceMotion\s*:\s*reduceMotion\s*\|\|\s*lowPowerMode')

    def test_preferences_persist_every_knob(self):
        for token in ('property real fontScale', 'property bool highContrast',
                      'property bool reduceTransparency', 'property bool lowPowerMode',
                      'property bool followSun'):
            self.assertIn(token, self.preferences, f'Missing {token}')
        for token in ('"fontScale"', '"highContrast"', '"reduceTransparency"',
                      '"lowPowerMode"', '"followSun"'):
            self.assertIn(token, self.preferences, f'Missing persisted {token}')

    def test_preferences_expose_setters(self):
        for name in ('setFontScale', 'setHighContrast', 'setReduceTransparency',
                     'setLowPowerMode', 'setFollowSun'):
            self.assertRegex(self.preferences, r'function\s+' + name + r'\s*\(')

    def test_font_scale_is_bounded(self):
        block = re.search(r'function\s+setFontScale\s*\([^)]*\)\s*\{(.*?)\n    \}', self.preferences, re.DOTALL)
        self.assertIsNotNone(block)
        self.assertIn('0.85', block.group(1))
        self.assertIn('1.5', block.group(1))

    def test_theme_service_syncs_every_knob(self):
        for token in ('Appearance.fontScale = UiPreferences.fontScale',
                      'Appearance.highContrast = UiPreferences.highContrast',
                      'Appearance.reduceTransparency = UiPreferences.reduceTransparency',
                      'Appearance.lowPowerMode = UiPreferences.lowPowerMode'):
            self.assertIn(token, self.theme, f'Missing sync for {token}')
        for signal in ('onFontScaleChanged', 'onHighContrastChanged', 'onReduceTransparencyChanged',
                       'onLowPowerModeChanged'):
            self.assertIn(signal, self.theme, f'Missing {signal}')

    def test_accessibility_page_is_routed(self):
        self.assertIn('general.accessibility', self.routes)
        self.assertIn('AccessibilityPage.qml', self.routes)

    def test_accessibility_page_exposes_every_toggle(self):
        for setter in ('UiPreferences.setReduceMotion', 'UiPreferences.setFontScale',
                       'UiPreferences.setHighContrast', 'UiPreferences.setReduceTransparency',
                       'UiPreferences.setLowPowerMode', 'UiPreferences.setFollowSun'):
            self.assertIn(setter, self.page, f'Page does not wire {setter}')

    def test_solar_theme_service_uses_weather_schedule(self):
        self.assertIn('WeatherService.dailyForecast', self.theme)
        self.assertIn('solarSunriseEpoch', self.theme)
        self.assertIn('solarSunsetEpoch', self.theme)
        self.assertIn('root.setThemeMode(mode)', self.theme)
        self.assertIn('solarScheduleAvailable', self.theme)

    def test_solar_timer_is_torn_down(self):
        destruction = self.theme[self.theme.index('Component.onDestruction'):]
        self.assertIn('solarThemeTimer.stop()', destruction)


if __name__ == '__main__':
    unittest.main()