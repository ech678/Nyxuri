import QtQuick

Item {
    id: root
    property string sourcePath: ""
    property string previewPath: ""
    readonly property bool ready: saved.ready || (preview.item !== null && preview.item.ready)

    WallpaperImageViewport {
        id: saved
        anchors.fill: parent
        sourcePath: root.sourcePath
    }
    Loader {
        id: preview
        anchors.fill: parent
        active: root.previewPath !== ""
        sourceComponent: WallpaperImageViewport {
            sourcePath: root.previewPath
        }
    }
}
