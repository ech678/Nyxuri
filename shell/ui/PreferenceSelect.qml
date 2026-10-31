import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Dropdown select row (Caelestia Nexus SelectRow): label plus optional
// subtext on the left, the current value shown in a tonal pill button on
// the right. Pressing the pill opens the shared MD3 menu; the page injects
// `inputRegionService` so menus that overhang the floating window keep
// compositor input.
ConnectedRect {
    id: root

    property alias label: titleLabel.text
    property string subtext: ""
    property string icon: ""
    property alias model: splitButton.model
    property alias currentValue: splitButton.currentValue
    // Shown when currentValue matches no model entry (Caelestia SelectRow
    // fallbackText; e.g. an unset default application).
    property alias fallbackText: splitButton.fallbackText
    property var inputRegionService: null

    signal selected(string value)

    function closeMenu() {
        splitButton.closeMenu();
    }

    Layout.fillWidth: true
    implicitHeight: column.implicitHeight + NexusStyle.padding.medium * 2
    clip: false
    z: 0

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.largeIncreased
        anchors.rightMargin: NexusStyle.padding.largeIncreased
        spacing: NexusStyle.padding.small

        MaterialSymbol {
            visible: root.icon.length > 0
            Layout.preferredWidth: root.icon.length > 0 ? implicitWidth : 0
            text: root.icon
            iconSize: NexusStyle.icon.medium
            fill: 1
            color: Appearance.m3colors.m3onSurfaceVariant
        }

        ColumnLayout {
            id: column

            Layout.fillWidth: true
            spacing: 0

            StyledText {
                id: titleLabel

                Layout.fillWidth: true
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
                elide: Text.ElideRight
            }

            StyledText {
                Layout.fillWidth: true
                visible: root.subtext.length > 0
                text: root.subtext
                color: Appearance.m3colors.m3outline
                font.pixelSize: NexusStyle.font.labelSmall
                elide: Text.ElideRight
            }
        }

        SplitMenuButton {
            id: splitButton

            inputRegionService: root.inputRegionService
            onValueSelected: value => root.selected(value)
        }
    }
}
