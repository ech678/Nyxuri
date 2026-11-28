import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Visual card selector grid (dux SettingsLayoutPicker lineage, skinned in
// NexusStyle / ConnectedRect / StateLayer). Each choice is
// { key, label, icon?, preview?: "top"|"bottom"|"left"|"right", enabled? }.
ConnectedRect {
    id: root

    property var choices: []
    property string selectedKey: ""
    property string previewMode: "edge" // "edge" | "icon"

    signal selected(string key)

    Layout.fillWidth: true
    implicitHeight: grid.implicitHeight + NexusStyle.padding.medium * 2

    GridLayout {
        id: grid

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.largeIncreased
        anchors.rightMargin: NexusStyle.padding.largeIncreased
        columns: Math.min(Math.max(1, root.choices.length), Math.max(1, Math.floor((width + columnSpacing) / (96 + columnSpacing))))
        columnSpacing: NexusStyle.padding.small
        rowSpacing: NexusStyle.padding.small

        Repeater {
            model: root.choices

            Rectangle {
                id: card

                required property var modelData

                readonly property bool isActive: root.selectedKey === String(modelData.key ?? "")
                readonly property bool itemEnabled: modelData.enabled !== false

                Layout.fillWidth: true
                implicitWidth: 88
                implicitHeight: cardCol.implicitHeight + NexusStyle.padding.medium * 2
                radius: NexusStyle.rounding.medium
                color: card.isActive ? Appearance.m3colors.m3secondaryContainer : Appearance.m3colors.m3surfaceContainerHigh
                border.width: card.isActive ? 2 : 1
                border.color: card.isActive ? Appearance.m3colors.m3primary : Appearance.m3colors.m3outlineVariant
                opacity: card.itemEnabled ? 1 : 0.45

                StateLayer {
                    anchors.fill: parent
                    layerRadius: card.radius
                    color: Appearance.m3colors.m3primary
                    hovered: cardMouse.containsMouse && card.itemEnabled
                    pressed: cardMouse.pressed && card.itemEnabled
                }

                MouseArea {
                    id: cardMouse

                    anchors.fill: parent
                    enabled: card.itemEnabled
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selected(String(card.modelData.key ?? ""))
                }

                ColumnLayout {
                    id: cardCol

                    anchors.centerIn: parent
                    width: parent.width - NexusStyle.padding.small * 2
                    spacing: NexusStyle.padding.extraSmall

                    Rectangle {
                        id: previewBox

                        readonly property string edge: String(card.modelData.preview ?? card.modelData.key ?? "top")
                        readonly property bool verticalEdge: edge === "left" || edge === "right"
                        readonly property real edgePad: NexusStyle.padding.extraSmall
                        readonly property real stripSize: NexusStyle.padding.small

                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 56
                        Layout.preferredHeight: 36
                        radius: NexusStyle.rounding.extraSmall
                        color: Appearance.m3colors.m3surfaceContainerLowest
                        border.width: 1
                        border.color: Appearance.m3colors.m3outlineVariant

                        Rectangle {
                            visible: root.previewMode === "edge"
                            x: previewBox.edge === "right" ? parent.width - width - previewBox.edgePad : previewBox.edgePad
                            y: previewBox.edge === "bottom" ? parent.height - height - previewBox.edgePad : previewBox.edgePad
                            width: previewBox.verticalEdge ? previewBox.stripSize : parent.width - previewBox.edgePad * 2
                            height: previewBox.verticalEdge ? parent.height - previewBox.edgePad * 2 : previewBox.stripSize
                            radius: NexusStyle.rounding.full
                            color: card.isActive ? Appearance.m3colors.m3primary : Appearance.m3colors.m3onSurfaceVariant
                        }

                        MaterialSymbol {
                            visible: root.previewMode !== "edge" && String(card.modelData.icon ?? "").length > 0
                            anchors.centerIn: parent
                            text: String(card.modelData.icon ?? "")
                            iconSize: NexusStyle.icon.medium
                            fill: card.isActive ? 1 : 0
                            color: card.isActive ? Appearance.m3colors.m3primary : Appearance.m3colors.m3onSurfaceVariant
                        }
                    }

                    StyledText {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: String(card.modelData.label ?? "")
                        color: card.isActive ? Appearance.m3colors.m3onSecondaryContainer : Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.labelMedium
                        font.weight: card.isActive ? NexusStyle.font.labelMediumWeight : Font.Normal
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
