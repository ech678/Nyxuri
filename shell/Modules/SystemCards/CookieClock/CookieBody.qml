import QtQuick
import QtQuick.Effects
import qs.Common

Item {
    id: root

    property bool active: true
    property bool constantlyRotate: false
    property int sides: 14
    property color faceColor: Appearance.colors.colPrimaryContainer

    anchors.fill: parent

    CookieFace {
        id: cookieFace

        sides: root.sides
        fillColor: root.faceColor
        // The effect receives this exact M3Shapes render layer, so the face
        // and its shadow share one geometry, rotation, and morph lifecycle.
        layer.enabled: true

        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Appearance.applyAlpha(Appearance.colors.colShadow, 0.4)
            shadowBlur: 0.8
            shadowVerticalOffset: 4
            shadowHorizontalOffset: 0
            autoPaddingEnabled: true
        }

    }

    RotationAnimation on rotation {
        running: root.active && root.constantlyRotate
        from: 360
        to: 0
        duration: 30000
        loops: Animation.Infinite
        easing.type: Easing.Linear
    }

}
