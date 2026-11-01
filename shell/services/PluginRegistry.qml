pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import "../commons/Toml.js" as Toml
import "PluginManifest.js" as Manifest

// PluginRegistry — the shell's plugin heart (S1-3). Physically copied from
// Omarchy 4's shell/services/PluginRegistry.qml (806 lines, commit c91fc6a
// is the untouched baseline) and trimmed in place (Fork & Trim). The trim
// map, auditable against the baseline diff:
//
//   KEPT verbatim — the process-guard trio (scanProcess / initProcess /
//     watcherReaper with its orphaned-inotifywait reaping / localPluginWatcher
//     inotify hot watch + restart timer), the segmented stream parser
//     (parseScanOutput), ensureUserDir, localPluginIdForPath, the scan →
//     reap → watch → rescan startup chain, the four signals and the
//     destruction stop.
//   CUT (~460 lines) — the shell.json switch and bar-layout machinery
//     (shellConfigProvider/Mutator, setEnabled, findBarLocation, move/put,
//     clone/restore, disabledPlugins). The ledger is the single switch truth;
//     flips route through UnitControlService → `nyxuri on/off` and re-project
//     via StateProjection. This registry is a read-only projection.
//   CUT (deferred with the facades, S1-0 ruling) — trustedCapabilities /
//     stampHostCapabilities; their only consumers are the Plugin*Api facades.
//   RELOCATED — validateManifest / isSafeEntryPoint / entryPointUrl: the same
//     containment invariants live in PluginManifest.js (isSafeRelPath +
//     absolute file:// resolution), one implementation instead of two. The
//     registry adds the root-dependent layer the manifest validator cannot
//     know: third-party ids must be reverse-DNS shaped and can never claim
//     the reserved "shell." / "nyxuri." namespaces or shadow first-party ids.
//   ADAPTED — two blueprint roots, ids derive from the ROOT (never content):
//     firstPartyDir  <shell>/plugins/<domain>/manifest.toml → "shell.<domain>"
//     pluginsDir     ~/.local/share/nyxuri/plugins/<id>/manifest.toml → the
//                    reverse-DNS id itself (engine sources.py landing zone,
//                    watched live; repo manifests are content, never watched).
//     JSON manifests → manifest.toml via Toml.parse + Manifest.validate (the
//     S0-2 vocabulary, manifest-schema.md is the field authority). A manifest
//     that fails any check is rejected loudly; the rest of the registry still
//     stands. Entry points resolve to absolute file:// URLs (loader-form.md).
//
// The S0-2 views (units / toggles / settingsRoutes / settingsAnchors /
// actions) are re-derived from the merged records after every scan — every
// S0 consumer keeps its feed, now including third-party rows. Rows carry
// `unitId` (the full ledger key: "shell.<domain>" first-party, the
// reverse-DNS id third-party) beside `id` (the domain: display text and
// first-party slot arbitration).
Singleton {
    id: registry

    // Third-party root: the add verb's landing zone, watched for hot reload.
    readonly property string pluginsDir: Paths.dataHome + "/plugins"
    // Repo root: manifests are content — scanned at startup, never watched.
    readonly property string firstPartyDir: Paths.shareRoot + "/plugins"
    readonly property string idPrefix: "shell."

    // { pluginId: record } — validated records from both roots.
    property var installedPlugins: ({})
    property int registryRevision: 0
    property bool scanning: false
    property bool ready: false

    // S0-2 views (并轨不丢失) — SlotHost, the switch UI, the settings
    // aggregator and the spotlight index all read these.
    // Mount rows (one per ui kind), sorted by (order, id, kind) — SlotHost's model.
    property var units: []
    // One row per plugin, sorted by (order, id) — the switch UI's model.
    property var toggles: []
    // Settings schema: navigable routes and search anchors.
    property var settingsRoutes: []
    property var settingsAnchors: []
    // Searchable fixed actions (the search index's include set).
    property var actions: []

    signal pluginsChanged
    signal scanFinished
    signal pluginLoadFailed(string id, string error)
    signal localPluginChanged(string id)

    // ---------------------------------------------------------------- helpers

    // Third-party id shape, mirroring nyxuri/sources.py is_reverse_dns:
    // ≥2 clean labels; the reserved namespaces are never third-party.
    function isReverseDns(name) {
        var key = String(name || "");
        if (!key || key !== key.trim())
            return false;
        if (key.indexOf("shell.") === 0 || key.indexOf("nyxuri.") === 0)
            return false;
        var labels = key.split(".");
        if (labels.length < 2)
            return false;
        for (var i = 0; i < labels.length; i++) {
            if (!labels[i] || labels[i].charAt(0) === "-")
                return false;
        }
        return true;
    }

    // ---------------------------------------------------------------- views

    // The S0-2 projection, re-derived from the merged records after every
    // scan. `unitId` is the ledger key the switch plane speaks; `id` (the
    // domain) is what slot arbitration and display labels use.
    function deriveViews(merged) {
        const records = Object.keys(merged).map(id => merged[id]);
        records.sort((a, b) => (a.order - b.order) || (a.id < b.id ? -1 : 1));

        const mountRows = [];
        const toggleRows = [];
        const routes = [];
        const anchors = [];
        const acts = [];
        for (let i = 0; i < records.length; i++) {
            const record = records[i];
            toggleRows.push({
                                unitId: record.id,
                                id: record.domain,
                                label: record.label,
                                order: record.order
                            });
            for (let k = 0; k < record.kinds.length; k++) {
                const kind = record.kinds[k];
                if (kind === "config")
                    continue;
                mountRows.push({
                                   unitId: record.id,
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

        registry.units = mountRows;
        registry.toggles = toggleRows;
        registry.settingsRoutes = routes;
        registry.settingsAnchors = anchors;
        registry.actions = acts;
    }

    // ---------------------------------------------------------------- scanning

    // Output format produced by the rescan script:
    //   ===<kind>::<absolute-source-dir>===
    //   ... raw manifest.toml content ...
    //   === EOM ===
    // (repeating for every manifest found)
    function parseScanOutput(text) {
        var lines = String(text || "").split("\n");
        var firstParty = {};
        var thirdParty = {};
        var currentSource = null;
        var currentKind = null;
        var currentToml = [];

        function flush() {
            if (!currentSource)
                return;
            var dir = currentSource;
            var base = dir.split("/").pop();
            var parsed = null;
            try {
                parsed = Toml.parse(currentToml.join("\n").trim());
            } catch (e) {
                console.warn("PluginRegistry: bad toml at " + dir + "/manifest.toml: " + e);
                registry.pluginLoadFailed(base, String(e));
            }
            if (parsed) {
                var expectedId = currentKind === "firstparty" ? registry.idPrefix + base : base;
                // sourceDir is the plugin DIRECTORY: validate resolves
                // entry point URLs and derives `domain` from it.
                var record = Manifest.validate(parsed, expectedId, dir);
                if (record) {
                    if (currentKind === "firstparty") {
                        firstParty[record.id] = record;
                    } else if (!registry.isReverseDns(record.id)) {
                        console.warn("PluginRegistry: plugin " + record.id
                                     + " rejected: third-party ids must be reverse-DNS shaped");
                        registry.pluginLoadFailed(record.id, "id is not reverse-DNS shaped");
                    } else {
                        thirdParty[record.id] = record;
                    }
                } else {
                    registry.pluginLoadFailed(expectedId, "manifest rejected");
                }
            }
            currentSource = null;
            currentKind = null;
            currentToml = [];
        }

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            var startMatch = line.match(/^===([a-z]+)::(.+)===$/);
            if (startMatch) {
                flush();
                currentKind = startMatch[1];
                currentSource = startMatch[2].replace(/\/$/, "");
                currentToml = [];
                continue;
            }
            if (line === "=== EOM ===") {
                flush();
                continue;
            }
            if (currentSource)
                currentToml.push(line);
        }
        flush();

        var merged = {};
        for (var fk in firstParty)
            merged[fk] = firstParty[fk];
        // Third-party plugins never shadow first-party ids, and the reserved
        // namespaces stay unclaimable (engine registry parity): the whole
        // "shell." / "nyxuri." space belongs to the built-in roots.
        for (var tk in thirdParty) {
            if (firstParty[tk] !== undefined || tk.indexOf("shell.") === 0 || tk.indexOf("nyxuri.") === 0) {
                console.warn("PluginRegistry: plugin " + tk
                             + " rejected: id is reserved for first-party plugins");
                registry.pluginLoadFailed(tk, "id is reserved for first-party plugins");
                continue;
            }
            merged[tk] = thirdParty[tk];
        }

        registry.installedPlugins = merged;
        registry.deriveViews(merged);
        registry.registryRevision++;
        registry.scanning = false;
        registry.ready = true;
        registry.pluginsChanged();
        registry.scanFinished();
    }

    property Process scanProcess: Process {
        onExited: function (exitCode) {
            // An empty registry must never look like a successful scan.
            if (exitCode !== 0)
                console.warn("PluginRegistry: manifest scan exited with " + exitCode);
            registry.parseScanOutput(scanStdout.text || "");
        }
        stdout: StdioCollector {
            id: scanStdout
            waitForEnd: true
        }
    }

    property Process initProcess: Process {
        onExited: {
            registry.reapOrphanedPluginWatchers();
        }
    }

    // Quickshell does not take its Process children with it when it stops, so
    // every shell restart leaves this watcher running, reparented to init
    // (63 of them on one long-lived machine). Before starting our own, stop
    // any plugin watcher whose parent is no longer a shell; a live shell's
    // watcher — parented to it — is left alone. The [i] keeps this script's
    // own command line from matching its search.
    property Process watcherReaper: Process {
        onExited: {
            localPluginWatcher.running = true;
            registry.rescan();
        }
    }

    function reapOrphanedPluginWatchers() {
        watcherReaper.command = ["bash", "-c",
                                 "for p in $(pgrep -f '[i]notifywait -m -r -q -e close_write,create,delete,move' || true); do "
                                 + "tr '\\0' '\\n' < \"/proc/$p/cmdline\" 2>/dev/null | grep -Fxq \"$1\" || continue; "
                                 + "parent=$(ps -o ppid= -p \"$p\" 2>/dev/null | tr -d ' '); "
                                 + "[[ $parent =~ ^[0-9]+$ ]] || continue; "
                                 + "case \"$(ps -o comm= -p \"$parent\" 2>/dev/null)\" in quickshell|qs) ;; *) kill \"$p\" 2>/dev/null || true ;; esac; "
                                 + "done; true", "watcher-reaper", registry.pluginsDir];
        watcherReaper.running = true;
    }

    // A graceful stop takes the watcher with it; the reaper above covers the
    // stops that never run this (a killed or crashed shell).
    Component.onDestruction: {
        localPluginWatcherRestart.stop();
        localPluginReload.stop();
        localPluginWatcher.running = false;
    }

    // Only the third-party root is a live feed; repo manifests change with
    // the shell itself, not under a running session.
    property Process localPluginWatcher: Process {
        command: ["inotifywait", "-m", "-r", "-q", "-e", "close_write,create,delete,move", "--format", "%w%f",
            registry.pluginsDir]
        stdout: SplitParser {
            onRead: function (path) {
                var pluginId = registry.localPluginIdForPath(path);
                if (pluginId) {
                    registry.localPluginChanged(pluginId);
                    registry.localPluginReload.restart();
                }
            }
        }
        onExited: localPluginWatcherRestart.restart()
    }

    property Timer localPluginWatcherRestart: Timer {
        interval: 1000
        onTriggered: localPluginWatcher.running = true
    }

    // A burst of inotify events (a clone checkout, a manifest edit)
    // coalesces into one rescan. Omarchy wired this host-side (its shell.qml
    // injection factory, deferred here with the facades), so the heart owns
    // the connection itself.
    property Timer localPluginReload: Timer {
        interval: 150
        onTriggered: registry.rescan()
    }

    function rescan() {
        if (scanning)
            return;
        scanning = true;
        // $0 = first-party dir, $1 = third-party dir. Both roots share one
        // shape: <root>/<name>/manifest.toml at depth 2. find never follows
        // symlinks (no -L), so a symlinked plugin directory or manifest
        // simply yields nothing — the engine's 禁软链 rule, scan-layer form.
        var script = "" + "emit_manifest() { local kind=\"$1\"; local manifest=\"$2\"; "
                + "  printf '===%s::%s===\\n' \"$kind\" \"${manifest%/manifest.toml}\"; "
                + "  printf '%s\\n' \"$(<\"$manifest\")\"; " + "  printf '\\n=== EOM ===\\n'; " + "}; "
                + "scan_root() { local kind=\"$1\"; local dir=\"$2\"; " + "  [[ -d \"$dir\" ]] || return 0; "
                + "  while IFS= read -r manifest; do emit_manifest \"$kind\" \"$manifest\"; "
                + "  done < <(find \"$dir\" -mindepth 2 -maxdepth 2 -type f -name manifest.toml | sort); "
                + "}; " + "scan_root firstparty \"$0\"; " + "scan_root thirdparty \"$1\"";
        scanProcess.command = ["bash", "-c", script, registry.firstPartyDir, registry.pluginsDir];
        scanProcess.running = true;
    }

    function ensureUserDir() {
        initProcess.command = ["bash", "-c", "mkdir -p \"$0\"", registry.pluginsDir];
        initProcess.running = true;
    }

    function localPluginIdForPath(filePath) {
        var base = pluginsDir.replace(/\/$/, "") + "/";
        var path = String(filePath || "").trim();
        if (path.indexOf(base) !== 0)
            return "";

        var relative = path.slice(base.length);
        // Hidden entries are not plugins: clone staging dirs, remove backups.
        if (relative.indexOf(".") === 0)
            return "";
        if (relative.indexOf("/.git/") !== -1 || relative.endsWith("/.git"))
            return "";

        var slash = relative.indexOf("/");
        return slash === -1 ? relative : relative.slice(0, slash);
    }

    Component.onCompleted: ensureUserDir()
}
