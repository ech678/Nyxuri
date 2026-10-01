import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: root
    required property string label
    required property bool animate
    width: 480
    height: 320
    visible: true
    title: "Clavis Capture Fixture " + label
    color: label === "A" ? "#b02436" : "#164eb5"
    property int tick: 0
    Timer {
        interval: 100
        repeat: true
        running: root.animate
        onTriggered: root.tick++
    }
    Rectangle {
        x: (root.tick * 17) % Math.max(1, root.width - width)
        y: 24
        width: 70
        height: 70
        color: "#ffdc50"
    }
    Text {
        anchors.centerIn: parent
        text: root.label + "\n" + root.tick
        color: "white"
        font.pixelSize: 64
        horizontalAlignment: Text.AlignHCenter
    }
    Rectangle {
        width: 28
        height: 28
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: "#40eac0"
    }
}
