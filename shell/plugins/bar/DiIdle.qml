// Fork & Trim: end4-pC modules/ii/bar/DiIdle.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import qs.services
import qs.commons
import qs.ui
import "island/clock"

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

    readonly property bool systemIconsElsewhere: Config.options.bar.layouts.leftLayout.includes("systemIcons") || Config.options.bar.layouts.rightLayout.includes("systemIcons")
    readonly property bool showAvatar: PersonalizationConfig.islandShowAvatar

    // Probe surface (scripts/dev/probe-bar.sh): the horizontal clock and the
    // avatar fallback are the two idle-face facts that cannot be read from the
    // bar geometry.
    readonly property var probeClockFace: satelliteLoader.item
    readonly property bool probeAvatarVisible: diIdleRoot.showAvatar
    readonly property bool probeAvatarReady: avatarImage.status === Image.Ready
    readonly property bool probeAvatarFallback: avatarFallback.visible

    Rectangle {
        id: avatarRect
        width: di.isMaterial ? di.pillHeight : di.pillHeight - 8
        height: di.isMaterial ? di.pillHeight : di.pillHeight - 8
        visible: diIdleRoot.showAvatar
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
            source: diIdleRoot.showAvatar ? AvatarService.avatarUrl : ""
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
        }

        // No ~/.face (or an unreadable one) must not leave an empty tinted
        // circle: fall back to the account glyph.
        MaterialSymbol {
            id: avatarFallback

            anchors.centerIn: parent
            visible: avatarImage.status !== Image.Ready
            text: "person"
            iconSize: di.isMaterial ? Appearance.font.pixelSize.large : Appearance.font.pixelSize.normal
            color: Appearance.colors.colOnPrimaryContainer
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
                        onClicked: ActionGateway.requestSidebarToggle("dashboard")
                    }
                }
            }
        }

        Loader {
            id: satelliteLoader

            Layout.alignment: Qt.AlignVCenter
            sourceComponent: PersonalizationConfig.islandSatellite === "clock" ? clockComponent : PersonalizationConfig.islandSatellite === "weather" ? weatherComponent : null

            Component {
                id: clockComponent
                ClockContent {
                    edge: "top"
                }
            }

            Component {
                id: weatherComponent
                RowLayout {
                    spacing: 4

                    MaterialSymbol {
                        fill: 0
                        text: WeatherService.hasValidData ? WeatherService.currentIconName : "cloud"
                        iconSize: Appearance.font.pixelSize.normal
                        color: Appearance.colors.colOnLayer0
                        Layout.alignment: Qt.AlignVCenter
                    }

                    StyledText {
                        font.pixelSize: di.isMaterial ? Appearance.font.pixelSize.normal : Appearance.font.pixelSize.small
                        font.features: {
                            "tnum": 1
                        }
                        color: Appearance.colors.colOnLayer0
                        text: WeatherService.hasValidData ? (Math.round(WeatherService.currentTemperatureC) + "°") : "--°"
                        Layout.alignment: Qt.AlignVCenter
                    }
                }
            }
        }

        readonly property real avatarBlockWidth: diIdleRoot.showAvatar ? avatarRect.width + (di.isMaterial ? 0 : 4) : 0
        readonly property real computedIdleWidth: avatarBlockWidth + 10 + rightSideRow.implicitWidth + 10

        onComputedIdleWidthChanged: di.idleTextContentWidth = rightSideRow.computedIdleWidth
        Component.onCompleted: di.idleTextContentWidth = rightSideRow.computedIdleWidth
    }
}
