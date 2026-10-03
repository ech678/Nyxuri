import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls

ColumnLayout {
    id: root

    property var parentModal: null
    property bool active: visible
    property real candidateLatitude: Number(WeatherPlugin.latitude)
    property real candidateLongitude: Number(WeatherPlugin.longitude)
    property string coordinateError: ""
    readonly property bool expanded: false

    function coordinateText(latitudeValue, longitudeValue) {
        return Number(latitudeValue).toFixed(6) + ", " + Number(longitudeValue).toFixed(6);
    }

    function setCandidate(latitudeValue, longitudeValue) {
        root.candidateLatitude = latitudeValue;
        root.candidateLongitude = longitudeValue;
        coordinateField.text = root.coordinateText(latitudeValue, longitudeValue);
        root.coordinateError = "";
    }

    function commitCoordinate() {
        const values = coordinateField.text.trim().split(/[\s,]+/);
        if (values.length !== 2 || values[0] === "" || values[1] === "") {
            root.coordinateError = qsTr("Enter latitude and longitude");
            return;
        }
        const latitudeValue = Number(values[0]);
        const longitudeValue = Number(values[1]);
        if (!isFinite(latitudeValue) || latitudeValue < -90 || latitudeValue > 90) {
            root.coordinateError = qsTr("Latitude must be between -90 and 90");
            return;
        }
        if (!isFinite(longitudeValue) || longitudeValue < -180 || longitudeValue > 180) {
            root.coordinateError = qsTr("Longitude must be between -180 and 180");
            return;
        }
        root.setCandidate(latitudeValue, longitudeValue);
    }

    function returnToSavedLocation() {
        const latitudeValue = Number(WeatherPlugin.latitude);
        const longitudeValue = Number(WeatherPlugin.longitude);
        root.setCandidate(latitudeValue, longitudeValue);
    }

    function saveCoordinate() {
        root.commitCoordinate();
        if (root.coordinateError !== "")
            return;

        WeatherPlugin.setManualLocation(root.candidateLatitude, root.candidateLongitude, root.coordinateText(
                                            root.candidateLatitude, root.candidateLongitude));
    }

    function useAutomaticLocation() {
        WeatherPlugin.clearManualLocation();
    }

    function openWindow() {}
    function closeChildWindows() {}

    spacing: Metrics.spacingM

    OutlinedTextField {
        id: coordinateField

        Layout.fillWidth: true
        labelText: qsTr("Coordinates")
        errorText: root.coordinateError
        text: root.coordinateText(root.candidateLatitude, root.candidateLongitude)
        onTextChanged: root.coordinateError = ""
        onAccepted: root.commitCoordinate()
        onEditingFinished: root.commitCoordinate()
    }

    RowLayout {
        Layout.fillWidth: true

        Item {
            Layout.fillWidth: true
        }

        InlineBusyIndicator {
            busy: WeatherPlugin.loading
        }

        ActionButton {
            id: saveLocationButton

            text: qsTr("Save location")
            iconName: "save"
            onClicked: root.saveCoordinate()
        }

        ActionButton {
            text: qsTr("Use automatic location")
            iconName: "my_location"
            enabled: !WeatherPlugin.loading
            onClicked: root.useAutomaticLocation()
        }
    }

    Connections {
        target: WeatherPlugin
        function onDataChanged() {
            if (WeatherPlugin.hasManualLocation || WeatherPlugin.locationName === "")
                return;

            root.candidateLatitude = Number(WeatherPlugin.latitude);
            root.candidateLongitude = Number(WeatherPlugin.longitude);
            root.setCandidate(root.candidateLatitude, root.candidateLongitude);
        }
    }
}

