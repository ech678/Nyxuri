pragma Singleton
import QtQuick
import Quickshell
import Clavis.Niri

Singleton {
    id: root

    property bool suspended: false
    readonly property var backend: backendLoader.item
    readonly property bool supported: backend !== null && backend.supported
    readonly property bool connected: backend !== null && backend.connected
    readonly property int captureCount: backend !== null ? backend.captureCount : 0
    readonly property int revision: backend !== null ? backend.revision : 0
    property int nextConsumer: 0

    function createConsumer() {
        return "dock-preview-" + (++nextConsumer);
    }
    function setTargets(consumer, ids) {
        if (backend !== null)
            backend.setTargets(consumer, ids);
    }
    function release(consumer) {
        if (backend !== null)
            backend.release(consumer);
    }
    function captureFor(id) {
        return backend !== null ? backend.captureFor(id) : null;
    }
    function frameFor(id) {
        return backend !== null ? backend.frameFor(id) : null;
    }
    function snapshot(id, callback) {
        return backend !== null && backend.snapshot(id, callback);
    }

    Loader {
        id: backendLoader
        // Keep optional imports outside the core module's loading closure.
        // Resolve once on a real Niri connection; a missing plugin disables
        // thumbnails locally while the dock's ordinary window actions remain.
        active: Niri.connected
        source: Qt.resolvedUrl("windowpreview/WindowPreviewBackend.qml")
    }
    Binding {
        target: root.backend
        property: "suspended"
        value: root.suspended
        when: root.backend !== null
    }
}
