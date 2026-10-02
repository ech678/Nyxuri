import QtQuick
import Qt5Compat.GraphicalEffects

Item {
    id: root

    required property string artUrl
    // Decode for the expanded panel, independently of its animated geometry.
    required property size sourceSize
    required property real topLeftRadius
    required property real topRightRadius
    required property real bottomLeftRadius
    required property real bottomRightRadius

    // This item belongs to the outer Keystone surface, not its padded content.
    layer.enabled: true
    layer.effect: OpacityMask {
        maskSource: Rectangle {
            width: root.width
            height: root.height
            topLeftRadius: root.topLeftRadius
            topRightRadius: root.topRightRadius
            bottomLeftRadius: root.bottomLeftRadius
            bottomRightRadius: root.bottomRightRadius
        }
    }

    Image {
        id: coverArt
        anchors.left: parent.left
        height: parent.height
        width: Math.min(root.width, root.height * 1.5)
        source: root.artUrl
        asynchronous: true
        retainWhileLoading: true
        sourceSize: root.sourceSize
        fillMode: Image.PreserveAspectCrop
        visible: false
    }

    Rectangle {
        id: fadeMask
        width: coverArt.width
        height: coverArt.height
        visible: false
        layer.enabled: true
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "white"
            }
            GradientStop {
                position: 0.45
                color: "white"
            }
            GradientStop {
                position: 0.72
                color: Qt.rgba(1, 1, 1, 0.35)
            }
            GradientStop {
                position: 1
                color: "transparent"
            }
        }
    }

    OpacityMask {
        anchors.fill: coverArt
        source: coverArt
        maskSource: fadeMask
    }
}
