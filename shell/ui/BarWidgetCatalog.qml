import QtQuick
import qs.commons.i18n

// Unified bar-widget catalog (D4a): label + icon for every canonical id in
// services/BarWidgetDefaults.js IDS. Pure data only — no config reads, no
// files, no processes — so both the bar settings page (plugins/bar) and the
// dashboard layout tile (plugins/settings) consume it without a cross-plugin
// import. It replaces the three scattered lists: PersonalizationConfig
// .barComponentOptions, ui/DashboardBarWidgets.qml and the inline option
// arrays in the settings cards.
//
// Registration point 2 of 3 for a new widget (the others: services/
// BarWidgetDefaults.js, shell/plugins/bar/BarWidgetFiles.js). The id set
// must match both — tests/shell/test_d4a_bar_config.py pins the equality.
//
// D4b adds the fourth registration surface here: `optionsFiles` maps a
// widget id to its per-instance options page (resolved by BarWidgetPage
// against plugins/bar/options/). Widgets without an entry (island has its
// own routed page; visualizer/systemIcons carry no axes yet) render the
// generic card only. quickSettings shares UtilButtonsOptions.qml because
// both ids load UtilButtons.qml.
//
// `label` stays an untranslated literal on purpose (DashboardBarWidgets
// precedent): translating at construction would evaluate I18n.tr() before
// the dictionary has loaded and every label would come out empty.
// displayName() resolves it at use time instead.
QtObject {
    id: root

    readonly property var all: [
        {
            id: "island",
            label: "Island",
            icon: "vignette"
        },
        {
            id: "clock",
            label: "Clock",
            icon: "schedule"
        },
        {
            id: "tray",
            label: "Tray",
            icon: "inbox"
        },
        {
            id: "systemMonitor",
            label: "System Monitor",
            icon: "monitoring"
        },
        {
            id: "weather",
            label: "Weather",
            icon: "partly_cloudy_day"
        },
        {
            id: "visualizer",
            label: "Audio visualizer",
            icon: "graphic_eq"
        },
        {
            id: "battery",
            label: "Battery",
            icon: "battery_full"
        },
        {
            id: "systemIcons",
            label: "System Icons",
            icon: "volume_up"
        },
        {
            id: "quickSettings",
            label: "Quick Settings",
            icon: "tune"
        },
        {
            id: "utilButtons",
            label: "Utility buttons",
            icon: "widgets"
        },
        {
            id: "launcherButton",
            label: "Launcher",
            icon: "search"
        },
        {
            id: "powerButton",
            label: "Power",
            icon: "power_settings_new"
        },
        {
            id: "workspaces",
            label: "Workspaces",
            icon: "grid_view"
        },
        {
            id: "activeWindow",
            label: "Active Window",
            icon: "web_asset"
        },
        {
            id: "media",
            label: "Media",
            icon: "music_note"
        },
        {
            id: "separator",
            label: "Divider",
            icon: "more_vert"
        },
        {
            id: "spacer",
            label: "Spacer",
            icon: "space_bar"
        }
    ]

    function displayName(entry) {
        return I18n.tr(entry.label);
    }

    // D4b per-instance options pages (files live in plugins/bar/options/).
    readonly property var optionsFiles: ({
        clock: "ClockOptions.qml",
        workspaces: "WorkspacesOptions.qml",
        systemMonitor: "SystemMonitorOptions.qml",
        utilButtons: "UtilButtonsOptions.qml",
        quickSettings: "UtilButtonsOptions.qml",
        tray: "TrayOptions.qml",
        battery: "BatteryOptions.qml",
        media: "MediaOptions.qml",
        activeWindow: "ActiveWindowOptions.qml",
        launcherButton: "LauncherButtonOptions.qml",
        powerButton: "PowerButtonOptions.qml",
        weather: "WeatherOptions.qml",
        separator: "SeparatorOptions.qml",
        spacer: "SpacerOptions.qml"
    })

    function optionsFile(id) {
        return root.optionsFiles[String(id || "")] ?? "";
    }

    function hasOptions(id) {
        return root.optionsFiles[String(id || "")] !== undefined;
    }

    function byId(id) {
        for (let index = 0; index < root.all.length; index += 1) {
            if (root.all[index].id === id)
                return root.all[index];
        }
        return {
            id: id,
            label: id,
            icon: "widgets"
        };
    }

    // The {value, label, icon} options shape SortableMultiSelectField and
    // the preference selects already consume.
    function options() {
        return root.all.map(entry => ({
                    value: entry.id,
                    label: root.displayName(entry),
                    icon: entry.icon
                }));
    }
}
