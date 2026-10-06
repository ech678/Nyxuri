pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs.app.services
import qs.app

Singleton {
    id: root

    readonly property string socketPath: Quickshell.env("NIRI_SOCKET")
    readonly property bool isNiri: socketPath.length > 0
    property bool connected: false
    readonly property bool actionReady: requestSocket.connected
    // Public reconnection visibility for the shell control plane (R11); the
    // backoff timer itself stays private.
    readonly property bool reconnecting: reconnectTimer.running

    // Workspaces
    property var workspacesMap: ({})
    property var allWorkspaces: []
    property int focusedWorkspaceIndex: 0
    property string focusedWorkspaceId: ""
    property var currentOutputWorkspaces: []
    property string currentOutput: ""
    property var focusedWorkspace: focusedWorkspaceIndex >= 0 && focusedWorkspaceIndex < allWorkspaces.length
                                   ? allWorkspaces[focusedWorkspaceIndex] : null

    ListModel {
        id: workspacesModel
    }
    readonly property alias workspaces: workspacesModel

    // Outputs
    property var outputs: ({
                               count: 0
                           })
    property var displayScales: ({})
    property int _fetchOutputsGen: 0

    // Windows
    property var windows: []
    property var mruWindowIds: []
    property var activeWindow: null
    readonly property alias focusedWindow: root.activeWindow

    // Overview & Capabilities
    property bool inOverview: false
    readonly property bool supportsMinimize: false
    readonly property bool supportsMinimizeAnimation: false
    readonly property var minimizeEffects: []

    // Config load status
    property bool configLoaded: false
    property bool configLoadFailed: false
    property string configError: ""

    // Keyboard layouts
    property int currentKeyboardLayoutIndex: 0
    property var keyboardLayoutNames: []
    readonly property bool hasMultipleKeyboardLayouts: keyboardLayoutNames.length > 1

    // Internal state
    property int _reconnectAttempt: 0
    property bool _windowsDirty: false
    property var _pendingWindows: []
    property bool _windowOrderDirty: false
    property var _latestFocusedWindowId: null

    readonly property var liveWindows: _windowsDirty ? _pendingWindows : windows

    // Signals
    signal windowUrgentChanged
    signal windowOrderChanged
    signal windowFocusRequested
    signal configLoadFinished(bool ok, string error)
    signal overviewChanged
    signal keyboardLayoutChanged

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
            console.warn("NiriService: send error:", e);
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

        stdout: StdioCollector {
            id: fetchOutputsCollector
            onStreamFinished: {
                try {
                    const data = JSON.parse(fetchOutputsCollector.text);
                    root._applyOutputs(data);
                } catch (e) {
                    console.warn("NiriService: Failed to parse outputs JSON:", e);
                }
            }
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

        // Display scales
        const scales = {};
        for (const outputName in outputsData) {
            const out = outputsData[outputName];
            if (out.logical && out.logical.scale !== undefined) {
                scales[outputName] = out.logical.scale;
            }
        }
        root.displayScales = scales;

        // Current output fallback
        const outputNames = Object.keys(outputsData || {});
        let nextCurrentOutput = "";
        if (focusedWorkspaceIndex >= 0 && focusedWorkspaceIndex < allWorkspaces.length) {
            nextCurrentOutput = allWorkspaces[focusedWorkspaceIndex]?.output || "";
        }
        if ((!nextCurrentOutput || outputsData[nextCurrentOutput] === undefined) && outputNames.length > 0) {
            nextCurrentOutput = outputNames[0];
        }
        if (root.currentOutput !== nextCurrentOutput) {
            root.currentOutput = nextCurrentOutput;
        }

        updateCurrentOutputWorkspaces();
        if (windows.length > 0) {
            windows = sortWindowsByLayout(windows);
        }
        root.windowOrderChanged();
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
            enabled: !out.disabled,
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
                const orderChanged = root._windowOrderDirty;
                root.windows = nextWindows;
                const nextActive = nextWindows.find(w => w.isFocused || w.is_focused) || null;
                if (root.activeWindow !== nextActive) {
                    root.activeWindow = nextActive;
                    root.focusedWindowChanged();
                }
                root._windowsDirty = false;
                root._windowOrderDirty = false;
                root.windowsChanged();
                if (orderChanged) {
                    root.windowOrderChanged();
                }
            }
        }
    }

    function scheduleWindowsUpdate(newWindowsList) {
        const enriched = (newWindowsList || []).map(w => root._enrichWindow(w));
        const normalized = root._normalizeWindowFocus(enriched);
        root._windowOrderDirty = root._windowOrderDirty || root._windowOrderDiffers(root._windowsDirty
                                                                                    ? root._pendingWindows :
                                                                                      root.windows,
                                                                                    normalized);
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
            isUrgent: !!rawWindow.is_urgent,
            is_urgent: !!rawWindow.is_urgent,
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

    function _windowOrderDiffers(previousWindows, nextWindows) {
        if (!Array.isArray(previousWindows) || !Array.isArray(nextWindows))
            return true;
        if (previousWindows.length !== nextWindows.length)
            return true;

        const prevMap = new Map();
        for (const w of previousWindows) {
            prevMap.set(w.id, w);
        }

        for (const w of nextWindows) {
            const prev = prevMap.get(w.id);
            if (!prev)
                return true;
            if (prev.app_id !== w.app_id || prev.workspace_id !== w.workspace_id || !!prev.is_floating !== !
                    !w.is_floating)
                return true;

            const prevPos = prev.layout?.pos_in_scrolling_layout;
            const nextPos = w.layout?.pos_in_scrolling_layout;
            const prevCol = Array.isArray(prevPos) ? prevPos[0] : undefined;
            const prevRow = Array.isArray(prevPos) ? prevPos[1] : undefined;
            const nextCol = Array.isArray(nextPos) ? nextPos[0] : undefined;
            const nextRow = Array.isArray(nextPos) ? nextPos[1] : undefined;
            if (prevCol !== nextCol || prevRow !== nextRow)
                return true;
        }

        return false;
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
        case 'KeyboardLayoutsChanged':
            handleKeyboardLayoutsChanged(event.KeyboardLayoutsChanged);
            break;
        case 'KeyboardLayoutSwitched':
            handleKeyboardLayoutSwitched(event.KeyboardLayoutSwitched);
            break;
        case 'WorkspaceUrgencyChanged':
            handleWorkspaceUrgencyChanged(event.WorkspaceUrgencyChanged);
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
                                       isFocused: ws.isFocused,
                                       is_focused: ws.is_focused,
                                       isUrgent: ws.isUrgent,
                                       is_urgent: ws.is_urgent,
                                       activeWindowId: ws.activeWindowId || 0,
                                       active_window_id: ws.active_window_id || 0,
                                       windowCount: ws.windowCount || 0,
                                       tiledWindowCount: ws.tiledWindowCount || 0,
                                       tiledColumnCount: ws.tiledColumnCount || 0
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
            updatedWs.isUrgent = !!ws.is_urgent;
            updatedWs.activeWindowId = ws.active_window_id || (oldWs ? oldWs.activeWindowId : 0);
            newWorkspaces[ws.id] = updatedWs;
        }

        root.workspacesMap = newWorkspaces;
        const sorted = Object.values(newWorkspaces).sort((a, b) => a.idx - b.idx);
        root.allWorkspaces = sorted;
        _syncWorkspacesModel(sorted);

        focusedWorkspaceIndex = sorted.findIndex(w => w.isFocused || w.is_focused);
        if (focusedWorkspaceIndex >= 0) {
            const focusedWs = sorted[focusedWorkspaceIndex];
            focusedWorkspaceId = String(focusedWs.id);
            currentOutput = focusedWs.output || "";
        } else {
            focusedWorkspaceIndex = 0;
            focusedWorkspaceId = "";
        }

        updateCurrentOutputWorkspaces();
        root.windowOrderChanged();
        root.workspacesChanged();
        root.focusedWorkspaceChanged();
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
        root.allWorkspaces = sorted;
        _syncWorkspacesModel(sorted);

        focusedWorkspaceIndex = sorted.findIndex(w => w.isFocused || w.is_focused);
        if (focusedWorkspaceIndex >= 0) {
            const focusedWs = sorted[focusedWorkspaceIndex];
            focusedWorkspaceId = String(focusedWs.id);
            currentOutput = focusedWs.output || "";
        } else {
            focusedWorkspaceIndex = 0;
            focusedWorkspaceId = "";
        }

        updateCurrentOutputWorkspaces();
        root.workspacesChanged();
        root.focusedWorkspaceChanged();
    }

    function handleWindowFocusChanged(data) {
        const focusedWindowId = data.id;
        root._latestFocusedWindowId = focusedWindowId;

        if (focusedWindowId !== null && focusedWindowId !== undefined) {
            const newOrder = [];
            for (let i = 0; i < root.mruWindowIds.length; i++) {
                const id = root.mruWindowIds[i];
                if (id !== focusedWindowId)
                    newOrder.push(id);
            }
            newOrder.unshift(focusedWindowId);
            root.mruWindowIds = newOrder;
        }

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

        if (root.mruWindowIds && root.mruWindowIds.length > 0) {
            root.mruWindowIds = root.mruWindowIds.filter(id => id !== data.id);
        }
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
            root.overviewChanged();
        }
    }

    function handleConfigLoaded(data) {
        const failed = !!(data && data.failed);
        root.configLoaded = !failed;
        root.configLoadFailed = failed;
        root.configError = (failed && data && data.error) ? data.error : "";
        root.configLoadFinished(!failed, root.configError);
    }

    function handleKeyboardLayoutsChanged(data) {
        const layouts = data?.keyboard_layouts ?? data;
        const names = Array.isArray(layouts?.names) ? layouts.names : [];
        const index = Number(layouts?.current_idx ?? 0);
        root.keyboardLayoutNames = names;
        root.currentKeyboardLayoutIndex = isNaN(index) ? 0 : index;
        root.keyboardLayoutChanged();
    }

    function handleKeyboardLayoutSwitched(data) {
        root.currentKeyboardLayoutIndex = data.idx;
        root.keyboardLayoutChanged();
    }

    function handleWorkspaceUrgencyChanged(data) {
        const ws = root.workspacesMap[data.id];
        if (!ws)
            return;
        const updatedWs = Object.assign({}, ws);
        updatedWs.is_urgent = data.urgent;
        updatedWs.isUrgent = data.urgent;

        const updatedWorkspaces = {};
        for (const id in root.workspacesMap) {
            updatedWorkspaces[id] = id === String(data.id) ? updatedWs : root.workspacesMap[id];
        }
        root.workspacesMap = updatedWorkspaces;
        const sorted = Object.values(updatedWorkspaces).sort((a, b) => a.idx - b.idx);
        root.allWorkspaces = sorted;
        _syncWorkspacesModel(sorted);
        root.windowUrgentChanged();
    }

    function updateCurrentOutputWorkspaces() {
        if (!root.currentOutput) {
            root.currentOutputWorkspaces = root.allWorkspaces;
            return;
        }
        root.currentOutputWorkspaces = root.allWorkspaces.filter(w => w.output === root.currentOutput);
    }

    // Actions
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

    function focusWorkspaceByIndex(workspaceIndex) {
        return send({
                        "Action": {
                            "FocusWorkspace": {
                                "reference": {
                                    "Index": Number(workspaceIndex)
                                }
                            }
                        }
                    });
    }

    function focusWorkspaceByName(name) {
        return send({
                        "Action": {
                            "FocusWorkspace": {
                                "reference": {
                                    "Name": String(name)
                                }
                            }
                        }
                    });
    }

    function focusWindow(windowId) {
        root.windowFocusRequested();
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

    function closeFocusedWindow() {
        return send({
                        "Action": {
                            "CloseWindow": {}
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

    function moveWindowToWorkspace(windowId, workspaceIndex, focus) {
        return send({
                        "Action": {
                            "MoveWindowToWorkspace": {
                                "window_id": Number(windowId),
                                "reference": {
                                    "Index": Number(workspaceIndex)
                                },
                                "focus": focus === undefined ? false : !!focus
                            }
                        }
                    });
    }

    function moveWindowToWorkspaceById(windowId, workspaceId, focus) {
        return send({
                        "Action": {
                            "MoveWindowToWorkspace": {
                                "window_id": Number(windowId),
                                "reference": {
                                    "Id": Number(workspaceId)
                                },
                                "focus": focus === undefined ? false : !!focus
                            }
                        }
                    });
    }

    function powerOffMonitors() {
        return send({
                        "Action": {
                            "PowerOffMonitors": {}
                        }
                    });
    }

    function powerOnMonitors() {
        return send({
                        "Action": {
                            "PowerOnMonitors": {}
                        }
                    });
    }

    function quit() {
        return send({
                        "Action": {
                            "Quit": {
                                "skip_confirmation": true
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

    function focusColumnLeft() {
        return send({
                        "Action": {
                            "FocusColumnLeft": {}
                        }
                    });
    }

    function focusColumnRight() {
        return send({
                        "Action": {
                            "FocusColumnRight": {}
                        }
                    });
    }

    function focusColumnFirst() {
        return send({
                        "Action": {
                            "FocusColumnFirst": {}
                        }
                    });
    }

    function focusColumnLast() {
        return send({
                        "Action": {
                            "FocusColumnLast": {}
                        }
                    });
    }

    function moveColumnToFirst() {
        return send({
                        "Action": {
                            "MoveColumnToFirst": {}
                        }
                    });
    }

    function moveColumnToLast() {
        return send({
                        "Action": {
                            "MoveColumnToLast": {}
                        }
                    });
    }

    function maximizeColumn() {
        return send({
                        "Action": {
                            "MaximizeColumn": {}
                        }
                    });
    }

    function consumeWindowIntoColumn() {
        return send({
                        "Action": {
                            "ConsumeWindowIntoColumn": {}
                        }
                    });
    }

    function expelWindowFromColumn() {
        return send({
                        "Action": {
                            "ExpelWindowFromColumn": {}
                        }
                    });
    }

    function setColumnWidth(change) {
        return send({
                        "Action": {
                            "SetColumnWidth": change
                        }
                    });
    }

    function switchLayout() {
        return send({
                        "Action": {
                            "SwitchLayout": {
                                "layout": "Next"
                            }
                        }
                    });
    }

    function switchLayoutPrevious() {
        return send({
                        "Action": {
                            "SwitchLayout": {
                                "layout": "Prev"
                            }
                        }
                    });
    }

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

    function workspaceById(id) {
        const numId = Number(id);
        return root.allWorkspaces.find(w => Number(w.id) === numId) || null;
    }

    function workspacesForOutput(outputName) {
        if (!outputName)
            return root.allWorkspaces.slice();
        return root.allWorkspaces.filter(w => w.output === outputName);
    }

    function activeWorkspaceForOutput(outputName) {
        return root.allWorkspaces.find(w => w.output === outputName && (w.isActive || w.is_active)) || null;
    }

    function windowsForWorkspace(wsId) {
        const numId = Number(wsId);
        return root.windows.filter(w => Number(w.workspaceId || w.workspace_id) === numId);
    }

    function windowsForOutput(outputName) {
        const wsList = root.workspacesForOutput(outputName);
        const wsIds = new Set(wsList.map(w => Number(w.id)));
        return root.windows.filter(w => wsIds.has(Number(w.workspaceId || w.workspace_id)));
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

    // Foreign toplevel mapping (iNiR)
    function sortToplevels(toplevels) {
        if (!toplevels || !root.isNiri)
            return toplevels ? [...toplevels] : [];
        if (root.windows.length === 0)
            return [];

        const usedToplevels = new Set();
        const enrichedToplevels = [];

        for (const niriWindow of sortWindowsByLayout(root.windows)) {
            let bestMatch = null;
            let bestScore = -1;

            for (const toplevel of toplevels) {
                if (usedToplevels.has(toplevel))
                    continue;
                const score = matchToplevelToWindow(toplevel, niriWindow);
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = toplevel;
                    if (score === 3)
                        break;
                }
            }

            if (!bestMatch || bestScore <= 0)
                continue;

            usedToplevels.add(bestMatch);
            enrichedToplevels.push(enrichToplevel(bestMatch, niriWindow));
        }

        return enrichedToplevels;
    }

    function matchToplevelToWindow(toplevel, niriWindow) {
        if (!toplevel || !niriWindow)
            return 0;
        if (toplevel.appId !== niriWindow.app_id && toplevel.appId !== niriWindow.appId)
            return 0;

        let score = 1;
        if (niriWindow.title && toplevel.title) {
            if (toplevel.title === niriWindow.title) {
                score = 3;
            } else if (toplevel.title.includes(niriWindow.title) || niriWindow.title.includes(
                           toplevel.title)) {
                score = 2;
            }
        }
        return score;
    }

    function enrichToplevel(toplevel, niriWindow) {
        const workspace = root.workspacesMap[niriWindow.workspace_id];
        const isFocused = niriWindow.is_focused ?? (workspace && workspace.active_window_id === niriWindow.id)
              ?? false;
        const windowId = niriWindow.id;

        const enriched = {
            "appId": toplevel.appId,
            "title": toplevel.title,
            "activated": isFocused,
            "niriWindowId": windowId,
            "niriWorkspaceId": niriWindow.workspace_id,
            "_sourceKey": `niri:${windowId}`,
            "_sourceToplevel": toplevel,
            "activate": function () {
                return root.focusWindow(windowId);
            },
            "close": function () {
                if (toplevel.close)
                    return toplevel.close();
                return false;
            }
        };

        for (const prop in toplevel) {
            if (!(prop in enriched)) {
                enriched[prop] = toplevel[prop];
            }
        }

        return enriched;
    }

    function filterCurrentWorkspace(toplevels, screenName) {
        let currentWorkspaceId = null;
        for (const workspace of root.allWorkspaces) {
            if (workspace.output === screenName && (workspace.is_active || workspace.isActive)) {
                currentWorkspaceId = workspace.id;
                break;
            }
        }

        if (currentWorkspaceId === null)
            return toplevels || [];

        const workspaceWindows = root.windows.filter(w => w.workspace_id === currentWorkspaceId);
        const usedToplevels = new Set();
        const result = [];

        for (const niriWindow of workspaceWindows) {
            let bestMatch = null;
            let bestScore = -1;

            for (const toplevel of (toplevels || [])) {
                if (usedToplevels.has(toplevel))
                    continue;
                const score = matchToplevelToWindow(toplevel, niriWindow);
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = toplevel;
                    if (score === 3)
                        break;
                }
            }

            if (!bestMatch || bestScore <= 0)
                continue;

            usedToplevels.add(bestMatch);
            result.push(enrichToplevel(bestMatch, niriWindow));
        }

        return result;
    }

    function hasWindowsOnActiveWorkspace(outputName) {
        const active = Object.values(root.workspacesMap || {}).filter(workspace => (workspace?.is_active || workspace
                                                                                   ?.isActive) && (
                  !outputName || workspace.output === outputName));
        if (active.length === 0 || !Array.isArray(root.windows))
            return false;
        return root.windows.some(window => !window?.is_minimized && active.some(workspace => workspace.id
                                                                                             === window.workspace_id));
    }

    function activeWorkspaceCovers(outputName) {
        const workspace = Object.values(root.workspacesMap || {}).find(entry => (entry?.is_active || entry
                                                                                ?.isActive) && entry.output
              === outputName);
        const width = Number(root.outputs?.[outputName]?.logical?.width || 0);
        if (!workspace || width <= 0 || !Array.isArray(root.windows))
            return false;
        const columns = {};
        for (const window of root.windows) {
            const pos = window?.layout?.pos_in_scrolling_layout;
            if (window?.workspace_id !== workspace.id || window.is_floating || window.is_minimized || !pos)
                continue;
            columns[pos[0]] = Math.max(columns[pos[0]] || 0, Number(window.layout?.tile_size?.[0] || 0));
        }
        return Object.values(columns).reduce((sum, col) => sum + col, 0) >= width * 0.95;
    }

    // Explicit Teardown (Lifecycle contract)
    Component.onDestruction: {
        windowsUpdateTimer.stop();
        fetchOutputsDebounce.stop();
        reconnectTimer.stop();
        eventStreamSocket.connected = false;
        requestSocket.connected = false;
        if (fetchOutputsProcess.running) {
            fetchOutputsProcess.running = false;
        }
    }
}
