import QtQuick

WeatherServiceApiKeyCard {
    id: root

    serviceName: "OpenWeather Weather Maps"
    iconName: "rainy"
    fieldLabel: "OpenWeather API key"
    placeholderText: qsTr("Enter OpenWeather API key")
    invalidKeyText: qsTr("Enter a valid OpenWeather API key")
    clearDescription: qsTr("Remove the OpenWeather API key from the system keyring")
    configured: WeatherMapBridge.apiConfigured
    credentialsReady: WeatherMapBridge.credentialsReady
    busy: WeatherMapBridge.credentialBusy
    checking: WeatherMapBridge.available && (!WeatherMapBridge.credentialsReady || WeatherMapBridge.status === "loading_credentials")
    statusError: !WeatherMapBridge.available || WeatherMapBridge.status === "keychain_error"
    storeAction: value => {
        return WeatherMapBridge.storeApiKey(value);
    }
    clearAction: () => {
        return WeatherMapBridge.clearApiKey();
    }

    Connections {
        function onCredentialOperationFinished(operation, success, message) {
            if (operation === "openweather_store" || operation === "openweather_clear")
                root.completeOperation(success, message);
        }

        target: WeatherMapBridge
    }
}
