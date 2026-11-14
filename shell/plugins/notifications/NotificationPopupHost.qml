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
            // the ledger's (StateProjection), its edge is appearance config.
            readonly property bool barEnabled: StateProjection.isEnabled("bar")
            readonly property string barEdge: Config.options?.bar?.edge ?? "top"
            readonly property bool barTop: barEnabled && barEdge === "top"
            readonly property bool barRight: barEnabled && barEdge === "right"
            // B9.4/B9.5: the bar's real thickness and outer edge margin, not
            // the legacy 0.85-scaled Sizes tokens (they were 37.4/6.8 against
            // a 36px bar, so the popup overlapped the bar it was avoiding).
            readonly property real barOffset: (barEdge === "left" || barEdge === "right" ? Appearance.sizes.verticalBarWidth : Appearance.sizes.barHeight) + (Config.options?.bar?.edgeMargin ?? 0) + 12
            readonly property int notifWidth: 380
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
                top: true
                right: true
            }

            margins {
                top: (popupWindow.barTop ? popupWindow.barOffset : 16) - popupWindow.shadowBuffer
                right: (popupWindow.barRight ? popupWindow.barOffset : 16) - popupWindow.shadowBuffer
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
                    color: Appearance.applyAlpha(Appearance.colors.colLayer0, Appearance.backgroundOpacity)
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
