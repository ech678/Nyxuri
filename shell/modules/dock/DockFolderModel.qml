import QtQuick
import Qt.labs.folderlistmodel
import Clavis.Files

QtObject {
    id: root
    property int revision: 0
    function get(index) {
        const version = root.revision;
        const length = root.count;
        return sortedModel.get(index);
    }
    property Connections updates: Connections {
        target: sortedModel
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
    readonly property alias model: sortedModel
    readonly property int count: sorted.count
    readonly property bool ready: directory.status === FolderListModel.Ready
    readonly property bool loading: directory.status === FolderListModel.Loading
    readonly property var info: {
        const count = sorted.count;
        const status = directory.status;
        return DesktopFiles.info(folder);
    }
    readonly property bool available: !!info.available && !!info.isDirectory && !!info.readable
    property FolderListModel directory: FolderListModel {
        folder: root.folder
        showDotAndDotDot: false
        showHidden: false
        sortField: FolderListModel.Unsorted
    }
    property FolderSortModel sorted: FolderSortModel {
        id: sortedModel
        sourceModel: root.directory
        order: root.sort
    }
}
