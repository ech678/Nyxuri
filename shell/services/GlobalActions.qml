pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.Pipewire
import qs.services

Singleton {
    id: root

    function runById(actionId, param) {
        if (actionId === "screenshot") {
            ActionGateway.execute(["nyxuri-screenshot"], "bar.screenshot");
        } else if (actionId === "color-picker") {
            ActionGateway.execute(["hyprpicker", "-a"], "bar.colorpicker");
        } else if (actionId === "screen-record") {
            ActionGateway.execute([Directories.recordScriptPath], "bar.recording");
        } else if (actionId === "toggle-mic-mute") {
            if (Pipewire.defaultAudioSource) {
                Pipewire.defaultAudioSource.muted = !Pipewire.defaultAudioSource.muted;
            }
        }
    }
}
