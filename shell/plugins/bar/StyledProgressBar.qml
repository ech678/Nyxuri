// Forked from pctrade/end4-pC modules/common/widgets/StyledProgressBar.qml
// at b881970bfc25ff92b0f72b751c810a178c5fc677 (GPL-3.0-or-later).
// Nyxuri adaptation: shell commons/ui import paths.
pragma ComponentBehavior: Bound
import qs.commons
import qs.ui
import QtQuick
import QtQuick.Controls


/**
 * Material 3 progress bar. See https://m3.material.io/components/progress-indicators/overview
 */
ProgressBar {
    id: root
    property real valueBarWidth: 120
    property real valueBarHeight: 4
    property real valueBarGap: 4
    property color highlightColor: Appearance?.colors.colPrimary ?? "#685496"
    property color trackColor: Appearance?.m3colors.m3secondaryContainer ?? "#F1D3F9"
    property bool wavy: false // If true, the progress bar will have a wavy fill effect
    property bool animateWave: true
    property real waveAmplitudeMultiplier: wavy ? 0.5 : 0
    property real waveFrequency: 6
    property real waveFps: 60

    Behavior on waveAmplitudeMultiplier {
        animation: Appearance?.animation.elementMoveFast.numberAnimation.createObject(this)
    }

    Behavior on value {
        animation: Appearance?.animation.elementMoveEnter.numberAnimation.createObject(this)
    }
    
    background: Item {
        implicitHeight: valueBarHeight
        implicitWidth: valueBarWidth
    }

    contentItem: Item {
        id: contentItem
        anchors.fill: parent

        Loader {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
            }
            active: root.wavy
            sourceComponent: WavyLine {
                id: wavyFill
                frequency: root.waveFrequency
                color: root.highlightColor
                amplitudeMultiplier: root.wavy ? 0.5 : 0
                height: contentItem.height * 6
                width: contentItem.width * root.visualPosition
                lineWidth: contentItem.height
                fullLength: root.width
                Connections {
                    target: root
                    function onValueChanged() { wavyFill.requestPaint(); }
                    function onHighlightColorChanged() { wavyFill.requestPaint(); }
                }
                FrameAnimation {
                    running: root.animateWave
                    onTriggered: {
                        wavyFill.requestPaint()
                    }
                }
            }
        }

        Loader {
            active: !root.wavy
            sourceComponent: Rectangle {
                anchors.left: parent.left
                width: contentItem.width * root.visualPosition
                height: contentItem.height
                radius: height / 2
                color: root.highlightColor
            }
        }
        
        Rectangle { // Right remaining part fill
            anchors.right: parent.right
            width: (1 - root.visualPosition) * parent.width - valueBarGap
            height: parent.height
            radius: height / 2
            color: root.trackColor
        }
        
        Rectangle { // Stop point
            anchors.right: parent.right
            width: valueBarGap
            height: valueBarGap
            radius: height / 2
            color: root.highlightColor
        }
    }
}
