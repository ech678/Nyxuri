import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.modules.keystone.notifications

Scope {
    id: root

    Variants {
        model: Quickshell.screens

        delegate: PanelWindow {
            id: popupWindow

            required property var modelData

            readonly property bool barTop: PersonalizationConfig.barEnabled && PersonalizationConfig.barPosition === "top"
            readonly property bool barRight: PersonalizationConfig.barEnabled && PersonalizationConfig.barPosition === "right"
            readonly property int notifWidth: 380
            readonly property int notifContentHeight: NotificationManager.popupList.reduce((h, notif) => {
                return h + (NotificationManager.normalActions(notif).length > 0 ? 104 : 64);
            }, 0) + Math.max(0, NotificationManager.popupList.length - 1) * 10
            readonly property int cardHeight: notifContentHeight > 0 ? (notifContentHeight + 20) : 0
            readonly property real shadowBuffer: 10

            screen: modelData
            color: "transparent"
            exclusiveZone: 0
            WlrLayershell.namespace: "nyxuri-shell-notifications"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.exclusionMode: ExclusionMode.Ignore
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            visible: NotificationManager.popupList.length > 0 && !NotificationManager.popupInhibited

            anchors {
                top: true
                right: true
            }

            margins {
                top: (popupWindow.barTop ? (Sizes.barOuterEdgeMargin + Sizes.barVisualThickness + 12) : 16) - popupWindow.shadowBuffer
                right: (popupWindow.barRight ? (Sizes.barOuterEdgeMargin + Sizes.barVisualThickness + 12) : 16) - popupWindow.shadowBuffer
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
                        manager: NotificationManager
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
