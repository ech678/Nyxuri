pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

// Dashboard "Themes" page — replaces end4-pC's Presets tab.
//
// Why this instead of Presets: end4-pC's Presets tab is a browseable gallery of
// whole-theme snapshots (colour scheme + bar layout + clock + dock + blur, saved
// as JSON, plus online/imported sources). nyxuri has no preset system at all, so
// that page has nothing to render. What nyxuri *does* have is matugen: a set of
// colour schemes plus per-application templates, which is the only real
// "change the whole look" mechanism in this tree. So the tab keeps end4-pC's
// visual role — a gallery you click to restyle the shell — and fills it with the
// mechanism that actually exists here. Nothing is faked: every card applies a
// real setting, and the palette strip shows the live result.
Item {
    id: root

    required property Item pager
    property int staggerMs: 45

    readonly property var schemes: PersonalizationConfig.matugenSchemes
    readonly property string activeScheme: PersonalizationConfig.matugenScheme
    readonly property int schemeColumns: Math.max(2, Math.round(width / 240))

    // The template ids nyxuri ships matugen templates for. MatugenTemplateService
    // resolves each one and refuses ids it does not know, so a wrong id here
    // simply does not render a working toggle.
    readonly property var templates: [
        {
            "id": "kitty",
            "label": I18n.tr("Kitty"),
            "icon": "terminal"
        },
        {
            "id": "btop",
            "label": I18n.tr("btop"),
            "icon": "monitoring"
        },
        {
            "id": "cava",
            "label": I18n.tr("Cava"),
            "icon": "graphic_eq"
        },
        {
            "id": "yazi",
            "label": I18n.tr("Yazi"),
            "icon": "folder"
        }
    ]

    // Role swatches for the live preview. Kept in one place so the strip and any
    // future page share the same reading of the palette.
    readonly property var paletteRoles: [
        {
            "name": I18n.tr("Primary"),
            "color": Appearance.m3colors.m3primary
        },
        {
            "name": I18n.tr("Primary container"),
            "color": Appearance.m3colors.m3primaryContainer
        },
        {
            "name": I18n.tr("Secondary"),
            "color": Appearance.m3colors.m3secondary
        },
        {
            "name": I18n.tr("Secondary container"),
            "color": Appearance.m3colors.m3secondaryContainer
        },
        {
            "name": I18n.tr("Tertiary"),
            "color": Appearance.m3colors.m3tertiary
        },
        {
            "name": I18n.tr("Tertiary container"),
            "color": Appearance.m3colors.m3tertiaryContainer
        },
        {
            "name": I18n.tr("Surface"),
            "color": Appearance.m3colors.m3surface
        },
        {
            "name": I18n.tr("Outline"),
            "color": Appearance.m3colors.m3outline
        }
    ]

    function schemeLabel(value) {
        const entry = root.schemes.find(scheme => scheme.value === value);
        return entry ? entry.label : value;
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 200
            Layout.minimumHeight: 200
            Layout.maximumHeight: 200
            spacing: 12

            DashboardCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 22
                Layout.fillHeight: true
                tint: Appearance.colors.colPrimaryContainer
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 0
                travelX: -200
                travelY: 0

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        MaterialShapeWrappedMaterialSymbol {
                            wrappedShape: MaterialShapeCanvas.Shape.Flower
                            text: "palette"
                            iconSize: 24
                            fill: 1
                            padding: 10
                            color: Appearance.colors.colPrimary
                            colSymbol: Appearance.colors.colOnPrimary
                        }

                        ColumnLayout {
                            spacing: 0

                            StyledText {
                                text: I18n.tr("Current palette")
                                font.pixelSize: Typography.titleLarge.pixelSize
                                font.weight: Font.DemiBold
                                color: Appearance.colors.colOnPrimaryContainer
                            }

                            StyledText {
                                text: root.schemeLabel(root.activeScheme)
                                font.pixelSize: Typography.bodySmall.pixelSize
                                color: Appearance.colors.colOnPrimaryContainer
                                opacity: 0.75
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: root.paletteRoles

                            delegate: ColumnLayout {
                                id: swatch

                                required property var modelData

                                Layout.fillWidth: true
                                Layout.preferredWidth: 1
                                spacing: 4

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 26
                                    radius: Appearance.rounding.small
                                    color: swatch.modelData.color
                                    border.width: 1
                                    border.color: Appearance.colors.colOutlineVariant
                                }

                                StyledText {
                                    Layout.fillWidth: true
                                    text: swatch.modelData.name
                                    font.pixelSize: 10
                                    color: Appearance.colors.colOnPrimaryContainer
                                    opacity: 0.7
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }

            DashboardCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 10
                Layout.fillHeight: true
                tint: Appearance.colors.colSecondaryContainer
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 1
                travelX: 200
                travelY: 0

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        MaterialShapeWrappedMaterialSymbol {
                            wrappedShape: MaterialShapeCanvas.Shape.Gem
                            text: "widgets"
                            iconSize: 22
                            fill: 1
                            padding: 9
                            color: Appearance.colors.colSecondary
                            colSymbol: Appearance.colors.colOnSecondary
                        }

                        StyledText {
                            Layout.fillWidth: true
                            text: I18n.tr("Matugen templates")
                            font.pixelSize: Typography.bodyLarge.pixelSize
                            font.weight: Font.DemiBold
                            color: Appearance.colors.colOnSecondaryContainer
                            elide: Text.ElideRight
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Repeater {
                            model: root.templates

                            delegate: RippleButton {
                                id: templateToggle

                                required property var modelData

                                Layout.fillWidth: true
                                // Qt Quick Layouts default Layout.minimumWidth to the
                                // item's implicitWidth, so a button whose content is
                                // wider than the card refuses to shrink and spills out.
                                // Zero it and let the label elide instead.
                                Layout.minimumWidth: 0
                                implicitHeight: 26
                                leftPadding: 8
                                rightPadding: 8
                                buttonRadius: 13
                                containerColor: PersonalizationConfig.isMatugenTemplateEnabled(
                                                    templateToggle.modelData.id)
                                                ? Appearance.colors.colSecondary : Qt.rgba(1, 1, 1, 0.12)
                                rippleColor: Appearance.colors.colOnSecondary
                                stateLayerColor: Appearance.colors.colOnSecondary
                                stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                                downAction: () => {
                                    const id = templateToggle.modelData.id;
                                    const next = !PersonalizationConfig.isMatugenTemplateEnabled(id);
                                    Qt.callLater(() => PersonalizationConfig.setMatugenTemplateEnabled(id,
                                                                                                       next));
                                }

                                contentItem: Item {
                                    implicitWidth: templateRow.implicitWidth
                                    implicitHeight: templateRow.implicitHeight

                                    RowLayout {
                                        id: templateRow

                                        anchors.centerIn: parent
                                        spacing: 6

                                        MaterialSymbol {
                                            text: templateToggle.modelData.icon
                                            iconSize: 16
                                            fill: PersonalizationConfig.isMatugenTemplateEnabled(
                                                      templateToggle.modelData.id) ? 1 : 0
                                            color: Appearance.colors.colOnSecondaryContainer
                                        }

                                        StyledText {
                                            Layout.fillWidth: true
                                            text: templateToggle.modelData.label
                                            color: Appearance.colors.colOnSecondaryContainer
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        GridView {
            id: schemeGrid

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            cellWidth: Math.floor(width / root.schemeColumns)
            cellHeight: Math.round(cellWidth * 0.62)
            model: root.schemes
            cacheBuffer: 0
            ScrollBar.vertical: StyledScrollBar {}

            WheelScrollController {
                flickable: schemeGrid
            }

            delegate: Item {
                id: schemeCell

                required property int index
                required property var modelData

                readonly property bool selected: root.activeScheme === schemeCell.modelData.value

                width: schemeGrid.cellWidth
                height: schemeGrid.cellHeight

                DashboardCard {
                    id: schemeCard

                    anchors.fill: parent
                    anchors.margins: 6
                    tint: schemeCell.selected ? Appearance.colors.colPrimaryContainer :
                                                Appearance.colors.colLayer1
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: schemeCell.index % 8
                    travelX: 0
                    travelY: 80

                    Behavior on tint {
                        ColorAnimation {
                            duration: 200
                        }
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            MaterialShapeWrappedMaterialSymbol {
                                wrappedShape: MaterialShapeCanvas.Shape.Cookie6Sided
                                text: "palette"
                                iconSize: 20
                                fill: schemeCell.selected ? 1 : 0
                                padding: 8
                                color: schemeCell.selected ? Appearance.colors.colPrimary :
                                                             Appearance.colors.colSecondaryContainer
                                colSymbol: schemeCell.selected ? Appearance.colors.colOnPrimary :
                                                                 Appearance.colors.colOnSecondaryContainer
                            }

                            StyledText {
                                Layout.fillWidth: true
                                text: schemeCell.modelData.label
                                font.pixelSize: Typography.bodyLarge.pixelSize
                                font.weight: Font.DemiBold
                                color: schemeCell.selected ? Appearance.colors.colOnPrimaryContainer :
                                                             Appearance.colors.colOnLayer1
                                elide: Text.ElideRight
                            }

                            MaterialSymbol {
                                visible: schemeCell.selected
                                text: "check_circle"
                                iconSize: 20
                                fill: 1
                                color: Appearance.colors.colPrimary
                            }
                        }

                        Item {
                            Layout.fillHeight: true
                        }

                        StyledText {
                            Layout.fillWidth: true
                            text: schemeCell.modelData.value
                            font.pixelSize: Typography.bodySmall.pixelSize
                            color: schemeCell.selected ? Appearance.colors.colOnPrimaryContainer :
                                                         Appearance.colors.colSubtext
                            opacity: 0.75
                            elide: Text.ElideRight
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            const value = schemeCell.modelData.value;
                            Qt.callLater(() => PersonalizationConfig.setMatugenScheme(value));
                        }
                    }
                }
            }
        }
    }
}
