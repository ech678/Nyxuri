import QtQuick
import Clavis.Cava

Item {
    id: root

    property bool active: false
    property int bars: 45
    readonly property bool available: cava.available
    readonly property var values: cava.values

    CavaProvider {
        id: cava

        active: root.active
        bars: root.bars
    }
}
