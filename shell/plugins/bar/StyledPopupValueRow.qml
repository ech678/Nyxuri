// Fork & Trim: end4-pC modules/ii/bar/StyledPopupValueRow.qml (GPL-3, see
// shell/LICENSE appendix end-4-dots-hyprland-GPL-3.0.txt). B4 reskin promotes
// this component to plugins/bar/.
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

Row {
    id: root

    required property var icon
    required property var label
    required property var value
    spacing: 5

    MaterialSymbol {
        anchors.verticalCenter: parent.verticalCenter
        fill: 0
        text: root.icon
        iconSize: 16
        color: Appearance.colors.colOnSurfaceVariant
    }

    StyledText {
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        font.pixelSize: 12
        color: Appearance.colors.colOnSurfaceVariant
    }

    Item {
        Layout.fillWidth: true
    }

    StyledText {
        anchors.verticalCenter: parent.verticalCenter
        text: root.value
        font.pixelSize: 12
        color: Appearance.colors.colOnSurface
    }
}
