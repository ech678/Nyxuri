import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Stepper row (Caelestia Nexus StepperRow): label plus optional subtext on
// the left, the shared pill stepper (`-` value `+`) on the right with press
// repeat.
ConnectedRect {
    id: root

    property alias label: titleLabel.text
    property string subtext: ""
    property alias value: stepper.value
    property alias from: stepper.from
    property alias to: stepper.to
    property alias stepSize: stepper.stepSize
    property alias busy: stepper.busy

    signal moved(int value)

    Layout.fillWidth: true
    implicitHeight: column.implicitHeight + NexusStyle.padding.medium * 2

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.largeIncreased
        anchors.rightMargin: NexusStyle.padding.largeIncreased
        spacing: NexusStyle.padding.small

        ColumnLayout {
            id: column

            Layout.fillWidth: true
            spacing: 0

            StyledText {
                id: titleLabel

                Layout.fillWidth: true
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
                elide: Text.ElideRight
            }

            StyledText {
                Layout.fillWidth: true
                visible: root.subtext.length > 0
                text: root.subtext
                color: Appearance.m3colors.m3outline
                font.pixelSize: NexusStyle.font.labelSmall
                elide: Text.ElideRight
            }
        }

        MaterialStepper {
            id: stepper

            onValueModified: value => root.moved(value)
        }
    }
}
