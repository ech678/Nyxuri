import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.commons.i18n

ColumnLayout {
    id: root

    property var groups: []
    property string current: ""
    property var dimmed: ({})
    readonly property int count: root.groups ? root.groups.length : 0
    readonly property real speed: 1
    readonly property int minGap: 6
    readonly property real boxSize: Math.max(44, Math.min(64, (height - minGap * (root.count - 1)) / Math.max(
                                                              1, root.count)))

    signal picked(string id)

    spacing: root.count > 1 ? Math.max(minGap, (height - boxSize * root.count) / (root.count - 1)) : 0

    Repeater {
        model: root.groups

        delegate: Item {
            id: box

            required property var modelData
            readonly property bool on: root.current === modelData.id
            readonly property bool dim: root.dimmed[modelData.id] ?? false

            Layout.alignment: Qt.AlignHCenter
            implicitWidth: root.boxSize
            implicitHeight: root.boxSize
            opacity: dim ? 0.35 : 1

            Behavior on opacity {
                NumberAnimation {
                    duration: 150
                }
            }

            Item {
                id: lift
                anchors.fill: parent

                StyledRectangularShadow {
                    target: plate
                    opacity: box.on ? 1 : 0

                    Behavior on opacity {
                        NumberAnimation {
                            duration: 200
                        }
                    }
                }

                Rectangle {
                    id: plate
                    anchors.fill: parent
                    radius: button.buttonRadius
                    color: "transparent"
                }

                RippleButton {
                    id: button
                    anchors.fill: parent
                    toggled: box.on
                    buttonRadius: box.on ? 22 : 14
                    containerColor: box.on ? box.modelData.accent : box.modelData.container
                    rippleColor: box.on ? box.modelData.onAccent : box.modelData.onContainer
                    stateLayerColor: box.on ? box.modelData.onAccent : box.modelData.onContainer
                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                    onClicked: root.picked(box.modelData.id)

                    Behavior on buttonRadius {
                        SpringAnimation {
                            spring: 4 * root.speed
                            damping: 0.22
                        }
                    }

                    contentItem: ColumnLayout {
                        spacing: 1

                        MaterialSymbol {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.topMargin: 6
                            text: box.modelData.icon
                            iconSize: Appearance.font.pixelSize.huge
                            fill: box.on ? 1 : 0
                            rotation: box.modelData.rotation ?? 0
                            color: box.on ? box.modelData.onAccent : box.modelData.onContainer
                        }

                        StyledText {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.bottomMargin: 6
                            text: box.modelData.name
                            font.pixelSize: Appearance.font.pixelSize.smallest
                            font.weight: Font.DemiBold
                            color: box.on ? box.modelData.onAccent : box.modelData.onContainer
                        }
                    }
                }

                Rectangle {
                    visible: box.modelData.count > 0
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: -5
                    anchors.rightMargin: -5
                    implicitHeight: 20
                    implicitWidth: Math.max(20, badgeText.implicitWidth + 10)
                    radius: 10
                    color: Appearance.m3colors.m3surfaceContainerHighest

                    StyledText {
                        id: badgeText
                        anchors.centerIn: parent
                        text: box.modelData.count
                        font.pixelSize: Appearance.font.pixelSize.smallest
                        font.weight: Font.Bold
                        color: Appearance.m3colors.m3onSurface
                    }
                }
            }
        }
    }
}
