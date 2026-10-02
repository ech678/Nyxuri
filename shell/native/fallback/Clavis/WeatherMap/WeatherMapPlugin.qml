pragma Singleton
import QtQuick

QtObject {
    property bool active: false
    readonly property bool apiConfigured: false
    readonly property bool mapTilerConfigured: false
    readonly property bool credentialsReady: false
    readonly property bool credentialBusy: false
    readonly property bool busy: false
    readonly property string status: "unavailable"
    readonly property string errorMessage: ""
    readonly property string mapTilerStatus: "unavailable"
    readonly property string radarStatus: "unavailable"
}
