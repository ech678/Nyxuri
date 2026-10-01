import QtQuick
import QtQuick.Effects
import qs.Common

Item {
    id: root

    default property alias contentData: contentViewport.data
    property bool animateResize: true
    property bool backgroundVisible: true

    // Animate the size consumed by the bar layout so the surface, shadow and
    // neighbouring pills follow the same geometry throughout a resize.
    property bool resizeAnimationReady: false
    Component.onCompleted: resizeAnimationReady = true

    // Keep the shadow outside the clipped content subtree.
    data: [
        TopBarPillBackground {
            anchors.fill: parent
            visible: root.backgroundVisible
        },
        Rectangle {
            id: contentMask
            width: root.width
            height: root.height
            radius: Math.min(width, height) / 2
            color: "white"
            visible: false
            layer.enabled: true
        },
        Item {
            id: contentViewport
            anchors.fill: parent
            clip: true
            layer.enabled: true
            layer.effect: MultiEffect {
                maskEnabled: true
                maskSource: contentMask
            }
        }
    ]

    Behavior on implicitWidth {
        enabled: root.resizeAnimationReady && root.animateResize
        NumberAnimation {
            duration: Appearance.animation.standard.duration
            easing.type: Appearance.animation.standard.type
            easing.bezierCurve: Appearance.animation.standard.bezierCurve
        }
    }

    Behavior on implicitHeight {
        enabled: root.resizeAnimationReady && root.animateResize
        NumberAnimation {
            duration: Appearance.animation.standard.duration
            easing.type: Appearance.animation.standard.type
            easing.bezierCurve: Appearance.animation.standard.bezierCurve
        }
    }
}
