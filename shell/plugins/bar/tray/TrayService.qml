pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.SystemTray
import qs.commons
import qs.services
import qs.commons.i18n

Singleton {
    id: root

    readonly property string configDir: Paths.configHome
    readonly property string filePath: ConfigService.filePath

    readonly property bool storeReady: ConfigService.storeReady
    property bool showItemId: false
    property bool invertPinnedItems: true
    property bool filterPassive: true
    property var pinnedItemIds: ["Fcitx"]

    readonly property var visibleItems: (SystemTray.items.values || []).filter(item => !root.filterPassive
                                                                                       || item.status
                                                                                       !== Status.Passive)
    readonly property var itemsInUserList: visibleItems.filter(item => root.pinnedItemIds.indexOf(item.id)
                                                                       !== -1)
    readonly property var itemsNotInUserList: visibleItems.filter(item => root.pinnedItemIds.indexOf(item.id)
                                                                          === -1)
    readonly property var pinnedItems: root.invertPinnedItems ? root.itemsNotInUserList : root.itemsInUserList
    readonly property var unpinnedItems: root.invertPinnedItems ? root.itemsInUserList :
                                                                  root.itemsNotInUserList

    function defaultConfig() {
        return {
            "showItemId": false,
            "invertPinnedItems": true,
            "pinnedItems": ["Fcitx"],
            "filterPassive": true
        };
    }

    function normalizeStringList(value) {
        if (!Array.isArray(value))
            return root.defaultConfig().pinnedItems;
        return value.filter(item => typeof item === "string" && item.length > 0);
    }

    function loadFromObject(parsed) {
        const defaults = root.defaultConfig();
        root.showItemId = typeof parsed.showItemId === "boolean" ? parsed.showItemId : defaults.showItemId;
        root.invertPinnedItems = typeof parsed.invertPinnedItems === "boolean" ? parsed.invertPinnedItems :
                                                                                 defaults.invertPinnedItems;
        root.filterPassive = typeof parsed.filterPassive === "boolean" ? parsed.filterPassive :
                                                                         defaults.filterPassive;
        root.pinnedItemIds = root.normalizeStringList(parsed.pinnedItems);
    }

    function save() {
        if (!root.storeReady)
            return;

        ConfigService.updateSection("bar.tray", {
            "showItemId": root.showItemId,
            "invertPinnedItems": root.invertPinnedItems,
            "pinnedItems": root.pinnedItemIds,
            "filterPassive": root.filterPassive
        });
    }

    function loadFromConfigStore() {
        const trayData = ConfigService.getSection("bar.tray", null);
        if (trayData)
            root.loadFromObject(trayData);
        else
            root.loadFromObject(root.defaultConfig());
    }

    Connections {
        target: ConfigService
        function onConfigLoaded() {
            root.loadFromConfigStore();
        }
        function onSectionChanged(path, data) {
            if (path === "bar.tray" || path === "bar")
                root.loadFromConfigStore();
        }
    }

    function getTooltipForItem(item) {
        if (!item)
            return I18n.tr("Tray");

        let result = item.tooltipTitle && item.tooltipTitle.length > 0 ? item.tooltipTitle : (item.title
                                                                                              && item.title.length
                                                                                              > 0 ? item.title :
                                                                                                    item.id);

        if (item.tooltipDescription && item.tooltipDescription.length > 0)
            result += " • " + item.tooltipDescription;
        if (root.showItemId)
            result += "\n[" + item.id + "]";
        return result;
    }

    function isPinned(itemId) {
        for (let i = 0; i < root.pinnedItems.length; i += 1) {
            if (root.pinnedItems[i].id === itemId)
                return true;
        }
        return false;
    }

    function togglePin(itemId) {
        if (!itemId || itemId.length === 0)
            return;

        const nextIds = root.pinnedItemIds.slice();
        const index = nextIds.indexOf(itemId);
        if (index === -1)
            nextIds.push(itemId);
        else
            nextIds.splice(index, 1);

        root.pinnedItemIds = nextIds;
        root.save();
    }

    Component.onCompleted: {
        if (ConfigService.storeReady)
            root.loadFromConfigStore();
    }
}
