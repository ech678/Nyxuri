pragma ComponentBehavior: Bound
import QtQuick
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

Item {
    id: root

    readonly property var player: MediaService.active
    readonly property string title: player && player.trackTitle ? player.trackTitle : I18n.tr("No media")
    readonly property real batteryPercent: Math.max(0, Math.min(100, PowerService.percentage * 100))
    readonly property string networkIcon: {
        if (!NetworkService.connected)
            return "wifi_off";
        if (NetworkService.ethernetConnected)
            return "settings_ethernet";
        const strength = Number(NetworkService.signalStrength || 0);
        return strength >= 80 ? "signal_wifi_4_bar" : strength >= 60 ? "network_wifi_3_bar" : strength >= 40
                                                                       ? "network_wifi_2_bar" : strength
                                                                         >= 20 ? "network_wifi_1_bar" :
                                                                                 "signal_wifi_0_bar";
    }

    implicitWidth: statusRow.width
    implicitHeight: 40

    Row {
        id: statusRow
        spacing: 8
        height: 40

        Row {
            spacing: 2
            MediaButton {
                iconName: "skip_previous"
                accessibleName: I18n.tr("Previous track")
                enabled: root.player !== null && root.player.canGoPrevious
                onClicked: root.player.previous()
            }
            MediaButton {
                iconName: root.player && root.player.isPlaying ? "pause" : "play_arrow"
                accessibleName: root.player && root.player.isPlaying ? I18n.tr("Pause") : I18n.tr("Play")
                enabled: root.player !== null && root.player.canTogglePlaying
                onClicked: root.player.togglePlaying()
            }
            MediaButton {
                iconName: "skip_next"
                accessibleName: I18n.tr("Next track")
                enabled: root.player !== null && root.player.canGoNext
                onClicked: root.player.next()
            }
        }

        Item {
            id: titleViewport
            width: Math.max(40, Math.min(220, root.parent.width - 530))
            height: 40
            clip: true
            readonly property real overflow: Math.max(0, titleText.implicitWidth - width)
            onOverflowChanged: restartScroll()
            function restartScroll() {
                titleScroll.stop();
                titleText.x = 0;
                if (overflow > 0 && root.visible)
                    titleScroll.start();
            }
            Text {
                id: titleText
                anchors.verticalCenter: parent.verticalCenter
                text: root.title
                font.family: Fonts.ui
                font.pixelSize: 16
                color: "#F5F7FA"
                onTextChanged: Qt.callLater(titleViewport.restartScroll)
            }
            Connections {
                target: root
                function onVisibleChanged() {
                    titleViewport.restartScroll();
                }
            }
            SequentialAnimation {
                id: titleScroll
                loops: Animation.Infinite
                PauseAnimation {
                    duration: 1800
                }
                NumberAnimation {
                    target: titleText
                    property: "x"
                    to: -titleViewport.overflow
                    duration: Math.max(1800, titleViewport.overflow * 35)
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: [0.25, 0.1, 0.25, 1, 1, 1]
                }
                PauseAnimation {
                    duration: 1800
                }
                NumberAnimation {
                    target: titleText
                    property: "x"
                    to: 0
                    duration: Math.max(1800, titleViewport.overflow * 35)
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: [0.25, 0.1, 0.25, 1, 1, 1]
                }
            }
        }

        Row {
            spacing: 4
            StatusIcon {
                symbol: WeatherService.hasValidData ? WeatherService.currentIconName || "cloud" : "cloud_off"
                description: WeatherService.hasValidData ? WeatherService.currentWeatherText : I18n.tr(
                                                               "Weather unavailable")
            }
            Text {
                height: 40
                verticalAlignment: Text.AlignVCenter
                text: WeatherService.hasValidData ? Math.round(UiPreferences.weatherTemperature(
                                                                   WeatherService.currentTemperatureC))
                                                    + UiPreferences.weatherTemperatureSymbol() : "—"
                font.family: Fonts.numeric
                font.pixelSize: 16
                color: "#F5F7FA"
            }
        }

        StatusIcon {
            symbol: root.networkIcon
            active: NetworkService.connected
            description: !NetworkService.available ? I18n.tr("Network unavailable") :
                                                     NetworkService.connected
                                                     ? NetworkService.activeConnection || I18n.tr(
                                                           "Connected") : I18n.tr("Disconnected")
        }
        StatusIcon {
            visible: KeyboardLockService.available
            symbol: "keyboard_capslock"
            active: KeyboardLockService.available && KeyboardLockService.capsLock
            description: active ? I18n.tr("Caps Lock on") : I18n.tr("Caps Lock off")
        }
        StatusIcon {
            visible: KeyboardLockService.available
            symbol: "pin"
            active: KeyboardLockService.available && KeyboardLockService.numLock
            description: active ? I18n.tr("Num Lock on") : I18n.tr("Num Lock off")
        }
        Row {
            visible: PowerService.present
            spacing: 4
            StatusIcon {
                symbol: PowerService.charging ? "battery_android_bolt" : !isFinite(root.batteryPercent)
                                                ? "battery_android_question" : root.batteryPercent >= 95
                                                  ? "battery_android_full" : "battery_android_" + Math.max(0,
                                                                                                           Math.min(6,
                                                                                                                    Math.floor(
                                                                                                                        root.batteryPercent
                                                                                                                        / 15)))
                description: PowerService.full ? I18n.tr("Fully charged") : PowerService.charging ? I18n.tr(
                                                                                                        "Charging") :
                                                                                                    PowerService.powerConnected
                                                                                                    ? I18n.tr(
                                                                                                          "Plugged in") :
                                                                                                      I18n.tr("On battery")
            }
            Text {
                height: 40
                verticalAlignment: Text.AlignVCenter
                text: isFinite(root.batteryPercent) ? Math.round(root.batteryPercent) + "%" : "—"
                font.family: Fonts.numeric
                font.pixelSize: 16
                color: "#F5F7FA"
            }
        }
    }

    component MediaButton: IconButton {
        controlSize: 40
        iconSize: 24
        iconColor: "#F5F7FA"
        normalContainerColor: "transparent"
        normalHoverStateLayerColor: "#20FFFFFF"
        normalPressedStateLayerColor: "#30FFFFFF"
        opacity: enabled ? 1 : 0.35
        showTooltip: false
        focusPolicy: Qt.NoFocus
    }
    component StatusIcon: Item {
        id: status
        required property string symbol
        required property string description
        property bool active: true
        width: 28
        height: 40
        Accessible.role: Accessible.StaticText
        Accessible.name: description
        MaterialSymbol {
            anchors.centerIn: parent
            text: status.symbol
            iconSize: 24
            color: status.active ? "#F5F7FA" : "#80F5F7FA"
        }
    }
}
