// CompositorDriver (S0-5): the shell-facing compositor surface. Consumers
// bind to this singleton only; the niri implementation lives in the
// NiriDriver singleton, which no other live file may reference (contract:
// test_r4c_niri_single_runtime_entry). A future compositor is added as
// another driver behind this same face — that is the whole point of the
// split (T5 groundwork). Interface vocabulary stays desktop-intent; niri
// dialect stays in the driver file.

pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import qs.services

Singleton {
    id: root

    // --- Session & connection state ---
    readonly property bool available: NiriDriver.isNiri
    readonly property bool connected: NiriDriver.connected
    readonly property bool reconnecting: NiriDriver.reconnecting

    // --- Compositor version (probe result; consumers interpret it) ---
    readonly property string compositorVersion: NiriDriver.compositorVersion
    readonly property bool compositorVersionReady: NiriDriver.compositorVersionReady
    readonly property string compositorVersionError: NiriDriver.compositorVersionError

    // --- Capability flags (honest degradation, not wishful defaults) ---
    readonly property bool supportsMinimize: NiriDriver.supportsMinimize
    readonly property bool supportsMinimizeAnimation: NiriDriver.supportsMinimizeAnimation
    readonly property var minimizeEffects: NiriDriver.minimizeEffects

    // --- Mirrored state ---
    readonly property var workspaces: NiriDriver.workspaces
    readonly property string currentOutput: NiriDriver.currentOutput
    readonly property var outputs: NiriDriver.outputs
    readonly property var windows: NiriDriver.windows
    readonly property var focusedWindow: NiriDriver.focusedWindow
    readonly property bool inOverview: NiriDriver.inOverview
    readonly property bool configLoadFailed: NiriDriver.configLoadFailed
    readonly property string configError: NiriDriver.configError

    // --- Session verbs ---
    function toggleOverview() {
        return NiriDriver.toggleOverview();
    }

    function reconnect() {
        return NiriDriver.reconnect();
    }

    function refreshOutputs() {
        NiriDriver.refreshOutputs();
    }

    // End the compositor session (logout). Fire-and-forget: the request is
    // detached so it survives the shell's own teardown.
    function quitSession() {
        return NiriDriver.quitSession();
    }

    // Monitor power. Pass a callback(exitCode) for managed use (idle policy
    // needs the outcome); omit it for fire-and-forget (idle teardown).
    function setMonitorsPower(off, callback) {
        return NiriDriver.setMonitorsPower(off, callback);
    }

    // --- Window & workspace verbs ---
    function focusWorkspaceById(workspaceId) {
        return NiriDriver.focusWorkspaceById(workspaceId);
    }

    function focusWindow(windowId) {
        return NiriDriver.focusWindow(windowId);
    }

    function closeWindow(windowId) {
        return NiriDriver.closeWindow(windowId);
    }

    function minimizeWindow(windowId) {
        return NiriDriver.minimizeWindow(windowId);
    }

    function restoreWindow(windowId, output) {
        return NiriDriver.restoreWindow(windowId, output);
    }

    // Capability stubs: upstream niri exposes no IPC for these; the callers
    // (wallpaper parallax, dock minimize animation) degrade on `false`.
    function setFloatingParallaxOffsets(offsets) {
        return NiriDriver.setFloatingParallaxOffsets(offsets);
    }

    function setWindowAnimationTargets(screenName, targets) {
        return NiriDriver.setWindowAnimationTargets(screenName, targets);
    }

    // --- Queries ---
    function windowById(id) {
        return NiriDriver.windowById(id);
    }

    function workspacesForOutput(outputName) {
        return NiriDriver.workspacesForOutput(outputName);
    }

    function activeWorkspaceForOutput(outputName) {
        return NiriDriver.activeWorkspaceForOutput(outputName);
    }

    function windowsForWorkspace(wsId) {
        return NiriDriver.windowsForWorkspace(wsId);
    }

    function searchWindows(query) {
        return NiriDriver.searchWindows(query);
    }

    function outputSnapshot() {
        return NiriDriver.outputSnapshot();
    }
}
