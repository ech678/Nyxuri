import QtQuick
import Quickshell
import qs.app.services

Scope {
    Variants {
        model: RegionSelectionService.active ? Quickshell.screens : []

        delegate: Loader {
            id: selectorLoader
            required property var modelData

            active: RegionSelectionService.active
            sourceComponent: RegionSelectionWindow {
                targetScreen: selectorLoader.modelData
            }
        }
    }
}
