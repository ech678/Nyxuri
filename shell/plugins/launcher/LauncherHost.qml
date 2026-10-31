import QtQuick
import Quickshell
import Quickshell.Io
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

    // Unit-owned IPC surface (unit-model.md §6): the launcher's spotlight
    // target exists exactly while the unit is loaded.
    IpcHandler {
        target: "spotlight"

        function toggle(): string {
            root.toggleWindow();
            return root.windowPhase.toUpperCase();
        }

        function open(): string {
            root.openSpotlight();
            return root.windowPhase.toUpperCase();
        }

        function search(): string {
            root.openSpotlight("search");
            return "SEARCH";
        }

        function close(): string {
            root.requestClose();
            return root.windowPhase.toUpperCase();
        }

        function web(): string {
            root.openWebMode();
            return "WEB";
        }

        function command(name: string): string {
            return root.runCommand(name);
        }

        function commands(): string {
            return root.openMode("commands");
        }

        function files(): string {
            return root.openMode("files");
        }

        function openMode(mode: string): string {
            if (root.normalizedMode(mode || "") === "")
                return "INVALID_MODE";

            root.openSpotlight(mode);
            return String(mode).toUpperCase();
        }
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
