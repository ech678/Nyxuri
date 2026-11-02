pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services
import "lyrics" as Lyrics
import "lyrics/LyricsParser.js" as LyricsParser
import qs.commons.i18n

// Lyric transcript. Follows dux-shell's LyricsOverlay: the whole song is a
// scrolling ListView with a third-of-viewport header and footer so the first
// and last lines can still reach the centre, rather than a fixed window of
// seven rows. Rows scale and dim by distance from the active line, and clicking
// one seeks there.
Item {
    id: root

    Lyrics.LyricsService {
        id: lyricsService
        active: root.visible
    }

    property var colors: null
    readonly property var scheme: root.colors ?? Appearance.colors

    readonly property color accent: root.scheme.colPrimary
    readonly property color textColor: root.scheme.colOnLayer0
    readonly property color dimColor: root.scheme.colSubtext

    readonly property real nearOpacity: 0.55
    readonly property real farOpacity: 0.3
    readonly property real lineHeight: 1.25

    readonly property var lines: lyricsService.lines
    readonly property int currentIndex: lyricsService.currentLineIndex
    readonly property bool ready: lyricsService.state === "ready" && lyricsService.hasLyrics

    // Distance to the active line drives both scale and dimming. Unbounded
    // rather than clamped to a window, because the list shows the whole song.
    function distanceFor(index) {
        return root.currentIndex < 0 ? 99 : Math.abs(index - root.currentIndex);
    }

    function scaleFor(index) {
        const d = root.distanceFor(index);
        if (d === 0)
            return 1;
        if (d === 1)
            return 0.68;
        return 0.56;
    }

    function opacityFor(index) {
        const d = root.distanceFor(index);
        if (d === 0)
            return 1;
        if (d === 1)
            return root.nearOpacity;
        return root.farOpacity;
    }

    readonly property real leadFontSize: Math.round(Math.max(15, Math.min(36, Math.min(root.height / 12,
                                                                                       root.width / 11))))

    readonly property int activeWordIndex: {
        if (!root.ready || root.currentIndex < 0)
            return -1;
        const line = root.lines[root.currentIndex];
        return line ? LyricsParser.wordIndexAt(line, lyricsService.positionMs) : -1;
    }

    // Overlay text for the active line: sung words in the accent, the rest kept
    // in the layout but transparent. Omitting the tail would let the overlay
    // re-wrap from the line start and collide with the base layer.
    function sungText(line, uptoWord) {
        if (!line || !line.words || line.words.length === 0)
            return "";
        let html = "";
        for (let i = 0; i < line.words.length; i++) {
            const word = line.words[i];
            const text = String(word.text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            html += i <= uptoWord ? '<font color="' + String(root.accent) + '">' + text + "</font>" :
                                    '<font color="transparent">' + text + "</font>";
        }
        return html;
    }

    readonly property real wordProgress: {
        if (!root.ready || root.activeWordIndex < 0)
            return 0;
        const line = root.lines[root.currentIndex];
        if (!line || !line.words || line.words.length === 0)
            return 0;
        return LyricsParser.wordProgress(line.words[root.activeWordIndex], lyricsService.positionMs);
    }

    // Follow the active line while playing. `following` turns off as soon as the
    // reader scrolls, so the list does not yank itself back mid-read.
    property bool following: true

    function scrollToCurrent() {
        if (root.currentIndex >= 0)
            transcript.positionViewAtIndex(root.currentIndex, ListView.Center);
    }

    onCurrentIndexChanged: {
        if (root.following)
            root.scrollToCurrent();
    }

    onReadyChanged: {
        if (root.ready)
            Qt.callLater(() => root.scrollToCurrent());
    }

    Component.onCompleted: {
        if (root.ready)
            Qt.callLater(() => root.scrollToCurrent());
    }

    ListView {
        id: transcript

        anchors.fill: parent
        clip: true
        visible: root.ready
        model: root.lines
        spacing: 4
        reuseItems: true
        boundsBehavior: Flickable.StopAtBounds
        // A third of the viewport at each end lets the first and last lines
        // reach the centre instead of stopping at the edge.
        header: Item {
            width: transcript.width
            height: transcript.height / 3
        }
        footer: Item {
            width: transcript.width
            height: transcript.height / 3
        }

        onMovementEnded: root.following = false
        onDraggingChanged: {
            if (transcript.dragging)
                root.following = false;
        }

        delegate: Item {
            id: lyricRow

            required property int index
            required property var modelData

            width: transcript.width
            height: column.implicitHeight + 10

            readonly property bool active: index === root.currentIndex
            readonly property bool timed: root.ready && root.lines[index] && root.lines[index].words
                                          && root.lines[index].words.length > 0
            readonly property string translation: modelData ? (modelData.translation ?? "") : ""

            Column {
                id: column

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Item {
                    id: textSlot

                    width: parent.width
                    height: baseLine.implicitHeight
                    scale: root.scaleFor(lyricRow.index)
                    opacity: root.opacityFor(lyricRow.index)
                    transformOrigin: Item.Center

                    Behavior on scale {
                        NumberAnimation {
                            duration: 500
                            easing.type: Easing.BezierSpline
                            // M3 expressive default-spatial: overshoots, which
                            // is what makes the lead line settle into place.
                            easing.bezierCurve: [0.38, 1.21, 0.22, 1, 1, 1]
                        }
                    }

                    Behavior on opacity {
                        NumberAnimation {
                            duration: 200
                            easing.type: Easing.BezierSpline
                            easing.bezierCurve: [0.34, 0.8, 0.34, 1, 1, 1]
                        }
                    }

                    StyledText {
                        id: baseLine

                        anchors.left: parent.left
                        anchors.right: parent.right
                        text: lyricRow.modelData ? (lyricRow.modelData.text ?? "") : ""
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        maximumLineCount: 3
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: root.leadFontSize
                        font.weight: lyricRow.active ? Font.Bold : Font.Medium
                        color: root.textColor
                        lineHeight: root.lineHeight
                    }

                    StyledText {
                        anchors.fill: baseLine
                        visible: lyricRow.timed
                        textFormat: Text.RichText
                        text: lyricRow.timed ? root.sungText(lyricRow.modelData, root.activeWordIndex) : ""
                        wrapMode: baseLine.wrapMode
                        maximumLineCount: 3
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        font: baseLine.font
                        lineHeight: baseLine.lineHeight
                        color: Qt.tint(root.textColor, Qt.rgba(root.accent.r, root.accent.g, root.accent.b,
                                                               root.wordProgress))

                        Behavior on color {
                            ColorAnimation {
                                duration: 120
                                easing.type: Easing.Linear
                            }
                        }
                    }
                }

                StyledText {
                    width: parent.width
                    visible: lyricRow.active && lyricRow.translation !== ""
                    text: lyricRow.translation
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: Math.max(11, root.leadFontSize * 0.5)
                    font.weight: Font.Medium
                    color: root.dimColor
                    opacity: 0.8
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                enabled: root.ready
                onClicked: {
                    const line = root.lines[lyricRow.index];
                    if (!line)
                        return;
                    root.following = true;
                    const player = MediaService.active;
                    if (player && player.position !== undefined)
                        player.position = line.startMs / 1000;
                }
            }
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.8, 320)
        spacing: 12
        visible: !root.ready

        MaterialShapeWrappedMaterialSymbol {
            Layout.alignment: Qt.AlignHCenter
            wrappedShape: MaterialShapeCanvas.Shape.Clover4Leaf
            text: "lyrics"
            iconSize: 30
            fill: lyricsService.hasLyrics ? 1 : 0
            padding: 14
            color: root.accent
            colSymbol: root.scheme.colOnPrimary
        }

        StyledText {
            Layout.fillWidth: true
            text: root.statusText()
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: root.dimColor
            opacity: 0.85
        }
    }

    function statusText() {
        switch (lyricsService.state) {
        case "loading":
            return I18n.tr("Loading lyrics…");
        case "empty":
            return I18n.tr("No lyrics found");
        case "error":
            return lyricsService.errorMessage || I18n.tr("Lyrics unavailable");
        default:
            return lyricsService.title !== "" ? I18n.tr("Waiting for playback") : I18n.tr("Nothing playing");
        }
    }
}
