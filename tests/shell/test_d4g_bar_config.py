"""D4g batch two contract tests: the bar widget rail capability catalog.

Pins the D4g 批二 contract (shell/ROADMAP.md, D4g row), corrected by 批三:
- every catalog entry declares `orientations`; a vertical-capable entry
  additionally declares `verticalMode`, and the pairing is exact (a
  missing `verticalMode` IS the "no rail face yet" verdict — no fourth
  value);
- the rail syntax vocabulary is closed (stack / rotate / iconPopup, D-9)
  and the per-widget classification is pinned as the audit result. 批三
  correction: clock and systemMonitor always had B9.4-era rail faces
  (the roadmap claim was wrong), and the island gained its compact rail
  face — every widget is rail-capable now, so the absence verdict has no
  current exemplar (it stays the protocol for future widgets);
- the settings faces consume the catalog verdict to disable and explain
  (picker blocks the add, lane rows annotate the subtitle, the instance
  page shows the capability note) — while the engine consumes none of it;
- 批三: the island mounts on the rail as the compact face growing along
  the track (the old rail-only island drop is retired) and the clock's
  rail face is the caelestia stack (TextMetrics optical matching).
"""

from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
SERVICES_DIR = os.path.join(SHELL, "services")
UI_DIR = os.path.join(SHELL, "ui")

VOCABULARY = ("stack", "rotate", "iconPopup")

# The audit verdict per widget id: (orientations, verticalMode or None).
# 批三 correction: clock and systemMonitor always had B9.4-era rail faces
# (fixed-size stack / gauge column), and the island gained its compact
# rail face — the "no rail face" verdict has no current exemplar.
EXPECTED_CAPABILITY = {
    "island": (["horizontal", "vertical"], "stack"),
    "clock": (["horizontal", "vertical"], "stack"),
    "tray": (["horizontal", "vertical"], "stack"),
    "systemMonitor": (["horizontal", "vertical"], "stack"),
    "weather": (["horizontal", "vertical"], "stack"),
    "visualizer": (["horizontal", "vertical"], "stack"),
    "battery": (["horizontal", "vertical"], "rotate"),
    "systemIcons": (["horizontal", "vertical"], "stack"),
    "quickSettings": (["horizontal", "vertical"], "stack"),
    "utilButtons": (["horizontal", "vertical"], "stack"),
    "launcherButton": (["horizontal", "vertical"], "stack"),
    "powerButton": (["horizontal", "vertical"], "stack"),
    "workspaces": (["horizontal", "vertical"], "stack"),
    "activeWindow": (["horizontal", "vertical"], "iconPopup"),
    "media": (["horizontal", "vertical"], "iconPopup"),
    "separator": (["horizontal", "vertical"], "stack"),
    "spacer": (["horizontal", "vertical"], "stack"),
}


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def js_ids(content: str, header: str) -> set[str]:
    """Extract the quoted ids under `var <header> = [ ... ]` (flat list)."""
    match = re.search(rf"var {header} = \[(.*?)\];", content, re.S)
    assert match, f"{header} list not found"
    return set(re.findall(r'"([a-zA-Z_][a-zA-Z0-9_]*)"', match.group(1)))


def catalog_blocks(content: str) -> dict[str, str]:
    """Extract each entry block of the catalog `all` array, keyed by id.

    The scan stops at the array terminator (the first `]` back at the
    property's four-space indent), so the helper functions below the
    array are never picked up.
    """
    start = content.index("readonly property var all: [")
    end = content.index("\n    ]", start)
    blocks: dict[str, str] = {}
    for match in re.finditer(r"\{([^{}]*)\}", content[start:end], re.S):
        block = match.group(0)
        id_match = re.search(r'id: "([a-zA-Z_][a-zA-Z0-9_]*)"', block)
        if id_match:
            blocks[id_match.group(1)] = block
    return blocks


def entry_orientations(block: str) -> list[str]:
    match = re.search(r"orientations: \[([^\]]*)\]", block)
    assert match, f"entry has no orientations field:\n{block}"
    return re.findall(r'"([a-zA-Z]+)"', match.group(1))


def entry_vertical_mode(block: str) -> str | None:
    match = re.search(r'verticalMode: "([a-zA-Z]+)"', block)
    return match.group(1) if match else None


class CapabilityCatalogTest(unittest.TestCase):
    """The catalog carries the rail capability metadata for every widget."""

    @classmethod
    def setUpClass(cls):
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarWidgetDefaults.js"))
        cls.catalog = read(os.path.join(UI_DIR, "BarWidgetCatalog.qml"))
        cls.ids = js_ids(cls.defaults, "IDS")
        cls.blocks = catalog_blocks(cls.catalog)

    def test_every_widget_has_a_capability_block(self):
        self.assertEqual(self.ids, set(self.blocks),
                         "every registered widget id needs a catalog entry")

    def test_orientation_fields_are_well_formed(self):
        for widget_id, block in self.blocks.items():
            orientations = entry_orientations(block)
            self.assertTrue(orientations, f"{widget_id}: empty orientations")
            for value in orientations:
                self.assertIn(value, ("horizontal", "vertical"),
                              f"{widget_id}: unknown orientation {value!r}")
            self.assertEqual(orientations[0], "horizontal",
                             f"{widget_id}: horizontal must come first")

    def test_vertical_mode_pairs_with_capability(self):
        for widget_id, block in self.blocks.items():
            vertical = "vertical" in entry_orientations(block)
            mode = entry_vertical_mode(block)
            if vertical:
                self.assertIsNotNone(
                    mode, f"{widget_id}: rail-capable but no verticalMode")
                self.assertIn(mode, VOCABULARY,
                              f"{widget_id}: verticalMode {mode!r} outside the D-9 vocabulary")
            else:
                self.assertIsNone(
                    mode, f"{widget_id}: no rail face yet must not declare a verticalMode")

    def test_vocabulary_is_exported_and_closed(self):
        match = re.search(r"readonly property var verticalModes: \[([^\]]*)\]", self.catalog)
        self.assertIsNotNone(match, "the catalog must export the verticalModes vocabulary")
        exported = re.findall(r'"([a-zA-Z]+)"', match.group(1))
        self.assertEqual(list(VOCABULARY), exported,
                         "the exported vocabulary drifted from the D-9 three syntaxes")

    def test_lookup_helpers_exist(self):
        self.assertIn("function supportsVertical(id)", self.catalog)
        self.assertIn("function verticalMode(id)", self.catalog)

    def test_audit_classification_is_pinned(self):
        for widget_id, (orientations, mode) in EXPECTED_CAPABILITY.items():
            block = self.blocks[widget_id]
            self.assertEqual(entry_orientations(block), orientations,
                             f"{widget_id}: orientations drifted from the audit verdict")
            self.assertEqual(entry_vertical_mode(block), mode,
                             f"{widget_id}: verticalMode drifted from the audit verdict")


class SettingsEnforcementTest(unittest.TestCase):
    """The settings faces disable and explain; the engine stays out."""

    @classmethod
    def setUpClass(cls):
        cls.picker = read(os.path.join(BAR_DIR, "BarWidgetPickerPopup.qml"))
        cls.lane_section = read(os.path.join(BAR_DIR, "BarLaneSection.qml"))
        cls.widget_page = read(os.path.join(BAR_DIR, "BarWidgetPage.qml"))
        cls.bar_content = read(os.path.join(BAR_DIR, "BarContent.qml"))

    def test_picker_blocks_rail_less_widgets(self):
        # The picker targets the selected bar; the orientation gate rides
        # the same axes the lane editor already reads.
        self.assertIn('PersonalizationConfig.barAxes.position === "left" || PersonalizationConfig.barAxes.position === "right"', self.picker)
        self.assertIn("blockedOrientation", self.picker)
        self.assertIn("widgetCatalog.supportsVertical(modelData.value)", self.picker)
        self.assertIn('I18n.tr("Not available on a vertical bar")', self.picker)
        self.assertIn("enabled: !blocked", self.picker)

    def test_lane_rows_annotate_rail_less_entries(self):
        self.assertIn('PersonalizationConfig.barAxes.position === "left" || PersonalizationConfig.barAxes.position === "right"', self.lane_section)
        self.assertIn("root.barVertical && !root.widgetCatalog.supportsVertical(entry.widgetId)", self.lane_section)
        self.assertIn('I18n.tr("Not available on a vertical bar")', self.lane_section)

    def test_instance_page_shows_the_capability_note(self):
        self.assertIn("editingOnRail", self.widget_page)
        self.assertIn("!widgetCatalog.supportsVertical(root.widgetId)", self.widget_page)
        self.assertIn('I18n.tr("Vertical bar")', self.widget_page)
        self.assertIn('I18n.tr("This widget has no vertical face yet")', self.widget_page)

    def test_engine_consumes_none_of_the_catalog_verdict(self):
        # Mounting decisions come from the host's own filterLayout (system
        # gates), not from the capability data.
        self.assertNotIn("supportsVertical", self.bar_content)
        self.assertNotIn("verticalMode", self.bar_content)


class IslandRailFaceTest(unittest.TestCase):
    """批三: the island mounts on the rail as the compact face growing
    along the track; the clock's rail face is the caelestia stack."""

    @classmethod
    def setUpClass(cls):
        cls.island = read(os.path.join(BAR_DIR, "DynamicIsland.qml"))
        cls.content = read(os.path.join(BAR_DIR, "BarContent.qml"))
        cls.clock = read(os.path.join(BAR_DIR, "ClockWidget.qml"))
        cls.idle = read(os.path.join(BAR_DIR, "DiIdle.qml"))
        cls.osd = read(os.path.join(BAR_DIR, "DiOsd.qml"))
        cls.media = read(os.path.join(BAR_DIR, "DiMedia.qml"))
        cls.session = read(os.path.join(BAR_DIR, "DiSession.qml"))
        cls.notifs = read(os.path.join(BAR_DIR, "DiNotifs.qml"))

    def test_island_no_longer_drops_from_rails(self):
        # 批一 kept end4's rail-only island drop; 批三 retires it.
        self.assertNotIn('entry.widgetId !== "island"', self.content)
        self.assertNotIn("if (root.vertical)", self.content)

    def test_island_geometry_follows_the_axis(self):
        # Along/cross swap: rail cross = the bar thickness direction, the
        # pill grows along the track (dux pillTarget lineage).
        self.assertIn("readonly property real railCrossSize: PersonalizationConfig.resolvedVerticalBarWidth(root.barAxes)", self.island)
        self.assertIn("implicitHeight: root.vertical ? root.railPillLength : root.pillHeight", self.island)
        self.assertIn("implicitWidth: root.vertical ? root.railCrossSize :", self.island)
        self.assertIn("radius: Math.min(root.width, root.height) / 2", self.island)
        # Conditional anchors are forbidden (flip regression note); the
        # pill positions explicitly.
        self.assertIn("        x: 0\n        y: 0", self.island)
        # Animations ride their own axis only.
        self.assertIn("Behavior on width {\n            enabled: !root.vertical", self.island)
        self.assertIn("Behavior on height {\n            enabled: root.vertical", self.island)

    def test_every_face_has_a_rail_length(self):
        for provider in ("notification", "battery", "osd", "media", "session"):
            self.assertRegex(self.island, rf'id: "{provider}",[^}}]*railLength: \d+', f"{provider} needs a rail length")
        self.assertIn("property real idleRailContentLength: 0", self.island)
        self.assertIn("readonly property real railPillLength:", self.island)

    def test_content_loader_is_no_longer_rail_gated(self):
        self.assertNotIn("active: !root.vertical", self.island)
        # Badge row stays a row-face feature (compact faces are the 批三
        # deliverable; rail badges ride a later pass).
        self.assertIn("visible: root.badgeProviders.length > 0 && !root.vertical", self.island)

    def test_rail_faces_branch_on_di_vertical(self):
        # idle: three segments stacked along the rail.
        self.assertIn("readonly property bool railFace: di.vertical", self.idle)
        self.assertIn("ClockContent {\n                // The ClockContent vertical stack keys off the edge; the\n                // owning bar's position is the single truth.\n                edge: di.barAxes.position", self.idle)
        self.assertIn("statusIconsColumn", self.idle)
        self.assertIn("di.idleRailContentLength = diIdleRoot.computedRailLength", self.idle)
        # osd: icon over value (dux verticalFace lineage).
        self.assertIn("visible: di.vertical", self.osd)
        # media: rail face is art + play/pause; row-only extras gate off.
        self.assertIn("radius: Math.min(width, height) / 2", self.media)
        self.assertIn("visible: di.vertical\n            cursorShape: Qt.PointingHandCursor", self.media)
        self.assertIn("visible: !di.vertical && diMediaRoot.visualizerStyle === \"wave\"", self.media)
        self.assertIn("visible: !di.vertical && diMediaRoot.showMediaControls", self.media)
        # session: the four actions stack along the track.
        self.assertIn("component ActionDelegate: Item {", self.session)
        self.assertEqual(self.session.count("visible: di.vertical"), 1)
        self.assertEqual(self.session.count("visible: !di.vertical"), 1)
        # notifs: icon compact face, text face stays a row face.
        self.assertIn("visible: di.vertical", self.notifs)
        self.assertIn("visible: !di.vertical", self.notifs)

    def test_clock_rail_face_is_the_caelestia_stack(self):
        self.assertIn("component RailClockFace: ColumnLayout {", self.clock)
        self.assertIn("function railFitScale(hourWidth, minuteWidth)", self.clock)
        self.assertIn("function railLineScale(text, metricWidth, widest)", self.clock)
        self.assertIn("TextMetrics {\n            id: hourMetrics", self.clock)
        self.assertIn('colDefault: Component {\n        RailClockFace {\n            materialSkin: false\n        }\n    }', self.clock)
        self.assertIn('colMaterial: Component {\n        RailClockFace {\n            materialSkin: true\n        }\n    }', self.clock)


class BilingualCopyTest(unittest.TestCase):
    """The new user-facing strings resolve in the zh dictionary."""

    STRINGS = (
        "Not available on a vertical bar",
        "Vertical bar",
        "This widget has no vertical face yet",
    )

    def test_zh_dictionary_covers_the_new_strings(self):
        zh = read(os.path.join(SHELL, "commons", "i18n", "zh_CN.toml"))
        for text in self.STRINGS:
            self.assertIn(f'"{text}"', zh, f"zh_CN.toml must provide a translation for {text!r}")


if __name__ == "__main__":
    unittest.main()
