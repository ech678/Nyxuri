import QtQuick
import qs.commons
import qs.ui
import qs.services

Revealer { // Scroll hint
    id: root
    property string icon
    // "left"/"right" (row): hug the inner edge beside the middle lane.
    // "top"/"bottom" (rail, D4h): hug the seam ends of the start/end halves.
    property string side: "left"
    property string tooltipText: ""

    MouseArea {
        id: mouseArea
        anchors.right: root.side === "left" ? parent.right : undefined
        anchors.left: root.side === "right" ? parent.left : undefined
        anchors.bottom: root.side === "top" ? parent.bottom : undefined
        anchors.top: root.side === "bottom" ? parent.top : undefined
        implicitWidth: contentColumn.implicitWidth
        implicitHeight: contentColumn.implicitHeight
        property bool hovered: false

        hoverEnabled: true
        onEntered: hovered = true
        onExited: hovered = false
        acceptedButtons: Qt.NoButton

        property bool showHintTimedOut: false
        onHoveredChanged: showHintTimedOut = false
        Timer {
            running: mouseArea.hovered
            interval: 500
            onTriggered: mouseArea.showHintTimedOut = true
        }

        M3ToolTip {
            extraVisibleCondition: (tooltipText.length > 0 && mouseArea.showHintTimedOut)
            text: tooltipText
        }

        Column {
            id: contentColumn
            anchors {
                fill: parent
            }
            spacing: -5
            MaterialSymbol {
                text: "keyboard_arrow_up"
                iconSize: 14
                color: Appearance.colors.colSubtext
            }
            MaterialSymbol {
                text: root.icon
                iconSize: 14
                color: Appearance.colors.colSubtext
            }
            MaterialSymbol {
                text: "keyboard_arrow_down"
                iconSize: 14
                color: Appearance.colors.colSubtext
            }
        }
    }
}
