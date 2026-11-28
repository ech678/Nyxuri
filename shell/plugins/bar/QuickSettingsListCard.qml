import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Independent list card for quickSettingsComponents (quickpanel popup items),
// preserved when BarComponentsCard chip fields retired in D4e e4.
ColumnLayout {
    id: root

    readonly property var activeIds: Array.isArray(PersonalizationConfig.quickSettingsComponents) ? PersonalizationConfig.quickSettingsComponents : []
    readonly property var allOptions: Array.isArray(PersonalizationConfig.quickSettingsComponentOptions) ? PersonalizationConfig.quickSettingsComponentOptions : []

    function optionFor(id) {
        for (let i = 0; i < root.allOptions.length; i += 1) {
            if (root.allOptions[i].value === id)
                return root.allOptions[i];
        }
        return {
            value: id,
            label: id,
            icon: "widgets"
        };
    }

    Layout.fillWidth: true
    spacing: NexusStyle.padding.extraSmall / 2

    PreferenceHeader {
        text: I18n.tr("Quick settings")
    }

    PreferenceGroup {
        Repeater {
            model: root.allOptions

            ConnectedRect {
                required property var modelData

                readonly property int activeIndex: root.activeIds.indexOf(modelData.value)
                readonly property bool isSelected: activeIndex !== -1

                Layout.fillWidth: true
                implicitHeight: itemRow.implicitHeight + NexusStyle.padding.medium * 2

                RowLayout {
                    id: itemRow

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: NexusStyle.padding.largeIncreased
                    anchors.rightMargin: NexusStyle.padding.largeIncreased
                    spacing: NexusStyle.padding.small

                    MaterialSymbol {
                        text: modelData.icon || "widgets"
                        iconSize: NexusStyle.icon.medium
                        fill: isSelected ? 1 : 0
                        color: isSelected ? Appearance.m3colors.m3primary : Appearance.m3colors.m3onSurfaceVariant
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: modelData.label
                        color: Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.bodyMedium
                        elide: Text.ElideRight
                    }

                    IconButton {
                        visible: isSelected && activeIndex > 0
                        Layout.alignment: Qt.AlignVCenter
                        width: NexusStyle.icon.small + NexusStyle.padding.small
                        height: NexusStyle.icon.small + NexusStyle.padding.small
                        controlSize: NexusStyle.icon.small + NexusStyle.padding.small
                        iconSize: NexusStyle.icon.small
                        iconName: "arrow_upward"
                        accessibleName: I18n.tr("Move up")
                        tooltipText: accessibleName
                        onClicked: PersonalizationConfig.moveQuickSettingsComponent(modelData.value, activeIndex - 1)
                    }

                    IconButton {
                        visible: isSelected && activeIndex < root.activeIds.length - 1
                        Layout.alignment: Qt.AlignVCenter
                        width: NexusStyle.icon.small + NexusStyle.padding.small
                        height: NexusStyle.icon.small + NexusStyle.padding.small
                        controlSize: NexusStyle.icon.small + NexusStyle.padding.small
                        iconSize: NexusStyle.icon.small
                        iconName: "arrow_downward"
                        accessibleName: I18n.tr("Move down")
                        tooltipText: accessibleName
                        onClicked: PersonalizationConfig.moveQuickSettingsComponent(modelData.value, activeIndex + 1)
                    }

                    StyledSwitch {
                        id: qsSwitch

                        checked: isSelected
                        onToggled: {
                            if (qsSwitch.checked)
                                PersonalizationConfig.toggleQuickSettingsComponent(modelData.value);
                            else
                                PersonalizationConfig.removeQuickSettingsComponent(modelData.value);
                        }
                    }
                }
            }
        }
    }
}
