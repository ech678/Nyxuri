import QtQuick

WeatherServiceApiKeyCard {
    id: root

    serviceName: "MapTiler Dataviz"
    iconName: "map"
    fieldLabel: "MapTiler API key"
    placeholderText: qsTr("Enter MapTiler API key")
    invalidKeyText: qsTr("Enter a valid MapTiler API key")
    clearDescription: qsTr("Remove the MapTiler API key from the system keyring")
    configured: WeatherMapBridge.mapTilerConfigured
    credentialsReady: WeatherMapBridge.credentialsReady
    busy: WeatherMapBridge.credentialBusy
    checking: WeatherMapBridge.available && (!WeatherMapBridge.credentialsReady || WeatherMapBridge.mapTilerStatus === "loading_credentials")
    statusError: !WeatherMapBridge.available || WeatherMapBridge.mapTilerStatus === "keychain_error"
    storeAction: value => {
        return WeatherMapBridge.storeMapTilerApiKey(value);
    }
    clearAction: () => {
        return WeatherMapBridge.clearMapTilerApiKey();
    }

    Connections {
        function onCredentialOperationFinished(operation, success, message) {
            if (operation === "maptiler_store" || operation === "maptiler_clear")
                root.completeOperation(success, message);
        }

        target: WeatherMapBridge
    }
}
