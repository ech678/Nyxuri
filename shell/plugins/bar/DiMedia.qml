// Fork & Trim: end4-pC modules/ii/bar/DiMedia.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// B-10 (2026-11-21): the end4 control set is unfrozen — `showMediaControls`
// (three playback buttons) and `visualizerStyle` dots/wave/none. cava stays
// an on-demand consumer: the wave canvas holds its CavaProcess lease only
// while the wave is the chosen style and a track is playing; the dots
// visualizer leases its own inside Visualizer.qml under the same rule. Both
// feed from the one shared IslandVisualizerService process.

import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell
import Quickshell.Services.Mpris
import qs.services
import qs.commons
import qs.ui

Item {
    id: diMediaRoot
    required property Item di
    anchors.fill: parent

    readonly property bool showMediaControls: di && typeof di.option === "function" ? di.option("showMediaControls") : false
    readonly property string visualizerStyle: di && typeof di.option === "function" ? di.option("visualizerStyle") : "dots"

    // Probe surface (scripts/dev/probe-bar.sh): the B-10 control matrix
    // (controls x visualizer style) and the cava lease, read at runtime.
    readonly property bool probeMediaFace: true
    readonly property bool probeControlsVisible: mediaControlsRow.visible
    readonly property bool probeWaveVisible: visualizerCanvas.visible
    readonly property bool probeDotsVisible: islandVisualizer.visible
    readonly property bool probeWaveCavaActive: mediaFaceCava.active

    Rectangle {
        id: mediaMask
        anchors.fill: parent
        color: "transparent"
        radius: height / 2

        layer.enabled: true
        layer.effect: OpacityMask {
            maskSource: Rectangle {
                width: mediaMask.width
                height: mediaMask.height
                radius: mediaMask.radius
            }
        }

        Rectangle {
            id: artMask
            width: di.isMaterial ? di.pillHeight : di.pillHeight - 8
            height: di.isMaterial ? di.pillHeight : di.pillHeight - 8
            anchors {
                left: parent.left
                leftMargin: di.isMaterial ? 0 : 4
                verticalCenter: parent.verticalCenter
            }
            radius: di.isMaterial ? Appearance.rounding?.full : Appearance.rounding?.small ?? 8
            color: Appearance.colors.colLayer1
            clip: true

            layer.enabled: true
            layer.effect: OpacityMask {
                maskSource: Rectangle {
                    width: artMask.width
                    height: artMask.height
                    radius: artMask.radius
                }
            }

            StyledImage {
                anchors.fill: parent
                fillMode: Image.PreserveAspectCrop
                source: di.activePlayer?.trackArtUrl ?? ""
                sourceSize.width: artMask.width * 2
                sourceSize.height: artMask.height * 2
                visible: (di.activePlayer?.trackArtUrl ?? "") !== ""
            }

            MaterialSymbol {
                anchors.centerIn: parent
                text: "music_note"
                iconSize: 14
                color: Appearance.colors.colOnLayer1
                visible: (di.activePlayer?.trackArtUrl ?? "") === ""
            }
        }

        StyledText {
            id: trackTitleMetrics
            visible: false
            text: di.activePlayer?.trackTitle ?? ""
            font.pixelSize: NexusStyle.font.bodySmall * BarScale.fontFor(di.widgetBar)
            font.weight: Font.DemiBold
        }
        StyledText {
            id: trackArtistMetrics
            visible: false
            text: di.activePlayer?.trackArtist ?? ""
            font.pixelSize: NexusStyle.font.labelSmall * BarScale.fontFor(di.widgetBar)
        }

        ColumnLayout {
            id: trackInfoColumn
            anchors {
                left: artMask.right
                leftMargin: 8
                verticalCenter: parent.verticalCenter
                right: mediaControlsRow.visible ? mediaControlsRow.left : (visualizerCanvas.visible ? visualizerCanvas.left : (islandVisualizer.visible ? islandVisualizer.left : parent.right))
                rightMargin: 8
            }
            spacing: di.isMaterial ? -2 : -4
            opacity: di.mediaTrackInfoVisible ? 1 : 0

            Behavior on opacity {
                NumberAnimation {
                    duration: 200
                    easing.type: Easing.OutCubic
                }
            }

            StyledText {
                Layout.fillWidth: true
                text: di.activePlayer?.trackTitle ?? ""
                font.pixelSize: NexusStyle.font.bodySmall * BarScale.fontFor(di.widgetBar)
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnLayer0
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
                maximumLineCount: 1
            }
            StyledText {
                Layout.fillWidth: true
                text: di.activePlayer?.trackArtist ?? ""
                font.pixelSize: NexusStyle.font.labelSmall * BarScale.fontFor(di.widgetBar)
                color: Appearance.colors.colOnLayer0
                opacity: 0.7
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
                maximumLineCount: 1
            }

            readonly property real widestLineWidth: Math.max(trackTitleMetrics.implicitWidth, trackArtistMetrics.implicitWidth)

            readonly property real computedContentWidth: artMask.width + (di.isMaterial ? 14 : 8) + trackInfoColumn.widestLineWidth + 12 + (mediaControlsRow.visible ? mediaControlsRow.implicitWidth : (visualizerCanvas.visible ? visualizerCanvas.width : (islandVisualizer.visible ? islandVisualizer.width : 0))) + (di.isMaterial ? 0 : 4) + 10

            onComputedContentWidthChanged: di.mediaTextContentWidth = trackInfoColumn.computedContentWidth
            Component.onCompleted: di.mediaTextContentWidth = trackInfoColumn.computedContentWidth
        }

        WaveVisualizer {
            id: visualizerCanvas
            anchors {
                right: mediaControlsRow.visible ? mediaControlsRow.left : parent.right
                rightMargin: mediaControlsRow.visible ? 6 : 10
                verticalCenter: parent.verticalCenter
            }
            width: di.isMaterial ? 60 : 50
            height: di.isMaterial ? di.pillHeight * 1.5 : di.pillHeight * 0.85
            live: mediaFaceCava.audioSignalActive
            points: mediaFaceCava.points
            maxVisualizerValue: mediaFaceCava.normalizationCeiling
            smoothing: 2
            color: Appearance.colors.colOnLayer0
            visible: diMediaRoot.visualizerStyle === "wave"
        }

        // Lease the shared cava process only while the wave is the chosen
        // style and something is actually playing.
        CavaProcess {
            id: mediaFaceCava
            active: visualizerCanvas.visible && (di.activePlayer?.isPlaying ?? false)
            Component.onDestruction: {
                mediaFaceCava.active = false;
            }
        }

        Visualizer {
            id: islandVisualizer
            anchors {
                right: parent.right
                rightMargin: 10
                verticalCenter: parent.verticalCenter
            }
            height: di.isMaterial ? di.pillHeight * 1.5 : di.pillHeight * 0.85
            vertical: false
            isMaterial: false
            barCount: 5
            dotSize: 3
            dotSpacing: 3
            maxBarHeight: di.isMaterial ? di.pillHeight * 1.5 : di.pillHeight * 0.85
            barColor: Appearance.colors.colOnLayer0
            // end4 baseline: dots yield to the playback buttons when those
            // are enabled; "none" shows no spectrum at all. Opacity fades with
            // the audio signal, so the cava lease inside still gates on
            // isPlaying.
            visible: !diMediaRoot.showMediaControls && diMediaRoot.visualizerStyle === "dots"
        }

        RowLayout {
            id: mediaControlsRow
            anchors {
                right: parent.right
                rightMargin: di.isMaterial ? 4 : 8
                verticalCenter: parent.verticalCenter
            }
            spacing: di.isMaterial ? -2 : -4
            visible: diMediaRoot.showMediaControls

            Item {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: 20
                implicitHeight: 20
                visible: di.activePlayer?.canGoPrevious ?? false

                MaterialSymbol {
                    anchors.centerIn: parent
                    text: "skip_previous"
                    fill: 1
                    iconSize: di.isMaterial ? 20 : 16
                    color: Appearance.colors.colOnLayer0
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: di.activePlayer?.previous()
                }
            }

            Item {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: 22
                implicitHeight: 22

                MaterialSymbol {
                    anchors.centerIn: parent
                    text: di.activePlayer?.isPlaying ? "pause" : "play_arrow"
                    fill: 1
                    iconSize: di.isMaterial ? 20 : 18
                    color: Appearance.colors.colOnLayer0
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: di.activePlayer?.togglePlaying()
                }
            }

            Item {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: 20
                implicitHeight: 20
                visible: di.activePlayer?.canGoNext ?? false

                MaterialSymbol {
                    anchors.centerIn: parent
                    text: "skip_next"
                    fill: 1
                    iconSize: di.isMaterial ? 20 : 16
                    color: Appearance.colors.colOnLayer0
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: di.activePlayer?.next()
                }
            }
        }
    }
}
