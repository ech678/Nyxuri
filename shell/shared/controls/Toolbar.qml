pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme

// Material 3 expressive toolbar. Ported 1:1 from end4-pC's Toolbar.
// https://m3.material.io/components/toolbars
Item {
    id: root

    property bool enableShadow: true
    property real padding: 8
    property alias colBackground: background.color
    property alias spacing: toolbarLayout.spacing
    default property alias content: toolbarLayout.data

    implicitWidth: background.implicitWidth
    implicitHeight: background.implicitHeight
    property alias radius: background.radius

    Loader {
        active: root.enableShadow
        anchors.fill: background

        sourceComponent: StyledRectangularShadow {
            target: background
            anchors.fill: undefined
        }
    }

    Rectangle {
        id: background

        anchors.fill: parent
        color: Appearance.m3colors.m3surfaceContainer
        implicitHeight: 56
        implicitWidth: toolbarLayout.implicitWidth + root.padding * 2
        radius: height / 2

        // Plain Items don't consume mouse events in QML, so clicks on the
        // toolbar's empty areas would fall through to content underneath
        // (e.g. the card grid). Block them; interactive children (buttons, text
        // fields) sit above and still get their own events.
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            hoverEnabled: true
            onClicked: mouse => mouse.accepted = true
            onWheel: wheel => wheel.accepted = true
        }

        RowLayout {
            id: toolbarLayout

            anchors.fill: parent
            anchors.margins: root.padding
            spacing: 4
        }
    }
}
