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
    property bool markerReady: false
    property bool startupChecked: false

    signal unlocked
    signal secured

    // 接受锁屏请求并开始抓取背景；LOCKED 表示请求已接收，安全锁定由 sessionLock.secure 确认。
    function open(): string {
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

    // 抓取期间也视为锁定，阻止切换 Shell 在安全锁定前的准备阶段销毁当前实例。
    function isLocked(): bool {
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
        if (!markerReady)
            return;

        lockMarkerFile.setText((Quickshell.env("XDG_SESSION_ID") || "") + "\n" + Date.now());
    }

    function clearLockMarker() {
        if (!markerReady)
            return;

        lockMarkerFile.setText("");
    }

    function restoreLockAfterCrash() {
        if (!markerReady || startupChecked)
            return;

        startupChecked = true;
        if (previousInstanceDiedLocked()) {
            console.warn("[Lock] Previous shell instance died while the session was locked;"
                         + " taking over the session lock");
            sessionLock.locked = true;
            writeLockMarker();
        } else {
            clearLockMarker();
        }
    }

    Process {
        id: ensureRuntimeDir

        command: ["mkdir", "-p", Paths.runtimeHome]
        running: true
        onExited: exitCode => {
            if (exitCode === 0)
                root.markerReady = true;
            else
                console.warn("[Lock] Runtime directory unavailable; crash-recovery marker disabled");
        }
    }

    onActiveChanged: {
        SystemIdentityService.setUptimeConsumer("lock-screen", root.active);
        SystemMonitorService.setConsumerModules("lock-screen", root.active ? ["cpu", "memory", "disk"] : []);
    }

    // Unit self-registration (unit-model.md §6): the lock unit owns its
    // gateway presence and its IPC surface; both exist exactly while the
    // unit is loaded.
    Component.onCompleted: ActionGateway.sessionLocker = root
    Component.onDestruction: {
        preLockCapture.cancel();
        preLockCapture.clear();
        SystemIdentityService.setUptimeConsumer("lock-screen", false);
        SystemMonitorService.clearConsumer("lock-screen");
        if (ActionGateway.sessionLocker === root)
            ActionGateway.sessionLocker = null;
    }

    IpcHandler {
        target: "lock"

        // IPC 需要显式返回类型才能导出正确方法与值；外部切换器依赖 bool 锁态守卫。
        function open(): string {
            return root.open();
        }

        function isLocked(): bool {
            return root.isLocked();
        }
    }

    PreLockCapture {
        id: preLockCapture

        onCompleted: captureRequestId => {
            return root.finishCapture(captureRequestId);
        }
    }

    FileView {
        id: lockMarkerFile

        path: root.markerReady ? root.lockMarkerPath : ""
        watchChanges: false
        atomicWrites: true
        onLoaded: root.restoreLockAfterCrash()
        onLoadFailed: error => {
            if (error === FileViewError.FileNotFound) {
                root.restoreLockAfterCrash();
                return;
            }
            console.warn("[Lock] Cannot read crash-recovery marker:", error);
        }
        onSaveFailed: error => console.warn("[Lock] Cannot write crash-recovery marker:", error)
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

            configDirectory: Paths.shellDir + "/units/lock/pam"
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
