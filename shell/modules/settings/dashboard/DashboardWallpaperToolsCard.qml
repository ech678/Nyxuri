pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

// Wallpaper quick actions. Ported from end4-pC's DashboardWallpaperToolsCard.
DashboardCard {
    id: root

    property string title: ""
    property string icon: "casino"
    property var tileShape: MaterialShapeCanvas.Shape.Sunny

    signal randomRequested
    signal foldersRequested

    tint: Appearance.colors.colPrimaryContainer

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            MaterialShapeWrappedMaterialSymbol {
                wrappedShape: root.tileShape
                text: root.icon
                iconSize: 24
                fill: 1
                padding: 10
                color: Appearance.colors.colPrimary
                colSymbol: Appearance.colors.colOnPrimary
            }

            StyledText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Typography.titleLarge.pixelSize
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnPrimaryContainer
                elide: Text.ElideRight
            }
        }

        Item {
            Layout.fillHeight: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: [
                    {
                        "icon": "shuffle",
                        "label": I18n.tr("Random"),
                        "primary": true
                    },
                    {
                        "icon": "folder_open",
                        "label": I18n.tr("More folders"),
                        "primary": false
                    }
                ]

                delegate: RippleButton {
                    id: tool

                    required property var modelData

                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    implicitHeight: 40
                    buttonRadius: 20
                    containerColor: tool.modelData.primary ? Appearance.colors.colPrimary : Qt.rgba(1, 1, 1,
                                                                                                    0.14)
                    rippleColor: Appearance.colors.colOnPrimary
                    stateLayerColor: tool.modelData.primary ? Appearance.colors.colOnPrimary :
                                                              Appearance.colors.colOnPrimaryContainer
                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                    downAction: () => {
                        const random = tool.modelData.primary;
                        Qt.callLater(() => {
                            if (random)
                                root.randomRequested();
                            else
                                root.foldersRequested();
                        });
                    }

                    contentItem: RowLayout {
                        spacing: 6

                        Item {
                            Layout.fillWidth: true
                        }

                        MaterialSymbol {
                            text: tool.modelData.icon
                            iconSize: 18
                            color: tool.modelData.primary ? Appearance.colors.colOnPrimary :
                                                            Appearance.colors.colOnPrimaryContainer
                        }

                        StyledText {
                            text: tool.modelData.label
                            font.weight: Font.Medium
                            color: tool.modelData.primary ? Appearance.colors.colOnPrimary :
                                                            Appearance.colors.colOnPrimaryContainer
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }
}
