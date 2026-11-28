import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Widget picker dialog for BarLaneSection's "Add widget" button. Lists the
// shared BarWidgetCatalog entries, enforces the cross-bar island singleton
// rule, and emits widgetSelected(widgetId, targetZone).
MaterialDialog {
    id: root

    property string targetZone: "left"
    readonly property bool islandTaken: PersonalizationConfig.anyBarUsesWidget("island")

    signal widgetSelected(string widgetId, string targetZone)

    BarWidgetCatalog {
        id: widgetCatalog
    }

    dialogTitle: I18n.tr("Add widget")
    implicitWidth: 420

    contentComponent: Item {
        implicitWidth: 360
        implicitHeight: Math.min(420, flick.contentHeight)

        Flickable {
            id: flick

            anchors.fill: parent
            contentWidth: width
            contentHeight: listCol.implicitHeight
            clip: true

            ColumnLayout {
                id: listCol

                width: flick.width
                spacing: NexusStyle.padding.extraSmall / 2

                PreferenceGroup {
                    Repeater {
                        model: widgetCatalog.options()

                        PreferenceAction {
                            required property var modelData

                            readonly property bool blockedSingleton: modelData.value === "island" && root.islandTaken

                            icon: modelData.icon || "widgets"
                            text: modelData.label
                            subtext: blockedSingleton ? I18n.tr("Already placed on a bar") : ""
                            trailingIcon: blockedSingleton ? "block" : "add"
                            enabled: !blockedSingleton
                            onClicked: {
                                root.widgetSelected(modelData.value, root.targetZone);
                                root.close();
                            }
                        }
                    }
                }
            }
        }
    }

    actionsComponent: RowLayout {
        Layout.fillWidth: true

        Item {
            Layout.fillWidth: true
        }

        RippleButton {
            buttonText: I18n.tr("Close")
            buttonRadius: NexusStyle.rounding.full
            horizontalPadding: NexusStyle.padding.large
            verticalPadding: NexusStyle.padding.small
            colBackground: Appearance.m3colors.m3secondaryContainer
            colBackgroundHover: Appearance.m3colors.m3secondaryContainer
            onClicked: root.close()

            contentItem: StyledText {
                text: I18n.tr("Close")
                color: Appearance.m3colors.m3onSecondaryContainer
                font.pixelSize: NexusStyle.font.labelLarge
                font.weight: NexusStyle.font.labelLargeWeight
            }
        }
    }
}
