pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import "lyrics" as Lyrics
import "lyrics/LyricsParser.js" as LyricsParser
import qs.shared.i18n

Item {
    id: root

    Lyrics.LyricsService {
        id: lyricsService
        active: root.visible
    }

    // Cover-derived palette, or null to use the theme. Same contract as
    // DashboardMediaPage: both expose the same colour names.
    property var colors: null
    readonly property var scheme: root.colors ?? Appearance.colors

    readonly property color accent: root.scheme.colPrimary
    readonly property color textColor: root.scheme.colOnLayer0
    readonly property color dimColor: root.scheme.colSubtext

    // Half the window. Seven slots total (three either side of the active one),
    // which is what fits at the sizes below without the outermost lines landing
    // under the transport controls.
    readonly property int radius: 3
    readonly property int slotCount: root.radius * 2 + 1

    readonly property var lines: lyricsService.lines
    readonly property int currentIndex: lyricsService.currentLineIndex
    readonly property bool ready: lyricsService.state === "ready" && lyricsService.hasLyrics
                                  && root.currentIndex >= 0

    readonly property real baseFontSize: Math.max(14, Math.min(22, root.height * 0.055))

    // Position of the lyric line shown in a given slot, or -1 when the slot
    // falls outside the song. Returned rather than computed inline so the
    // delegate can test one value instead of repeating the arithmetic.
    function lineIndexFor(slot) {
        const index = root.currentIndex + (slot - root.radius);
        return index >= 0 && index < root.lines.length ? index : -1;
    }

    function lineText(slot) {
        const index = root.lineIndexFor(slot);
        return index >= 0 ? root.lines[index].text : "";
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

    // Rich text for the active line: sung words in the accent, unsung in the
    // body colour, and the word being sung blended between the two by how far
    // playback has reached into it. The blend is what produces a sweep — a
    // binary on/off highlight snaps from word to word, which at KRC's 300-500ms
    // word lengths reads as a stutter.
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

                Layout.fillWidth: true
                Layout.fillHeight: true

                // Word-timed path (KRC): only the active line has word runs.
                Text {
                    anchors.fill: parent
                    visible: slotRoot.distance === 0 && root.richLine !== ""
                    textFormat: Text.RichText
                    text: slotRoot.distance === 0 ? root.richLine : ""
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.family: Fonts.ui
                    font.pixelSize: root.fontSizeFor(slotRoot.index)
                    font.weight: slotRoot.distance === 0 ? Font.Bold : Font.Medium
                    color: root.textColor
                    opacity: root.opacityFor(slotRoot.index)

                    Behavior on opacity {
                        NumberAnimation {
                            duration: 250
                            easing.type: Easing.OutCubic
                        }
                    }
                }

                // Line-timed path: everything without word runs, including the
                // neighbours of a KRC line.
                StyledText {
                    anchors.fill: parent
                    visible: !(slotRoot.distance === 0 && root.richLine !== "")
                    text: root.lineText(slotRoot.index)
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: root.fontSizeFor(slotRoot.index)
                    font.weight: slotRoot.distance === 0 ? Font.Bold : Font.Medium
                    color: slotRoot.distance === 0 ? root.accent : root.textColor
                    opacity: root.opacityFor(slotRoot.index)

                    Behavior on opacity {
                        NumberAnimation {
                            duration: 250
                            easing.type: Easing.OutCubic
                        }
                    }

                    Behavior on font.pixelSize {
                        NumberAnimation {
                            duration: 300
                            easing.type: Easing.OutCubic
                        }
                    }
                }
            }
        }
    }

    // Status block, shown instead of the lines whenever there is nothing to
    // sing along to. Centred as one unit so the icon and the message stay
    // together at any pane height.
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
