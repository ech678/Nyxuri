import QtQuick
import Quickshell
import Quickshell.Io
import qs.services

ShellRoot {
    id: root

    property int initialCount: 2000
    property int stage: 0
    property bool profileMode: Quickshell.env("NOTIFICATION_CONNECTIONS_PROFILE") === "1"
    property int serverId: -1
    property var replacementTarget

    function fail(reason) {
        console.log("NOTIFICATION_CONNECTIONS_FAIL " + reason);
        Qt.exit(1);
    }

    function pass() {
        console.log("NOTIFICATION_CONNECTIONS_PASS " + JSON.stringify({
            "restoredCount": root.initialCount,
            "finalCount": NotificationService.list.length,
            "liveActionCount": 1,
            "detachedConnection": true
        }));
        Qt.exit(0);
    }

    function verifyRestoredRows(checkConnections) {
        for (let index = 0; index < NotificationService.list.length; index++) {
            const item = NotificationService.list[index];
            if (item.notificationId !== 1000000 + index
                    || item.localKind !== "" || item.filePath !== ""
                    || item.appIcon !== "/tmp/notification-fixture/icon.svg"
                    || item.appName !== "Representative Application"
                    || item.body !== "B".repeat(256)
                    || item.desktopEntry !== "representative-application.desktop"
                    || item.image !== "/tmp/notification-fixture/image.png"
                    || item.receivedAt !== 1762548900000 + index
                    || item.summary !== "Representative notification summary"
                    || item.urgency !== 1 || item.popup)
                return root.fail("restored display/history field mismatch at index " + index + ": "
                                 + JSON.stringify({id: item.notificationId, localKind: item.localKind,
                                                   filePath: item.filePath, appIcon: item.appIcon,
                                                   appName: item.appName, bodyLength: item.body.length,
                                                   desktopEntry: item.desktopEntry, image: item.image,
                                                   receivedAt: item.receivedAt, summary: item.summary,
                                                   urgency: item.urgency, popup: item.popup}));
            if (item.notification !== null
                    || (checkConnections && item.closeConnection !== null))
                return root.fail("restored row retained live notification state at index " + index);
        }
        return true;
    }

    function verifyPersistedRows() {
        const expectedKeys = ["notificationId", "localKind", "filePath", "appIcon", "appName", "body",
                              "desktopEntry", "image", "receivedAt", "summary", "urgency"];
        let rows;
        try {
            rows = JSON.parse(historyFile.text());
        } catch (error) {
            return false;
        }
        if (!Array.isArray(rows) || rows.length !== root.initialCount + 1)
            return false;
        for (let index = 0; index < root.initialCount; index++) {
            const row = rows[index];
            if (Object.keys(row).join(",") !== expectedKeys.join(",")
                    || row.notificationId !== 1000000 + index
                    || row.localKind !== "" || row.filePath !== ""
                    || row.appIcon !== "/tmp/notification-fixture/icon.svg"
                    || row.appName !== "Representative Application"
                    || row.body !== "B".repeat(256)
                    || row.desktopEntry !== "representative-application.desktop"
                    || row.image !== "/tmp/notification-fixture/image.png"
                    || row.receivedAt !== 1762548900000 + index
                    || row.summary !== "Representative notification summary"
                    || row.urgency !== 1)
                return root.fail("serialized history field/order mismatch at index " + index);
        }
        const last = rows[root.initialCount];
        if (last.notificationId !== NotificationService.list[root.initialCount].notificationId
                || last.summary !== "Replacement summary" || last.body !== "Replacement body")
            return root.fail("serialized live notification fields changed");
        return true;
    }

    FileView {
        id: historyFile
        path: NotificationService.filePath
        blockLoading: true
        printErrors: false
    }

    Process {
        id: sendNotification
        command: ["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications",
                  "--object-path", "/org/freedesktop/Notifications", "--method",
                  "org.freedesktop.Notifications.Notify", "Notification connection probe", "0", "",
                  "Live summary", "Live body", "['default', 'Open', 'details', 'Details']", "{}", "10000"]
        stdout: StdioCollector {
            id: initialNotificationOutput
        }
        onExited: (exitCode, exitStatus) => {
            console.log("NOTIFICATION_CONNECTIONS_INITIAL_NOTIFY " + JSON.stringify({
                "exitCode": exitCode,
                "output": initialNotificationOutput.text
            }));
            if (exitCode !== 0)
                root.fail("gdbus Notify failed: " + exitCode);
            const match = initialNotificationOutput.text.match(/uint32 (\d+)/);
            if (!match)
                return root.fail("gdbus Notify did not return a server ID: " + initialNotificationOutput.text);
            root.serverId = Number(match[1]);
        }
    }

    Process {
        id: replacementNotification
        command: []
        stdout: StdioCollector {
            id: replacementNotificationOutput
        }
        onExited: (exitCode, exitStatus) => {
            console.log("NOTIFICATION_CONNECTIONS_REPLACEMENT_NOTIFY " + JSON.stringify({
                "exitCode": exitCode,
                "output": replacementNotificationOutput.text
            }));
            if (exitCode !== 0)
                root.fail("gdbus replacement Notify failed: " + exitCode);
        }
    }

    Timer {
        interval: 100
        repeat: true
        running: true
        onTriggered: {
            if (!NotificationService.historyReady)
                return;

            if (root.stage === 0) {
                if (NotificationService.list.length !== root.initialCount)
                    return root.fail("restored history count mismatch: " + NotificationService.list.length);
                if (!root.verifyRestoredRows(!root.profileMode))
                    return;
                if (root.profileMode) {
                    console.log("NOTIFICATION_PROFILE_READY " + JSON.stringify({
                        "ready": NotificationService.historyReady,
                        "count": NotificationService.list.length
                    }));
                    root.stage = 3;
                    return;
                }
                for (let index = 0; index < NotificationService.list.length; index++) {
                    const item = NotificationService.list[index];
                    if (item.closeConnection !== null)
                        return root.fail("restored record has a close connection at index " + index);
                    if (item.notification !== null)
                        return root.fail("restored record has a native notification at index " + index);
                }
                root.stage = 1;
                sendNotification.running = true;
                return;
            }

            const live = NotificationService.list.find(item => item.summary === "Live summary");
            if (root.stage === 1 && live) {
                if (!live.notification || !live.closeConnection)
                    return root.fail("live notification did not attach its close connection");
                if (NotificationService.defaultAction(live)?.identifier !== "default")
                    return root.fail("default action was not retained");
                const actions = NotificationService.normalActions(live);
                if (actions.length !== 1 || actions[0].identifier !== "details"
                        || actions[0].text !== "Details")
                    return root.fail("normal actions were not retained: " + JSON.stringify(actions));
                if (NotificationService.list.length !== root.initialCount + 1
                        || NotificationService.list[root.initialCount] !== live)
                    return root.fail("live notification order or identity changed");
                if (!live.popup || !NotificationService.popupList.includes(live))
                    return root.fail("live notification was not added to popup history");
                root.replacementTarget = live;
                root.stage = 2;
                replacementNotification.command = ["gdbus", "call", "--session", "--dest",
                                                    "org.freedesktop.Notifications", "--object-path",
                                                    "/org/freedesktop/Notifications", "--method",
                                                    "org.freedesktop.Notifications.Notify",
                                                    "Notification connection probe", String(root.serverId), "",
                                                    "Replacement summary", "Replacement body",
                                                    "['default', 'Open', 'details', 'Details']", "{}", "10000"];
                replacementNotification.running = true;
                return;
            }

            const replacement = NotificationService.list.find(item => item.summary === "Replacement summary");
            if (root.stage === 2 && replacement) {
                const sameServerId = NotificationService.list.filter(item => item.serverNotificationId === root.serverId);
                if (sameServerId.length !== 1 || sameServerId[0] !== replacement)
                    return root.fail("replacement did not retain exactly one record for server ID " + root.serverId);
                if (root.replacementTarget.notification !== null
                        || root.replacementTarget.closeConnection !== null)
                    return root.fail("replaced notification retained its native connection");
                if (NotificationService.list.length !== root.initialCount + 1
                        || NotificationService.list[root.initialCount] !== replacement)
                    return root.fail("replacement changed history count/order");
                if (!replacement.notification || !replacement.closeConnection)
                    return root.fail("replacement lost native notification connection");
                if (NotificationService.normalActions(replacement).length !== 1
                        || NotificationService.defaultAction(replacement)?.identifier !== "default")
                    return root.fail("replacement actions were not retained");
                root.stage = 3;
                NotificationService.dismissPopup(replacement.notificationId);
                return;
            }

            if (root.stage === 3 && replacement && replacement.notification === null) {
                if (replacement.closeConnection !== null)
                    return root.fail("dismissed replacement retained its close connection");
                if (NotificationService.list.length !== root.initialCount + 1
                        || NotificationService.list[root.initialCount] !== replacement)
                    return root.fail("dismiss changed persisted history count/order");
                if (replacement.popup || NotificationService.popupList.includes(replacement))
                    return root.fail("dismiss did not remove notification from popup history");
                root.stage = 4;
                historyFile.reload();
            } else if (root.stage === 4) {
                if (root.verifyPersistedRows())
                    root.pass();
                else
                    historyFile.reload();
            }
        }
    }

    Timer {
        interval: root.profileMode ? 10000 : 20000
        running: true
        onTriggered: {
            if (root.profileMode && root.stage === 3)
                Qt.quit();
            else
                root.fail("lifecycle probe timed out at stage " + root.stage);
        }
    }
}
