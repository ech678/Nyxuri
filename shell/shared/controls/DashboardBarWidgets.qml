import QtQuick
import qs.shared.i18n

// Static catalog of status-bar widgets that can be arranged through the drag
// layout tile. Pure data only — it reads no config, writes no files and starts
// no processes — so it belongs in shared/controls under the shell's four-layer
// boundary.
//
// The ids listed here are exactly the components BarComponentLoader dispatches
// (shell/modules/bar/BarComponentLoader.qml). Upstream end4-pC exposes a larger
// set, but ids this project does not implement are intentionally excluded: a
// user could otherwise drag a non-existent widget into a lane, store it, and see
// nothing happen. Confirmed supported ids:
//   workspaces, information, activeWindow, media, tray,
//   systemMonitor, quickSettings, clock
//
// `label` stays an untranslated literal on purpose. Translating it here would
// evaluate I18n.tr() while this object is being constructed — before the
// translation dictionary has loaded — and every label would come out empty.
// displayName() resolves it at use time instead.
QtObject {
    id: root

    // Widgets that may appear more than once. Empty here: every bar component is
    // a singleton, so placing the same widget in two lanes is rejected.
    readonly property var multipleAllowed: []

    readonly property var all: [
        {
            id: "workspaces",
            label: "Workspaces",
            icon: "grid_view"
        },
        {
            id: "information",
            label: "Information",
            icon: "info"
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
            id: "quickSettings",
            label: "Quick Settings",
            icon: "tune"
        },
        {
            id: "clock",
            label: "Clock",
            icon: "schedule"
        }
    ]

    function displayName(entry) {
        return I18n.tr(entry.label);
    }

    function byId(id) {
        for (let i = 0; i < root.all.length; i++) {
            if (root.all[i].id === id)
                return root.all[i];
        }
        return {
            id: id,
            label: id,
            icon: "widgets"
        };
    }
}
