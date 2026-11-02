pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services
import "lyrics" as Lyrics
import "lyrics/LyricsParser.js" as LyricsParser
import qs.commons.i18n

// Lyric pane: word-level sweep for KRC, translated sub-line, and a scrolling
// window of neighbours. The parser and service are the ones already in
// lyrics/; this file owns only presentation.
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

    readonly property int radius: 3
    readonly property int slotCount: root.radius * 2 + 1

    readonly property var lines: lyricsService.lines
    readonly property int currentIndex: lyricsService.currentLineIndex
    readonly property bool ready: lyricsService.state === "ready" && lyricsService.hasLyrics
                                  && root.currentIndex >= 0

    readonly property real baseFontSize: Math.max(14, Math.min(22, root.height * 0.055))

    function lineIndexFor(slot) {
        const index = root.currentIndex + (slot - root.radius);
        return index >= 0 && index < root.lines.length ? index : -1;
    }

    function lineText(slot) {
        const index = root.lineIndexFor(slot);
        return index >= 0 ? root.lines[index].text : "";
    }

    function lineTranslation(slot) {
        const index = root.lineIndexFor(slot);
        return index >= 0 ? (root.lines[index].translation ?? "") : "";
    }

    function distanceFor(slot) {
        return Math.abs(slot - root.radius);
    }

    function fontSizeFor(slot) {
        const distance = root.distanceFor(slot);
        if (distance === 0)
            return root.baseFontSize * 1.5;
        if (distance === 1)
            return root.baseFontSize * 1.05;
        if (distance === 2)
            return root.baseFontSize * 0.92;
        return root.baseFontSize * 0.82;
    }

    function opacityFor(slot) {
        const distance = root.distanceFor(slot);
        if (distance === 0)
            return 1;
        if (distance === 1)
            return 0.62;
        if (distance === 2)
            return 0.36;
        return 0.16;
    }

    // Word-level rich text for the active line. Sung words take the accent,
    // unsung stay in the body colour, and the word currently being sung is a
    // blend of the two so the highlight sweeps rather than snapping.
    readonly property string richLine: {
        if (!root.ready)
            return "";
        const line = root.lines[root.currentIndex];
        if (!line || !line.words || line.words.length === 0)
            return "";
        const accentHex = String(root.accent);
        const baseHex = String(root.textColor);
        const position = lyricsService.positionMs;
        let html = "";
        for (let i = 0; i < line.words.length; i++) {
            const word = line.words[i];
            const text = String(word.text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const progress = LyricsParser.wordProgress(word, position);
            if (progress >= 1)
                html += '<font color="' + accentHex + '">' + text + "</font>";
            else if (progress <= 0)
                html += text;
            else
                html += '<font color="' + LyricsParser.blendHex(baseHex, accentHex, progress) + '">' + text
                        + "</font>";
        }
        return html;
    }

    // Fraction of the active line already sung, for the progress hairline.
    readonly property real lineProgress: {
        if (!root.ready)
            return 0;
        const line = root.lines[root.currentIndex];
        if (!line)
            return 0;
        const span = line.endMs - line.startMs;
        if (span <= 0)
            return 0;
        const ratio = (lyricsService.positionMs - line.startMs) / span;
        return Math.max(0, Math.min(1, ratio));
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 4
        visible: root.ready

        Repeater {
            model: root.slotCount

            delegate: Item {
                id: slotRoot

                required property int index

                readonly property real distance: root.distanceFor(slotRoot.index)
                readonly property bool active: slotRoot.distance === 0
                readonly property string translation: root.lineTranslation(slotRoot.index)

                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 2

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Text {
                            anchors.fill: parent
                            visible: slotRoot.active && root.richLine !== ""
                            textFormat: Text.RichText
                            text: slotRoot.active ? root.richLine : ""
                            wrapMode: Text.WordWrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.family: Fonts.ui
                            font.pixelSize: root.fontSizeFor(slotRoot.index)
                            font.weight: Font.Bold
                            color: root.textColor
                            opacity: root.opacityFor(slotRoot.index)
                        }

                        StyledText {
                            anchors.fill: parent
                            visible: !(slotRoot.active && root.richLine !== "")
                            text: root.lineText(slotRoot.index)
                            wrapMode: Text.WordWrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: root.fontSizeFor(slotRoot.index)
                            font.weight: slotRoot.active ? Font.Bold : Font.Medium
                            color: slotRoot.active ? root.accent : root.textColor
                            opacity: root.opacityFor(slotRoot.index)

                            Behavior on font.pixelSize {
                                NumberAnimation {
                                    duration: 300
                                    easing.type: Easing.OutCubic
                                }
                            }

                            Behavior on opacity {
                                NumberAnimation {
                                    duration: 250
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }

                        Behavior on opacity {
                            NumberAnimation {
                                duration: 250
                                easing.type: Easing.OutCubic
                            }
                        }
                    }

                    // Translation sits under the active line only; a wall of
                    // translated neighbours would fight the lyric for attention.
                    StyledText {
                        Layout.fillWidth: true
                        visible: slotRoot.active && slotRoot.translation !== ""
                        text: slotRoot.translation
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: Math.max(11, root.baseFontSize * 0.72)
                        font.weight: Font.Medium
                        color: root.dimColor
                        opacity: 0.85
                    }
                }
            }
        }
    }

    // Hairline progress for the active line, pinned to the bottom of the pane.
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 2
        visible: root.ready
        color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18)

        Rectangle {
            width: parent.width * root.lineProgress
            height: parent.height
            radius: 1
            color: root.accent

            Behavior on width {
                NumberAnimation {
                    duration: 120
                    easing.type: Easing.Linear
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
