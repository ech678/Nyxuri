pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.shared.theme
import qs.app
import "../../modules/settings/DisplaySchedule.js" as Schedule
import qs.shared.i18n

Singleton {
    id: root

    property var preferences: Schedule.normalize({})
    property bool ready: false
    property string error: ""
    property bool locating: false
    property string locationError: ""
    property var locationRequest: null
    property var ipLocation: null
    property bool locationAttempted: false
    property var schedule: Schedule.evaluate(preferences, Date.now())
    readonly property bool available: true
    readonly property var outputs: []
    readonly property real dimming: preferences.dimming
    readonly property real dimmingLowerLimit: 0.25
    readonly property real gamma: preferences.gamma
    readonly property real contrast: preferences.contrast
    readonly property string scheduleWarning: {
        switch (schedule.condition) {
        case "missing-location":
            return I18n.tr("Set a location. Using the fixed night temperature.");
        case "polar-day":
            return I18n.tr("Midnight sun: using the day temperature.");
        case "polar-night":
            return I18n.tr("Polar night: using the night temperature.");
        case "equal-times":
            return I18n.tr("Choose different start and end times. Using the fixed night temperature.");
        default:
            return "";
        }
    }

    signal resumed

    function setPreference(key, value) {
        if (!ready)
            return;
        const oldNightEnabled = preferences.nightEnabled;
        preferences = Schedule.normalize(Object.assign({}, preferences, {
                                                           [key]: value
                                                       }));
        config.setText(JSON.stringify(preferences, null, 2));

        if (key === "nightEnabled" && oldNightEnabled !== value) {
            eyecareToggleProc.command = [Paths.xdgConfigHome + "/niri/scripts/toggle-eyecare.sh", value
                                         ? "on" : "off"];
            eyecareToggleProc.running = true;
        } else if (key === "nightTemperature") {
            eyecareTempProc.command = [Paths.xdgConfigHome + "/niri/scripts/toggle-eyecare.sh", "set-temp",
                                       String(value)];
            eyecareTempProc.running = true;
        }

        if (key === "useIP") {
            locationAttempted = false;
            locationError = "";
            if (!value && locationRequest) {
                locationRequest.abort();
                locationRequest = null;
                locating = false;
            }
        }
        evaluate();
    }

    function setDimming(value) {
        setPreference("dimming", value);
    }

    function useWeatherLocation() {
        if (!WeatherService.hasValidData)
            return;
        preferences = Schedule.normalize(Object.assign({}, preferences, {
                                                           latitude: WeatherService.latitude,
                                                           longitude: WeatherService.longitude
                                                       }));
        config.setText(JSON.stringify(preferences, null, 2));
        evaluate();
    }

    function locate() {
        if (!preferences.useIP || locating)
            return;
        locationAttempted = true;
        locating = true;
        locationError = "";
        const request = new XMLHttpRequest();
        locationRequest = request;
        request.onreadystatechange = function () {
            if (request.readyState !== XMLHttpRequest.DONE || root.locationRequest !== request)
                return;
            locationTimeout.stop();
            root.locating = false;
            root.locationRequest = null;
            try {
                const data = JSON.parse(request.responseText);
                if (request.status !== 200 || !data.success || typeof data.latitude !== "number"
                        || typeof data.longitude !== "number" || !isFinite(data.latitude) || !isFinite(
                            data.longitude) || Math.abs(data.latitude) > 90 || Math.abs(data.longitude) > 180)
                    throw new Error("Invalid location response");
                root.ipLocation = {
                    latitude: data.latitude,
                    longitude: data.longitude
                };
            } catch (e) {
                root.locationError = I18n.tr(
                            "Location lookup failed. Using the manual location or fixed night temperature.");
            }
            root.evaluate();
        };
        request.open("GET", "https://ipwho.is/?fields=success,latitude,longitude");
        request.send();
        locationTimeout.restart();
    }

    function evaluate() {
        if (ready && preferences.useIP && !locationAttempted)
            locate();
        const effective = preferences.useIP && ipLocation ? Object.assign({}, preferences, ipLocation) :
                                                            preferences;
        schedule = Schedule.evaluate(effective, Date.now());
        deadline.interval = Math.max(100, Math.min(2147483647, schedule.wake - Date.now()));
        deadline.restart();
    }

    function checkSystemEyecareSync() {
        if (!effectsCheckProc.running)
            effectsCheckProc.running = true;
    }

    Process {
        id: eyecareToggleProc
        onExited: root.checkSystemEyecareSync()
    }

    Process {
        id: eyecareTempProc
    }

    Process {
        id: effectsCheckProc
        command: ["readlink", Paths.xdgConfigHome + "/niri/effects.kdl"]
        stdout: StdioCollector {
            onStreamFinished: {
                const target = (this.text || "").trim();
                const isOn = target.indexOf("effects_eyecare.kdl") >= 0;
                if (root.ready && root.preferences.nightEnabled !== isOn) {
                    root.preferences = Schedule.normalize(Object.assign({}, root.preferences, {
                                                                            nightEnabled: isOn
                                                                        }));
                    root.evaluate();
                }
            }
        }
    }

    Timer {
        id: eyecarePollTimer
        interval: 2000
        running: true
        repeat: true
        onTriggered: root.checkSystemEyecareSync()
    }

    Timer {
        id: locationTimeout
        interval: 15000
        onTriggered: {
            const request = root.locationRequest;
            root.locationRequest = null;
            if (request)
                request.abort();
            root.locating = false;
            root.locationError = I18n.tr(
                        "Location lookup timed out. Using the manual location or fixed night temperature.");
        }
    }

    Timer {
        id: deadline
        onTriggered: root.evaluate()
    }

    SystemClock {
        precision: SystemClock.Minutes
        onDateChanged: root.evaluate()
    }

    Process {
        id: ensureConfigDir
        command: ["mkdir", "-p", Paths.configHome]
        running: true
        onExited: code => {
            if (code !== 0) {
                root.error = I18n.tr("Unable to open display preferences");
                return;
            }
            config.reload();
        }
    }

    FileView {
        id: config
        path: Paths.configHome + "/display-color.json"
        atomicWrites: true
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                root.preferences = Schedule.normalize(JSON.parse(text()));
                root.ready = true;
                root.error = "";
                root.evaluate();
                root.checkSystemEyecareSync();
            } catch (e) {
                root.error = I18n.tr("Invalid display preferences: %1").arg(String(e));
            }
        }
        onLoadFailed: error => {
            if (error === FileViewError.FileNotFound) {
                root.ready = true;
                root.evaluate();
                root.checkSystemEyecareSync();
            } else
                root.error = I18n.tr("Unable to read display preferences");
        }
        onSaveFailed: root.error = I18n.tr("Unable to save display preferences")
    }

    Component.onDestruction: {
        deadline.stop();
        eyecarePollTimer.stop();
        if (ensureConfigDir)
            ensureConfigDir.running = false;
        if (effectsCheckProc)
            effectsCheckProc.running = false;
        if (eyecareToggleProc)
            eyecareToggleProc.running = false;
        if (eyecareTempProc)
            eyecareTempProc.running = false;
    }
}
