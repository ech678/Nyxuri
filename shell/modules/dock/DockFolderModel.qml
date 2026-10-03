import QtQuick
import Qt.labs.folderlistmodel
import qs.app.services

QtObject {
    id: root
    property int revision: 0
    function get(index) {
        const version = root.revision;
        const length = root.count;
        return {
            name: directory.get(index, "fileName") || "",
            url: directory.get(index, "fileURL") || "",
            filePath: directory.get(index, "filePath") || "",
            isFolder: directory.isFolder(index),
            isDirectory: directory.isFolder(index),
            icon: directory.isFolder(index) ? "folder" : "text-x-generic"
        };
    }
    property Connections updates: Connections {
        target: directory
        function onModelReset() {
            root.revision++;
        }
        function onRowsInserted() {
            root.revision++;
        }
        function onRowsRemoved() {
            root.revision++;
        }
        function onDataChanged() {
            root.revision++;
        }
        function onLayoutChanged() {
            root.revision++;
        }
    }
    required property url folder
    property string sort: "name"
    readonly property alias model: dirModel
    readonly property int count: directory.count
    readonly property bool ready: directory.status === FolderListModel.Ready
    readonly property bool loading: directory.status === FolderListModel.Loading
    readonly property var info: DesktopFiles.info(folder)
    readonly property bool available: !!info.available && !!info.isDirectory && !!info.readable
    property FolderListModel directory: FolderListModel {
        id: dirModel
        folder: root.folder
        showDotAndDotDot: false
        showHidden: false
        sortField: root.sort === "time" ? FolderListModel.Time : root.sort === "size" ? FolderListModel.Size : root.sort
                                                                                        === "type"
                                                                                        ? FolderListModel.Type :
                                                                                          FolderListModel.Name
    }
}
