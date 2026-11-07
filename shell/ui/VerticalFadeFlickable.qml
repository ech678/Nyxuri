pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import qs.commons

// Vertical flickable whose content fades out at the top and bottom edges
// (Caelestia VerticalFadeFlickable): a gradient mask layered over the whole
// view replaces any scrollbar; the fades snap away when the list fits.
StyledFlickable {
    id: root

    property real fadeAmount: 0.2

    property real topFadeOpacity: fadeShouldBeActive(true) ? 0 : 1
    property real bottomFadeOpacity: fadeShouldBeActive(false) ? 0 : 1

    function fadeShouldBeActive(isStart: bool): bool {
        // When content is smaller than flickable size, hide fade when rebound starts
        if (contentHeight + topMargin + bottomMargin < height && rebound.running && ((isStart
                                                                                      ? verticalOvershoot > 0 :
                                                                                        verticalOvershoot
                                                                                        < 0)))
            return false;

        if (isStart)
            return visibleArea.yPosition > 0;
        return visibleArea.yPosition + visibleArea.heightRatio < 1;
    }

    flickableDirection: Flickable.VerticalFlick
    showVerticalScrollBar: false

    layer.enabled: true
    layer.effect: MultiEffect {
        maskEnabled: true
        maskSpreadAtMin: 1
        maskThresholdMin: 0.5
        maskSource: mask

        Rectangle {
            id: mask

            anchors.fill: parent
            visible: false
            layer.enabled: true

            gradient: Gradient {
                orientation: Gradient.Vertical

                GradientStop {
                    position: 0
                    color: Qt.rgba(0, 0, 0, root.topFadeOpacity)
                }
                GradientStop {
                    position: root.fadeAmount
                    color: Qt.rgba(0, 0, 0, 1)
                }
                GradientStop {
                    position: 1 - root.fadeAmount
                    color: Qt.rgba(0, 0, 0, 1)
                }
                GradientStop {
                    position: 1
                    color: Qt.rgba(0, 0, 0, root.bottomFadeOpacity)
                }
            }
        }
    }

    Behavior on topFadeOpacity {
        NumberAnimation {
            duration: Appearance.animation.expressiveSlowEffects.duration
            easing.type: Appearance.animation.expressiveSlowEffects.type
            easing.bezierCurve: Appearance.animation.expressiveSlowEffects.bezierCurve
        }
    }

    Behavior on bottomFadeOpacity {
        NumberAnimation {
            duration: Appearance.animation.expressiveSlowEffects.duration
            easing.type: Appearance.animation.expressiveSlowEffects.type
            easing.bezierCurve: Appearance.animation.expressiveSlowEffects.bezierCurve
        }
    }
}
