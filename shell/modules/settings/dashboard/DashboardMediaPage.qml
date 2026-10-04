pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

// Dashboard "Media" page. Layout ported from end4-pC's DashboardMediaPage: a
// 46/54 split with album art, track info and transport controls on the left,
// and the scrolling lyrics on the right.
//
// The page takes its colours from `colors`, which DashboardContent supplies
// from the cover art while a track is playing (see DashboardMediaState). That
// is what makes the page look like the record instead of like the settings
// panel. `colors` follows the same shape as end4-pC's `mediaColors`: it is
// either the derived scheme or a plain Appearance.colors, and both expose the
// same names, so nothing below needs to branch. The fallback exists only so the
// page can be previewed standalone.
Item {
    id: root

    required property Item pager
    property int staggerMs: 45

    // Resolved palette: the cover-derived scheme, or the theme's own colours.
    property var colors: null
    readonly property var scheme: root.colors ?? Appearance.colors

    // The blurred album-art backdrop, handed to the cards so their tint is
    // sampled from the artwork rather than a flat colour.
    property Item blurSource: null

    readonly property var player: MediaService.active
    readonly property bool playing: root.player ? root.player.isPlaying : false
    readonly property bool hasShuffle: (root.player ? root.player.shuffleSupported ?? false : false) && (
                                           root.player ? root.player.canControl ?? false : false)
    readonly property bool hasLoop: (root.player ? root.player.loopSupported ?? false : false) && (
                                        root.player ? root.player.canControl ?? false : false)
    readonly property bool canSeek: root.player ? root.player.canSeek ?? false : false

    readonly property color fg: root.scheme.colOnLayer0
    readonly property color fgDim: root.scheme.colSubtext
    readonly property color hoverColor: root.scheme.colSecondaryContainerHover
    readonly property color activeColor: root.scheme.colSecondaryContainerActive

    property string shownTitle: ""
    property string shownArtist: ""
    readonly property string trackKey: (root.player ? root.player.trackTitle ?? "" : "") + "|" + (root.player
                                                                                                  ? root.player.trackArtist
                                                                                                    ?? "" : "")

    function seekBy(seconds) {
        if (!root.player || !root.canSeek)
            return;
        const length = root.player.length > 0 ? root.player.length : Number.MAX_VALUE;
        root.player.position = Math.max(0, Math.min(length, root.player.position + seconds));
    }

    function formatTime(seconds) {
        const total = Math.max(0, Math.floor(seconds || 0));
        const m = Math.floor(total / 60);
        const s = total % 60;
        return m + ":" + (s < 10 ? "0" : "") + s;
    }

    onTrackKeyChanged: trackSwap.restart()
    Component.onCompleted: {
        root.shownTitle = root.player ? root.player.trackTitle ?? "" : "";
        root.shownArtist = root.player ? root.player.trackArtist ?? "" : "";
    }

    SequentialAnimation {
        id: trackSwap

        ParallelAnimation {
            NumberAnimation {
                target: infoColumn
                property: "opacity"
                to: 0
                duration: 160
                easing.type: Easing.InQuad
            }
            NumberAnimation {
                target: infoShift
                property: "x"
                to: -40
                duration: 160
                easing.type: Easing.InQuad
            }
        }
        ScriptAction {
            script: {
                root.shownTitle = root.player ? root.player.trackTitle ?? "" : "";
                root.shownArtist = root.player ? root.player.trackArtist ?? "" : "";
                infoShift.x = 40;
            }
        }
        ParallelAnimation {
            NumberAnimation {
                target: infoColumn
                property: "opacity"
                to: 1
                duration: 260
                easing.type: Easing.OutQuad
            }
            NumberAnimation {
                target: infoShift
                property: "x"
                to: 0
                duration: 420
                easing.type: Easing.OutBack
            }
        }
    }

    SequentialAnimation {
        id: artPop

        ParallelAnimation {
            NumberAnimation {
                target: artImage
                property: "scale"
                to: 0.88
                duration: 140
                easing.type: Easing.InQuad
            }
            NumberAnimation {
                target: artImage
                property: "opacity"
                to: 0.2
                duration: 140
            }
        }
        ParallelAnimation {
            SpringAnimation {
                target: artImage
                property: "scale"
                to: 1
                spring: 3
                damping: 0.28
            }
            NumberAnimation {
                target: artImage
                property: "opacity"
                to: 1
                duration: 260
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 24

        ColumnLayout {
            Layout.fillHeight: true
            Layout.preferredWidth: root.width * 0.46
            Layout.maximumWidth: root.width * 0.46
            spacing: 12

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                DashboardCard {
                    id: artCard

                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    width: Math.min(parent.width, parent.height)
                    height: width
                    tint: root.scheme.colSecondaryContainer
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: 0
                    travelX: -320
                    travelY: 0

                    Image {
                        id: artImage

                        anchors.fill: parent
                        source: root.player ? root.player.trackArtUrl ?? "" : ""
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        cache: false
                        sourceSize: Qt.size(artCard.width * 2, artCard.height * 2)
                        onSourceChanged: artPop.restart()
                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: artCard.width
                                height: artCard.height
                                radius: artCard.cardRadius
                            }
                        }
                    }

                    MaterialSymbol {
                        anchors.centerIn: parent
                        visible: artImage.status !== Image.Ready
                        text: "music_note"
                        fill: 1
                        iconSize: 96
                        color: root.scheme.colPrimary
                    }
                }
            }

            DashboardCard {
                Layout.fillWidth: true
                Layout.preferredHeight: infoColumn.implicitHeight
                tint: "transparent"
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 1
                travelX: -300
                travelY: 100

                ColumnLayout {
                    id: infoColumn

                    anchors.left: parent.left
                    anchors.right: parent.right
                    spacing: 0
                    transform: Translate {
                        id: infoShift
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: root.shownTitle || I18n.tr("Nothing playing")
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 34
                        font.weight: Font.Bold
                        color: root.fg
                        elide: Text.ElideRight
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: root.shownArtist
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: Typography.titleLarge.pixelSize
                        color: root.fgDim
                        elide: Text.ElideRight
                    }
                }
            }

            DashboardCard {
                Layout.fillWidth: true
                Layout.preferredHeight: controlsLayout.implicitHeight + 28
                tint: root.scheme.colSecondaryContainer
                tintOpacity: 0.45
                // The transport bar sits on a blurred slice of the cover rather
                // than a flat fill, which is what ties it to the artwork behind
                // it. Same arrangement as end4-pC.
                blurSource: root.blurSource
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 2
                travelX: -200
                travelY: 260

                Rectangle {
                    anchors.fill: parent
                    radius: parent.cardRadius
                    color: Qt.rgba(0, 0, 0, 0.28)
                }

                ColumnLayout {
                    id: controlsLayout

                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        StyledText {
                            // Fixed slot for the elapsed time. Without it the
                            // label width tracks the text, so every tick that
                            // changed "0:59" to "1:00" resized the row and slid
                            // the slider out from under the cursor mid-drag.
                            Layout.preferredWidth: 44
                            horizontalAlignment: Text.AlignRight
                            text: root.formatTime(root.player ? root.player.position : 0)
                            font.pixelSize: Typography.bodySmall.pixelSize
                            color: root.fg
                        }

                        MaterialSplitSlider {
                            id: seekSlider

                            Layout.fillWidth: true
                            // 44px rather than the 78px default: what the transport
                            // row's height budget allows.
                            Layout.preferredHeight: 44
                            Layout.minimumHeight: 44
                            // Wavy is upstream's seek-bar configuration. The track
                            // is one line tall, which is what makes the row fit
                            // around it; the settings tiles keep the taller handle.
                            configuration: MaterialSplitSlider.Configuration.Wavy
                            enabled: root.canSeek
                            from: 0
                            to: 1
                            value: root.player && root.player.length > 0 ? (root.player.position ?? 0)
                                                                           / root.player.length : 0
                            highlightColor: root.scheme.colPrimary
                            trackColor: root.scheme.colSecondaryContainer
                            handleColor: root.scheme.colPrimary
                            // The slider tracks a 0..1 ratio, so the default
                            // indicator would read "0"/"1"; show the time the
                            // handle is sitting on instead.
                            usePercentTooltip: false
                            tooltipContent: root.formatTime(seekSlider.value * (root.player
                                                                                && root.player.length > 0
                                                                                ? root.player.length : 0))
                            // QtQuick's moved() carries no argument, unlike the
                            // MaterialSlider this replaced.
                            onMoved: {
                                if (root.player && root.canSeek)
                                    root.player.position = seekSlider.value * root.player.length;
                            }
                        }

                        StyledText {
                            Layout.preferredWidth: 44
                            horizontalAlignment: Text.AlignLeft
                            text: "-" + root.formatTime((root.player ? root.player.length ?? 0 : 0) - (
                                                            root.player ? root.player.position ?? 0 : 0))
                            font.pixelSize: Typography.bodySmall.pixelSize
                            color: root.fg
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        RippleButton {
                            implicitWidth: 40
                            implicitHeight: 40
                            buttonRadius: 20
                            toggled: root.hasShuffle && (root.player ? root.player.shuffle ?? false : false)
                            enabled: root.hasShuffle || root.canSeek
                            containerColor: "transparent"
                            rippleColor: root.fg
                            stateLayerColor: root.fg
                            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                            downAction: () => {
                                if (root.hasShuffle)
                                    root.player.shuffle = !root.player.shuffle;
                                else
                                    root.seekBy(-10);
                            }

                            contentItem: Item {
                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    text: root.hasShuffle ? "shuffle" : "replay_10"
                                    iconSize: 20
                                    color: root.fg
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        RippleButton {
                            implicitWidth: 48
                            implicitHeight: 48
                            buttonRadius: 24
                            containerColor: "transparent"
                            rippleColor: root.fg
                            stateLayerColor: root.fg
                            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                            downAction: () => {
                                if (root.player)
                                    root.player.previous();
                            }

                            contentItem: Item {
                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    text: "fast_rewind"
                                    iconSize: 26
                                    fill: 1
                                    color: root.fg
                                }
                            }
                        }

                        RippleButton {
                            implicitWidth: 64
                            implicitHeight: 64
                            buttonRadius: root.playing ? Appearance.rounding.large : 32
                            containerColor: root.scheme.colPrimary
                            rippleColor: root.scheme.colOnPrimary
                            stateLayerColor: root.scheme.colOnPrimary
                            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                            downAction: () => {
                                if (root.player)
                                    root.player.togglePlaying();
                            }

                            contentItem: Item {
                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    text: root.playing ? "pause" : "play_arrow"
                                    iconSize: 32
                                    fill: 1
                                    color: root.scheme.colOnPrimary
                                }
                            }
                        }

                        RippleButton {
                            implicitWidth: 48
                            implicitHeight: 48
                            buttonRadius: 24
                            containerColor: "transparent"
                            rippleColor: root.fg
                            stateLayerColor: root.fg
                            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                            downAction: () => {
                                if (root.player)
                                    root.player.next();
                            }

                            contentItem: Item {
                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    text: "fast_forward"
                                    iconSize: 26
                                    fill: 1
                                    color: root.fg
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        RippleButton {
                            implicitWidth: 40
                            implicitHeight: 40
                            buttonRadius: 20
                            toggled: root.hasLoop && (root.player ? root.player.loopState ?? 0 : 0) !== 0
                            enabled: root.hasLoop || root.canSeek
                            containerColor: "transparent"
                            rippleColor: root.fg
                            stateLayerColor: root.fg
                            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                            pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                            downAction: () => {
                                if (root.hasLoop)
                                    root.player.loopState = root.player.loopState === 0 ? 2 : 0;
                                else
                                    root.seekBy(10);
                            }

                            contentItem: Item {
                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    text: root.hasLoop ? "repeat" : "forward_10"
                                    iconSize: 20
                                    color: root.fg
                                }
                            }
                        }
                    }
                }
            }
        }

        // Lyrics fill the right column, which is what the 46/54 split exists
        // for: the left column is the record, this is what is being sung.
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            DashboardLyricsPane {
                anchors.fill: parent
                colors: root.colors
            }
        }
    }
}
