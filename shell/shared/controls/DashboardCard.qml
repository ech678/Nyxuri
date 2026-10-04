pragma ComponentBehavior: Bound
import QtQuick
import Qt5Compat.GraphicalEffects
import qs.shared.theme

// Staggered card used by the settings dashboard grid. Ported from end4-pC's
// DashboardCard so the shell keeps the same spring-in / fly-out feel.
//
// Difference from upstream: blur is injected, not looked up. The original read
// Config.options.background.widgets.blurRadius directly, which the shared layer
// is not allowed to do — callers pass blurSource and blurRadius instead.
Rectangle {
    id: root

    property color tint: Appearance.colors.colLayer1
    property real tintOpacity: 0.35
    property real cardRadius: Appearance.rounding.large

    // When set, the card draws the blurred backdrop of this item instead of a
    // flat tint. Used by pages that sit on top of a wallpaper or album art.
    property Item blurSource: null
    property real blurRadius: 32

    // Entry/exit choreography. pager owns the grid and emits
    // pageExitRequested when the user navigates away, which flies every card
    // out in the same staggered order it flew in.
    property Item pager: null
    property int animIndex: 0
    property int staggerMs: 45
    property real travelX: 0
    property real travelY: 0

    property real animScale: 0.25
    property real animOpacity: 0
    property real offsetX: travelX
    property real offsetY: travelY

    color: root.blurSource ? "transparent" : root.tint
    radius: root.cardRadius

    transformOrigin: Item.Center
    scale: root.animScale
    opacity: root.animOpacity
    transform: Translate {
        x: root.offsetX
        y: root.offsetY
    }

    Loader {
        anchors.fill: parent
        anchors.margins: -1
        active: root.blurSource !== null

        sourceComponent: Item {
            id: backdrop

            // Oversample past the card edge so the blur kernel does not pull
            // transparent pixels in from the border.
            readonly property real oversample: root.blurRadius * 1.5

            layer.enabled: true
            layer.effect: OpacityMask {
                maskSource: Rectangle {
                    width: backdrop.width
                    height: backdrop.height
                    radius: root.cardRadius + 1
                }
            }

            FastBlur {
                id: blur

                x: -backdrop.oversample
                y: -backdrop.oversample
                width: backdrop.width + backdrop.oversample * 2
                height: backdrop.height + backdrop.oversample * 2
                radius: root.blurRadius
                source: shaderSource

                ShaderEffectSource {
                    id: shaderSource

                    sourceItem: root.blurSource
                    hideSource: false
                    live: true
                    // sourceRect is in blurSource coordinates, so map through
                    // the card itself — the card animates, the source does not.
                    sourceRect: {
                        const point = root.mapToItem(root.blurSource, -backdrop.oversample,
                                                     -backdrop.oversample);
                        return Qt.rect(point.x, point.y, blur.width, blur.height);
                    }
                }
            }

            Rectangle {
                anchors.fill: parent
                radius: root.cardRadius + 1
                color: root.tint
                opacity: root.tintOpacity
            }
        }
    }

    SequentialAnimation {
        id: enterAnim

        PauseAnimation {
            duration: root.animIndex * root.staggerMs
        }
        ParallelAnimation {
            SpringAnimation {
                target: root
                property: "animScale"
                to: 1
                spring: 2.6
                damping: 0.32
            }
            SpringAnimation {
                target: root
                property: "offsetX"
                to: 0
                spring: 2.6
                damping: 0.32
            }
            SpringAnimation {
                target: root
                property: "offsetY"
                to: 0
                spring: 2.6
                damping: 0.32
            }
            NumberAnimation {
                target: root
                property: "animOpacity"
                to: 1
                duration: 220
                easing.type: Easing.OutQuad
            }
        }
    }

    SequentialAnimation {
        id: exitAnim

        PauseAnimation {
            duration: root.animIndex * Math.max(1, root.staggerMs - 4)
        }
        ParallelAnimation {
            NumberAnimation {
                target: root
                property: "animScale"
                to: 0.25
                duration: 260
                easing.type: Easing.InBack
            }
            NumberAnimation {
                target: root
                property: "offsetX"
                to: root.travelX
                duration: 280
                easing.type: Easing.InQuad
            }
            NumberAnimation {
                target: root
                property: "offsetY"
                to: root.travelY
                duration: 280
                easing.type: Easing.InQuad
            }
            NumberAnimation {
                target: root
                property: "animOpacity"
                to: 0
                duration: 220
                easing.type: Easing.InQuad
            }
        }
    }

    Component.onCompleted: enterAnim.start()

    Connections {
        target: root.pager
        ignoreUnknownSignals: true

        function onPageExitRequested() {
            exitAnim.restart();
        }
    }
}
