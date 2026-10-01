import QtQuick
import QtQuick.Controls
import qs.Common
import qs.Components
import qs.Widgets.common
import "RecordingFormat.js" as RecordingFormat

// The Pill presentation's contents, arranged inside one continuous surface.
// The parent owns all geometry; the action never becomes a satellite.
Item {
    id: root

    required property bool active
    required property bool recording
    required property bool finalizing
    required property string recordingType
    required property double elapsedMs
    required property real recordingInfoProgress
    required property real recordingActionProgress
    required property real processingContentProgress
    property bool vertical: false
    property string edge: "top"
    property double heldElapsedMs: 0
    property real entryProgress: active ? 1 : 0
    readonly property real infoProgress: Math.max(0, Math.min(1, recordingInfoProgress))
    readonly property real actionProgress: Math.max(0, Math.min(1, recordingActionProgress))
    readonly property real processingProgress: Math.max(0, Math.min(1, processingContentProgress))
    readonly property color typeContainerColor: Appearance.colors.colTertiaryContainer
    readonly property color typeContentColor: Appearance.colors.colOnTertiaryContainer

    signal stopRequested

    opacity: entryProgress
    onElapsedMsChanged: {
        if (recording)
            heldElapsedMs = elapsedMs;
    }
    onRecordingChanged: {
        if (recording)
            heldElapsedMs = elapsedMs;
        else if (!finalizing && !active)
            heldElapsedMs = 0;
    }

    Grid {
        anchors.centerIn: parent
        columns: root.vertical ? 1 : 3
        spacing: root.vertical ? 8 : 10
        opacity: root.infoProgress
        visible: opacity > 0.01

        Item {
            width: 42
            height: 42

            Rectangle {
                anchors.centerIn: parent
                width: 30
                height: 30
                radius: 15
                color: root.typeContainerColor

                MaterialSymbol {
                    anchors.centerIn: parent
                    text: root.recordingType === "gif" ? "gif_box" : "videocam"
                    iconSize: 18
                    fill: 1
                    color: root.typeContentColor
                }
            }
        }

        Item {
            width: root.vertical ? 42 : 86
            height: root.vertical ? 72 : 42

            Text {
                anchors.centerIn: parent
                text: RecordingFormat.elapsed(root.heldElapsedMs)
                color: Appearance.colors.colOnLayer0
                font.family: Fonts.numeric
                font.pixelSize: 18
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                rotation: !root.vertical ? 0 : root.edge === "left" ? -90 : 90
            }
        }

        ToolButton {
            id: stopButton

            width: 42
            height: 42
            padding: 0
            opacity: root.actionProgress
            enabled: root.recording && root.actionProgress > 0.55
            hoverEnabled: true
            Accessible.name: qsTr("Stop recording")
            Accessible.role: Accessible.Button
            onClicked: root.stopRequested()
            background: Item {}
            contentItem: Item {
                Rectangle {
                    anchors.centerIn: parent
                    width: 16
                    height: 16
                    radius: 8
                    color: Appearance.colors.colError

                    SequentialAnimation on opacity {
                        running: root.recording && root.actionProgress > 0.01
                        loops: Animation.Infinite
                        NumberAnimation {
                            from: 0.35
                            to: 1
                            duration: 800
                            easing.type: Easing.InOutSine
                        }
                        NumberAnimation {
                            from: 1
                            to: 0.35
                            duration: 800
                            easing.type: Easing.InOutSine
                        }
                    }
                }
            }
            StyledToolTip {
                extraVisibleCondition: stopButton.hovered && stopButton.enabled
                text: qsTr("Stop recording")
            }
        }
    }

    Grid {
        anchors.centerIn: parent
        columns: root.vertical ? 1 : 2
        spacing: root.vertical ? 8 : 10
        opacity: root.processingProgress
        visible: opacity > 0.01

        Item {
            width: root.vertical ? 42 : 30
            height: 30

            Rectangle {
                anchors.centerIn: parent
                width: 30
                height: 30
                radius: 15
                color: root.typeContainerColor

                ProcessingSpiralIndicator {
                    anchors.centerIn: parent
                    running: root.finalizing && root.processingProgress > 0.01
                    dotColor: root.typeContentColor
                }
            }
        }

        Item {
            width: root.vertical ? 42 : processingLabel.implicitWidth
            height: root.vertical ? processingLabel.implicitWidth : 30

            Text {
                id: processingLabel
                anchors.centerIn: parent
                text: qsTr("Processing")
                color: Appearance.colors.colOnLayer0
                font.family: Fonts.ui
                font.pixelSize: 15
                font.weight: Font.DemiBold
                rotation: !root.vertical ? 0 : root.edge === "left" ? -90 : 90
            }
        }
    }
}
