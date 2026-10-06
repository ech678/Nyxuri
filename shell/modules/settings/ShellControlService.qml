pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import qs.app.services
import qs.shared.i18n
import qs.modules.keystone.tools
import "ShellDiagnostics.js" as ShellDiagnostics
import "ShellSamplerMath.js" as SamplerMath

// Shell control-plane backend (R11). Owns exactly the I/O the Shell page
// cannot do as a view, nothing else:
//
// 1. Self sampling. A timer re-reads /proc/self so the page can show the
//    shell's own footprint. The gate is "page mounted AND user opted in":
//    closing the page or flipping the switch off stops the timer, abandons
//    in-flight reads and clears every retained number.
// 2. Diagnostics. Assembles an allowlisted payload from the single-source
//    services, sanitizes it through ShellDiagnostics.js and writes it into
//    the cache directory. Module states are read from their owners at build
//    time; nothing is mirrored here.
Singleton {
    id: root

    // ── Sampling ──────────────────────────────────────────────────────────
    // Low frequency by design; not a setting. First sample fires immediately
    // when the gate opens so the page never waits a full interval.
    readonly property int sampleIntervalMs: 5000
    readonly property string samplingSource: "/proc/self/status + /proc/self/stat"

    property bool pageMounted: false
    readonly property bool samplingActive: pageMounted && UiPreferences.controlPlaneResourceSampling
    property double cpuPercent: -1
    property double rssKb: -1
    property double lastSampleMs: 0

    property double _previousJiffies: -1
    property double _previousSampleMs: 0
    property bool _sampleReadInFlight: false

    onSamplingActiveChanged: root._applyGate()

    function setPageMounted(mounted) {
        const next = mounted === true;
        if (root.pageMounted === next)
            return;
        root.pageMounted = next;
        root._applyGate();
    }

    function _applyGate() {
        if (root.samplingActive) {
            root._previousJiffies = -1;
            root._previousSampleMs = 0;
            root._sampleNow();
            sampleTimer.restart();
        } else {
            sampleTimer.stop();
            root._clearSamples();
        }
    }

    function _clearSamples() {
        root.cpuPercent = -1;
        root.rssKb = -1;
        root.lastSampleMs = 0;
        root._previousJiffies = -1;
        root._previousSampleMs = 0;
    }

    function _sampleNow() {
        if (!root.samplingActive || root._sampleReadInFlight)
            return;
        root._sampleReadInFlight = true;
        procStatus.reload();
    }

    function _sampleReadFinished() {
        root._sampleReadInFlight = false;
    }

    // /proc is a plain file read: two service-owned FileViews reloaded per
    // tick. XHR is not an option here — QML blocks local-file XHR unless an
    // environment variable is set, and the sampler must not depend on how
    // the shell was launched. Every handler re-checks the gate before
    // touching state, so late loads cannot resurrect cleared numbers.
    FileView {
        id: procStatus

        path: "/proc/self/status"
        blockLoading: true
        watchChanges: false
        onLoaded: {
            if (!root.samplingActive)
                return;
            const rss = SamplerMath.parseVmRssKb(procStatus.text());
            if (rss >= 0)
                root.rssKb = rss;
            procStat.reload();
        }
        onLoadFailed: root._sampleReadFinished()
    }

    FileView {
        id: procStat

        path: "/proc/self/stat"
        blockLoading: true
        watchChanges: false
        onLoaded: {
            if (!root.samplingActive)
                return;
            const jiffies = SamplerMath.parseCpuJiffies(procStat.text());
            const now = Date.now();
            root.cpuPercent = SamplerMath.percentFromJiffies(jiffies, root._previousJiffies, now
                                                             - root._previousSampleMs);
            if (jiffies >= 0) {
                root._previousJiffies = jiffies;
                root._previousSampleMs = now;
            }
            root.lastSampleMs = now;
            root._sampleReadFinished();
        }
        onLoadFailed: root._sampleReadFinished()
    }

    Timer {
        id: sampleTimer

        interval: root.sampleIntervalMs
        repeat: true
        running: false
        onTriggered: root._sampleNow()
    }

    // ── Diagnostics ───────────────────────────────────────────────────────
    readonly property string diagnosticsDir: Paths.cacheHome + "/diagnostics"
    property string lastExportPath: ""
    property string lastExportError: ""
    property string _pendingExportPath: ""
    property string _pendingExportJson: ""

    function buildDiagnostics() {
        const metrics = ShellStartupService.startupMetrics();
        const now = Date.now();
        const deps = ClipboardService.dependencies || ({});
        return ShellDiagnostics.buildDiagnostics({
                                                     "homePath": Paths.homeDir,
                                                     "generatedAtMs": now,
                                                     "stage": metrics.stage,
                                                     "uptimeMs": now - ShellStartupService.initTimestampMs,
                                                     "firstFrameMs": metrics.first_frame_ms,
                                                     "readyMs": metrics.ready_ms,
                                                     "ipcReadyMs": metrics.ipc_ready_ms,
                                                     "compositorPresent": NiriService.isNiri,
                                                     "compositorConnected": NiriService.connected,
                                                     "compositorReconnecting": NiriService.reconnecting,
                                                     "samplingEnabled": root.samplingActive,
                                                     "samplingIntervalMs": root.sampleIntervalMs,
                                                     "samplingCpuPercent": root.cpuPercent,
                                                     "samplingRssKb": root.rssKb,
                                                     "samplingLastSampleMs": root.lastSampleMs,
                                                     "modules": [
                                                         {
                                                             "id": "bar",
                                                             "enabled": PersonalizationConfig.barEnabled,
                                                             "state": PersonalizationConfig.barEnabled
                                                                      ? "loaded" : "unloaded"
                                                         },
                                                         {
                                                             "id": "dock",
                                                             "enabled": DockService.enabled,
                                                             "state": DockService.enabled ? "loaded" :
                                                                                            "unloaded"
                                                         },
                                                         {
                                                             "id": "keystone",
                                                             "enabled": PersonalizationConfig.keystoneEnabled,
                                                             "state": PersonalizationConfig.keystoneEnabled
                                                                      ? "loaded" : "unloaded"
                                                         },
                                                         {
                                                             "id": "overview",
                                                             "enabled": PersonalizationConfig.overviewEnabled,
                                                             "state": PersonalizationConfig.overviewEnabled
                                                                      ? "loaded" : "unloaded"
                                                         },
                                                         {
                                                             "id": "clipboard",
                                                             "enabled": true,
                                                             "state": ClipboardService.available ? "ready" :
                                                                                                   "degraded"
                                                         },
                                                         {
                                                             "id": "network",
                                                             "enabled": true,
                                                             "state": NetworkService.available ? "ready" :
                                                                                                 "degraded"
                                                         },
                                                         {
                                                             "id": "bluetooth",
                                                             "enabled": true,
                                                             "state": BluetoothService.available ? "ready" :
                                                                                                   "degraded"
                                                         },
                                                         {
                                                             "id": "system-monitor",
                                                             "enabled": true,
                                                             "state": SystemMonitorService.state
                                                         }
                                                     ],
                                                     "dependencies": [
                                                         {
                                                             "id": "wl-copy",
                                                             "available": deps.wlCopy === true,
                                                             "probed": true
                                                         },
                                                         {
                                                             "id": "wl-paste",
                                                             "available": deps.wlPaste === true,
                                                             "probed": true
                                                         },
                                                         {
                                                             "id": "cliphist",
                                                             "available": deps.cliphist === true,
                                                             "probed": true
                                                         },
                                                         {
                                                             "id": "hyprpicker",
                                                             "available": ColorPickerService.available,
                                                             "probed": ColorPickerService.probeFinished
                                                         },
                                                         {
                                                             "id": "key-cli",
                                                             "available": SystemMonitorService.ready,
                                                             "probed": SystemMonitorService.hasData
                                                                       || SystemMonitorService.state
                                                                       !== "idle"
                                                         }
                                                     ],
                                                     "errors": [
                                                         {
                                                             "source": "niri",
                                                             "message": NiriService.configError
                                                         },
                                                         {
                                                             "source": "dock",
                                                             "message": DockService.configError
                                                         },
                                                         {
                                                             "source": "system-monitor",
                                                             "message": SystemMonitorService.errorMessage
                                                         },
                                                         {
                                                             "source": "theme",
                                                             "message": ThemeService.paletteError
                                                         }
                                                     ],
                                                     "paths": {
                                                         "config": Paths.configHome,
                                                         "data": Paths.dataHome,
                                                         "state": Paths.stateHome,
                                                         "cache": Paths.cacheHome,
                                                         "diagnostics": root.diagnosticsDir
                                                     }
                                                 });
    }

    // Sanitized by construction: the payload leaves ShellDiagnostics.buildDiagnostics()
    // with home paths masked, truncated strings and no environment variables
    // or configuration contents. Used by both the export and the IPC target.
    function diagnosticsJson() {
        return JSON.stringify(root.buildDiagnostics(), null, 2);
    }

    function exportDiagnostics() {
        if (ensureDiagnosticsDir.running)
            return false;
        root.lastExportError = "";
        root.lastExportPath = "";
        const stamp = new Date().toISOString().replace(/[:.]/g, "-");
        root._pendingExportPath = root.diagnosticsDir + "/nyxuri-shell-" + stamp + ".json";
        root._pendingExportJson = root.diagnosticsJson();
        ensureDiagnosticsDir.command = ["mkdir", "-p", root.diagnosticsDir];
        ensureDiagnosticsDir.running = true;
        return true;
    }

    function _finishExport(exitCode) {
        const target = root._pendingExportPath;
        const json = root._pendingExportJson;
        root._pendingExportPath = "";
        root._pendingExportJson = "";
        if (exitCode !== 0 || target === "" || json === "") {
            root.lastExportError = I18n.tr("Could not create the diagnostics directory");
            return;
        }
        root.lastExportPath = target;
        exportFile.path = target;
        exportFile.setText(json);
    }

    Process {
        id: ensureDiagnosticsDir

        onExited: exitCode => root._finishExport(exitCode)
    }

    FileView {
        id: exportFile

        atomicWrites: true
        onSaveFailed: {
            root.lastExportPath = "";
            root.lastExportError = I18n.tr("Could not write the diagnostics file");
        }
    }

    Component.onDestruction: {
        sampleTimer.stop();
        root._clearSamples();
        root.pageMounted = false;
        if (ensureDiagnosticsDir)
            ensureDiagnosticsDir.running = false;
        root._pendingExportPath = "";
        root._pendingExportJson = "";
    }
}
