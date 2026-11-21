"""D2 SystemIcons QS expansion contract tests.

Pins the D2 contract (ROADMAP D-2):
- UtilButton 26↔54px hover expansion skeleton (200ms);
- 150ms intent delay to prevent jitter from rapid mouse sweeps;
- Expanded area presents one line of status data (volume %, SSID, Bluetooth
  device count, peripheral battery %, etc.);
- Vertical bar support (implicitHeight 26↔54px, implicitWidth 26px);
- Keyboard indicator stays fixed at 26px (expandable: false);
- High-contrast color bindings (M3 primary/primaryForeground in Material,
  layer1Hover + resolvedContentColor in non-Material);
- Font size strictly consumes NexusStyle.font.labelSmall with tabular numbers.
"""

from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAR_DIR = os.path.join(REPO_ROOT, "shell", "plugins", "bar")


def read_bar_file(name: str) -> str:
    path = os.path.join(BAR_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class SystemIconSlotContractTest(unittest.TestCase):
    """SystemIconSlot 26↔54px expansion skeleton & 150ms intent delay."""

    def setUp(self):
        self.slot = read_bar_file("SystemIconSlot.qml")

    def test_expansion_skeleton_dimensions(self):
        self.assertIn("readonly property int slotSize: 26", self.slot)
        self.assertIn("readonly property int expandedSize: 54", self.slot)
        self.assertIn("readonly property int intentDelay: 150", self.slot)
        self.assertIn("implicitWidth: root.vertical ? root.slotSize : (root.expanded ? root.expandedSize : root.slotSize)", self.slot)
        self.assertIn("implicitHeight: root.vertical ? (root.expanded ? root.expandedSize : root.slotSize) : root.slotSize", self.slot)

    def test_motion_duration_is_200ms(self):
        # D-2 specifies 200ms duration with standard motion curve
        self.assertGreaterEqual(self.slot.count("duration: 200"), 2)
        self.assertIn("Appearance.animationCurves.standard", self.slot)

    def test_intent_delay_timer(self):
        self.assertIn("id: intentTimer", self.slot)
        self.assertIn("interval: root.intentDelay", self.slot)
        self.assertIn("property bool intentHovered: false", self.slot)
        self.assertIn("root.intentHovered = true", self.slot)
        self.assertIn("intentTimer.restart()", self.slot)
        self.assertIn("intentTimer.stop()", self.slot)

    def test_anchor_box_keeps_icon_stationary(self):
        # Icon anchor box stays locked to top-left 26x26 so expanding right/bottom
        # never shifts or jitters the glyph
        self.assertIn("id: anchorBox", self.slot)
        self.assertIn("width: root.slotSize", self.slot)
        self.assertIn("height: root.slotSize", self.slot)
        self.assertIn("id: symbol", self.slot)
        self.assertIn("id: contentHost", self.slot)

    def test_expanded_data_label(self):
        self.assertIn("id: label", self.slot)
        self.assertIn("font.pixelSize: NexusStyle.font.labelSmall", self.slot)
        self.assertIn('"tnum": 1', self.slot)
        self.assertIn("elide: Text.ElideRight", self.slot)
        self.assertIn("text: root.dataText", self.slot)

    def test_contrast_colors_for_both_skins(self):
        # Capsule background
        self.assertIn("root.isMaterial ? M3Palette.primary : Appearance.colors.colLayer1Hover", self.slot)
        # Ink foreground (symbol + label)
        self.assertIn("root.hovered && root.isMaterial ? M3Palette.primaryForeground : root.resolvedContentColor", self.slot)

    def test_mouse_area_fills_expanded_capsule(self):
        self.assertIn("id: mouseArea", self.slot)
        self.assertIn("anchors.fill: parent", self.slot)
        self.assertIn("signal wheeled(real delta)", self.slot)


class SystemIconsWiringContractTest(unittest.TestCase):
    """SystemIcons slots wire dataText according to D-2 decision."""

    def setUp(self):
        self.icons = read_bar_file("SystemIcons.qml")

    def test_volume_slot_data_wiring(self):
        self.assertIn('slotKey: "volume"', self.icons)
        self.assertIn("VolumeService.sinkMuted ? I18n.tr(\"Muted\")", self.icons)
        self.assertIn("Math.round((VolumeService.sinkVolume ?? 0) * 100)}%", self.icons)

    def test_wifi_slot_data_wiring(self):
        self.assertIn('slotKey: "wifi"', self.icons)
        self.assertIn("NetworkService.activeSsid || I18n.tr(\"Wi-Fi\")", self.icons)
        self.assertIn("NetworkService.wiredConnected ? I18n.tr(\"Eth\")", self.icons)

    def test_bluetooth_slot_data_wiring(self):
        self.assertIn('slotKey: "bluetooth"', self.icons)
        self.assertIn("BluetoothService.connectedDevices.length", self.icons)

    def test_peripheral_battery_data_wiring(self):
        self.assertIn('slotKey: "peripheral"', self.icons)
        self.assertIn("Math.round(modelData.percentage * 100)}%", self.icons)

    def test_mic_slot_data_wiring(self):
        self.assertIn('slotKey: "mic"', self.icons)
        self.assertIn('dataText: I18n.tr("Muted")', self.icons)

    def test_notification_slot_data_wiring(self):
        self.assertIn('slotKey: "notifications"', self.icons)
        self.assertIn("NotificationService.silent ? I18n.tr(\"DND\") : `${NotificationService.unread}`", self.icons)

    def test_keyboard_slot_is_not_expandable(self):
        self.assertIn('slotKey: "keyboard"', self.icons)
        self.assertIn("expandable: false", self.icons)


if __name__ == "__main__":
    unittest.main()
