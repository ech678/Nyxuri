pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Notifications
import qs.commons
import qs.ui
import qs.commons.i18n

Singleton {
    id: root

    readonly property int defaultPopupTimeoutMs: PersonalizationConfig.notificationTimeoutMs
    readonly property int maxHistoryCount: 500
    readonly property string notificationsDir: Paths.stateHome + "/notifications"
    readonly property string filePath: notificationsDir + "/notifications.json"
    readonly property bool silent: UiPreferences.dndEnabled
    readonly property bool popupInhibited: silent || (WidgetState.dashboardSidebarOpen && WidgetState.dashboardSidebarView === "info")
    readonly property bool hasNotifs: popupList.length > 0

    property bool historyReady: false
    property bool historyDegraded: false
    property var pendingSavedFiles: []
    property int unread: 0
    property int idOffset: 0
    property list<Notif> list: []
    // Keep the public projections, but refresh them as one derived-index pass.  The
    // previous bindings independently walked and sorted the history for each
    // projection, which made every list replacement more expensive than needed.
    property var popupList: []
    property var latestTimeForApp: ({})
    property var groupsByAppName: ({})
    property var popupGroupsByAppName: ({})
    property list<string> appNameList: []
    property list<string> popupAppNameList: []
    property var notificationIndex: ({})

    signal notify(notification: var)
    signal discard(id: int)
    signal discardAll
    signal timeout(id: var)
    signal initDone

    component Notif: QtObject {
        id: wrapper

        required property int notificationId
        property int serverNotificationId: -1
        property Notification notification: null
        property string appIcon: ""
        property string appName: ""
        property string body: ""
        property string desktopEntry: ""
        property string image: ""
        property bool isTransient: false
        property bool popup: false
        property double popupExpiresAt: 0
        property double popupStartedAt: 0
        property double receivedAt: Date.now()
        property string summary: ""
        property string localKind: ""
        property string filePath: ""
        property Timer timer: null
        property var urgency: NotificationUrgency.Normal
        property Connections closeConnection: Connections {
            target: wrapper.notification

            function onClosed(reason) {
                root.handleNativeClosed(wrapper.notificationId, reason);
            }

            function onBodyChanged() {
                wrapper.body = wrapper.notification.body || "";
                root.saveNotifications();
            }

            function onSummaryChanged() {
                wrapper.summary = wrapper.notification.summary || wrapper.notification.appName
                        || I18n.tr("Notification");
                root.saveNotifications();
            }

            function onAppNameChanged() {
                wrapper.appName = wrapper.notification.appName || wrapper.notification.desktopEntry
                        || I18n.tr("System");
                root.saveNotifications();
            }

            function onAppIconChanged() {
                wrapper.appIcon = wrapper.notification.appIcon || "";
            }

            function onDesktopEntryChanged() {
                wrapper.desktopEntry = wrapper.notification.desktopEntry || "";
            }

            function onImageChanged() {
                wrapper.image = wrapper.notification.image || "";
            }

            function onUrgencyChanged() {
                wrapper.urgency = wrapper.notification.urgency;
            }
        }

        onNotificationChanged: {
            if (notification === null && serverNotificationId !== -1)
                root.detachNotification(notificationId);
        }
    }

    component NotifTimer: Timer {
        required property int notificationId
        running: true
        repeat: false

        onTriggered: {
            const notifObject = root.notificationById(notificationId);
            if (notifObject)
                notifObject.timer = null;
            destroy();
            root.expireNotification(notificationId);
        }
    }

    Component {
        id: notifComponent
        Notif {}
    }
    Component {
        id: notifTimerComponent
        NotifTimer {}
    }

    Component.onCompleted: {
        root.rebuildDerivedIndexes();
        ensureStoreDir.running = true;
    }

    onInitDone: {
        root.historyReady = true;
        root.flushPendingSavedFiles();
    }

    function flushPendingSavedFiles() {
        if (root.pendingSavedFiles.length === 0)
            return;
        const pending = root.pendingSavedFiles;
        root.pendingSavedFiles = [];
        pending.forEach(item => root.fileSaved(item.title, item.path));
    }

    Connections {
        target: FileActionService
        function onFinished(action, path, response) {
            if (!response || !response.ok)
                root.addLocal(I18n.tr("File action failed"), I18n.tr("Could not open the saved file or its location: %1").arg(path));
            else if (!response.fileExists)
                root.addLocal(I18n.tr("File no longer exists"), I18n.tr("Opened the containing folder: %1").arg(path));
        }
    }

    function fileSaved(title, path) {
        if (typeof path !== "string" || !path.startsWith("/") || path.indexOf("\u0000") !== -1)
            return;
        if (!root.historyReady && !root.historyDegraded) {
            root.pendingSavedFiles = [...root.pendingSavedFiles,
                {
                    title,
                    path
                }
            ];
            return;
        }
        root.addLocal(title, path, path);
    }

    function addLocal(title, body, filePath) {
        const now = Date.now();
        const notif = notifComponent.createObject(root, {
            notificationId: ++root.idOffset,
            appName: "Nyxuri Shell",
            appIcon: "folder",
            summary: title,
            body: body.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"),
            localKind: filePath ? "file-saved" : "",
            filePath: filePath || "",
            receivedAt: now,
            urgency: NotificationUrgency.Low,
            popup: !root.popupInhibited,
            popupStartedAt: now,
            popupExpiresAt: now + root.defaultPopupTimeoutMs
        });
        notif.timer = notifTimerComponent.createObject(root, {
            notificationId: notif.notificationId,
            interval: root.defaultPopupTimeoutMs
        });
        root.list = [...root.list, notif];
        if (notif.popup)
            root.unread++;
        root.trimPopupList(3);
        root.trimHistory();
        root.saveNotifications();
        root.notify(notif);
    }

    onListChanged: root.rebuildDerivedIndexes()

    Process {
        id: ensureStoreDir
        command: ["mkdir", "-p", root.notificationsDir]
        running: false
        onExited: root.refresh()
    }

    NotificationServer {
        id: notifServer

        actionsSupported: true
        actionIconsSupported: false
        bodyHyperlinksSupported: true
        bodyImagesSupported: false
        bodyMarkupSupported: true
        bodySupported: true
        imageSupported: true
        inlineReplySupported: false
        keepOnReload: false
        persistenceSupported: true

        onNotification: notification => {
            notification.tracked = true;

            const replaced = root.list.filter(notif => notif.serverNotificationId === notification.id);
            replaced.forEach(notif => root.stopPopupTimer(notif));

            const now = Date.now();
            const timeoutMs = root.popupTimeoutMs(notification.expireTimeout);
            root.idOffset++;
            const newNotifObject = notifComponent.createObject(root, {
                "notificationId": root.idOffset,
                "serverNotificationId": notification.id,
                "notification": notification,
                "appIcon": notification.appIcon || "",
                "appName": notification.appName || notification.desktopEntry || I18n.tr("System"),
                "body": notification.body || "",
                "desktopEntry": notification.desktopEntry || "",
                "image": notification.image || "",
                "isTransient": notification.transient,
                "summary": notification.summary || notification.appName || I18n.tr("Notification"),
                "receivedAt": now,
                "urgency": notification.urgency
            });

            if (timeoutMs > 0) {
                newNotifObject.popupStartedAt = now;
                newNotifObject.popupExpiresAt = now + timeoutMs;
                newNotifObject.timer = notifTimerComponent.createObject(root, {
                    "notificationId": newNotifObject.notificationId,
                    "interval": timeoutMs
                });
            }

            if (!root.popupInhibited) {
                newNotifObject.popup = true;
                root.unread++;
            }

            root.list = [...root.list.filter(notif => notif.serverNotificationId !== notification.id), newNotifObject,];
            replaced.forEach(notif => Qt.callLater(() => notif.destroy()));
            root.trimPopupList(3);
            root.trimHistory();
            root.saveNotifications();
            root.notify(newNotifObject);
        }
    }

    FileView {
        id: notifFileView
        path: root.filePath
        atomicWrites: true

        onLoaded: {
            try {
                const live = root.list.filter(notif => notif && notif.notification !== null);
                const fileContents = notifFileView.text();
                const loaded = JSON.parse(fileContents && fileContents.trim() !== "" ? fileContents : "[]");
                if (!Array.isArray(loaded)) {
                    root.historyDegraded = true;
                    root.list = live;
                    root.initDone();
                    root.flushPendingSavedFiles();
                    return;
                }

                const entries = loaded.filter(notif => notif !== null && typeof notif === "object");
                let maxId = 0;
                const storedIds = entries.map(notif => {
                    const rawId = Number(notif.notificationId || notif.id || 0);
                    const parsed = Number.isFinite(rawId) && rawId > 0 ? Math.floor(rawId) : 0;
                    if (parsed > maxId)
                        maxId = parsed;
                    return parsed;
                });
                const usedIds = new Set();
                for (const notif of live) {
                    usedIds.add(notif.notificationId);
                    if (notif.notificationId > maxId)
                        maxId = notif.notificationId;
                }
                const restored = entries.map((notif, index) => {
                    let notificationId = storedIds[index];
                    if (notificationId === 0 || usedIds.has(notificationId))
                        notificationId = ++maxId;
                    usedIds.add(notificationId);
                    return notifComponent.createObject(root, {
                        "notificationId": notificationId,
                        "localKind": notif.localKind === "file-saved" ? "file-saved" : "",
                        "filePath": notif.localKind === "file-saved" && typeof notif.filePath === "string" && notif.filePath.startsWith("/") && notif.filePath.indexOf("\u0000") === -1 ? notif.filePath : "",
                        "appIcon": root.durableHistorySource(notif.appIcon),
                        "appName": notif.appName || I18n.tr("System"),
                        "body": notif.body || "",
                        "desktopEntry": notif.desktopEntry || "",
                        "image": root.durableHistorySource(notif.image),
                        "summary": notif.summary || notif.appName || I18n.tr("Notification"),
                        "receivedAt": Number(notif.receivedAt || notif.time) || Date.now(),
                        "urgency": notif.urgency ?? NotificationUrgency.Normal
                    });
                });
                root.list = restored.concat(live);
                root.idOffset = maxId;
                root.historyDegraded = false;
                root.trimHistory();
                root.saveNotifications();
                root.initDone();
            } catch (error) {
                console.warn("NotificationService failed to load history:", error);
                root.historyDegraded = true;
                root.list = live;
                root.idOffset = 0;
                root.initDone();
                root.flushPendingSavedFiles();
            }
        }

        onLoadFailed: error => {
            if (error === FileViewError.FileNotFound) {
                root.historyDegraded = false;
                root.saveNotifications();
                root.initDone();
            } else {
                console.warn("NotificationService failed to load notification file; leaving the existing file untouched:", error);
                root.historyDegraded = true;
                root.initDone();
                root.flushPendingSavedFiles();
            }
        }

        onSaveFailed: error => console.warn("NotificationService failed to save:", error)
    }

    function notificationById(id) {
        return root.notificationIndex[String(id)] || null;
    }

    function rebuildDerivedIndexes() {
        const nextLatest = {};
        const nextNotificationIndex = {};
        const nextPopupList = [];
        const nextGroups = {};
        const nextPopupGroups = {};
        const appendGroup = (groups, notif) => {
            const appName = notif.appName || I18n.tr("System");
            if (!groups[appName]) {
                groups[appName] = {
                    appName,
                    appIcon: notif.appIcon,
                    notifications: [],
                    receivedAt: notif.receivedAt
                };
            }
            groups[appName].notifications.push(notif);
            // Preserve groupsForList's fallback: when latestTimeForApp has no
            // matching (display) key, the last notification wins.
            groups[appName].receivedAt = notif.receivedAt;
            if (!groups[appName].appIcon && notif.appIcon)
                groups[appName].appIcon = notif.appIcon;
        };

        // Build both group projections from this same traversal.  Popup groups are
        // sorted below because popupList has the public receivedAt ordering.
        root.list.forEach(notif => {
            nextNotificationIndex[String(notif.notificationId)] = notif;
            if (!nextLatest[notif.appName] || notif.receivedAt > nextLatest[notif.appName])
                nextLatest[notif.appName] = notif.receivedAt;
            appendGroup(nextGroups, notif);
            if (notif.popup) {
                nextPopupList.push(notif);
                appendGroup(nextPopupGroups, notif);
            }
        });
        Object.keys(nextGroups).forEach(appName => {
            nextGroups[appName].receivedAt = nextLatest[appName] || nextGroups[appName].receivedAt;
        });
        Object.keys(nextPopupGroups).forEach(appName => {
            nextPopupGroups[appName].receivedAt = nextLatest[appName] || nextPopupGroups[appName].receivedAt;
            nextPopupGroups[appName].notifications.sort((a, b) => b.receivedAt - a.receivedAt);
        });
        nextPopupList.sort((a, b) => b.receivedAt - a.receivedAt);

        // Publish the projections after deriving them from the same list snapshot.
        root.notificationIndex = nextNotificationIndex;
        root.latestTimeForApp = nextLatest;
        root.popupList = nextPopupList;
        root.groupsByAppName = nextGroups;
        root.popupGroupsByAppName = nextPopupGroups;
        root.appNameList = root.appNameListForGroups(nextGroups);
        root.popupAppNameList = root.appNameListForGroups(nextPopupGroups);
    }

    // Quickshell passes Notification.expireTimeout through verbatim as the
    // freedesktop expire_timeout: milliseconds, with 0 = "never expire". Its
    // docs claim seconds, which is wrong (notification.cpp stores the raw
    // int32). 0 is clamped to the default so a sticky notification cannot
    // pin the island forever; the full text stays in the dashboard history.
    function popupTimeoutMs(expireTimeout) {
        if (expireTimeout <= 0)
            return root.defaultPopupTimeoutMs;
        return Math.max(1, Math.round(expireTimeout));
    }

    function nativeActions(notifObject) {
        if (notifObject && notifObject.localKind === "file-saved" && notifObject.filePath) {
            const path = notifObject.filePath;
            return [
                {
                    identifier: "default",
                    text: I18n.tr("Show in folder"),
                    invoke: () => FileActionService.run("reveal", path)
                },
                {
                    identifier: "reveal",
                    text: I18n.tr("Show in folder"),
                    invoke: () => FileActionService.run("reveal", path)
                },
                {
                    identifier: "open",
                    text: I18n.tr("Open"),
                    invoke: () => FileActionService.run("open", path)
                }
            ];
        }
        return notifObject && notifObject.notification && notifObject.notification.actions ? notifObject.notification.actions : [];
    }

    function defaultAction(notifObject) {
        return root.nativeActions(notifObject).find(action => action.identifier === "default") || null;
    }

    function normalActions(notifObject) {
        return root.nativeActions(notifObject).filter(action => action.identifier !== "default");
    }

    function durableHistorySource(source) {
        const value = source || "";
        return value.startsWith("image://qsimage/") ? "" : value;
    }

    function notifToJSON(notif) {
        return {
            "notificationId": notif.notificationId,
            "localKind": notif.localKind,
            "filePath": notif.filePath,
            "appIcon": root.durableHistorySource(notif.appIcon),
            "appName": notif.appName,
            "body": String(notif.body === undefined || notif.body === null ? "" : notif.body).slice(0, 65536),
            "desktopEntry": notif.desktopEntry,
            "image": root.durableHistorySource(notif.image),
            "receivedAt": notif.receivedAt,
            "summary": String(notif.summary === undefined || notif.summary === null ? "" : notif.summary).slice(0, 65536),
            "urgency": notif.urgency
        };
    }

    function stringifyList(notifications) {
        return JSON.stringify(notifications.filter(notif => !notif.isTransient).map(notif => root.notifToJSON(notif)), null, 2);
    }

    function refresh() {
        notifFileView.reload();
    }

    function trimHistory() {
        const durable = root.list.filter(notif => !notif.isTransient).sort((a, b) => b.receivedAt - a.receivedAt);
        if (durable.length <= root.maxHistoryCount)
            return;

        const retained = new Set(durable.slice(0, root.maxHistoryCount));
        const removed = root.list.filter(notif => !notif.isTransient && !retained.has(notif));
        root.list = root.list.filter(notif => notif.isTransient || retained.has(notif));
        removed.forEach(notif => {
            root.stopPopupTimer(notif);
            Qt.callLater(() => notif.destroy());
        });
    }

    function saveNotifications() {
        if (root.historyDegraded)
            return;
        saveDebounce.restart();
    }

    Timer {
        id: saveDebounce
        interval: 100
        repeat: false
        onTriggered: {
            if (root.historyDegraded)
                return;
            notifFileView.setText(root.stringifyList(root.list));
        }
    }

    function appNameListForGroups(groups) {
        return Object.keys(groups).sort((a, b) => groups[b].receivedAt - groups[a].receivedAt);
    }

    function groupsForList(notifications) {
        const groups = {};
        notifications.forEach(notif => {
            const appName = notif.appName || I18n.tr("System");
            if (!groups[appName]) {
                groups[appName] = {
                    appName,
                    appIcon: notif.appIcon,
                    notifications: [],
                    receivedAt: 0
                };
            }
            groups[appName].notifications.push(notif);
            groups[appName].receivedAt = root.latestTimeForApp[appName] || notif.receivedAt;
            if (!groups[appName].appIcon && notif.appIcon)
                groups[appName].appIcon = notif.appIcon;
        });
        return groups;
    }

    // Qt 6.12 list properties compare content on assignment: self-assigning a
    // re-derived sequence (slice/spread of the same object pointers) does not
    // emit listChanged, so in-place popup-flag mutations never refreshed the
    // projections. Refresh them directly instead of round-tripping the signal.
    function triggerListChange() {
        root.rebuildDerivedIndexes();
    }

    function stopPopupTimer(notifObject) {
        if (!notifObject || !notifObject.timer)
            return;
        notifObject.timer.stop();
        notifObject.timer.destroy();
        notifObject.timer = null;
    }

    function hidePopup(notifObject) {
        if (notifObject)
            notifObject.popup = false;
    }

    function finishPopupLifetime(notifObject) {
        if (!notifObject)
            return;
        root.stopPopupTimer(notifObject);
        notifObject.popup = false;
        notifObject.popupStartedAt = 0;
        notifObject.popupExpiresAt = 0;
    }

    function trimPopupList(maxCount) {
        const popups = root.list.filter(notif => notif.popup).sort((a, b) => b.receivedAt - a.receivedAt);
        for (let i = maxCount; i < popups.length; i++)
            root.hidePopup(popups[i]);
        if (popups.length > maxCount)
            root.triggerListChange();
    }

    function setSilent(value) {
        UiPreferences.setDndEnabled(value);
    }

    function markAllRead() {
        root.unread = 0;
    }

    function detachNotification(id) {
        const notifObject = root.notificationById(id);
        if (!notifObject)
            return;
        if (notifObject.isTransient) {
            root.removeSnapshot(id);
            return;
        }
        root.finishPopupLifetime(notifObject);
        notifObject.appIcon = root.durableHistorySource(notifObject.appIcon);
        notifObject.image = root.durableHistorySource(notifObject.image);
        notifObject.serverNotificationId = -1;
        notifObject.notification = null;
        root.triggerListChange();
        root.saveNotifications();
    }

    function handleNativeClosed(id, reason) {
        root.detachNotification(id);
    }

    function removeSnapshot(id) {
        const notifObject = root.notificationById(id);
        if (!notifObject)
            return;
        root.stopPopupTimer(notifObject);
        root.list = root.list.filter(candidate => candidate.notificationId !== id);
        root.saveNotifications();
        Qt.callLater(() => notifObject.destroy());
    }

    function dismissPopup(id) {
        const notifObject = root.notificationById(id);
        if (!notifObject)
            return;
        const nativeNotification = notifObject.notification;
        root.finishPopupLifetime(notifObject);
        if (nativeNotification)
            nativeNotification.dismiss();
        else if (notifObject.isTransient)
            root.removeSnapshot(id);
        root.triggerListChange();
    }

    function expireNotification(id) {
        const notifObject = root.notificationById(id);
        if (!notifObject)
            return;
        const nativeNotification = notifObject.notification;
        root.finishPopupLifetime(notifObject);
        if (nativeNotification)
            nativeNotification.expire();
        else if (notifObject.isTransient)
            root.removeSnapshot(id);
        root.triggerListChange();
        root.timeout(id);
    }

    function discardNotification(id) {
        root.discardNotifications([id]);
    }

    function discardNotifications(ids) {
        const targetIds = new Set(ids || []);
        const removed = root.list.filter(notif => targetIds.has(notif.notificationId));
        if (removed.length === 0)
            return;
        removed.forEach(notif => root.stopPopupTimer(notif));
        root.list = root.list.filter(candidate => !targetIds.has(candidate.notificationId));
        root.saveNotifications();
        removed.forEach(notif => {
            if (notif.notification)
                notif.notification.dismiss();
            root.discard(notif.notificationId);
            Qt.callLater(() => notif.destroy());
        });
    }

    function discardAllNotifications() {
        const removed = root.list.slice();
        removed.forEach(notif => root.stopPopupTimer(notif));
        root.list = [];
        root.saveNotifications();
        removed.forEach(notif => {
            if (notif.notification)
                notif.notification.dismiss();
            Qt.callLater(() => notif.destroy());
        });
        root.discardAll();
    }

    function hideAllPopups() {
        root.popupList.forEach(notif => root.hidePopup(notif));
        root.triggerListChange();
    }

    function invokeDefaultAction(id) {
        const action = root.defaultAction(root.notificationById(id));
        if (action)
            action.invoke();
    }

    function invokeAction(action) {
        if (action)
            action.invoke();
    }

    Component.onDestruction: {
        saveDebounce.stop();
        if (!root.historyDegraded)
            notifFileView.setText(root.stringifyList(root.list));
        if (ensureStoreDir)
            ensureStoreDir.running = false;
        root.list.forEach(notif => root.stopPopupTimer(notif));
    }
}
