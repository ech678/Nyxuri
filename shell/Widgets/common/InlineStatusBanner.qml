import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components

Rectangle {
    id: root

    property string tone: "info"
    property string message: ""
    property string iconName: tone === "error" ? "error" : tone === "warning" ? "warning" : "info"

    implicitHeight: statusRow.implicitHeight + Appearance.spacing.small * 2
    radius: Appearance.rounding.normal
    color: tone === "error"
        ? Appearance.colors.colErrorContainer
        : tone === "warning"
            ? Appearance.colors.colTertiaryContainer
            : Appearance.colors.colLayer2

    RowLayout {
        id: statusRow

        anchors {
            fill: parent
            margins: Appearance.spacing.small
        }
        spacing: Appearance.spacing.small

        MaterialSymbol {
            text: root.iconName
            iconSize: 20
            color: root.tone === "error"
                ? Appearance.colors.colOnErrorContainer
                : root.tone === "warning"
                    ? Appearance.colors.colOnTertiaryContainer
                    : Appearance.colors.colOnLayer2
        }

        Text {
            Layout.fillWidth: true
            text: root.message
            color: root.tone === "error"
                ? Appearance.colors.colOnErrorContainer
                : root.tone === "warning"
                    ? Appearance.colors.colOnTertiaryContainer
                    : Appearance.colors.colOnLayer2
            font.family: Fonts.ui
            font.pixelSize: 12
            wrapMode: Text.Wrap
        }
    }
}
