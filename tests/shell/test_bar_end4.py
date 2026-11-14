"""B4 bar reskin and cornerStyle contract tests.

Verifies:
  - Promoted end4 baseline files exist in shell/plugins/bar/ and carry GPL-3 Fork & Trim headers
  - No bare import qs statements in the promoted components
  - BarGroup.qml has trimmed dead paths (BarGroupStylePopup, widgetStyles) and manages child backgroundVisible
  - Divisor.qml supports rect/dot/space styles and connects to PersonalizationConfig
  - BarContent.qml registers "divisor" and "island" in its widget URL map
  - DynamicIsland.qml wires isMaterial to PersonalizationConfig.barCornerStyle
  - PersonalizationConfig defines barCornerStyles, barBorderlessModes, barDividerStyles, and includes "divisor"
  - BarContent.qml implements 3-lane cornerStyle, centerOnly mode, and material pill wrapping
  - HorizontalBarWindow.qml and VerticalBarWindow.qml implement roundDecorators and dynamic exclusiveThickness
"""

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAR_DIR = os.path.join(REPO_ROOT, "shell", "plugins", "bar")
SERVICES_DIR = os.path.join(REPO_ROOT, "shell", "services")


def read_bar_file(filename):
    with open(os.path.join(BAR_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def read_services_file(filename):
    with open(os.path.join(SERVICES_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


class BarEnd4ContractTest(unittest.TestCase):

    def test_promoted_files_exist(self):
        promoted = [
            "RoundCorner.qml",
            "Divisor.qml",
            "BarGroup.qml",
            "StyledPopupHeaderRow.qml",
            "StyledPopupValueRow.qml",
        ]
        for name in promoted:
            path = os.path.join(BAR_DIR, name)
            self.assertTrue(os.path.isfile(path), f"Missing promoted file {name} in {BAR_DIR}")

    def test_fork_and_trim_headers(self):
        for name in ["RoundCorner.qml", "Divisor.qml", "BarGroup.qml", "StyledPopupHeaderRow.qml", "StyledPopupValueRow.qml"]:
            content = read_bar_file(name)
            self.assertIn("Fork & Trim: end4-pC", content, f"{name} missing Fork & Trim header")
            self.assertIn("GPL-3", content, f"{name} missing GPL-3 notice")

    def test_no_bare_import_qs(self):
        for name in ["RoundCorner.qml", "Divisor.qml", "BarGroup.qml", "StyledPopupHeaderRow.qml", "StyledPopupValueRow.qml", "BarContent.qml"]:
            content = read_bar_file(name)
            for line in content.splitlines():
                stripped = line.strip()
                self.assertFalse(
                    stripped == "import qs" or stripped.startswith("import qs "),
                    f"{name} contains invalid bare 'import qs': {line}"
                )

    def test_bar_group_trims_and_bindings(self):
        content = read_bar_file("BarGroup.qml")
        # B8.1: the group is a full end4 fork again — the per-widget style
        # editor is wired, and persistence goes through PersonalizationConfig
        # instead of the read-only Config bridge.
        self.assertIn("BarGroupStylePopup", content, "BarGroup must wire the right-click style editor")
        self.assertIn("PersonalizationConfig.setBarWidgetStyle", content, "widget styles must persist via PersonalizationConfig")
        self.assertIn("resolvedGroupColor", content, "BarGroup must consume bar.groupColor")
        self.assertIn("paintBackground", content, "BarGroup must honour paintBackground")
        self.assertIn("isSegmented", content, "BarGroup must implement segmented borders")
        self.assertIn("isMaterial", content)
        self.assertIn("startRadius", content)
        self.assertIn("endRadius", content)

    def test_bar_content_centered_lanes(self):
        content = read_bar_file("BarContent.qml")
        self.assertIn("anchors.centerIn: parent", content, "middle lane must be anchored to the optical centre")
        self.assertNotIn("hostScale", content, "the iNiR compression clamp is retired (NaN source)")
        self.assertNotIn("centerHostX", content, "the iNiR compression clamp is retired (NaN source)")
        self.assertIn('"island"', content, "island must be in the material-pill blacklist")
        self.assertIn("bar.m3.layouts", content)

    def test_divisor_contracts(self):
        content = read_bar_file("Divisor.qml")
        self.assertIn("PersonalizationConfig.barDividerStyle", content)
        self.assertIn("isMaterial", content)
        self.assertIn("vertical", content)

    def test_component_loader_registrations(self):
        content = read_bar_file("BarContent.qml")
        self.assertIn('"divisor": "./Divisor.qml"', content)
        self.assertIn('"island": "./DynamicIsland.qml"', content)

    def test_dynamic_island_is_material_binding(self):
        content = read_bar_file("DynamicIsland.qml")
        self.assertIn("Config.options.bar.cornerStyle === 3", content)
        self.assertIn("Config.options.bar.cornerStyle === 4", content)

    def test_personalization_config_bar_keys(self):
        content = read_services_file("PersonalizationConfig.qml")
        self.assertIn("barCornerStyles", content)
        self.assertIn("barCornerStyle", content)
        self.assertIn("barBorderlessModes", content)
        self.assertIn("barBorderless", content)
        self.assertIn("barDividerStyles", content)
        self.assertIn("barDividerStyle", content)
        self.assertIn("barGroupColorOptions", content)
        self.assertIn("barWidgetStyles", content)
        self.assertIn('"divisor"', content)
        self.assertIn("setBarCornerStyle", content)
        self.assertIn("setBarBorderless", content)
        self.assertIn("setBarDividerStyle", content)
        self.assertIn("setBarWidgetStyle", content)

    def test_bar_content_contracts(self):
        content = read_bar_file("BarContent.qml")
        self.assertIn("centerOnly", content)
        self.assertIn("barBackground", content)
        self.assertIn("centerPill", content)
        self.assertIn("leftMaterialPill", content)
        self.assertIn("centerMaterialPill", content)
        self.assertIn("rightMaterialPill", content)
        self.assertIn("BarGroup", content)

    def test_bar_windows_screen_corners_and_exclusive_zone(self):
        content = read_bar_file("Bar.qml")
        self.assertIn("roundDecorators", content)
        self.assertIn("shownExclusiveZone", content)

    def test_bar_and_island_ipc_handlers(self):
        content = read_bar_file("Bar.qml")
        self.assertIn('target: "bar"', content)
        self.assertIn("function toggle(): string", content)
        self.assertIn("function open(): string", content)
        self.assertIn("function close(): string", content)
        self.assertIn('target: "island"', content)
        self.assertIn("function state(): string", content)
        # Recording is parked; the IPC face must not promise it.
        self.assertNotIn("stopRecording", content)


if __name__ == "__main__":
    unittest.main()
