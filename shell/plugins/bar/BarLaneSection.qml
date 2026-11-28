import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

// D4e list-based lane editor (dux WidgetsTabSection lineage, Nexus ConnectedRect
// skin): renders one bar zone's entries as reorderable rows with inline enable
// switch, spacer size stepper, per-row editor click, delete button, and an
// expandable per-lane overflow setting card.
ColumnLayout {
    id: root

    required property string zone // "left" | "middle" | "right"
    required property string title
    required property var entries
    required property var widgetCatalog
    property var dragCoordinator: null

    property bool overflowExpanded: false
    readonly property string overflowKey: root.zone + "OverflowMode"
    readonly property string overflowMode: PersonalizationConfig.barAxes[root.overflowKey] ?? "auto"
    readonly property bool overflowModified: root.overflowMode !== "auto"
    // D4g batch two: the lane editor edits the selected bar; its orientation
    // decides whether rail-less widgets get the capability note.
    readonly property bool barVertical: PersonalizationConfig.barAxes.position === "left" || PersonalizationConfig.barAxes.position === "right"

    signal addRequested(string zone)
    signal configureRequested(string entryUid)

    function entrySubtitle(entry): string {
        const parts = [];
        if (entry.enabled === false)
            parts.push(I18n.tr("Hidden"));
        const ov = entry.overrides || {};
        if (ov.overflowMode === "always")
            parts.push(I18n.tr("Always in overflow"));
        else if (ov.overflowMode === "bar")
            parts.push(I18n.tr("Pinned in bar"));
        if (root.barVertical && !root.widgetCatalog.supportsVertical(entry.widgetId))
            parts.push(I18n.tr("Not available on a vertical bar"));
        if (entry.widgetId === "spacer")
            parts.push(Math.round(BarWidgetDefaults.option("spacer", entry, "size")) + " px");
        return parts.join(" • ");
    }

    function dropIndexAt(localY): int {
        if (!Array.isArray(root.entries) || root.entries.length === 0)
            return 0;
        let currentIndex = 0;
        for (let i = 0; i < rowsRepeater.count; i += 1) {
            const row = rowsRepeater.itemAt(i);
            if (!row)
                continue;
            const midpoint = row.y + row.height / 2;
            if (localY < midpoint)
                return currentIndex;
            currentIndex += 1;
        }
        return root.entries.length;
    }

    function containsOverlayPoint(overlay, overlayX, overlayY): bool {
        const pt = root.mapFromItem(overlay, overlayX, overlayY);
        return pt.x >= 0 && pt.x <= root.width && pt.y >= 0 && pt.y <= root.height;
    }

    function insertionIndexFromOverlay(overlay, overlayY): int {
        const pt = rowsHost.mapFromItem(overlay, 0, overlayY);
        return root.dropIndexAt(pt.y);
    }

    Layout.fillWidth: true
    spacing: NexusStyle.padding.extraSmall / 2

    PreferenceHeader {
        text: root.title

        IconButton {
            Layout.alignment: Qt.AlignVCenter
            width: NexusStyle.icon.small + NexusStyle.padding.small
            height: NexusStyle.icon.small + NexusStyle.padding.small
            controlSize: NexusStyle.icon.small + NexusStyle.padding.small
            iconSize: NexusStyle.icon.small
            iconName: "more_horiz"
            selected: root.overflowExpanded
            accessibleName: I18n.tr("Overflow settings")
            tooltipText: accessibleName
            onClicked: root.overflowExpanded = !root.overflowExpanded
        }
    }

    Item {
        Layout.fillWidth: true
        implicitHeight: root.overflowExpanded ? overflowGroup.implicitHeight : 0
        height: implicitHeight
        clip: true
        visible: height > 0 || root.overflowExpanded

        Behavior on implicitHeight {
            NumberAnimation {
                duration: Appearance.animation.expressiveDefaultSpatial.duration
                easing.type: Appearance.animation.expressiveDefaultSpatial.type
                easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
            }
        }

        PreferenceGroup {
            id: overflowGroup

            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right

            PreferenceToggle {
                id: autoOverflowToggle

                text: I18n.tr("Auto overflow")
                subtext: I18n.tr("Widgets move into the overflow menu when space runs out")
                checked: root.overflowMode !== "bar"
                modified: root.overflowModified
                onToggled: PersonalizationConfig.setBarLaneOverflowMode(root.zone, autoOverflowToggle.checked ? "auto" : "bar")
                onResetRequested: PersonalizationConfig.setBarLaneOverflowMode(root.zone, "auto")
            }
        }
    }

    ColumnLayout {
        id: rowsHost

        Layout.fillWidth: true
        spacing: NexusStyle.padding.extraSmall / 2

        ConnectedRect {
            visible: root.entries.length === 0
            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: emptyLabel.implicitHeight + NexusStyle.padding.medium * 2
            color: root.dragCoordinator && root.dragCoordinator.active && root.dragCoordinator.targetZone === root.zone ? Appearance.m3colors.m3secondaryContainer : Appearance.m3colors.m3surfaceContainer

            StyledText {
                id: emptyLabel

                anchors.centerIn: parent
                text: I18n.tr("No widgets — drag here or click Add")
                color: Appearance.m3colors.m3outline
                font.pixelSize: NexusStyle.font.bodySmall
            }
        }

        Repeater {
            id: rowsRepeater

            model: root.entries

            ConnectedRect {
                id: widgetRow

                required property var modelData
                required property int index

                readonly property var catalogItem: root.widgetCatalog.byId(modelData.widgetId)
                readonly property string subtextLabel: root.entrySubtitle(modelData)
                readonly property bool isSpacer: modelData.widgetId === "spacer"
                readonly property bool isDraggingMe: root.dragCoordinator && root.dragCoordinator.active && root.dragCoordinator.dragUid === modelData.uid

                first: index === 0
                last: index === root.entries.length - 1
                Layout.fillWidth: true
                implicitHeight: rowLayout.implicitHeight + NexusStyle.padding.medium * 2
                opacity: widgetRow.isDraggingMe ? 0.35 : 1

                StateLayer {
                    anchors.fill: parent
                    layerRadius: (widgetRow.first || widgetRow.last) ? NexusStyle.rounding.extraLarge : NexusStyle.rounding.extraSmall
                    color: Appearance.m3colors.m3onSurface
                    hovered: rowClickArea.containsMouse
                    pressed: rowClickArea.pressed
                }

                MouseArea {
                    id: rowClickArea

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.configureRequested(widgetRow.modelData.uid)
                }

                RowLayout {
                    id: rowLayout

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: NexusStyle.padding.medium
                    anchors.rightMargin: NexusStyle.padding.largeIncreased
                    spacing: NexusStyle.padding.small

                    Item {
                        id: dragHandle

                        Layout.preferredWidth: NexusStyle.icon.medium + NexusStyle.padding.small
                        Layout.preferredHeight: NexusStyle.icon.medium + NexusStyle.padding.small

                        MaterialSymbol {
                            anchors.centerIn: parent
                            text: "drag_indicator"
                            iconSize: NexusStyle.icon.small
                            color: Appearance.m3colors.m3onSurfaceVariant
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.OpenHandCursor
                            preventStealing: true
                            onPressed: mouse => {
                                if (!root.dragCoordinator)
                                    return;
                                const globalPt = dragHandle.mapToItem(null, mouse.x, mouse.y);
                                root.dragCoordinator.beginDrag(widgetRow.modelData.uid, widgetRow.modelData.widgetId, root.widgetCatalog.displayName(widgetRow.catalogItem), widgetRow.catalogItem.icon || "widgets", root.zone, widgetRow.index, globalPt);
                            }
                            onPositionChanged: mouse => {
                                if (!root.dragCoordinator || !root.dragCoordinator.active)
                                    return;
                                const globalPt = dragHandle.mapToItem(null, mouse.x, mouse.y);
                                root.dragCoordinator.updateDrag(globalPt);
                            }
                            onReleased: {
                                if (root.dragCoordinator && root.dragCoordinator.active)
                                    root.dragCoordinator.finishDrag();
                            }
                            onCanceled: {
                                if (root.dragCoordinator && root.dragCoordinator.active)
                                    root.dragCoordinator.cancelDrag();
                            }
                        }
                    }

                    MaterialSymbol {
                        text: widgetRow.catalogItem.icon || "widgets"
                        iconSize: NexusStyle.icon.medium
                        fill: 1
                        color: widgetRow.modelData.enabled !== false ? Appearance.m3colors.m3primary : Appearance.m3colors.m3onSurfaceVariant
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        StyledText {
                            Layout.fillWidth: true
                            text: root.widgetCatalog.displayName(widgetRow.catalogItem)
                            color: widgetRow.modelData.enabled !== false ? Appearance.m3colors.m3onSurface : Appearance.m3colors.m3onSurfaceVariant
                            font.pixelSize: NexusStyle.font.bodyMedium
                            elide: Text.ElideRight
                        }

                        StyledText {
                            Layout.fillWidth: true
                            visible: widgetRow.subtextLabel.length > 0
                            text: widgetRow.subtextLabel
                            color: Appearance.m3colors.m3outline
                            font.pixelSize: NexusStyle.font.labelSmall
                            elide: Text.ElideRight
                        }
                    }

                    MaterialStepper {
                        visible: widgetRow.isSpacer
                        Layout.alignment: Qt.AlignVCenter
                        implicitWidth: 120
                        value: Math.round(BarWidgetDefaults.option("spacer", widgetRow.modelData, "size"))
                        from: 4
                        to: 200
                        stepSize: 4
                        onValueModified: next => PersonalizationConfig.setBarEntryOverride(widgetRow.modelData.uid, "size", next === 20 ? undefined : next)
                    }

                    MaterialSymbol {
                        text: "chevron_right"
                        iconSize: NexusStyle.icon.small
                        color: Appearance.m3colors.m3onSurfaceVariant
                    }

                    StyledSwitch {
                        id: entryEnableSwitch

                        visible: !widgetRow.isSpacer
                        checked: widgetRow.modelData.enabled !== false
                        onToggled: PersonalizationConfig.setBarEntryEnabled(widgetRow.modelData.uid, entryEnableSwitch.checked)
                    }

                    IconButton {
                        Layout.alignment: Qt.AlignVCenter
                        width: NexusStyle.icon.small + NexusStyle.padding.small
                        height: NexusStyle.icon.small + NexusStyle.padding.small
                        controlSize: NexusStyle.icon.small + NexusStyle.padding.small
                        iconSize: NexusStyle.icon.small
                        iconName: "close"
                        iconColor: Appearance.m3colors.m3error
                        accessibleName: I18n.tr("Remove widget")
                        tooltipText: accessibleName
                        onClicked: PersonalizationConfig.removeBarEntry(widgetRow.modelData.uid)
                    }
                }
            }
        }
    }

    RippleButton {
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: NexusStyle.padding.extraSmall
        buttonText: I18n.tr("Add widget")
        buttonRadius: NexusStyle.rounding.full
        horizontalPadding: NexusStyle.padding.large
        verticalPadding: NexusStyle.padding.small
        colBackground: Appearance.m3colors.m3secondaryContainer
        colBackgroundHover: Appearance.m3colors.m3secondaryContainer
        onClicked: root.addRequested(root.zone)

        contentItem: RowLayout {
            spacing: NexusStyle.padding.small

            MaterialSymbol {
                text: "add"
                iconSize: NexusStyle.icon.small
                color: Appearance.m3colors.m3onSecondaryContainer
            }

            StyledText {
                text: I18n.tr("Add widget")
                color: Appearance.m3colors.m3onSecondaryContainer
                font.pixelSize: NexusStyle.font.labelLarge
                font.weight: NexusStyle.font.labelLargeWeight
            }
        }
    }
}
