pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services
import "lyrics" as Lyrics
import "lyrics/LyricsParser.js" as LyricsParser
import qs.commons.i18n

// Lyric pane. The sweep follows dux-shell's LyricsVocal: the line is drawn
// twice — a base layer with every word in the body colour and an overlay that
// renders only the words already sung, tinted toward the accent by an alpha
// that advances with the audio. Rebuilding a rich-text string per frame (the
// earlier approach) allocates on every tick; two static layers plus one animated
// alpha does not.
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

    // dux's opacity ladder: the neighbours stay legible rather than fading to
    // near-invisible, which keeps the pane from reading as a single line.
    readonly property real nearOpacity: 0.55
    readonly property real farOpacity: 0.3
    readonly property real lineHeight: 1.25

    readonly property int radius: 3
    readonly property int slotCount: root.radius * 2 + 1

    readonly property var lines: lyricsService.lines
    readonly property int currentIndex: lyricsService.currentLineIndex
    readonly property bool ready: lyricsService.state === "ready" && lyricsService.hasLyrics
                                  && root.currentIndex >= 0

    readonly property real leadFontSize: Math.max(15, Math.min(34, Math.min(root.height / 12, root.width
                                                                            / 11)))

    function lineIndexFor(slot) {
        const index = root.currentIndex + (slot - root.radius);
        return index >= 0 && index < root.lines.length ? index : -1;
    }

    function lineAt(slot) {
        const index = root.lineIndexFor(slot);
        return index >= 0 ? root.lines[index] : null;
    }

    function distanceFor(slot) {
        return Math.abs(slot - root.radius);
    }

    function scaleFor(slot) {
        const d = root.distanceFor(slot);
        if (d === 0)
            return 1;
        if (d === 1)
            return 0.68;
        return 0.56;
    }

    function opacityFor(slot) {
        const d = root.distanceFor(slot);
        if (d === 0)
            return 1;
        if (d === 1)
            return root.nearOpacity;
        return root.farOpacity;
    }

    // Index of the word being sung, or -1 when the line has no word timings.
    readonly property int activeWordIndex: {
        if (!root.ready)
            return -1;
        const line = root.lines[root.currentIndex];
        return line ? LyricsParser.wordIndexAt(line, lyricsService.positionMs) : -1;
    }

    // Overlay text for the active line: sung words in the accent, everything
    // after them kept in the layout but drawn transparent. Omitting the tail
    // instead would let the overlay re-wrap from the line start and collide
    // with the base layer underneath.
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

    // Progress through the word currently being sung, 0..1. Drives the overlay's
    // alpha so the boundary moves with the audio between word starts.
    readonly property real wordProgress: {
        if (!root.ready || root.activeWordIndex < 0)
            return 0;
        const line = root.lines[root.currentIndex];
        if (!line || !line.words || line.words.length === 0)
            return 0;
        return LyricsParser.wordProgress(line.words[root.activeWordIndex], lyricsService.positionMs);
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

                readonly property var line: root.lineAt(slotRoot.index)
                readonly property bool active: root.distanceFor(slotRoot.index) === 0
                readonly property bool timed: slotRoot.active && slotRoot.line && slotRoot.line.words
                                              && slotRoot.line.words.length > 0
                readonly property string translation: slotRoot.line ? (slotRoot.line.translation ?? "") : ""

                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 2

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Item {
                            id: lineBox

                            readonly property real scaleValue: root.scaleFor(slotRoot.index)
                            readonly property real opacityValue: root.opacityFor(slotRoot.index)

                            anchors.centerIn: parent
                            width: parent.width
                            height: Math.ceil(baseLine.implicitHeight * lineBox.scaleValue)
                            scale: lineBox.scaleValue
                            transformOrigin: Item.Center
                            opacity: lineBox.opacityValue

                            Behavior on scale {
                                NumberAnimation {
                                    duration: 500
                                    easing.type: Easing.BezierSpline
                                    // M3 expressive default-spatial: overshoots,
                                    // which is what makes the lead line settle.
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

                                anchors.centerIn: parent
                                width: parent.width / Math.max(0.01, lineBox.scale)
                                text: slotRoot.line ? (slotRoot.line.text ?? "") : ""
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                maximumLineCount: 3
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: root.leadFontSize
                                font.weight: slotRoot.active ? Font.Bold : Font.Medium
                                color: root.textColor
                                lineHeight: root.lineHeight
                            }

                            // Sung overlay. Only the active timed line gets one;
                            // its alpha is the word progress, so the accent
                            // sweeps across rather than switching on per word.
                            StyledText {
                                anchors.fill: baseLine
                                visible: slotRoot.timed
                                textFormat: Text.RichText
                                text: slotRoot.timed ? root.sungText(slotRoot.line, root.activeWordIndex) : ""
                                wrapMode: baseLine.wrapMode
                                maximumLineCount: 3
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignHCenter
                                font: baseLine.font
                                lineHeight: baseLine.lineHeight
                                color: Qt.tint(root.textColor, Qt.rgba(root.accent.r, root.accent.g,
                                                                       root.accent.b, root.wordProgress))

                                Behavior on color {
                                    ColorAnimation {
                                        duration: 120
                                        easing.type: Easing.Linear
                                    }
                                }
                            }
                        }
                    }

                    // Translation under the active line only; translated
                    // neighbours would compete with the lyric for attention.
                    StyledText {
                        Layout.fillWidth: true
                        visible: slotRoot.active && slotRoot.translation !== ""
                        text: slotRoot.translation
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
