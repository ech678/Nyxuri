pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

// Panelled three-way picker for the settings-panel style. Ported from end4-pC's
// DashboardStyleCard.
//
// Structural difference from upstream: upstream hardcodes its own option array
// ({value, name, detail, icon, shape}) next to a Config key, so the labels exist
// twice. Here the values and labels come from SettingsControlCatalog — the same
// object that already owns the getter/setter — and this card only supplies the
// decorative half keyed by value. The tile therefore cannot drift from the value
// the rest of the shell writes.
DashboardCard {
    id: root

    property string controlKey: "interface:Settings panel style"
    property var override: null

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property var currentValue: root.control ? root.control.get() : null

    // Decoration only: glyph, glyph shape, one-line explanation. A value the
    // catalog gains later still renders — it just falls back to a neutral
    // glyph and an empty detail line rather than disappearing from the picker.
    readonly property var decoration: ({
                                           "default": {
                                               "detail": qsTr("Full overlay panel"),
                                               "icon": "settings_panorama",
                                               "shape": MaterialShapeCanvas.Shape.Cookie9Sided
                                           },
                                           "minimal": {
                                               "detail": qsTr("Compact overlay panel"),
                                               "icon": "settings_heart",
                                               "shape": MaterialShapeCanvas.Shape.Clover4Leaf
                                           },
                                           "dashboard": {
                                               "detail": qsTr("Floating window with cards"),
                                               "icon": "dashboard",
                                               "shape": MaterialShapeCanvas.Shape.SoftBurst
                                           }
                                       })

    tint: Appearance.colors.colLayer1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

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
                spacing: 0

                StyledText {
                    text: qsTr("Settings panel")
                    font.pixelSize: Typography.titleLarge.pixelSize
                    font.weight: Font.DemiBold
                    color: Appearance.colors.colOnLayer1
                }

                StyledText {
                    text: qsTr("Choose how settings open")
                    font.pixelSize: Typography.bodyMedium.pixelSize
                    color: Appearance.colors.colSubtext
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Repeater {
                model: root.control ? root.control.options : []

                delegate: RippleButton {
                    id: option

                    required property var modelData

                    readonly property var decor: root.decoration[option.modelData.value] ?? ({})
                    readonly property bool selected: root.currentValue === option.modelData.value

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
                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                    // Deferred: writing the style mid-click rebuilds the whole
                    // settings host (the window swaps component), which would
                    // cancel the ripple before it is visible.
                    downAction: () => {
                        const value = option.modelData.value;
                        Qt.callLater(() => root.control.set(value));
                    }

                    contentItem: ColumnLayout {
                        spacing: 6

                        Item {
                            Layout.fillHeight: true
                        }

                        MaterialShapeWrappedMaterialSymbol {
                            Layout.alignment: Qt.AlignHCenter
                            wrappedShape: option.decor.shape ?? MaterialShapeCanvas.Shape.Pentagon
                            text: option.decor.icon ?? "tune"
                            iconSize: 32
                            fill: 1
                            padding: 15
                            color: option.selected ? Appearance.colors.colOnPrimary :
                                                     Appearance.colors.colPrimary
                            colSymbol: option.selected ? Appearance.colors.colPrimary :
                                                         Appearance.colors.colOnPrimary
                        }

                        StyledText {
                            Layout.alignment: Qt.AlignHCenter
                            text: option.modelData.label ?? ""
                            font.pixelSize: Typography.titleLarge.pixelSize
                            font.weight: Font.DemiBold
                            color: option.selected ? Appearance.colors.colOnPrimary :
                                                     Appearance.colors.colOnSecondaryContainer
                        }

                        StyledText {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            text: option.decor.detail ?? ""
                            font.pixelSize: Typography.bodyMedium.pixelSize
                            color: option.selected ? Appearance.colors.colOnPrimary :
                                                     Appearance.colors.colOnSecondaryContainer
                            opacity: 0.8
                        }

                        Item {
                            Layout.fillHeight: true
                        }

                        // Selection ring. Unselected draws the hollow outline so
                        // the row keeps a constant height and the glyphs do not
                        // shift when the selection moves.
                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.bottomMargin: 4
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
