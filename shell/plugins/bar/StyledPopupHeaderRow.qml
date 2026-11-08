// Fork & Trim: end4-pC modules/ii/bar/StyledPopupHeaderRow.qml (GPL-3, see
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
    spacing: 5

    MaterialSymbol {
        anchors.verticalCenter: parent.verticalCenter
        fill: 0
        font.weight: Font.DemiBold
        text: root.icon
        iconSize: 18
        color: Appearance.colors.colOnSurfaceVariant
    }

    StyledText {
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        font {
            weight: Font.DemiBold
            pixelSize: 13
        }
        color: Appearance.colors.colOnSurfaceVariant
    }
}
