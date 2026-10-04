import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services

// Three-way switch for how the settings panel presents itself. Ported 1:1 from
// end4-pC's DashboardStyleCard: same option grid, same selected badge, same
// shape-wrapped icon treatment — now backed by the real Material 3 shape
// library, so Clover4Leaf renders instead of the M3Shapes fallback's rounded
// rectangle.
//
// The value lives in PersonalizationConfig rather than a JsonAdapter, so writes
// go through setSettingsPanelStyle() and survive a config reload.
Rectangle {
    id: root

    readonly property var styleOptions: [
        {
            "value": "default",
            "name": qsTr("Default"),
            "detail": qsTr("Full rail and page layout"),
            "icon": "settings_panorama",
            "shape": MaterialShapeCanvas.Shape.Cookie9Sided
        },
        {
            "value": "minimal",
            "name": qsTr("Minimal"),
            "detail": qsTr("Compact rail, tighter padding"),
            "icon": "settings_heart",
            "shape": MaterialShapeCanvas.Shape.Clover4Leaf
        },
        {
            "value": "dashboard",
            "name": qsTr("Dashboard"),
            "detail": qsTr("Floating card grid"),
            "icon": "dashboard",
            "shape": MaterialShapeCanvas.Shape.SoftBurst
        }
    ]

    implicitHeight: cardColumn.implicitHeight + Appearance.spacing.medium * 2
    radius: Appearance.rounding.large
    color: Appearance.colors.colLayer1

    ColumnLayout {
        id: cardColumn

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Appearance.spacing.medium
        spacing: Appearance.spacing.medium

        RowLayout {
            Layout.fillWidth: true
            spacing: Appearance.spacing.small

            MaterialShapeWrappedMaterialSymbol {
                wrappedShape: MaterialShapeCanvas.Shape.Gem
                text: "settings"
                iconSize: 26
                fill: 1
                padding: 11
                color: Appearance.colors.colPrimary
                colSymbol: Appearance.colors.colOnPrimary
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                Text {
                    text: qsTr("Settings panel")
                    color: Appearance.colors.colOnLayer1
                    font.family: Fonts.ui
                    font.pixelSize: Typography.titleMedium.pixelSize
                    font.weight: Font.DemiBold
                }

                Text {
                    text: qsTr("Choose how settings open")
                    color: Appearance.colors.colSubtext
                    font.family: Fonts.ui
                    font.pixelSize: Typography.bodySmall.pixelSize
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 168
            spacing: Appearance.spacing.small

            Repeater {
                model: root.styleOptions

                delegate: RippleButton {
                    id: option

                    required property var modelData

                    readonly property bool selected: PersonalizationConfig.settingsPanelStyle
                                                     === option.modelData.value

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1
                    buttonRadius: Appearance.rounding.large
                    containerColor: option.selected ? Appearance.colors.colPrimary :
                                                      Appearance.colors.colSecondaryContainer
                    rippleColor: option.selected ? Appearance.colors.colOnPrimary :
                                                   Appearance.colors.colOnSecondaryContainer
                    stateLayerColor: option.selected ? Appearance.colors.colOnPrimary :
                                                       Appearance.colors.colOnSecondaryContainer
                    // RippleButton defaults its state layer to full opacity, which
                    // over a filled container floods the card. Use the M3 values.
                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    focusStateLayerOpacity: Appearance.interaction.focusStateLayerOpacity
                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                    downAction: () => {
                        const value = option.modelData.value;
                        Qt.callLater(() => {
                            PersonalizationConfig.setSettingsPanelStyle(value);
                        });
                    }

                    contentItem: ColumnLayout {
                        spacing: Appearance.spacing.small

                        Item {
                            Layout.fillHeight: true
                        }

                        MaterialShapeWrappedMaterialSymbol {
                            Layout.alignment: Qt.AlignHCenter
                            wrappedShape: option.modelData.shape
                            text: option.modelData.icon
                            iconSize: 34
                            fill: 1
                            padding: 16
                            color: option.selected ? Appearance.colors.colOnPrimary :
                                                     Appearance.colors.colPrimary
                            colSymbol: option.selected ? Appearance.colors.colPrimary :
                                                         Appearance.colors.colOnPrimary
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: option.modelData.name
                            color: option.selected ? Appearance.colors.colOnPrimary :
                                                     Appearance.colors.colOnSecondaryContainer
                            font.family: Fonts.ui
                            font.pixelSize: Typography.titleMedium.pixelSize
                            font.weight: Font.DemiBold
                        }

                        Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            text: option.modelData.detail
                            color: option.selected ? Appearance.colors.colOnPrimary :
                                                     Appearance.colors.colOnSecondaryContainer
                            opacity: 0.8
                            font.family: Fonts.ui
                            font.pixelSize: Typography.bodySmall.pixelSize
                        }

                        Item {
                            Layout.fillHeight: true
                        }

                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.bottomMargin: Appearance.spacing.small
                            implicitWidth: 26
                            implicitHeight: 26
                            radius: 13
                            color: option.selected ? Appearance.colors.colOnPrimary : "transparent"
                            border.width: option.selected ? 0 : 2
                            border.color: Appearance.colors.colOnSecondaryContainer

                            MaterialSymbol {
                                anchors.centerIn: parent
                                visible: option.selected
                                text: "check"
                                iconSize: 18
                                color: Appearance.colors.colPrimary
                            }
                        }
                    }
                }
            }
        }
    }
}
