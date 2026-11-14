import QtQuick
import QtQuick.Window
import Quickshell
import "./ui" as Ui

ShellRoot {
    id: root

    property string scenario: Quickshell.env("NYXURI_WEATHER_SCENARIO") || "partly"
    property string mode: Quickshell.env("NYXURI_WEATHER_MODE") || "static"
    property string implementation: Quickshell.env("NYXURI_WEATHER_IMPL") || "optimized"
    property string imagePath: Quickshell.env("NYXURI_WEATHER_IMAGE") || ""
    readonly property int bandCount: scenario === "rain" ? 3 : 2
    readonly property int expectedFrameInterval: scenario === "rain" ? 33 : 66
    readonly property int expectedTargetFps: scenario === "rain" ? 30 : 15
    readonly property int expectedPathBuilds: bandCount * (implementation === "baseline" ? 2 : 1)
    property bool configured: false
    property int initialPaintCount: 0
    property int driverTicks: 0
    property double animationStartedAt: 0
    property bool captureStarted: false

    function fail(reason) {
        console.error("WEATHER_CANVAS_FAIL", reason)
        Qt.exit(1)
    }

    function assertState() {
        if (weather.cloudBands.length !== root.bandCount)
            return root.fail("unexpected cloud band count " + weather.cloudBands.length)
        if (weather.targetFps !== root.expectedTargetFps
                || weather.sceneFrameInterval !== root.expectedFrameInterval)
            return root.fail("unexpected animation frame contract")
        if (weather.cloudPathBuildCount !== root.expectedPathBuilds)
            return root.fail("unexpected per-frame path builds " + weather.cloudPathBuildCount
                             + ", expected " + root.expectedPathBuilds)
        return true
    }

    function configureScene() {
        const fixedBands = [
            {offset: 34, height: 82, arch: 139, speed: 1.0, toneIndex: 0},
            {offset: 151, height: 112, arch: 171, speed: 0.72, toneIndex: 1},
            {offset: 279, height: 143, arch: 205, speed: 0.48, toneIndex: 2}
        ]
        root.initialPaintCount = weather.paintCount
        root.animationStartedAt = Date.now()
        weather.probeCaptureDataUrl = ""
        weather.cloudBands = fixedBands.slice(0, root.bandCount)
        weather.resetRainScene()
        root.configured = true
        console.log("WEATHER_CANVAS_SETUP", root.scenario, root.mode, root.implementation,
                    "weather_size=" + weather.width + "x" + weather.height,
                    "paint_count=" + weather.paintCount,
                    "bands=" + weather.cloudBands.length)
    }

    function captureImage() {
        if (weather.probeCaptureDataUrl.indexOf("data:image/png;base64,") !== 0)
            return root.fail("Canvas PNG capture failed: " + root.imagePath)
        if (!root.assertState())
            return
        console.log("WEATHER_CANVAS_PASS case=" + root.scenario + " mode=static"
                    + " bands=" + root.bandCount
                    + " per_frame_paths=" + weather.cloudPathBuildCount
                    + " paints=" + weather.paintCount
                    + " fps=" + weather.targetFps
                    + " interval_ms=" + weather.sceneFrameInterval
                    + " timer_running=" + weather.animationTimerRunning
                    + " image=" + root.imagePath)
        console.log("WEATHER_CANVAS_PNG_DATA " + weather.probeCaptureDataUrl)
        Qt.quit()
    }

    Window {
        id: probeWindow
        visible: true
        width: 480
        height: 320
        color: "#263642"

        Ui.WeatherBackground {
            id: weather
            anchors.fill: parent
            weatherCode: root.scenario === "rain" ? 63 : 2
            iconName: root.scenario === "rain" ? "rain" : "partly-cloudy"
            animate: root.mode === "animated"
        }
    }

    Timer {
        id: probeDriver
        interval: 10
        repeat: true
        running: probeWindow.visible && weather.width === probeWindow.width
                 && weather.height === probeWindow.height

        onTriggered: {
            if (!root.configured) {
                root.configureScene()
                return
            }
            root.driverTicks += 1
            if (root.driverTicks === 1 || root.driverTicks === 50)
                console.log("WEATHER_CANVAS_STATE", "ticks=" + root.driverTicks,
                            "configured=" + root.configured,
                            "paints=" + weather.paintCount,
                            "initial_paints=" + root.initialPaintCount,
                            "path_builds=" + weather.cloudPathBuildCount,
                            "frames=" + weather.simulationFrameCount,
                            "canvas_visible=" + weather.hasCanvasScene,
                            "window_visible=" + probeWindow.visible)
            if (root.mode === "static") {
                if (weather.paintCount <= root.initialPaintCount
                        || weather.cloudPathBuildCount !== root.expectedPathBuilds
                        || weather.probeCaptureDataUrl === "")
                    return
                if (weather.animationTimerRunning)
                    return root.fail("static capture unexpectedly has a running scene timer")
                probeDriver.stop()
                if (!root.captureStarted) {
                    root.captureStarted = true
                    captureDelay.start()
                    console.log("WEATHER_CANVAS_CAPTURE_SCHEDULED", root.imagePath)
                }
                return
            }

            if (weather.simulationFrameCount < 12)
                return
            if (!weather.animationTimerRunning)
                return root.fail("animated scene timer is stopped")
            if (!root.assertState())
                return
            if (!weather.animate)
                return root.fail("animation unexpectedly disabled")
            console.log("WEATHER_CANVAS_PASS case=" + root.scenario + " mode=animated"
                        + " bands=" + root.bandCount
                        + " per_frame_paths=" + weather.cloudPathBuildCount
                        + " simulation_frames=" + weather.simulationFrameCount
                        + " elapsed_ms=" + (Date.now() - root.animationStartedAt)
                        + " fps=" + weather.targetFps
                        + " interval_ms=" + weather.sceneFrameInterval
                        + " timer_running=" + weather.animationTimerRunning)
            Qt.quit()
        }
    }

    Timer {
        id: captureDelay
        interval: 150
        repeat: false
        onTriggered: root.captureImage()
    }

    Timer {
        interval: 15000
        repeat: false
        running: true
        onTriggered: {
            console.log("WEATHER_CANVAS_TIMEOUT", "ticks=" + root.driverTicks,
                        "paint_count=" + weather.paintCount,
                        "initial_paint_count=" + root.initialPaintCount,
                        "canvas_visible=" + weather.hasCanvasScene,
                        "window_visible=" + probeWindow.visible)
            root.fail("probe timed out")
        }
    }
}
