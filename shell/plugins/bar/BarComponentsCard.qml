import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// The drag-to-reorder card of the Bar page's Modules tab: display toggles,
// the three bar zone lanes, and the quick settings pool. Split out of the
// pre-tab GeneralBarPage monolith. The field ids are aliased so the drag
// coordinators can live in the section wrapper that owns the whole overlay
// area (BarModulesSection) — the ghost must paint above sibling groups.
// Geometry: all four fields share one label column, so the field edges
// align across the lanes and the quick settings row; the three lanes read
// as one connected card (first / flat / last) and the quick settings row
// stays its own rounded single-row group.
ColumnLayout {
    id: root

    readonly property alias leadingField: leadingField
    readonly property alias middleField: middleField
    readonly property alias trailingField: trailingField
    readonly property alias quickSettingsField: quickSettingsField

    // Injected by BarModulesSection: the coordinators live one level up
    // (the section wrapper owns the overlay area), so the fields reach
    // them through explicit bindings — cross-file ids are not visible.
    required property var zoneCoordinator
    required property var quickSettingsCoordinator

    readonly property bool horizontalBar: PersonalizationConfig.barPosition === "top" || PersonalizationConfig.barPosition === "bottom"

    // D4a: the shared catalog (label/icon registration point) replaces the
    // services-side option list; displayName resolves lazily so
    // construction order cannot blank the labels.
    BarWidgetCatalog {
        id: widgetCatalog
    }

    Layout.fillWidth: true
    spacing: NexusStyle.padding.extraSmall / 2

    PreferenceToggle {
        id: namesToggle

        first: true
        text: I18n.tr("Show device names")
        checked: PersonalizationConfig.barShowNames
        onToggled: PersonalizationConfig.setBarShowNames(checked)

        SettingsSearchAnchor {
            id: searchAnchorComponents

            target: namesToggle
            anchorId: "bar.modules.components"
        }
    }

    PreferenceToggle {
        last: true
        text: I18n.tr("Show numeric values")
        checked: PersonalizationConfig.barShowValues
        onToggled: PersonalizationConfig.setBarShowValues(checked)
    }

    StyledText {
        Layout.fillWidth: true
        Layout.leftMargin: NexusStyle.padding.extraSmall
        Layout.rightMargin: NexusStyle.padding.extraSmall
        Layout.topMargin: NexusStyle.padding.extraSmall
        text: I18n.tr("Drag widgets between lanes to arrange the bar")
        color: Appearance.m3colors.m3onSurfaceVariant
        font.pixelSize: NexusStyle.font.bodySmall
        wrapMode: Text.Wrap
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

    ConnectedRect {
        id: leadingZoneRow

        Layout.fillWidth: true
        first: true
        implicitHeight: Math.max(zoneLeadingLabel.implicitHeight, leadingField.implicitHeight) + NexusStyle.padding.medium * 2

        RowLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            StyledText {
                id: zoneLeadingLabel

                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 10
                Layout.preferredWidth: 120
                text: root.horizontalBar ? I18n.tr("Left") : I18n.tr("Top")
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
            }

            SortableMultiSelectField {
                id: leadingField

                Layout.fillWidth: true
                values: PersonalizationConfig.barLayoutEntriesLeft
                options: widgetCatalog.options()
                allowDuplicates: true
                zone: "left"
                dragCoordinator: root.zoneCoordinator
                onToggled: componentId => PersonalizationConfig.addBarEntry(zone, componentId)
                onRemoved: entryKey => PersonalizationConfig.removeBarEntry(entryKey)
                onEnabledToggled: entryKey => PersonalizationConfig.toggleBarEntryEnabled(entryKey)
            }
        }
    }

    ConnectedRect {
        id: middleZoneRow

        Layout.fillWidth: true
        implicitHeight: Math.max(zoneMiddleLabel.implicitHeight, middleField.implicitHeight) + NexusStyle.padding.medium * 2

        RowLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            StyledText {
                id: zoneMiddleLabel

                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 10
                Layout.preferredWidth: 120
                text: I18n.tr("Center")
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
            }

            SortableMultiSelectField {
                id: middleField

                Layout.fillWidth: true
                values: PersonalizationConfig.barLayoutEntriesMiddle
                options: widgetCatalog.options()
                allowDuplicates: true
                zone: "middle"
                dragCoordinator: root.zoneCoordinator
                onToggled: componentId => PersonalizationConfig.addBarEntry(zone, componentId)
                onRemoved: entryKey => PersonalizationConfig.removeBarEntry(entryKey)
                onEnabledToggled: entryKey => PersonalizationConfig.toggleBarEntryEnabled(entryKey)
            }
        }
    }

    ConnectedRect {
        id: trailingZoneRow

        Layout.fillWidth: true
        last: true
        implicitHeight: Math.max(zoneTrailingLabel.implicitHeight, trailingField.implicitHeight) + NexusStyle.padding.medium * 2

        RowLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            StyledText {
                id: zoneTrailingLabel

                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 10
                Layout.preferredWidth: 120
                text: root.horizontalBar ? I18n.tr("Right") : I18n.tr("Bottom")
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
            }

            SortableMultiSelectField {
                id: trailingField

                Layout.fillWidth: true
                values: PersonalizationConfig.barLayoutEntriesRight
                options: widgetCatalog.options()
                allowDuplicates: true
                zone: "right"
                dragCoordinator: root.zoneCoordinator
                onToggled: componentId => PersonalizationConfig.addBarEntry(zone, componentId)
                onRemoved: entryKey => PersonalizationConfig.removeBarEntry(entryKey)
                onEnabledToggled: entryKey => PersonalizationConfig.toggleBarEntryEnabled(entryKey)
            }
        }
    }

    ConnectedRect {
        id: quickSettingsCard

        Layout.fillWidth: true
        Layout.topMargin: NexusStyle.padding.small
        first: true
        last: true
        implicitHeight: Math.max(quickSettingsLabel.implicitHeight, quickSettingsField.implicitHeight) + NexusStyle.padding.medium * 2

        RowLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            StyledText {
                id: quickSettingsLabel

                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 10
                Layout.preferredWidth: 120
                text: I18n.tr("Quick settings")
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
            }

            SortableMultiSelectField {
                id: quickSettingsField

                Layout.fillWidth: true
                values: PersonalizationConfig.quickSettingsComponents
                options: PersonalizationConfig.quickSettingsComponentOptions
                zone: "quickSettings"
                dragCoordinator: root.quickSettingsCoordinator
                onToggled: componentId => PersonalizationConfig.toggleQuickSettingsComponent(componentId)
                onRemoved: componentId => PersonalizationConfig.removeQuickSettingsComponent(componentId)
            }
        }
    }
}
