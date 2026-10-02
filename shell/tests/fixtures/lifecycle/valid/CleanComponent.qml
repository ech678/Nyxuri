import QtQuick
import Quickshell
import Quickshell.Io
import qs.app

Item {
    id: root

    property bool active: false

    function triggerAction() {
        ActionGateway.execute(["notify-send", "Hello"], "clean-component");
    }

    Timer {
        id: periodicTimer
        interval: 1000
        repeat: true
        running: root.active
        onTriggered: console.log("tick")
    }

    Process {
        id: workerProcess
        command: ["echo", "test"]
    }

    Component.onDestruction: {
        periodicTimer.stop();
        if (workerProcess.running) {
            workerProcess.running = false;
        }
    }
}
