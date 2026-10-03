pragma Singleton
import QtQuick
import Quickshell
import qs.core

Singleton {
    id: root

    readonly property string fontFamily: "sans-serif"
    readonly property int barHeight: 34
    readonly property int radius: 20
    readonly property int radiusSmall: 12
    readonly property int radiusTiny: 8
    readonly property int pad: 14
    readonly property int gap: 8
    readonly property int fs: 12
    readonly property int fsSmall: 10
    readonly property int fsBig: 16
    readonly property int fsTitle: 20

    function p(k) {
        var v = Color.scheme[k]
        return v ? v : "#ff00ff"
    }

    function rgba(k, a) {
        var c = Qt.color(root.p(k))
        return Qt.rgba(c.r, c.g, c.b, a)
    }

    function hex2rgba(h, a) {
        var c = Qt.color(h)
        return Qt.rgba(c.r, c.g, c.b, a)
    }

    readonly property color accent: p("primary")
    readonly property color accentSoft: p("primaryContainer")
    readonly property color onAccent: p("onPrimary")
    readonly property color onAccentSoft: p("onPrimaryContainer")
    readonly property color text: p("onSurface")
    readonly property color textMuted: p("onSurfaceVariant")
    readonly property color line: p("outlineVariant")
    readonly property color base: p("surface")
    readonly property color elevated: p("surfaceContainerHigh")
    readonly property color err: p("error")

    function panel() {
        return rgba("surfaceContainerHigh", 0.97)
    }

    function chip() {
        return rgba("surfaceContainerHighest", 0.72)
    }

    function chipActive() {
        return rgba("primaryContainer", 0.95)
    }

    function scrim() {
        return rgba("scrim", 0.6)
    }

    function shadowColor() {
        return rgba("scrim", 0.45)
    }
}