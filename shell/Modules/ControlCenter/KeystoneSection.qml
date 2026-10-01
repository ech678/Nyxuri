import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components

ColumnLayout {
    id: root

    property string title: ""
    property string iconName: "toggle_off"
    default property alias content: body.data

    Layout.fillWidth: true
    spacing: 12

    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        MaterialSymbol {
            Layout.preferredWidth: 30
            Layout.preferredHeight: 30
            text: root.iconName
            iconSize: 26
            fill: 1
            color: Appearance.colors.colOnSecondaryContainer
        }

        Text {
            Layout.fillWidth: true
            text: root.title
            color: Appearance.colors.colOnSecondaryContainer
            font.family: Fonts.ui
            font.pixelSize: 18
            font.weight: Font.Medium
        }
    }

    ColumnLayout {
        id: body

        Layout.fillWidth: true
        spacing: 10
    }
}
