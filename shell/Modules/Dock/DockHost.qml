import QtQuick
import Quickshell
import qs.Services

Item {
    id: root

    // Recreate the layer surface when its anchoring topology changes.
    Variants {
        model: DockService.enabled && DockService.position === "bottom" ? Quickshell.screens : []
        DockSurface {
            required property var modelData
            screen: modelData
            edge: "bottom"
        }
    }
    Variants {
        model: DockService.enabled && DockService.position === "left" ? Quickshell.screens : []
        DockSurface {
            required property var modelData
            screen: modelData
            edge: "left"
        }
    }
    Variants {
        model: DockService.enabled && DockService.position === "right" ? Quickshell.screens : []
        DockSurface {
            required property var modelData
            screen: modelData
            edge: "right"
        }
    }
}
