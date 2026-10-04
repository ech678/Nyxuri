pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

// Stepper tile. Ported from end4-pC's DashboardSpinCard.
DashboardCard {
    id: root

    property string controlKey: ""
    property string title: ""
    property string icon: "tune"
    property var tileShape: MaterialShapeCanvas.Shape.Gem
    property var override: null

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property real current: root.control ? root.control.get() : 0

    tint: Appearance.colors.colPrimaryContainer

    function step(direction) {
        if (!root.control)
            return;
        const stepSize = root.control.stepSize ?? 1;
        const next = Math.max(root.control.from ?? -Infinity, Math.min(root.control.to ?? Infinity,
                                                                       root.current + direction * stepSize));
        Qt.callLater(() => root.control.set(next));
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            MaterialShapeWrappedMaterialSymbol {
                wrappedShape: root.tileShape
                text: root.icon
                iconSize: 22
                fill: 1
                padding: 9
                color: Appearance.colors.colPrimary
                colSymbol: Appearance.colors.colOnPrimary
            }

            StyledText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Typography.bodyLarge.pixelSize
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnPrimaryContainer
                wrapMode: Text.WordWrap
                maximumLineCount: 2
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
                model: [-1, 1]

                delegate: Item {
                    id: stepSlot

                    required property int modelData

                    Layout.fillWidth: stepSlot.modelData === 1
                    implicitWidth: 40
                    implicitHeight: 40

                    RippleButton {
                        anchors.right: stepSlot.modelData === 1 ? parent.right : undefined
                        implicitWidth: 40
                        implicitHeight: 40
                        buttonRadius: 20
                        containerColor: Qt.rgba(1, 1, 1, 0.14)
                        stateLayerColor: Appearance.colors.colOnPrimaryContainer
                        stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                        hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                        pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                        downAction: () => root.step(stepSlot.modelData)

                        contentItem: Item {
                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: stepSlot.modelData === 1 ? "add" : "remove"
                                iconSize: 22
                                color: Appearance.colors.colOnPrimaryContainer
                            }
                        }
                    }
                }
            }
        }
    }

    StyledText {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 14
        text: Math.round(root.current)
        font.pixelSize: 28
        font.weight: Font.Light
        color: Appearance.colors.colOnPrimaryContainer
    }
}
