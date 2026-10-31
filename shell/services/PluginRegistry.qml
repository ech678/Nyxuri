pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import "../commons/Toml.js" as Toml
import "PluginManifest.js" as Manifest

// PluginRegistry — the runtime plugin registry (S0-2). The hand-written host
// mirrors (unit catalog, settings route table, generated search catalog, nav
// grouping table) are replaced by ONE runtime read of every
// plugins/<domain>/manifest.toml: adding a plugin = adding a directory +
// manifest + code, zero host changes.
//
// Vocabulary and checks mirror nyxuri/deploy/manifest.py (manifest-schema.md
// is the field authority): schemaVersion 1, root-derived id, closed kinds
// enum, entryPoints containment, settings routes/anchors, fixed actions. A
// manifest that fails any check is rejected loudly; the rest of the registry
// still stands.
//
// Entry points resolve to absolute file:// URLs here (loader-form.md): a
// relative Loader source becomes a qs: URL and dies in the Quickshell 0.3.2
// dynamic-loading defect. Scanning is a startup affair — manifests are repo
// content, not a live feed (third-party lifecycle lands with S1).
Singleton {
    id: root

    readonly property string pluginsDir: Paths.shareRoot + "/plugins"
    readonly property string idPrefix: "shell."

    // Manifest id -> validated record.
    property var plugins: ({})
    // Mount rows (one per ui kind), sorted by (order, id, kind) — SlotHost's model.
    property var units: []
    // One row per plugin, sorted by (order, id) — the switch UI's model.
    property var toggles: []
    // Settings schema: navigable routes and search anchors.
    property var settingsRoutes: []
    property var settingsAnchors: []
    // Searchable fixed actions (the search index's include set).
    property var actions: []
    property bool ready: false

    property var _records: ({})
    property var _paths: []
    property int _settled: 0

    function _warn(message) {
        console.warn("[PluginRegistry] " + message);
    }

    // ---------------------------------------------------------------- scanning

    Process {
        id: scanProc

        command: ["find", root.pluginsDir, "-mindepth", "2", "-maxdepth", "2", "-type", "f", "-name",
            "manifest.toml"]
        stdout: SplitParser {
            onRead: line => {
                const path = String(line).trim();
                if (path.length > 0)
                    root._paths.push(path);
            }
        }
        onExited: exitCode => {
            if (exitCode !== 0)
                root._warn("manifest scan exited with " + exitCode + " (" + root.pluginsDir + ")");
            root._startReaders();
        }
    }

    Component {
        id: manifestReader

        FileView {
            onLoaded: root._onManifest(String(path), text())
            onLoadFailed: error => root._onManifestFailed(String(path), error)
        }
    }

    function _startReaders() {
        root._paths.sort();
        if (root._paths.length === 0) {
            root._finalize();
            return;
        }
        for (let i = 0; i < root._paths.length; i++) {
            const reader = manifestReader.createObject(root, {
                                                           "path": root._paths[i]
                                                       });
            if (!reader) {
                root._warn("cannot open " + root._paths[i]);
                root._settle();
            }
        }
    }

    function _onManifest(path, content) {
        const dir = String(path).replace(/\/manifest\.toml$/, "");
        const domain = dir.split("/").pop();
        let parsed = null;
        try {
            parsed = Toml.parse(String(content));
        } catch (error) {
            root._warn("bad toml at " + path + ": " + error);
        }
        if (parsed) {
            const record = Manifest.validate(parsed, root.idPrefix + domain, dir);
            if (record) {
                if (root._records[record.id])
                    root._warn("duplicate plugin id " + record.id + " (" + dir + ")");
                else
                    root._records[record.id] = record;
            } else {
                root._warn("rejected manifest at " + path);
            }
        }
        root._settle();
    }

    function _onManifestFailed(path, error) {
        root._warn("cannot read " + path + ": " + error);
        root._settle();
    }

    function _settle() {
        root._settled += 1;
        if (root._settled >= root._paths.length)
            root._finalize();
    }

    // ---------------------------------------------------------------- views

    function _finalize() {
        const records = Object.keys(root._records).map(id => root._records[id]);
        records.sort((a, b) => (a.order - b.order) || (a.id < b.id ? -1 : 1));

        const mountRows = [];
        const toggleRows = [];
        const routes = [];
        const anchors = [];
        const acts = [];
        for (let i = 0; i < records.length; i++) {
            const record = records[i];
            toggleRows.push({
                                id: record.domain,
                                label: record.label,
                                order: record.order
                            });
            for (let k = 0; k < record.kinds.length; k++) {
                const kind = record.kinds[k];
                if (kind === "config")
                    continue;
                mountRows.push({
                                   id: record.domain,
                                   label: record.label,
                                   kind: kind,
                                   order: record.order,
                                   entryUrl: record.entryUrls[kind]
                               });
            }
            for (let r = 0; r < record.settingsRoutes.length; r++)
                routes.push(Object.assign({
                                              pluginId: record.id
                                          }, record.settingsRoutes[r]));
            for (let a = 0; a < record.settingsAnchors.length; a++)
                anchors.push(Object.assign({
                                               pluginId: record.id
                                           }, record.settingsAnchors[a]));
            for (let s = 0; s < record.actions.length; s++)
                acts.push(Object.assign({
                                            pluginId: record.id
                                        }, record.actions[s]));
        }
        mountRows.sort((a, b) => (a.order - b.order) || (a.id < b.id ? -1 : 1) || (a.kind < b.kind ? -1 : 1));
        routes.sort((a, b) => (a.order - b.order) || (a.id < b.id ? -1 : 1));
        anchors.sort((a, b) => (a.id < b.id ? -1 : 1));
        acts.sort((a, b) => (a.id < b.id ? -1 : 1));

        root.units = mountRows;
        root.toggles = toggleRows;
        root.settingsRoutes = routes;
        root.settingsAnchors = anchors;
        root.actions = acts;
        root.ready = true;
    }

    Component.onCompleted: scanProc.running = true
    Component.onDestruction: scanProc.running = false
}
