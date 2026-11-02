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
    property int staggerMs: 45
    readonly property int count: root.groups ? root.groups.length : 0
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
            required property int index

            readonly property bool on: root.current === modelData.id
            readonly property bool dim: root.dimmed[modelData.id] ?? false

            Layout.alignment: Qt.AlignHCenter
            implicitWidth: root.boxSize
            implicitHeight: root.boxSize
            opacity: dim ? 0.35 : 1

            // Entrance matches DashboardCard: the rail is a sibling of the
            // card grid and a static rail next to flying cards reads as a
            // different, older surface.
            scale: 0.25
            transform: Translate {
                id: liftOffset

                x: 0
                y: 12
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: 150
                }
            }

            SequentialAnimation {
                id: enterAnim

                PauseAnimation {
                    duration: box.index * root.staggerMs
                }
                ParallelAnimation {
                    SpringAnimation {
                        target: box
                        property: "scale"
                        to: 1
                        spring: 2.6
                        damping: 0.32
                    }
                    SpringAnimation {
                        target: liftOffset
                        property: "y"
                        to: 0
                        spring: 2.6
                        damping: 0.32
                    }
                }
            }

            Component.onCompleted: enterAnim.start()

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
                            spring: 4
                            damping: 0.22
                        }
                    }

                    Behavior on containerColor {
                        ColorAnimation {
                            duration: 220
                            easing.type: Easing.OutCubic
                        }
                    }

                    Behavior on stateLayerColor {
                        ColorAnimation {
                            duration: 220
                            easing.type: Easing.OutCubic
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

                            Behavior on color {
                                ColorAnimation {
                                    duration: 220
                                    easing.type: Easing.OutCubic
                                }
                            }

                            // Fill is an int on the icon font; a spring overshoot
                            // would clip it, so this one eases rather than bounces.
                            Behavior on fill {
                                NumberAnimation {
                                    duration: 220
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }

                        StyledText {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.fillWidth: true
                            Layout.leftMargin: 2
                            Layout.rightMargin: 2
                            Layout.bottomMargin: 6
                            text: box.modelData.name
                            font.pixelSize: Appearance.font.pixelSize.smallest
                            font.weight: Font.DemiBold
                            color: box.on ? box.modelData.onAccent : box.modelData.onContainer
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            maximumLineCount: 2
                            elide: Text.ElideRight

                            Behavior on color {
                                ColorAnimation {
                                    duration: 220
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    id: badge

                    visible: box.modelData.count > 0
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: -5
                    anchors.rightMargin: -5
                    implicitHeight: 20
                    implicitWidth: Math.max(20, badgeText.implicitWidth + 10)
                    radius: 10
                    color: Appearance.m3colors.m3surfaceContainerHighest
                    scale: box.modelData.count > 0 ? 1 : 0

                    Behavior on scale {
                        SpringAnimation {
                            spring: 4
                            damping: 0.3
                        }
                    }

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
