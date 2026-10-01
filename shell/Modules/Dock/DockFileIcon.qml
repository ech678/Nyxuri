import QtQuick
import Clavis.Files
import qs.Components

Item {
    id: root
    property var info: ({})
    property bool preview: true
    property bool transformed: false
    readonly property url thumbnail: visible && preview && info.url ? DesktopFiles.thumbnail(info.url) : ""
    FileThemeIcon {
        anchors.fill: parent
        active: root.visible
        rasterSize: 192
        transformed: root.transformed
        themeIcon: root.info.icon || ""
        mimeType: root.info.mimeType || ""
        directory: !!root.info.isDirectory
        entryKey: root.info.url || ""
        visible: image.status !== Image.Ready
    }
    Image {
        id: image
        anchors.fill: parent
        source: root.thumbnail
        smooth: true
        antialiasing: root.transformed
        mipmap: root.transformed
        asynchronous: true
        autoTransform: true
        sourceSize: Qt.size(192, 192)
        fillMode: Image.PreserveAspectFit
        visible: status === Image.Ready
    }
}
