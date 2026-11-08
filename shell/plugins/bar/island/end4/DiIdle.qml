// Fork & Trim: end4-pC modules/ii/bar/DiIdle.qml (GPL-3, see shell/LICENSE
// appendix end-4-dots-hyprland-GPL-3.0.txt). Trimmed per the B volume four
// classes: upstream singletons -> tree services, Config.options -> keys,
// dead upstream paths dropped (systemIcons substitution, network/mic mute
// indicators land in B3-2 with their services).
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell
import qs.services
import qs.commons
import qs.ui

Item {
    id: root
    required property Item di
    anchors.fill: parent

    // Upstream hides the mic/volume/wifi indicators when a "systemIcons"
    // widget sits in the bar. The tree keeps those in the bar indicators, so
    // idle never duplicates them.
    readonly property bool systemIconsElsewhere: true

    Rectangle {
        id: avatarRect
        width: di.isMaterial ? di.pillHeight : di.pillHeight - 8
        height: di.isMaterial ? di.pillHeight : di.pillHeight - 8
        anchors {
            left: parent.left
            leftMargin: di.isMaterial ? 0 : 4
            verticalCenter: parent.verticalCenter
        }
        radius: width / 2
        color: Appearance.colors.colPrimaryContainer

        Image {
            id: avatarImage
            anchors.fill: parent
            source: AvatarService.avatarPath !== "" ? AvatarService.avatarUrl : "file:///home/" + (Quickshell.env("USER") ?? "user") + "/.face"
            sourceSize.width: avatarImage.width * 2
            sourceSize.height: avatarImage.height * 2
            fillMode: Image.PreserveAspectCrop
            layer.enabled: true
            layer.effect: OpacityMask {
                maskSource: Rectangle {
                    width: avatarRect.width
                    height: avatarRect.height
                    radius: avatarRect.radius
                }
            }
            onStatusChanged: {
                if (status === Image.Error)
                    visible = false;
            }
        }
    }

    RowLayout {
        id: rightSideRow
        anchors {
            right: parent.right
            rightMargin: 10
            verticalCenter: parent.verticalCenter
        }
        spacing: 8

        RowLayout {
            id: idleIconsRow
            Layout.alignment: Qt.AlignVCenter
            spacing: 4

            Revealer {
                reveal: (NotificationService.unread ?? 0) > 0
                Item {
                    implicitWidth: notifRow.implicitWidth
                    implicitHeight: notifRow.implicitHeight

                    RowLayout {
                        id: notifRow
                        spacing: 2
                        MaterialSymbol {
                            text: "notifications"
                            iconSize: Appearance.font.pixelSize.normal
                            color: Appearance.colors.colOnLayer0
                        }
                        StyledText {
                            text: `${NotificationService.unread}`
                            font.pixelSize: Appearance.font.pixelSize.smallest
                            font.features: {
                                "tnum": 1
                            }
                            color: Appearance.colors.colOnLayer0
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        // Upstream toggles its right sidebar; the tree's
                        // notifications surface is the dashboard info view.
                        onClicked: WidgetState.dashboardSidebarOpen && WidgetState.dashboardSidebarView === "info" ? ActionGateway.requestSidebarToggle("dashboard") : ActionGateway.requestSidebarOpenOnScreen("dashboard", "info", "")
                    }
                }
            }
        }

        Loader {
            Layout.alignment: Qt.AlignVCenter
            sourceComponent: clockComponent

            Component {
                id: clockComponent
                StyledText {
                    text: TimeService.hours + ":" + TimeService.minutes
                    font.pixelSize: di.isMaterial ? Appearance.font.pixelSize.normal : Appearance.font.pixelSize.small
                    font.features: {
                        "tnum": 1
                    }
                    color: Appearance.colors.colOnLayer0
                }
            }
        }

        readonly property real computedIdleWidth: avatarRect.width + (di.isMaterial ? 0 : 4) + 10 + rightSideRow.implicitWidth + 10

        onComputedIdleWidthChanged: di.idleTextContentWidth = rightSideRow.computedIdleWidth
        Component.onCompleted: di.idleTextContentWidth = rightSideRow.computedIdleWidth
    }
}
