pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Fixture: a view file with a FileView in the UI layer must trip LIFE008.
QtObject {
    id: root

    property string scheme: ""

    FileView {
        path: "/tmp/something.json"
        onLoaded: root.scheme = "loaded"
    }
}
