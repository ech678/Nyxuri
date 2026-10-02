pragma ComponentBehavior: Bound

import QtQuick
import qs.shared.theme
import qs.app.services

Item {
    id: root

    required property var player
    readonly property bool active: visible && !!player && player.isPlaying
    readonly property string spectrumToken: "keystone-lyrics-" + String(root)

    implicitWidth: 21
    implicitHeight: 21

    function syncSpectrum() {
        if (active)
            AudioSpectrum.acquire(spectrumToken);
        else
            AudioSpectrum.release(spectrumToken);
    }

    onActiveChanged: syncSpectrum()
    Component.onCompleted: syncSpectrum()
    Component.onDestruction: AudioSpectrum.release(spectrumToken)

    Row {
        anchors.centerIn: parent
        spacing: 2

        Repeater {
            model: 5

            Rectangle {
                required property int index
                readonly property real magnitude: root.active && AudioSpectrum.available ? Math.max(0, Math.min(
                                                                                                        1, Number(
                                                                                                            AudioSpectrum.values[Math.floor(
                                                                                                                                     index * AudioSpectrum.bars
                                                                                                                                     / 5)]) || 0)) :
                                                                                           0

                anchors.verticalCenter: parent.verticalCenter
                width: 2.6
                height: 2.6 + (root.height - 2.6) * magnitude
                radius: width / 2
                color: Appearance.colors.colOnLayer0

                Behavior on height {
                    NumberAnimation {
                        duration: 80
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: [0.2, 0, 0, 1, 1, 1]
                    }
                }
            }
        }
    }
}
