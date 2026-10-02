import QtQuick
import qs.shared.theme

Image {
    id: root

    property url iconSource: ""
    readonly property int themeRevision: Resources.iconThemeRevision
    property bool refreshing: false

    function finishRefresh() {
        refreshing = false;
    }

    source: refreshing ? "" : iconSource
    // Quickshell's image://icon URL is unchanged when QIcon's theme changes.
    // Reload on the next event loop and bypass the old Qt Quick pixmap cache.
    cache: !iconSource.toString().startsWith("image://icon/")
    onThemeRevisionChanged: {
        if (!iconSource.toString().startsWith("image://icon/"))
            return;
        refreshing = true;
        Qt.callLater(root.finishRefresh);
    }
}
