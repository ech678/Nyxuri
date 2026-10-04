pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

// Palette-style picker: the nine-way "how are colours derived from the
// wallpaper" selector. Ported from end4-pC's DashboardPaletteCard.
//
// Same split as DashboardStyleCard: the catalog owns the values and labels
// (matugenScheme already has both, and the setter regenerates the theme), while
// this card only adds the glyph for each value. Upstream also gates this tile on
// "no named colour scheme is active" via `when: "material"`; nyxuri has no named
// schemes, so the gate has nothing to hang on and is left out.
DashboardCard {
    id: root

    property string controlKey: ""
    property string title: ""
    property string icon: "auto_awesome"
    property var tileShape: MaterialShapeCanvas.Shape.SoftBurst
    property var override: null

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property var currentValue: root.control ? root.control.get() : null

    readonly property var allOptions: root.control ? (root.control.options ?? []) : []
    // Split in half rather than a fixed 5/4: the split has to keep working if the
    // catalog gains or loses a scheme.
    readonly property var firstRow: root.allOptions.slice(0, Math.ceil(root.allOptions.length / 2))
    readonly property var secondRow: root.allOptions.slice(Math.ceil(root.allOptions.length / 2))

    // Glyphs are upstream's own (DashboardSettingsCatalog, "interface:Palette
    // type"), so the rows read the same. `scheme-vibrant` exists only in nyxuri.
    readonly property var glyphs: ({
                                       "auto": "auto_awesome",
                                       "scheme-content": "image",
                                       "scheme-expressive": "palette",
                                       "scheme-fidelity": "equal",
                                       "scheme-fruit-salad": "nutrition",
                                       "scheme-monochrome": "invert_colors",
                                       "scheme-neutral": "tonality",
                                       "scheme-rainbow": "gradient",
                                       "scheme-tonal-spot": "lens",
                                       "scheme-vibrant": "color_lens"
                                   })

    tint: Appearance.colors.colSecondaryContainer

    component Pill: RippleButton {
        id: pill

        property var card: null
        property var option: ({})

        readonly property bool selected: pill.card.currentValue === pill.option.value

        implicitHeight: 40
        leftPadding: 16
        rightPadding: 16
        buttonRadius: 14
        containerColor: pill.selected ? Appearance.colors.colSecondary : Qt.rgba(1, 1, 1, 0.12)
        rippleColor: Qt.rgba(1, 1, 1, 0.3)
        stateLayerColor: pill.selected ? Appearance.colors.colOnSecondary :
                                         Appearance.colors.colOnSecondaryContainer
        stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
        hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
        pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
        downAction: () => {
            const value = pill.option.value;
            const control = pill.card.control;
            Qt.callLater(() => control.set(value));
        }

        contentItem: Item {
            implicitWidth: contentRow.implicitWidth
            implicitHeight: contentRow.implicitHeight

            RowLayout {
                id: contentRow

                anchors.centerIn: parent
                spacing: 6

                MaterialSymbol {
                    text: pill.card.glyphs[pill.option.value] ?? "palette"
                    iconSize: 18
                    fill: pill.selected ? 1 : 0
                    color: pill.selected ? Appearance.colors.colOnSecondary :
                                           Appearance.colors.colOnSecondaryContainer
                }

                StyledText {
                    text: pill.option.label ?? ""
                    font.pixelSize: Typography.bodyMedium.pixelSize
                    font.weight: Font.Medium
                    color: pill.selected ? Appearance.colors.colOnSecondary :
                                           Appearance.colors.colOnSecondaryContainer
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // Fixed-width heading column so the option rows always start at the same
        // x, regardless of how long the title is.
        Item {
            Layout.fillHeight: true
            Layout.preferredWidth: 300
            Layout.maximumWidth: 300

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                MaterialShapeWrappedMaterialSymbol {
                    Layout.alignment: Qt.AlignVCenter
                    wrappedShape: root.tileShape
                    text: root.icon
                    iconSize: 26
                    fill: 1
                    padding: 11
                    color: Appearance.colors.colSecondary
                    colSymbol: Appearance.colors.colOnSecondary
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 0

                    StyledText {
                        Layout.fillWidth: true
                        text: root.title
                        font.pixelSize: Typography.titleLarge.pixelSize
                        font.weight: Font.DemiBold
                        color: Appearance.colors.colOnSecondaryContainer
                        elide: Text.ElideRight
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: I18n.tr("How colors are made from your wallpaper")
                        font.pixelSize: Typography.bodyMedium.pixelSize
                        color: Appearance.colors.colOnSecondaryContainer
                        opacity: 0.75
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                Item {
                    Layout.fillHeight: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: root.firstRow

                        delegate: Pill {
                            required property var modelData

                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            card: root
                            option: modelData
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: root.secondRow

                        delegate: Pill {
                            required property var modelData

                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            card: root
                            option: modelData
                        }
                    }
                }

                Item {
                    Layout.fillHeight: true
                }
            }
        }
    }
}
