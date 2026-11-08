pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.SystemTray

Singleton {
    id: root

    readonly property var items: SystemTray.items.values
    readonly property var pinnedItems: SystemTray.items.values
    readonly property var unpinnedItems: []

    function getTooltipForItem(item) {
        if (!item) return "";
        return item.tooltip || item.title || item.id || "";
    }

    function togglePin(id) {
    }
}
