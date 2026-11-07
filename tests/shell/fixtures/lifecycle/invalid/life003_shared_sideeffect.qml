import QtQuick
import Quickshell.Io
import qs.services

Item {
    id: root

    Process {
        id: badProcess
        command: ["uname", "-a"]
    }
}
