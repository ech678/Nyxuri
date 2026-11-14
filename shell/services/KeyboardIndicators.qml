pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons
import qs.services

// Fork & Trim: iNiR services/KeyboardIndicators.qml.
//
// Kept: sysfs LED aggregation, multi-keyboard states, panel/popup split,
// layout-change popup, popup sequence for the OSD presenter.
// Dropped: the evdev daemon branch (no accel-run keyboard-lock daemon ships in
// Nyxuri) and the Hyprland singleton (KeyboardLayoutService owns the Niri
// projection). Sysfs stays the single source; the 500ms reread is the
// guaranteed event path because some LED drivers do not raise kernfs inotify.
Singleton {
    id: root

    property list<string> capsLockPaths: []
    property list<string> numLockPaths: []
    property var _capsLockStates: ({})
    property var _numLockStates: ({})
    property string _knownLayoutName: ""
    property bool _destroying: false
    property bool _numLockReliable: false
    property var _lastRawNumLockState: null

    property bool capsLock: false
    property bool numLock: false
    property bool ready: false
    readonly property bool available: root.ready
    property string popupKind: ""
    property bool popupActive: false
    property string popupText: ""
    property int popupSequence: 0

    readonly property bool showPopup: Config.options?.bar?.keyboardIndicators?.showPopup ?? true
    readonly property bool showPanel: Config.options?.bar?.keyboardIndicators?.showPanel ?? true
    readonly property bool showLayoutPopup: root.showPopup && (Config.options?.bar?.keyboardIndicators?.popup?.layout ?? true)
    readonly property bool showCapsPopup: root.showPopup && (Config.options?.bar?.keyboardIndicators?.popup?.caps ?? true)
    readonly property bool showNumPopup: root.showPopup && (Config.options?.bar?.keyboardIndicators?.popup?.num ?? false)
    readonly property bool showLayoutPanel: root.showPanel && (Config.options?.bar?.keyboardIndicators?.panel?.layout ?? true)
    readonly property bool showCapsPanel: root.showPanel && (Config.options?.bar?.keyboardIndicators?.panel?.caps ?? true)
    readonly property bool showNumPanel: root.showPanel && (Config.options?.bar?.keyboardIndicators?.panel?.num ?? false)

    readonly property bool hasMultipleLayouts: KeyboardLayoutService.hasMultipleLayouts
    readonly property string currentLayoutName: KeyboardLayoutService.currentLayoutName
    readonly property string currentLayoutCode: KeyboardLayoutService.currentLayoutCode
    readonly property string capsMaterialIcon: "keyboard_capslock"
    readonly property string numMaterialIcon: "dialpad"
    readonly property string popupMaterialIcon: root.popupKind === "layout" ? "language" : root.popupKind === "caps" ? root.capsMaterialIcon : root.numMaterialIcon
    readonly property string currentLayoutCodeInline: root.abbreviateLayoutCode(root.currentLayoutCode, " ")
    readonly property string currentLayoutCodeMultiline: root.abbreviateLayoutCode(root.currentLayoutCode, "\n")
    readonly property bool layoutVisible: root.showLayoutPanel && root.hasMultipleLayouts && root.currentLayoutCode.length > 0
    readonly property bool capsLockVisible: root.showCapsPanel && root.capsLock
    readonly property bool numLockVisible: root.showNumPanel && root.numLock
    readonly property bool hasPanelIndicators: root.layoutVisible || root.capsLockVisible || root.numLockVisible

    function abbreviateLayoutCode(fullCode, separator) {
        if (!fullCode || !fullCode.length)
            return "";
        return fullCode.split(":").map(layout => layout.split("-")[0].slice(0, 3)).join(separator);
    }

    function refreshLedPaths() {
        if (!ledDiscoveryProc.running)
            ledDiscoveryProc.running = true;
    }

    function _setCapsLockValue(nextValue, allowPopup) {
        const previousValue = root.capsLock;
        root.capsLock = nextValue;
        if (allowPopup && previousValue !== nextValue)
            root._emitLockPopup("caps", nextValue);
    }

    function _setNumLockValue(nextValue, allowPopup) {
        const previousValue = root.numLock;
        root.numLock = nextValue;
        if (allowPopup && previousValue !== nextValue)
            root._emitLockPopup("num", nextValue);
    }

    function _setPopup(kind, active, text) {
        if (!root.ready)
            return;
        if (kind === "layout" && !root.showLayoutPopup)
            return;
        if (kind === "caps" && !root.showCapsPopup)
            return;
        if (kind === "num" && !root.showNumPopup)
            return;
        root.popupKind = kind;
        root.popupActive = active;
        root.popupText = text;
        root.popupSequence += 1;
    }

    function _emitLockPopup(kind, active) {
        if (kind === "caps") {
            root._setPopup(kind, active, active ? Translation.tr("Caps Lock on") : Translation.tr("Caps Lock off"));
            return;
        }
        root._setPopup(kind, active, active ? Translation.tr("Num Lock on") : Translation.tr("Num Lock off"));
    }

    function _emitLayoutPopup() {
        if (!root.hasMultipleLayouts || !root.currentLayoutName.length)
            return;
        root._setPopup("layout", true, root.currentLayoutName);
    }

    function _hasKnownState(paths, states) {
        return paths.some(path => states[path] !== null && states[path] !== undefined);
    }

    function _setLockPaths(kind, paths) {
        const uniquePaths = [...new Set(paths)].sort();
        const previousStates = kind === "caps" ? root._capsLockStates : root._numLockStates;
        const nextStates = {};
        for (const path of uniquePaths)
            nextStates[path] = previousStates.hasOwnProperty(path) ? previousStates[path] : null;

        if (kind === "caps") {
            root.capsLockPaths = uniquePaths;
            root._capsLockStates = nextStates;
            if (!uniquePaths.length)
                root.capsLock = false;
            root._recomputeLockState(kind, false);
            return;
        }

        root.numLockPaths = uniquePaths;
        root._numLockStates = nextStates;
        if (!uniquePaths.length) {
            root._numLockReliable = false;
            root._lastRawNumLockState = null;
            root.numLock = false;
        }
        root._recomputeLockState(kind, false);
    }

    function _setLockState(kind, path, rawValue) {
        const nextValue = Number(String(rawValue).trim()) > 0;
        if (kind === "caps") {
            root._capsLockStates = Object.assign({}, root._capsLockStates, {
                [path]: nextValue
            });
            root._recomputeLockState(kind, true);
            return;
        }
        root._numLockStates = Object.assign({}, root._numLockStates, {
            [path]: nextValue
        });
        root._recomputeLockState(kind, true);
    }

    function _clearLockState(kind, path) {
        if (kind === "caps") {
            root._capsLockStates = Object.assign({}, root._capsLockStates, {
                [path]: null
            });
            root._recomputeLockState(kind, false);
            return;
        }
        root._numLockStates = Object.assign({}, root._numLockStates, {
            [path]: null
        });
        root._recomputeLockState(kind, false);
    }

    function _setNumLockRawValue(nextValue, allowPopup) {
        const previousVisibleValue = root._numLockReliable ? root.numLock : root._lastRawNumLockState;
        if (root._lastRawNumLockState === null) {
            root._lastRawNumLockState = nextValue;
            root._numLockReliable = !nextValue;
        } else if (nextValue !== root._lastRawNumLockState) {
            root._lastRawNumLockState = nextValue;
            root._numLockReliable = true;
        }
        root._setNumLockValue(root._numLockReliable ? nextValue : false, false);
        if (root._numLockReliable && allowPopup && previousVisibleValue !== null && previousVisibleValue !== root.numLock)
            root._emitLockPopup("num", root.numLock);
    }

    function _recomputeLockState(kind, allowPopup) {
        const paths = kind === "caps" ? root.capsLockPaths : root.numLockPaths;
        const states = kind === "caps" ? root._capsLockStates : root._numLockStates;
        if (paths.length > 0 && !root._hasKnownState(paths, states))
            return;
        const nextValue = paths.some(path => states[path] === true);
        if (kind === "caps") {
            root._setCapsLockValue(nextValue, allowPopup);
            return;
        }
        if (!paths.length) {
            root._numLockReliable = false;
            root._lastRawNumLockState = null;
            root.numLock = false;
            return;
        }
        root._setNumLockRawValue(nextValue, allowPopup);
    }

    function applyLedPaths(text) {
        const caps = [];
        const num = [];
        for (const rawLine of String(text || "").split("\n")) {
            const line = rawLine.trim();
            if (!line.length)
                continue;
            if (line.includes("::capslock"))
                caps.push(line);
            else if (line.includes("::numlock"))
                num.push(line);
        }
        root._setLockPaths("caps", caps);
        root._setLockPaths("num", num);
    }

    Process {
        id: ledDiscoveryProc

        command: ["find", "/sys/class/leds", "-maxdepth", "1", "(", "-name", "*::capslock", "-o", "-name", "*::numlock", ")", "-print"]
        stdout: StdioCollector {
            onStreamFinished: root.applyLedPaths(this.text)
        }
    }

    // Guaranteed event path for drivers that do not raise kernfs inotify; the
    // FileView watch above still gives instant feedback where it works.
    Timer {
        interval: 500
        running: !root._destroying && (root.capsLockPaths.length + root.numLockPaths.length) > 0
        repeat: true
        onTriggered: {
            for (let index = 0; index < capsViews.count; index += 1) {
                const view = capsViews.objectAt(index);
                if (view)
                    view.reload();
            }
            for (let index = 0; index < numViews.count; index += 1) {
                const view = numViews.objectAt(index);
                if (view)
                    view.reload();
            }
        }
    }

    Instantiator {
        id: capsViews

        model: root.capsLockPaths
        delegate: FileView {
            required property string modelData

            path: modelData + "/brightness"
            watchChanges: true
            onFileChanged: reload()
            onLoaded: root._setLockState("caps", modelData, text())
            onLoadFailed: root._clearLockState("caps", modelData)
        }
    }

    Instantiator {
        id: numViews

        model: root.numLockPaths
        delegate: FileView {
            required property string modelData

            path: modelData + "/brightness"
            watchChanges: true
            onFileChanged: reload()
            onLoaded: root._setLockState("num", modelData, text())
            onLoadFailed: root._clearLockState("num", modelData)
        }
    }

    Timer {
        interval: 8000
        running: !root._destroying
        repeat: true
        onTriggered: root.refreshLedPaths()
    }

    Timer {
        interval: 1200
        running: true
        repeat: false
        onTriggered: {
            root.ready = true;
            root._knownLayoutName = root.currentLayoutName;
        }
    }

    Connections {
        target: KeyboardLayoutService

        function onLayoutChanged() {
            if (!root.currentLayoutName.length)
                return;
            if (!root._knownLayoutName.length) {
                root._knownLayoutName = root.currentLayoutName;
                return;
            }
            if (root._knownLayoutName === root.currentLayoutName)
                return;
            root._knownLayoutName = root.currentLayoutName;
            root._emitLayoutPopup();
        }
    }

    Component.onCompleted: {
        root._knownLayoutName = root.currentLayoutName;
        root.refreshLedPaths();
    }

    Component.onDestruction: {
        root._destroying = true;
        ledDiscoveryProc.running = false;
        root.capsLockPaths = [];
        root.numLockPaths = [];
    }
}
