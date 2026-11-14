pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons
import "../commons/Toml.js" as Toml

Singleton {
    id: root

    readonly property string filePath: Paths.configHome + "/config.toml"
    readonly property string configDir: Paths.configHome

    property var rawConfig: ({})
    property bool storeReady: false
    property bool savePending: false
    property bool loading: false
    property string lastError: ""

    signal configLoaded()
    signal sectionChanged(string path, var data)

    function getSection(path, fallback) {
        if (!path || !root.rawConfig)
            return fallback;
        const parts = path.split(".");
        let curr = root.rawConfig;
        for (let i = 0; i < parts.length; ++i) {
            if (curr === undefined || curr === null || typeof curr !== "object")
                return fallback;
            curr = curr[parts[i]];
        }
        return curr !== undefined && curr !== null ? curr : fallback;
    }

    function updateSection(path, data) {
        if (!path)
            return;
        const parts = path.split(".");
        const next = Object.assign({}, root.rawConfig);
        let curr = next;
        for (let i = 0; i < parts.length - 1; ++i) {
            const key = parts[i];
            if (!curr[key] || typeof curr[key] !== "object")
                curr[key] = {};
            else
                curr[key] = Object.assign({}, curr[key]);
            curr = curr[key];
        }
        curr[parts[parts.length - 1]] = data;
        root.rawConfig = next;
        root.sectionChanged(path, data);
        root.requestSave();
    }

    function updateSections(sections) {
        if (!sections || typeof sections !== "object")
            return;
        const next = Object.assign({}, root.rawConfig);
        for (const k in sections)
            next[k] = sections[k];
        root.rawConfig = next;
        root.requestSave();
    }

    function requestSave() {
        if (!root.storeReady || root.loading) {
            root.savePending = true;
            return;
        }
        saveDebounce.restart();
    }

    function saveNow() {
        if (!root.storeReady || root.loading) {
            root.savePending = true;
            return;
        }
        root.savePending = false;
        try {
            let tomlText = "# ====================================================================\n"
                + "# Nyxuri Shell Unified Configuration File\n"
                + "# nyxuri-config-schema: 2\n"
                + "# Automatically maintained; hand-edits are preserved on file reload.\n"
                + "# ====================================================================\n\n";
            tomlText += Toml.stringify(root.rawConfig);
            configFile.setText(tomlText);
        } catch (e) {
            root.lastError = String(e);
            console.warn("[ConfigService] save failed:", e);
        }
    }

    Timer {
        id: saveDebounce
        interval: 50
        repeat: false
        onTriggered: root.saveNow()
    }

    Timer {
        id: reloadDebounce
        interval: 50
        repeat: false
        onTriggered: configFile.reload()
    }

    Process {
        id: initProcess
        command: ["python3", Paths.systemScriptsDir + "/migrate_config.py", "--config-dir", Paths.configHome, "--state-file", Paths.stateHome + "/state.json", "--cleanup"]
        // Not started at construction: the probe below decides whether the
        // migration has anything to do (legacy JSON absorption, [keystone]
        // rename). A stamped, current config.toml skips the interpreter start.
        running: false
        stdout: StdioCollector {
            id: migrationStdout
        }
        onExited: {
            // Stamp the file once so the next launch takes the fast path.
            root.savePending = true;
            root.storeReady = true;
            configFile.reload();
        }
    }

    FileView {
        id: configProbe
        path: root.filePath
        blockLoading: true
        watchChanges: false
        printErrors: false
        onLoaded: {
            const text = configProbe.text();
            if (text.indexOf("# nyxuri-config-schema: 2") !== -1 && text.indexOf("[keystone") === -1)
                root.storeReady = true;
            else
                initProcess.running = true;
        }
        onLoadFailed: error => {
            // Missing file: legacy absorption may have data for the first write.
            initProcess.running = true;
        }
    }

    FileView {
        id: configFile
        path: root.storeReady ? root.filePath : ""
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        watchChanges: true
        onFileChanged: reloadDebounce.restart()
        onLoaded: {
            root.loading = true;
            try {
                const text = configFile.text().trim();
                root.rawConfig = Toml.parse(text || "{}");
                root.lastError = "";
            } catch (error) {
                root.lastError = String(error);
                console.warn("[ConfigService] parse error; leaving existing config untouched:", error);
            }
            root.loading = false;
            root.configLoaded();
            if (root.savePending)
                root.saveNow();
        }
        onLoadFailed: error => {
            if (error === FileViewError.FileNotFound) {
                // If legacy absorption produced data, use it; otherwise empty object
                let absorbed = {};
                try {
                    const raw = migrationStdout.value ? migrationStdout.value.trim() : "";
                    if (raw && raw.length > 2)
                        absorbed = JSON.parse(raw);
                } catch (e) {
                    console.warn("[ConfigService] legacy absorption parse failed:", e);
                }
                root.rawConfig = absorbed;
                root.loading = false;
                root.configLoaded();
                root.saveNow();
            } else {
                root.loading = false;
                console.warn("[ConfigService] could not load " + root.filePath + ": " + error);
            }
        }
        onSaveFailed: error => {
            console.warn("[ConfigService] save failed to disk:", error);
        }
    }

    Component.onDestruction: {
        saveDebounce.stop();
        reloadDebounce.stop();
        if (initProcess)
            initProcess.running = false;
    }
}
