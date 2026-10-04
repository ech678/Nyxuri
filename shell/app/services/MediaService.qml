pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.Mpris
import qs.shared.i18n

Item {
    id: root

    // 获取所有可用的播放器数组
    readonly property list<MprisPlayer> list: Mpris.players.values

    // 保存用户手动指定的播放器
    property var manualActive: null

    // 核心计算逻辑：优先手动指定 -> 正在播放的 -> 列表第一个 -> null
    readonly property MprisPlayer active: {
        if (manualActive)
            return manualActive;
        for (let i = 0; i < list.length; i++) {
            if (list[i].isPlaying)
                return list[i];
        }
        return list.length > 0 ? list[0] : null;
    }

    // One shared, low-frequency position tick feeds all media surfaces. MPRIS
    // implementations do not need a separate QML polling loop per consumer.
    property real currentPosition: 0
    property int positionSubscribers: 0

    function acquirePositionTracking() {
        positionSubscribers += 1;
        if (positionSubscribers === 1)
            refreshPosition();
    }

    function releasePositionTracking() {
        positionSubscribers = Math.max(0, positionSubscribers - 1);
        if (positionSubscribers === 0)
            root.currentPosition = 0;
    }

    function refreshPosition() {
        const player = root.active;
        if (!player || !player.positionSupported || player.canControl === false) {
            root.currentPosition = 0;
            return;
        }
        try {
            root.currentPosition = Math.max(0, Number(player.position) || 0);
        } catch (e) {
            root.currentPosition = 0;
        }
    }

    onActiveChanged: {
        if (root.positionSubscribers > 0)
            root.refreshPosition();
    }
    Component.onCompleted: {
        if (root.positionSubscribers > 0)
            root.refreshPosition();
    }

    Timer {
        id: positionPollTimer
        interval: 500
        repeat: true
        triggeredOnStart: false
        running: root.positionSubscribers > 0 && root.active !== null && root.active.isPlaying
                 && root.active.positionSupported
        onTriggered: root.refreshPosition()
    }

    Connections {
        target: root.active
        ignoreUnknownSignals: true

        function onIsPlayingChanged() {
            if (root.positionSubscribers > 0)
                root.refreshPosition();
        }
        function onPositionChanged() {
            if (root.positionSubscribers > 0)
                root.refreshPosition();
        }
        function onLengthChanged() {
            if (root.positionSubscribers > 0)
                root.refreshPosition();
        }
    }

    // 监听底层状态：如果用户手动指定的播放器被彻底关掉（进程结束），则清空手动状态，让系统重新接管
    Connections {
        target: Mpris.players
        function onValuesChanged() {
            if (root.manualActive) {
                let stillExists = false;
                for (let i = 0; i < Mpris.players.values.length; i++) {
                    if (Mpris.players.values[i] === root.manualActive) {
                        stillExists = true;
                        break;
                    }
                }
                if (!stillExists)
                    root.manualActive = null;
            }
            if (root.positionSubscribers > 0)
                root.refreshPosition();
        }

        function onObjectRemovedPost(object, index) {
            if (root.manualActive === object)
                root.manualActive = null;
            if (root.active === object) {
                root.currentPosition = 0;
                root.refreshPosition();
            }
        }
    }

    // 辅助函数：将乱七八糟的底层进程名清洗为美观的名称
    function getIdentity(player) {
        if (!player || !player.identity)
            return I18n.tr("No media");
        let name = player.identity.toLowerCase();

        if (name.includes("chrome") || name.includes("chromium"))
            return I18n.tr("Browser");
        if (name.includes("firefox"))
            return "Firefox";
        if (name.includes("spotify"))
            return "Spotify";
        if (name.includes("vlc"))
            return "VLC";
        if (name.includes("edge"))
            return "Edge";

        return player.identity;
    }

    Component.onDestruction: {
        positionPollTimer.stop();
    }
}
