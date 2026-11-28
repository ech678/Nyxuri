import qs.services
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower
import qs.commons
import qs.ui
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults
import "BarStyle.js" as BarStyle

Item {
    id: root
    property var widgetEntry: null
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    property color contentColor: Appearance.colors.colOnLayer2
    property bool contentColorOverridden: false
    property bool vertical: root.barAxes.position === "left" || root.barAxes.position === "right"
    property bool isMaterial: BarStyle.isTinted(root.barAxes)
    // D4b: the seven slots are entry axes (utilButtons == quickSettings
    // share this component and one axes table).
    readonly property string widgetId: root.widgetEntry && root.widgetEntry.widgetId === "quickSettings" ? "quickSettings" : "utilButtons"
    readonly property bool showScreenSnip: BarWidgetDefaults.option(root.widgetId, root.widgetEntry, "screenSnip")
    readonly property bool showColorPicker: BarWidgetDefaults.option(root.widgetId, root.widgetEntry, "colorPicker")
    readonly property bool showKeyboardToggle: BarWidgetDefaults.option(root.widgetId, root.widgetEntry, "keyboardToggle")
    readonly property bool showMicToggle: BarWidgetDefaults.option(root.widgetId, root.widgetEntry, "micToggle")
    readonly property bool showWallpaperToggle: BarWidgetDefaults.option(root.widgetId, root.widgetEntry, "wallpaperToggle")
    readonly property bool showDarkModeToggle: BarWidgetDefaults.option(root.widgetId, root.widgetEntry, "darkModeToggle")
    readonly property bool showPerformanceProfile: BarWidgetDefaults.option(root.widgetId, root.widgetEntry, "performanceProfile")

    implicitWidth: isMaterial && !root.vertical ? flow.implicitWidth : root.vertical ? PersonalizationConfig.resolvedVerticalBarWidth(root.barAxes) - 14 : flow.implicitWidth + 4
    implicitHeight: isMaterial && root.vertical ? flow.implicitHeight : isMaterial ? 32 : root.vertical ? flow.implicitHeight + 4 : PersonalizationConfig.resolvedBarHeight(root.barAxes)

    Flow {
        id: flow
        anchors.centerIn: parent
        flow: root.vertical ? Flow.TopToBottom : Flow.LeftToRight
        spacing: isMaterial ? 2 : 4

        Loader {
            active: root.showScreenSnip
            visible: active
            sourceComponent: isMaterial ? screenSnipM3 : legacyScreenSnip
        }

        Component {
            id: screenSnipM3
            UtilButton {
                widgetBar: root.widgetBar
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
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(root.widgetBar)
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: root.showColorPicker
            visible: active
            sourceComponent: isMaterial ? colorPickerM3 : legacyColorPicker
        }
        Component {
            id: colorPickerM3
            UtilButton {
                widgetBar: root.widgetBar
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
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(root.widgetBar)
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: root.showKeyboardToggle
            visible: active
            sourceComponent: isMaterial ? keyboardM3 : legacyKeyboard
        }
        Component {
            id: keyboardM3
            UtilButton {
                widgetBar: root.widgetBar
                toolTipText: Translation.tr("On-screen keyboard")
                iconText: "keyboard"
                onClicked: GlobalActions.runById("toggle-osk", "")
            }
        }
        Component {
            id: legacyKeyboard
            CircleUtilButton {
                onClicked: GlobalActions.runById("toggle-osk", "")
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 0
                    text: "keyboard"
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(root.widgetBar)
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: root.showWallpaperToggle
            visible: active
            sourceComponent: isMaterial ? wallpaperM3 : legacyWallpaper
        }
        Component {
            id: wallpaperM3
            UtilButton {
                widgetBar: root.widgetBar
                toolTipText: Translation.tr("Choose wallpaper")
                iconText: "imagesmode"
                onClicked: ActionGateway.requestSettingsOpen("wallpaper")
            }
        }
        Component {
            id: legacyWallpaper
            CircleUtilButton {
                onClicked: ActionGateway.requestSettingsOpen("wallpaper")
                MaterialSymbol {
                    horizontalAlignment: Qt.AlignHCenter
                    fill: 0
                    text: "imagesmode"
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(root.widgetBar)
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: root.showMicToggle
            visible: active
            sourceComponent: isMaterial ? micM3 : legacyMic
        }
        Component {
            id: micM3
            UtilButton {
                widgetBar: root.widgetBar
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
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(root.widgetBar)
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: root.showDarkModeToggle
            visible: active
            sourceComponent: isMaterial ? darkModeM3 : legacyDarkMode
        }
        Component {
            id: darkModeM3
            UtilButton {
                widgetBar: root.widgetBar
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
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(root.widgetBar)
                    color: root.contentColor
                }
            }
        }

        Loader {
            active: root.showPerformanceProfile
            visible: active
            sourceComponent: isMaterial ? perfM3 : legacyPerf
        }
        Component {
            id: perfM3
            UtilButton {
                widgetBar: root.widgetBar
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
                    iconSize: NexusStyle.font.bodyLarge * BarScale.iconFor(root.widgetBar)
                    color: root.contentColor
                }
            }
        }
    }
}
