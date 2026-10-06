pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Fixture: a Service-suffixed domain file may own a Process; the UI-facing
// dispatch still routes through the Action Gateway with an owner.
QtObject {
    id: root

    function ping() {
        ActionGateway.execute(["notify-send", "hello"], "fixture:service");
    }

    Process {
        id: probe
        command: ["true"]
    }

    Component.onDestruction: {
        if (probe.running)
            probe.running = false;
    }
}
