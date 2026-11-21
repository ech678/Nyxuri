import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

RippleButton {
    id: root

    property string iconName: ""
    property string trailingIconName: "open_in_new"
    property string description: ""

    implicitHeight: description === "" ? Metrics.controlHeightXL : 68
    leftPadding: Metrics.spacingL
    rightPadding: Metrics.spacingL
    topPadding: 0
    bottomPadding: 0
    buttonRadius: Appearance.rounding.full
    containerColor: "transparent"
    rippleColor: Appearance.colors.colOnLayer2
    stateLayerColor: Appearance.colors.colOnLayer2
    pressedStateLayerColor: Appearance.colors.colOnLayer2
    focusStateLayerColor: Appearance.colors.colOnLayer2
    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
    focusStateLayerOpacity: Appearance.interaction.focusStateLayerOpacity
    focusPolicy: Qt.StrongFocus

    contentItem: RowLayout {
        spacing: Metrics.spacingS

        MaterialSymbol {
            visible: root.iconName !== ""
            text: root.iconName
            iconSize: 22
            color: Appearance.colors.colOnSurfaceVariant
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1

            Text {
                Layout.fillWidth: true
                text: root.text
                color: Appearance.colors.colOnSurface
                font.family: root.description === "" ? Fonts.ui : Fonts.ui
                font.pixelSize: root.description === "" ? NexusStyle.font.bodyLarge : NexusStyle.font.bodyMedium
                font.weight: root.description === "" ? Font.Medium : Font.Normal
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                visible: root.description !== ""
                text: root.description
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
                font.pixelSize: NexusStyle.font.bodySmall
                elide: Text.ElideRight
            }
        }

        Item {
            Layout.preferredWidth: Metrics.controlHeightM
            Layout.fillHeight: true
            visible: root.trailingIconName !== ""

            MaterialSymbol {
                anchors.centerIn: parent
                text: root.trailingIconName
                iconSize: 20
                color: Appearance.colors.colOnSurfaceVariant
            }
        }
    }
}
