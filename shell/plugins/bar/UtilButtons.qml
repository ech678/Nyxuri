import qs.services
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower
import qs.commons
import qs.ui

Item {
    id: root
    property color contentColor: Appearance.colors.colOnLayer2
    property bool contentColorOverridden: false
    property bool vertical: Config.options.bar.vertical
    property bool isMaterial: PersonalizationConfig.barIsMaterial

    implicitWidth: isMaterial && !root.vertical ? flow.implicitWidth : root.vertical ? Appearance.sizes.verticalBarWidth - 14 : flow.implicitWidth + 4
    implicitHeight: isMaterial && root.vertical ? flow.implicitHeight : isMaterial ? 32 : root.vertical ? flow.implicitHeight + 4 : Appearance.sizes.barHeight

    Flow {
        id: flow
        anchors.centerIn: parent
        flow: root.vertical ? Flow.TopToBottom : Flow.LeftToRight
        spacing: isMaterial ? 2 : 4

        Loader {
            active: Config.options.bar.m3.utilButtons.showScreenSnip
            visible: active
            sourceComponent: isMaterial ? screenSnipM3 : legacyScreenSnip
        }

        Component {
            id: screenSnipM3
            UtilButton {
                toolTipText: Translation.tr("Take screenshot")
                iconText: "screenshot_region"
                onClicked: GlobalActions.runById("screenshot", "")
            }
        }

        Component {
            id: legacyScreenSnip
            CircleUtilButton {
                onClicked: GlobalActions.runById("screenshot", "")
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 1
                    text: "screenshot_region"
                    iconSize: Appearance.font.pixelSize.large
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: Config.options.bar.m3.utilButtons.showColorPicker
            visible: active
            sourceComponent: isMaterial ? colorPickerM3 : legacyColorPicker
        }
        Component {
            id: colorPickerM3
            UtilButton {
                toolTipText: Translation.tr("Pick a color")
                iconText: "colorize"
                onClicked: GlobalActions.runById("color-picker", "")
            }
        }
        Component {
            id: legacyColorPicker
            CircleUtilButton {
                onClicked: GlobalActions.runById("color-picker", "")
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 1
                    text: "colorize"
                    iconSize: Appearance.font.pixelSize.large
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: Config.options.bar.m3.utilButtons.showKeyboardToggle
            visible: active
            sourceComponent: isMaterial ? keyboardM3 : legacyKeyboard
        }
        Component {
            id: keyboardM3
            UtilButton {
                toolTipText: Translation.tr("On-screen keyboard")
                iconText: "keyboard"
                onClicked: GlobalStates.oskOpen = !GlobalStates.oskOpen
            }
        }
        Component {
            id: legacyKeyboard
            CircleUtilButton {
                onClicked: GlobalStates.oskOpen = !GlobalStates.oskOpen
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 0
                    text: "keyboard"
                    iconSize: Appearance.font.pixelSize.large
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: Config.options.bar.m3.utilButtons.showWallpaperToggle
            visible: active
            sourceComponent: isMaterial ? wallpaperM3 : legacyWallpaper
        }
        Component {
            id: wallpaperM3
            UtilButton {
                toolTipText: Translation.tr("Choose wallpaper")
                iconText: "imagesmode"
                onClicked: GlobalStates.wallpaperSelectorOpen = !GlobalStates.wallpaperSelectorOpen
            }
        }
        Component {
            id: legacyWallpaper
            CircleUtilButton {
                onClicked: GlobalStates.wallpaperSelectorOpen = !GlobalStates.wallpaperSelectorOpen
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 0
                    text: "imagesmode"
                    iconSize: Appearance.font.pixelSize.large
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: Config.options.bar.m3.utilButtons.showMicToggle
            visible: active
            sourceComponent: isMaterial ? micM3 : legacyMic
        }
        Component {
            id: micM3
            UtilButton {
                toolTipText: Pipewire.defaultAudioSource?.audio?.muted ? Translation.tr("Unmute microphone") : Translation.tr("Mute microphone")
                iconText: Pipewire.defaultAudioSource?.audio?.muted ? "mic_off" : "mic"
                onClicked: GlobalActions.runById("toggle-mic-mute", "")
            }
        }
        Component {
            id: legacyMic
            CircleUtilButton {
                onClicked: GlobalActions.runById("toggle-mic-mute", "")
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 0
                    text: Pipewire.defaultAudioSource?.audio?.muted ? "mic_off" : "mic"
                    iconSize: Appearance.font.pixelSize.large
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: Config.options.bar.m3.utilButtons.showDarkModeToggle
            visible: active
            sourceComponent: isMaterial ? darkModeM3 : legacyDarkMode
        }
        Component {
            id: darkModeM3
            UtilButton {
                toolTipText: Appearance.m3colors.darkmode ? Translation.tr("Use light mode") : Translation.tr("Use dark mode")
                iconText: Appearance.m3colors.darkmode ? "light_mode" : "dark_mode"
                onClicked: ThemeService.toggleThemeMode()
            }
        }
        Component {
            id: legacyDarkMode
            CircleUtilButton {
                onClicked: ThemeService.toggleThemeMode()
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 0
                    text: Appearance.m3colors.darkmode ? "light_mode" : "dark_mode"
                    iconSize: Appearance.font.pixelSize.large
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: Config.options.bar.m3.utilButtons.showPerformanceProfileToggle
            visible: active
            sourceComponent: isMaterial ? perfM3 : legacyPerf
        }
        Component {
            id: perfM3
            UtilButton {
                toolTipText: Translation.tr("Change performance profile")
                iconText: switch (PowerProfiles.profile) {
                case PowerProfile.PowerSaver:
                    return "energy_savings_leaf";
                case PowerProfile.Balanced:
                    return "airwave";
                case PowerProfile.Performance:
                    return "local_fire_department";
                }
                onClicked: e => {
                    if (PowerProfiles.hasPerformanceProfile) {
                        switch (PowerProfiles.profile) {
                        case PowerProfile.PowerSaver:
                            PowerProfiles.profile = PowerProfile.Balanced;
                            break;
                        case PowerProfile.Balanced:
                            PowerProfiles.profile = PowerProfile.Performance;
                            break;
                        case PowerProfile.Performance:
                            PowerProfiles.profile = PowerProfile.PowerSaver;
                            break;
                        }
                    } else {
                        PowerProfiles.profile = PowerProfiles.profile == PowerProfile.Balanced ? PowerProfile.PowerSaver : PowerProfile.Balanced;
                    }
                }
            }
        }
        Component {
            id: legacyPerf
            CircleUtilButton {
                onClicked: e => {
                    if (PowerProfiles.hasPerformanceProfile) {
                        switch (PowerProfiles.profile) {
                        case PowerProfile.PowerSaver:
                            PowerProfiles.profile = PowerProfile.Balanced;
                            break;
                        case PowerProfile.Balanced:
                            PowerProfiles.profile = PowerProfile.Performance;
                            break;
                        case PowerProfile.Performance:
                            PowerProfiles.profile = PowerProfile.PowerSaver;
                            break;
                        }
                    } else {
                        PowerProfiles.profile = PowerProfiles.profile == PowerProfile.Balanced ? PowerProfile.PowerSaver : PowerProfile.Balanced;
                    }
                }
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 0
                    text: switch (PowerProfiles.profile) {
                    case PowerProfile.PowerSaver:
                        return "energy_savings_leaf";
                    case PowerProfile.Balanced:
                        return "airwave";
                    case PowerProfile.Performance:
                        return "local_fire_department";
                    }
                    iconSize: Appearance.font.pixelSize.large
                    color: root.contentColor
                }
            }
        }
    }
}
