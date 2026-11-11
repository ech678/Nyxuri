import QtQuick
import qs.ui

Item {
    id: root

    property string source: ""
    property string transitionKey: ""
    property bool downloaded: true
    property real artRadius: 0
    property color placeholderColor: "transparent"
    property color iconColor: "white"
    property int iconSize: 16

    clip: true

    Rectangle {
        id: placeholder
        anchors.fill: parent
        radius: root.artRadius
        color: root.placeholderColor
        visible: !artImage.visible

        MaterialSymbol {
            anchors.centerIn: parent
            text: "music_note"
            iconSize: root.iconSize
            color: root.iconColor
        }
    }

    StyledImage {
        id: artImage
        anchors.fill: parent
        source: root.source
        visible: root.source.length > 0 && status === Image.Ready
    }
}
