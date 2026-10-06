pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property var sessionLocker: null
    property var settingsHost: null
    property var sidebarHost: null
    property string pendingSecurePowerAction: ""

    Connections {
        target: root.sessionLocker
        function onSecured() {
            root.runSecurePowerAction(true);
        }
        function onActiveChanged() {
            if (root.sessionLocker && !root.sessionLocker.active) {
                pendingSecurePowerTimer.stop();
                root.pendingSecurePowerAction = "";
            }
        }
    }

    signal sessionOpenRequested(var screen)
    signal sessionCloseRequested
    signal sessionToggleRequested(var screen)
    signal settingsOpenRequested(string pageId)
    signal settingsCloseRequested
    signal settingsToggleRequested(string pageId)
    signal settingsSearchRequested(string searchId)

    // A secure power action must be confirmed by the session lock within this
    // window. Otherwise it is dropped, so it can never fire on an unrelated
    // secured() much later (e.g. the next idle lock).
    Timer {
        id: pendingSecurePowerTimer

        interval: 8000
        onTriggered: {
            if (root.pendingSecurePowerAction === "")
                return;
            console.warn("[ActionGateway] Dropped secure power action, lock never secured:",
                         root.pendingSecurePowerAction);
            root.pendingSecurePowerAction = "";
        }
    }

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

    function requestSidebarToggle(target) {
        if (!root.sidebarHost)
            return false;
        return root.sidebarHost.toggleSidebar(target || "dashboard") !== "INVALID_SIDE";
    }

    // Result semantics: the boolean return value means "dispatch accepted",
    // not "command completed". execDetached is fire-and-forget; callers that
    // need user-visible outcome report it themselves (notify-send etc.).
    // Parameter shape: args must be a non-empty argument array (never a shell
    // string); owner must be a non-empty identifier (audited as LIFE001).
    function execute(args, owner) {
        if (!args || !Array.isArray(args) || args.length === 0) {
            console.warn("[ActionGateway] Invalid execution args:", JSON.stringify(args), "from owner:",
                         owner);
            return false;
        }

        try {
            Quickshell.execDetached(args);
            return true;
        } catch (err) {
            console.error("[ActionGateway] Failed to execute:", JSON.stringify(args), "Error:", err);
            return false;
        }
    }

    function runSecurePowerAction(force) {
        if (root.pendingSecurePowerAction === "")
            return;

        if (!force && root.sessionLocker && !root.sessionLocker.secure) {
            console.warn("[ActionGateway] Waiting for session locker to secure before",
                         root.pendingSecurePowerAction);
            return;
        }

        const action = root.pendingSecurePowerAction;
        pendingSecurePowerTimer.stop();
        root.pendingSecurePowerAction = "";
        root.execute(["systemctl", action], "session:secure-power");
    }

    function requestSecurePowerAction(action) {
        if (root.pendingSecurePowerAction !== "")
            return;

        root.requestSessionClose();

        if (root.sessionLocker) {
            const result = root.sessionLocker.open();
            if (result !== "LOCKED" && result !== "ALREADY_LOCKED") {
                console.warn("[ActionGateway] Locker refused lock before", action, "Result:", result);
                return;
            }
        }

        root.pendingSecurePowerAction = action;
        pendingSecurePowerTimer.restart();
        if (root.sessionLocker && root.sessionLocker.secure) {
            root.runSecurePowerAction(true);
        }
    }

    // Power actions: "lock" | "logout" | "suspend" | "poweroff" | "hibernate"
    // | "reboot". Returns "dispatch accepted" (see execute()). suspend and
    // hibernate are deferred behind the secure lock and fire only once the
    // locker reports secured; an unsecured lock within 8s drops the pending
    // action (see requestSecurePowerAction).
    function powerAction(action, owner) {
        owner = owner || "session";
        switch (action) {
        case "lock":
            if (root.sessionLocker) {
                const res = root.sessionLocker.open();
                return res === "LOCKED" || res === "ALREADY_LOCKED";
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
