import QtQuick
import QtQuick.Layouts
import Clavis.Cava
import qs.Common
import "RecordingFormat.js" as RecordingFormat

Item {
    id: root

    required property bool sessionActive
    required property bool recording
    required property bool stopping
    required property string sourceNodeName
    required property bool captureSink
    required property double elapsedMs
    property bool vertical: false
    property string edge: "top"
    property real contentProgress: 0

    signal stopRequested()
    signal collapseRequested()
    signal exitFinished()

    function beginEntry() {
        exitSequence.stop();
        entryAnimation.stop();
        entryAnimation.restart();
    }

    function beginExit() {
        entryAnimation.stop();
        exitSequence.restart();
    }

    AudioLevelProvider {
        id: levelProvider

        active: root.recording && root.sourceNodeName !== ""
        sourceNodeName: root.sourceNodeName
        captureSink: root.captureSink
        onErrorStringChanged: {
            if (errorString !== "")
                console.warn("[AudioLevelProvider]", errorString);

        }
    }

    Item {
        id: contentLayer

        anchors.fill: parent
        opacity: root.contentProgress

        GridLayout {
            anchors.fill: parent
            anchors.leftMargin: root.vertical ? 8 : 12
            anchors.rightMargin: root.vertical ? 8 : 8
            anchors.topMargin: root.vertical ? 12 : 0
            anchors.bottomMargin: root.vertical ? 8 : 0
            rowSpacing: 8
            columnSpacing: 8
            columns: root.vertical ? 1 : 3

            AudioWaveform {
                id: waveform

                Layout.fillWidth: !root.vertical
                Layout.fillHeight: root.vertical
                Layout.preferredWidth: root.vertical ? 40 : -1
                Layout.preferredHeight: root.vertical ? -1 : 40
                vertical: root.vertical
                active: root.sessionActive
                acceptSamples: root.recording
                sourceAvailable: levelProvider.available
                amplitude: levelProvider.visualAmplitude
                sampleTimestampMs: levelProvider.visualTimestampMs
            }

            Item {
                Layout.preferredWidth: root.vertical ? 44 : 72
                Layout.preferredHeight: root.vertical ? 72 : 40
                Layout.alignment: Qt.AlignVCenter

                Text {
                    anchors.centerIn: parent
                    width: root.vertical ? parent.height : parent.width
                    text: RecordingFormat.elapsed(root.elapsedMs)
                    horizontalAlignment: Text.AlignHCenter
                    color: Appearance.colors.colOnSurface
                    font.family: Fonts.numeric
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    font.features: {
                        "tnum": 1
                    }
                    rotation: !root.vertical ? 0 : root.edge === "left" ? -90 : 90
                }

            }

            AudioStopButton {
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                Layout.alignment: Qt.AlignVCenter
                stopping: root.stopping
                canStop: root.recording
                onStopRequested: root.stopRequested()
            }

        }

    }

    NumberAnimation {
        id: entryAnimation

        target: root
        property: "contentProgress"
        to: 1
        duration: KeystoneMotion.audioContentEnterDuration
        easing.type: KeystoneMotion.type
        easing.bezierCurve: KeystoneMotion.hoverBezier
    }

    SequentialAnimation {
        id: exitSequence

        NumberAnimation {
            target: root
            property: "contentProgress"
            to: 0
            duration: KeystoneMotion.audioContentExitDuration
            easing.type: Appearance.animation.emphasizedAccel.type
            easing.bezierCurve: Appearance.animation.emphasizedAccel.bezierCurve
        }

        ScriptAction {
            script: root.collapseRequested()
        }

        PauseAnimation {
            duration: KeystoneMotion.audioCollapseDuration
        }

        ScriptAction {
            script: root.exitFinished()
        }

    }

}
