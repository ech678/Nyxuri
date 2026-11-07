import QtQuick
import Quickshell.Io

Item {
    id: root

    Timer {
        id: leakTimer
        interval: 1000
        repeat: true
        running: true
    }

    Process {
        id: leakProcess
        command: ["sleep", "100"]
    }
}
