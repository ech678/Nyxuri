import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components

Rectangle {
    id: root

    property string title: ""
    property string supportingText: ""
    property string iconName: "settings"
    property bool outlined: false
    property color containerColor: Appearance.colors.colSurfaceContainerHigh
    default property alias content: body.data

    implicitHeight: cardColumn.implicitHeight + Appearance.spacing.large * 2
    radius: Appearance.rounding.large
    color: containerColor
    border.width: outlined ? 1 : 0
    border.color: Appearance.colors.colOutlineVariant
    antialiasing: true

    ColumnLayout {
        id: cardColumn

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Appearance.spacing.large
        spacing: Appearance.spacing.medium

        RowLayout {
            Layout.fillWidth: true
            spacing: Appearance.spacing.small

            Rectangle {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                radius: Appearance.rounding.normal
                color: Appearance.colors.colSecondaryContainer

                MaterialSymbol {
                    anchors.centerIn: parent
                    text: root.iconName
                    iconSize: 23
                    fill: 1
                    color: Appearance.colors.colOnSecondaryContainer
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                Text {
                    Layout.fillWidth: true
                    text: root.title
                    color: Appearance.colors.colOnSurface
                    font.family: Typography.titleMedium.family
                    font.pixelSize: Typography.titleMedium.pixelSize
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    visible: text !== ""
                    text: root.supportingText
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Typography.bodySmall.family
                    font.pixelSize: Typography.bodySmall.pixelSize
                    elide: Text.ElideRight
                }
            }
        }

        ColumnLayout {
            id: body

            Layout.fillWidth: true
            spacing: Appearance.spacing.small
        }
    }
}
