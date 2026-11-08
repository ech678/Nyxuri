import QtQuick
import Quickshell
import qs.services

Item {
    id: root

    readonly property string edge: PersonalizationConfig.barPosition
    readonly property bool horizontal: edge === "top" || edge === "bottom"

    // B1 transition: the island keeps its own top-layered windows but lives in
    // the bar unit, so `off shell.bar` takes it down too. Its switch is the
    // islandEnabled config gate (the ledger knows no island unit anymore).
    // B2 replaces this loader with the inline bar-canvas hosting.
    Loader {
        active: PersonalizationConfig.islandEnabled
        source: Qt.resolvedUrl("island/Island.qml")
    }

    // Changing orientation changes the Variants model. Quickshell destroys
    // the old topology before creating the new per-output surface, so a
    // mapped horizontal layer surface is never mutated into a vertical one.
    Variants {
        model: root.horizontal ? Quickshell.screens : []

        HorizontalBarWindow {
            required property var modelData
            screen: modelData
            edge: root.edge
        }
    }

    Variants {
        model: root.horizontal ? [] : Quickshell.screens

        VerticalBarWindow {
            required property var modelData
            screen: modelData
            edge: root.edge
        }
    }
}
