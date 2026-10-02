pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property QtObject curves: QtObject {
        readonly property var standard: [0.2, 0, 0, 1, 1, 1]
        readonly property var standardAccel: [0.3, 0, 1, 1, 1, 1]
        readonly property var standardDecel: [0, 0, 0, 1, 1, 1]
        readonly property var emphasized: [0.05, 0, 0.1333, 0.06, 0.1667, 0.4, 0.2083, 0.82, 0.25, 1, 1, 1]
        readonly property var expressiveFastEffects: [0.31, 0.94, 0.34, 1, 1, 1]
        readonly property var expressiveDefaultEffects: [0.34, 0.8, 0.34, 1, 1, 1]
        readonly property var expressiveSlowEffects: [0.34, 0.88, 0.34, 1, 1, 1]
        readonly property var expressiveFastSpatial: [0.42, 1.67, 0.21, 0.9, 1, 1]
        readonly property var expressiveDefaultSpatial: [0.38, 1.21, 0.22, 1, 1, 1]
        readonly property var expressiveSlowSpatial: [0.39, 1.29, 0.35, 0.98, 1, 1]
    }

    readonly property QtObject durations: QtObject {
        readonly property int small: 200
        readonly property int normal: 400
        readonly property int large: 600
        readonly property int extraLarge: 1000
        readonly property int expressiveFastEffects: 150
        readonly property int expressiveDefaultEffects: 200
        readonly property int expressiveSlowEffects: 300
        readonly property int expressiveFastSpatial: 350
        readonly property int expressiveDefaultSpatial: 500
        readonly property int expressiveSlowSpatial: 650
    }

    readonly property QtObject animation: QtObject {
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

        readonly property QtObject expressiveFastSpatial: QtObject {
            readonly property int duration: root.durations.expressiveFastSpatial
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveFastSpatial
        }

        readonly property QtObject expressiveDefaultSpatial: QtObject {
            readonly property int duration: root.durations.expressiveDefaultSpatial
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveDefaultSpatial
        }

        readonly property QtObject expressiveSlowSpatial: QtObject {
            readonly property int duration: root.durations.expressiveSlowSpatial
            readonly property int type: Easing.BezierSpline
            readonly property var bezierCurve: root.curves.expressiveSlowSpatial
        }
    }

    readonly property QtObject rounding: QtObject {
        readonly property real none: 0
        readonly property real small: 4
        readonly property real normal: 8
        readonly property real medium: 12
        readonly property real large: 16
        readonly property real extraLarge: 28
        readonly property real full: 9999
    }

    readonly property QtObject spacing: QtObject {
        readonly property real tight: 4
        readonly property real normal: 8
        readonly property real medium: 12
        readonly property real large: 16
        readonly property real extraLarge: 24
        readonly property real huge: 32
    }

    readonly property QtObject interaction: QtObject {
        readonly property real hoverStateLayerOpacity: 0.08
        readonly property real focusStateLayerOpacity: 0.12
        readonly property real pressedStateLayerOpacity: 0.12
        readonly property real selectedStateLayerOpacity: 0.08
        readonly property int stateLayerTransitionDuration: 200
        readonly property int rippleDuration: 700
    }

    function clamp01(value) {
        return Math.max(0, Math.min(1, value));
    }

    function mix(color1, color2, percentage) {
        const amount = percentage === undefined ? 0.5 : percentage;
        const c1 = Qt.color(color1);
        const c2 = Qt.color(color2);
        return Qt.rgba(
            amount * c1.r + (1 - amount) * c2.r,
            amount * c1.g + (1 - amount) * c2.g,
            amount * c1.b + (1 - amount) * c2.b,
            amount * c1.a + (1 - amount) * c2.a
        );
    }

    function transparentize(color, percentage) {
        const amount = percentage === undefined ? 1 : percentage;
        const c = Qt.color(color);
        return Qt.rgba(c.r, c.g, c.b, c.a * (1 - amount));
    }

    function applyAlpha(color, alpha) {
        const c = Qt.color(color);
        return Qt.rgba(c.r, c.g, c.b, clamp01(alpha));
    }

    readonly property QtObject colors: QtObject {
        // Default Dark Material 3 Palette (pure fallback values)
        property color colBackground: "#0f1416"
        property color colLayer0: "#171d20"
        property color colLayer1: "#1f2528"
        property color colLayer1Hover: "#2d3438"
        property color colLayer1Active: "#3a4146"
        property color colLayer2: "#272d31"
        property color colLayer3: "#2f363a"
        property color colOnLayer0: "#dee3e6"
        property color colOnLayer1: "#dee3e6"
        property color colOnSurface: "#dee3e6"
        property color colOnSurfaceVariant: "#c0c7cd"

        property color colPrimary: "#8ad0ef"
        property color colOnPrimary: "#003544"
        property color colPrimaryHover: "#a4ddf5"
        property color colPrimaryActive: "#70c3e7"
        property color colPrimaryContainer: "#004d62"
        property color colOnPrimaryContainer: "#bee9ff"

        property color colSecondary: "#b4cad6"
        property color colOnSecondary: "#1f333c"
        property color colSecondaryContainer: "#354a53"
        property color colOnSecondaryContainer: "#d0e6f2"

        property color colError: "#ffb4ab"
        property color colOnError: "#690005"
        property color colErrorContainer: "#93000a"
        property color colOnErrorContainer: "#ffdad6"

        property color colOutline: "#8a9297"
        property color colOutlineVariant: "#40484c"
        property color colScrim: "#000000"
    }
}
