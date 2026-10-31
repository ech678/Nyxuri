import QtQuick
import qs.commons

// Connected group base (Caelestia Nexus ConnectedRect). The first row of a
// group rounds only its top corners, the last row only its bottom corners,
// middle rows stay flat — stacked rows read as one connected MD3 card.
// uniformRadius >= 0 overrides every corner at once (active-pill and press
// shape morphs in the NavPane); the default keeps the group rounding.
Rectangle {
    id: root

    property bool first: false
    property bool last: false
    property real uniformRadius: -1

    readonly property real groupTopRadius: root.first ? NexusStyle.rounding.extraLarge :
                                                        NexusStyle.rounding.extraSmall

    readonly property real groupBottomRadius: root.last ? NexusStyle.rounding.extraLarge :
                                                          NexusStyle.rounding.extraSmall

    color: Appearance.m3colors.m3surfaceContainer
    topLeftRadius: root.uniformRadius >= 0 ? root.uniformRadius : root.groupTopRadius
    topRightRadius: root.uniformRadius >= 0 ? root.uniformRadius : root.groupTopRadius
    bottomLeftRadius: root.uniformRadius >= 0 ? root.uniformRadius : root.groupBottomRadius
    bottomRightRadius: root.uniformRadius >= 0 ? root.uniformRadius : root.groupBottomRadius

    Behavior on topLeftRadius {
        NumberAnimation {
            duration: Appearance.animation.expressiveDefaultSpatial.duration
            easing.type: Appearance.animation.expressiveDefaultSpatial.type
            easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
        }
    }

    Behavior on topRightRadius {
        NumberAnimation {
            duration: Appearance.animation.expressiveDefaultSpatial.duration
            easing.type: Appearance.animation.expressiveDefaultSpatial.type
            easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
        }
    }

    Behavior on bottomLeftRadius {
        NumberAnimation {
            duration: Appearance.animation.expressiveDefaultSpatial.duration
            easing.type: Appearance.animation.expressiveDefaultSpatial.type
            easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
        }
    }

    Behavior on bottomRightRadius {
        NumberAnimation {
            duration: Appearance.animation.expressiveDefaultSpatial.duration
            easing.type: Appearance.animation.expressiveDefaultSpatial.type
            easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
        }
    }
}
