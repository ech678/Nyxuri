import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.shared.theme
import qs.shared.controls
import qs.app.services

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
            readonly property int notifContentHeight: NotificationService.popupList.reduce((h, notif) => {
                const base = NotificationService.normalActions(notif).length > 0 ? 104 : 64;
                const reply = NotificationService.replyable(notif) && notif.replyOpen ? 46 : 0;
                return h + base + reply;
            }, 0) + Math.max(0, NotificationService.popupList.length - 1) * 10
            readonly property int cardHeight: notifContentHeight > 0 ? (notifContentHeight + 20) : 0
            readonly property real shadowBuffer: 10
            property bool holding: false
            Connections {
                target: NotificationService
                function onPopupListChanged() {
                    if (NotificationService.popupList.length > 0) {
                        popupWindow.holding = true;
                        return;
                    }
                    if (!Appearance.animationsEnabled) {
                        popupWindow.holding = false;
                        return;
                    }
                    popupReleaseTimer.restart();
                }
            }
            Timer {
                id: popupReleaseTimer
                interval: Appearance.animation.expressiveFastSpatial.duration + 40
                onTriggered: popupWindow.holding = false
            }
            screen: modelData
            color: "transparent"
            exclusiveZone: 0
            WlrLayershell.namespace: "nyxuri-shell-notifications"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.exclusionMode: ExclusionMode.Ignore
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            visible: (NotificationService.popupList.length > 0 || holding) && !NotificationService.popupInhibited

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
                    property real revealProgress: popupWindow.visible ? 1 : 0
                    opacity: cardBackground.revealProgress
                    transform: Translate {
                        x: Appearance.animationsEnabled ? (1 - cardBackground.revealProgress) * 24 : 0
                    }
                    Behavior on revealProgress {
                        enabled: Appearance.animationsEnabled
                        NumberAnimation {
                            duration: Appearance.animation.expressiveFastSpatial.duration
                            easing.type: Appearance.animation.expressiveFastSpatial.type
                            easing.bezierCurve: Appearance.animation.expressiveFastSpatial.bezierCurve
                        }
                    }
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
