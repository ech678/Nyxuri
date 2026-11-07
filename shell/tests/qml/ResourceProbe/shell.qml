import QtQuick
import Quickshell
import Quickshell.Io
import ResourceProbe

ShellRoot {
    id: root

    property int phase: 0

    Timer {
        id: driver
        interval: 10
        repeat: true
        running: true
        onTriggered: root.checkResourceStates()
    }

    Timer {
        id: controlledTimer
        interval: 1000
        repeat: true
        running: false
    }

    Process {
        id: controlledProcess
        command: ["sleep", "5"]
        running: false
    }

    function fail(reason) {
        console.error("RESOURCE_PROBE_FAIL", reason);
        Qt.exit(1);
    }

    function expectState(states, kind, running, stopped) {
        const state = states[kind];
        return state && state.total === 1 && state.running === running && state.stopped === stopped
                && state.unknown === 0;
    }

    function checkResourceStates() {
        const metrics = ShellStartupService.startupMetrics();
        const resources = metrics.qml_resources;
        const states = resources.states;
        if (root.phase === 0) {
            if (!expectState(states, "timer", 0, 1) || !expectState(states, "process", 0, 1)) {
                root.fail("registered resources did not start stopped");
                return;
            }
            controlledTimer.running = true;
            controlledProcess.running = true;
            root.phase = 1;
            return;
        }

        if (root.phase === 1 && controlledTimer.running && controlledProcess.running) {
            if (!expectState(states, "timer", 1, 0) || !expectState(states, "process", 1, 0)) {
                root.fail("running transition was not exposed over IPC metrics");
                return;
            }
            console.log("RESOURCE_PROBE_STATE", JSON.stringify({
                "active": states,
                "status": resources.status,
                "states_status": resources.states_status
            }));
            controlledTimer.running = false;
            controlledProcess.running = false;
            root.phase = 2;
            return;
        }

        if (root.phase === 2 && !controlledTimer.running && !controlledProcess.running) {
            if (!expectState(states, "timer", 0, 1) || !expectState(states, "process", 0, 1)) {
                root.fail("stopped transition was not exposed over IPC metrics");
                return;
            }
            console.log("RESOURCE_PROBE_PASS", JSON.stringify({
                "active": {"timer": 1, "process": 1},
                "inactive": {"timer": 1, "process": 1},
                "states": states
            }));
            Qt.quit();
        }
    }

    Component.onCompleted: {
        ShellStartupService.registerQmlResource("ResourceProbe", "timer", controlledTimer);
        ShellStartupService.registerQmlResource("ResourceProbe", "process", controlledProcess);
    }

    Component.onDestruction: {
        ShellStartupService.unregisterQmlResources("ResourceProbe", [
            {"object": controlledTimer}, {"object": controlledProcess}
        ]);
        controlledTimer.stop();
        controlledProcess.running = false;
    }
}
