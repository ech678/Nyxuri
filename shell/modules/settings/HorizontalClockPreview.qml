import QtQuick
import Qt5Compat.GraphicalEffects
import qs.Common
import qs.Services
import qs.Modules.Keystone.ClockContent

Item {
    id: root

    readonly property real referenceWidth: 220
    readonly property real referenceHeight: 42
    readonly property real previewScale: Math.max(0.01, Math.min(width / referenceWidth, height / referenceHeight))
    property string edge: "top"
    readonly property int h0: clockContent.h0
    readonly property int h1: clockContent.h1
    readonly property int m0: clockContent.m0
    readonly property int m1: clockContent.m1
    readonly property string periodLead: clockContent.periodLead

    implicitHeight: 42
    implicitWidth: 220

    Rectangle {
        id: shadowSource

        anchors.fill: parent
        radius: height / 2
        color: BlurService.backgroundColor(Appearance.colors.colLayer0)
        visible: false
    }

    DropShadow {
        anchors.fill: shadowSource
        source: shadowSource
        horizontalOffset: 0
        verticalOffset: 6
        radius: 20
        samples: 32
        color: "#80000000"
        cached: true
    }

    Rectangle {
        id: surface

        anchors.fill: parent
        radius: height / 2
        color: BlurService.backgroundColor(Appearance.colors.colLayer0)
        clip: true

        Item {
            id: scaledClockContent

            width: root.referenceWidth
            height: root.referenceHeight
            anchors.centerIn: parent
            scale: root.previewScale

            ClockContent {
                id: clockContent

                anchors.fill: parent
                edge: root.edge
            }

        }

    }

}
