pragma Singleton
import QtQuick

QtObject {
    id: root

    property int trashCount: 0
    property bool trashAvailable: true
    property bool busy: false

    signal trashChanged
    signal filesChanged
    signal finished(bool success, string message)

    function info(url) {
        const urlStr = String(url || "");
        const path = urlStr.replace(/^file:\/\//, "");
        const parts = path.split("/").filter(Boolean);
        const basename = parts.length > 0 ? parts[parts.length - 1] : "";
        const isFolder = !basename.includes(".") || urlStr.endsWith("/");
        return {
            name: decodeURIComponent(basename),
            available: true,
            isFolder: isFolder,
            isDirectory: isFolder,
            readable: true,
            icon: isFolder ? "folder" : "text-x-generic",
            mime: isFolder ? "inode/directory" : "application/octet-stream",
            mimeType: isFolder ? "inode/directory" : "application/octet-stream",
            url: urlStr
        };
    }

    function thumbnail(url) {
        return "";
    }

    function watchUrls(urls) {
    }

    function canOpenWith(desktopId) {
        return true;
    }

    function openWith(desktopId, urls) {
        return true;
    }

    function moveToTrash(urls) {
        return true;
    }

    function emptyTrash() {
        return true;
    }
}
