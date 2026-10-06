import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pam
import Quickshell.Wayland
import qs.shared.theme
import qs.app.services
import qs.app

Scope {
    id: root

    readonly property bool active: sessionLock.locked || capturePending
    readonly property bool secure: sessionLock.secure
    property bool capturePending: false
    property int activeCaptureRequestId: 0
    property string sessionStyle: PersonalizationConfig.lockScreenStyle

    // Crash recovery marker. While the session is locked this file names the
    // owning login session and the lock start time. If the shell ever dies
    // while locked (niri keeps the session locked on a dead locker and shows
    // its solid red fallback), a fresh shell instance detects the marker here
    // and takes the session lock back over, so the user can simply unlock.
    readonly property string lockMarkerPath: Paths.runtimeHome + "/lock-active"
    readonly property int lockMarkerMaxAgeMs: 15 * 60 * 1000

    signal unlocked
    signal secured

    function open() {
        if (sessionLock.locked || capturePending)
            return "ALREADY_LOCKED";

        sessionStyle = PersonalizationConfig.lockScreenStyle;
        internalContext.authRevealed = false;
        internalContext.currentText = "";
        internalContext.unlockInProgress = false;
        internalContext.showFailure = false;
        capturePending = true;
        activeCaptureRequestId = preLockCapture.capture();
        return "LOCKED";
    }

    function isLocked() {
        return sessionLock.locked || capturePending;
    }

    function finishCapture(captureRequestId) {
        if (!capturePending || captureRequestId !== activeCaptureRequestId)
            return;

        sessionLock.locked = true;
        capturePending = false;
        writeLockMarker();
    }

    // Returns true when a fresh marker proves the previous shell instance died
    // while the session was locked, meaning this instance must take over.
    function previousInstanceDiedLocked() {
        const raw = lockMarkerFile.text().trim();
        if (raw === "")
            return false;

        const parts = raw.split("\n");
        const markerSession = parts[0] || "";
        const markerAge = Date.now() - (Number(parts[1]) || 0);
        const currentSession = Quickshell.env("XDG_SESSION_ID") || "";
        if (markerSession !== "" && markerSession !== currentSession)
            return false;
        if (markerAge < 0 || markerAge > root.lockMarkerMaxAgeMs)
            return false;
        return true;
    }

    function writeLockMarker() {
        lockMarkerFile.setText((Quickshell.env("XDG_SESSION_ID") || "") + "\n" + Date.now());
    }

    function clearLockMarker() {
        lockMarkerFile.setText("");
    }

    Component.onCompleted: {
        if (previousInstanceDiedLocked()) {
            console.warn("[Lock] Previous shell instance died while the session was locked;"
                         + " taking over the session lock");
            sessionLock.locked = true;
            writeLockMarker();
        } else {
            clearLockMarker();
        }
    }

    onActiveChanged: {
        SystemIdentityService.setUptimeConsumer("lock-screen", root.active);
        SystemMonitorService.setConsumerModules("lock-screen", root.active ? ["cpu", "memory", "disk"] : []);
    }
    Component.onDestruction: {
        preLockCapture.cancel();
        preLockCapture.clear();
        SystemIdentityService.setUptimeConsumer("lock-screen", false);
        SystemMonitorService.clearConsumer("lock-screen");
    }

    PreLockCapture {
        id: preLockCapture

        onCompleted: captureRequestId => {
            return root.finishCapture(captureRequestId);
        }
    }

    FileView {
        id: lockMarkerFile

        path: root.lockMarkerPath
        watchChanges: false
        atomicWrites: true
    }

    Scope {
        id: internalContext

        property bool authRevealed: false
        property string currentText: ""
        property bool unlockInProgress: false
        property bool showFailure: false

        signal unlockFailed
        signal shouldReFocus

        // Clear the failure state as soon as the user types again.
        onCurrentTextChanged: showFailure = false

        function tryUnlock() {
            if (currentText === "" || unlockInProgress)
                return;

            internalContext.unlockInProgress = true;
            pam.start();
        }

        function finishUnlock() {
            if (!sessionLock.locked)
                return;
            sessionLock.locked = false;
            clearLockMarker();
            root.unlocked();
            Qt.callLater(preLockCapture.clear);
        }

        PamContext {
            id: pam

            configDirectory: Paths.shellDir + "/modules/lock/pam"
            config: "password.conf"
            onPamMessage: {
                if (this.responseRequired)
                    this.respond(internalContext.currentText);
            }
            onCompleted: result => {
                if (result == PamResult.Success) {
                    internalContext.currentText = "";
                    internalContext.showFailure = false;
                    sessionLock.unlock();
                } else {
                    internalContext.currentText = "";
                    internalContext.showFailure = true;
                    internalContext.unlockFailed();
                }
                internalContext.unlockInProgress = false;
            }
        }
    }

    // Heartbeat re-focus while locked. Niri sometimes drops keyboard focus on the
    // ext-session-lock surface after suspend/resume — the surface stays visible but
    // input goes nowhere until something forces a re-grab. We just nudge it back.
    Timer {
        id: lockFocusHeartbeat
        interval: 1500
        repeat: true
        running: sessionLock.locked
        onTriggered: internalContext.shouldReFocus()
    }

    // Re-focus immediately when monitor topology changes (a common signal of wake-up).
    Connections {
        target: Quickshell
        function onScreensChanged() {
            if (sessionLock.locked) {
                Qt.callLater(() => internalContext.shouldReFocus());
            }
        }
    }

    WlSessionLock {
        id: sessionLock

        signal unlock

        onSecureStateChanged: {
            if (secure)
                root.secured();
        }

        LockSurface {
            lock: sessionLock
            context: internalContext
            snapshotProvider: preLockCapture
            style: root.sessionStyle
        }
    }
}
