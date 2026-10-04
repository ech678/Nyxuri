import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

StyledFlickable {
    id: root

    readonly property bool horizontalBar: PersonalizationConfig.barPosition === "top"
                                          || PersonalizationConfig.barPosition === "bottom"

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingL

        SettingsSection {
            id: searchSection0
            Layout.fillWidth: true
            flat: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                target: searchSection0
                declaration:
                    '{"id":"general.bar.section.position","route":"general.bar","title":"Position","context":"GeneralBarPage","icon":"dock_to_bottom","aliases":[]}'
            }
            iconName: "dock_to_bottom"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Show bar")
                trailing: StyledSwitch {
                    checked: PersonalizationConfig.barEnabled
                    Accessible.name: I18n.tr("Show bar")
                    onToggled: PersonalizationConfig.setValue("barEnabled", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Floating")
                trailing: StyledSwitch {
                    checked: PersonalizationConfig.barOverlay
                    Accessible.name: I18n.tr("Floating")
                    onToggled: PersonalizationConfig.setValue("barOverlay", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Screen edge")

                trailing: EdgePositionSelector {
                    position: PersonalizationConfig.barPosition
                    onPositionSelected: position => {
                        return PersonalizationConfig.setBarPosition(position);
                    }
                }
            }
        }

        SettingsSection {
            id: searchSection1
            Layout.fillWidth: true
            flat: true
            title: searchAnchor1.title
            SettingsSearchAnchor {
                id: searchAnchor1
                target: searchSection1
                declaration:
                    '{"id":"general.bar.section.components","route":"general.bar","title":"Components","context":"GeneralBarPage","icon":"dock_to_bottom","aliases":[]}'
            }
            iconName: "view_agenda"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Show device names")
                trailing: StyledSwitch {
                    checked: PersonalizationConfig.barShowNames
                    Accessible.name: I18n.tr("Show device names")
                    onToggled: PersonalizationConfig.setBarShowNames(checked)
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Show numeric values")
                trailing: StyledSwitch {
                    checked: PersonalizationConfig.barShowValues
                    Accessible.name: I18n.tr("Show numeric values")
                    onToggled: PersonalizationConfig.setBarShowValues(checked)
                }
            }
            supportingText: I18n.tr("Drag components to reorder them or move them to the other side.")

            SettingsRow {
                id: leadingFieldRow
                Layout.fillWidth: true
                title: root.horizontalBar ? I18n.tr("Left") : I18n.tr("Top")

                trailing: SortableMultiSelectField {
                    id: leadingField

                    Layout.minimumWidth: 0
                    Layout.preferredWidth: Math.max(0, leadingFieldRow.width - 96 - 3 * Metrics.spacingS)
                    values: PersonalizationConfig.barLeadingComponents
                    options: PersonalizationConfig.barComponentOptions
                    zone: "leading"
                    dragCoordinator: dragCoordinator
                    onToggled: componentId => {
                        return PersonalizationConfig.toggleBarComponent(componentId, zone);
                    }
                    onRemoved: componentId => {
                        return PersonalizationConfig.removeBarComponent(componentId);
                    }
                }
            }

            SettingsRow {
                id: trailingFieldRow
                Layout.fillWidth: true
                title: root.horizontalBar ? I18n.tr("Right") : I18n.tr("Bottom")

                trailing: SortableMultiSelectField {
                    id: trailingField

                    Layout.minimumWidth: 0
                    Layout.preferredWidth: Math.max(0, trailingFieldRow.width - 96 - 3 * Metrics.spacingS)
                    values: PersonalizationConfig.barTrailingComponents
                    options: PersonalizationConfig.barComponentOptions
                    zone: "trailing"
                    dragCoordinator: dragCoordinator
                    onToggled: componentId => {
                        return PersonalizationConfig.toggleBarComponent(componentId, zone);
                    }
                    onRemoved: componentId => {
                        return PersonalizationConfig.removeBarComponent(componentId);
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Metrics.spacingS
                Layout.rightMargin: Metrics.spacingS
                spacing: Metrics.spacingS

                Text {
                    Layout.fillWidth: true
                    text: I18n.tr("Quick settings widgets")
                    color: Appearance.colors.colOnSurface
                    font.family: Fonts.ui
                    font.pixelSize: Typography.bodyLarge.pixelSize
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }

                SortableMultiSelectField {
                    id: quickSettingsField

                    Layout.fillWidth: true
                    values: PersonalizationConfig.quickSettingsComponents
                    options: PersonalizationConfig.quickSettingsComponentOptions
                    zone: "quickSettings"
                    dragCoordinator: quickSettingsDragCoordinator
                    onToggled: componentId => {
                        return PersonalizationConfig.toggleQuickSettingsComponent(componentId);
                    }
                    onRemoved: componentId => {
                        return PersonalizationConfig.removeQuickSettingsComponent(componentId);
                    }
                }
            }
        }
    }

    BarLayoutDragCoordinator {
        id: dragCoordinator

        anchors.fill: parent
        z: 1000
        fields: [leadingField, trailingField]
        onDropped: (componentId, targetZone, targetIndex) => {
            return PersonalizationConfig.moveBarComponent(componentId, targetZone, targetIndex);
        }
    }

    BarLayoutDragCoordinator {
        id: quickSettingsDragCoordinator

        anchors.fill: parent
        z: 1001
        fields: [quickSettingsField]
        onDropped: (componentId, targetZone, targetIndex) => {
            return PersonalizationConfig.moveQuickSettingsComponent(componentId, targetIndex);
        }
    }
}
