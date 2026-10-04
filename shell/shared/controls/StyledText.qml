pragma ComponentBehavior: Bound
import QtQuick
import qs.shared.theme

// Default text primitive for the dashboard tree. Ported from end4-pC's
// StyledText, including the number-font switch and the slide/fade text-change
// animation.
//
// Token mapping (end4-pC px -> nyxuri Typography, which carries the local 0.85
// dense-panel scale):
//   small/smallie 15/13 -> bodyLarge   16*0.85 = 14
//   normal        16    -> bodyLarge   16*0.85 = 14
//   larger        19    -> titleLarge  22*0.85 = 19
//   huge          22    -> headlineSmall 24*0.85 = 20
//   smaller       12    -> bodySmall   12*0.85 = 10
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
        pixelSize: Typography.bodyLarge.pixelSize
        variableAxes: root.shouldUseNumberFont ? ({}) : ({
                                                             "wght": 450
                                                         })
    }
    color: Appearance.m3colors.m3onBackground
    linkColor: Appearance.m3colors.m3primary

    component Anim: NumberAnimation {
        target: root
        duration: 150
        easing.type: Easing.BezierSpline
        easing.bezierCurve: Appearance.animationCurves.expressiveFastEffects
    }

    Component.onCompleted: {
        textAnimationBehavior.originalX = root.x;
        textAnimationBehavior.originalY = root.y;
    }

    Behavior on text {
        id: textAnimationBehavior

        property real originalX: root.x
        property real originalY: root.y

        enabled: root.animateChange

        SequentialAnimation {
            alwaysRunToEnd: true

            ParallelAnimation {
                Anim {
                    property: "x"
                    to: textAnimationBehavior.originalX - root.animationDistanceX
                    easing.type: Easing.InSine
                }
                Anim {
                    property: "y"
                    to: textAnimationBehavior.originalY - root.animationDistanceY
                    easing.type: Easing.InSine
                }
                Anim {
                    property: "opacity"
                    to: 0
                    easing.type: Easing.InSine
                }
            }
            PropertyAction {} // Tie the text update to this point (we don't want it to happen during the first slide+fade)
            PropertyAction {
                target: root
                property: "x"
                value: textAnimationBehavior.originalX + root.animationDistanceX
            }
            PropertyAction {
                target: root
                property: "y"
                value: textAnimationBehavior.originalY + root.animationDistanceY
            }
            ParallelAnimation {
                Anim {
                    property: "x"
                    to: textAnimationBehavior.originalX
                    easing.type: Easing.OutSine
                }
                Anim {
                    property: "y"
                    to: textAnimationBehavior.originalY
                    easing.type: Easing.OutSine
                }
                Anim {
                    property: "opacity"
                    to: 1
                    easing.type: Easing.OutSine
                }
            }
        }
    }
}
