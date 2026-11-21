"""D0/D1 design-unification contract tests.

Pins the state-layer unification (one M3 StateLayer, live toggled colors,
opacity defaults from Appearance.interaction) and the D1 bar fixes (media
fill contract, weather wiring, visualizer + weather whitelisting, the
time.dateFormat key).

Runtime evidence comes from scripts/dev/probe-bar.sh (d1 report section);
these tests pin the structural contracts the probe cannot see.
"""

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
UI_DIR = os.path.join(SHELL, "ui")


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class StateLayerUnificationTest(unittest.TestCase):
    """D0: one state-layer truth — the M3 ui/StateLayer."""

    def test_end4_enum_state_layer_stays_retired(self):
        self.assertFalse(os.path.exists(os.path.join(BAR_DIR, "StateLayer.qml")))
        self.assertFalse(os.path.exists(os.path.join(BAR_DIR, "StateOverlay.qml")))

    def test_ui_state_layer_carries_drag_state(self):
        content = read(os.path.join(UI_DIR, "StateLayer.qml"))
        self.assertIn("property bool dragged: false", content)
        self.assertIn("dragOpacity: Appearance.interaction.dragStateLayerOpacity", content)
        # Priority: press > drag > hover > focus > selected.
        self.assertLess(content.index("root.pressed ? root.pressedColor"), content.index("root.dragged ? root.dragColor"))

    def test_interaction_tokens_match_contract(self):
        content = read(os.path.join(SHELL, "commons", "Appearance.qml"))
        self.assertIn("hoverStateLayerOpacity: 0.08", content)
        self.assertIn("focusStateLayerOpacity: 0.10", content)
        self.assertIn("pressedStateLayerOpacity: 0.10", content)
        self.assertIn("dragStateLayerOpacity: 0.16", content)
        self.assertIn("selectedStateLayerOpacity: 0.10", content)

    def test_ripple_button_opacity_chain_defaults_to_contract(self):
        content = read(os.path.join(UI_DIR, "RippleButton.qml"))
        # The dead `stateLayerOpacity: 1` chain is gone; all four opacities
        # default to the interaction tokens.
        self.assertNotIn("property real stateLayerOpacity", content)
        self.assertNotIn("hoverStateLayerOpacity: root.stateLayerOpacity", content)
        for prop in ("hoverStateLayerOpacity", "focusStateLayerOpacity",
                     "pressedStateLayerOpacity", "selectedStateLayerOpacity"):
            self.assertRegex(content, rf"property real {prop}: Appearance\.interaction\.")

    def test_ripple_button_toggled_colors_are_live(self):
        """The tray-arrow bug: colBackgroundToggled* were plain dead
        properties — assignments never reached the background."""
        content = read(os.path.join(UI_DIR, "RippleButton.qml"))
        self.assertIn("color: root.toggled ? (root.pointerHovered ? root.colBackgroundToggledHover : root.colBackgroundToggled) : root.containerColor", content)
        self.assertIn("color: root.toggled ? root.colRippleToggled : root.rippleColor", content)

    def test_workspaces_consume_the_m3_state_layer(self):
        content = read(os.path.join(BAR_DIR, "Workspaces.qml"))
        self.assertIn("StateLayer {", content)
        self.assertIn("dragged: true", content)
        self.assertNotIn("StateOverlay", content.replace("// D0: the end4 StateOverlay", ""))

    def test_no_state_layer_opacity_workarounds_left(self):
        """The 26 per-callsite `stateLayerOpacity: Appearance.interaction...`
        patches were workarounds for the dead default; with sane defaults they
        must stay deleted (the property no longer exists)."""
        pattern = re.compile(r"^\s*stateLayerOpacity:", re.MULTILINE)
        for root_dir, _, files in os.walk(SHELL):
            if "references" in root_dir:
                continue
            for name in files:
                if not name.endswith(".qml"):
                    continue
                content = read(os.path.join(root_dir, name))
                self.assertIsNone(pattern.search(content), f"{name} re-adds stateLayerOpacity")


class MediaFillContractTest(unittest.TestCase):
    """D1 quick fix: the material row fills the clamped widget and elides
    instead of centering an over-wide cluster (the overflow bug)."""

    def test_material_row_fills_and_elides(self):
        content = read(os.path.join(BAR_DIR, "Media.qml"))
        self.assertIn("clip: true", content)
        self.assertIn("id: materialRow", content)
        material_section = content[content.index("id: materialRow"):]
        self.assertIn("anchors.fill: parent", material_section)
        # Both text pairs cap at 120 and absorb the leftover width.
        self.assertEqual(material_section.count("Layout.maximumWidth: 120"), 4)
        self.assertGreaterEqual(material_section.count("Layout.fillWidth: true"), 4)

    def test_iNir_clamp_formula_unchanged(self):
        """The width authority stays the iNiR clamp; only the inner layout
        adapted. Defaults keep the user's chosen 160/300 (D4b: the clamp
        bounds are the media entry's min/maxWidth axes)."""
        content = read(os.path.join(BAR_DIR, "Media.qml"))
        self.assertIn("Math.max(root.mediaMinWidth, Math.min((isMaterial ? materialRow.implicitWidth : rowLayout.implicitWidth + 8), root.mediaMaxWidth))", content)
        self.assertIn('BarWidgetDefaults.option("media", root.widgetEntry, "minWidth")', content)
        self.assertIn('BarWidgetDefaults.option("media", root.widgetEntry, "maxWidth")', content)
        defaults = read(os.path.join(SHELL, "services", "BarWidgetDefaults.js"))
        self.assertIn("minWidth: 160", defaults)
        self.assertIn("maxWidth: 300", defaults)


class D1WeatherWiringTest(unittest.TestCase):
    """D1: WeatherBar/Popup consume WeatherService — the iNiR `Weather`
    singleton never existed here (22 dead bindings)."""

    def test_weather_bar_uses_weather_service(self):
        bar = read(os.path.join(BAR_DIR, "WeatherBar.qml"))
        self.assertIn("WeatherService.acquire", bar)
        self.assertIn("WeatherService.release", bar)
        self.assertIn("WeatherService.currentIconName", bar)
        self.assertNotIn("Weather.", bar.replace("WeatherService.", "").replace("WeatherPopup", ""))
        self.assertNotIn("Icons.getWeatherIcon(", bar)

    def test_weather_popup_uses_weather_service(self):
        popup = read(os.path.join(BAR_DIR, "WeatherPopup.qml"))
        self.assertIn("WeatherService.currentTemperatureC", popup)
        self.assertIn("WeatherService.dailyForecast", popup)
        self.assertNotIn("Icons.getWeatherIcon(", popup)

    def test_weather_and_visualizer_whitelisted(self):
        defaults = read(os.path.join(SHELL, "services", "BarWidgetDefaults.js"))
        self.assertIn('"weather"', defaults)
        self.assertIn('"visualizer"', defaults)
        files = read(os.path.join(BAR_DIR, "BarWidgetFiles.js"))
        self.assertIn('weather: "WeatherBar.qml"', files)
        self.assertIn('visualizer: "Visualizer.qml"', files)


class DateFormatKeyTest(unittest.TestCase):
    """D1: time.dateFormat — iNiR semantics, a Qt format pattern for the long
    date form; empty keeps the stock shape."""

    def test_datetime_reads_the_key(self):
        # D4b: the long-form pattern is the clock entry's dateFormat axis —
        # ClockWidget formats per instance; DateTime keeps only the fixed
        # short form.
        content = read(os.path.join(SHELL, "services", "DateTime.qml"))
        self.assertIn('Qt.formatDateTime(clock.date, "dd/MM")', content)
        self.assertNotIn("property string date:", content)
        clock = read(os.path.join(BAR_DIR, "ClockWidget.qml"))
        self.assertIn('BarWidgetDefaults.option("clock", root.widgetEntry, "dateFormat")', clock)
        self.assertIn('Qt.formatDateTime(root.today, root.dateFormat)', clock)

    def test_key_persists_and_bridges(self):
        # D4b: persistence is the entry override + the v4 fold of the old
        # [time].dateFormat key; there is no global store key or bridge.
        migrations = read(os.path.join(SHELL, "services", "ConfigMigrations.js"))
        self.assertIn('id === "clock"', migrations)
        self.assertIn("entry.dateFormat = legacyDateFormat", migrations)
        config = read(os.path.join(SHELL, "services", "PersonalizationConfig.qml"))
        self.assertNotIn("timeDateFormat", config)


if __name__ == "__main__":
    unittest.main()
