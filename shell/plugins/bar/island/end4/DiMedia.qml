// Fork & Trim: end4-pC modules/ii/bar/DiMedia.qml (GPL-3, see shell/LICENSE
// appendix end-4-dots-hyprland-GPL-3.0.txt). Trimmed per the B volume four
// classes: MprisController -> MediaService, Config.options -> keys, cava feed
// comes from IslandVisualizerService (tree-side lazy consumer) instead of the
// upstream GlobalStates singleton.
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell
import Quickshell.Services.Mpris
import qs.services
import qs.commons
import qs.ui

Item {
    id: root
    required property Item di
    anchors.fill: parent

    // Upstream read these straight off Config.options.bar.dynamicIsland. The
    // tree keeps the user's existing progress-style key and maps it: "wave"
    // draws the cava sine canvas, anything else draws the dots visualizer.
    readonly property string islandVisualizerStyle: PersonalizationConfig.islandMediaProgressStyle === "wave" ? "wave" : "dots"
    // end4 collapses the controls into the visualizer when showMediaControls
    // is off. The tree shows controls (they are the only transport affordance
    // inside the capsule) and lets the visualizer pick the remaining slot.
    readonly property bool showMediaControls: root.islandVisualizerStyle !== "dots"
    readonly property var activePlayer: di.activePlayer

    // cava is a lease, not a tenant: the island only pays for it while the
    // media face is actually on screen and the track is playing.
    readonly property bool waveWanted: root.visible && root.islandVisualizerStyle === "wave" && (root.activePlayer?.isPlaying ?? false)
    onWaveWantedChanged: root.waveWanted ? IslandVisualizerService.acquire() : IslandVisualizerService.release()
    Component.onDestruction: if (root.waveWanted)
        IslandVisualizerService.release()

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
            radius: di.isMaterial ? Appearance.rounding.full : Appearance.rounding.small
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

            Image {
                anchors.fill: parent
                asynchronous: true
                fillMode: Image.PreserveAspectCrop
                source: root.activePlayer?.trackArtUrl ?? ""
                sourceSize.width: artMask.width * 2
                sourceSize.height: artMask.height * 2
                visible: (root.activePlayer?.trackArtUrl ?? "") !== ""
            }

            MaterialSymbol {
                anchors.centerIn: parent
                text: "music_note"
                iconSize: 14
                color: Appearance.colors.colOnLayer1
                visible: (root.activePlayer?.trackArtUrl ?? "") === ""
            }
        }

        StyledText {
            id: trackTitleMetrics
            visible: false
            text: root.activePlayer?.trackTitle ?? ""
            font.pixelSize: Appearance.font.pixelSize.smaller
            font.weight: Font.DemiBold
        }
        StyledText {
            id: trackArtistMetrics
            visible: false
            text: root.activePlayer?.trackArtist ?? ""
            font.pixelSize: Appearance.font.pixelSize.smallest
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
                text: root.activePlayer?.trackTitle ?? ""
                font.pixelSize: Appearance.font.pixelSize.smaller
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnLayer0
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
                maximumLineCount: 1
            }
            StyledText {
                Layout.fillWidth: true
                text: root.activePlayer?.trackArtist ?? ""
                font.pixelSize: Appearance.font.pixelSize.smallest
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
            live: root.activePlayer?.isPlaying
            points: IslandVisualizerService.points
            maxVisualizerValue: 1000
            smoothing: 2
            color: Appearance.colors.colOnLayer0
            visible: root.islandVisualizerStyle === "wave"
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
            points: IslandVisualizerService.points
            visible: !root.showMediaControls && root.islandVisualizerStyle === "dots"
        }

        RowLayout {
            id: mediaControlsRow
            anchors {
                right: parent.right
                rightMargin: di.isMaterial ? 4 : 8
                verticalCenter: parent.verticalCenter
            }
            spacing: di.isMaterial ? -2 : -4
            visible: root.showMediaControls

            Item {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: 20
                implicitHeight: 20
                visible: root.activePlayer?.canGoPrevious ?? false

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
                    onClicked: root.activePlayer?.previous()
                }
            }

            Item {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: 22
                implicitHeight: 22

                MaterialSymbol {
                    anchors.centerIn: parent
                    text: root.activePlayer?.isPlaying ? "pause" : "play_arrow"
                    fill: 1
                    iconSize: di.isMaterial ? 20 : 18
                    color: Appearance.colors.colOnLayer0
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.activePlayer?.togglePlaying()
                }
            }

            Item {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: 20
                implicitHeight: 20
                visible: root.activePlayer?.canGoNext ?? false

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
                    onClicked: root.activePlayer?.next()
                }
            }
        }
    }
}
