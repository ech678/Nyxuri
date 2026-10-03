pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property bool available: false
    readonly property var backend: null
    readonly property bool credentialsReady: false
    readonly property bool mapTilerConfigured: false
    readonly property bool apiConfigured: false
    readonly property bool credentialBusy: false
    readonly property string mapTilerStatus: "unavailable"
    readonly property string status: "unavailable"

    signal credentialOperationFinished(string operation, bool success, string message)

    function storeMapTilerApiKey(value) {
        return { ok: false, message: "WeatherMap not supported" };
    }

    function clearMapTilerApiKey() {
        return { ok: false, message: "WeatherMap not supported" };
    }

    function storeApiKey(value) {
        return { ok: false, message: "WeatherMap not supported" };
    }

    function clearApiKey() {
        return { ok: false, message: "WeatherMap not supported" };
    }
}

