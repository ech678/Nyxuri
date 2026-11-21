import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Modules tab of the Bar page: what lives IN the bar. Wraps the drag card
// (BarComponentsCard); the two drag coordinators anchor to this wrapper so
// the drag ghost paints above anything below the card.
//
// D4b: the widget-scoped setting groups (Workspaces / Utility buttons /
// Resources / Tray rows) retired — every per-widget axis moved to the
// lane entries and is edited on the per-instance page the chip gear opens
// (BarWidgetPage). The end4 `isUsed` gate concept retired with them: a
// widget's settings now exist exactly while its entry exists.
Item {
    id: root

    // The island is a bar layout part, so its entry row rides this tab; the
    // page owns the bar.island route, so the button asks instead of routing.
    signal islandRequested

    // D4b: chip gear → per-instance editor (GeneralBarPage owns the
    // section switch).
    signal widgetEditorRequested(string entryUid)

    // Above the tab-host default so the coordinator ghosts paint over the
    // island entry rows one level up (the tab host itself carries the z).
    z: 1
    implicitHeight: modulesColumn.implicitHeight

    ColumnLayout {
        id: modulesColumn

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: parent.width
        spacing: NexusStyle.padding.extraSmall / 2

        BarComponentsCard {
            id: componentsCard

            zoneCoordinator: dragCoordinator
            quickSettingsCoordinator: quickSettingsDragCoordinator
            onWidgetConfigureRequested: entryUid => root.widgetEditorRequested(entryUid)
        }

        // Island (B1: the island is a bar layout part — one page). Rides the
        // Modules tab because it is content of the bar, not its frame.
        PreferenceHeader {
            first: true
            text: I18n.tr("Island")
        }

        PreferenceAction {
            first: true
            last: true
            icon: "toggle_off"
            text: I18n.tr("Island settings")
            subtext: I18n.tr("Visibility, satellite, indicators, and clock")
            onClicked: root.islandRequested()
        }
    }

    LayoutDragCoordinator {
        id: dragCoordinator

        anchors.fill: parent
        z: 1000
        fields: [componentsCard.leadingField, componentsCard.middleField, componentsCard.trailingField]
        // D4a: chip drags carry the entry uid (moves one instance with its
        // enabled/override state); a uid-less drop is a pool add.
        onDropped: (componentUid, componentId, targetZone, targetIndex) => {
            if (componentUid !== "")
                PersonalizationConfig.moveBarEntry(componentUid, targetZone, targetIndex);
            else
                PersonalizationConfig.addBarEntry(targetZone, componentId, targetIndex);
        }
    }

    LayoutDragCoordinator {
        id: quickSettingsDragCoordinator

        anchors.fill: parent
        z: 1001
        fields: [componentsCard.quickSettingsField]
        onDropped: (componentUid, componentId, targetZone, targetIndex) => PersonalizationConfig.moveQuickSettingsComponent(componentId, targetIndex)
    }
}
