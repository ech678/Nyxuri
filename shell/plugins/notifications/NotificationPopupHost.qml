import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.commons
import qs.ui
import qs.services

Scope {
    id: root

    Variants {
        model: Quickshell.screens

        delegate: PanelWindow {
            id: popupWindow

            required property var modelData

            // Slot placement, not a private switch: the bar's existence is
            // the ledger's (StateProjection); the avoidance insets are the
            // topology projection's (ScreenBarLayout) — per-screen, per-edge,
            // autoHide bars reserve nothing. D4g 批四b: the selected-bar
            // bridge read retired (it could not see a rail on another entry).
            readonly property real topReserve: ScreenBarLayout.reservation(modelData, "top")
            readonly property real bottomReserve: ScreenBarLayout.reservation(modelData, "bottom")
            readonly property real leftReserve: ScreenBarLayout.reservation(modelData, "left")
            readonly property real rightReserve: ScreenBarLayout.reservation(modelData, "right")
            readonly property string notifPos: PersonalizationConfig.notificationPosition
            readonly property bool isBottom: notifPos.indexOf("bottom") === 0
            readonly property bool isLeft: notifPos.endsWith("left")
            readonly property bool isCenter: notifPos.endsWith("center")
            readonly property int notifWidth: PersonalizationConfig.notificationWidth
            readonly property real notifOpacity: PersonalizationConfig.notificationOpacity >= 0 ? PersonalizationConfig.notificationOpacity : Appearance.backgroundOpacity
            readonly property int notifContentHeight: NotificationService.popupList.reduce((h, notif) => {
                return h + (NotificationService.normalActions(notif).length > 0 ? 104 : 64);
            }, 0) + Math.max(0, NotificationService.popupList.length - 1) * 10
            readonly property int cardHeight: notifContentHeight > 0 ? (notifContentHeight + 20) : 0
            readonly property real shadowBuffer: 10

            screen: modelData
            color: "transparent"
            exclusiveZone: 0
            WlrLayershell.namespace: "nyxuri-shell-notifications"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.exclusionMode: ExclusionMode.Ignore
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            visible: NotificationService.popupList.length > 0 && !NotificationService.popupInhibited

            anchors {
                top: !popupWindow.isBottom
                bottom: popupWindow.isBottom
                left: popupWindow.isLeft
                right: !popupWindow.isLeft && !popupWindow.isCenter
            }

            margins {
                top: (!popupWindow.isBottom ? (popupWindow.topReserve > 0 ? popupWindow.topReserve + 12 : 16) : 0) - popupWindow.shadowBuffer
                bottom: (popupWindow.isBottom ? (popupWindow.bottomReserve > 0 ? popupWindow.bottomReserve + 12 : 16) : 0) - popupWindow.shadowBuffer
                left: (popupWindow.isLeft ? (popupWindow.leftReserve > 0 ? popupWindow.leftReserve + 12 : 16) : 0) - popupWindow.shadowBuffer
                right: (!popupWindow.isLeft && !popupWindow.isCenter ? (popupWindow.rightReserve > 0 ? popupWindow.rightReserve + 12 : 16) : 0) - popupWindow.shadowBuffer
            }

            implicitWidth: notifWidth + shadowBuffer * 2
            implicitHeight: cardHeight + shadowBuffer * 2

            Item {
                anchors.fill: parent

                StyledRectangularShadow {
                    target: cardBackground
                    opacity: cardBackground.opacity
                }

                Rectangle {
                    id: cardBackground

                    anchors.centerIn: parent
                    width: popupWindow.notifWidth
                    height: popupWindow.cardHeight
                    radius: Appearance.rounding.large
                    color: Appearance.applyAlpha(Appearance.colors.colLayer0Base, popupWindow.notifOpacity)
                    border.width: 1
                    border.color: Appearance.colors.colLayer0Border
                    clip: true

                    Behavior on height {
                        NumberAnimation {
                            duration: Appearance.animation.expressiveEffects.duration
                            easing.type: Appearance.animation.expressiveEffects.type
                            easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                        }
                    }

                    NotificationContent {
                        anchors.centerIn: parent
                        width: parent.width - 20
                        height: Math.max(0, parent.height - 20)
                        manager: NotificationService
                    }
                }

                CompositorBlurRegion {
                    targetWindow: popupWindow
                    backgroundItem: cardBackground
                    radius: cardBackground.radius
                }
            }
        }
    }
}
