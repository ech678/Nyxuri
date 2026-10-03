import QtQuick
import Quickshell
import qs.app

Scope {
    id: root

    property bool active: false
    property string initialMode: ""
    property string initialCommand: ""

    readonly property var launcherItem: launcherLoader.item
    readonly property string windowPhase: launcherItem ? launcherItem.windowPhase : "hidden"

    function toggleWindow(): void {
        if (!root.active) {
            root.initialMode = "";
            root.initialCommand = "";
            root.active = true;
        } else if (launcherItem) {
            launcherItem.toggleWindow();
        }
    }

    function openSpotlight(mode: string): void {
        root.initialMode = mode || "search";
        root.initialCommand = "";
        if (!root.active) {
            root.active = true;
        } else if (launcherItem) {
            launcherItem.openSpotlight(root.initialMode);
        }
    }

    function openWebMode(): void {
        if (!root.active) {
            root.initialMode = "web";
            root.initialCommand = "";
            root.active = true;
        } else if (launcherItem) {
            launcherItem.openWebMode();
        }
    }

    function requestClose(): void {
        if (launcherItem) {
            launcherItem.requestClose();
        }
    }

    function runCommand(name: string): string {
        if (!root.active) {
            root.initialCommand = name || "";
            root.initialMode = "";
            root.active = true;
            return "EXECUTED";
        }
        return launcherItem ? launcherItem.runCommand(name) : "FAILED";
    }

    function normalizedMode(mode: string): string {
        return launcherItem ? launcherItem.normalizedMode(mode) : (mode || "");
    }

    LazyLoader {
        id: launcherLoader
        active: root.active

        LauncherWindow {
            id: window

            Component.onCompleted: {
                if (root.initialCommand !== "") {
                    window.runCommand(root.initialCommand);
                    root.initialCommand = "";
                } else if (root.initialMode !== "") {
                    window.openSpotlight(root.initialMode);
                    root.initialMode = "";
                } else {
                    window.openSpotlight();
                }
            }
        }
    }
}
