import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Bar page (T3 M4): NexusPageBase scaffold + M1 atom rows. The drag-to-reorder
// component fields stay the sanctioned custom shape (SortableMultiSelectField
// + BarLayoutDragCoordinator overlay); the drag overlay must not be a root
// child — NexusPageBase takes a single content child, so it rides inside it.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("bar")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    readonly property bool horizontalBar: PersonalizationConfig.barPosition === "top"
                                          || PersonalizationConfig.barPosition === "bottom"

    Item {
        id: content

        width: parent.width
        implicitHeight: contentColumn.implicitHeight

        ColumnLayout {
            id: contentColumn

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            width: root.cappedWidth
            spacing: NexusStyle.padding.extraSmall / 2

            // Position
            PreferenceHeader {
                first: true
                text: I18n.tr("Position")
            }

            PreferenceToggle {
                id: floatingToggle

                first: true
                text: I18n.tr("Floating")
                checked: PersonalizationConfig.barOverlay
                onToggled: PersonalizationConfig.setValue("barOverlay", checked)

                SettingsSearchAnchor {
                    id: searchAnchor0
                    target: floatingToggle
                    declaration:
                        '{"id":"bar.section.position","route":"bar","title":"Position","context":"GeneralBarPage","icon":"dock_to_bottom","aliases":["general.bar.section.position"]}'
                }
            }

            PreferenceSelect {
                last: true
                label: I18n.tr("Screen edge")
                model: PersonalizationConfig.edgePositions
                currentValue: PersonalizationConfig.barPosition
                inputRegionService: PopupInputRegionService
                onSelected: value => PersonalizationConfig.setBarPosition(String(value))
            }

            // Components
            PreferenceHeader {
                text: I18n.tr("Components")
            }

            StyledText {
                Layout.fillWidth: true
                Layout.leftMargin: NexusStyle.padding.extraSmall
                Layout.rightMargin: NexusStyle.padding.extraSmall
                Layout.bottomMargin: NexusStyle.padding.extraSmall
                text: I18n.tr("Drag components to reorder them or move them to the other side.")
                color: Appearance.m3colors.m3onSurfaceVariant
                font.pixelSize: NexusStyle.font.bodySmall
                wrapMode: Text.Wrap
            }

            PreferenceToggle {
                id: namesToggle

                first: true
                text: I18n.tr("Show device names")
                checked: PersonalizationConfig.barShowNames
                onToggled: PersonalizationConfig.setBarShowNames(checked)

                SettingsSearchAnchor {
                    id: searchAnchor1
                    target: namesToggle
                    declaration:
                        '{"id":"bar.section.components","route":"bar","title":"Components","context":"GeneralBarPage","icon":"view_agenda","aliases":["general.bar.section.components"]}'
                }
            }

            PreferenceToggle {
                text: I18n.tr("Show numeric values")
                checked: PersonalizationConfig.barShowValues
                onToggled: PersonalizationConfig.setBarShowValues(checked)
            }

            ConnectedRect {
                id: leadingZoneRow

                Layout.fillWidth: true
                implicitHeight: Math.max(zoneLeadingLabel.implicitHeight, leadingField.implicitHeight)
                                + NexusStyle.padding.medium * 2

                RowLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: NexusStyle.padding.largeIncreased
                    anchors.rightMargin: NexusStyle.padding.largeIncreased
                    spacing: NexusStyle.padding.small

                    StyledText {
                        id: zoneLeadingLabel

                        text: root.horizontalBar ? I18n.tr("Left") : I18n.tr("Top")
                        color: Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.bodyMedium
                    }

                    SortableMultiSelectField {
                        id: leadingField

                        Layout.fillWidth: true
                        values: PersonalizationConfig.barLeadingComponents
                        options: PersonalizationConfig.barComponentOptions
                        zone: "leading"
                        dragCoordinator: dragCoordinator
                        onToggled: componentId => PersonalizationConfig.toggleBarComponent(componentId, zone)
                        onRemoved: componentId => PersonalizationConfig.removeBarComponent(componentId)
                    }
                }
            }

            ConnectedRect {
                id: trailingZoneRow

                Layout.fillWidth: true
                implicitHeight: Math.max(zoneTrailingLabel.implicitHeight, trailingField.implicitHeight)
                                + NexusStyle.padding.medium * 2

                RowLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: NexusStyle.padding.largeIncreased
                    anchors.rightMargin: NexusStyle.padding.largeIncreased
                    spacing: NexusStyle.padding.small

                    StyledText {
                        id: zoneTrailingLabel

                        text: root.horizontalBar ? I18n.tr("Right") : I18n.tr("Bottom")
                        color: Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.bodyMedium
                    }

                    SortableMultiSelectField {
                        id: trailingField

                        Layout.fillWidth: true
                        values: PersonalizationConfig.barTrailingComponents
                        options: PersonalizationConfig.barComponentOptions
                        zone: "trailing"
                        dragCoordinator: dragCoordinator
                        onToggled: componentId => PersonalizationConfig.toggleBarComponent(componentId, zone)
                        onRemoved: componentId => PersonalizationConfig.removeBarComponent(componentId)
                    }
                }
            }

            ConnectedRect {
                id: quickSettingsCard

                last: true
                Layout.fillWidth: true
                implicitHeight: quickSettingsColumn.implicitHeight + NexusStyle.padding.medium * 2

                ColumnLayout {
                    id: quickSettingsColumn

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: NexusStyle.padding.largeIncreased
                    anchors.rightMargin: NexusStyle.padding.largeIncreased
                    spacing: NexusStyle.padding.small

                    StyledText {
                        Layout.fillWidth: true
                        text: I18n.tr("Quick settings widgets")
                        color: Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.bodyMedium
                        elide: Text.ElideRight
                    }

                    SortableMultiSelectField {
                        id: quickSettingsField

                        Layout.fillWidth: true
                        values: PersonalizationConfig.quickSettingsComponents
                        options: PersonalizationConfig.quickSettingsComponentOptions
                        zone: "quickSettings"
                        dragCoordinator: quickSettingsDragCoordinator
                        onToggled: componentId => PersonalizationConfig.toggleQuickSettingsComponent(
                                                      componentId)
                        onRemoved: componentId => PersonalizationConfig.removeQuickSettingsComponent(
                                                      componentId)
                    }
                }
            }
        }

        BarLayoutDragCoordinator {
            id: dragCoordinator

            anchors.fill: parent
            z: 1000
            fields: [leadingField, trailingField]
            onDropped: (componentId, targetZone, targetIndex) => PersonalizationConfig.moveBarComponent(
                                                                     componentId, targetZone, targetIndex)
        }

        BarLayoutDragCoordinator {
            id: quickSettingsDragCoordinator

            anchors.fill: parent
            z: 1001
            fields: [quickSettingsField]
            onDropped: (componentId, targetZone, targetIndex)
                       => PersonalizationConfig.moveQuickSettingsComponent(componentId, targetIndex)
        }
    }
}
