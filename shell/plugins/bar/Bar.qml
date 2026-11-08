import QtQuick
import Quickshell
import qs.services

Item {
    id: root

    readonly property string edge: PersonalizationConfig.barPosition
    readonly property bool horizontal: edge === "top" || edge === "bottom"

    // B1 merge + B3-1 inline hosting: the island is a bar layout part
    // (componentId "island", see BarComponentLoader). The end4 capsule rides
    // the bar canvas; the legacy styles (bangs/pill/long) keep their own
    // top-layer window until B4 retires them (ROADMAP D4).
    //
    // The gate waits for the config store: before it loads, islandStyle still
    // holds whatever the file will overwrite, and both island hosts would
    // register the same IPC target for that instant.
    readonly property bool legacyIsland: PersonalizationConfig.ready
                                         && PersonalizationConfig.islandEnabled
                                         && PersonalizationConfig.islandStyle !== "end4"

    Loader {
        active: root.legacyIsland
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
