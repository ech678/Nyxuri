// Fork & Trim: end4-pC modules/ii/bar/DiIdle.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// D1 re-layout (2026-11-21): upstream packs everything but the avatar into one
// right-anchored cluster, which left the horizontal clock uncentered with a
// hole under the 144px pill floor and let the unread Revealer's width
// animation shove the clock around. The idle face is now three segments:
// avatar left-anchored, clock/weather satellite centered, status icons
// right-anchored. The unread bell is gone (D1 处决): unread state belongs to
// the SystemIcons notification slot (8px dot, end4 `showUnreadCount=false`
// semantics) — a third copy on the idle face was pure duplication.

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
        di.idleTextContentWidth = diIdleRoot.computedIdleWidth;
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
    // bar geometry. clockSegmentCenterX pins the three-segment contract: the
    // clock cluster must sit in the pill's optical centre.
    readonly property var probeClockFace: satelliteLoader.item
    readonly property bool probeAvatarVisible: diIdleRoot.showAvatar
    readonly property bool probeAvatarReady: avatarImage.status === Image.Ready
    readonly property bool probeAvatarFallback: avatarFallback.visible
    readonly property real probeClockCenterX: satelliteLoader.x + satelliteLoader.width / 2
    readonly property real probeFaceWidth: diIdleRoot.width
    readonly property real probeStatusWidth: statusIconsRow.implicitWidth

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
            iconSize: NexusStyle.font.bodyLarge * BarScale.font
            color: Appearance.colors.colOnPrimaryContainer
        }
    }

    // Third segment: status icons, right-anchored. They only repeat the
    // SystemIcons group when that group is not on any bar lane.
    RowLayout {
        id: statusIconsRow
        anchors {
            right: parent.right
            rightMargin: 10
            verticalCenter: parent.verticalCenter
        }
        spacing: 4

        Revealer {
            reveal: !diIdleRoot.systemIconsElsewhere && VolumeService.sourceMuted
            MaterialSymbol {
                text: "mic_off"
                iconSize: NexusStyle.font.bodyLarge * BarScale.font
                color: Appearance.colors.colOnLayer0
            }
        }

        Revealer {
            reveal: !diIdleRoot.systemIconsElsewhere && VolumeService.sinkMuted
            MaterialSymbol {
                text: "volume_off"
                iconSize: NexusStyle.font.bodyLarge * BarScale.font
                color: Appearance.colors.colOnLayer0
            }
        }

        Revealer {
            reveal: !diIdleRoot.systemIconsElsewhere && !NetworkService.connected
            MaterialSymbol {
                text: "wifi_off"
                iconSize: NexusStyle.font.bodyLarge * BarScale.font
                color: Appearance.colors.colError
            }
        }
    }

    // Second segment: the clock (or weather satellite), optically centred in
    // the pill independent of the anchored side clusters.
    Loader {
        id: satelliteLoader

        anchors.centerIn: parent
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
                    iconSize: NexusStyle.font.bodyLarge * BarScale.font
                    color: Appearance.colors.colOnLayer0
                    Layout.alignment: Qt.AlignVCenter
                }

                StyledText {
                    font.pixelSize: di.isMaterial ? NexusStyle.font.bodyLarge * BarScale.font : NexusStyle.font.bodyMedium * BarScale.font
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
    readonly property real satelliteWidth: satelliteLoader.item ? satelliteLoader.item.implicitWidth : 0
    readonly property real computedIdleWidth: diIdleRoot.avatarBlockWidth + 10 + diIdleRoot.satelliteWidth + 10 + statusIconsRow.implicitWidth + 10

    onComputedIdleWidthChanged: di.idleTextContentWidth = diIdleRoot.computedIdleWidth
}
