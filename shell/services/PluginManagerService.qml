pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.services
import qs.commons

// PluginManagerService — coordinates third-party plugin lifecycle operations
// (add, remove, update) and config resets (P1 / lain-connect).
// Views never spawn processes themselves (LIFE008); all operations dispatch
// via parameter arrays to the nyxuri engine CLI (LIFE004).
Singleton {
    id: root

    readonly property bool busy: proc.running
    property string activeOp: ""
    property string targetPluginId: ""
    property string lastOutput: ""
    property string lastError: ""

    signal operationFinished(string op, string pluginId, bool success, string message)

    function installPlugin(source, enable) {
        if (root.busy || !source || String(source).trim() === "")
            return false;
        root._prepare("install", String(source).trim());
        const args = [Paths.binHome + "/nyxuri", "add", String(source).trim()];
        if (enable === true)
            args.push("--enable");
        proc.command = args;
        proc.running = true;
        watchdog.restart();
        LogService.info("plugins", "dispatch install: " + source);
        return true;
    }

    function updatePlugin(pluginId) {
        if (root.busy || !pluginId)
            return false;
        root._prepare("update", pluginId);
        proc.command = [Paths.binHome + "/nyxuri", "update", pluginId, "-y"];
        proc.running = true;
        watchdog.restart();
        LogService.info("plugins", "dispatch update: " + pluginId);
        return true;
    }

    function removePlugin(pluginId) {
        if (root.busy || !pluginId)
            return false;
        root._prepare("remove", pluginId);
        proc.command = [Paths.binHome + "/nyxuri", "remove", pluginId, "-y"];
        proc.running = true;
        watchdog.restart();
        LogService.info("plugins", "dispatch remove: " + pluginId);
        return true;
    }

    function resetPlugin(pluginId, domain) {
        if (root.busy || !pluginId)
            return false;
        // First reset schema keys in PluginSettings
        PluginSettings.resetPlugin(pluginId);
        root._prepare("reset", pluginId);
        // Dispatch form default reset if deployable
        proc.command = [Paths.binHome + "/nyxuri", "use", domain || pluginId, "default"];
        proc.running = true;
        watchdog.restart();
        LogService.info("plugins", "dispatch reset: " + pluginId);
        return true;
    }

    function openPluginDir(dir) {
        if (!dir)
            return false;
        ApplicationService.openUrl(Paths.fileUrl(dir));
        return true;
    }

    function _prepare(op, pluginId) {
        root.activeOp = op;
        root.targetPluginId = pluginId;
        root.lastOutput = "";
        root.lastError = "";
    }

    function _finish(code) {
        watchdog.stop();
        const stdoutText = (outCollector.text || "").trim();
        const stderrText = (errCollector.text || "").trim();
        root.lastOutput = stdoutText;
        const op = root.activeOp;
        const target = root.targetPluginId;

        if (code !== 0) {
            // For reset on pure-UI plugins that have no "default" form, the schema
            // settings reset already succeeded; do not treat missing form as fatal.
            if (op === "reset" && stdoutText.indexOf("没有名为 'default' 的形态") !== -1) {
                root.lastOutput = "Config reset to defaults.";
                root.operationFinished(op, target, true, root.lastOutput);
            } else {
                root.lastError = stderrText || stdoutText || ("Operation " + op + " failed (exit " + code + ")");
                LogService.error("plugins", root.lastError);
                root.operationFinished(op, target, false, root.lastError);
            }
        } else {
            root.operationFinished(op, target, true, stdoutText);
            LogService.info("plugins", "operation " + op + " succeeded for " + target);
        }
        root.activeOp = "";
        root.targetPluginId = "";
    }

    Process {
        id: proc

        stdout: StdioCollector {
            id: outCollector
        }
        stderr: StdioCollector {
            id: errCollector
        }
        onExited: (code, status) => root._finish(code)
    }

    Timer {
        id: watchdog

        interval: 120000
        onTriggered: {
            if (!proc.running)
                return;
            proc.running = false;
            root.lastError = "Plugin operation timed out";
            root.operationFinished(root.activeOp, root.targetPluginId, false, root.lastError);
            root.activeOp = "";
            root.targetPluginId = "";
        }
    }

    Component.onDestruction: {
        watchdog.stop();
        proc.running = false;
    }
}
