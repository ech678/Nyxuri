import QtQuick
import qs.shared.theme

Item {
    id: root

    required property color backgroundColor
    property bool open: false
    property bool onLeft: true
    property color shadowColor: Appearance.colors.colShadow
    default property alias content: contentFrame.data
    // The host combines both viewports into one compositor blur region.
    readonly property alias blurBackgroundItem: revealViewport
    property real revealProgress: 0

    signal closed

    function reset() {
        revealAnimation.stop();
        revealProgress = 0;
    }

    function animateReveal() {
        revealAnimation.stop();
        const targetProgress = open ? 1 : 0;
        if (revealProgress === targetProgress) {
            if (!open) {
                Qt.callLater(() => {
                    if (!root.open && root.visible && root.revealProgress === 0)
                        root.closed();
                });
            }
            return;
        }
        revealAnimation.from = revealProgress;
        revealAnimation.to = targetProgress;
        revealAnimation.duration = Math.round((open ? Animations.durations.sidebarEnter :
                                                      Animations.durations.sidebarExit) * Math.abs(
                                                  targetProgress - revealProgress));
        // Select before start(): an onOpenChanged handler can run before a
        // separate easing binding has observed the new direction.
        revealAnimation.easing.bezierCurve = open ? Animations.curves.emphasizedDecel :
                                                    Animations.curves.emphasizedAccel;
        revealAnimation.start();
    }

    function containsVisiblePoint(localX, localY) {
        return visible && revealViewport.width > 0 && localX >= revealViewport.x && localX < revealViewport.x
                + revealViewport.width && localY >= 0 && localY < height;
    }

    onOpenChanged: animateReveal()
    Component.onCompleted: {
        if (open)
            animateReveal();
    }

    NumberAnimation {
        id: revealAnimation

        target: root
        property: "revealProgress"
        easing.type: Easing.BezierSpline
        onFinished: {
            if (!root.open)
                root.closed();
        }
    }

    Item {
        id: revealViewport

        x: root.onLeft ? 0 : root.width - width
        width: root.width * Math.max(0, Math.min(1, root.revealProgress))
        height: root.height
        clip: true

        Item {
            id: contentFrame

            // Cancel the right-hand viewport's moving origin. Content keeps its
            // final screen position and full layout size throughout the reveal.
            x: -revealViewport.x
            width: root.width
            height: root.height

            Rectangle {
                z: -1
                anchors.fill: parent
                color: root.backgroundColor
            }
        }

        // The desktop appears to cover the surface: shade inward from the
        // moving seam, without a full-surface effect or offscreen texture.
        Rectangle {
            x: root.onLeft ? revealViewport.width - width : 0
            width: Math.min(24, root.width)
            height: revealViewport.height
            opacity: Math.min(1, revealViewport.width / Math.max(1, width))
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0
                    color: root.onLeft ? "transparent" : root.shadowColor
                }
                GradientStop {
                    position: 0.5
                    color: Qt.rgba(root.shadowColor.r, root.shadowColor.g, root.shadowColor.b,
                                   root.shadowColor.a * 0.25)
                }
                GradientStop {
                    position: 1
                    color: root.onLeft ? root.shadowColor : "transparent"
                }
            }
        }
    }
}
