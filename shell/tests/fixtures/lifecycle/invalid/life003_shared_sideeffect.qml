import QtQuick
import Quickshell.Io
import qs.app.services

Item {
    id: root

    Process {
        id: badProcess
        command: ["uname", "-a"]
    }
}
