// Fork & Trim: end4-pC modules/ii/bar/DiIdle.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell
import qs.services
import qs.commons
import qs.ui

Item {
    id: diIdleRoot
    required property Item di

    property string weatherLeaseId: ""
    Component.onCompleted: {
        weatherLeaseId = WeatherService.allocateLeaseId("di-idle");
        WeatherService.acquire(weatherLeaseId);
    }
    Component.onDestruction: {
        if (weatherLeaseId !== "")
            WeatherService.release(weatherLeaseId);
    }
    anchors.fill: parent

    readonly property bool systemIconsElsewhere:
        Config.options.bar.layouts.leftLayout.includes("systemIcons")
        || Config.options.bar.layouts.rightLayout.includes("systemIcons")

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
            source: Config.options.profile.avatarPath !== ""
                ? "file://" + Config.options.profile.avatarPicture
                : "file://" + Paths.profileAvatar
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
                    visible = false
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
                reveal: !diIdleRoot.systemIconsElsewhere && VolumeService.sourceMuted
                MaterialSymbol {
                    text: "mic_off"
                    iconSize: Appearance.font.pixelSize.normal
                    color: Appearance.colors.colOnLayer0
                }
            }

            Revealer {
                reveal: !diIdleRoot.systemIconsElsewhere && VolumeService.sinkMuted
                MaterialSymbol {
                    text: "volume_off"
                    iconSize: Appearance.font.pixelSize.normal
                    color: Appearance.colors.colOnLayer0
                }
            }

            Revealer {
                reveal: !diIdleRoot.systemIconsElsewhere && !NetworkService.connected
                MaterialSymbol {
                    text: "wifi_off"
                    iconSize: Appearance.font.pixelSize.normal
                    color: Appearance.colors.colError
                }
            }

            Revealer {
                reveal: (NotificationService.unreadCount ?? 0) > 0
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
                            text: `${NotificationService.unreadCount}`
                            font.pixelSize: Appearance.font.pixelSize.smallest
                            font.features: { "tnum": 1 }
                            color: Appearance.colors.colOnLayer0
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: ActionGateway.requestSidebarToggle("dashboard")
                    }
                }
            }
        }

        Loader {
            Layout.alignment: Qt.AlignVCenter
            sourceComponent: Config.options.bar.dynamicIsland.leftWidget === "clockWidget" ? weatherComponent : clockComponent

            Component {
                id: clockComponent
                StyledText {
                    text: DateTime.time
                    font.pixelSize: di.isMaterial ? Appearance.font.pixelSize.normal : Appearance.font.pixelSize.small
                    font.features: { "tnum": 1 }
                    color: Appearance.colors.colOnLayer0
                }
            }

            Component {
                id: weatherComponent
                RowLayout {
                    spacing: 4

                    MaterialSymbol {
                        fill: 0
                        text: "cloud"
                        iconSize: Appearance.font.pixelSize.normal
                        color: Appearance.colors.colOnLayer0
                        Layout.alignment: Qt.AlignVCenter
                    }

                    StyledText {
                        font.pixelSize: di.isMaterial ? Appearance.font.pixelSize.normal : Appearance.font.pixelSize.small
                        font.features: { "tnum": 1 }
                        color: Appearance.colors.colOnLayer0
                        text: WeatherService.hasValidData ? (Math.round(WeatherService.currentTemperatureC) + "°") : "--°"
                        Layout.alignment: Qt.AlignVCenter
                    }
                }
            }
        }

        readonly property real computedIdleWidth: avatarRect.width
            + (di.isMaterial ? 0 : 4)
            + 10
            + rightSideRow.implicitWidth
            + 10

        onComputedIdleWidthChanged: di.idleTextContentWidth = rightSideRow.computedIdleWidth
        Component.onCompleted: di.idleTextContentWidth = rightSideRow.computedIdleWidth
    }
}