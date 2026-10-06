pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

// Segmented option tile. Ported from end4-pC's DashboardSelectCard.
DashboardCard {
    id: root

    property string controlKey: ""
    property string title: ""
    property string icon: "tune"
    property var tileShape: MaterialShapeCanvas.Shape.Pentagon
    property var override: null

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property var currentValue: root.control ? root.control.get() : null

    tint: Appearance.colors.colTertiaryContainer

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            MaterialShapeWrappedMaterialSymbol {
                wrappedShape: root.tileShape
                text: root.icon
                iconSize: 24
                fill: 1
                padding: 10
                color: Appearance.colors.colTertiary
                colSymbol: Appearance.colors.colOnTertiary
            }

            StyledText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Typography.titleLarge.pixelSize
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnTertiaryContainer
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
                model: root.control ? root.control.options : []

                delegate: RippleButton {
                    id: option

                    required property var modelData

                    readonly property bool selected: root.currentValue === option.modelData.value

                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    implicitHeight: 44
                    leftPadding: 16
                    rightPadding: 16
                    buttonRadius: 22
                    containerColor: option.selected ? Appearance.colors.colTertiary : Qt.rgba(1, 1, 1, 0.12)
                    rippleColor: Appearance.colors.colOnTertiary
                    stateLayerColor: Appearance.colors.colOnTertiary
                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                    downAction: () => {
                        const value = option.modelData.value;
                        Qt.callLater(() => root.control.set(value));
                    }

                    contentItem: Item {
                        implicitWidth: contentRow.implicitWidth
                        implicitHeight: contentRow.implicitHeight
                        clip: true

                        RowLayout {
                            id: contentRow

                            anchors.fill: parent
                            spacing: 6

                            MaterialSymbol {
                                visible: !!(option.modelData && option.modelData.icon)
                                text: option.modelData.icon ?? ""
                                iconSize: 18
                                fill: option.selected ? 1 : 0
                                color: option.selected ? Appearance.colors.colOnTertiary :
                                                         Appearance.colors.colOnTertiaryContainer
                            }

                            StyledText {
                                Layout.fillWidth: true
                                text: option.modelData.label ?? ""
                                font.weight: Font.Medium
                                color: option.selected ? Appearance.colors.colOnTertiary :
                                                         Appearance.colors.colOnTertiaryContainer
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
