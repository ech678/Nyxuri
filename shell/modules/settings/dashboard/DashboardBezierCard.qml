pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import qs.shared.theme
import qs.shared.controls
import qs.modules.settings
import qs.app.services
import qs.modules.wallpaper
import qs.shared.i18n

// Interactive easing-curve tile. Reuses BezierCurveEditor from the flat
// settings style; upstream end4-pC has no counterpart, so the span and the
// chrome follow the local dashboard conventions instead.
//
// The chart is square, so the tile needs a [2, 2] cell: one row is 140px tall,
// too short for a chart plus its coordinate row.
DashboardCard {
    id: root

    property string title: ""
    property string icon: "gesture"
    property var tileShape: MaterialShapeCanvas.Shape.Clover8Leaf

    tint: Appearance.colors.colTertiaryContainer

    readonly property string easingMode: PersonalizationConfig.transitionEasingMode
    readonly property bool editable: root.easingMode === "customBezier"

    // Square chart, but the editor also stacks a coordinate row under it, so
    // reserve that height before taking the shorter axis.
    readonly property real chartSide: Math.max(72, Math.min(editorSlot.width, editorSlot.height - 40))

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
            id: editorSlot

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            BezierCurveEditor {
                id: editor

                anchors.centerIn: parent
                chartSize: root.chartSide
                curve: PersonalizationConfig.transitionBezierCurve
                easingMode: root.easingMode
                playDurationMs: Math.max(200, PersonalizationConfig.transitionDurationMs)
                // Editor defaults draw on m3surfaceContainerLowest, a near-black
                // that reads as a hole on the container tile; re-seat the chart
                // on this card's own palette.
                chartSurfaceColor: Appearance.applyAlpha(Appearance.colors.colTertiary, 0.10)
                chartAxisColor: Appearance.applyAlpha(Appearance.colors.colOnTertiaryContainer, 0.38)
                chartPrimaryColor: Appearance.colors.colTertiary
                chartSecondaryColor: Appearance.colors.colOnTertiaryContainer
                chartTertiaryColor: Appearance.colors.colOnTertiaryContainer
                onControlsEdited: nextCurve => WallpaperService.setTransitionBezierCurve(nextCurve)
                onEditRequested: root.openEditor()
            }
        }

        RippleButton {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            buttonRadius: 18
            enabled: root.editable
            opacity: root.editable ? 1 : 0.45
            containerColor: Qt.rgba(1, 1, 1, 0.12)
            rippleColor: Appearance.colors.colOnTertiary
            stateLayerColor: Appearance.colors.colOnTertiary
            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
            hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
            pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
            Accessible.name: root.editable ? I18n.tr("Edit Bézier curve") : I18n.tr("Preset easing")
            downAction: () => Qt.callLater(() => root.openEditor())

            contentItem: RowLayout {
                spacing: 6

                Item {
                    Layout.fillWidth: true
                }

                MaterialSymbol {
                    text: "edit"
                    iconSize: 18
                    color: Appearance.colors.colOnTertiaryContainer
                }

                StyledText {
                    text: root.editable ? I18n.tr("Edit Bézier curve") : I18n.tr("Preset easing")
                    font.weight: Font.Medium
                    color: Appearance.colors.colOnTertiaryContainer
                }

                Item {
                    Layout.fillWidth: true
                }
            }
        }
    }

    function openEditor(): void {
        if (!root.editable)
            return;
        layerEditor.active = true;
        Qt.callLater(() => {
            const item = layerEditor.item;
            if (item)
                item.openWithCurve(PersonalizationConfig.transitionBezierCurve);
        });
    }

    // Full-size editing lives in its own window; the tile only carries the
    // inline chart, so the editor is built on first use.
    Loader {
        id: layerEditor

        active: false
        asynchronous: true

        sourceComponent: Component {
            BezierCurveLayerEditor {
                parentModal: root.Window.window
                onCurveEdited: nextCurve => WallpaperService.setTransitionBezierCurve(nextCurve)
            }
        }
    }
}
