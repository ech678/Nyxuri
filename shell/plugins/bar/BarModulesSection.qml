import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Modules tab of the Bar page (D4e e4 list-based editor, dux WidgetsTab
// lineage): renders the three bar lanes via BarLaneSection with cross-lane
// drag reordering, lane-level overflow settings, widget picker dialog,
// quick settings pool card, and the routed Island entry.
Item {
    id: root

    signal islandRequested
    signal widgetEditorRequested(string entryUid)

    readonly property bool horizontalBar: PersonalizationConfig.barPosition === "top" || PersonalizationConfig.barPosition === "bottom"

    BarWidgetCatalog {
        id: widgetCatalog
    }

    // Cross-lane drag state owned at the section wrapper so the floating ghost
    // paints over all three lanes and sibling cards.
    QtObject {
        id: listDrag

        property bool active: false
        property string dragUid: ""
        property string dragId: ""
        property string dragLabel: ""
        property string dragIcon: "widgets"
        property string sourceZone: ""
        property int sourceIndex: -1
        property string targetZone: ""
        property int targetIndex: -1
        property real pointerX: 0
        property real pointerY: 0

        function beginDrag(uid, widgetId, label, icon, zone, index, globalPoint): void {
            active = true;
            dragUid = uid;
            dragId = widgetId;
            dragLabel = label;
            dragIcon = icon;
            sourceZone = zone;
            sourceIndex = index;
            updateDrag(globalPoint);
        }

        function updateDrag(globalPoint): void {
            if (!active)
                return;
            const local = root.mapFromItem(null, globalPoint.x, globalPoint.y);
            pointerX = local.x;
            pointerY = local.y;
            const sections = [leftLane, middleLane, rightLane];
            let matched = null;
            for (let i = 0; i < sections.length; i += 1) {
                if (sections[i].containsOverlayPoint(root, pointerX, pointerY)) {
                    matched = sections[i];
                    break;
                }
            }
            if (!matched) {
                targetZone = "";
                targetIndex = -1;
                return;
            }
            targetZone = matched.zone;
            targetIndex = matched.insertionIndexFromOverlay(root, pointerY);
        }

        function finishDrag(): void {
            const wasActive = active;
            const uid = dragUid;
            const zone = targetZone;
            let index = targetIndex;
            const srcZone = sourceZone;
            const srcIdx = sourceIndex;
            cancelDrag();
            if (!wasActive || !uid || !zone || index < 0)
                return;
            if (zone === srcZone && srcIdx >= 0 && index > srcIdx)
                index -= 1;
            PersonalizationConfig.moveBarEntry(uid, zone, index);
        }

        function cancelDrag(): void {
            active = false;
            dragUid = "";
            dragId = "";
            dragLabel = "";
            dragIcon = "widgets";
            sourceZone = "";
            sourceIndex = -1;
            targetZone = "";
            targetIndex = -1;
        }
    }

    function openPickerFor(zone): void {
        widgetPicker.targetZone = zone;
        widgetPicker.open();
    }

    z: 1
    implicitHeight: modulesColumn.implicitHeight

    ColumnLayout {
        id: modulesColumn

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: parent.width
        spacing: NexusStyle.padding.small

        PreferenceHeader {
            first: true
            text: I18n.tr("Lanes")
            showReset: true
            resetText: I18n.tr("Reset widgets to default")
            onResetRequested: PersonalizationConfig.resetBarLanes()
        }

        StyledText {
            id: componentsHint

            Layout.fillWidth: true
            Layout.leftMargin: NexusStyle.padding.extraSmall
            Layout.rightMargin: NexusStyle.padding.extraSmall
            text: I18n.tr("Drag the handle to reorder across lanes, tap a widget for its settings, or toggle visibility")
            color: Appearance.m3colors.m3onSurfaceVariant
            font.pixelSize: NexusStyle.font.bodySmall
            wrapMode: Text.Wrap

            SettingsSearchAnchor {
                target: componentsHint
                anchorId: "bar.modules.components"
            }
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: NexusStyle.padding.extraSmall
            Layout.rightMargin: NexusStyle.padding.extraSmall
            visible: !root.horizontalBar
            text: I18n.tr("The island stays hidden on a vertical bar for now")
            color: Appearance.m3colors.m3onSurfaceVariant
            font.pixelSize: NexusStyle.font.bodySmall
            wrapMode: Text.Wrap
        }

        BarLaneSection {
            id: leftLane

            zone: "left"
            title: root.horizontalBar ? I18n.tr("Left") : I18n.tr("Top")
            entries: PersonalizationConfig.barLayoutEntriesLeft
            widgetCatalog: widgetCatalog
            dragCoordinator: listDrag
            onAddRequested: zone => root.openPickerFor(zone)
            onConfigureRequested: uid => root.widgetEditorRequested(uid)
        }

        BarLaneSection {
            id: middleLane

            zone: "middle"
            title: I18n.tr("Center")
            entries: PersonalizationConfig.barLayoutEntriesMiddle
            widgetCatalog: widgetCatalog
            dragCoordinator: listDrag
            onAddRequested: zone => root.openPickerFor(zone)
            onConfigureRequested: uid => root.widgetEditorRequested(uid)
        }

        BarLaneSection {
            id: rightLane

            zone: "right"
            title: root.horizontalBar ? I18n.tr("Right") : I18n.tr("Bottom")
            entries: PersonalizationConfig.barLayoutEntriesRight
            widgetCatalog: widgetCatalog
            dragCoordinator: listDrag
            onAddRequested: zone => root.openPickerFor(zone)
            onConfigureRequested: uid => root.widgetEditorRequested(uid)
        }

        QuickSettingsListCard {
            Layout.topMargin: NexusStyle.padding.small
        }

        PreferenceHeader {
            text: I18n.tr("Island")
        }

        PreferenceGroup {
            PreferenceAction {
                icon: "toggle_off"
                text: I18n.tr("Island settings")
                subtext: I18n.tr("Visibility, satellite, indicators, and clock")
                onClicked: root.islandRequested()
            }
        }
    }

    // Floating drag preview ghost above all lane lists.
    ConnectedRect {
        visible: listDrag.active
        first: true
        last: true
        x: Math.max(0, Math.min(root.width - width, listDrag.pointerX - width / 2))
        y: listDrag.pointerY - height / 2
        width: Math.min(260, root.width * 0.7)
        implicitHeight: ghostRow.implicitHeight + NexusStyle.padding.small * 2
        height: implicitHeight
        color: Appearance.m3colors.m3secondaryContainer
        opacity: 0.92
        z: 1000

        RowLayout {
            id: ghostRow

            anchors.fill: parent
            anchors.leftMargin: NexusStyle.padding.medium
            anchors.rightMargin: NexusStyle.padding.medium
            spacing: NexusStyle.padding.small

            MaterialSymbol {
                text: listDrag.dragIcon
                iconSize: NexusStyle.icon.medium
                fill: 1
                color: Appearance.m3colors.m3onSecondaryContainer
            }

            StyledText {
                Layout.fillWidth: true
                text: listDrag.dragLabel
                color: Appearance.m3colors.m3onSecondaryContainer
                font.pixelSize: NexusStyle.font.bodyMedium
                elide: Text.ElideRight
            }
        }
    }

    BarWidgetPickerPopup {
        id: widgetPicker

        onWidgetSelected: (widgetId, targetZone) => PersonalizationConfig.addBarEntry(targetZone, widgetId)
    }
}
