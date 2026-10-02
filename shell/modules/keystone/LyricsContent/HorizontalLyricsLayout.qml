import QtQuick
import qs.Common
import qs.Widgets.common

Item {
    id: root

    required property var lyricsModel
    required property int currentLineIndex
    required property string artUrl
    required property var player
    required property string status
    required property string errorText
    property int defaultTextWidth: 350
    property int currentTextWidth: defaultTextWidth

    implicitWidth: 102 + currentTextWidth
    implicitHeight: 42

    LyricsAlbumArt {
        id: albumArt

        anchors.left: parent.left
        anchors.leftMargin: 15
        anchors.verticalCenter: parent.verticalCenter
        sourceUrl: root.artUrl
    }

    StyledListView {
        id: lyricsView

        anchors.left: albumArt.right
        anchors.leftMargin: 12
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.currentTextWidth
        interactive: false
        animateAppearance: false
        animateMovement: false
        showVerticalScrollBar: false
        model: root.lyricsModel
        currentIndex: root.currentLineIndex
        highlightRangeMode: ListView.StrictlyEnforceRange
        preferredHighlightBegin: 0
        preferredHighlightEnd: 0
        highlightMoveDuration: 400

        delegate: Item {
            required property var modelData
            required property int index
            readonly property bool isCurrent: index === root.currentLineIndex

            width: ListView.view.width
            height: 42
            onIsCurrentChanged: {
                if (isCurrent)
                    root.currentTextWidth = Math.max(root.defaultTextWidth, Math.min(lyricText.implicitWidth,
                                                                                     800));
            }

            Text {
                id: lyricText

                anchors.centerIn: parent
                text: parent.modelData.text
                color: Appearance.m3colors.darkmode ? "white" : "black"
                font.family: Fonts.ui
                font.pixelSize: 15
                font.weight: Font.Bold
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter

                Behavior on color {
                    ColorAnimation {
                        duration: Appearance.animation.expressiveFastEffects.duration
                        easing.type: Appearance.animation.expressiveFastEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                    }
                }
            }
        }
    }

    Text {
        anchors.centerIn: lyricsView
        width: lyricsView.width - 12
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        color: Appearance.applyAlpha(Appearance.colors.colOnLayer0, 0.65)
        font.family: Fonts.ui
        font.pixelSize: 13
        visible: root.status !== "ready"
        text: root.status === "loading" ? qsTr("Loading lyrics…") : root.status === "error" ? root.errorText
                                                                                              || qsTr("Failed to load lyrics") :
                                                                                              qsTr("No lyrics available")
    }

    LyricsSpectrum {
        anchors.right: parent.right
        anchors.rightMargin: 15
        anchors.verticalCenter: parent.verticalCenter
        width: 21
        height: 21
        player: root.player
    }
}
