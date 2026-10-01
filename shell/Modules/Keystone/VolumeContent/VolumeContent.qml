import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Common
import qs.Components

Item {
    id: root

    property string mode: "volume"
    property var audioNode: null
    property real externalValue: 0
    property bool externalMuted: false
    property string iconName: ""
    property bool vertical: false
    signal moved(real value)
    signal iconActivated()

    readonly property bool usesAudioNode: audioNode !== null && audioNode !== undefined
    readonly property real controlValue: usesAudioNode ? audioNode.volume : externalValue
    readonly property bool isMuted: usesAudioNode ? audioNode.muted : externalMuted
    readonly property real displayVolume: root.isMuted ? 0.0 : root.controlValue
    readonly property string effectiveIconName: {
        if (root.iconName.length > 0)
            return root.iconName;
        if (root.mode === "brightness")
            return "brightness_medium";
        if (root.mode === "mic")
            return root.isMuted || root.displayVolume <= 0 ? "mic_off" : "mic";
        return root.isMuted || root.displayVolume <= 0 ? "volume_off" : "volume_up";
    }

    readonly property bool isInteractionActive: hoverArea.containsMouse || dragArea.pressed

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton 
    }

    GridLayout {
        id: volumeLayout

        anchors.fill: parent
        anchors.leftMargin: root.vertical ? 16 : 24
        anchors.rightMargin: root.vertical ? 16 : 24
        anchors.topMargin: root.vertical ? 16 : 0
        anchors.bottomMargin: root.vertical ? 16 : 0
        rows: root.vertical ? 3 : 1
        columns: root.vertical ? 1 : 3
        rowSpacing: root.vertical ? 12 : 0
        columnSpacing: root.vertical ? 0 : 16

        MaterialSymbol {
            id: sliderIcon

            text: root.effectiveIconName
            iconSize: 24
            fill: root.isMuted ? 1 : 0
            color: Appearance.colors.colOnLayer0
            Layout.row: root.vertical ? 0 : 0
            Layout.column: root.vertical ? 0 : 0
            Layout.alignment: root.vertical ? Qt.AlignHCenter : Qt.AlignVCenter

            MouseArea {
                anchors.fill: parent
                anchors.margins: -10 
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.usesAudioNode)
                        root.audioNode.muted = !root.audioNode.muted;
                    else
                        root.iconActivated();
                }
            }
        }

        Item {
            id: track

            Layout.row: root.vertical ? 1 : 0
            Layout.column: root.vertical ? 0 : 1
            Layout.fillWidth: !root.vertical
            Layout.fillHeight: root.vertical
            Layout.preferredWidth: root.vertical ? 6 : -1
            Layout.preferredHeight: root.vertical ? -1 : 6
            Layout.minimumWidth: root.vertical ? 6 : 0
            Layout.minimumHeight: root.vertical ? 100 : 6
            Layout.alignment: root.vertical ? Qt.AlignHCenter : Qt.AlignVCenter

            readonly property real progress: Math.max(0, Math.min(1, root.displayVolume))
            readonly property real gapWidth: 10
            readonly property real splitX: progress * width
            readonly property real leftWidth: Math.max(0, splitX - gapWidth / 2)
            readonly property real rightX: Math.min(width, splitX + gapWidth / 2)
            readonly property real rightWidth: Math.max(0, width - rightX)
            readonly property real splitY: (1 - progress) * height
            readonly property real topHeight: Math.max(0, splitY - gapWidth / 2)
            readonly property real bottomY: Math.min(height, splitY + gapWidth / 2)
            readonly property real bottomHeight: Math.max(0, height - bottomY)

            Rectangle {
                id: fillRect
                x: 0
                y: root.vertical ? parent.height - height
                    : (parent.height - height) / 2
                width: root.vertical ? parent.width : track.leftWidth
                height: root.vertical ? track.bottomHeight : parent.height
                radius: 3
                color: Appearance.colors.colOnLayer0
                
                Behavior on width { 
                    enabled: !dragArea.pressed
                    NumberAnimation { duration: 150; easing.type: Easing.OutQuint } 
                }
            }

            Rectangle {
                id: restRect
                x: root.vertical ? 0 : track.rightX
                y: root.vertical ? 0 : (parent.height - height) / 2
                width: root.vertical ? parent.width : track.rightWidth
                height: root.vertical ? track.topHeight : parent.height
                radius: 3
                color: Appearance.applyAlpha(Appearance.colors.colOnLayer0, 0.22)

                Behavior on x {
                    enabled: !dragArea.pressed
                    NumberAnimation { duration: 150; easing.type: Easing.OutQuint }
                }

                Behavior on width {
                    enabled: !dragArea.pressed
                    NumberAnimation { duration: 150; easing.type: Easing.OutQuint }
                }

                Behavior on height {
                    enabled: !dragArea.pressed
                    NumberAnimation { duration: 150; easing.type: Easing.OutQuint }
                }
            }

            MouseArea {
                id: dragArea
                anchors.fill: parent
                anchors.margins: -10 
                cursorShape: Qt.PointingHandCursor
                preventStealing: true

                function setVol(position) {
                    let p = root.vertical ? 1 - position / height : position / width
                    if (p < 0) p = 0
                    if (p > 1) p = 1

                    if (root.usesAudioNode) {
                        root.audioNode.volume = p
                        if (root.isMuted)
                            root.audioNode.muted = false
                    } else {
                        root.moved(p)
                    }
                }

                onPressed: (mouse) => setVol(root.vertical ? mouse.y : mouse.x)
                onPositionChanged: (mouse) => setVol(root.vertical ? mouse.y : mouse.x)
            }
        }

        Text {
            Layout.row: root.vertical ? 2 : 0
            Layout.column: root.vertical ? 0 : 2
            text: Math.round(root.displayVolume * 100)
            color: Appearance.colors.colOnLayer0
            font.pixelSize: 15
            font.bold: true
            font.family: Fonts.numeric
            Layout.alignment: root.vertical ? Qt.AlignHCenter : Qt.AlignVCenter
            Layout.minimumWidth: root.vertical ? 0 : 32
            horizontalAlignment: root.vertical ? Text.AlignHCenter : Text.AlignRight
        }
    }
}
