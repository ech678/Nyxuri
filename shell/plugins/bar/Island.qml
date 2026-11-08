// Island as a bar layout part (B1 merge, B3-1 inline hosting). The unit owns
// its IPC face here; the capsule body itself is the end4-pC DynamicIsland
// fork in ./island/end4/. The bar canvas hosts it, so the island no longer
// runs its own layer window when it is selected as the layout widget.
//
// The legacy styles (bangs/pill/long) still live behind their own layer
// window (island/Island.qml) until B4 retires them — D4 freeze. Only the end4
// capsule is hostable inline today.
import QtQuick
import Quickshell.Io
import qs.services
import "./island/end4"

Item {
    id: root

    property bool vertical: false

    readonly property bool end4Style: PersonalizationConfig.islandStyle === "end4"
    readonly property bool searchActionsAvailable: islandBody.item !== null

    implicitWidth: islandBody.item ? islandBody.item.implicitWidth : 0
    implicitHeight: islandBody.item ? islandBody.item.implicitHeight : 0

    // The bar layout only ever instantiates this when the end4 style is
    // selected; other styles keep their own window (see Bar.qml).
    Loader {
        id: islandBody

        active: root.end4Style
        sourceComponent: end4Capsule
    }

    Component {
        id: end4Capsule

        DynamicIsland {
            vertical: root.vertical
        }
    }

    IpcHandler {
        target: "island"

        function currentStyle(): string {
            return PersonalizationConfig.islandStyle;
        }
    }
}
