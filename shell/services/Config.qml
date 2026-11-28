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

        readonly property QtObject time: QtObject {
            // D1's dateFormat became the clock entry's axis (D4b); the
            // bridge object stays only for future time-section keys.
        }

        readonly property QtObject battery: QtObject {
            readonly property int low: 20
            readonly property int critical: 10
            // Peripheral (mouse/keyboard/headset) thresholds, end4 defaults.
            readonly property int peripheralLow: 20
            readonly property int peripheralCritical: 5
            readonly property bool peripheralNotify: true
        }

        readonly property QtObject resources: QtObject {
            readonly property int updateInterval: 1000
            readonly property int historyLength: 60
            readonly property int autoStopDelay: 15000
            readonly property bool monitorGpu: true
        }

        readonly property QtObject bar: QtObject {
            id: barOptions

            // B9.4: `edge` is the single truth (end4 only had a bottom bool,
            // which made a right-edge bar look like a left-edge one to every
            // popup). The derived `bottom`/`vertical` views retired with
            // D4g 批四 — they had zero consumers, and the selected-bar
            // orientation is a per-entry fact now, not a global one.
            readonly property string edge: PersonalizationConfig.barPosition
            // B9.5 outer margins.
            readonly property real edgeMargin: PersonalizationConfig.barEdgeMargin ?? 5
            readonly property real sideMargin: PersonalizationConfig.resolvedBarSideMargin()
            readonly property bool showScrollHints: true
            readonly property bool followFrameColor: false
            readonly property string frameColor: ""
            // B9.7: screen filter from the settings page; empty = all screens.
            readonly property var screenList: PersonalizationConfig.barScreenList
            readonly property string groupColor: PersonalizationConfig.barGroupColor
            readonly property alias layouts: m3Options.layouts

            readonly property QtObject autoHide: QtObject {
                // B9.7: user-visible surface is only the slide-out switch.
                // pushWindows / hoverRegionWidth / super-reveal stay internal
                // defaults — they have live consumers in Bar.qml but no UI.
                readonly property bool enable: PersonalizationConfig.barAutoHide
                readonly property bool pushWindows: false
                readonly property int hoverRegionWidth: 2
                readonly property QtObject showWhenPressingSuper: QtObject {
                    readonly property bool enable: false
                    readonly property int delay: 100
                }
            }

            readonly property QtObject m3: QtObject {
                id: m3Options
                readonly property real gapsOut: 5

                readonly property QtObject layouts: QtObject {
                    // D4a: derived enabled-only id views off the barConfigs
                    // entry truth. Vendor widgets asking "is X on this side"
                    // must not count a disabled entry, so the bridge never
                    // serves raw membership.
                    readonly property var leftLayout: PersonalizationConfig.barLayoutEnabledIds("left")
                    readonly property var middleLayout: PersonalizationConfig.barLayoutEnabledIds("middle")
                    readonly property var rightLayout: PersonalizationConfig.barLayoutEnabledIds("right")
                }

                // iNiR reads these straight off the object (no optional
                // chaining), so a missing key is a TypeError on every binding
                // evaluation, not a silent default.
                readonly property bool verbose: true

                // D4b: the divider/resources/utilButtons/tray/workspaces
                // per-widget axes moved to lane-entry overrides
                // (BarWidgetDefaults.DEFAULTS). The bridge only keeps what is
                // still global: internal literals with no settings surface.

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

                // B9.7 widget surface: real properties instead of frozen
                // literals, so the Bar settings page rows are honest.
                // (D4b: the resources meters moved to lane-entry overrides.)
                readonly property QtObject resources: QtObject {
                    readonly property int memoryWarningThreshold: 90
                    readonly property int cpuWarningThreshold: 95
                    readonly property int swapWarningThreshold: 90
                }

                // D4d: the old tooltips hardcode retired with the
                // hoverPopouts axis (PersonalizationConfig.barAxes) — the
                // popup intent now has one truth.

                readonly property QtObject media: QtObject {
                    readonly property string preferredPlayer: ""
                    readonly property bool alwaysVisible: false
                    readonly property int updateInterval: 1000
                    readonly property bool onlyTitle: false
                }

                readonly property QtObject workspaces: QtObject {
                    readonly property bool useNerdFont: false
                    readonly property bool monochromeIcons: false
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
