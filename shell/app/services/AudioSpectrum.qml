pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property int bars: 45
    property var _owners: ({})

    readonly property int refCount: Object.keys(_owners).length
    readonly property bool active: refCount > 0
    readonly property bool available: backendLoader.status === Loader.Ready && backendLoader.item ? backendLoader.item.available : false
    readonly property var values: backendLoader.status === Loader.Ready && backendLoader.item ? backendLoader.item.values : []

    function acquire(token) {
        if (!token || root._owners[token])
            return;

        const next = Object.assign({}, root._owners);
        next[token] = true;
        root._owners = next;
    }

    function release(token) {
        if (!token || !root._owners[token])
            return;

        const next = Object.assign({}, root._owners);
        delete next[token];
        root._owners = next;
    }

    Loader {
        id: backendLoader

        active: root.active
        source: "cava/CavaBackend.qml"
    }
}
