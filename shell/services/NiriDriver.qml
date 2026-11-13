// Niri compositor driver (S0-5): the sole file allowed to speak niri's
// dialect — NIRI_SOCKET IPC, `niri msg` argv and the `niri --version` probe
// all live here. Everything else in the shell talks to CompositorDriver,
// which projects this driver's live surface. Zero-consumer legacy verbs
// (workspace navigation owned by compositor binds, keyboard-layout state,
// foreign-toplevel mapping) were executed with the S0-5 rename instead of
// being carried over.

pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs.services

Singleton {
    id: root

    readonly property string socketPath: Quickshell.env("NIRI_SOCKET")
    readonly property bool isNiri: socketPath.length > 0
    property bool connected: false

    // Workspaces
    property var workspacesMap: ({})
    property int _focusedWorkspaceIdx: 0
    property string currentOutput: ""

    ListModel {
        id: workspacesModel
    }
    readonly property alias workspaces: workspacesModel

    // Outputs
    property var outputs: ({
                               count: 0
                           })
    property int _fetchOutputsGen: 0

    // Windows
    property var windows: []
    property var activeWindow: null
    readonly property alias focusedWindow: root.activeWindow

    // Overview & capabilities (upstream niri: no minimize, no animation hooks)
    property bool inOverview: false
    readonly property bool supportsMinimize: false
    readonly property bool supportsMinimizeAnimation: false
    readonly property var minimizeEffects: []

    // Config load status
    property bool configLoadFailed: false
    property string configError: ""

    // Version probe (published for capability consumers such as blur)
    property string compositorVersion: ""
    property bool compositorVersionReady: false
    property string compositorVersionError: ""

    // Internal state
    property int _reconnectAttempt: 0
    property bool _windowsDirty: false
    property var _pendingWindows: []
    property var _latestFocusedWindowId: null

    // Sockets
    Socket {
        id: eventStreamSocket
        path: root.socketPath
        connected: root.isNiri

        onConnectionStateChanged: {
            root._updateConnectionStatus();
            if (eventStreamSocket.connected) {
                root._reconnectAttempt = 0;
                root._sendRaw(eventStreamSocket, '"EventStream"');
                root.fetchOutputs();
            } else if (root.isNiri) {
                root._scheduleReconnect();
            }
        }

        parser: SplitParser {
            onRead: line => {
                try {
                    const event = JSON.parse(line);
                    root.handleNiriEvent(event);
                } catch (e) {
                    // Ignore malformed event stream lines
                }
            }
        }
    }

    Socket {
        id: requestSocket
        path: root.socketPath
        connected: root.isNiri

        onConnectionStateChanged: {
            root._updateConnectionStatus();
            if (!requestSocket.connected && root.isNiri) {
                root._scheduleReconnect();
            }
        }
    }

    function _updateConnectionStatus() {
        const next = eventStreamSocket.connected && requestSocket.connected;
        if (root.connected !== next) {
            root.connected = next;
        }
    }

    function _sendRaw(sock, data) {
        if (!sock || !sock.connected)
            return false;
        try {
            const json = typeof data === "string" ? data : JSON.stringify(data);
            const message = json.endsWith("\n") ? json : json + "\n";
            sock.write(message);
            sock.flush();
            return true;
        } catch (e) {
            console.warn("NiriDriver: send error:", e);
            return false;
        }
    }

    function send(request) {
        if (!root.isNiri || !requestSocket.connected)
            return false;
        return root._sendRaw(requestSocket, request);
    }

    Timer {
        id: reconnectTimer
        interval: 500
        repeat: false
        onTriggered: {
            if (!root.isNiri)
                return;
            eventStreamSocket.connected = false;
            requestSocket.connected = false;
            Qt.callLater(() => {
                if (root.isNiri) {
                    eventStreamSocket.connected = true;
                    requestSocket.connected = true;
                }
            });
        }
    }

    function _scheduleReconnect() {
        if (reconnectTimer.running || !root.isNiri)
            return;
        const pow = Math.min(root._reconnectAttempt, 6);
        const base = Math.min(400 * Math.pow(2, pow), 10000);
        const jitter = Math.floor(Math.random() * (base / 4));
        reconnectTimer.interval = base + jitter;
        reconnectTimer.restart();
        root._reconnectAttempt++;
    }

    // Recovery entry for the shell control plane: resets the backoff and
    // cycles any dead socket. Idempotent when both sockets are healthy.
    readonly property bool reconnecting: reconnectTimer.running

    function reconnect() {
        if (!root.isNiri)
            return false;
        root._reconnectAttempt = 0;
        if (eventStreamSocket.connected && requestSocket.connected)
            return true;
        if (!reconnectTimer.running)
            root._scheduleReconnect();
        return true;
    }

    // Process: Fetch outputs
    Process {
        id: fetchOutputsProcess
        command: ["niri", "msg", "-j", "outputs"]

        onRunningChanged: {
            if (running)
                fetchOutputsWatchdog.restart();
            else
                fetchOutputsWatchdog.stop();
        }

        stdout: StdioCollector {
            id: fetchOutputsCollector
            onStreamFinished: {
                const text = String(fetchOutputsCollector.text || "");
                if (text.length > 262144) {
                    console.warn("NiriDriver: outputs response exceeded 256 KiB");
                    root.compositorVersionError = "outputs response too large";
                    return;
                }
                try {
                    const data = JSON.parse(text);
                    root._applyOutputs(data);
                } catch (e) {
                    console.warn("NiriDriver: Failed to parse outputs JSON:", e);
                }
            }
        }
    }

    Timer {
        id: fetchOutputsWatchdog
        interval: 3000
        repeat: false
        onTriggered: {
            if (!fetchOutputsProcess.running)
                return;
            console.warn("NiriDriver: outputs query timed out");
            fetchOutputsProcess.running = false;
            root.fetchOutputs();
        }
    }

    Timer {
        id: fetchOutputsDebounce
        interval: 200
        repeat: false
        onTriggered: {
            if (root.isNiri && !fetchOutputsProcess.running) {
                root._fetchOutputsGen++;
                fetchOutputsProcess.running = true;
            }
        }
    }

    function fetchOutputs() {
        if (!root.isNiri)
            return;
        fetchOutputsDebounce.restart();
    }

    function refreshOutputs() {
        fetchOutputs();
    }

    function _applyOutputs(outputsData) {
        const nextOutputs = Object.assign({}, outputsData);
        nextOutputs.count = Object.keys(outputsData || {}).length;
        root.outputs = nextOutputs;

        // Current output fallback: the focused workspace's output if known
        const outputNames = Object.keys(outputsData || {});
        let nextCurrentOutput = "";
        for (const ws of Object.values(root.workspacesMap || {})) {
            if (ws.is_focused && ws.output) {
                nextCurrentOutput = ws.output;
                break;
            }
        }
        if ((!nextCurrentOutput || outputsData[nextCurrentOutput] === undefined) && outputNames.length > 0) {
            nextCurrentOutput = outputNames[0];
        }
        if (root.currentOutput !== nextCurrentOutput) {
            root.currentOutput = nextCurrentOutput;
        }

        if (windows.length > 0) {
            windows = sortWindowsByLayout(windows);
        }
        root.outputsChanged();
    }

    function outputSnapshot() {
        const result = [];
        if (!root.outputs)
            return result;
        for (const name in root.outputs) {
            if (name === "count")
                continue;
            const out = root.outputs[name];
            if (!out || typeof out !== "object")
                continue;
            const logical = out.logical || {};
            const modes = out.modes || [];
            const curModeIdx = out.current_mode;
            let curModeStr = "";
            if (curModeIdx !== undefined && curModeIdx !== null && modes[curModeIdx]) {
                const m = modes[curModeIdx];
                curModeStr = m.width + "x" + m.height + "@" + (Number(m.refresh_rate || 0) / 1000).toFixed(3);
            }
            result.push({
                            name: name,
                            make: out.make || "Unknown",
                            model: out.model || "Unknown",
                            serial: out.serial || "Unknown",
                            logicalX: logical.x !== undefined ? logical.x : 0,
                            logicalY: logical.y !== undefined ? logical.y : 0,
                            logicalWidth: logical.width !== undefined ? logical.width : 0,
                            logicalHeight: logical.height !== undefined ? logical.height : 0,
                            scale: logical.scale !== undefined ? logical.scale : 1.0,
                            transform: logical.transform || "normal",
                            currentMode: curModeStr,
                            modes: modes.map(m => ({
                                width: m.width,
                                height: m.height,
                                refreshMilliHz: m.refresh_rate,
                                preferred: !!m.is_preferred
                            })),
            enabled: !!out.logical,
            vrrSupported: !!out.vrr_supported,
            vrrEnabled: !!out.vrr_enabled
        });
    }
    return result;
}

    // Windows update batching
    Timer {
        id: windowsUpdateTimer
        interval: 50
        repeat: false
        onTriggered: {
            if (root._windowsDirty) {
                const nextWindows = root.sortWindowsByLayout(root._pendingWindows);
                root.windows = nextWindows;
                const nextActive = nextWindows.find(w => w.isFocused || w.is_focused) || null;
                if (root.activeWindow !== nextActive) {
                    root.activeWindow = nextActive;
                }
                root._windowsDirty = false;
                root.windowsChanged();
            }
        }
    }

    function scheduleWindowsUpdate(newWindowsList) {
        const enriched = (newWindowsList || []).map(w => root._enrichWindow(w));
        const normalized = root._normalizeWindowFocus(enriched);
        root._pendingWindows = normalized;
        root._windowsDirty = true;
        if (!windowsUpdateTimer.running) {
            windowsUpdateTimer.restart();
        }
    }

    function _enrichWindow(rawWindow) {
        if (!rawWindow)
            return null;
        const appId = rawWindow.app_id || rawWindow.appId || "";
        const app = ApplicationService ? ApplicationService.findById(appId) : null;
        const icon = app && app.icon ? ApplicationService.iconSource(app.icon) : (ApplicationService
                                                                                  ? ApplicationService.iconSource(
                                                                                        appId) : "");
        const appName = app ? (app.name || app.id) : (appId || rawWindow.title || "");
        const pos = rawWindow.layout?.pos_in_scrolling_layout;
        const col = (Array.isArray(pos) && pos.length >= 1) ? pos[0] : 999999;
        const row = (Array.isArray(pos) && pos.length >= 2) ? pos[1] : 999999;

        return {
            id: rawWindow.id,
            title: rawWindow.title || "",
            appId: appId,
            app_id: appId,
            appName: appName,
            iconPath: icon,
            workspaceId: rawWindow.workspace_id,
            workspace_id: rawWindow.workspace_id,
            isFocused: !!rawWindow.is_focused,
            is_focused: !!rawWindow.is_focused,
            isFloating: !!rawWindow.is_floating,
            is_floating: !!rawWindow.is_floating,
            isMinimized: !!rawWindow.is_minimized,
            is_minimized: !!rawWindow.is_minimized,
            layout: rawWindow.layout || {},
            layoutColumn: col,
            layoutRow: row,
            hasLayoutPosition: Array.isArray(pos) && pos.length >= 2
        };
    }

    function _normalizeWindowFocus(windowList) {
        if (!Array.isArray(windowList) || root._latestFocusedWindowId === undefined)
            return windowList;

        let changed = false;
        const normalized = windowList.map(window => {
            const shouldBeFocused = root._latestFocusedWindowId !== null && window.id
                  === root._latestFocusedWindowId;
            if (window.isFocused === shouldBeFocused)
                return window;
            changed = true;
            const copy = Object.assign({}, window);
            copy.isFocused = shouldBeFocused;
            copy.is_focused = shouldBeFocused;
            return copy;
        });
        return changed ? normalized : windowList;
    }

    function sortWindowsByLayout(windowList) {
        const enriched = (windowList || []).map(w => {
            const ws = root.workspacesMap[w.workspace_id];
            if (!ws) {
                return {
                    window: w,
                    outputX: 999999,
                    outputY: 999999,
                    wsIdx: 999999,
                    col: 999999,
                    row: 999999
                };
            }

            const outputInfo = root.outputs[ws.output];
            const outputX = (outputInfo && outputInfo.logical) ? outputInfo.logical.x : 999999;
            const outputY = (outputInfo && outputInfo.logical) ? outputInfo.logical.y : 999999;
            const pos = w.layout?.pos_in_scrolling_layout;
            const col = (pos && pos.length >= 2) ? pos[0] : 999999;
            const row = (pos && pos.length >= 2) ? pos[1] : 999999;

            return {
                window: w,
                outputX: outputX,
                outputY: outputY,
                wsIdx: ws.idx !== undefined ? ws.idx : 999999,
                col: col,
                row: row
            };
        });

        enriched.sort((a, b) => {
            if (a.outputX !== b.outputX)
                return a.outputX - b.outputX;
            if (a.outputY !== b.outputY)
                return a.outputY - b.outputY;
            if (a.wsIdx !== b.wsIdx)
                return a.wsIdx - b.wsIdx;
            if (a.col !== b.col)
                return a.col - b.col;
            if (a.row !== b.row)
                return a.row - b.row;
            return Number(a.window.id) - Number(b.window.id);
        });

        return enriched.map(e => e.window);
    }

    // Event Stream dispatch
    function handleNiriEvent(event) {
        const eventType = Object.keys(event)[0];
        switch (eventType) {
        case 'WorkspacesChanged':
            handleWorkspacesChanged(event.WorkspacesChanged);
            break;
        case 'WorkspaceActivated':
            handleWorkspaceActivated(event.WorkspaceActivated);
            break;
        case 'WorkspaceActiveWindowChanged':
            handleWorkspaceActiveWindowChanged(event.WorkspaceActiveWindowChanged);
            break;
        case 'WindowFocusChanged':
            handleWindowFocusChanged(event.WindowFocusChanged);
            break;
        case 'WindowsChanged':
            handleWindowsChanged(event.WindowsChanged);
            break;
        case 'WindowClosed':
            handleWindowClosed(event.WindowClosed);
            break;
        case 'WindowOpenedOrChanged':
            handleWindowOpenedOrChanged(event.WindowOpenedOrChanged);
            break;
        case 'WindowLayoutsChanged':
            handleWindowLayoutsChanged(event.WindowLayoutsChanged);
            break;
        case 'OutputsChanged':
            handleOutputsChanged(event.OutputsChanged);
            break;
        case 'OverviewOpenedOrClosed':
            handleOverviewChanged(event.OverviewOpenedOrClosed);
            break;
        case 'ConfigLoaded':
            handleConfigLoaded(event.ConfigLoaded);
            break;
        }
    }

    function _syncWorkspacesModel(list) {
        workspacesModel.clear();
        for (const ws of list) {
            workspacesModel.append({
                                       id: ws.id,
                                       idx: ws.idx,
                                       index: ws.index,
                                       name: ws.name || "",
                                       output: ws.output || "",
                                       isActive: ws.isActive,
                                       is_active: ws.is_active,
                                       activeWindowId: ws.activeWindowId || 0,
                                       active_window_id: ws.active_window_id || 0,
                                       windowCount: ws.windowCount || 0
                                   });
        }
    }

    function handleWorkspacesChanged(data) {
        const newWorkspaces = {};
        for (const ws of (data.workspaces || [])) {
            const oldWs = root.workspacesMap[ws.id];
            const updatedWs = Object.assign({}, ws);
            updatedWs.index = ws.idx;
            updatedWs.isActive = !!ws.is_active;
            updatedWs.isFocused = !!ws.is_focused;
            updatedWs.activeWindowId = ws.active_window_id || (oldWs ? oldWs.activeWindowId : 0);
            newWorkspaces[ws.id] = updatedWs;
        }

        root.workspacesMap = newWorkspaces;
        const sorted = Object.values(newWorkspaces).sort((a, b) => a.idx - b.idx);
        _syncWorkspacesModel(sorted);

        const focused = sorted.find(w => w.isFocused || w.is_focused) || null;
        if (focused) {
            currentOutput = focused.output || "";
        }

        root.workspacesChanged();
    }

    function handleWorkspaceActivated(data) {
        const ws = root.workspacesMap[data.id];
        if (!ws)
            return;
        const output = ws.output;
        const updatedWorkspaces = {};
        let hasChanges = false;

        for (const id in root.workspacesMap) {
            const workspace = root.workspacesMap[id];
            const got_activated = workspace.id === data.id;
            const needsUpdate = (workspace.output === output) || data.focused;

            if (!needsUpdate) {
                updatedWorkspaces[id] = workspace;
                continue;
            }

            const updatedWs = Object.assign({}, workspace);
            if (workspace.output === output) {
                updatedWs.is_active = got_activated;
                updatedWs.isActive = got_activated;
            }
            if (data.focused) {
                updatedWs.is_focused = got_activated;
                updatedWs.isFocused = got_activated;
            }

            updatedWorkspaces[id] = updatedWs;
            hasChanges = true;
        }

        if (!hasChanges)
            return;
        root.workspacesMap = updatedWorkspaces;
        const sorted = Object.values(updatedWorkspaces).sort((a, b) => a.idx - b.idx);
        _syncWorkspacesModel(sorted);

        const focused = sorted.find(w => w.isFocused || w.is_focused) || null;
        if (focused) {
            currentOutput = focused.output || "";
        }

        root.workspacesChanged();
    }

    function handleWindowFocusChanged(data) {
        const focusedWindowId = data.id;
        root._latestFocusedWindowId = focusedWindowId;

        const currentList = root._windowsDirty ? root._pendingWindows : root.windows;
        scheduleWindowsUpdate(currentList);

        const focusedWindow = currentList.find(w => w.id === focusedWindowId);
        if (focusedWindow) {
            const ws = root.workspacesMap[focusedWindow.workspace_id];
            if (ws && (ws.active_window_id !== focusedWindowId || ws.activeWindowId !== focusedWindowId)) {
                const updatedWs = Object.assign({}, ws);
                updatedWs.active_window_id = focusedWindowId;
                updatedWs.activeWindowId = focusedWindowId;
                const updatedWorkspaces = {};
                for (const id in root.workspacesMap) {
                    updatedWorkspaces[id] = id === String(focusedWindow.workspace_id) ? updatedWs :
                                                                                        root.workspacesMap[id];
                }
                root.workspacesMap = updatedWorkspaces;
            }
        }
    }

    function handleWorkspaceActiveWindowChanged(data) {
        const ws = root.workspacesMap[data.workspace_id];
        if (!ws)
            return;
        const updatedWs = Object.assign({}, ws);
        updatedWs.active_window_id = data.active_window_id;
        updatedWs.activeWindowId = data.active_window_id;

        const updatedWorkspaces = {};
        for (const id in root.workspacesMap) {
            updatedWorkspaces[id] = id === String(data.workspace_id) ? updatedWs : root.workspacesMap[id];
        }
        root.workspacesMap = updatedWorkspaces;
    }

    function handleWindowsChanged(data) {
        const focused = (data.windows || []).find(w => w.is_focused === true);
        root._latestFocusedWindowId = focused ? focused.id : null;
        scheduleWindowsUpdate(data.windows || []);
    }

    function handleWindowClosed(data) {
        const currentList = _windowsDirty ? _pendingWindows : windows;
        const updatedWindows = currentList.filter(w => w.id !== data.id);
        scheduleWindowsUpdate(updatedWindows);
    }

    function handleWindowOpenedOrChanged(data) {
        if (!data.window)
            return;
        const window = data.window;
        if (window.is_focused === true)
            root._latestFocusedWindowId = window.id;
        const currentList = _windowsDirty ? _pendingWindows : windows;
        const existingIndex = currentList.findIndex(w => w.id === window.id);
        let updatedWindows;

        if (existingIndex >= 0) {
            updatedWindows = [...currentList];
            updatedWindows[existingIndex] = window;
        } else {
            updatedWindows = [...currentList, window];
        }

        scheduleWindowsUpdate(updatedWindows);
    }

    function handleWindowLayoutsChanged(data) {
        if (!data.changes)
            return;
        const currentList = _windowsDirty ? _pendingWindows : windows;
        const updatedWindows = [...currentList];
        let hasChanges = false;

        for (const change of data.changes) {
            const windowId = change[0];
            const layoutData = change[1];
            const windowIndex = updatedWindows.findIndex(w => w.id === windowId);
            if (windowIndex < 0)
                continue;

            const updatedWindow = Object.assign({}, updatedWindows[windowIndex]);
            updatedWindow.layout = layoutData;
            const pos = layoutData?.pos_in_scrolling_layout;
            if (Array.isArray(pos)) {
                updatedWindow.layoutColumn = pos[0];
                updatedWindow.layoutRow = pos[1];
                updatedWindow.hasLayoutPosition = true;
            }
            updatedWindows[windowIndex] = updatedWindow;
            hasChanges = true;
        }

        if (hasChanges) {
            scheduleWindowsUpdate(updatedWindows);
        }
    }

    function handleOutputsChanged(data) {
        fetchOutputs();
    }

    function handleOverviewChanged(data) {
        const next = !!data.is_open;
        if (root.inOverview !== next) {
            root.inOverview = next;
        }
    }

    function handleConfigLoaded(data) {
        const failed = !!(data && data.failed);
        root.configLoadFailed = failed;
        root.configError = (failed && data && data.error) ? data.error : "";
    }

    // --- Process-backed actions (argv truth lives here, nowhere else) ---

    // Managed monitor power with exit-code callback. A null callback means
    // fire-and-forget: the request must outlive the host (idle teardown), so
    // it is detached instead of riding a host-owned process.
    property var _monitorsPowerCallback: null

    function setMonitorsPower(off, callback) {
        const args = ["niri", "msg", "action", off ? "power-off-monitors" : "power-on-monitors"];
        if (!callback) {
            try {
                Quickshell.execDetached(args);
                return true;
            } catch (err) {
                console.warn("NiriDriver: monitor power request failed:", err);
                return false;
            }
        }
        if (monitorsPowerProcess.running)
            return false;
        root._monitorsPowerCallback = callback;
        monitorsPowerProcess.exec(args);
        return true;
    }

    // End the compositor session. Detached on purpose: the shell may be on
    // its way out when this fires (logout), and the request must survive it.
    function quitSession() {
        try {
            Quickshell.execDetached(["niri", "msg", "action", "quit", "--skip-confirmation"]);
            return true;
        } catch (err) {
            console.warn("NiriDriver: quit request failed:", err);
            return false;
        }
    }

    Process {
        id: monitorsPowerProcess

        onExited: exitCode => {
            const cb = root._monitorsPowerCallback;
            root._monitorsPowerCallback = null;
            if (cb)
                cb(exitCode);
        }
    }

    // Version probe: runs once when a niri session is present. Consumers
    // interpret the version (blur needs >= 26.4); the driver only reports it.
    Process {
        id: versionProcess
        command: ["niri", "--version"]
        // Armed one event-loop turn after assembly so the probe does not compete
        // with the first-frame path; consumers gate on compositorVersionReady.
        property bool armed: false
        running: root.isNiri && armed
        onRunningChanged: {
            if (running)
                versionWatchdog.restart();
            else
                versionWatchdog.stop();
        }

        stdout: StdioCollector {
            id: versionOutput
        }

        stderr: StdioCollector {
            id: versionError
        }

        onExited: exitCode => {
            if (exitCode === 0 && String(versionOutput.text || "").length > 4096) {
                root.compositorVersion = "";
                root.compositorVersionError = "version response too large";
                root.compositorVersionReady = true;
                return;
            }
            if (exitCode === 0) {
                root.compositorVersion = versionOutput.text.trim();
                root.compositorVersionError = "";
            } else {
                root.compositorVersion = "";
                root.compositorVersionError = versionError.text.trim();
            }
            root.compositorVersionReady = true;
        }
    }

    Timer {
        id: versionWatchdog
        interval: 3000
        repeat: false
        onTriggered: {
            if (!versionProcess.running)
                return;
            versionProcess.running = false;
            root.compositorVersion = "";
            root.compositorVersionError = "version probe timed out";
            root.compositorVersionReady = true;
        }
    }

    // Actions (live surface only; workspace navigation verbs belong to the
    // compositor's own binds, not to the shell)
    function toggleOverview() {
        return send({
                        "Action": {
                            "ToggleOverview": {}
                        }
                    });
    }

    function focusWorkspaceById(workspaceId) {
        return send({
                        "Action": {
                            "FocusWorkspace": {
                                "reference": {
                                    "Id": Number(workspaceId)
                                }
                            }
                        }
                    });
    }

    function focusWorkspaceUp() {
        return send({
                        "Action": {
                            "FocusWorkspaceUp": {}
                        }
                    });
    }

    function focusWorkspaceDown() {
        return send({
                        "Action": {
                            "FocusWorkspaceDown": {}
                        }
                    });
    }

    function focusWindow(windowId) {
        return send({
                        "Action": {
                            "FocusWindow": {
                                "id": Number(windowId)
                            }
                        }
                    });
    }

    function closeWindow(windowId) {
        return send({
                        "Action": {
                            "CloseWindow": {
                                "id": Number(windowId)
                            }
                        }
                    });
    }

    function minimizeWindow(windowId) {
        if (!root.supportsMinimize)
            return false;
        return send({
                        "Action": {
                            "MinimizeWindow": {
                                "id": Number(windowId)
                            }
                        }
                    });
    }

    function restoreWindow(windowId, output) {
        if (!root.supportsMinimize)
            return false;
        const payload = {
            "id": Number(windowId)
        };
        if (output)
            payload.output = String(output);
        return send({
                        "Action": {
                            "RestoreWindow": payload
                        }
                    });
    }

    // Capability stubs (upstream niri has no IPC surface for these; the
    // parallax/animation consumers degrade on these constants)
    function setFloatingParallaxOffsets(offsets) {
        return false;
    }

    function setWindowAnimationTargets(screenName, targets) {
        return false;
    }

    // Query methods
    function windowById(id) {
        const numId = Number(id);
        const list = root._windowsDirty ? root._pendingWindows : root.windows;
        return list.find(w => Number(w.id) === numId) || null;
    }

    function workspacesForOutput(outputName) {
        const all = Object.values(root.workspacesMap || {}).sort((a, b) => a.idx - b.idx);
        if (!outputName)
            return all;
        return all.filter(w => w.output === outputName);
    }

    function activeWorkspaceForOutput(outputName) {
        return Object.values(root.workspacesMap || {}).find(w => w.output === outputName && (w.isActive
                                                                                             || w.is_active))
                || null;
    }

    function windowsForWorkspace(wsId) {
        const numId = Number(wsId);
        return root.windows.filter(w => Number(w.workspaceId || w.workspace_id) === numId);
    }

    function searchWindows(query) {
        if (!root.windows || root.windows.length === 0)
            return [];
        if (!query || String(query).trim() === "")
            return root.windows.slice();
        const q = String(query).toLowerCase().trim();
        return root.windows.filter(w => {
            return (w.title && w.title.toLowerCase().includes(q)) || (w.appName && w.appName.toLowerCase().includes(
                                                                          q)) || (w.appId
                                                                                  && w.appId.toLowerCase(
                                                                                      ).includes(q));
        });
    }

    // Explicit Teardown (Lifecycle contract)
    Component.onCompleted: {
        ShellStartupService.registerQmlResource("NiriDriver", "timer", reconnectTimer);
        ShellStartupService.registerQmlResource("NiriDriver", "timer", fetchOutputsDebounce);
        ShellStartupService.registerQmlResource("NiriDriver", "timer", fetchOutputsWatchdog);
        ShellStartupService.registerQmlResource("NiriDriver", "timer", windowsUpdateTimer);
        ShellStartupService.registerQmlResource("NiriDriver", "process", fetchOutputsProcess);
        ShellStartupService.registerQmlResource("NiriDriver", "process", monitorsPowerProcess);
        ShellStartupService.registerQmlResource("NiriDriver", "process", versionProcess);
        ShellStartupService.registerQmlResource("NiriDriver", "timer", versionWatchdog);
        Qt.callLater(() => {
            versionProcess.armed = true;
        });
    }
    Component.onDestruction: {
        ShellStartupService.unregisterQmlResources("NiriDriver", [
            {"object": reconnectTimer}, {"object": fetchOutputsDebounce}, {"object": fetchOutputsWatchdog}, {"object": windowsUpdateTimer},
            {"object": fetchOutputsProcess}, {"object": monitorsPowerProcess}, {"object": versionProcess},
            {"object": versionWatchdog}
        ]);
        windowsUpdateTimer.stop();
        fetchOutputsDebounce.stop();
        fetchOutputsWatchdog.stop();
        reconnectTimer.stop();
        versionWatchdog.stop();
        eventStreamSocket.connected = false;
        requestSocket.connected = false;
        if (fetchOutputsProcess.running) {
            fetchOutputsProcess.running = false;
        }
        if (monitorsPowerProcess.running) {
            monitorsPowerProcess.running = false;
        }
        if (versionProcess.running) {
            versionProcess.running = false;
        }
    }
}
