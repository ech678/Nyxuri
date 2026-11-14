pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property QtObject curves
    property QtObject durations
    property QtObject animation

    curves: QtObject {
        readonly property var emphasized: [0.05, 0, 0.1333, 0.06, 0.1667, 0.4, 0.2083, 0.82, 0.25, 1, 1, 1]
        readonly property var emphasizedAccel: [0.3, 0, 0.8, 0.15, 1, 1]
        readonly property var emphasizedDecel: [0.05, 0.7, 0.1, 1, 1, 1]
        readonly property var standard: [0.2, 0, 0, 1, 1, 1]
        readonly property var standardAccel: [0.3, 0, 1, 1, 1, 1]
        readonly property var standardDecel: [0, 0, 0, 1, 1, 1]
        readonly property var expressiveFastSpatial: [0.42, 1.67, 0.21, 0.9, 1, 1]
        readonly property var expressiveDefaultSpatial: [0.38, 1.21, 0.22, 1, 1, 1]
        readonly property var expressiveSlowSpatial: [0.39, 1.29, 0.35, 0.98, 1, 1]
        readonly property var expressiveFastEffects: [0.31, 0.94, 0.34, 1, 1, 1]
        readonly property var expressiveDefaultEffects: [0.34, 0.8, 0.34, 1, 1, 1]
        readonly property var expressiveSlowEffects: [0.34, 0.88, 0.34, 1, 1, 1]

        readonly property var expressiveEffects: expressiveDefaultEffects
        readonly property int expressiveFastSpatialDuration: root.durations.expressiveFastSpatial
        readonly property int expressiveDefaultSpatialDuration: root.durations.expressiveDefaultSpatial
        readonly property int expressiveEffectsDuration: root.durations.expressiveDefaultEffects
        readonly property int emphasizedAccelDuration: root.durations.emphasizedAccel
        readonly property int standardDecelDuration: root.durations.standardDecel
    }

    durations: QtObject {
        readonly property int small: 200
        readonly property int normal: 400
        readonly property int large: 600
        readonly property int extraLarge: 1000
        readonly property int expressiveFastSpatial: 350
        readonly property int sidebarEnter: expressiveFastSpatial
        readonly property int sidebarExit: small
        readonly property int expressiveDefaultSpatial: 500
        readonly property int expressiveSlowSpatial: 650
        readonly property int expressiveFastEffects: 150
        readonly property int expressiveDefaultEffects: 200
        readonly property int expressiveSlowEffects: 300

        readonly property int expressiveEffects: expressiveDefaultEffects
        readonly property int emphasizedAccel: small
        readonly property int standardDecel: small
    }

    animation: QtObject {
        readonly property QtObject standardSmall: QtObject {
            readonly property int duration: root.durations.small
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.standard
        }

        readonly property QtObject standard: QtObject {
            readonly property int duration: root.durations.normal
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.standard
        }

        readonly property QtObject standardLarge: QtObject {
            readonly property int duration: root.durations.large
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.standard
        }

        readonly property QtObject standardExtraLarge: QtObject {
            readonly property int duration: root.durations.extraLarge
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.standard
        }

        readonly property QtObject standardAccel: QtObject {
            readonly property int duration: root.durations.normal
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.standardAccel
        }

        readonly property QtObject standardDecel: QtObject {
            readonly property int duration: root.durations.standardDecel
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.standardDecel
        }

        readonly property QtObject emphasizedAccel: QtObject {
            readonly property int duration: root.durations.emphasizedAccel
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.emphasizedAccel
        }

        readonly property QtObject expressiveFastSpatial: QtObject {
            readonly property int duration: root.durations.expressiveFastSpatial
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveFastSpatial
            // iNiR sources instantiate Behaviors from Component factories
            // (`animation.elementMoveFast.colorAnimation.createObject(this)`).
            // Nyxuri kept only duration/type/bezierCurve, so every ported
            // Behavior threw "Cannot read property 'createObject' of
            // undefined" once per frame. The factories are part of the contract
            // now, not an optional extra.
            readonly property Component colorAnimation: Component {
                ColorAnimation {
                    duration: root.animation.expressiveFastSpatial.duration
                    easing.type: root.animation.expressiveFastSpatial.type
                    easing.bezierCurve: root.animation.expressiveFastSpatial.bezierCurve
                }
            }
            readonly property Component numberAnimation: Component {
                NumberAnimation {
                    duration: root.animation.expressiveFastSpatial.duration
                    easing.type: root.animation.expressiveFastSpatial.type
                    easing.bezierCurve: root.animation.expressiveFastSpatial.bezierCurve
                }
            }
        }

        readonly property QtObject expressiveDefaultSpatial: QtObject {
            readonly property int duration: root.durations.expressiveDefaultSpatial
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveDefaultSpatial
            readonly property Component colorAnimation: Component {
                ColorAnimation {
                    duration: root.animation.expressiveDefaultSpatial.duration
                    easing.type: root.animation.expressiveDefaultSpatial.type
                    easing.bezierCurve: root.animation.expressiveDefaultSpatial.bezierCurve
                }
            }
            readonly property Component numberAnimation: Component {
                NumberAnimation {
                    duration: root.animation.expressiveDefaultSpatial.duration
                    easing.type: root.animation.expressiveDefaultSpatial.type
                    easing.bezierCurve: root.animation.expressiveDefaultSpatial.bezierCurve
                }
            }
        }

        readonly property QtObject expressiveSlowSpatial: QtObject {
            readonly property int duration: root.durations.expressiveSlowSpatial
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveSlowSpatial
        }

        readonly property QtObject expressiveFastEffects: QtObject {
            readonly property int duration: root.durations.expressiveFastEffects
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveFastEffects
        }

        readonly property QtObject expressiveDefaultEffects: QtObject {
            readonly property int duration: root.durations.expressiveDefaultEffects
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveDefaultEffects
        }

        readonly property QtObject expressiveSlowEffects: QtObject {
            readonly property int duration: root.durations.expressiveSlowEffects
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveSlowEffects
        }

        readonly property QtObject expressiveEffects: expressiveDefaultEffects
        // Shared spatial token for wallpaper-card reflow, including the
        // sidebar-to-desktop handoff and geometry remapping.
        readonly property QtObject desktopCardReflow: expressiveDefaultSpatial
        readonly property QtObject elementMoveFast: expressiveFastSpatial
        readonly property QtObject wallpaperParallax: QtObject {
            readonly property int duration: root.durations.large
            readonly property int type: Easing.OutCubic
            readonly property var bezierCurve: []
        }
        readonly property QtObject elementResize: QtObject {
            readonly property int duration: 300
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.emphasized
            readonly property Component numberAnimation: Component {
                NumberAnimation {
                    duration: root.animation.elementResize.duration
                    easing.type: root.animation.elementResize.type
                    easing.bezierCurve: root.animation.elementResize.bezierCurve
                }
            }
        }
        // iNiR's scalar names for the same two spatial tokens; ported bar
        // components reference them directly.
        readonly property QtObject elementMove: expressiveDefaultSpatial
        readonly property QtObject elementMoveEnter: QtObject {
            readonly property int duration: root.durations.emphasizedAccel
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.emphasizedDecel
            readonly property Component colorAnimation: Component {
                ColorAnimation {
                    duration: root.animation.elementMoveEnter.duration
                    easing.type: root.animation.elementMoveEnter.type
                    easing.bezierCurve: root.animation.elementMoveEnter.bezierCurve
                }
            }
            readonly property Component numberAnimation: Component {
                NumberAnimation {
                    duration: root.animation.elementMoveEnter.duration
                    easing.type: root.animation.elementMoveEnter.type
                    easing.bezierCurve: root.animation.elementMoveEnter.bezierCurve
                }
            }
        }
        readonly property QtObject scroll: standardDecel
        readonly property QtObject clickBounce: QtObject {
            readonly property int duration: root.durations.normal
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveDefaultSpatial
        }
    }
}
