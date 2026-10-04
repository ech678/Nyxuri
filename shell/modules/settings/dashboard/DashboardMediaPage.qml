pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import qs.shared.theme
import qs.shared.controls
import qs.app.services

// Dashboard "Media" page. Layout ported from end4-pC's DashboardMediaPage: a
// 46/54 split with album art, track info and transport controls on the left.
//
// Not ported, because nyxuri has no counterpart:
//   - the cava wave visualiser (Cava is sealed in this tree).
//   - the lyrics pane that fills the right column (keystone/lyrics was deleted).
//   - the album-art derived palette that recolours the whole dashboard
//     (`DashboardMediaState` + ColorQuantizer + AdaptedMaterialScheme). nyxuri
//     derives colours from the wallpaper through matugen instead.
// The right column is kept so the split geometry still matches end4-pC.
Item {
    id: root

    required property Item pager
    property int staggerMs: 45

    readonly property var player: MediaService.active
    readonly property bool playing: root.player ? root.player.isPlaying : false
    readonly property bool hasShuffle: (root.player ? root.player.shuffleSupported ?? false : false) && (
                                           root.player ? root.player.canControl ?? false : false)
    readonly property bool hasLoop: (root.player ? root.player.loopSupported ?? false : false) && (
                                        root.player ? root.player.canControl ?? false : false)
    readonly property bool canSeek: root.player ? root.player.canSeek ?? false : false

    readonly property color fg: Appearance.colors.colOnLayer0
    readonly property color fgDim: Appearance.colors.colSubtext

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
                    tint: Appearance.colors.colSecondaryContainer
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
                        color: Appearance.colors.colPrimary
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
                        text: root.shownTitle || qsTr("Nothing playing")
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
                tint: Appearance.colors.colSecondaryContainer
                tintOpacity: 0.45
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
                            text: root.formatTime(root.player ? root.player.position : 0)
                            font.pixelSize: Typography.bodySmall.pixelSize
                            color: root.fg
                        }

                        MaterialSlider {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            enabled: root.canSeek
                            from: 0
                            to: 1
                            value: root.player && root.player.length > 0 ? (root.player.position ?? 0)
                                                                           / root.player.length : 0
                            accessibleName: qsTr("Seek")
                            // The slider tracks a 0..1 ratio, so the default indicator
                            // showed "0"/"1" instead of a position. Render it as time.
                            valueFormatter: sliderValue => root.formatTime(sliderValue * (root.player
                                                                                          && root.player.length
                                                                                          > 0 ? root.player.length :
                                                                                                0))
                            onMoved: value => {
                                if (root.player && root.canSeek)
                                    root.player.position = value * root.player.length;
                            }
                        }

                        StyledText {
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
                            containerColor: Appearance.colors.colPrimary
                            rippleColor: Appearance.colors.colOnPrimary
                            stateLayerColor: Appearance.colors.colOnPrimary
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
                                    color: Appearance.colors.colOnPrimary
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

        // ── 待接入：歌词栏 ──────────────────────────────────────────────
        // end4-pC 在这个位置放 `Lyrics` 组件（见其 DashboardMediaPage 右列：
        // fontScale 1.8、lineSpacing 28、居中对齐，当前行跟随播放进度高亮）。
        //
        // nyxuri 现状：keystone/lyrics 在 R4-C-02 被物理删除，仓库里已无歌词能力，
        // 因此这里只保留 46/54 分栏的几何，右列空置。
        //
        // 要补齐需要：
        //   1. 歌词来源。MPRIS 不提供歌词，需接一个 provider —— end4-pC 走 kugou
        //      抓取，另有 SPlayer WebSocket 与 songrec 音频指纹两种兜底。
        //   2. 一个 Lyrics 组件：逐行渲染 + 当前行高亮 + 随进度滚动。
        //   3. 数据注入：从 `MediaService.active` 取 trackTitle / trackArtist 匹配
        //      歌词，用 `MediaService.currentPosition` 驱动当前行。
        //   4. 若还要恢复封面取色重着色，需补上 end4-pC 的 DashboardMediaState
        //      （ColorQuantizer + AdaptedMaterialScheme）；nyxuri 目前走 matugen
        //      从壁纸取色。
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
