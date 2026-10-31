"""T3 M1 contracts: the Caelestia-style preference atom suite.

The atoms land in shell/ui/ as a pure-QML presentation
library: every row extends ConnectedRect (the connected-card group form),
theme colours come exclusively from the Nyxuri singletons (Appearance), and
geometry, rhythm and type sizes come from NexusStyle — the unscaled 1:1 port
of Caelestia's tokens.hpp, so the settings surface keeps pixel parity with
the original instead of the fork-wide 0.85 dense-panel scale. These tests pin
the per-atom API surface so M3 page rebuilds cannot silently drift it, and
keep the pool free of upstream and side-effect imports.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROLS = REPO_ROOT / "shell" / "ui"

ATOMS = (
    "ConnectedRect.qml",
    "PreferenceHeader.qml",
    "PreferenceToggle.qml",
    "PreferenceSlider.qml",
    "PreferenceInput.qml",
    "PreferenceSelect.qml",
    "PreferenceStepper.qml",
    "PreferenceAction.qml",
    "PreferenceInfo.qml",
    "NexusSearchBar.qml",
    "NexusPageBase.qml",
)


def _source(name: str) -> str:
    return (CONTROLS / name).read_text(encoding="utf-8")


class TestSuiteShape(unittest.TestCase):
    """The pool exists, is complete, and holds nothing else."""

    def test_exactly_the_eleven_atoms_ship(self):
        self.assertTrue(CONTROLS.is_dir(), "ui/ directory missing")
        # S0-1: the atoms live flat in ui/ beside the control library, so the
        # pool check is membership — all eleven present, none missing.
        shipped = {p.name for p in CONTROLS.glob("*.qml")}
        missing = [name for name in ATOMS if name not in shipped]
        self.assertEqual(missing, [], f"missing atoms in ui/: {missing}")

    def test_no_upstream_or_sideeffect_imports(self):
        forbidden = (
            "import Caelestia",
            "import qs.services",
            "import qs.modules",
            "import Quickshell",
            "import qs.app",
        )
        for name in ATOMS:
            source = _source(name)
            for token in forbidden:
                self.assertNotIn(token, source, f"{name} imports {token}")

    def test_theme_truth_is_the_nyxuri_singletons(self):
        for name in ATOMS:
            source = _source(name)
            self.assertIn("qs.commons", source, f"{name} does not bridge theme tokens")
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", source),
                              f"{name} hardcodes a hex color")

    def test_geometry_comes_from_the_unscaled_nexus_tokens(self):
        # Pixel parity with Caelestia: no 0.85-scaled Metrics/Typography sizes
        # may leak into the atom pool (colors and animations stay Appearance).
        for name in ATOMS:
            source = _source(name)
            self.assertNotRegex(source, r"\bTypography\.", f"{name} uses scaled typography")
            self.assertIsNone(re.search(r"\bMetrics\.(?!scale\b)", source),
                              f"{name} uses scaled metrics")


class TestConnectedForm(unittest.TestCase):
    """first/last drive the connected-card rounding; groups share the container color."""

    def test_radius_and_color_contract(self):
        # Whitespace-insensitive: qmlformat reflows long ternaries, the
        # contract is the rounding logic, not the line breaks.
        source = re.sub(r"\s+", " ", _source("ConnectedRect.qml"))
        self.assertIn("property bool first", source)
        self.assertIn("property bool last", source)
        self.assertIn("color: Appearance.m3colors.m3surfaceContainer", source)
        self.assertIn("first ? NexusStyle.rounding.extraLarge : NexusStyle.rounding.extraSmall", source)
        self.assertIn("last ? NexusStyle.rounding.extraLarge : NexusStyle.rounding.extraSmall", source)
        # M2: whole-shape override for the NavPane's active pill and press morph.
        self.assertIn("property real uniformRadius: -1", source)
        self.assertEqual(source.count("root.uniformRadius >= 0 ? root.uniformRadius : root.group"), 4,
                         "uniformRadius must override all four corners")

    def test_row_atoms_sit_on_connected_rect(self):
        for name in ("PreferenceToggle.qml", "PreferenceSlider.qml", "PreferenceInput.qml",
                     "PreferenceSelect.qml", "PreferenceStepper.qml", "PreferenceAction.qml",
                     "PreferenceInfo.qml"):
            source = _source(name)
            self.assertRegex(source, re.compile(r"^ConnectedRect \{", re.MULTILINE),
                             f"{name} must root in ConnectedRect")

    def test_section_header_is_a_plain_label(self):
        source = _source("PreferenceHeader.qml")
        self.assertIn("property bool first", source)
        self.assertIn("Appearance.m3colors.m3onSurfaceVariant", source)
        self.assertIn("NexusStyle.font.labelMedium", source)


class TestRowAtoms(unittest.TestCase):
    """Per-atom API surface pinned for the M3 page rebuilds."""

    def test_toggle_row(self):
        source = _source("PreferenceToggle.qml")
        self.assertIn("signal toggled", source)
        # Optional leading icon (adapter rows, bluetooth trust/block/wake).
        self.assertIn('property string icon: ""', source)
        self.assertIn("property alias checked: toggleItem.checked", source)
        self.assertRegex(source, r"signal toggled\b")
        # Whole-row activation: a row-level press area plus the pill switch.
        self.assertIn("onClicked: root.toggle()", source)
        self.assertIn("StyledSwitch {", source)
        self.assertIn("onToggled: root.toggled()", source)
        self.assertIn("StateLayer {", source)

    def test_slider_row(self):
        source = _source("PreferenceSlider.qml")
        self.assertIn("signal moved(real value)", source)
        # Live-preview consumers (horizontal clock axes) persist on commit.
        self.assertIn("signal committed(real value)", source)
        self.assertIn("property real wheelStep:", source)
        self.assertIn("function onWheel(event: WheelEvent): void", source)
        # Slim Nexus slider: unstyled template Slider, visuals in contentItem.
        self.assertIn("import QtQuick.Templates", source)
        self.assertIn("property real pos: visualPosition", source)
        self.assertIn("when: dragArea.pressed", source)

    def test_input_row(self):
        source = _source("PreferenceInput.qml")
        self.assertIn("signal valueEdited(string value)", source)
        self.assertIn("signal editingFinished(string value)", source)
        self.assertIn("property var validate", source)
        self.assertIn("readonly property bool valid:", source)
        # Edits still pending when the page closes are flushed, not dropped.
        self.assertIn("Component.onDestruction:", source)
        self.assertIn("editingFinished(input.text)", source)
        # Breathing focus border + clear affordance.
        self.assertRegex(source, r"Behavior on border\.color")
        self.assertRegex(source, r"input\.activeFocus\s*\?\s*Appearance\.m3colors\.m3primary")
        self.assertIn('iconName: "clear"', source)

    def test_select_row(self):
        source = _source("PreferenceSelect.qml")
        self.assertIn("property alias model: splitButton.model", source)
        self.assertIn("property alias currentValue: splitButton.currentValue", source)
        self.assertIn("signal selected(string value)", source)
        self.assertIn("SplitMenuButton {", source)
        # Compositor input regions are injected by the page, not read here.
        self.assertIn("property var inputRegionService: null", source)
        # Caelestia SelectRow/PopupRow parity: optional leading icon and the
        # SplitButton fallback for unset selections (default applications).
        self.assertIn('property string icon: ""', source)
        self.assertIn("property alias fallbackText: splitButton.fallbackText", source)

    def test_stepper_row(self):
        source = _source("PreferenceStepper.qml")
        self.assertIn("signal moved(int value)", source)
        self.assertIn("MaterialStepper {", source)
        self.assertIn("onValueModified: value => root.moved(value)", source)

    def test_action_row(self):
        source = _source("PreferenceAction.qml")
        self.assertIn('property string trailingIcon: "chevron_right"', source)
        self.assertRegex(source, r"signal clicked\b")
        self.assertIn("animateChange: true", source)

    def test_info_row_is_readonly(self):
        source = _source("PreferenceInfo.qml")
        self.assertIn("property alias value: valueLabel.text", source)
        for token in ("MouseArea", "StateLayer", "signal clicked"):
            self.assertNotIn(token, source, f"PreferenceInfo must stay read-only: found {token}")


class TestWindowChrome(unittest.TestCase):
    """Search bar and page scaffold."""

    def test_search_bar_is_a_pill_textfield(self):
        source = _source("NexusSearchBar.qml")
        self.assertRegex(source, re.compile(r"^TextField \{", re.MULTILINE))
        self.assertIn("radius: NexusStyle.rounding.full", source)
        self.assertIn('text: "search"', source)
        self.assertIn("enabled: root.text.length > 0", source)
        # Caelestia fidelity: borderless capsule on surface-container-lowest
        # with a press overlay while unfocused; no outline, no focus frame.
        self.assertIn("color: Appearance.m3colors.m3surfaceContainerLowest", source)
        self.assertNotIn("border.", source, "the original pill carries no border")
        self.assertIn("StateLayer {", source)
        self.assertIn("pressed: !root.activeFocus && tapHandler.pressed", source)
        self.assertIn('iconName: "clear"', source)

    def test_page_base_keeps_navigation_with_the_host(self):
        source = _source("NexusPageBase.qml")
        self.assertIn("required property string title", source)
        self.assertIn("property bool isSubPage: false", source)
        self.assertRegex(source, r"signal backRequested\b")
        self.assertNotIn("NexusState", source, "navigation state must not leak into the scaffold")
        self.assertIn("default property Item contentChild", source)
        self.assertIn("readonly property int cappedWidth: Math.min(maxContentWidth, width)", source)
        self.assertIn("contentItem.children: root.contentChild ? [root.contentChild] : []", source)
        # Pages own their big title; the hosting window hides its shim.
        self.assertIn("readonly property bool rendersPageTitle: root.title.length > 0", source)


class TestNexusStyleParity(unittest.TestCase):
    """Every NexusStyle value is pinned against Caelestia tokens.hpp."""

    def test_token_values_match_the_upstream_header(self):
        source = (REPO_ROOT / "shell" / "ui" / "NexusStyle.qml").read_text(encoding="utf-8")
        pins = (
            "extraSmall: 4", "small: 8", "medium: 12", "large: 16",
            "largeIncreased: 20", "extraLarge: 28", "extraLargeIncreased: 32",
            "extraExtraLarge: 48",
            "labelSmall: 11", "bodySmall: 12", "labelMedium: 12",
            "bodyMedium: 14", "bodyLarge: 16", "titleMedium: 16",
            "titleLarge: 22", "headlineLarge: 28",
            "extraLarge: 48", "large: 32", "medium: 24", "small: 20",
            "heightMult: 0.7", "ratio: 16 / 9",
            "minWidth: 800", "minHeight: 500",
            "maxNavWidth: 480", "maxContentWidth: 800",
            "frameBand: 12",
        )
        for pin in pins:
            self.assertIn(pin, source, f"token drifted from tokens.hpp: {pin}")

    def test_medium_and_large_weights_follow_the_upstream_styles(self):
        source = (REPO_ROOT / "shell" / "ui" / "NexusStyle.qml").read_text(encoding="utf-8")
        self.assertIn("titleWeight: Font.Medium", source)
        self.assertIn("headlineWeight: Font.Medium", source)
        self.assertIn("labelMediumWeight: Font.Medium", source)


class TestWarmupAndI18n(unittest.TestCase):
    """KM4.6 rule + translation coverage for the atoms' own strings."""

    def test_controls_pool_is_in_the_slot_host_warmup(self):
        source = (REPO_ROOT / "shell" / "app" / "SlotHost.qml").read_text(encoding="utf-8")
        self.assertIn("import qs.ui", source,
                      "new synthesized qs.* pool must warm up in SlotHost")
        # The atoms now also reference the parent pool (NexusStyle).
        self.assertIn("import qs.plugins.settings", source,
                      "the unit root pool must stay warmed for the atoms' NexusStyle import")

    def test_atom_strings_are_translated(self):
        zh = (REPO_ROOT / "shell" / "commons" / "i18n" / "zh_CN.toml").read_text(encoding="utf-8")
        for key in ("Go back", "Clear"):
            self.assertIn(f'"{key}"', zh)


if __name__ == "__main__":
    unittest.main()
