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
//
// D4g batch two capability metadata: every entry carries `orientations`
// (the bar axes the widget can present on) and, when the rail is one of
// them, a `verticalMode` naming the rail syntax family it uses (D-9:
// stack / rotate / iconPopup). A missing `verticalMode` IS the "no rail
// face yet" verdict — there is no fourth value. The classification below
// is the per-widget audit result (what each widget does on a rail today,
// mostly the B9.4 rail work), not an aspiration; supportsVertical() is
// the single verdict the settings faces consume to disable and explain.
QtObject {
    id: root

    // Closed rail syntax vocabulary (D-9). "stack": content reflows to run
    // along the rail axis (column cells, axis-reflipped geometry). "rotate":
    // content turns ±90°. "iconPopup": an icon face on the rail whose full
    // content surfaces through a popup.
    readonly property var verticalModes: ["stack", "rotate", "iconPopup"]

    readonly property var all: [
        {
            // D4g batch three: the rail face is the compact pill growing
            // along the track (idle/OSD/media/session column faces; text
            // faces wait for the window-growth infra).
            id: "island",
            label: "Island",
            icon: "vignette",
            orientations: ["horizontal", "vertical"],
            verticalMode: "stack"
        },
        {
            // D4g batch three: caelestia's stacked clock (TextMetrics
            // optical matching + a rail-cross fit stage) replaced the
            // end4 fixed-size stack.
            id: "clock",
            label: "Clock",
            icon: "schedule",
            orientations: ["horizontal", "vertical"],
            verticalMode: "stack"
        },
        {
            id: "tray",
            label: "Tray",
            icon: "inbox",
            orientations: ["horizontal", "vertical"],
            // Items stack into a single column (grid columns: 1).
            verticalMode: "stack"
        },
        {
            // Five gauges stack along the rail (colDefault/colMaterial
            // vertical column of the same meters).
            id: "systemMonitor",
            label: "System Monitor",
            icon: "monitoring",
            orientations: ["horizontal", "vertical"],
            verticalMode: "stack"
        },
        {
            id: "weather",
            label: "Weather",
            icon: "partly_cloudy_day",
            orientations: ["horizontal", "vertical"],
            // colContent/rowContent loaders swap on the rail.
            verticalMode: "stack"
        },
        {
            id: "visualizer",
            label: "Audio visualizer",
            icon: "graphic_eq",
            orientations: ["horizontal", "vertical"],
            // Spectrum bars run vertically (barsColumn).
            verticalMode: "stack"
        },
        {
            id: "battery",
            label: "Battery",
            icon: "battery_full",
            orientations: ["horizontal", "vertical"],
            // The whole progress bar turns -90° on the rail.
            verticalMode: "rotate"
        },
        {
            id: "systemIcons",
            label: "System Icons",
            icon: "volume_up",
            orientations: ["horizontal", "vertical"],
            // Icon flow turns TopToBottom.
            verticalMode: "stack"
        },
        {
            id: "quickSettings",
            label: "Quick Settings",
            icon: "tune",
            orientations: ["horizontal", "vertical"],
            // One component with utilButtons: the same UtilButtons.qml flow.
            verticalMode: "stack"
        },
        {
            id: "utilButtons",
            label: "Utility buttons",
            icon: "widgets",
            orientations: ["horizontal", "vertical"],
            // Icon flow turns TopToBottom.
            verticalMode: "stack"
        },
        {
            id: "launcherButton",
            label: "Launcher",
            icon: "search",
            orientations: ["horizontal", "vertical"],
            // Single icon cell — orientation-agnostic, flows as a rail cell.
            verticalMode: "stack"
        },
        {
            id: "powerButton",
            label: "Power",
            icon: "power_settings_new",
            orientations: ["horizontal", "vertical"],
            // Single icon cell — orientation-agnostic, flows as a rail cell.
            verticalMode: "stack"
        },
        {
            id: "workspaces",
            label: "Workspaces",
            icon: "grid_view",
            orientations: ["horizontal", "vertical"],
            // Indicator strip turns into a column (Workspaces/Alt).
            verticalMode: "stack"
        },
        {
            id: "activeWindow",
            label: "Active Window",
            icon: "web_asset",
            orientations: ["horizontal", "vertical"],
            // The rail face is the bare app icon today (dux vertical
            // degradation); the hover-popup half of this syntax is not
            // built yet — the title only lives on the horizontal face.
            verticalMode: "iconPopup"
        },
        {
            id: "media",
            label: "Media",
            icon: "music_note",
            orientations: ["horizontal", "vertical"],
            // The rail face is a compact play/pause icon (dux vertical
            // degradation); the hover-popup half of this syntax is not
            // built yet — text/controls only live on the horizontal face.
            verticalMode: "iconPopup"
        },
        {
            id: "separator",
            label: "Divider",
            icon: "more_vert",
            orientations: ["horizontal", "vertical"],
            // Rule flips to the cross axis; the space style runs along
            // the rail.
            verticalMode: "stack"
        },
        {
            id: "spacer",
            label: "Spacer",
            icon: "space_bar",
            orientations: ["horizontal", "vertical"],
            // Extent runs along the rail.
            verticalMode: "stack"
        }
    ]

    function displayName(entry) {
        return I18n.tr(entry.label);
    }

    // D4b/D4e per-instance options pages (files live in plugins/bar/options/).
    readonly property var optionsFiles: ({
            island: "IslandOptions.qml",
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

    // D4g batch two rail capability verdict (see the header note): true
    // exactly when the entry declares the rail in `orientations`. Unknown
    // ids fall through the byId() fallback, which has no rail face.
    function supportsVertical(id) {
        const entry = root.byId(id);
        return Array.isArray(entry.orientations) && entry.orientations.indexOf("vertical") !== -1;
    }

    // Rail syntax family for vertical-capable widgets ("" when the widget
    // has no rail face). Values are pinned to root.verticalModes.
    function verticalMode(id) {
        return root.byId(id).verticalMode ?? "";
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
