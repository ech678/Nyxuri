pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

// PluginSettings — the host-owned value store for schema-declared settings
// controls (S0-3b). A route that declares `controls` instead of `source`
// renders through the generic schema page; its values live here, keyed
// "<pluginId>.<controlKey>" (the plugin namespace keeps third-party and
// domain plugins apart without a per-plugin file). This is the replacement
// face for Omarchy's shell.json widget values — declaration in the manifest,
// storage host-side, never a second switch truth.
Singleton {
    id: root

    signal valueChanged(string key)

    property var values: ({})
    property bool storeReady: false
    property bool savePending: false

    readonly property string filePath: Paths.configHome + "/plugin-settings.json"

    function fullKey(pluginId, key) {
        return pluginId + "." + key;
    }

    function value(pluginId, key, fallback) {
        const id = root.fullKey(pluginId, key);
        const stored = root.values[id];
        if (stored === undefined || stored === null)
            return fallback;
        return stored;
    }

    function setValue(pluginId, key, value) {
        const id = root.fullKey(pluginId, key);
        if (root.values[id] === value)
            return;
        const next = Object.assign({}, root.values);
        next[id] = value;
        root.values = next;
        root.valueChanged(id);
        root.save();
    }

    function resetPlugin(pluginId) {
        if (!pluginId)
            return;
        const prefix = pluginId + ".";
        let changed = false;
        const next = Object.assign({}, root.values);
        for (const k in next) {
            if (k.indexOf(prefix) === 0) {
                delete next[k];
                changed = true;
                root.valueChanged(k);
            }
        }
        if (changed) {
            root.values = next;
            root.save();
        }
    }

    function save() {
        if (!root.storeReady) {
            root.savePending = true;
            return;
        }
        root.savePending = false;
        storeFile.setText(JSON.stringify(root.values, null, 2) + "\n");
        storeFile.save();
    }

    FileView {
        id: storeFile

        path: root.filePath
        watchChanges: true
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        onFileChanged: reloadDebounce.restart()
        onLoaded: {
            try {
                const parsed = JSON.parse(storeFile.text().trim() || "{}");
                if (parsed && typeof parsed === "object" && !Array.isArray(parsed))
                    root.values = parsed;
            } catch (error) {
                console.warn("[PluginSettings] cannot parse " + root.filePath + ": " + error);
            }
            root.storeReady = true;
            if (root.savePending)
                root.save();
        }
        onLoadFailed: error => {
            // A missing file is the pristine case, not an error.
            root.storeReady = true;
            if (root.savePending)
                root.save();
        }
    }

    Timer {
        id: reloadDebounce
        interval: 150
        onTriggered: storeFile.reload()
    }

    Component.onCompleted: {
        ShellStartupService.registerQmlResource("PluginSettings", "fileview", storeFile);
        storeFile.reload();
    }

    Component.onDestruction: {
        ShellStartupService.unregisterQmlResource("PluginSettings", "fileview", storeFile);
    }
}
