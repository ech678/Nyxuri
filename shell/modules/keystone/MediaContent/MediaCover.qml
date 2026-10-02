import QtQuick
import Qt5Compat.GraphicalEffects
import qs.Common

Item {
    id: root

    required property string artUrl
    required property bool playing
    required property bool caelestia
    required property color accentColor
    property bool active: visible

    Loader {
        anchors.fill: parent
        sourceComponent: root.caelestia ? caelestiaCover : roundedCover
    }

    Component {
        id: caelestiaCover
        CaelestiaCover {
            artUrl: root.artUrl
            playing: root.playing
            active: root.active
            accentColor: root.accentColor
        }
    }

    Component {
        id: roundedCover
        Item {
            id: scaleWrapper
            anchors.centerIn: parent
            width: root.width
            height: width
            scale: root.playing ? 1 : 0.8

            Behavior on scale {
                NumberAnimation {
                    duration: 400
                    easing.type: Easing.OutQuint
                }
            }

            DropShadow {
                anchors.fill: coverContainer
                source: coverContainer
                color: Appearance.applyAlpha(Appearance.colors.colScrim, 0.85)
                radius: 24
                samples: 49
                verticalOffset: 8
                opacity: root.playing ? 1 : 0

                Behavior on opacity {
                    NumberAnimation {
                        duration: 400
                        easing.type: Easing.OutQuint
                    }
                }
            }

            Item {
                id: coverContainer
                anchors.fill: parent

                Rectangle {
                    anchors.fill: parent
                    radius: 16
                    color: Appearance.colors.colLayer3
                    visible: rawImg.status !== Image.Ready

                    Text {
                        anchors.centerIn: parent
                        text: "music_note"
                        color: Appearance.colors.colOnLayer3
                        font.family: Fonts.materialSymbolsOutlined
                        font.pixelSize: parent.width * 0.47
                    }
                }

                Image {
                    id: rawImg
                    anchors.fill: parent
                    source: root.artUrl
                    sourceSize: Qt.size(240, 240)
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: false
                }

                Rectangle {
                    id: maskRect
                    anchors.fill: parent
                    radius: 16
                    visible: false
                }

                OpacityMask {
                    anchors.fill: parent
                    source: rawImg
                    maskSource: maskRect
                    visible: rawImg.status === Image.Ready
                }
            }
        }
    }
}
