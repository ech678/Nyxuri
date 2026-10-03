pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property int bars: 45
    readonly property int refCount: 0
    readonly property bool active: false
    readonly property bool available: false
    readonly property var values: []

    function acquire(token) {}
    function release(token) {}
}

