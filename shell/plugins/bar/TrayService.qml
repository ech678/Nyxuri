// Fork & Trim: iNiR services/TrayService.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri (ROADMAP B9.1): the xembedsniproxy supervisor (systemd-run
// / sv / pgrep) and the problematicApps launch table are gone — the shell never
// spawns tray proxies, and launching apps belongs to the launcher. Config
// storage moved to PersonalizationConfig.barTray* so pin/unpin persists in the
// same file as the rest of the bar.

pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.SystemTray
import qs.services

Singleton {
    id: root

    property bool smartTray: PersonalizationConfig.barTrayFilterPassive
    property bool invertPins: PersonalizationConfig.barTrayInvertPinnedItems

    // Filter out invalid items (null or missing id): some clients publish a
    // placeholder before the real item registers.
    function isValidItem(item) {
        return item && item.id;
    }

    readonly property var pinnedIds: PersonalizationConfig.barTrayPinnedItems ?? []
    property list<var> itemsInUserList: SystemTray.items.values.filter(i => (isValidItem(i) && pinnedIds.includes(i.id)))
    property list<var> itemsNotInUserList: SystemTray.items.values.filter(i => (isValidItem(i) && !pinnedIds.includes(i.id) && (!smartTray || i.status !== Status.Passive)))

    property list<var> pinnedItems: invertPins ? itemsNotInUserList : itemsInUserList
    property list<var> unpinnedItems: invertPins ? itemsInUserList : itemsNotInUserList

    function getSafeIcon(item): string {
        if (!item)
            return "";
        return item.icon ?? "";
    }

    function getTooltipForItem(item) {
        if (!item)
            return "";
        const tooltipTitle = item.tooltipTitle ?? "";
        const title = item.title ?? "";
        const id = item.id ?? "";
        const tooltipDescription = item.tooltipDescription ?? "";

        var result = tooltipTitle.length > 0 ? tooltipTitle : (title.length > 0 ? title : id);
        if (tooltipDescription.length > 0)
            result += " • " + tooltipDescription;
        if (PersonalizationConfig.barTrayShowItemId)
            result += "\n[" + id + "]";
        return result;
    }

    // Pinning. With invertPinnedItems on (the default), the stored list is the
    // hidden set: every new client is pinned/visible until the user unpins it.
    // pin()/unpin() therefore resolve the list membership from the requested
    // visibility instead of writing the raw list, which kept "Pin" hiding the
    // item it was supposed to show.
    function setShown(itemId, shown) {
        const inList = root.pinnedIds.includes(itemId);
        const wantInList = root.invertPins ? !shown : shown;
        if (inList === wantInList)
            return;
        const next = wantInList ? Array.from(root.pinnedIds).concat(itemId) : Array.from(root.pinnedIds).filter(id => id !== itemId);
        PersonalizationConfig.setBarTrayPinnedItems(next);
    }

    function pin(itemId) {
        root.setShown(itemId, true);
    }

    function unpin(itemId) {
        root.setShown(itemId, false);
    }

    function isPinned(itemId) {
        return root.pinnedItems.some(item => item.id === itemId);
    }

    function togglePin(itemId) {
        root.setShown(itemId, !root.isPinned(itemId));
    }
}
