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
//
// D4g batch three: the rail face stacks the same three segments along the
// rail (avatar top, satellite middle, status icons bottom) inside the
// pill grown along the track — dux HomeCompact's compactColumn lineage.
// Positions are explicit x/y on both axes (conditional anchors are
// forbidden — the flip must not leave stale anchors behind).

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
        di.idleRailContentLength = diIdleRoot.computedRailLength;
    }
    Component.onDestruction: {
        if (weatherLeaseId !== "")
            WeatherService.release(weatherLeaseId);
    }
    anchors.fill: parent

    readonly property bool railFace: di.vertical
    readonly property bool systemIconsElsewhere: di.widgetBar ? ["left", "middle", "right"].some(z => (di.widgetBar.lanes?.[z] ?? []).some(e => e.enabled !== false && e.widgetId === "systemIcons")) : (PersonalizationConfig.barLayoutLeft.includes("systemIcons") || PersonalizationConfig.barLayoutRight.includes("systemIcons"))
    readonly property bool showAvatar: di && typeof di.option === "function" ? di.option("showAvatar") : true
    readonly property string satellite: di && typeof di.option === "function" ? di.option("satellite") : "clock"

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

    // First segment: the avatar. Left-anchored on the row, top-centred on
    // the rail.
    Rectangle {
        id: avatarRect
        width: di.isMaterial ? di.pillHeight : di.pillHeight - 8
        height: width
        visible: diIdleRoot.showAvatar
        x: diIdleRoot.railFace ? (parent.width - width) / 2 : (di.isMaterial ? 0 : 4)
        y: diIdleRoot.railFace ? 6 : (parent.height - height) / 2
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
            iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(di.widgetBar)
            color: Appearance.colors.colOnPrimaryContainer
        }
    }

    // Third segment: status icons. Right-anchored row on the bar, centred
    // column at the rail face's tail. They only repeat the SystemIcons
    // group when that group is not on any bar lane.
    component MicRevealer: Revealer {
        reveal: !diIdleRoot.systemIconsElsewhere && VolumeService.sourceMuted
        MaterialSymbol {
            text: "mic_off"
            iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(di.widgetBar)
            color: Appearance.colors.colOnLayer0
        }
    }

    component SinkRevealer: Revealer {
        reveal: !diIdleRoot.systemIconsElsewhere && VolumeService.sinkMuted
        MaterialSymbol {
            text: "volume_off"
            iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(di.widgetBar)
            color: Appearance.colors.colOnLayer0
        }
    }

    component NetRevealer: Revealer {
        reveal: !diIdleRoot.systemIconsElsewhere && !NetworkService.connected
        MaterialSymbol {
            text: "wifi_off"
            iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(di.widgetBar)
            color: Appearance.colors.colError
        }
    }

    RowLayout {
        id: statusIconsRow
        visible: !diIdleRoot.railFace
        anchors {
            right: parent.right
            rightMargin: 10
            verticalCenter: parent.verticalCenter
        }
        spacing: 4

        MicRevealer {}

        SinkRevealer {}

        NetRevealer {}
    }

    ColumnLayout {
        id: statusIconsColumn
        visible: diIdleRoot.railFace
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: 10
        }
        spacing: 4

        MicRevealer {}

        SinkRevealer {}

        NetRevealer {}
    }

    // Second segment: the clock (or weather satellite), optically centred
    // in the pill on the bar and centred under the avatar on the rail.
    Loader {
        id: satelliteLoader

        x: (parent.width - width) / 2
        y: diIdleRoot.railFace ? (diIdleRoot.showAvatar ? avatarRect.y + avatarRect.height + 8 : 8) : (parent.height - height) / 2
        sourceComponent: diIdleRoot.satellite === "clock" ? clockComponent : diIdleRoot.satellite === "weather" ? (diIdleRoot.railFace ? weatherComponent : weatherRowComponent) : null

        Component {
            id: clockComponent
            ClockContent {
                // The ClockContent vertical stack keys off the edge; the
                // owning bar's position is the single truth.
                edge: di.barAxes.position
            }
        }

        Component {
            id: weatherComponent
            ColumnLayout {
                spacing: 2

                MaterialSymbol {
                    fill: 0
                    text: WeatherService.hasValidData ? WeatherService.currentIconName : "cloud"
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(di.widgetBar)
                    color: Appearance.colors.colOnLayer0
                    Layout.alignment: Qt.AlignHCenter
                }

                StyledText {
                    font.pixelSize: (di.isMaterial ? NexusStyle.font.bodyLarge : NexusStyle.font.bodyMedium) * BarScale.fontFor(di.widgetBar)
                    font.features: {
                        "tnum": 1
                    }
                    color: Appearance.colors.colOnLayer0
                    text: WeatherService.hasValidData ? (Math.round(WeatherService.currentTemperatureC) + "°") : "--°"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Row twin of the weather satellite for the horizontal face.
        Component {
            id: weatherRowComponent
            RowLayout {
                spacing: 4

                MaterialSymbol {
                    fill: 0
                    text: WeatherService.hasValidData ? WeatherService.currentIconName : "cloud"
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(di.widgetBar)
                    color: Appearance.colors.colOnLayer0
                    Layout.alignment: Qt.AlignVCenter
                }

                StyledText {
                    font.pixelSize: (di.isMaterial ? NexusStyle.font.bodyLarge : NexusStyle.font.bodyMedium) * BarScale.fontFor(di.widgetBar)
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

    readonly property real avatarBlockHeight: diIdleRoot.showAvatar ? avatarRect.y + avatarRect.height + 8 : 8
    readonly property real avatarBlockWidth: diIdleRoot.showAvatar ? avatarRect.width + (di.isMaterial ? 0 : 4) : 0
    readonly property real satelliteWidth: satelliteLoader.item ? satelliteLoader.item.implicitWidth : 0
    readonly property real computedIdleWidth: diIdleRoot.avatarBlockWidth + 10 + diIdleRoot.satelliteWidth + 10 + statusIconsRow.implicitWidth + 10
    readonly property real computedRailLength: {
        if (!diIdleRoot.railFace)
            return 0;
        const head = diIdleRoot.avatarBlockHeight;
        const satelliteHeight = satelliteLoader.item ? satelliteLoader.item.implicitHeight : 0;
        const tail = statusIconsColumn.visible ? statusIconsColumn.implicitHeight + 10 : 0;
        return head + satelliteHeight + tail + 8;
    }

    onComputedIdleWidthChanged: di.idleTextContentWidth = diIdleRoot.computedIdleWidth
    onComputedRailLengthChanged: di.idleRailContentLength = diIdleRoot.computedRailLength
}
