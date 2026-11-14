pragma Singleton

import QtQuick
import Quickshell
import qs.services

// Bridge singleton adapting upstream iNiR/end4 Config.options queries to PersonalizationConfig
Singleton {
    id: root

    readonly property QtObject options: QtObject {
        id: optionsRoot

        readonly property QtObject interactions: QtObject {
            readonly property QtObject deadPixelWorkaround: QtObject {
                readonly property bool enable: false
            }
        }

        readonly property QtObject battery: QtObject {
            readonly property int low: 20
            readonly property int critical: 10
        }

        readonly property QtObject resources: QtObject {
            readonly property int updateInterval: 1000
            readonly property int historyLength: 60
            readonly property int autoStopDelay: 15000
            readonly property bool monitorGpu: true
        }

        readonly property QtObject profile: QtObject {
            readonly property string avatarPath: ""
            readonly property string avatarPicture: ""
        }

        readonly property QtObject bar: QtObject {
            id: barOptions

            readonly property bool bottom: PersonalizationConfig.barPosition === "bottom"
            readonly property bool vertical: PersonalizationConfig.barPosition === "left" || PersonalizationConfig.barPosition === "right"
            readonly property bool showBackground: PersonalizationConfig.barShowBackground ?? true
            readonly property int cornerStyle: PersonalizationConfig.barCornerStyle ?? 3
            readonly property string borderless: PersonalizationConfig.barBorderless ?? "separated"
            readonly property bool showScrollHints: true
            readonly property bool followFrameColor: false
            readonly property string frameColor: ""
            readonly property var screenList: []
            readonly property string groupColor: PersonalizationConfig.barGroupColor
            readonly property alias layouts: m3Options.layouts

            readonly property QtObject divider: QtObject {
                readonly property string style: PersonalizationConfig.barDividerStyle ?? "rect"
                readonly property int spacing: PersonalizationConfig.barDividerSpacing ?? 4
            }

            readonly property QtObject autoHide: QtObject {
                readonly property bool enable: false
                readonly property bool pushWindows: false
                readonly property int hoverRegionWidth: 2
                readonly property QtObject showWhenPressingSuper: QtObject {
                    readonly property bool enable: false
                    readonly property int delay: 100
                }
            }

            readonly property QtObject m3: QtObject {
                id: m3Options
                readonly property bool showBackground: PersonalizationConfig.barShowBackground ?? true
                readonly property int cornerStyle: PersonalizationConfig.barCornerStyle ?? 3
                readonly property string borderless: PersonalizationConfig.barBorderless ?? "separated"
                readonly property real gapsOut: 5

                readonly property QtObject layouts: QtObject {
                    readonly property var leftLayout: PersonalizationConfig.barLayoutLeft
                    readonly property var middleLayout: PersonalizationConfig.barLayoutMiddle
                    readonly property var rightLayout: PersonalizationConfig.barLayoutRight
                }

                // iNiR reads these straight off the object (no optional
                // chaining), so a missing key is a TypeError on every binding
                // evaluation, not a silent default.
                readonly property bool verbose: true

                readonly property QtObject divider: QtObject {
                    readonly property string style: PersonalizationConfig.barDividerStyle ?? "rect"
                    readonly property int spacing: 4
                }

                readonly property QtObject clock: QtObject {
                    readonly property string timeFontFamily: ""
                    readonly property int timePixelSize: 0
                    readonly property string dateFontFamily: ""
                    readonly property int datePixelSize: 0
                }

                readonly property QtObject indicators: QtObject {
                    readonly property QtObject notifications: QtObject {
                        readonly property bool showUnreadCount: true
                    }
                }

                readonly property QtObject resources: QtObject {
                    readonly property string style: "outline"
                    readonly property bool showValue: false
                    readonly property bool alwaysShowRam: true
                    readonly property bool alwaysShowCpu: true
                    readonly property bool alwaysShowCpuTemp: false
                    readonly property bool alwaysShowDisk: false
                    readonly property bool alwaysShowSwap: false
                    readonly property int memoryWarningThreshold: 90
                    readonly property int cpuWarningThreshold: 95
                    readonly property int swapWarningThreshold: 90
                }

                readonly property QtObject tooltips: QtObject {
                    readonly property bool clickToShow: false
                }

                // B9.1 tray surface: SysTrayItem tints glyphs through this
                // bridge (it used to read a property that never existed, so the
                // `?? true` fallback silently forced tinting on).
                readonly property QtObject tray: QtObject {
                    readonly property bool monochromeIcons: PersonalizationConfig.barTrayMonochromeIcons
                    readonly property bool filterPassive: PersonalizationConfig.barTrayFilterPassive
                }

                readonly property QtObject media: QtObject {
                    readonly property string preferredPlayer: ""
                    readonly property int minWidth: 160
                    readonly property int maxWidth: 300
                    readonly property bool alwaysVisible: false
                    readonly property int updateInterval: 1000
                    readonly property bool onlyTitle: false
                }

                readonly property QtObject utilButtons: QtObject {
                    readonly property bool showScreenSnip: true
                    readonly property bool showColorPicker: true
                    readonly property bool showScreenRecord: true
                    readonly property bool showKeyboardToggle: false
                    readonly property bool showWallpaperToggle: false
                    readonly property bool showMicToggle: false
                    readonly property bool showDarkModeToggle: true
                    readonly property bool showPerformanceProfileToggle: false
                }

                readonly property QtObject workspaces: QtObject {
                    readonly property bool showAppIcons: PersonalizationConfig.barShowAppIcons
                    readonly property bool alwaysShowNumbers: PersonalizationConfig.barAlwaysShowNumbers
                    readonly property bool useNerdFont: false
                    readonly property bool monochromeIcons: false
                    readonly property string indicatorStyle: PersonalizationConfig.barWorkspaceIndicatorStyle
                    readonly property var numberMap: []
                }

                readonly property QtObject keyboardIndicators: QtObject {
                    readonly property bool showPopup: PersonalizationConfig.keyboardShowPopup
                    readonly property bool showPanel: PersonalizationConfig.keyboardShowPanel

                    readonly property QtObject popup: QtObject {
                        readonly property bool layout: PersonalizationConfig.keyboardPopupLayout
                        readonly property bool caps: PersonalizationConfig.keyboardPopupCaps
                        readonly property bool num: PersonalizationConfig.keyboardPopupNum
                    }

                    readonly property QtObject panel: QtObject {
                        readonly property bool layout: PersonalizationConfig.keyboardPanelLayout
                        readonly property bool caps: PersonalizationConfig.keyboardPanelCaps
                        readonly property bool num: PersonalizationConfig.keyboardPanelNum
                    }
                }
            }
        }
    }
}
