pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Clavis.Files
import Clavis.Niri
import qs.Common
import qs.Services
import "../Common/functions/DockModel.js" as DockModel

Singleton {
    id: root

    readonly property string filePath: Paths.configHome + "/dock.json"
    readonly property string dragMimeType: "application/x-clavis-dock"
    readonly property bool supportsThumbnails: WindowPreviewService.supported
    readonly property bool showThumbnails: root._options.showThumbnails
    readonly property int previewSize: root._options.previewSize
    readonly property bool supportsMinimize: Niri.supportsMinimize
    readonly property bool supportsMinimizeEffects: Niri.minimizeEffects.indexOf("scale") >= 0
                                                    && Niri.minimizeEffects.indexOf("genie") >= 0
    property alias model: entries
    readonly property var pinnedEntries: root._pinned
    readonly property int pinnedAppCount: root._pinned.filter(entry => !DockModel.isFile(entry)).length
    readonly property int fileStartIndex: {
        const revision = root._revision;
        for (let i = 0; i < entries.count; ++i)
            if (DockModel.isFile(entries.get(i)) || entries.get(i).kind === "trash")
                return i;
        return entries.count;
    }
    property string fileError: ""
    function pinIndexForSlot(index, kind) {
        return kind === "file" || kind === "folder" ? Math.max(root.pinnedAppCount, Math.min(root._pinned.length,
                                                                                             root.pinnedAppCount
                                                                                             + index - root.fileStartIndex)) :
                                                      Math.min(root.pinnedAppCount, index);
    }
    function fileRow(pin) {
        const info = DesktopFiles.info(pin.url);
        return {
            key: DockModel.pinnedKey(pin),
            kind: pin.kind,
            desktopId: "",
            name: info.name || pin.url,
            icon: !info.available && pin.kind === "folder" ? "folder" : info.icon || "text-x-generic",
            symbol: "",
            pinned: true,
            windowCount: 0,
            focused: false,
            launching: false,
            available: !!info.available,
            url: pin.url,
            view: pin.view || "fan",
            sort: pin.sort || "name",
            display: pin.display || "folder"
        };
    }
    function folderOption(key, name, value) {
        const allowed = {
            view: ["fan", "grid", "list"],
            sort: ["name", "modified", "created", "kind", "size"],
            display: ["folder", "stack"]
        };
        if (!allowed[name] || allowed[name].indexOf(value) < 0)
            return false;
        const next = root._pinned.map(entry => DockModel.pinnedKey(entry) === key && entry.kind === "folder"
                                               ? Object.assign({}, entry, {
                                                                   [name]: value
                                                               }) : entry);
        return root.commitPinned(next);
    }
    readonly property int revision: root._revision
    readonly property bool enabled: root._options.enabled
    readonly property string position: root._options.position
    readonly property int iconSize: root._options.iconSize
    readonly property bool magnification: root._options.magnification
    readonly property real magnificationScale: root._options.magnificationScale
    readonly property bool autoHide: root._options.autoHide
    readonly property bool launchBounce: root._options.launchBounce
    readonly property bool showIndicators: root._options.showIndicators
    readonly property bool showRecent: root._options.showRecent
    readonly property bool contextPinning: root._options.contextPinning
    property bool externalDragActive: false
    property bool fileDragActive: false
    function finishFileDrag(operation) {
        root.externalDragActive = false;
        root.fileDragActive = false;
        if (operation)
            operation();
    }
    property bool ready: false
    property bool writable: false
    property string configError: ""
    property bool _storeReady: false
    property var _options: DockModel.defaults()
    property var _pinned: [
        {
            kind: "app",
            desktopId: "org.clavis.Settings"
        }
    ]
    property var _windowsByKey: ({})
    property var _focusOrder: ({})
    property var _pendingLaunches: ({})
    property int _focusSerial: 0
    property string _focusedWindowId: ""
    property int _revision: 0
    readonly property var _dataRoots: [Paths.xdgDataHome].concat(String(Quickshell.env("XDG_DATA_DIRS")
                                                                        || "/usr/local/share:/usr/share").split(
                                                                     ":").filter(path => path.startsWith(
                                                                                             "/")))

    signal activated(string key)

    ListModel {
        id: entries
    }

    function rowIndex(key) {
        for (let index = 0; index < entries.count; index++) {
            if (entries.get(index).key === key)
                return index;
        }
        return -1;
    }

    function entryFor(key) {
        const index = root.rowIndex(key);
        return index < 0 ? null : entries.get(index);
    }

    function windowsFor(key) {
        return (root._windowsByKey[key] || []).slice();
    }

    function appRow(key, application, windows, pinned) {
        const first = windows.length ? windows[0] : null;
        const id = application ? DockModel.desktopId(application.id) : key.startsWith("app:") ? key.slice(4) :
                                                                                                "";
        return {
            key: key,
            kind: "app",
            desktopId: id,
            name: String(application ? application.name || application.id : first ? first.appName || first.appId
                                                                                    || first.title : id),
            icon: application ? application.icon : first ? first.iconPath : "",
            symbol: String(application && application.symbol || ""),
            pinned: pinned,
            windowCount: windows.length,
            focused: windows.some(window => window.isFocused),
            launching: !!root._pendingLaunches[key],
            available: !!application || windows.length > 0
        };
    }

    function rebuild() {
        const applications = ApplicationService.launcherApplications.filter(application =>
        !application.dragOnly);
        const windows = Niri.connected ? Niri.searchWindows("") : [];
        const focusOrder = Object.create(null);
        for (const window of windows)
            focusOrder[window.id] = root._focusOrder[window.id] || 0;
        const focused = windows.find(window => window.isFocused);
        if (focused && String(focused.id) !== root._focusedWindowId)
            focusOrder[focused.id] = ++root._focusSerial;
        root._focusedWindowId = focused ? String(focused.id) : "";
        root._focusOrder = focusOrder;
        const groups = DockModel.groupWindows(windows, applications, focusOrder);
        const pending = DockModel.pendingLaunches(root._pendingLaunches, groups, Date.now());
        root._pendingLaunches = pending;
        const rows = [];
        const used = new Set();
        const byKey = Object.create(null);
        for (const key of Object.keys(groups))
            byKey[key] = groups[key].windows;
        root._windowsByKey = byKey;
        for (const pinned of root._pinned.filter(entry => !DockModel.isFile(entry))) {
            const key = DockModel.pinnedKey(pinned);
            used.add(key);
            if (DockModel.isSpacer(pinned)) {
                rows.push({
                              key: key,
                              kind: pinned.kind,
                              desktopId: "",
                              name: pinned.kind === "small-spacer" ? qsTranslate("ApplicationService",
                                                                                 "Small Space") : qsTranslate(
                                                                         "ApplicationService", "Space"),
                              icon: "",
                              symbol: "",
                              pinned: true,
                              windowCount: 0,
                              focused: false,
                              launching: false,
                              available: true
                          });
            } else {
                rows.push(root.appRow(key, ApplicationService.findById(pinned.desktopId), byKey[key] || [],
                                      true));
            }
        }
        // Existing running applications keep their slots across focus/title changes.
        const running = Object.keys(groups).filter(key => !used.has(key));
        running.sort((left, right) => {
            const leftIndex = root.rowIndex(left);
            const rightIndex = root.rowIndex(right);
            return (leftIndex < 0 ? Number.MAX_SAFE_INTEGER : leftIndex) - (rightIndex < 0
                                                                            ? Number.MAX_SAFE_INTEGER :
                                                                              rightIndex) || Number(
                        groups[left].windows[0].id) - Number(groups[right].windows[0].id);
        });
        for (const key of running) {
            rows.push(root.appRow(key, groups[key].application, groups[key].windows, false));
            used.add(key);
        }
        if (root.showRecent) {
            for (const id of DockModel.recentIds(SpotlightAppUsage.records, applications, used, 3)) {
                const key = "app:" + id;
                rows.push(root.appRow(key, ApplicationService.findById(id), [], false));
                used.add(key);
            }
        }
        // Keep a submitted launch visible until it opens or its timeout expires,
        // including launches from a recent slot while recent apps are hidden.
        for (const key of Object.keys(pending)) {
            if (!used.has(key))
                rows.push(root.appRow(key, ApplicationService.findById(key.slice(4)), [], false));
        }
        for (const pin of root._pinned.filter(DockModel.isFile))
            rows.push(root.fileRow(pin));
        rows.push({
                      key: "trash",
                      kind: "trash",
                      desktopId: "",
                      name: qsTr("Trash"),
                      icon: DesktopFiles.trashCount > 0 ? "user-trash-full" : "user-trash",
                      symbol: "",
                      pinned: false,
                      windowCount: 0,
                      focused: false,
                      launching: false,
                      available: true
                  });
        DockModel.reconcile(entries, rows);
        root._revision++;
        launchTimeout.running = Object.keys(pending).length > 0;
    }

    function activate(key, outputName) {
        const entry = root.entryFor(key);
        if (entry && (DockModel.isFile(entry) || entry.kind === "trash")) {
            if (entry.kind !== "trash" && !DesktopFiles.info(entry.url).available) {
                root.fileError = qsTr("This file or folder is unavailable.");
                return false;
            }
            return ApplicationService.openUrl(entry.kind === "trash" ? "trash:///" : entry.url);
        }
        const windows = root.windowsFor(key);
        const choice = DockModel.activation(windows, root.supportsMinimize);
        const success = choice.action === "launch" ? root.launch(key) : choice.action === "minimize"
                                                     ? root.minimizeWindow(choice.id) : root.focusWindow(
                                                           choice.id, outputName);
        if (success)
            root.activated(key);
        return success;
    }

    function launch(key) {
        const entry = root.entryFor(key);
        if (!entry || !entry.desktopId)
            return false;
        if (root._pendingLaunches[key] && root._pendingLaunches[key].deadline > Date.now())
            return true;
        const desktopId = entry.desktopId;
        const initialWindows = root.windowsFor(key).map(window => String(window.id));
        if (!SpotlightAppUsage.launch(desktopId))
            return false;
        // Settings is a shell window and opens synchronously through its service.
        if (desktopId !== ApplicationService.settingsApplication.id) {
            const next = Object.assign({}, root._pendingLaunches);
            next[key] = {
                deadline: Date.now() + 12000,
                windowIds: initialWindows
            };
            root._pendingLaunches = next;
        }
        root.rebuild();
        return true;
    }

    function focusWindow(id, outputName) {
        if (!Niri.connected || WindowPreviewService.suspended)
            return false;
        const window = Niri.windowById(id);
        if (!window || !window.id)
            return false;
        return window.isMinimized ? Niri.restoreWindow(id, String(outputName || "")) : Niri.focusWindow(id);
    }

    function minimizeWindow(id) {
        if (!root.supportsMinimize || WindowPreviewService.suspended)
            return false;
        const window = Niri.windowById(id);
        if (!window || !window.id || window.isMinimized)
            return false;
        return WindowPreviewService.snapshot(id, () => {
            const current = Niri.windowById(id);
            if (root.supportsMinimize && current && current.id && !current.isMinimized)
                Niri.minimizeWindow(id);
        });
    }

    function closeWindow(id) {
        return Niri.connected && Niri.closeWindow(id);
    }

    function setOption(name, value) {
        const normalized = DockModel.option(name, value);
        if (!root.ready || normalized === undefined)
            return false;
        if (root._options[name] === normalized)
            return true;
        const next = Object.assign({}, root._options);
        next[name] = normalized;
        root._options = next;
        root.rebuild();
        root.save();
        return true;
    }

    function commitPinned(next) {
        if (!root.ready || next.length > 128)
            return false;
        root._pinned = DockModel.groupPins(next);
        DesktopFiles.watchUrls(root._pinned.filter(DockModel.isFile).map(entry => entry.url));
        root.rebuild();
        root.save();
        return true;
    }

    function pin(identifier, index) {
        const application = ApplicationService.findById(identifier);
        if (!application || application.dragOnly)
            return false;
        const id = DockModel.desktopId(application.id);
        const key = "app:" + id;
        if (root._pinned.some(entry => DockModel.pinnedKey(entry) === key))
            return index === undefined || index < 0 ? true : root.movePinned(key, index);
        const next = root._pinned.slice();
        next.splice(DockModel.insertionIndex(index, next.length), 0, {
                        kind: "app",
                        desktopId: id
                    });
        return root.commitPinned(next);
    }

    function unpin(key) {
        const next = root._pinned.filter(entry => DockModel.pinnedKey(entry) !== key);
        return next.length !== root._pinned.length && root.commitPinned(next);
    }

    function movePinned(key, index) {
        const next = DockModel.movePinned(root._pinned, key, index);
        return next !== null && root.commitPinned(next);
    }

    function dropEntries(mimeText, urls) {
        if (mimeText) {
            const payload = DockModel.dropPayload(String(mimeText));
            const application = payload && payload.kind === "app" ? ApplicationService.findById(
                                                                        payload.desktopId) : null;
            if (!payload || (payload.kind === "app" && (!application || application.dragOnly)))
                return [];
            return [payload];
        }
        const result = [];
        const seen = new Set();
        for (const url of Array.from(urls || [])) {
            const info = DesktopFiles.info(url);
            if (!info.url || !info.available && !info.isLink)
                return [];
            const id = DockModel.desktopIdForPath(info.path, root._dataRoots);
            const entry = id && ApplicationService.findById(id) ? {
                                                                      kind: "app",
                                                                      desktopId: id
                                                                  } : {
                kind: info.isDirectory ? "folder" : "file",
                url: info.url
            };
            const key = DockModel.pinnedKey(entry);
            if (!seen.has(key)) {
                seen.add(key);
                result.push(entry);
            }
        }
        return result;
    }

    function canDrop(mimeText, urls) {
        return root.ready && root.dropEntries(mimeText, urls).length > 0;
    }

    function acceptDrop(mimeText, urls, index) {
        const dropped = root.dropEntries(mimeText, urls);
        if (!root.ready || !dropped.length)
            return false;
        const incoming = dropped.map(entry => DockModel.isSpacer(entry) ? {
                                                                              kind: entry.kind,
                                                                              id: Date.now().toString(36)
                                                                                  + "_" + Math.random(
                                                                                      ).toString(36).slice(2,
                                                                                                           10)
                                                                          } : entry);
        const keys = new Set(incoming.map(entry => DockModel.pinnedKey(entry)));
        const gap = DockModel.insertionIndex(index, root._pinned.length);
        let position = 0;
        for (let before = 0; before < gap; ++before) {
            if (!keys.has(DockModel.pinnedKey(root._pinned[before])))
                position++;
        }
        const next = root._pinned.filter(entry => !keys.has(DockModel.pinnedKey(entry)));
        next.splice(position, 0, ...incoming);
        // Validate the whole operation before publishing/saving, so a large
        // drop never partially pins a selection then reports failure.
        return root.commitPinned(next);
    }

    function save() {
        if (!root.ready || !root.writable)
            return;
        configFile.setText(JSON.stringify({
                                              schemaVersion: 1,
                                              options: root._options,
                                              pinned: root._pinned
                                          }, null, 2));
    }

    function loaded(config, canWrite, error) {
        if (config) {
            root._options = config.options;
            root._pinned = config.pinned;
        }
        root.writable = canWrite;
        root.configError = error;
        root.ready = true;
        DesktopFiles.watchUrls(root._pinned.filter(DockModel.isFile).map(entry => entry.url));
        root.rebuild();
    }

    Connections {
        target: DesktopFiles
        function onTrashChanged() {
            if (root.ready)
                root.rebuild();
        }
        function onFilesChanged() {
            if (root.ready)
                root.rebuild();
        }
        function onFinished(action, succeeded, errors) {
            if (errors.length)
                root.fileError = (succeeded > 0 ? qsTr("Some files could not be processed.") : qsTr(
                                                      "The file operation failed.")) + "\n" + errors.join(
                            "\n");
        }
    }
    Process {
        command: ["mkdir", "-p", Paths.configHome]
        running: true
        onExited: exitCode => {
            if (exitCode === 0)
                root._storeReady = true;
            else
                root.loaded(null, false, qsTr(
                                "Dock settings cannot be saved because the configuration directory is unavailable."));
        }
    }

    FileView {
        id: configFile
        path: root._storeReady ? root.filePath : ""
        blockWrites: true
        atomicWrites: true
        watchChanges: true
        onFileChanged: {
            root.writable = false;
            configFile.reload();
        }
        onLoaded: {
            const config = DockModel.decodeConfig(configFile.text());
            root.loaded(config, config !== null, config === null ? qsTr(
                                                                       "Dock settings could not be read. The existing file is preserved; changes apply to this session only.") :
                                                                   "");
        }
        onLoadFailed: error => {
            if (!root._storeReady)
                return;
            const missing = error === FileViewError.FileNotFound;
            root.loaded(null, missing, missing ? "" : qsTr(
                                                     "Dock settings could not be opened. Changes apply to this session only."));
        }
        onSaveFailed: error => {
            root.writable = false;
            root.configError = qsTr("Dock settings could not be saved. Changes apply to this session only.");
            console.warn("DockService: cannot save settings:", error);
        }
    }

    Timer {
        id: launchTimeout
        interval: 500
        repeat: true
        onTriggered: root.rebuild()
    }

    Connections {
        target: Niri
        function onWindowsChanged() {
            root.rebuild();
        }
        function onFocusedWindowChanged() {
            root.rebuild();
        }
        function onConnectedChanged() {
            root.rebuild();
        }
    }

    Connections {
        target: ApplicationService
        function onLauncherApplicationsChanged() {
            root.rebuild();
        }
    }

    Connections {
        target: SpotlightAppUsage
        function onRecordsChanged() {
            root.rebuild();
        }
    }

    Component.onCompleted: root.rebuild()
}
