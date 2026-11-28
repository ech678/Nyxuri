.pragma library

// Bar widget id -> component file (D4a). Registration point 3 of 3 for a
// new bar widget (the others: services/BarWidgetDefaults.js, shell/ui/
// BarWidgetCatalog.qml). This replaces the two identical inline getWidgetUrl
// maps in the lane host — including the capitalized-name
// fallback, which silently resolved unknown ids to whatever file happened
// to share the name (visualizer only ever worked through it). Unknown ids
// now fail loud at the caller and empty at the Loader.
//
// Paths stay relative: the resolving QML context (BarContent,
// host file) lives in this directory, so Qt.resolvedUrl anchors
// them to plugins/bar no matter which host asks.
var FILES = {
    island: "DynamicIsland.qml",
    clock: "ClockWidget.qml",
    tray: "SysTray.qml",
    systemMonitor: "Resources.qml",
    weather: "WeatherBar.qml",
    visualizer: "Visualizer.qml",
    battery: "BatteryIndicator.qml",
    systemIcons: "SystemIcons.qml",
    quickSettings: "UtilButtons.qml",
    utilButtons: "UtilButtons.qml",
    launcherButton: "LauncherButton.qml",
    powerButton: "PowerButton.qml",
    workspaces: "Workspaces.qml",
    activeWindow: "ActiveWindow.qml",
    media: "Media.qml",
    separator: "Divisor.qml",
    spacer: "Spacer.qml"
};

function fileFor(id) {
    return FILES[String(id || "")] || "";
}
