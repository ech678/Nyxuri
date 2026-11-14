pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

// Keyboard lock state from the kernel LED class.
//
// The old implementation shelled out to `key keyboard watch`, but key-cli is
// retired (known-issues 2026-11-07) and the binary is absent on current hosts,
// which left capsLock/numLock permanently null: no island OSD, no SystemIcons
// indicator, and a hidden "Keyboard indicators" settings section. The kernel
// already exposes the same state in /sys/class/leds/*::capslock|numlock/
// brightness, so watch those files directly — no external process per event
// and no dependency on a retired package.
Singleton {
    id: root

    property bool supported: false
    property string state: "scanning"
    readonly property bool available: state === "ready"
    property var capsLock: null
    property var numLock: null
    property var error: null
    property bool _hasSnapshot: false
    property double _armedAt: 0

    // LED class paths found by the scan; one FileView per LED file watches it.
    property var ledPaths: []

    signal lockStateChanged
    signal availabilityChanged

    function unavailable(code, message) {
        state = "unavailable";
        supported = false;
        capsLock = null;
        numLock = null;
        _hasSnapshot = false;
        error = {
            "code": code,
            "message": message
        };
        availabilityChanged();
    }

    function scan() {
        if (!scanProc.running)
            scanProc.running = true;
    }

    function applyPaths(text) {
        const next = String(text || "").split("\n").map(line => line.trim()).filter(line => line.length > 0);
        if (next.length === 0) {
            root.ledPaths = [];
            root.unavailable("keyboard_led_unavailable", "No /sys/class/leds/*::capslock or *::numlock devices");
            return;
        }
        root.ledPaths = next;
        root.supported = true;
        root.state = "ready";
        root.error = null;
        root._hasSnapshot = false;
        root._armedAt = Date.now();
        root.availabilityChanged();
    }

    function readLedViews() {
        if (root.ledPaths.length === 0)
            return;
        let caps = null;
        let num = null;
        for (let index = 0; index < ledViews.count; index += 1) {
            const view = ledViews.objectAt(index);
            if (!view)
                continue;
            const value = String(view.text() || "").trim();
            if (value !== "0" && value !== "1")
                continue;
            const on = value === "1";
            if (String(view.path).includes("::capslock"))
                caps = caps === null ? on : (caps || on);
            else if (String(view.path).includes("::numlock"))
                num = num === null ? on : (num || on);
        }
        if (caps === null && num === null)
            return;
        const changed = caps !== root.capsLock || num !== root.numLock;
        root.capsLock = caps;
        root.numLock = num;
        if (!root._hasSnapshot || Date.now() - root._armedAt < 500) {
            // Baseline only: opening the shell (or the second LED view loading
            // after the first) must not announce a lock change.
            root._hasSnapshot = true;
            return;
        }
        if (changed)
            root.lockStateChanged();
    }

    Component.onCompleted: root.scan()

    Process {
        id: scanProc

        command: ["find", "/sys/class/leds", "-maxdepth", "1", "(", "-name", "*::capslock", "-o", "-name", "*::numlock", ")", "-print"]
        stdout: StdioCollector {
            onStreamFinished: root.applyPaths(this.text)
        }
        onExited: code => {
            if (code !== 0 && !root.available)
                root.unavailable("keyboard_led_scan_failed", "Keyboard LED scan exited " + code);
        }
    }

    Instantiator {
        id: ledViews

        model: root.ledPaths
        delegate: FileView {
            required property string modelData

            path: modelData + "/brightness"
            watchChanges: true
            onFileChanged: reload()
            onLoaded: root.readLedViews()
            onLoadFailed: root.unavailable("keyboard_led_read_failed", "Cannot read " + path)
        }
    }

    // kernfs inotify delivery depends on the LED driver calling sysfs_notify;
    // several drivers update the attribute without notifying. A 300ms reread
    // of two or three tiny sysfs files is the only guaranteed event source
    // without an evdev/libinput daemon.
    Timer {
        id: ledPollTimer

        interval: 300
        repeat: true
        running: root.available && root.ledPaths.length > 0
        onTriggered: {
            for (let index = 0; index < ledViews.count; index += 1) {
                const view = ledViews.objectAt(index);
                if (view)
                    view.reload();
            }
        }
    }

    Component.onDestruction: {
        scanProc.running = false;
        root.ledPaths = [];
    }
}
