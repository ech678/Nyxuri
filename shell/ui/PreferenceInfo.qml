import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Read-only property row (Caelestia Nexus InfoRow): leading icon, property
// name (plus optional subtext), and the value right-aligned in the variant
// colour. Pure display — no interaction, no state layer.
ConnectedRect {
    id: root

    property alias label: titleLabel.text
    property string subtext: ""
    property alias value: valueLabel.text
    property string icon: ""
    property color iconColor: Appearance.m3colors.m3onSurfaceVariant

    Layout.fillWidth: true
    implicitHeight: column.implicitHeight + NexusStyle.padding.medium * 2

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
            color: root.iconColor
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

        StyledText {
            id: valueLabel

            Layout.maximumWidth: root.width / 2
            horizontalAlignment: Text.AlignRight
            color: Appearance.m3colors.m3onSurfaceVariant
            font.pixelSize: NexusStyle.font.bodyMedium
            elide: Text.ElideRight
        }
    }
}
