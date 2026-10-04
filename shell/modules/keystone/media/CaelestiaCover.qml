// Adapted from Caelestia Shell's CoverVisualiser.qml and CoverArt.qml.
// GPL-3.0; source mapping and modifications: licenses/README.md.
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import Qt5Compat.GraphicalEffects
import Quickshell
import M3Shapes
import qs.shared.theme
import qs.app.services

Item {
    id: root

    required property string artUrl
    required property bool playing
    required property bool active
    required property color accentColor
    readonly property bool spectrumActive: active && playing
    readonly property int barCount: 36
    readonly property real coverSize: Math.min(width, height) * 0.8
    readonly property real maxMagnitude: 20
    readonly property var values: new Array(root.barCount).fill(0)

    Shape {
        anchors.fill: parent
        asynchronous: true
        preferredRendererType: Shape.CurveRenderer
        data: bars.instances
        opacity: 0.35
    }

    Variants {
        id: bars
        model: Array.from({
                              length: root.barCount
                          }, (_, i) => i)

        ShapePath {
            id: bar
            required property int modelData
            readonly property real angle: modelData * 2 * Math.PI / root.barCount
            readonly property real edge: {
                cookie.rotation;
                return cookie.distanceAtAngle(modelData * 360 / root.barCount + 90) + 6;
            }
            readonly property real magnitude: 2 + root.values[modelData] * (root.maxMagnitude - 2)
            readonly property real cos: Math.cos(angle)
            readonly property real sin: Math.sin(angle)
            capStyle: ShapePath.RoundCap
            strokeWidth: 4
            strokeColor: root.accentColor
            fillColor: "transparent"
            startX: root.width / 2 + edge * cos
            startY: root.height / 2 + edge * sin
            PathLine {
                x: root.width / 2 + (bar.edge + bar.magnitude) * bar.cos
                y: root.height / 2 + (bar.edge + bar.magnitude) * bar.sin
            }
        }
    }

    Item {
        id: cover
        anchors.centerIn: parent
        width: root.coverSize
        height: width

        Item {
            id: cookieMask
            anchors.fill: parent
            layer.enabled: true
            visible: false

            MaterialShape {
                id: cookie
                anchors.centerIn: parent
                implicitSize: root.coverSize
                shape: MaterialShape.Cookie9Sided
                color: "white"
                NumberAnimation on rotation {
                    running: root.active && root.playing
                    from: 360
                    to: 0
                    duration: 23500
                    loops: Animation.Infinite
                }
            }
        }

        Item {
            id: artwork
            anchors.fill: parent
            visible: false
            Rectangle {
                anchors.fill: parent
                color: Appearance.colors.colLayer3
                Text {
                    anchors.centerIn: parent
                    text: "music_note"
                    color: Appearance.colors.colOnLayer3
                    font.family: Fonts.materialSymbolsOutlined
                    font.pixelSize: root.coverSize * 0.47
                    visible: image.status !== Image.Ready
                }
            }
            Image {
                id: image
                anchors.fill: parent
                source: root.artUrl
                sourceSize: Qt.size(360, 360)
                asynchronous: true
                fillMode: Image.PreserveAspectCrop
            }
        }

        OpacityMask {
            anchors.fill: parent
            source: artwork
            maskSource: cookieMask
        }
    }
}
