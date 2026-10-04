pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.shared.i18n

Singleton {
    id: root

    readonly property int supportedSchemaVersion: 1
    property string commandName: {
        const configured = String(Quickshell.env("CLAVIS_KEY") || "").trim();
        return configured !== "" ? configured : "key";
    }
    property var system: ({})
    property bool ready: false
    property bool _initializationStarted: false
    property string errorMessage: ""
    property var _uptimeConsumers: ({})
    property real _baseUptimeSeconds: 0
    property real uptimeSeconds: 0
    property bool _uptimeBaseReady: false
    readonly property bool uptimeActive: Object.keys(_uptimeConsumers).length > 0
    readonly property string accountName: system.systemUser || "user"
    readonly property string hostName: system.hostName || "host"
    readonly property string accountIdentity: accountName + "@" + hostName
    readonly property string wmName: system.wmName || "unknown"
    readonly property string shellName: system.shellName || "unknown"
    readonly property string kernelRelease: system.kernel || "unknown"
    readonly property string architecture: system.architecture || "unknown"
    readonly property string chassis: system.chassis || I18n.tr("Computer")
    readonly property string vendor: system.vendor || ""
    readonly property string productName: system.productName || ""
    readonly property string boardName: system.boardName || ""
    readonly property string biosVersion: system.biosVersion || ""
    readonly property string cpuModelName: system.cpuModelName || ""
    // Marketing name of the primary GPU. `key sysmon` reports only vendor and
    // driver ("AMD (amdgpu)"), which reads like a detection failure, so the
    // model string comes from lspci — the same source end4-pC's SystemInfo uses.
    // Empty when lspci is unavailable; callers fall back on the sysmon name.
    property string gpuModelName: ""
    readonly property int physicalCoreCount: Number(system.physicalCoreCount) || 0
    readonly property int logicalCpuCount: Number(system.logicalCpuCount) || 0
    readonly property real bootTimeMs: Number(system.bootTimeMs) || 0
    readonly property string osAgeText: system.osAgeText || ""
    readonly property string distroId: system.distroId || "linux"
    readonly property string distroName: system.osName || "Linux"
    readonly property string uptimeText: formatUptime(uptimeSeconds)

    function setUptimeConsumer(owner, active) {
        const key = String(owner || "").trim();
        if (key === "")
            return;

        const next = Object.assign({}, root._uptimeConsumers);
        if (active)
            next[key] = true;
        else
            delete next[key];
        root._uptimeConsumers = next;
    }

    function _startUptimeSession() {
        root._uptimeBaseReady = false;
        root.uptimeSeconds = 0;
        uptimeFile.path = "";
        uptimeFile.path = "/proc/uptime";
    }

    function _finishUptimeRead() {
        const fields = String(uptimeFile.text() || "").trim().split(/\s+/);
        const value = Number(fields[0]);
        if (!isFinite(value) || value < 0)
            return;

        root._baseUptimeSeconds = value;
        root.uptimeSeconds = value;
        root._uptimeBaseReady = true;
        monotonicTimer.restartMs();
    }

    function _updateUptime() {
        if (root._uptimeBaseReady)
            root.uptimeSeconds = root._baseUptimeSeconds + monotonicTimer.elapsedMs() / 1000;
    }

    function _consumeIdentity() {
        try {
            const payload = JSON.parse(identityOutput.text.trim());
            if (payload.schemaVersion !== root.supportedSchemaVersion || !payload.system
                    || typeof payload.system !== "object")
                throw new Error("schemaVersion or system field is invalid");

            root.system = payload.system;
            root.ready = true;
            root.errorMessage = "";
        } catch (error) {
            root.errorMessage = I18n.tr("Unable to read system identity");
            console.warn("SystemIdentityService:", error);
        }
    }

    function initialize() {
        if (root._initializationStarted)
            return;

        root._initializationStarted = true;
        identityProcess.command = [root.commandName, "sysmon", "system", "--format", "json"];
        identityProcess.running = true;
        // Deliberately its own process: lspci is unrelated to the key backend,
        // and a missing pciutils must not stall or fail the identity read.
        gpuProcess.running = true;
    }

    // `lspci -mm` quotes every field, so a vendor whose name contains spaces and
    // brackets ("[AMD/ATI]") stays a single field and the model can be taken by
    // position instead of by stripping prefixes with sed. Returns the model of
    // the first display-class device, or "" when there is nothing to report.
    function _parseGpuModel(output) {
        const lines = String(output || "").split("\n");
        for (let i = 0; i < lines.length; i++) {
            // match() with /g returns the *whole* match including quotes, so the
            // fields are positional: [0] class, [1] vendor, [2] device,
            // [3] subsystem vendor. Reading the class from [1] compares against
            // the vendor string instead, never matches a display class, and the
            // model quietly comes back empty.
            const fields = lines[i].match(/"((?:[^"\\]|\\.)*)"/g);
            if (!fields || fields.length < 4)
                continue;
            if (!/(vga|3d|display)/i.test(fields[0].slice(1, -1)))
                continue;
            return fields[2].slice(1, -1).trim();
        }
        return "";
    }

    function formatUptime(value) {
        const total = Math.max(0, Math.floor(Number(value) || 0));
        const days = Math.floor(total / 86400);
        const hours = Math.floor((total % 86400) / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        if (days > 0)
            return I18n.tr("%1 days %2 hours").arg(days).arg(hours);

        if (hours > 0)
            return I18n.tr("%1 hours %2 minutes").arg(hours).arg(minutes);

        return I18n.tr("%1 minutes").arg(minutes);
    }

    onUptimeActiveChanged: {
        if (uptimeActive) {
            root._startUptimeSession();
        } else {
            root._uptimeBaseReady = false;
            uptimeFile.path = "";
        }
    }
    Component.onCompleted: root.initialize()

    ElapsedTimer {
        id: monotonicTimer
    }

    Timer {
        interval: 1000
        repeat: true
        running: root.uptimeActive && root._uptimeBaseReady
        onTriggered: root._updateUptime()
    }

    FileView {
        id: uptimeFile

        path: ""
        watchChanges: false
        blockLoading: true
        onLoaded: root._finishUptimeRead()
        onLoadFailed: error => {
            return console.warn("SystemIdentityService /proc/uptime:", error);
        }
    }

    Process {
        id: identityProcess

        onExited: (exitCode, exitStatus) => {
            if (exitCode === 0)
                root._consumeIdentity();
            else
                root.errorMessage = I18n.tr("Unable to read system identity");
        }

        stdout: StdioCollector {
            id: identityOutput
        }

        stderr: StdioCollector {}
    }

    Process {
        id: gpuProcess

        // No `bash -c`: the pipe and sed of the upstream implementation are not
        // needed once lspci is asked for a machine-readable layout.
        command: ["lspci", "-mm"]

        onExited: exitCode => {
            if (exitCode === 0)
                root.gpuModelName = root._parseGpuModel(gpuOutput.text);
        }

        stdout: StdioCollector {
            id: gpuOutput
        }

        stderr: StdioCollector {}
    }

    Component.onDestruction: {
        if (identityProcess)
            identityProcess.running = false;
        if (gpuProcess)
            gpuProcess.running = false;
    }
}
