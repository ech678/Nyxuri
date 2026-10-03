import QtQuick
import qs.app.services

Item {
    id: root

    required property var player
    property bool vertical: false
    property string edge: "top"

    // 封存组件：解耦已废弃的 C++ 原生歌词插件，支持外部注入或纯 QML/JS 服务
    property var lyricsModel: []
    property bool hasSynchronizedLyrics: false
    property string status: "idle"
    property string errorText: ""
    readonly property string artUrl: player ? player.trackArtUrl || "" : ""
    readonly property int currentLineIndex: -1
    readonly property string currentLyric: currentLineIndex >= 0 && currentLineIndex < lyricsModel.length ? String(
                                                                                                                lyricsModel[currentLineIndex].text
                                                                                                                || "") : lyricsModel
                                                                                                            && lyricsModel.length
                                                                                                            > 0 ? String(
                                                                                                                      lyricsModel[0].text
                                                                                                                      || "") : ""

    implicitWidth: presenter.item ? presenter.item.implicitWidth : 0
    implicitHeight: presenter.item ? presenter.item.implicitHeight : 0
    Loader {
        id: presenter

        anchors.fill: parent
        sourceComponent: root.vertical ? verticalComponent : horizontalComponent
    }

    Component {
        id: horizontalComponent

        HorizontalLyricsLayout {
            lyricsModel: root.lyricsModel
            currentLineIndex: root.currentLineIndex
            artUrl: root.artUrl
            player: root.player
            status: root.status
            errorText: root.errorText
        }
    }

    Component {
        id: verticalComponent

        VerticalLyricsLayout {
            lyric: root.currentLyric
            artUrl: root.artUrl
            player: root.player
            edge: root.edge
            status: root.status
            errorText: root.errorText
        }
    }
}
