pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property bool suspended: false
    readonly property bool supported: false
    readonly property bool connected: false
    readonly property int captureCount: 0
    readonly property int revision: 0
    property int nextConsumer: 0

    function createConsumer() {
        return "";
    }

    function setTargets(consumer, ids) {}
    function release(consumer) {}
    function captureFor(id) {
        return null;
    }
    function frameFor(id) {
        return null;
    }
    function snapshot(id, callback) {
        return false;
    }
}

