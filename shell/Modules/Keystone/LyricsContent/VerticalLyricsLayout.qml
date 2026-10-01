import QtQuick
import qs.Common

Item {
    id: root

    required property string lyric
    required property string artUrl
    required property var player
    required property string edge
    required property string status
    required property string errorText
    readonly property int padding: 15
    readonly property int contentSpacing: 12
    readonly property int tokenSpacing: 3
    readonly property int lyricWidth: 42
    readonly property real lyricExtent: Math.max(20, currentTokens.implicitHeight)

    function isCjk(character) {
        return /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]/.test(character);
    }

    function isLatinCore(character) {
        return /[A-Za-z0-9]/.test(character);
    }

    function isLatinPunctuation(character) {
        return /['’\-….,!?]/.test(character);
    }

    function tokenize(text) {
        const result = [];
        const source = String(text || "");
        let index = 0;
        while (index < source.length) {
            const character = source[index];
            if (/\s/.test(character)) {
                ++index;
                continue;
            }
            if (isCjk(character)) {
                result.push({
                                "text": character,
                                "latin": false
                            });
                ++index;
                continue;
            }
            if (isLatinCore(character)) {
                let token = character;
                ++index;
                while (index < source.length && (isLatinCore(source[index]) || isLatinPunctuation(
                                                     source[index]))) {
                    token += source[index];
                    ++index;
                }
                result.push({
                                "text": token,
                                "latin": true
                            });
                continue;
            }
            result.push({
                            "text": character,
                            "latin": false
                        });
            ++index;
        }
        return result;
    }

    implicitWidth: lyricWidth
    implicitHeight: padding + 26 + contentSpacing + lyricExtent + contentSpacing + 21 + padding

    LyricsAlbumArt {
        id: albumArt

        anchors.top: parent.top
        anchors.topMargin: root.padding
        anchors.horizontalCenter: parent.horizontalCenter
        sourceUrl: root.artUrl
    }

    Item {
        id: lyricSlot

        anchors.top: albumArt.bottom
        anchors.topMargin: root.contentSpacing
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.lyricWidth
        height: root.lyricExtent

        TokenColumn {
            id: currentTokens

            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            lyricText: root.lyric
        }

        Text {
            anchors.centerIn: parent
            width: root.lyricWidth
            visible: root.status !== "ready"
            text: root.status === "loading" ? qsTr("Loading") : root.status === "error" ? qsTr("Failed") :
                                                                                          qsTr("Unavailable")
            color: Appearance.applyAlpha(Appearance.colors.colOnLayer0, 0.65)
            font.family: Fonts.ui
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WrapAnywhere
        }
    }

    LyricsSpectrum {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: root.padding
        anchors.horizontalCenter: parent.horizontalCenter
        width: 21
        height: 21
        player: root.player
    }

    component TokenColumn: Column {
        required property string lyricText
        property var tokenModel: root.tokenize(lyricText)

        width: root.lyricWidth
        spacing: root.tokenSpacing

        Repeater {
            model: parent.tokenModel

            delegate: Item {
                required property var modelData
                readonly property bool latin: modelData.latin

                width: root.lyricWidth
                height: latin ? tokenText.implicitWidth : Math.max(18, tokenText.implicitHeight)

                Text {
                    id: tokenText

                    anchors.centerIn: parent
                    text: parent.modelData.text
                    color: Appearance.m3colors.darkmode ? "white" : "black"
                    font.family: Fonts.ui
                    font.pixelSize: 15
                    font.weight: Font.Bold
                    rotation: parent.latin ? (root.edge === "left" ? -90 : 90) : 0
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }
}
