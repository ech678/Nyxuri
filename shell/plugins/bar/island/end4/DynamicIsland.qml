// Fork & Trim: end4-pC modules/ii/bar/DynamicIsland.qml (GPL-3, see
// shell/LICENSE appendix end-4-dots-hyprland-GPL-3.0.txt). B3-1 copies the
// capsule body and the idle/media faces; B3-2 wires DiNotifs, DiOsd,
// RecordingService / AudioRecordingService, and battery/timer skeletons.
// Four trim classes only: (1) upstream singletons -> tree services,
// (2) colors/sizes -> Appearance/Sizes, (3) copy -> I18n, (4) dead upstream
// paths dropped.
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.Mpris
import qs.services
import qs.commons
import qs.ui
import "../tools"

Item {
    id: root
    property bool mirrored: false

    // end4 scale is absolute: the capsule keeps its 32px height instead of
    // riding the tree-wide 0.85 Sizes scale.
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
    readonly property real recordingWidth: 150
    readonly property real badgeSize: 32
    readonly property real badgeSpacing: 6
    // B3-1 island side only: the bar shell keeps its own surface until B4
    // wires the full cornerStyle system.
    readonly property bool isMaterial: false
    property bool vertical: PersonalizationConfig.barPosition === "left" || PersonalizationConfig.barPosition === "right"

    property string manualFocusId: ""

    property bool forceIdle: false

    readonly property var displayedProvider: root.forceIdle ? null : root.activeProvider

    onActiveProviderChanged: {
        if (root.activeProvider && root.alwaysWinIds.includes(root.activeProvider.id)) {
            root.forceIdle = false;
        }
    }

    readonly property MprisPlayer activePlayer: MediaService.active
    readonly property bool hasMedia: root.activePlayer !== null && ((root.activePlayer.trackTitle ?? "") !== "" || root.activePlayer.isPlaying)
    readonly property var latestNotification: NotificationService.popupList.length > 0 ? NotificationService.popupList[NotificationService.popupList.length - 1] : null

    // Recording face (B3-2: RecordingService & AudioRecordingService bridge).
    readonly property bool isRecording: (RecordingService.isRecording || RecordingService.state === "paused") || AudioRecordingService.isRecording
    readonly property int recordingElapsedSeconds: Math.floor((AudioRecordingService.isRecording ? AudioRecordingService.elapsedMs : RecordingService.elapsedMs) / 1000)

    function formatRecordingTime(s) {
        return Math.floor(s / 60).toString().padStart(2, '0') + ":" + (s % 60).toString().padStart(2, '0');
    }

    function stopRecording() {
        if (AudioRecordingService.isRecording)
            AudioRecordingService.stop();
        else
            RecordingService.stop();
    }

    // OSD face (B3-2: VolumeService, BrightnessService, KeyboardLockService).
    readonly property bool osdActive: osdTimeoutTimer.running
    property string osdType: "volume"

    Timer {
        id: osdTimeoutTimer
        interval: 1800
        repeat: false
    }

    function triggerOsd(type) {
        root.osdType = type;
        osdTimeoutTimer.restart();
    }

    function osdValueText() {
        switch (root.osdType) {
        case "brightness":
            return `${Math.round(BrightnessService.brightnessValue * 100)}`;
        case "mic":
            return `${Math.round((VolumeService.sourceVolume ?? 0) * 100)}`;
        case "capslock":
            return KeyboardLockService.capsLock ? "ON" : "OFF";
        case "numlock":
            return KeyboardLockService.numLock ? "ON" : "OFF";
        default:
            return `${Math.round((VolumeService.sinkVolume ?? 0) * 100)}`;
        }
    }

    property real lastSinkVolume: VolumeService.sinkVolume
    property bool lastSinkMuted: VolumeService.sinkMuted
    property bool sinkTrackingInitialized: false

    Connections {
        target: VolumeService
        function onSinkVolumeChanged() {
            if (!root.sinkTrackingInitialized) {
                root.sinkTrackingInitialized = true;
                root.lastSinkVolume = VolumeService.sinkVolume;
                return;
            }
            if (Math.abs(VolumeService.sinkVolume - root.lastSinkVolume) > 0.0001) {
                root.lastSinkVolume = VolumeService.sinkVolume;
                root.triggerOsd("volume");
            }
        }
        function onSinkMutedChanged() {
            if (!root.sinkTrackingInitialized) {
                root.sinkTrackingInitialized = true;
                root.lastSinkMuted = VolumeService.sinkMuted;
                return;
            }
            if (VolumeService.sinkMuted !== root.lastSinkMuted) {
                root.lastSinkMuted = VolumeService.sinkMuted;
                root.triggerOsd("volume");
            }
        }
        function onSourceVolumeChanged() {
            root.triggerOsd("mic");
        }
        function onSourceMutedChanged() {
            root.triggerOsd("mic");
        }
    }

    Connections {
        target: BrightnessService
        function onBrightnessChanged() {
            root.triggerOsd("brightness");
        }
    }

    property var previousCapsLock: null
    property var previousNumLock: null
    property bool locksInitialized: false

    Connections {
        target: KeyboardLockService
        function onLockStateChanged() {
            const caps = KeyboardLockService.capsLock;
            const num = KeyboardLockService.numLock;
            if (root.locksInitialized) {
                if (caps !== root.previousCapsLock && PersonalizationConfig.islandCapsLockOsd) {
                    root.triggerOsd("capslock");
                }
                if (num !== root.previousNumLock && PersonalizationConfig.islandNumLockOsd) {
                    root.triggerOsd("numlock");
                }
            }
            root.previousCapsLock = caps;
            root.previousNumLock = num;
            root.locksInitialized = true;
        }
    }

    // D8: battery and timer faces stay empty skeletons until BatteryService
    // and the timer domain exist.
    property string engagedTimerKind: ""
    readonly property bool hasActiveTimer: false
    property bool batteryAlertActive: false
    property string batteryAlertKind: ""

    function timerIcon() {
        return "timer";
    }

    function timerValueText() {
        return "";
    }

    function timerRunning() {
        return false;
    }

    function toggleActiveTimer() {
    }

    function resetActiveTimer() {
    }

    function batteryStatusText() {
        return "";
    }

    function batteryIcon() {
        return "battery_android_frame_full";
    }

    function batteryAlertColor() {
        return Appearance.colors.colError;
    }

    Timer {
        id: mediaTrackChangeTimer
        interval: 3000
        repeat: false
    }

    Connections {
        target: root.activePlayer
        function onTrackTitleChanged() {
            mediaTrackChangeTimer.restart();
        }
        function onTrackArtistChanged() {
            mediaTrackChangeTimer.restart();
        }
    }

    // D8: session is not ported — the power-menu unit owns it.
    // Provider precedence: osd -> notification -> battery in alwaysWinIds;
    // recording -> timer -> media in activeOthers.
    readonly property var contentProviders: [
        {
            id: "osd",
            active: root.osdActive,
            component: osdComponent,
            width: root.osdWidth
        },
        {
            id: "notification",
            active: root.latestNotification !== null,
            component: notificationComponent,
            width: root.notificationWidth
        },
        {
            id: "battery",
            active: root.batteryAlertActive,
            component: batteryComponent,
            width: root.batteryWidth
        },
        {
            id: "recording",
            active: root.isRecording,
            component: recordingComponent,
            width: root.recordingWidth
        },
        {
            id: "timer",
            active: root.hasActiveTimer,
            component: timerComponent,
            width: root.timerWidth
        },
        {
            id: "media",
            active: root.hasMedia,
            component: mediaComponent,
            width: root.mediaWidth
        },
    ]

    readonly property var alwaysWinIds: ["osd", "notification", "battery"]

    readonly property var activeOthers: root.contentProviders.filter(p => !root.alwaysWinIds.includes(p.id) && p.active)

    readonly property var activeProvider: {
        const forcedTop = root.contentProviders.find(p => root.alwaysWinIds.includes(p.id) && p.active);
        if (forcedTop)
            return forcedTop;
        if (root.manualFocusId !== "") {
            const forced = root.activeOthers.find(p => p.id === root.manualFocusId);
            if (forced)
                return forced;
        }
        return root.activeOthers[0] ?? null;
    }

    readonly property var badgeProviders: {
        if (root.alwaysWinIds.some(id => root.contentProviders.find(p => p.id === id)?.active))
            return [];
        return root.activeOthers.filter(p => p.id !== root.activeProvider?.id);
    }

    function iconForProviderId(id) {
        switch (id) {
        case "media":
            return "music_note";
        case "recording":
            return AudioRecordingService.isRecording ? "mic" : "screen_record";
        case "notification":
            return "notifications";
        case "timer":
            return root.timerIcon();
        case "battery":
            return root.batteryIcon();
        case "osd":
            switch (root.osdType) {
            case "brightness":
                return "light_mode";
            case "mic":
                return VolumeService.sourceMuted ? "mic_off" : "mic";
            case "capslock":
                return "keyboard_capslock";
            case "numlock":
                return "pin";
            default:
                return VolumeService.sinkMuted ? "volume_off" : VolumeService.isHeadphone ? "headphones" : "volume_up";
            }
        default:
            return "circle";
        }
    }

    readonly property string activeContentId: root.displayedProvider?.id ?? "idle"

    implicitHeight: root.pillHeight
    implicitWidth: (root.displayedProvider?.width ?? root.idleWidth) + (!root.vertical && root.badgeProviders.length > 0 ? root.badgeProviders.length * (root.badgeSpacing + root.badgeSize) : 0)

    // The capsule animates its own width; the host widget follows so the bar
    // grid cell grows with it instead of clipping the transition.
    width: root.implicitWidth
    height: root.implicitHeight

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
        color: root.isMaterial ? "transparent" : Appearance.colors.colLayer0
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
            onWheel: event => {
                if (coolingDown)
                    return;
                coolingDown = true;
                idleToggleDebounceTimer.restart();
                root.forceIdle = !root.forceIdle;
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
        }

        Component {
            id: idleComponent
            DiIdle {
                di: root
            }
        }

        Component {
            id: mediaComponent
            DiMedia {
                di: root
            }
        }

        Component {
            id: osdComponent
            DiOsd {
                di: root
            }
        }

        Component {
            id: notificationComponent
            DiNotifs {
                di: root
            }
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

                Item {
                    Layout.fillWidth: true
                }

                StyledText {
                    Layout.alignment: Qt.AlignVCenter
                    text: root.formatRecordingTime(root.recordingElapsedSeconds)
                    font.pixelSize: Appearance.font.pixelSize.small
                    font.features: {
                        "tnum": 1
                    }
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

                Item {
                    Layout.fillWidth: true
                }

                MaterialSymbol {
                    Layout.alignment: Qt.AlignVCenter
                    text: root.batteryIcon()
                    fill: 1
                    iconSize: 16
                    color: root.batteryAlertColor()
                }
            }
        }

        Component {
            id: timerComponent
            RowLayout {
                anchors {
                    fill: parent
                    leftMargin: root.isMaterial ? 4 : 8
                    rightMargin: 10
                }
                spacing: 6

                StyledText {
                    Layout.alignment: Qt.AlignVCenter
                    text: root.timerValueText()
                    font.pixelSize: Appearance.font.pixelSize.small
                    font.features: {
                        "tnum": 1
                    }
                    color: Appearance.colors.colOnLayer0
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
                    wrappedShape: MaterialShapeCanvas.Shape.Cookie7Sided
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
