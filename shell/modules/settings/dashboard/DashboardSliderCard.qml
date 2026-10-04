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

        // Two-sided spacers, as in end4-pC's DashboardSliderCard. A single
        // leading spacer would strand the slider on the card's bottom edge and
        // pool every unused pixel into one dead band above it — at the [2,2]
        // span that is ~158px of nothing on a 292px tile. Splitting the slack
        // above and below reads as deliberate padding and keeps the track
        // optically centred.
        Item {
            Layout.fillHeight: true
            Layout.maximumHeight: 24
        }

        MaterialSlider {
            id: slider

            Layout.fillWidth: true
            // Absorb what is left after the capped spacers. MaterialSlider
            // re-centres its track from the actual height, so a taller tile
            // widens the gap between the label and the track rather than
            // opening a void underneath it.
            Layout.fillHeight: true
            Layout.minimumHeight: implicitHeight
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

        Item {
            Layout.fillHeight: true
            Layout.maximumHeight: 24
        }
    }
}
