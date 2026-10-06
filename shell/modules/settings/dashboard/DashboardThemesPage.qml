pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
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

    // The template ids in the builtin registry. TemplateService resolves each
    // one and refuses ids it does not know, so a wrong id here simply does not
    // render a working toggle.
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
            "id": "starship",
            "label": I18n.tr("Starship"),
            "icon": "terminal"
        },
        {
            "id": "gtk3",
            "label": I18n.tr("GTK 3"),
            "icon": "palette"
        },
        {
            "id": "gtk4",
            "label": I18n.tr("GTK 4"),
            "icon": "palette"
        },
        {
            "id": "niri_glow",
            "label": I18n.tr("Niri glow"),
            "icon": "palette"
        },
        {
            "id": "palette_toml",
            "label": I18n.tr("Shared palette"),
            "icon": "palette"
        }
    ]

    // Role swatches for the live preview. Kept in one place so the strip and any
    // future page share the same reading of the palette.
    // True per-scheme preview palettes, owned by TemplateService (keyed
    // by scheme value, snake_case colors.json shape). Falls back to the live
    // palette for any scheme missing from the cache.
    readonly property var schemePreviews: TemplateService.schemePreviews

    function previewStrip(schemeValue) {
        const preview = root.schemePreviews[schemeValue];
        if (preview && preview.primary && preview.secondary && preview.tertiary)
            return [preview.primary, preview.secondary, preview.tertiary];
        return [Appearance.colors.colPrimary, Appearance.colors.colSecondary, Appearance.colors.colTertiary];
    }

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
                                    // ThemeService, not PersonalizationConfig: writing the
                                    // value alone leaves the generated palette on the
                                    // previous scheme, so the gallery selection moves
                                    // but nothing on screen changes.
                                    Qt.callLater(() => ThemeService.setMatugenTemplateEnabled(id, next));
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

        // Scheme gallery, replaced from a colour-grid with a horizontal tile row.
        // Nyxuri can't preview a scheme's colours from its name alone: matugen
        // derives the palette from the wallpaper source, so the same scheme name
        // yields different colours per wallpaper. The strips therefore show the
        // live palette's three brand hues (primary/secondary/tertiary), not a
        // per-scheme guess — honest, if less individually distinctive.
        // Card wrapper gives the tile strip the same enter/exit choreography as
        // every other card; without it the strip popped in and out instantly and
        // the page switch read as a hitch.
        DashboardCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            tint: Appearance.colors.colLayer1
            pager: root.pager
            staggerMs: root.staggerMs
            animIndex: 2
            travelX: 0
            travelY: 90

            Item {
                id: schemeArea

                anchors.fill: parent
                anchors.margins: 12

                function scrollBy(delta) {
                    const max = Math.max(0, schemeScroller.contentWidth - schemeScroller.width);
                    schemeScroller.contentX = Math.max(0, Math.min(max, schemeScroller.contentX + delta));
                }

                Flickable {
                    id: schemeScroller

                    anchors.fill: parent
                    contentWidth: schemeRow.implicitWidth
                    contentHeight: height
                    interactive: false
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    Behavior on contentX {
                        NumberAnimation {
                            duration: 300
                            easing.type: Easing.OutCubic
                        }
                    }

                    WheelHandler {
                        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                        onWheel: event => {
                            const step = event.angleDelta.y !== 0 ? event.angleDelta.y : event.pixelDelta.y;
                            const max = Math.max(0, schemeScroller.contentWidth - schemeScroller.width);
                            const desired = schemeScroller.contentX - step;
                            if (desired >= 0 && desired <= max) {
                                schemeScroller.contentX = desired;
                                return;
                            }
                            // Reached a horizontal edge: hand the gesture to the page
                            // scroller when it exposes one.
                            const p = root.pager;
                            if (p && typeof p.scrollSettingsBy === "function")
                                p.scrollSettingsBy(-step);
                        }
                    }

                    Row {
                        id: schemeRow

                        spacing: 10
                        height: schemeScroller.height

                        Repeater {
                            model: root.schemes

                            delegate: Item {
                                id: tileRoot

                                required property var modelData

                                readonly property bool selected: root.activeScheme
                                                                 === tileRoot.modelData.value

                                width: 118
                                height: schemeScroller.height

                                RippleButton {
                                    id: tile

                                    anchors.fill: parent
                                    buttonRadius: 18
                                    // Primary wash stands in for the scheme's main colour:
                                    // the only honest single hue we have is the live one.
                                    containerColor: Appearance.applyAlpha(Appearance.colors.colPrimary, 0.16)
                                    stateLayerColor: Appearance.colors.colOnLayer1
                                    hoverStateLayerColor: Qt.lighter(Appearance.applyAlpha(
                                                                         Appearance.colors.colPrimary, 0.16),
                                                                     1.1)
                                    hoverStateLayerOpacity: 0.5
                                    rippleColor: Appearance.colors.colOnLayer1
                                    toggled: tileRoot.selected
                                    selectedStateLayerEnabled: true
                                    selectedStateLayerColor: Appearance.colors.colPrimary
                                    selectedStateLayerOpacity: 0.22
                                    downAction: () => {
                                        const value = tileRoot.modelData.value;
                                        // Orchestrated setter re-derives the palette;
                                        // writing PersonalizationConfig alone leaves the
                                        // screen on the previous scheme.
                                        Qt.callLater(() => ThemeService.setMatugenScheme(value));
                                    }

                                    contentItem: Item {
                                        anchors.fill: parent

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 6

                                            RowLayout {
                                                id: strip

                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 28
                                                spacing: 5

                                                Repeater {
                                                    model: root.previewStrip(tileRoot.modelData.value)

                                                    delegate: Rectangle {
                                                        required property var modelData

                                                        Layout.fillWidth: true
                                                        Layout.fillHeight: true
                                                        Layout.preferredWidth: 1
                                                        radius: 11
                                                        color: modelData
                                                    }
                                                }
                                            }

                                            Item {
                                                Layout.fillHeight: true
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 4

                                                StyledText {
                                                    Layout.fillWidth: true
                                                    text: tileRoot.modelData.label
                                                    font.pixelSize: Appearance.font.pixelSize.small
                                                    font.weight: tileRoot.selected ? Font.DemiBold :
                                                                                     Font.Normal
                                                    color: Appearance.colors.colOnLayer1
                                                    elide: Text.ElideRight
                                                }

                                                MaterialSymbol {
                                                    visible: tileRoot.selected
                                                    text: "check_circle"
                                                    iconSize: 18
                                                    fill: 1
                                                    color: Appearance.colors.colPrimary
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 18
                                    color: "transparent"
                                    border.width: 2
                                    border.color: tileRoot.selected ? Appearance.colors.colPrimary :
                                                                      "transparent"
                                    Behavior on border.color {
                                        ColorAnimation {
                                            duration: 200
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    id: leftArrow

                    width: 38
                    height: 38
                    radius: 19
                    x: 6
                    z: 2
                    anchors.verticalCenter: parent.verticalCenter
                    color: Appearance.colors.colSecondaryContainer
                    opacity: schemeScroller.contentX > 1 ? (leftHover.containsMouse ? 1 : 0.85) : 0
                    visible: opacity > 0.01
                    Behavior on opacity {
                        NumberAnimation {
                            duration: 150
                        }
                    }

                    MaterialSymbol {
                        anchors.centerIn: parent
                        text: "chevron_left"
                        iconSize: 24
                        color: Appearance.colors.colOnSecondaryContainer
                    }

                    MouseArea {
                        id: leftHover

                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: {
                            hoverTimer.direction = -1;
                            hoverTimer.restart();
                        }
                        onExited: hoverTimer.stop()
                    }
                }

                Rectangle {
                    id: rightArrow

                    width: 38
                    height: 38
                    radius: 19
                    x: parent.width - width - 6
                    z: 2
                    anchors.verticalCenter: parent.verticalCenter
                    color: Appearance.colors.colSecondaryContainer
                    opacity: schemeScroller.contentX < Math.max(0, schemeScroller.contentWidth
                                                                - schemeScroller.width) - 1 ? (
                                                                                                  rightHover.containsMouse
                                                                                                  ? 1 : 0.85) :
                                                                                              0
                    visible: opacity > 0.01
                    Behavior on opacity {
                        NumberAnimation {
                            duration: 150
                        }
                    }

                    MaterialSymbol {
                        anchors.centerIn: parent
                        text: "chevron_right"
                        iconSize: 24
                        color: Appearance.colors.colOnSecondaryContainer
                    }

                    MouseArea {
                        id: rightHover

                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: {
                            hoverTimer.direction = 1;
                            hoverTimer.restart();
                        }
                        onExited: hoverTimer.stop()
                    }
                }

                Timer {
                    id: hoverTimer

                    interval: 360
                    repeat: true
                    triggeredOnStart: true
                    property int direction: 0
                    onTriggered: schemeArea.scrollBy(direction * (118 + 10))
                }
            }
        }
    }
}
