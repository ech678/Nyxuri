pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property string kind: ""
    property real value: 0
    property bool muted: false
    property bool visible: false
    property bool primed: false
    property int holdMs: 1600

    function show(nextKind, nextValue, nextMuted) {
        root.kind = nextKind;
        root.value = Math.max(0, Math.min(1, nextValue));
        root.muted = nextMuted === true;
        root.visible = true;
        hideTimer.restart();
    }

    function hide() {
        hideTimer.stop();
        root.visible = false;
    }

    function acceptVolume(nextValue, nextMuted) {
        if (!root.primed) {
            root.primed = true;
            return;
        }
        root.show(nextMuted ? "muted" : "volume", nextValue, nextMuted);
    }

    function acceptBrightness(nextValue) {
        if (!root.primed)
            return;
        root.show("brightness", nextValue, false);
    }

    Timer {
        id: hideTimer
        interval: root.holdMs
        onTriggered: root.visible = false
    }

    Connections {
        target: VolumeService
        function onSinkVolumeChanged() {
            root.acceptVolume(VolumeService.sinkVolume, VolumeService.sinkMuted);
        }
        function onSinkMutedChanged() {
            root.acceptVolume(VolumeService.sinkVolume, VolumeService.sinkMuted);
        }
    }

    Connections {
        target: BrightnessService
        function onBrightnessValueChanged() {
            root.acceptBrightness(BrightnessService.brightnessValue);
        }
    }
}
