pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property bool available: backendLoader.status === Loader.Ready && backendLoader.item !== null
    readonly property var backend: available ? backendLoader.item.plugin : null

    readonly property bool credentialsReady: backend ? backend.credentialsReady : false
    readonly property bool mapTilerConfigured: backend ? backend.mapTilerConfigured : false
    readonly property bool apiConfigured: backend ? backend.apiConfigured : false
    readonly property bool credentialBusy: backend ? backend.credentialBusy : false
    readonly property string mapTilerStatus: backend ? backend.mapTilerStatus : "unavailable"
    readonly property string status: backend ? backend.status : "unavailable"

    signal credentialOperationFinished(string operation, bool success, string message)

    function storeMapTilerApiKey(value) {
        return backend ? backend.storeMapTilerApiKey(value) : { ok: false, message: "WeatherMap plugin not installed" };
    }

    function clearMapTilerApiKey() {
        return backend ? backend.clearMapTilerApiKey() : { ok: false, message: "WeatherMap plugin not installed" };
    }

    function storeApiKey(value) {
        return backend ? backend.storeApiKey(value) : { ok: false, message: "WeatherMap plugin not installed" };
    }

    function clearApiKey() {
        return backend ? backend.clearApiKey() : { ok: false, message: "WeatherMap plugin not installed" };
    }

    Connections {
        target: root.backend
        ignoreUnknownSignals: true

        function onCredentialOperationFinished(operation, success, message) {
            root.credentialOperationFinished(operation, success, message);
        }
    }

    Loader {
        id: backendLoader
        source: "backend/WeatherMapBackend.qml"
    }
}
