pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

// Continuous value tile. Ported from end4-pC's DashboardSliderCard; the slider
// is nyxuri's MaterialSlider (end4-pC's StyledSlider has no counterpart here).
DashboardCard {
    id: root

    property string controlKey: ""
    property string title: ""
    property string icon: "tune"
    property var tileShape: MaterialShapeCanvas.Shape.Flower
    property bool showPercent: true
    property var override: null

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property real current: root.control ? root.control.get() : 0
    readonly property real fromValue: root.control && root.control.from !== undefined ? root.control.from : 0
    readonly property real toValue: root.control && root.control.to !== undefined ? root.control.to : 1

    tint: Appearance.colors.colSecondaryContainer

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
                color: Appearance.colors.colSecondary
                colSymbol: Appearance.colors.colOnSecondary
            }

            StyledText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Typography.titleLarge.pixelSize
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnSecondaryContainer
                elide: Text.ElideRight
            }

            StyledText {
                text: root.showPercent ? Math.round((root.current - root.fromValue) / Math.max(0.0001,
                                                                                               root.toValue
                                                                                               - root.fromValue)
                                                    * 100) + "%" : Math.round(root.current)
                font.pixelSize: 28
                font.weight: Font.Light
                color: Appearance.colors.colOnSecondaryContainer
            }
        }

        // One flexible band between the label and the track, and the slider at a
        // fixed compact height.
        //
        // end4-pC's DashboardSliderCard puts two uncapped `fillHeight` spacers
        // around a `StyledSlider` whose implicit height is only about a track
        // thick, so its [2, 1] tile has room to spare. nyxuri's MaterialSlider
        // is a 78px control — twice that — and at 78 it does not fit a 140px
        // tile alongside a 46px label row. The equivalent arrangement is
        // therefore the same [2, 1] span with a compact slider: 48px plus the
        // label fits with room left over, and the single spacer puts the little
        // that remains in one place above the control instead of splitting it
        // into two dead strips.
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 0
        }

        MaterialSlider {
            id: slider

            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Layout.minimumHeight: 48
            from: root.fromValue
            to: root.toValue
            stepSize: root.control ? root.control.stepSize ?? 0 : 0
            discrete: stepSize > 0
            value: root.current
            accessibleName: root.title
            onMoved: value => {
                if (root.control)
                    root.control.set(value);
            }
        }
    }
}
