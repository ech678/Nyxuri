pragma ComponentBehavior: Bound
import QtQuick
import qs.commons

// Default text primitive for the dashboard tree. Ported from end4-pC's
// StyledText, including the number-font switch and the slide/fade text-change
// animation.
//
// Token mapping (D-1 single M3 scale; the local 0.85 dense-panel era is
// over — type comes from NexusStyle.font at 1.0 everywhere):
//   small/smallie 15/13 -> bodyMedium   14
//   normal        16    -> bodyLarge    16
//   larger        19    -> titleLarge   22
//   huge          22    -> titleLarge   22
//   smaller       12    -> bodySmall    12
//
// Deviation from the end4 baseline (bar media bug, 2026-11-15): the slide
// rides on a Translate transform instead of the item's x/y. Upstream captures
// originalX/originalY once at Component.onCompleted — before the parent
// layout's first polish — so every later text change ends the animation on a
// stale coordinate that overrides the layout: after a track change the bar
// media artist/title lines settled ~6px high (or on each other's rows) until
// an unrelated re-layout happened to fix them. x/y belong to the layout; the
// transform always ends at 0, so residue is structurally impossible. Slide
// distance, curve and duration are unchanged.
Text {
    id: root

    property bool animateChange: false
    property real animationDistanceX: 0
    property real animationDistanceY: 6

    renderType: Text.NativeRendering
    verticalAlignment: Text.AlignVCenter

    // Numeric strings get the numeric family so digits stay tabular; everything
    // else uses the UI family. Same rule as upstream.
    readonly property bool shouldUseNumberFont: /^\d+$/.test(root.text)
    readonly property string defaultFont: root.shouldUseNumberFont ? Fonts.numeric : Fonts.ui

    font {
        hintingPreference: Font.PreferDefaultHinting
        family: root.defaultFont
        pixelSize: NexusStyle.font.bodyLarge
        variableAxes: root.shouldUseNumberFont ? ({}) : ({
                "wght": 450
            })
    }
    color: Appearance.m3colors.m3onBackground
    linkColor: Appearance.m3colors.m3primary

    transform: Translate {
        id: slideTransform
        x: 0
        y: 0
    }

    component Anim: NumberAnimation {
        target: slideTransform
        duration: 150
        easing.type: Easing.BezierSpline
        easing.bezierCurve: Appearance.animationCurves.expressiveFastEffects
    }

    Behavior on text {
        enabled: root.animateChange

        SequentialAnimation {
            alwaysRunToEnd: true

            ParallelAnimation {
                Anim {
                    property: "x"
                    to: -root.animationDistanceX
                    easing.type: Easing.InSine
                }
                Anim {
                    property: "y"
                    to: -root.animationDistanceY
                    easing.type: Easing.InSine
                }
                Anim {
                    target: root
                    property: "opacity"
                    to: 0
                    easing.type: Easing.InSine
                }
            }
            PropertyAction {} // Tie the text update to this point (we don't want it to happen during the first slide+fade)
            PropertyAction {
                target: slideTransform
                property: "x"
                value: root.animationDistanceX
            }
            PropertyAction {
                target: slideTransform
                property: "y"
                value: root.animationDistanceY
            }
            ParallelAnimation {
                Anim {
                    property: "x"
                    to: 0
                    easing.type: Easing.OutSine
                }
                Anim {
                    property: "y"
                    to: 0
                    easing.type: Easing.OutSine
                }
                Anim {
                    target: root
                    property: "opacity"
                    to: 1
                    easing.type: Easing.OutSine
                }
            }
        }
    }
}
