pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pipewire
import qs.services
import qs.commons.i18n

Singleton {
    id: root

    readonly property var oskCandidates: ["wvkbd-mobintl", "wvkbd", "squeekboard", "onboard"]
    readonly property var screenshotCandidates: ["nyxuri-screenshot"]
    readonly property var colorPickerCandidates: ["hyprpicker"]
    property int oskProbeIndex: -1
    property string oskBinary: ""
    property bool oskRunning: false
    property bool toolProbing: false
    property var pendingTool: null

    function toggleOsk() {
        if (root.oskBinary !== "") {
            root.oskRunning = !root.oskRunning;
            return;
        }
        if (root.oskProbeIndex >= 0)
            return;
        root.startOskProbe(0);
    }

    function startOskProbe(index) {
        root.oskProbeIndex = index;
        oskProbe.started = false;
        oskProbe.command = ["which", root.oskCandidates[index]];
        oskProbe.running = false;
        oskProbe.running = true;
    }

    Process {
        id: oskProbe

        property bool started: false

        onStarted: oskProbe.started = true
        onRunningChanged: if (!running && !started)
                              Qt.callLater(() => oskProbe.advance(-1))

        stdout: StdioCollector {}
        onExited: exitCode => oskProbe.advance(exitCode)

        function advance(exitCode) {
            const index = root.oskProbeIndex;
            if (index < 0)
                return;
            if (exitCode === 0) {
                root.oskBinary = root.oskCandidates[index];
                root.oskProbeIndex = -1;
                root.oskRunning = true;
                return;
            }
            const next = index + 1;
            if (next >= root.oskCandidates.length) {
                root.oskProbeIndex = -1;
                console.warn("[GlobalActions] On-screen keyboard: no supported backend found");
                NotificationService.addLocal(I18n.tr("On-screen keyboard unavailable"),
                                             I18n.tr("No supported on-screen keyboard is installed."));
                return;
            }
            root.startOskProbe(next);
        }
    }

    Process {
        id: oskProcess

        property bool started: false

        running: root.oskRunning && root.oskBinary !== ""
        command: root.oskBinary === "" ? [] : [root.oskBinary]
        onStarted: oskProcess.started = true
        onRunningChanged: if (!running && !started && root.oskRunning) {
                              const attempted = oskProcess.command.join(" ");
                              root.oskRunning = false;
                              root.oskBinary = "";
                              console.warn("[GlobalActions] On-screen keyboard could not be started: "
                                           + attempted);
                          }
        onExited: {
            oskProcess.started = false;
            root.oskRunning = false;
        }
    }

    function dispatchTool(candidates, extraArgs, owner, missingTitle, missingBody) {
        if (root.toolProbing)
            return;
        root.toolProbing = true;
        root.pendingTool = {
            "candidates": candidates,
            "index": 0,
            "extraArgs": extraArgs,
            "owner": owner,
            "missingTitle": missingTitle,
            "missingBody": missingBody
        };
        root.probeTool(root.pendingTool);
    }

    function probeTool(pending) {
        toolProbe.started = false;
        toolProbe.command = ["which", pending.candidates[pending.index]];
        toolProbe.running = false;
        toolProbe.running = true;
    }

    Process {
        id: toolProbe

        property bool started: false

        onStarted: toolProbe.started = true
        onRunningChanged: if (!running && !started)
                              Qt.callLater(() => toolProbe.advance(-1))

        stdout: StdioCollector {}
        onExited: exitCode => toolProbe.advance(exitCode)

        function advance(exitCode) {
            const pending = root.pendingTool;
            if (!pending)
                return;
            if (exitCode === 0) {
                root.pendingTool = null;
                root.toolProbing = false;
                ActionGateway.execute([pending.candidates[pending.index]].concat(pending.extraArgs), pending.owner);
                return;
            }
            const next = pending.index + 1;
            if (next < pending.candidates.length) {
                pending.index = next;
                root.probeTool(pending);
                return;
            }
            root.pendingTool = null;
            root.toolProbing = false;
            console.warn("[GlobalActions] " + pending.owner + ": none of " + pending.candidates.join(", ")
                         + " is available");
            NotificationService.addLocal(pending.missingTitle, pending.missingBody);
        }
    }

    function runById(actionId, param) {
        if (actionId === "screenshot") {
            root.dispatchTool(root.screenshotCandidates, [], "bar.screenshot",
                              I18n.tr("Screenshot unavailable"),
                              I18n.tr("No screenshot tool is installed; nothing was captured."));
        } else if (actionId === "color-picker") {
            root.dispatchTool(root.colorPickerCandidates, ["-a"], "bar.colorpicker",
                              I18n.tr("Color picker unavailable"),
                              I18n.tr("Install hyprpicker to pick a color from the screen."));
        } else if (actionId === "toggle-mic-mute") {
            if (Pipewire.defaultAudioSource) {
                Pipewire.defaultAudioSource.muted = !Pipewire.defaultAudioSource.muted;
            }
        } else if (actionId === "toggle-osk") {
            root.toggleOsk();
        }
    }

    Component.onDestruction: {
        root.oskProbeIndex = -1;
        root.oskRunning = false;
        if (oskProbe.running)
            oskProbe.running = false;
        if (oskProcess.running)
            oskProcess.running = false;
    }
}
