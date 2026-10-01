import QtQuick
import qs.Common
import qs.Services
import "../../Common/functions/FileUtils.js" as FileUtils

Item {
    id: root
    property bool active: false
    property string query: ""
    readonly property string searchState: FileSearchService.state
    readonly property var error: FileSearchService.error
    readonly property var results: FileSearchService.entries.map(entry => ({
        provider: "files",
        id: entry.path,
        title: entry.name,
        subtitle: metadataLine(entry),
        icon: entry.icon,
        actions: ["open", "reveal"],
        file: entry,
        location: compactPath(entry.parentPath)
    }))
    signal activated

    function compactPath(path) {
        const home = String(Paths.homeDir).replace(/\/+$/, "");
        return path === home || path.startsWith(home + "/") ? "~" + path.slice(home.length) : path;
    }
    function metadataLine(entry) {
        const type = entry.isDirectory ? qsTr("Folder") : entry.mimeType.startsWith("audio/") ? qsTr(
                                                                                                    "%1 audio").arg(
                                                                                                    entry.extension.toUpperCase(
                                                                                                        )) : entry.mimeType.startsWith(
                                                                                                    "image/")
                                                                                                ? qsTr("%1 image").arg(
                                                                                                      entry.extension.toUpperCase(
                                                                                                          )) : entry.mimeType.startsWith(
                                                                                                      "video/")
                                                                                                  ? qsTr("%1 video").arg(
                                                                                                        entry.extension.toUpperCase(
                                                                                                            )) : entry.extension
                                                                                                    ? qsTr("%1 file").arg(
                                                                                                          entry.extension.toUpperCase(
                                                                                                              )) : qsTr(
                                                                                                          "File");
        const parts = [type];
        if (entry.size !== null && !entry.isDirectory)
            parts.push(FileUtils.humanReadableSize(entry.size));
        if (entry.modifiedTime !== null) {
            const date = new Date(entry.modifiedTime * 1000);
            parts.push(qsTr("%1 %2").arg(date.toLocaleDateString(Qt.locale(), Locale.ShortFormat)).arg(
                           UiPreferences.shortTime(date)));
        }
        parts.push(entry.parentName);
        return parts.join(" · ");
    }
    function execute(index, reveal) {
        const result = results[index];
        return !!result && FileSearchService.execute(result.file.path, reveal);
    }
    onActiveChanged: FileSearchService.active = active
    onQueryChanged: FileSearchService.query = query
    Component.onDestruction: FileSearchService.active = false
    Connections {
        target: FileSearchService
        function onActivated() {
            root.activated();
        }
    }
}
