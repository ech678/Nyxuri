pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property var sessionLocker: null
    property var settingsHost: null
    property string pendingSecurePowerAction: ""

    Connections {
        target: root.sessionLocker
        function onSecured() {
            root.runSecurePowerAction();
        }
        function onActiveChanged() {
            if (root.sessionLocker && !root.sessionLocker.active)
                root.pendingSecurePowerAction = "";
        }
    }

    signal actionDispatched(string owner, string action, bool success)
    signal sessionOpenRequested(var screen)
    signal sessionCloseRequested()
    signal sessionToggleRequested(var screen)
    signal settingsOpenRequested(string pageId)
    signal settingsCloseRequested()
    signal settingsToggleRequested(string pageId)
    signal settingsSearchRequested(string searchId)

    function requestSessionOpen(screen) {
        root.sessionOpenRequested(screen);
        return true;
    }

    function requestSessionClose() {
        root.sessionCloseRequested();
        return true;
    }

    function requestSessionToggle(screen) {
        root.sessionToggleRequested(screen);
        return true;
    }

    function requestSettingsOpen(pageId) {
        if (root.settingsHost)
            return root.settingsHost.open(pageId || "");
        root.settingsOpenRequested(pageId || "");
        return true;
    }

    function requestSettingsClose() {
        if (root.settingsHost)
            return root.settingsHost.close();
        root.settingsCloseRequested();
        return true;
    }

    function requestSettingsToggle(pageId) {
        if (root.settingsHost)
            return root.settingsHost.toggle(pageId || "");
        root.settingsToggleRequested(pageId || "");
        return true;
    }

    function requestSettingsSearch(searchId) {
        root.settingsSearchRequested(searchId || "");
        return true;
    }

    function execute(args, owner) {
        if (!args || !Array.isArray(args) || args.length === 0) {
            console.warn("[ActionGateway] Invalid execution args:", JSON.stringify(args), "from owner:", owner);
            return false;
        }

        try {
            Quickshell.execDetached(args);
            root.actionDispatched(owner || "unknown", args.join(" "), true);
            return true;
        } catch (err) {
            console.error("[ActionGateway] Failed to execute:", JSON.stringify(args), "Error:", err);
            root.actionDispatched(owner || "unknown", args.join(" "), false);
            return false;
        }
    }

    function runSecurePowerAction() {
        if (root.pendingSecurePowerAction === "")
            return;

        if (root.sessionLocker && !root.sessionLocker.secure) {
            console.warn("[ActionGateway] Waiting for session locker to secure before", root.pendingSecurePowerAction);
            return;
        }

        const action = root.pendingSecurePowerAction;
        root.pendingSecurePowerAction = "";
        root.execute(["loginctl", action], "session:secure-power");
    }

    function requestSecurePowerAction(action) {
        if (root.pendingSecurePowerAction !== "")
            return;

        if (root.sessionLocker) {
            const result = root.sessionLocker.open();
            if (result !== "LOCKED" && result !== "ALREADY_LOCKED") {
                console.warn("[ActionGateway] Locker refused lock before", action, "Result:", result);
                return;
            }
        }

        root.pendingSecurePowerAction = action;
        root.runSecurePowerAction();
    }

    function powerAction(action, owner) {
        owner = owner || "session";
        switch (action) {
        case "lock":
            if (root.sessionLocker) {
                const res = root.sessionLocker.open();
                root.actionDispatched(owner, "lock", res === "LOCKED" || res === "ALREADY_LOCKED");
                return true;
            }
            return false;
        case "logout":
            return root.execute(["niri", "msg", "action", "quit", "--skip-confirmation"], owner);
        case "suspend":
            root.requestSecurePowerAction("suspend");
            return true;
        case "poweroff":
            return root.execute(["systemctl", "poweroff"], owner);
        case "hibernate":
            root.requestSecurePowerAction("hibernate");
            return true;
        case "reboot":
            return root.execute(["systemctl", "reboot"], owner);
        default:
            console.warn("[ActionGateway] Unknown power action:", action, "from owner:", owner);
            return false;
        }
    }

    function launchApp(desktopFileOrCommand, args, owner) {
        owner = owner || "launcher";
        if (!desktopFileOrCommand || desktopFileOrCommand.trim() === "")
            return false;

        const target = desktopFileOrCommand.trim();
        if (target.endsWith(".desktop")) {
            return root.execute(["gio", "launch", target], owner);
        }

        const fullArgs = [target].concat(args || []);
        return root.execute(fullArgs, owner);
    }
}
