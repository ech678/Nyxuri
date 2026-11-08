// Fork & Trim: end4-pC modules/ii/bar/DynamicIsland.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import Quickshell.Services.Mpris
import Qt5Compat.GraphicalEffects
import QtQuick.Controls
import qs.services
import qs.commons
import qs.ui

Item {
    id: root
    property bool mirrored: false

    readonly property real pillHeight: 32
    readonly property real idleCollapsedWidth: 144
    readonly property real sessionWidth: 164
    property real idleTextContentWidth: 0
    readonly property real idleWidth: Math.max(root.idleCollapsedWidth, root.idleTextContentWidth)
    readonly property real mediaCollapsedWidth: 140
    readonly property real mediaExpandedWidthCap: 220
    property real mediaTextContentWidth: 0
    property bool mediaTrackInfoVisible: mediaHoverHandler.hovered || mediaTrackChangeTimer.running
    readonly property real mediaExpandedWidth: Math.min(root.mediaExpandedWidthCap, root.mediaTextContentWidth)
    readonly property real mediaWidth: root.mediaTrackInfoVisible ? root.mediaExpandedWidth : root.mediaCollapsedWidth
    readonly property real timerWidth: 130
    readonly property real osdWidth: 132
    readonly property real notificationWidth: 220
    readonly property real batteryWidth: 170
    readonly property real badgeSize: 32
    readonly property real badgeSpacing: 6
    readonly property bool isMaterial: Config.options.bar.cornerStyle === 3 || Config.options.bar.cornerStyle === 4
    property bool vertical: Config.options.bar.vertical

    property string manualFocusId: ""

    property bool forceIdle: false

    readonly property var displayedProvider: root.forceIdle ? null : root.activeProvider

    onActiveProviderChanged: {
        if (root.activeProvider && root.alwaysWinIds.includes(root.activeProvider.id)) {
            root.forceIdle = false
        }
    }

    readonly property bool isPrimaryScreen: {
        const winScreen = root.QsWindow.window?.screen;
        const primary = Quickshell.screens[0];
        return !winScreen || winScreen === primary;
    }

    Component.onCompleted: {
        if (root.isPrimaryScreen) {
            ActionGateway.islandHost = root;
        }
    }

    Component.onDestruction: {
        if (ActionGateway.islandHost === root) {
            ActionGateway.islandHost = null;
        }
    }

    function invoke(method) {
        if (!method) return "ISLAND_UNAVAILABLE";
        if (method === "toggle") {
            root.forceIdle = !root.forceIdle;
            return true;
        } else if (method === "open") {
            root.forceIdle = false;
            return true;
        } else if (method === "close") {
            root.forceIdle = true;
            return true;
        }
        return true;
    }

    readonly property var activePlayer: MediaService.primaryPlayer ?? null
    readonly property bool hasMedia: root.activePlayer !== null
        && ((root.activePlayer.trackTitle ?? "") !== "" || root.activePlayer.isPlaying)
    readonly property var latestNotification: NotificationService.popupList.length > 0
        ? NotificationService.popupList[NotificationService.popupList.length - 1]
        : null
    readonly property bool isRecording: false
    property int recordingElapsedSeconds: 0

    function stopRecording() {
        if (typeof AudioRecordingService !== "undefined" && AudioRecordingService?.isRecording)
            AudioRecordingService.stop();
        else if (typeof RecordingService !== "undefined" && RecordingService?.stop)
            RecordingService.stop();
    }

    // Service bindings
    readonly property var _recordingService: typeof RecordingService !== "undefined" ? RecordingService : null
    readonly property var _audioRecordingService: typeof AudioRecordingService !== "undefined" ? AudioRecordingService : null
    readonly property var _volumeService: typeof VolumeService !== "undefined" ? VolumeService : null
    readonly property var _brightnessService: typeof BrightnessService !== "undefined" ? BrightnessService : null
    readonly property var _keyboardLockService: typeof KeyboardLockService !== "undefined" ? KeyboardLockService : null

    onIsRecordingChanged: {
        if (!isRecording) recordingElapsedSeconds = 0
    }

    function formatRecordingTime(s) {
        return Math.floor(s / 60).toString().padStart(2, '0') + ":" + (s % 60).toString().padStart(2, '0')
    }

    Timer {
        interval: 1000
        repeat: true
        running: root.isRecording
        onTriggered: root.recordingElapsedSeconds++
    }

    property string engagedTimerKind: ""
    readonly property bool hasActiveTimer: false

    function timerIcon() {
        return "timer";
    }

    function timerValueText() {
        return "00:00";
    }

    function timerRunning() {
        return false;
    }

    function toggleActiveTimer() {
    }

    function resetActiveTimer() {
        root.engagedTimerKind = "";
    }

    property bool batteryAlertActive: false
    property string batteryAlertKind: "" 
    readonly property int batteryAlertDuration: 4000

    Timer {
        id: batteryAlertTimer
        interval: root.batteryAlertDuration
        repeat: false
        onTriggered: root.batteryAlertActive = false
    }

    Timer {
        id: mediaTrackChangeTimer
        interval: 3000
        repeat: false
    }

    Connections {
        target: root.activePlayer
        function onTrackTitleChanged() { mediaTrackChangeTimer.restart() }
        function onTrackArtistChanged() { mediaTrackChangeTimer.restart() }
    }

    function triggerBatteryAlert(kind) {
        root.batteryAlertKind = kind
        root.batteryAlertActive = true
        batteryAlertTimer.restart()
    }

    Connections {
        target: Battery
        function onIsCriticalAndNotChargingChanged() {
            if (Battery.isCriticalAndNotCharging) root.triggerBatteryAlert("critical")
        }
        function onIsLowAndNotChargingChanged() {
            if (Battery.isLowAndNotCharging && !Battery.isCriticalAndNotCharging) root.triggerBatteryAlert("low")
        }
        function onIsPluggedInChanged() {
            if (Battery.isPluggedIn) root.triggerBatteryAlert("charging")
        }
    }

    function batteryStatusText() {
        switch (root.batteryAlertKind) {
            case "critical": return Translation.tr("Critical Battery")
            case "charging": return Translation.tr("Charging")
            default:         return Translation.tr("Low Battery")
        }
    }

    function batteryIcon() {
        if (root.batteryAlertKind === "charging" || Battery.isCharging) return "battery_android_frame_bolt"
        const pct = Battery.percentage
        if (pct <= 0.1) return "battery_android_frame_alert"
        if (pct <= 0.2) return "battery_android_frame_1"
        if (pct <= 0.4) return "battery_android_frame_2"
        if (pct <= 0.6) return "battery_android_frame_3"
        if (pct <= 0.8) return "battery_android_frame_4"
        if (pct < 1)    return "battery_android_frame_5"
        return "battery_android_full"
    }

    function batteryAlertColor() {
        return root.batteryAlertKind === "charging" ? Appearance.m3colors.m3success : Appearance.colors.colError
    }

    readonly property var contentProviders: [
        { id: "notification", active: root.latestNotification !== null, component: notificationComponent, width: root.notificationWidth },
        { id: "battery",      active: root.batteryAlertActive,          component: batteryComponent,      width: root.batteryWidth },
        { id: "recording",    active: root.isRecording,                 component: recordingComponent,    width: root.recordingWidth },
        { id: "timer",        active: root.hasActiveTimer,              component: timerComponent,        width: root.timerWidth },
        { id: "osd",          active: GlobalStates.osdVolumeOpen,       component: osdComponent,          width: root.osdWidth },
        { id: "media",        active: root.hasMedia,                    component: mediaComponent,        width: root.mediaWidth },
        { id: "session",      active: GlobalStates.diSessionOpen,       component: sessionComponent,      width: root.sessionWidth },
    ]

    readonly property var alwaysWinIds: ["session", "notification", "battery", "osd"]

    readonly property var activeOthers: root.contentProviders.filter(p => !root.alwaysWinIds.includes(p.id) && p.active)

    readonly property var activeProvider: {
        const forcedTop = root.contentProviders.find(p => root.alwaysWinIds.includes(p.id) && p.active)
        if (forcedTop) return forcedTop
        if (root.manualFocusId !== "") {
            const forced = root.activeOthers.find(p => p.id === root.manualFocusId)
            if (forced) return forced
        }
        return root.activeOthers[0] ?? null
    }

    readonly property var badgeProviders: {
        if (root.alwaysWinIds.some(id => root.contentProviders.find(p => p.id === id)?.active)) return []
        return root.activeOthers.filter(p => p.id !== root.activeProvider?.id)
    }

    function iconForProviderId(id) {
        switch (id) {
            case "media":     return "music_note"
            case "recording": return "screen_record"
            case "timer":     return root.timerIcon()
            case "battery":   return root.batteryIcon()
            case "osd":
                switch (GlobalStates.osdIndicatorType) {
                    case "brightness": return "light_mode"
                    case "gamma":      return "wb_twilight"
                    default:           return "volume_up"
                }
            default: return "circle"
        }
    }

    readonly property string activeContentId: root.displayedProvider?.id ?? "idle"

    implicitHeight: root.pillHeight
    implicitWidth: (root.displayedProvider?.width ?? root.idleWidth)
        + (!root.vertical && root.badgeProviders.length > 0
            ? root.badgeProviders.length * (root.badgeSpacing + root.badgeSize)
            : 0)

    Behavior on implicitWidth {
        NumberAnimation {
            duration: 350
            easing.type: Easing.BezierSpline
            easing.bezierCurve: Appearance.animationCurves.expressiveDefaultSpatial
        }
    }

    Rectangle {
        id: pill
        anchors.left: parent.left
        width: root.displayedProvider?.width ?? root.idleWidth
        height: root.pillHeight
        color: root.isMaterial || (GlobalStates.barCenterOnly && Config.options.bar.cornerStyle === 0) ? "transparent" : Config.options.bar.followFrameColor
            ? Appearance.getColorFromName(Config.options.bar.frameColor)
            : Appearance.colors.colLayer0
        radius: height / 2
        clip: true
        visible: !root.vertical

        Behavior on width {
            NumberAnimation {
                duration: 350
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Appearance.animationCurves.expressiveDefaultSpatial
            }
        }

        HoverHandler {
            id: mediaHoverHandler
            enabled: root.activeContentId === "media"
        }

        WheelHandler {
            id: idleToggleWheelHandler
            target: pill
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            property bool coolingDown: false
            onWheel: (event) => {
                if (coolingDown) return
                coolingDown = true
                idleToggleDebounceTimer.restart()
                root.forceIdle = !root.forceIdle
            }
        }

        Timer {
            id: idleToggleDebounceTimer
            interval: 200
            onTriggered: idleToggleWheelHandler.coolingDown = false
        }

        Loader {
            id: contentLoader
            anchors.fill: parent
            sourceComponent: root.displayedProvider?.component ?? idleComponent
            active: !root.vertical

            onLoaded: {
                if (root.displayedProvider?.id === "session" && item) {
                    item.forceActiveFocus()
                }
            }
        }

        Component {
            id: idleComponent
            DiIdle { di: root }
        }

        Component {
            id: mediaComponent
            DiMedia { di: root }
        }

        Component {
            id: osdComponent
            DiOsd { di: root }
        }

        Component {
            id: notificationComponent
            DiNotifs { di: root }
        }

        Component {
            id: timerComponent
            DiTimers { di: root }
        }

        Component {
            id: sessionComponent
            DiSession { di: root }
        }

        Component {
            id: recordingComponent
            RowLayout {
                anchors {
                    fill: parent
                    leftMargin: root.isMaterial ? 4 : 8
                    rightMargin: 10
                }
                spacing: 6

                Item {
                    id: stopButton
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: 16
                    implicitHeight: 16

                    MaterialSymbol {
                        anchors.fill: parent
                        text: "stop_circle"
                        fill: 1
                        iconSize: root.isMaterial ? 26 : 16
                        color: Appearance.colors.colError
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.stopRecording()
                    }
                }

                Item { Layout.fillWidth: true }

                StyledText {
                    Layout.alignment: Qt.AlignVCenter
                    text: root.formatRecordingTime(root.recordingElapsedSeconds)
                    font.pixelSize: Appearance.font.pixelSize.small
                    font.features: { "tnum": 1 }
                    color: Appearance.colors.colOnLayer0
                }
            }
        }

        Component {
            id: batteryComponent
            RowLayout {
                anchors {
                    fill: parent
                    leftMargin: 10
                    rightMargin: 10
                }
                spacing: 6

                StyledText {
                    Layout.alignment: Qt.AlignVCenter
                    text: root.batteryStatusText()
                    font.pixelSize: Appearance.font.pixelSize.small
                    font.weight: Font.DemiBold
                    color: root.batteryAlertColor()
                }

                Item { Layout.fillWidth: true }

                MaterialSymbol {
                    Layout.alignment: Qt.AlignVCenter
                    text: root.batteryIcon()
                    fill: 1
                    iconSize: 16
                    color: root.batteryAlertColor()
                }

                StyledText {
                    Layout.alignment: Qt.AlignVCenter
                    text: `${Math.round(Battery.percentage * 100)}`
                    font.pixelSize: Appearance.font.pixelSize.small
                    font.features: { "tnum": 1 }
                    color: root.batteryAlertColor()
                }
            }
        }
    }

    Row {
        id: badgesRow
        visible: root.badgeProviders.length > 0 && !root.vertical
        anchors {
            left: pill.right
            leftMargin: root.badgeSpacing
            verticalCenter: pill.verticalCenter
        }
        spacing: root.badgeSpacing

        Repeater {
            model: root.badgeProviders
            delegate: Item {
                id: badgeItem
                required property var modelData
                width: root.badgeSize
                height: root.badgeSize

                MaterialShapeWrappedMaterialSymbol {
                    anchors.fill: parent
                    wrappedShape: MaterialShape.Shape.Cookie7Sided
                    color: root.isMaterial ? Appearance.colors.colPrimary : Appearance.colors.colLayer0
                    colSymbol: root.isMaterial ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer0
                    text: root.iconForProviderId(badgeItem.modelData.id)
                    iconSize: 16
                    fill: 1
                    padding: 4
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.manualFocusId = badgeItem.modelData.id
                }
            }
        }
    }
}