pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Common

Singleton {
    id: root

    property bool active: false
    property string query: ""
    property var entries: []
    property string state: "idle"
    property var error: null
    property bool limited: false
    property bool actionRunning: false
    property bool capabilityKnown: false
    property bool available: false
    property string capabilityError: "fd_unavailable"
    property int generation: 0
    property int searchGeneration: -1
    property int actionGeneration: -1
    property string actionName: ""
    property string actionPath: ""
    property string searchOutput: ""
    property string statusOutput: ""
    property string actionOutput: ""
    property bool searchFinished: false
    property bool searchExited: false
    property bool statusFinished: false
    property bool statusExited: false
    property bool actionFinished: false
    property bool actionExited: false
    property int searchExitCode: -1
    property int statusExitCode: -1
    property int actionExitCode: -1
    signal activated

    function failure(code) {
        const messages = {
            fd_unavailable: qsTr("Install fd to search files"),
            file_capability_missing: qsTr("Update key-cli to enable file search"),
            invalid_file_response: qsTr("The file service returned invalid data"),
            file_missing: qsTr("The file or link target no longer exists"),
            directory_missing: qsTr("The containing folder no longer exists"),
            file_execution_blocked: qsTr("Use Apps to launch this item, or show it in the file manager"),
            dependency_missing: qsTr("The system file opener is unavailable"),
            file_action_timeout: qsTr("The system did not confirm the request in time"),
            file_search_failed: qsTr("File search failed"),
            file_action_failed: qsTr("Unable to open or show this item")
        };
        return {
            code: code,
            message: messages[code] || qsTr("File operation failed")
        };
    }

    function parse(text, command) {
        try {
            const value = JSON.parse(text);
            return value && !Array.isArray(value) && value.schemaVersion === 1 && value.command === command
                    && typeof value.ok === "boolean" && (value.ok ? value.error === null : value.error
                                                                    && typeof value.error.code === "string")
                    ? value : null;
        } catch (e) {
            return null;
        }
    }

    function refresh() {
        generation += 1;
        debounce.stop();
        entries = [];
        limited = false;
        error = null;
        if (searchProcess.running)
            searchProcess.signal(15);
        if (!active) {
            state = "idle";
            return;
        }
        if (!capabilityKnown) {
            state = "loading";
            if (!statusProcess.running) {
                statusFinished = false;
                statusExited = false;
                statusOutput = "";
                statusProcess.command = [Paths.stableKey, "file", "status", "--format", "json"];
                statusProcess.running = true;
            }
            return;
        }
        if (!available) {
            state = "unavailable";
            error = failure(capabilityError);
            return;
        }
        state = query.trim() === "" ? "idle" : "loading";
        if (state === "loading")
            debounce.restart();
    }

    function finishStatus() {
        if (!statusExited || !statusFinished)
            return;
        const value = parse(statusOutput, "file.status");
        capabilityKnown = true;
        available = !!(value && statusExitCode === 0 && value.ok && value.capabilities
                       && value.capabilities.search === true && value.canSearch === true);
        if (!active)
            return;
        if (!value || !value.capabilities || value.capabilities.search !== true) {
            capabilityError = "file_capability_missing";
            state = "unavailable";
            error = failure(capabilityError);
            return;
        }
        capabilityError = "fd_unavailable";
        refresh();
    }

    function startSearch() {
        if (!active || !available || query.trim() === "" || searchProcess.running || (!searchExited ||
                                                                                      !searchFinished)
                && searchGeneration >= 0)
            return;
        searchGeneration = generation;
        searchFinished = false;
        searchExited = false;
        searchOutput = "";
        searchProcess.command = [Paths.stableKey, "file", "search", "--format", "json", "--limit", "50", "--",
                                 query];
        searchProcess.running = true;
    }

    function validEntry(e) {
        return e && typeof e.name === "string" && typeof e.path === "string" && e.path.startsWith("/") && typeof e.parentPath
                === "string" && e.parentPath.startsWith("/") && typeof e.parentName === "string" && ["file", "directory",
                                                                                                     "symlink"].indexOf(
                    e.kind) >= 0 && typeof e.mimeType === "string" && typeof e.extension === "string" && (
                    e.size === null || typeof e.size === "number" && isFinite(e.size) && e.size >= 0) && (e.modifiedTime === null
                                                                                                          || typeof e.modifiedTime
                                                                                                          === "number"
                                                                                                          && isFinite(
                                                                                                              e.modifiedTime))
                && typeof e.isDirectory === "boolean" && typeof e.isSymlink === "boolean"
                && typeof e.isExecutable === "boolean" && typeof e.icon === "string" && !
                /[\u0000\uD800-\uDFFF]/u.test(e.path);
    }

    function finishSearch() {
        if (!searchExited || !searchFinished)
            return;
        if (searchGeneration !== generation || !active) {
            if (active && !debounce.running)
                Qt.callLater(root.startSearch);
            return;
        }
        const value = parse(searchOutput, "file.search");
        if (!value || searchExitCode !== 0 || !value.ok || value.query !== query || !Array.isArray(
                    value.entries) || value.entries.length > 50 || !value.entries.every(root.validEntry)
                || typeof value.complete !== "boolean" || typeof value.limited !== "boolean"
                || value.complete === value.limited) {
            state = "error";
            error = failure(value && value.error ? value.error.code : "invalid_file_response");
            return;
        }
        entries = value.entries;
        limited = value.limited;
        state = limited ? "limited" : entries.length ? "results" : "empty";
    }

    function execute(path, reveal) {
        if (!active || actionRunning || searchGeneration !== generation || state === "loading" || !entries.some(
                    e => e.path === path))
            return false;
        actionRunning = true;
        actionGeneration = generation;
        actionName = reveal ? "reveal" : "open";
        actionPath = path;
        actionFinished = false;
        actionExited = false;
        actionOutput = "";
        error = null;
        actionProcess.command = [Paths.stableKey, "file", actionName, "--format", "json", "--", path];
        actionProcess.running = true;
        return true;
    }

    function finishAction() {
        if (!actionFinished || !actionExited)
            return;
        actionRunning = false;
        if (!active || actionGeneration !== generation)
            return;
        const value = parse(actionOutput, "file." + actionName);
        if (value && value.ok && actionExitCode === 0 && value.path === actionPath && typeof value.fileExists
                === "boolean" && (actionName === "open" ? value.mode === "open" : ["reveal",
                                                                                   "directory"].indexOf(
                                                              value.mode) >= 0))
            activated();
        else
            error = failure(value && value.error ? value.error.code : "file_action_failed");
    }

    onActiveChanged: {
        if (active)
            capabilityKnown = false;
        refresh();
    }
    onQueryChanged: refresh()

    Timer {
        id: debounce
        interval: 180
        onTriggered: root.startSearch()
    }
    Process {
        id: statusProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.statusOutput = text;
                root.statusFinished = true;
                root.finishStatus();
            }
        }
        onExited: code => {
            root.statusExitCode = code;
            root.statusExited = true;
            root.finishStatus();
        }
    }
    Process {
        id: searchProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.searchOutput = text;
                root.searchFinished = true;
                root.finishSearch();
            }
        }
        onExited: code => {
            root.searchExitCode = code;
            root.searchExited = true;
            root.finishSearch();
        }
    }
    Process {
        id: actionProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.actionOutput = text;
                root.actionFinished = true;
                root.finishAction();
            }
        }
        onExited: code => {
            root.actionExitCode = code;
            root.actionExited = true;
            root.finishAction();
        }
    }
}
