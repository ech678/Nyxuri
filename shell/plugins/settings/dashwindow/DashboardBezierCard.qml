pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import qs.commons
import qs.ui
import ".."
import qs.services
import qs.commons.i18n

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

    tint: Appearance.colors.colLayer1

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
                color: Appearance.colors.colOnLayer1
                elide: Text.ElideRight
            }
        }

        Item {
            id: editorSlot

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Loader {
                id: editorLoader
                anchors.centerIn: parent
                active: StateProjection.isEnabled("wallpaper")
                source: Qt.resolvedUrl("../../wallpaper/BezierCurveEditor.qml")
                onLoaded: {
                    if (item) {
                        item.chartSize = root.chartSide;
                        item.curve = Qt.binding(() => PersonalizationConfig.transitionBezierCurve);
                        item.easingMode = Qt.binding(() => root.easingMode);
                        item.playDurationMs = Qt.binding(() => Math.max(200, PersonalizationConfig.transitionDurationMs));
                        item.chartSurfaceColor = Appearance.applyAlpha(Appearance.colors.colTertiary, 0.10);
                        item.chartAxisColor = Appearance.applyAlpha(Appearance.colors.colOnLayer1, 0.38);
                        item.chartPrimaryColor = Appearance.colors.colTertiary;
                        item.chartSecondaryColor = Appearance.colors.colOnLayer1;
                        item.chartTertiaryColor = Appearance.colors.colOnLayer1;
                        item.controlsEdited.connect(nextCurve => PersonalizationConfig.setTransitionBezierCurve(nextCurve));
                        item.editRequested.connect(root.openEditor);
                    }
                }
            }
        }

        RippleButton {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            buttonRadius: 18
            enabled: root.editable
            opacity: root.editable ? 1 : 0.45
            containerColor: Appearance.colors.colSurfaceContainerHigh
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
                    color: Appearance.colors.colOnLayer1
                }

                StyledText {
                    text: root.editable ? I18n.tr("Edit Bézier curve") : I18n.tr("Preset easing")
                    font.weight: Font.Medium
                    color: Appearance.colors.colOnLayer1
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
        source: StateProjection.isEnabled("wallpaper") ? Qt.resolvedUrl("../../wallpaper/BezierCurveLayerEditor.qml") : ""
        onLoaded: {
            if (item) {
                item.parentModal = root.Window.window;
                item.curveEdited.connect(nextCurve => PersonalizationConfig.setTransitionBezierCurve(nextCurve));
            }
        }
    }
}
