import QtQuick
import Quickshell
import qs.app.services

Item {
    id: root

    readonly property string edge: PersonalizationConfig.barPosition
    readonly property bool horizontal: edge === "top" || edge === "bottom"

    // Changing orientation changes the Variants model. Quickshell destroys
    // the old topology before creating the new per-output surface, so a
    // mapped horizontal layer surface is never mutated into a vertical one.
    Variants {
        model: PersonalizationConfig.barEnabled && root.horizontal ? Quickshell.screens : []

        HorizontalBarWindow {
            required property var modelData
            screen: modelData
            edge: root.edge
        }
    }

    Variants {
        model: PersonalizationConfig.barEnabled && !root.horizontal ? Quickshell.screens : []

        VerticalBarWindow {
            required property var modelData
            screen: modelData
            edge: root.edge
        }
    }
}
