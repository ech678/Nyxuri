pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons
import qs.services

Singleton {
    id: root

    readonly property string configDir: Paths.configHome
    readonly property string filePath: ConfigService.filePath

    readonly property bool storeReady: ConfigService.storeReady
    property var toggles: defaultToggles()

    function defaultToggles() {
        return [
                    {
                        "type": "network",
                        "size": 2
                    },
                    {
                        "type": "bluetooth",
                        "size": 2
                    },
                    {
                        "type": "caffeine",
                        "size": 1
                    },
                    {
                        "type": "mic",
                        "size": 1
                    },
                    {
                        "type": "audio",
                        "size": 2
                    },
                    {
                        "type": "theme",
                        "size": 2
                    },
                    {
                        "type": "dnd",
                        "size": 1
                    },
                    {
                        "type": "night",
                        "size": 2
                    }
                ];
    }

    function normalizeToggles(rawToggles) {
        if (!Array.isArray(rawToggles))
            return root.defaultToggles();

        const validTypes = root.defaultToggles().map(toggle => toggle.type);
        const seen = {};
        const normalized = [];
        for (const item of rawToggles) {
            const type = item && typeof item.type === "string" ? item.type : "";
            if (validTypes.indexOf(type) === -1 || seen[type])
                continue;

            seen[type] = true;
            normalized.push({
                                "type": type,
                                "size": Number(item.size) === 2 ? 2 : 1
                            });
        }
        // Existing saved layouts also receive the new action without reordering their buttons.
        if (!seen.night)
            normalized.push({
                                "type": "night",
                                "size": 2
                            });
        return normalized;
    }

    function indexOfType(type) {
        return root.toggles.findIndex(toggle => toggle.type === type);
    }

    function refreshBindings() {
        root.toggles = root.toggles.slice();
        root.save();
    }

    function toggleSize(type) {
        const index = root.indexOfType(type);
        if (index === -1)
            return;

        const current = root.toggles[index];
        root.toggles[index] = {
            "type": current.type,
            "size": current.size === 2 ? 1 : 2
        };
        root.refreshBindings();
    }

    function move(type, offset) {
        const index = root.indexOfType(type);
        const target = index + offset;
        if (index === -1 || target < 0 || target >= root.toggles.length)
            return;

        const current = root.toggles[index];
        root.toggles[index] = root.toggles[target];
        root.toggles[target] = current;
        root.refreshBindings();
    }

    function save() {
        if (!root.storeReady)
            return;

        ConfigService.updateSection("bar.quickToggles", root.toggles);
    }

    function loadFromConfigStore() {
        const qtData = ConfigService.getSection("bar.quickToggles", null);
        if (qtData)
            root.toggles = root.normalizeToggles(qtData);
        else
            root.toggles = root.defaultToggles();
        root.refreshBindings();
    }

    Connections {
        target: ConfigService
        function onConfigLoaded() {
            root.loadFromConfigStore();
        }
        function onSectionChanged(path, data) {
            if (path === "bar.quickToggles" || path === "bar")
                root.loadFromConfigStore();
        }
    }

    Component.onCompleted: {
        if (ConfigService.storeReady)
            root.loadFromConfigStore();
    }
}
