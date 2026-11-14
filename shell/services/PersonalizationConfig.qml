pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons
import "../commons/SidebarPolicy.js" as SidebarPolicy
import "../commons/WallpaperSource.js" as WallpaperSource
import qs.services
import qs.commons.i18n

Singleton {
    id: root

    readonly property string configOverride: Quickshell.env("NYXURI_PERSONALIZATION_CONFIG") || ""
    readonly property string filePath: root.configOverride !== "" ? root.configOverride : ConfigService.filePath

    readonly property string configDir: {
        const separator = root.filePath.lastIndexOf("/");
        return separator > 0 ? root.filePath.slice(0, separator) : Paths.configHome;
    }
    readonly property var fillModes: [({
                "value": "Stretch",
                "label": I18n.tr("Stretch")
            }), ({
                "value": "Fit",
                "label": I18n.tr("Fit")
            }), ({
                "value": "Fill",
                "label": I18n.tr("Fill")
            }), ({
                "value": "Tile",
                "label": I18n.tr("Tile")
            }), ({
                "value": "TileVertically",
                "label": I18n.tr("Tile vertically")
            }), ({
                "value": "TileHorizontally",
                "label": I18n.tr("Tile horizontally")
            }), ({
                "value": "Pad",
                "label": I18n.tr("Cover")
            })]
    readonly property var desktopFillModes: root.fillModes.concat([({
                "value": "panorama",
                "label": I18n.tr("Panorama")
            })])
    readonly property var transitionTypes: [({
                "value": "random",
                "label": I18n.tr("Random")
            }), ({
                "value": "none",
                "label": I18n.tr("None")
            }), ({
                "value": "fade",
                "label": I18n.tr("Crossfade")
            }), ({
                "value": "wipe",
                "label": I18n.tr("Wipe")
            }), ({
                "value": "disc",
                "label": I18n.tr("Disc")
            }), ({
                "value": "stripes",
                "label": I18n.tr("Stripes")
            }), ({
                "value": "iris bloom",
                "label": I18n.tr("Iris bloom")
            }), ({
                "value": "pixelate",
                "label": I18n.tr("Pixelate")
            }), ({
                "value": "portal",
                "label": I18n.tr("Portal")
            })]
    readonly property var transitionEasingModes: [({
                "value": "linear",
                "label": I18n.tr("Linear")
            }), ({
                "value": "quad",
                "label": I18n.tr("Quadratic")
            }), ({
                "value": "cubic",
                "label": I18n.tr("Cubic")
            }), ({
                "value": "quart",
                "label": I18n.tr("Quartic")
            }), ({
                "value": "quint",
                "label": I18n.tr("Quintic")
            }), ({
                "value": "sine",
                "label": I18n.tr("Sine")
            }), ({
                "value": "expo",
                "label": I18n.tr("Exponential")
            }), ({
                "value": "circ",
                "label": I18n.tr("Circular")
            }), ({
                "value": "customBezier",
                "label": I18n.tr("Custom Bézier")
            })]
    readonly property var baseTransitions: ["fade", "wipe", "disc", "stripes", "iris bloom", "pixelate", "portal"]
    readonly property var matugenSchemes: [({
                "value": "scheme-tonal-spot",
                "label": I18n.tr("Tonal spot")
            }), ({
                "value": "scheme-vibrant",
                "label": I18n.tr("Vibrant")
            }), ({
                "value": "scheme-content",
                "label": I18n.tr("Content")
            }), ({
                "value": "scheme-expressive",
                "label": I18n.tr("Expressive")
            }), ({
                "value": "scheme-fidelity",
                "label": I18n.tr("Fidelity")
            }), ({
                "value": "scheme-fruit-salad",
                "label": I18n.tr("Fruit salad")
            }), ({
                "value": "scheme-monochrome",
                "label": I18n.tr("Monochrome")
            }), ({
                "value": "scheme-neutral",
                "label": I18n.tr("Neutral")
            }), ({
                "value": "scheme-rainbow",
                "label": I18n.tr("Rainbow")
            })]
    readonly property var edgePositions: [({
                "value": "top",
                "label": I18n.tr("Top"),
                "icon": "arrow_upward"
            }), ({
                "value": "left",
                "label": I18n.tr("Left"),
                "icon": "arrow_back"
            }), ({
                "value": "bottom",
                "label": I18n.tr("Bottom"),
                "icon": "arrow_downward"
            }), ({
                "value": "right",
                "label": I18n.tr("Right"),
                "icon": "arrow_forward"
            })]
    readonly property bool storeReady: ConfigService.storeReady
    property bool loading: false
    property bool loaded: false
    readonly property bool ready: root.storeReady && root.loaded && !root.loading
    property string bannerSource: ""
    property string wallpaperFolder: Paths.dataHome + "/wallpapers"
    property string wallpaperPath: ""
    property string wallpaperPathLight: ""
    property string wallpaperPathDark: ""
    property bool perModeWallpaper: false
    property bool perMonitorWallpaper: false
    property var monitorWallpapers: ({})
    property var monitorWallpaperFillModes: ({})
    property var recentWallpaperColors: []
    property string wallpaperFillMode: "Fill"
    property string desktopWallpaperBackend: "quickshell"
    property bool autoCycleEnabled: false
    property string autoCycleMode: "interval"
    property int autoCycleInterval: 300
    property string autoCycleTime: "06:00"
    property string wallpaperTransitionType: "fade"
    property var includedTransitions: root.baseTransitions
    property int transitionDurationMs: 1000
    property string transitionEasingMode: "customBezier"
    property var transitionBezierCurve: [0.43, 1.19, 1, 0.4, 1, 1]
    property bool overviewEnabled: true
    property bool overviewUseDesktopWallpaper: true
    property string overviewWallpaperPath: ""
    property string overviewWallpaperFillMode: "Fill"
    property bool overviewPerMonitorWallpaper: false
    property var overviewMonitorWallpapers: ({})
    property var overviewMonitorFillModes: ({})
    property string overviewTransitionType: "fade"
    property real overviewBlurRadius: 0
    property real overviewDim: 0
    property real overviewSaturation: 1
    property real overviewContrast: 1
    property bool parallaxVerticalEnabled: false
    property bool parallaxFollowWorkspaces: true
    property bool parallaxFollowSidebars: false
    property bool parallaxFollowTiledColumns: false
    property real parallaxPreferredScale: 1.1
    property int parallaxTiledColumnSpan: 6
    property string matugenScheme: "scheme-tonal-spot"
    property var matugenTemplates: ({})
    readonly property var lockScreenStyles: [
        {
            value: "default",
            label: "default"
        },
        {
            value: "caelestia",
            label: "caelestia"
        }
    ]
    property string lockScreenStyle: "default"
    readonly property var settingsPanelStyles: [
        {
            "value": "default",
            "label": I18n.tr("Default")
        },
        {
            "value": "dashboard",
            "label": I18n.tr("Dashboard")
        }
    ]
    property string settingsPanelStyle: "default"

    // ── Lyrics ──────────────────────────────────────────────────────────────
    readonly property var lyricSources: [
        {
            "value": "kugou",
            "label": I18n.tr("Kugou (word timing)")
        },
        {
            "value": "lrclib",
            "label": I18n.tr("LRCLIB only")
        }
    ]
    property string lyricSource: "kugou"

    readonly property int lyricOffsetMinMs: -5000
    readonly property int lyricOffsetMaxMs: 5000
    property int lyricOffsetMs: 0

    readonly property int lyricFontSizeMin: 16
    readonly property int lyricFontSizeMax: 40
    property int lyricFontSize: 26

    property bool lyricAlbumArtTint: true

    property bool lyricShowTranslation: true

    function setLyricSource(value) {
        setValue("lyricSource", normalizedOption(root.lyricSources, value, "kugou"));
    }

    function setLyricShowTranslation(value) {
        setValue("lyricShowTranslation", value === true);
    }

    function setLyricOffsetMs(value) {
        setValue("lyricOffsetMs", normalizedBoundedInt(value, 0, root.lyricOffsetMinMs, root.lyricOffsetMaxMs));
    }

    function setLyricFontSize(value) {
        setValue("lyricFontSize", normalizedBoundedInt(value, 26, root.lyricFontSizeMin, root.lyricFontSizeMax));
    }

    function setLyricAlbumArtTint(value) {
        setValue("lyricAlbumArtTint", value === true);
    }
    property string themeMode: "dark"
    property string superKeyStyle: "text"
    readonly property var superKeyStyles: [
        {
            "value": "text",
            "label": "Super"
        },
        {
            "value": "command",
            "label": "⌘ Command"
        }
    ]
    property string cursorTheme: ""
    property int cursorSize: 24
    property bool cursorHideWhenTyping: false
    property int cursorHideAfterInactiveMs: 0
    property string iconTheme: ""
    // B9.3: layout membership is the island's only switch. The old
    // `islandEnabled` gate is read once during load (legacy migration) and is
    // never serialized again.
    // B8.4: idle-face satellite is an explicit optional part, not the iNiR
    // leftWidget hardcode that rendered weather under a "clockWidget" value.
    property string islandSatellite: "clock"
    readonly property var islandSatelliteOptions: [
        {
            "value": "clock",
            "label": I18n.tr("Clock"),
            "icon": "schedule"
        },
        {
            "value": "weather",
            "label": I18n.tr("Weather"),
            "icon": "partly_cloudy_day"
        },
        {
            "value": "none",
            "label": I18n.tr("None"),
            "icon": "block"
        }
    ]
    // B3-1 one-shot marker: seed the middle lane with the island exactly once.
    property bool islandLayoutMigrated: false
    property string barPosition: "top"
    // B9.7 settled keys. `barAutoHide` drives `bar.autoHide.enable` (the
    // slide-out window); pushWindows / hoverRegionWidth / super-reveal stay
    // internal bridge defaults — consumed, but not user-visible surface.
    property bool barAutoHide: false
    // Screen filter for the bar windows. Empty list = every screen (end4
    // semantics); names come from Quickshell.screens.
    property var barScreenList: []
    // end4 `bar.showBackground`: the frame/pill background of non-material
    // styles. Only Hug/Float expose it; other styles ignore it downstream.
    property bool barShowBackground: true
    readonly property var barCornerStyles: [
        {
            value: 0,
            label: I18n.tr("Hug")
        },
        {
            value: 1,
            label: I18n.tr("Floating")
        },
        {
            value: 2,
            label: I18n.tr("Islands")
        },
        {
            value: 3,
            label: I18n.tr("Material")
        },
        {
            value: 4,
            label: I18n.tr("Material hug")
        },
        {
            value: 5,
            label: I18n.tr("Panel")
        }
    ]
    property int barCornerStyle: 1
    // Single truth for the material pill treatment (end4: cornerStyle 3 or 4).
    // Widgets bind these instead of re-deriving `=== 3`, which kept 4/5
    // half-styled in nine files.
    readonly property bool barIsMaterial: root.barCornerStyle === 3 || root.barCornerStyle === 4
    readonly property bool barIsMaterialHug: root.barCornerStyle === 4
    readonly property bool barIsPanel: root.barCornerStyle === 5
    // end4 style heights (ROADMAP B-2): Float adds the outer gap on both edges,
    // Material hug and Panel add 4 for their round decorators. Everything else
    // keeps the user's thickness, and groups/OSD/popups read the evaluated
    // height through Appearance.sizes.barHeight.
    readonly property real barStyleHeightBoost: root.barCornerStyle === 1 ? Appearance.sizes.hyprlandGapsOut * 2 : ((root.barIsMaterialHug || root.barIsPanel) ? 4 : 0)
    Binding {
        target: Appearance
        property: "barStyleBoost"
        value: root.barStyleHeightBoost
        restoreMode: Binding.RestoreNone
    }
    readonly property var barBorderlessModes: [
        {
            value: "pills",
            label: I18n.tr("Pills")
        },
        {
            value: "separated",
            label: I18n.tr("Separated")
        },
        {
            value: "segmented",
            label: I18n.tr("Segmented")
        },
        {
            value: "transparent",
            label: I18n.tr("Transparent")
        }
    ]
    property string barBorderless: "pills"
    property string barGroupColor: "layer1"
    readonly property var barGroupColorOptions: [
        {
            "value": "primaryContainer",
            "label": I18n.tr("Primary container")
        },
        {
            "value": "secondaryContainer",
            "label": I18n.tr("Secondary container")
        },
        {
            "value": "tertiaryContainer",
            "label": I18n.tr("Tertiary container")
        },
        {
            "value": "layer1",
            "label": I18n.tr("Surface layer")
        },
        {
            "value": "layer0",
            "label": I18n.tr("Background")
        }
    ]
    // Per-widget background/border overrides from the bar's right-click style
    // editor. Shape: { mode, widget, color?, borderColor?, radius?,
    // borderWidth?, padding? } — normalized on load, saved with the bar block.
    property var barWidgetStyles: []
    readonly property var barDividerStyles: [
        {
            value: "rect",
            label: I18n.tr("Line")
        },
        {
            value: "dot",
            label: I18n.tr("Dot")
        },
        {
            value: "space",
            label: I18n.tr("Space")
        }
    ]
    property string barDividerStyle: "rect"
    // end4 `bar.divider.spacing`: width of the "space" divider style only
    // (line/dot dividers ignore it). end4 spinbox range 4–400 step 2.
    property int barDividerSpacing: 4
    // Tray contract (ROADMAP B9.1). Pinned ids keep a permanent slot; every
    // other visible client moves behind the overflow arrow. filterPassive hides
    // Status.Passive clients, invertPinnedItems swaps the two groups, showItemId
    // appends the DBus id to the tooltip, monochromeIcons tints the glyphs with
    // the bar ink instead of the app's own colour.
    property var barTrayPinnedItems: []
    property bool barTrayFilterPassive: true
    property bool barTrayInvertPinnedItems: true
    property bool barTrayShowItemId: false
    property bool barTrayMonochromeIcons: true
    // end4 `bar.utilButtons` slots (B9.7): which shortcut buttons the
    // UtilButtons widget renders. The screen-record slot was executed with the
    // recorder domain (B-4); the remaining seven map to live actions.
    property bool barShowScreenSnip: true
    property bool barShowColorPicker: true
    property bool barShowKeyboardToggle: false
    property bool barShowMicToggle: false
    property bool barShowWallpaperToggle: false
    property bool barShowDarkModeToggle: true
    property bool barShowPerformanceProfile: false
    // end4 `bar.resources` widget surface (B9.7): which meters the
    // Resources widget shows, its icon style, and the percentage readout.
    // The polling service keeps its own internal defaults (not user surface).
    property bool barShowCpu: true
    property bool barShowCpuTemp: false
    property bool barShowRam: true
    property bool barShowDisk: false
    property bool barShowSwap: false
    readonly property var barResourceStyles: [
        {
            value: "filled",
            label: I18n.tr("Filled")
        },
        {
            value: "outline",
            label: I18n.tr("Outline")
        }
    ]
    property string barResourceStyle: "outline"
    property bool barResourceShowValue: false
    // Workspace indicator shape (B8.3 parity with end4): numbers by default,
    // optional app icons, dot/icon marker when neither is shown.
    property bool barShowAppIcons: false
    property bool barAlwaysShowNumbers: true
    readonly property var barWorkspaceIndicatorStyles: [
        {
            value: "dot",
            label: I18n.tr("Dot")
        },
        {
            value: "icon",
            label: I18n.tr("Icon")
        }
    ]
    property string barWorkspaceIndicatorStyle: "dot"
    // Workspace lane shape (B9.6 parity with end4): fixed slot count with
    // group paging, and the four end4 skins (default/gnome/dots/ticks).
    readonly property var barWorkspaceStyles: [
        {
            value: "default",
            label: I18n.tr("Default")
        },
        {
            value: "gnome",
            label: I18n.tr("Gnome")
        },
        {
            value: "dots",
            label: I18n.tr("Dots")
        },
        {
            value: "ticks",
            label: I18n.tr("Ticks")
        }
    ]
    property string barWorkspaceStyle: "default"
    property int barWorkspaceShown: 10
    // end4 "Numbers style" (B9.7): the workspace number label preset. end4
    // serialized the raw string array; Nyxuri stores the preset name as the
    // single truth and derives the array — the UI only ever offered the three
    // presets, so nothing else was representable.
    readonly property var barWorkspaceNumberStyles: [
        {
            value: "normal",
            label: I18n.tr("Normal")
        },
        {
            value: "han",
            label: I18n.tr("Han chars")
        },
        {
            value: "roman",
            label: I18n.tr("Roman")
        }
    ]
    property string barWorkspaceNumberStyle: "normal"
    readonly property var _barWorkspaceNumberHanMaps: ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]
    readonly property var _barWorkspaceNumberRomanMaps: ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
    // What `bar.m3.workspaces.numberMap` feeds the Workspaces widget. Slots
    // beyond the preset fall back to plain numbers at the consumer.
    readonly property var barWorkspaceNumberMap: root.barWorkspaceNumberStyle === "han" ? root._barWorkspaceNumberHanMaps : root.barWorkspaceNumberStyle === "roman" ? root._barWorkspaceNumberRomanMaps : []
    // Only ids the bar can actually render. `information` was never a widget
    // (it was an iNiR bar style name) and mapped to a missing Information.qml.
    // B8.2 re-added the end4 base widgets (BarWidgetSwitcher/ClippedProgressBar/
    // ResourceUsage), so clock / systemMonitor / battery are selectable again.
    // B9.7 re-added `utilButtons` (end4 keeps it addable; its seven slots are
    // wired to real toggles), which had been stripped from the whitelist and
    // made the whole widget unreachable.
    readonly property var barComponentIds: ["workspaces", "activeWindow", "media", "tray", "quickSettings", "island", "divisor", "clock", "systemMonitor", "battery", "systemIcons", "launcherButton", "powerButton", "utilButtons"]
    readonly property var defaultBarLeadingComponents: ["launcherButton", "workspaces", "activeWindow"]
    readonly property var defaultBarTrailingComponents: ["tray", "quickSettings", "systemIcons", "powerButton"]
    readonly property var barComponentOptions: [({
                "value": "media",
                "label": I18n.tr("Media"),
                "icon": "music_note"
            }), ({
                "value": "workspaces",
                "label": I18n.tr("Workspaces"),
                "icon": "grid_view"
            }), ({
                "value": "activeWindow",
                "label": I18n.tr("Active Window"),
                "icon": "web_asset"
            }), ({
                "value": "tray",
                "label": I18n.tr("Tray"),
                "icon": "inbox"
            }), ({
                "value": "quickSettings",
                "label": I18n.tr("Quick Settings"),
                "icon": "tune"
            }), ({
                "value": "divisor",
                "label": I18n.tr("Divider"),
                "icon": "more_vert"
            }), ({
                "value": "clock",
                "label": I18n.tr("Clock"),
                "icon": "schedule"
            }), ({
                "value": "systemMonitor",
                "label": I18n.tr("System Monitor"),
                "icon": "monitoring"
            }), ({
                "value": "battery",
                "label": I18n.tr("Battery"),
                "icon": "battery_full"
            }), ({
                "value": "systemIcons",
                "label": I18n.tr("System Icons"),
                "icon": "volume_up"
            }), ({
                "value": "launcherButton",
                "label": I18n.tr("Launcher"),
                "icon": "search"
            }), ({
                "value": "powerButton",
                "label": I18n.tr("Power"),
                "icon": "power_settings_new"
            }), ({
                "value": "utilButtons",
                "label": I18n.tr("Utility buttons"),
                "icon": "widgets"
            })]
    readonly property var quickSettingsComponentIds: ["network", "bluetooth", "brightness", "volume", "microphone", "battery", "settings", "power"]
    readonly property var defaultQuickSettingsComponents: root.quickSettingsComponentIds.slice()
    readonly property var quickSettingsComponentOptions: [({
                "value": "network",
                "label": I18n.tr("Network"),
                "icon": "wifi"
            }), ({
                "value": "bluetooth",
                "label": I18n.tr("Bluetooth"),
                "icon": "bluetooth"
            }), ({
                "value": "brightness",
                "label": I18n.tr("Brightness"),
                "icon": "brightness_6"
            }), ({
                "value": "volume",
                "label": I18n.tr("Volume"),
                "icon": "volume_up"
            }), ({
                "value": "microphone",
                "label": I18n.tr("Microphone"),
                "icon": "mic"
            }), ({
                "value": "battery",
                "label": I18n.tr("Battery"),
                "icon": "battery_full"
            }), ({
                "value": "settings",
                "label": I18n.tr("Settings"),
                "icon": "settings"
            }), ({
                "value": "power",
                "label": I18n.tr("Power"),
                "icon": "power_settings_new"
            })]
    property var barLeadingComponents: root.defaultBarLeadingComponents.slice()
    property var barTrailingComponents: root.defaultBarTrailingComponents.slice()
    property var quickSettingsComponents: root.defaultQuickSettingsComponents.slice()
    readonly property int defaultBarThickness: 36
    property int barThickness: root.defaultBarThickness
    onBarThicknessChanged: Appearance.barThickness = root.barThickness
    // B9.4: vertical thickness is a separate axis (ROADMAP B-2). It used to
    // reuse `barThickness`, which made the left/right edges impossible to tune
    // apart from the top/bottom one.
    readonly property int defaultBarVerticalThickness: 36
    property int barVerticalThickness: root.defaultBarVerticalThickness
    onBarVerticalThicknessChanged: Appearance.verticalBarThickness = root.barVerticalThickness
    // B9.5 outer margins: distance from the screen edge (normal axis) and the
    // inset at both ends (along the bar). 0 keeps the end4 edge-flush baseline;
    // they are separate from the internal lane inset.
    property int barEdgeMargin: 0
    property int barSideMargin: 0

    // Three-lane drag layout for the status bar (left / middle / right). These
    // mirror the leading/trailing model but let the user place widgets freely
    // across three lanes. An empty array means "show nothing in that lane", so
    // fresh configs fall back to a sensible default instead of a blank bar.
    readonly property var defaultBarLayoutLeft: ["launcherButton", "workspaces", "activeWindow"]
    // B3-1: the island is a first-class middle widget, not a reserved gap.
    readonly property var defaultBarLayoutMiddle: ["island"]
    readonly property var defaultBarLayoutRight: ["tray", "quickSettings", "systemIcons", "powerButton"]
    property var barLayoutLeft: root.defaultBarLayoutLeft.slice()
    property var barLayoutMiddle: root.defaultBarLayoutMiddle.slice()
    property var barLayoutRight: root.defaultBarLayoutRight.slice()

    // B9.3 single truth: the island exists exactly when it is a member of any
    // bar lane. Notification-slot arbitration and the bar widget filter both
    // read this instead of a second config switch.
    readonly property bool islandInLayout: root.barLayoutLeft.indexOf("island") !== -1 || root.barLayoutMiddle.indexOf("island") !== -1 || root.barLayoutRight.indexOf("island") !== -1

    // iNiR keyboardIndicators semantics: the persistent panel (SystemIcons)
    // and the transient popup (island OSD) are independent axes.
    property bool keyboardShowPopup: true
    property bool keyboardShowPanel: true
    property bool keyboardPopupLayout: true
    property bool keyboardPopupCaps: true
    property bool keyboardPopupNum: false
    property bool keyboardPanelLayout: true
    property bool keyboardPanelCaps: true
    property bool keyboardPanelNum: false

    property bool islandHideDate: false
    // Idle-face avatar is optional: the identity circle can be hidden while the
    // satellite clock/weather and status icons stay.
    property bool islandShowAvatar: true
    property bool barShowValues: true
    property bool barShowNames: false

    readonly property var horizontalClockAxisDefaults: ({
            "wght": 900,
            "wdth": 85,
            "opsz": 18,
            "GRAD": 0,
            "ROND": 25,
            "slnt": 0
        })
    readonly property var horizontalClockAxisMinimums: ({
            "wght": 1,
            "wdth": 25,
            "opsz": 6,
            "GRAD": 0,
            "ROND": 0,
            "slnt": -10
        })
    readonly property var horizontalClockAxisMaximums: ({
            "wght": 1000,
            "wdth": 151,
            "opsz": 144,
            "GRAD": 100,
            "ROND": 100,
            "slnt": 0
        })
    readonly property var horizontalClockDigitDefaults: ({
            "separator": ({
                    "x": 0,
                    "y": 0,
                    "rotation": 0,
                    "colorRole": "primary",
                    "customColor": ""
                }),
            "h0": ({
                    "x": 0,
                    "y": -2,
                    "rotation": -3,
                    "colorRole": "inversePrimary",
                    "customColor": ""
                }),
            "h1": ({
                    "x": 0,
                    "y": 1,
                    "rotation": 3,
                    "colorRole": "primary",
                    "customColor": ""
                }),
            "m0": ({
                    "x": 0,
                    "y": -1,
                    "rotation": -2,
                    "colorRole": "inversePrimary",
                    "customColor": ""
                }),
            "m1": ({
                    "x": 0,
                    "y": 1,
                    "rotation": 2,
                    "colorRole": "primary",
                    "customColor": ""
                }),
            "ap": ({
                    "x": 1,
                    "y": -2,
                    "rotation": -2,
                    "colorRole": "inversePrimary",
                    "customColor": ""
                }),
            "periodM": ({
                    "x": 1,
                    "y": 1,
                    "rotation": 2,
                    "colorRole": "primary",
                    "customColor": ""
                })
        })
    property int horizontalClockFontSize: 22
    property var horizontalClockAxes: ({
            "wght": 900,
            "wdth": 85,
            "opsz": 18,
            "GRAD": 0,
            "ROND": 25,
            "slnt": 0
        })
    property var horizontalClockDigits: ({
            "separator": ({
                    "x": 0,
                    "y": 0,
                    "rotation": 0,
                    "colorRole": "primary",
                    "customColor": ""
                }),
            "h0": ({
                    "x": 0,
                    "y": -2,
                    "rotation": -3,
                    "colorRole": "inversePrimary",
                    "customColor": ""
                }),
            "h1": ({
                    "x": 0,
                    "y": 1,
                    "rotation": 3,
                    "colorRole": "primary",
                    "customColor": ""
                }),
            "m0": ({
                    "x": 0,
                    "y": -1,
                    "rotation": -2,
                    "colorRole": "inversePrimary",
                    "customColor": ""
                }),
            "m1": ({
                    "x": 0,
                    "y": 1,
                    "rotation": 2,
                    "colorRole": "primary",
                    "customColor": ""
                }),
            "ap": ({
                    "x": 1,
                    "y": -2,
                    "rotation": -2,
                    "colorRole": "inversePrimary",
                    "customColor": ""
                }),
            "periodM": ({
                    "x": 1,
                    "y": 1,
                    "rotation": 2,
                    "colorRole": "primary",
                    "customColor": ""
                })
        })
    readonly property string uiFontFamily: FontService.configuredUi || FontService.defaultUi
    readonly property string monoFontFamily: FontService.configuredMono || FontService.defaultMono
    readonly property string numericFontFamily: FontService.configuredNumeric || FontService.defaultNumeric
    readonly property string expressiveFontFamily: FontService.configuredExpressive || Fonts.bundledFamilyName
    property real shellBackgroundOpacity: 1
    property bool shellBlurEnabled: false
    property bool shellBlurXray: true
    property bool keepSidebarsLoaded: true
    property var sidebarPositions: ({
            dashboard: "left",
            quickSettings: "right"
        })
    readonly property string dashboardSidebarSide: sidebarPositions.dashboard
    readonly property string quickSettingsSidebarSide: sidebarPositions.quickSettings
    readonly property var hotCornerIds: ["top-left", "top-right", "bottom-left", "bottom-right"]
    readonly property var hotCornerActionIds: ["disabled", "overview", "dashboard:info", "dashboard:drawer", "dashboard:weather", "quicksettings:settings", "quicksettings:network", "quicksettings:bluetooth", "quicksettings:audio", "quicksettings:microphone", "quicksettings:idle", "quicksettings:night"]
    property var hotCornerActions: ({
            "top-left": "overview",
            "top-right": "disabled",
            "bottom-left": "disabled",
            "bottom-right": "disabled"
        })
    property bool desktopCardGridSnapEnabled: true
    property bool desktopCardGridVisibleWhileDragging: true

    signal settingsLoaded

    function optionExists(options, value) {
        for (let i = 0; i < options.length; i += 1) {
            if (options[i].value === value)
                return true;
        }
        return false;
    }

    function normalizedOption(options, value, fallback) {
        return optionExists(options, value) ? value : fallback;
    }

    function normalizedTransition(value) {
        return normalizedOption(root.transitionTypes, value, "fade");
    }

    function normalizedEasingMode(value) {
        return normalizedOption(root.transitionEasingModes, value, "customBezier");
    }

    function normalizedEdgePosition(value) {
        return normalizedOption(root.edgePositions, value, "top");
    }

    function normalizedIncluded(raw) {
        if (!Array.isArray(raw))
            return root.baseTransitions.slice();

        const result = [];
        for (let i = 0; i < raw.length; i += 1) {
            const value = raw[i];
            if (root.baseTransitions.indexOf(value) !== -1 && result.indexOf(value) === -1)
                result.push(value);
        }
        return result.length > 0 ? result : root.baseTransitions.slice();
    }

    function normalizedBezier(raw) {
        const fallback = [0.43, 1.19, 1, 0.4, 1, 1];
        if (!Array.isArray(raw) || raw.length < 4)
            return fallback.slice();

        const source = raw.length === 4 ? [raw[0], raw[1], raw[2], raw[3], 1, 1] : raw;
        const result = [];
        for (let i = 0; i < 6; i += 1) {
            const value = Number(source[i]);
            result.push(isFinite(value) ? value : fallback[i]);
        }
        return result;
    }

    function cloneMap(map) {
        const result = {};
        if (!map)
            return result;

        for (let key in map)
            result[key] = map[key];
        return result;
    }

    function normalizedStringMap(raw) {
        const result = {};
        if (!raw || typeof raw !== "object" || Array.isArray(raw))
            return result;

        for (let key in raw)
            result[String(key)] = String(raw[key] || "");
        return result;
    }

    function normalizedCursorTheme(value) {
        if (typeof value !== "string")
            return "";

        const result = value.trim();
        if (result.length > 256 || /[\u0000-\u001f\u007f]/.test(result))
            return "";

        return result;
    }

    function normalizedMatugenTemplates(raw) {
        const source = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
        const result = Object.create(null);
        for (const id of Object.keys(source)) {
            if (/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$/.test(id) && id !== "quickshell" && typeof source[id] === "boolean")
                result[id] = source[id];
        }
        return result;
    }

    function normalizedFillModeMap(raw, options) {
        const result = {};
        if (!raw || typeof raw !== "object" || Array.isArray(raw))
            return result;

        const validOptions = options || root.desktopFillModes;
        for (let key in raw)
            result[String(key)] = normalizedOption(validOptions, raw[key], "Fill");
        return result;
    }

    function normalizedRecentColors(raw) {
        if (!Array.isArray(raw))
            return [];

        const result = [];
        for (let i = 0; i < raw.length && result.length < 5; i += 1) {
            const value = String(raw[i] || "").trim().toLowerCase();
            if (/^#([0-9a-f]{6}|[0-9a-f]{8})$/.test(value) && result.indexOf(value) === -1)
                result.push(value);
        }
        return result;
    }

    function setValue(propertyName, value) {
        if (root[propertyName] === value)
            return;

        root[propertyName] = value;
        root.save();
    }

    function setBannerSource(value) {
        setValue("bannerSource", String(value || ""));
    }

    function setWallpaperFolder(value) {
        setValue("wallpaperFolder", value || Paths.dataHome + "/wallpapers");
    }

    function setWallpaperPath(value) {
        setValue("wallpaperPath", value || "");
    }

    function setWallpaperPathForMode(mode, value) {
        if (mode === "light")
            setValue("wallpaperPathLight", value || "");
        else
            setValue("wallpaperPathDark", value || "");
    }

    function setPerModeWallpaper(value) {
        setValue("perModeWallpaper", !!value);
    }

    function setPerMonitorWallpaper(value) {
        setValue("perMonitorWallpaper", !!value);
    }

    function setDesktopWallpaperBackend(value) {
        setValue("desktopWallpaperBackend", "quickshell");
    }

    function setMonitorWallpaper(screenName, value) {
        if (!screenName)
            return;

        const next = cloneMap(root.monitorWallpapers);
        next[screenName] = value || "";
        root.monitorWallpapers = next;
        root.save();
    }

    function monitorWallpaper(screenName) {
        if (!screenName || !root.monitorWallpapers)
            return "";

        return root.monitorWallpapers[screenName] || "";
    }

    function setWallpaperFillMode(value) {
        setValue("wallpaperFillMode", normalizedOption(root.desktopFillModes, value, "Fill"));
    }

    function setMonitorWallpaperFillMode(screenName, value) {
        if (!screenName)
            return;

        const next = cloneMap(root.monitorWallpaperFillModes);
        next[screenName] = normalizedOption(root.desktopFillModes, value, "Fill");
        root.monitorWallpaperFillModes = next;
        root.save();
    }

    function monitorFillMode(screenName) {
        if (!screenName || !root.monitorWallpaperFillModes)
            return root.wallpaperFillMode;

        return root.monitorWallpaperFillModes[screenName] || root.wallpaperFillMode;
    }

    function addRecentWallpaperColor(color) {
        const value = String(color || "").trim().toLowerCase();
        if (!/^#([0-9a-f]{6}|[0-9a-f]{8})$/.test(value))
            return;

        const next = [value];
        const source = normalizedRecentColors(root.recentWallpaperColors);
        for (let i = 0; i < source.length && next.length < 5; i += 1) {
            if (source[i] !== value)
                next.push(source[i]);
        }
        root.recentWallpaperColors = next;
        root.save();
    }

    function setAutoCycleEnabled(value) {
        setValue("autoCycleEnabled", !!value);
    }

    function setAutoCycleMode(value) {
        setValue("autoCycleMode", value === "time" ? "time" : "interval");
    }

    function setAutoCycleInterval(value) {
        setValue("autoCycleInterval", Math.max(5, Math.round(Number(value) || 300)));
    }

    function setAutoCycleTime(value) {
        const next = /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/.test(value) ? value : "06:00";
        setValue("autoCycleTime", next);
    }

    function setWallpaperTransitionType(value) {
        setValue("wallpaperTransitionType", normalizedTransition(value));
    }

    function setIncludedTransitions(values) {
        root.includedTransitions = normalizedIncluded(values);
        root.save();
    }

    function setTransitionIncluded(value, enabled) {
        if (root.baseTransitions.indexOf(value) === -1)
            return;

        const next = root.includedTransitions.slice();
        const index = next.indexOf(value);
        if (enabled && index === -1)
            next.push(value);

        if (!enabled && index !== -1)
            next.splice(index, 1);

        root.setIncludedTransitions(next);
    }

    function normalizedDurationMs(value, fallback) {
        if (value === null || value === undefined || value === "")
            return fallback;

        const numberValue = Number(value);
        return !isFinite(numberValue) ? fallback : Math.max(0, Math.min(5000, Math.round(numberValue)));
    }

    function normalizedBoundedInt(value, fallback, minValue, maxValue) {
        if (value === null || value === undefined || value === "")
            return fallback;

        const numberValue = Number(value);
        if (!isFinite(numberValue))
            return fallback;

        return Math.max(minValue, Math.min(maxValue, Math.round(numberValue)));
    }

    function setTransitionDurationMs(value) {
        setValue("transitionDurationMs", normalizedDurationMs(value, 0));
    }

    function setTransitionEasingMode(value) {
        setValue("transitionEasingMode", normalizedEasingMode(value));
    }

    function setTransitionBezierCurve(value) {
        root.transitionBezierCurve = normalizedBezier(value);
        root.save();
    }

    function setTransitionBezierControlPoints(x1, y1, x2, y2) {
        root.setTransitionBezierCurve([x1, y1, x2, y2, 1, 1]);
    }

    function normalizedBoundedReal(value, fallback, minValue, maxValue) {
        if (value === null || value === undefined || value === "")
            return fallback;

        const numberValue = Number(value);
        if (!isFinite(numberValue))
            return fallback;

        return Math.max(minValue, Math.min(maxValue, numberValue));
    }

    function normalizedHorizontalClockAxes(raw) {
        const source = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
        const result = {};
        const names = ["wght", "wdth", "opsz", "GRAD", "ROND", "slnt"];
        for (let i = 0; i < names.length; i += 1) {
            const name = names[i];
            result[name] = root.normalizedBoundedReal(source[name], root.horizontalClockAxisDefaults[name], root.horizontalClockAxisMinimums[name], root.horizontalClockAxisMaximums[name]);
        }
        return result;
    }

    function normalizedHorizontalClockDigits(raw) {
        const source = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
        const result = {};
        const ids = ["h0", "h1", "separator", "m0", "m1", "ap", "periodM"];
        const colorRoles = ["primary", "inversePrimary", "custom"];
        for (let i = 0; i < ids.length; i += 1) {
            const id = ids[i];
            const fallback = root.horizontalClockDigitDefaults[id];
            const candidate = source[id] && typeof source[id] === "object" && !Array.isArray(source[id]) ? source[id] : {};
            const candidateColor = String(candidate.customColor || "").trim().toLowerCase();
            const hasCustomColor = /^#([0-9a-f]{6}|[0-9a-f]{8})$/.test(candidateColor);
            let colorRole = colorRoles.indexOf(candidate.colorRole) !== -1 ? candidate.colorRole : fallback.colorRole;
            if (colorRole === "custom" && !hasCustomColor)
                colorRole = fallback.colorRole;

            result[id] = {
                "x": root.normalizedBoundedInt(candidate.x, fallback.x, -8, 8),
                "y": root.normalizedBoundedInt(candidate.y, fallback.y, -6, 6),
                "rotation": root.normalizedBoundedInt(candidate.rotation, fallback.rotation, -12, 12),
                "colorRole": colorRole,
                "customColor": hasCustomColor ? candidateColor : ""
            };
        }
        return result;
    }

    function horizontalClockDigit(id) {
        const defaults = root.horizontalClockDigitDefaults[id];
        const configured = root.horizontalClockDigits[id];
        return configured || defaults;
    }

    function horizontalClockDigitColor(id) {
        const digit = root.horizontalClockDigit(id);
        if (digit.colorRole === "custom" && /^#([0-9a-f]{6}|[0-9a-f]{8})$/i.test(String(digit.customColor || "")))
            return digit.customColor;

        return digit.colorRole === "inversePrimary" ? Appearance.colors.colInversePrimary : Appearance.colors.colPrimary;
    }

    function setOverviewEnabled(value) {
        setValue("overviewEnabled", !!value);
    }

    function setOverviewUseDesktopWallpaper(value) {
        setValue("overviewUseDesktopWallpaper", !!value);
    }

    function setOverviewWallpaperPath(value) {
        setValue("overviewWallpaperPath", value || "");
    }

    function setOverviewWallpaperFillMode(value) {
        setValue("overviewWallpaperFillMode", normalizedOption(root.fillModes, value, "Fill"));
    }

    function setOverviewPerMonitorWallpaper(value) {
        setValue("overviewPerMonitorWallpaper", !!value);
    }

    function setOverviewMonitorWallpaper(screenName, value) {
        if (!screenName)
            return;

        const next = cloneMap(root.overviewMonitorWallpapers);
        next[screenName] = value || "";
        root.overviewMonitorWallpapers = next;
        root.save();
    }

    function overviewMonitorWallpaper(screenName) {
        if (!screenName || !root.overviewMonitorWallpapers)
            return "";

        return root.overviewMonitorWallpapers[screenName] || "";
    }

    function setOverviewMonitorFillMode(screenName, value) {
        if (!screenName)
            return;

        const next = cloneMap(root.overviewMonitorFillModes);
        next[screenName] = normalizedOption(root.fillModes, value, "Fill");
        root.overviewMonitorFillModes = next;
        root.save();
    }

    function overviewMonitorFillMode(screenName) {
        if (!screenName || !root.overviewMonitorFillModes)
            return root.overviewWallpaperFillMode;

        return root.overviewMonitorFillModes[screenName] || root.overviewWallpaperFillMode;
    }

    function setOverviewTransitionType(value) {
        setValue("overviewTransitionType", normalizedTransition(value));
    }

    function setOverviewBlurRadius(value) {
        setValue("overviewBlurRadius", normalizedBoundedReal(value, 0, 0, 100));
    }

    function setOverviewDim(value) {
        setValue("overviewDim", normalizedBoundedReal(value, 0, 0, 1));
    }

    function setOverviewSaturation(value) {
        setValue("overviewSaturation", normalizedBoundedReal(value, 1, 0, 2));
    }

    function setOverviewContrast(value) {
        setValue("overviewContrast", normalizedBoundedReal(value, 1, 0.5, 2));
    }

    function setParallaxVerticalEnabled(value) {
        setValue("parallaxVerticalEnabled", !!value);
    }

    function setParallaxFollowWorkspaces(value) {
        setValue("parallaxFollowWorkspaces", !!value);
    }

    function setParallaxFollowSidebars(value) {
        setValue("parallaxFollowSidebars", !!value);
    }

    function setParallaxFollowTiledColumns(value) {
        setValue("parallaxFollowTiledColumns", !!value);
    }

    function setParallaxPreferredScale(value) {
        setValue("parallaxPreferredScale", normalizedBoundedReal(value, 1.1, 1, 1.35));
    }

    function setParallaxTiledColumnSpan(value) {
        setValue("parallaxTiledColumnSpan", normalizedBoundedInt(value, 6, 2, 12));
    }

    function setMatugenScheme(value) {
        setValue("matugenScheme", normalizedOption(root.matugenSchemes, value, "scheme-tonal-spot"));
    }

    function isMatugenTemplateEnabled(id) {
        if (id === "fcitx5") {
            const t = TemplateService.templateById("fcitx5_theme");
            if (!t || !t.valid)
                return false;
            return root.isMatugenTemplateEnabled("fcitx5_theme") && root.isMatugenTemplateEnabled("fcitx5_panel") && root.isMatugenTemplateEnabled("fcitx5_highlight");
        }
        const template = TemplateService.templateById(id);
        if (!template || !template.valid)
            return false;
        if (Object.prototype.hasOwnProperty.call(root.matugenTemplates, id))
            return root.matugenTemplates[id] === true;
        return template.origin === "builtin";
    }

    function setMatugenTemplateEnabled(id, enabled) {
        if (id === "fcitx5") {
            let changed = false;
            for (const subId of ["fcitx5_theme", "fcitx5_panel", "fcitx5_highlight"]) {
                changed = root.setMatugenTemplateEnabled(subId, enabled) || changed;
            }
            return changed;
        }
        const template = TemplateService.templateById(id);
        if (!root.ready || !template || !template.valid)
            return false;
        const nextEnabled = !!enabled;
        if (root.isMatugenTemplateEnabled(id) === nextEnabled)
            return false;
        const next = root.normalizedMatugenTemplates(root.matugenTemplates);
        next[id] = nextEnabled;
        root.matugenTemplates = next;
        root.save();
        return true;
    }

    function discoverMatugenTemplates(templates) {
        if (!root.ready)
            return;
        const next = root.normalizedMatugenTemplates(root.matugenTemplates);
        let changed = false;
        for (const template of templates) {
            if (!Object.prototype.hasOwnProperty.call(next, template.id)) {
                next[template.id] = template.origin === "builtin";
                changed = true;
            }
        }
        if (changed) {
            root.matugenTemplates = next;
            root.save();
        }
    }

    function removeMatugenTemplate(id) {
        const next = root.normalizedMatugenTemplates(root.matugenTemplates);
        delete next[id];
        root.matugenTemplates = next;
        root.save();
    }

    function setThemeMode(value) {
        setValue("themeMode", value === "light" ? "light" : "dark");
    }

    function setCursorTheme(value) {
        setValue("cursorTheme", root.normalizedCursorTheme(value));
    }

    function setCursorSize(value) {
        setValue("cursorSize", root.normalizedBoundedInt(value, 24, 12, 128));
    }

    function setCursorHideWhenTyping(value) {
        setValue("cursorHideWhenTyping", typeof value === "boolean" ? value : false);
    }

    function setCursorHideAfterInactiveMs(value) {
        setValue("cursorHideAfterInactiveMs", root.normalizedBoundedInt(value, 0, 0, 5000));
    }

    function setIconTheme(value) {
        setValue("iconTheme", value || "");
    }

    function setLockScreenStyle(value) {
        setValue("lockScreenStyle", normalizedOption(root.lockScreenStyles, value, "default"));
    }

    function setSettingsPanelStyle(value) {
        setValue("settingsPanelStyle", normalizedOption(root.settingsPanelStyles, value, "default"));
    }

    // B9.3: "Show island" is a layout edit, not a separate gate. Adding puts
    // it back into the middle lane; removing drops it from every lane.
    function setIslandInLayout(value) {
        if (value === true)
            return root.islandInLayout || root.moveBarComponent("island", "middle", root.barLayoutMiddle.length);
        return root.removeBarComponent("island");
    }

    function setIslandSatellite(value) {
        setValue("islandSatellite", normalizedOption(root.islandSatelliteOptions, value, "clock"));
    }

    function setIslandShowAvatar(value) {
        setValue("islandShowAvatar", value === true);
    }

    function setFontFamily(role, family) {
        const allowedRoles = ["ui", "mono", "numeric", "expressive"];
        if (allowedRoles.indexOf(role) === -1)
            return false;

        const value = String(family || "").trim();
        if (value === "")
            return false;

        if (!FontService.containsFamily(value))
            return false;

        if (!FontService.setConfiguredFamily(role, value))
            return false;

        root.save();
        return true;
    }

    function setShellBackgroundOpacity(value) {
        setValue("shellBackgroundOpacity", normalizedBoundedReal(value, 1, 0, 1));
    }

    function setShellBlurEnabled(value) {
        setValue("shellBlurEnabled", !!value);
    }

    function setShellBlurXray(value) {
        setValue("shellBlurXray", !!value);
    }

    function setDashboardSidebarSide(value) {
        const side = SidebarPolicy.normalizeSide(value, "left");
        if (side !== root.dashboardSidebarSide)
            setValue("sidebarPositions", {
                dashboard: side,
                quickSettings: root.quickSettingsSidebarSide
            });
    }

    function setQuickSettingsSidebarSide(value) {
        const side = SidebarPolicy.normalizeSide(value, "right");
        if (side !== root.quickSettingsSidebarSide)
            setValue("sidebarPositions", {
                dashboard: root.dashboardSidebarSide,
                quickSettings: side
            });
    }

    function setKeepSidebarsLoaded(value) {
        setValue("keepSidebarsLoaded", !!value);
    }

    function normalizedHotCornerActions(value) {
        const source = value && typeof value === "object" ? value : {};
        const result = {};
        for (const corner of root.hotCornerIds) {
            const action = source[corner];
            result[corner] = root.hotCornerActionIds.indexOf(action) >= 0 ? action : corner === "top-left" ? "overview" : "disabled";
        }
        return result;
    }

    function setHotCornerAction(corner, action) {
        if (root.hotCornerIds.indexOf(corner) < 0 || root.hotCornerActionIds.indexOf(action) < 0)
            return;
        const next = root.normalizedHotCornerActions(root.hotCornerActions);
        next[corner] = action;
        setValue("hotCornerActions", next);
    }

    function setDesktopCardGridSnapEnabled(value) {
        setValue("desktopCardGridSnapEnabled", !!value);
    }

    function setDesktopCardGridVisibleWhileDragging(value) {
        setValue("desktopCardGridVisibleWhileDragging", !!value);
    }

    function setBarPosition(value) {
        setValue("barPosition", normalizedEdgePosition(value));
    }

    function setBarCornerStyle(value) {
        setValue("barCornerStyle", normalizedBoundedInt(value, 1, 0, 5));
    }

    function setBarBorderless(value) {
        setValue("barBorderless", normalizedOption(root.barBorderlessModes, value, "pills"));
    }

    function setBarGroupColor(value) {
        setValue("barGroupColor", normalizedOption(root.barGroupColorOptions, value, "layer1"));
    }

    function setBarShowAppIcons(value) {
        setValue("barShowAppIcons", !!value);
    }

    function setBarAlwaysShowNumbers(value) {
        setValue("barAlwaysShowNumbers", !!value);
    }

    function setBarWorkspaceIndicatorStyle(value) {
        setValue("barWorkspaceIndicatorStyle", normalizedOption(root.barWorkspaceIndicatorStyles, value, "dot"));
    }

    function setBarWorkspaceStyle(value) {
        setValue("barWorkspaceStyle", normalizedOption(root.barWorkspaceStyles, value, "default"));
    }

    function setBarWorkspaceShown(value) {
        const parsed = Math.round(Number(value));
        setValue("barWorkspaceShown", isFinite(parsed) ? Math.max(1, Math.min(50, parsed)) : 10);
    }

    function setBarWorkspaceNumberStyle(value) {
        setValue("barWorkspaceNumberStyle", normalizedOption(root.barWorkspaceNumberStyles, value, "normal"));
    }

    // Right-click style editor (BarGroupStylePopup) persistence. One entry per
    // (borderless mode, widget) pair, matching end4's `bar.widgetStyles` shape,
    // but owned here so the config store stays the single writer.
    function barWidgetStyleEntry(mode, widget) {
        if (!mode || !widget)
            return undefined;
        return (root.barWidgetStyles ?? []).find(entry => entry.mode === mode && entry.widget === widget);
    }

    function normalizedBarWidgetStyles(raw) {
        if (!Array.isArray(raw))
            return [];
        const modes = root.barBorderlessModes.map(option => option.value);
        const numericKeys = ["radius", "borderWidth", "padding"];
        const stringKeys = ["color", "borderColor"];
        const result = [];
        for (const candidate of raw) {
            if (!candidate || typeof candidate !== "object")
                continue;
            const mode = String(candidate.mode ?? "");
            const widget = String(candidate.widget ?? "");
            if (!modes.includes(mode) || widget === "")
                continue;
            const entry = {
                mode: mode,
                widget: widget
            };
            for (const key of numericKeys) {
                const value = candidate[key];
                if (typeof value === "number" && isFinite(value) && value >= 0)
                    entry[key] = value;
            }
            for (const key of stringKeys) {
                const value = candidate[key];
                if (typeof value === "string" && value !== "")
                    entry[key] = value;
            }
            result.push(entry);
        }
        return result;
    }

    function setBarWidgetStyle(mode, widget, key, value) {
        if (!mode || !widget)
            return;
        const styles = (root.barWidgetStyles ?? []).map(entry => Object.assign({}, entry));
        let entry = styles.find(candidate => candidate.mode === mode && candidate.widget === widget);
        if (!entry) {
            entry = {
                mode: mode,
                widget: widget
            };
            styles.push(entry);
        }
        if (value === undefined || value === "")
            delete entry[key];
        else
            entry[key] = value;
        setValue("barWidgetStyles", styles.filter(candidate => Object.keys(candidate).length > 2));
    }

    function resetBarWidgetStyle(mode, widget) {
        if (!mode || !widget)
            return;
        setValue("barWidgetStyles", (root.barWidgetStyles ?? []).filter(entry => !(entry.mode === mode && entry.widget === widget)));
    }

    function setBarDividerStyle(value) {
        setValue("barDividerStyle", normalizedOption(root.barDividerStyles, value, "rect"));
    }

    function normalizedBarComponents(raw, excluded) {
        const source = Array.isArray(raw) ? raw : [];
        const blocked = excluded || [];
        const result = [];
        for (let index = 0; index < source.length; index += 1) {
            const componentId = String(source[index] || "");
            if (root.barComponentIds.indexOf(componentId) === -1 || blocked.indexOf(componentId) !== -1 || result.indexOf(componentId) !== -1)
                continue;

            result.push(componentId);
        }
        return result;
    }

    function normalizedBarLayout(leading, trailing, useDefaults) {
        const normalizedLeading = root.normalizedBarComponents(useDefaults ? root.defaultBarLeadingComponents : leading, []);
        const normalizedTrailing = root.normalizedBarComponents(useDefaults ? root.defaultBarTrailingComponents : trailing, normalizedLeading);
        return {
            "leading": normalizedLeading,
            "trailing": normalizedTrailing
        };
    }

    function barZoneComponents(zone) {
        if (zone === "left" || zone === "leading")
            return root.barLayoutLeft;
        if (zone === "middle" || zone === "center")
            return root.barLayoutMiddle;
        if (zone === "right" || zone === "trailing")
            return root.barLayoutRight;
        return [];
    }

    function moveBarComponent(componentId, targetZone, targetIndex) {
        const id = String(componentId || "");
        if (root.barComponentIds.indexOf(id) === -1)
            return false;

        const leading = root.barLayoutLeft.filter(value => value !== id);
        const middle = root.barLayoutMiddle.filter(value => value !== id);
        const trailing = root.barLayoutRight.filter(value => value !== id);

        const target = (targetZone === "middle" || targetZone === "center") ? middle : (targetZone === "right" || targetZone === "trailing") ? trailing : leading;

        const numericIndex = Number(targetIndex);
        const insertionIndex = isFinite(numericIndex) ? Math.max(0, Math.min(target.length, Math.round(numericIndex))) : target.length;
        target.splice(insertionIndex, 0, id);

        root.barLayoutLeft = root.normalizedBarLayoutIds(leading);
        root.barLayoutMiddle = middle;
        root.barLayoutRight = root.normalizedBarLayoutIds(trailing);
        root.barLeadingComponents = root.barLayoutLeft.slice();
        root.barTrailingComponents = root.barLayoutRight.slice();
        root.save();
        return true;
    }

    function removeBarComponent(componentId) {
        const id = String(componentId || "");
        if (root.barComponentIds.indexOf(id) === -1)
            return false;

        const prevLen = root.barLayoutLeft.length + root.barLayoutMiddle.length + root.barLayoutRight.length;
        root.barLayoutLeft = root.barLayoutLeft.filter(value => value !== id);
        root.barLayoutMiddle = root.barLayoutMiddle.filter(value => value !== id);
        root.barLayoutRight = root.barLayoutRight.filter(value => value !== id);
        const nextLen = root.barLayoutLeft.length + root.barLayoutMiddle.length + root.barLayoutRight.length;
        if (prevLen === nextLen)
            return false;

        root.barLeadingComponents = root.barLayoutLeft.slice();
        root.barTrailingComponents = root.barLayoutRight.slice();
        root.save();
        return true;
    }

    function toggleBarComponent(componentId, zone) {
        const target = (zone === "middle" || zone === "center") ? root.barLayoutMiddle : (zone === "right" || zone === "trailing") ? root.barLayoutRight : root.barLayoutLeft;

        if (target.indexOf(componentId) !== -1)
            return root.removeBarComponent(componentId);

        return root.moveBarComponent(componentId, zone, target.length);
    }

    // The drag layout only accepts widgets the bar actually renders. The set is
    // exactly BarComponentLoader's dispatch table, so ids the project has not
    // implemented are rejected rather than silently stored and ignored.
    readonly property var barLayoutAllowedIds: root.barComponentIds

    function arraysEqual(first, second) {
        if (!Array.isArray(first) || !Array.isArray(second) || first.length !== second.length)
            return false;

        for (let i = 0; i < first.length; i += 1) {
            if (first[i] !== second[i])
                return false;
        }
        return true;
    }

    function normalizedBarLayoutIds(raw) {
        if (!Array.isArray(raw))
            return [];

        const seen = {};
        const out = [];
        raw.forEach(id => {
            const candidate = String(id || "");
            if (root.barLayoutAllowedIds.indexOf(candidate) === -1 || seen[candidate])
                return;

            seen[candidate] = true;
            out.push(candidate);
        });
        return out;
    }

    // Tray pin list: ids are opaque DBus names, so only blank/duplicate entries
    // are rejected here — validating against SystemTray.items would drop pins
    // for clients that are not running right now.
    // B9.7 screen filter: deduped non-empty monitor names. An empty array
    // means "every screen"; unknown names simply never match at the window
    // (Bar.qml falls back to all screens in that case).
    function normalizedScreenList(raw) {
        if (!Array.isArray(raw))
            return [];

        const seen = {};
        const out = [];
        raw.forEach(name => {
            const candidate = String(name || "").trim();
            if (candidate.length === 0 || seen[candidate])
                return;

            seen[candidate] = true;
            out.push(candidate);
        });
        return out;
    }

    function normalizedTrayPinnedItems(raw) {
        if (!Array.isArray(raw))
            return [];

        const seen = {};
        const out = [];
        raw.forEach(id => {
            const candidate = String(id || "").trim();
            if (candidate.length === 0 || seen[candidate])
                return;

            seen[candidate] = true;
            out.push(candidate);
        });
        return out;
    }

    function setBarTrayPinnedItems(value) {
        const next = root.normalizedTrayPinnedItems(value);
        if (root.arraysEqual(root.barTrayPinnedItems, next))
            return;
        root.barTrayPinnedItems = next;
        root.save();
    }

    // Orchestrated write for the three-lane bar layout. The UI calls this instead
    // of assigning the properties directly, so the schema change goes through the
    // settings backend and only persists when an array actually changed.
    function setBarThickness(value) {
        const numeric = Number(value);
        const clamped = isFinite(numeric) ? Math.max(28, Math.min(64, Math.round(numeric))) : root.defaultBarThickness;
        if (root.barThickness !== clamped) {
            root.barThickness = clamped;
            root.save();
        }
    }

    function setBarVerticalThickness(value) {
        const numeric = Number(value);
        const clamped = isFinite(numeric) ? Math.max(28, Math.min(64, Math.round(numeric))) : root.defaultBarVerticalThickness;
        if (root.barVerticalThickness !== clamped) {
            root.barVerticalThickness = clamped;
            root.save();
        }
    }

    function setBarEdgeMargin(value) {
        const clamped = root.normalizedBoundedInt(value, 0, 0, 48);
        if (root.barEdgeMargin !== clamped) {
            root.barEdgeMargin = clamped;
            root.save();
        }
    }

    function setBarSideMargin(value) {
        const clamped = root.normalizedBoundedInt(value, 0, 0, 96);
        if (root.barSideMargin !== clamped) {
            root.barSideMargin = clamped;
            root.save();
        }
    }

    function setBarLayouts(left, middle, right) {
        const nextLeft = root.normalizedBarLayoutIds(left);
        const nextMiddle = root.normalizedBarLayoutIds(middle);
        const nextRight = root.normalizedBarLayoutIds(right);
        let changed = false;
        if (!root.arraysEqual(nextLeft, root.barLayoutLeft)) {
            root.barLayoutLeft = nextLeft;
            changed = true;
        }
        if (!root.arraysEqual(nextMiddle, root.barLayoutMiddle)) {
            root.barLayoutMiddle = nextMiddle;
            changed = true;
        }
        if (!root.arraysEqual(nextRight, root.barLayoutRight)) {
            root.barLayoutRight = nextRight;
            changed = true;
        }
        if (changed) {
            root.barLeadingComponents = nextLeft.slice();
            const combinedTrailing = [];
            nextMiddle.forEach(id => {
                if (combinedTrailing.indexOf(id) === -1 && nextLeft.indexOf(id) === -1)
                    combinedTrailing.push(id);
            });
            nextRight.forEach(id => {
                if (combinedTrailing.indexOf(id) === -1 && nextLeft.indexOf(id) === -1)
                    combinedTrailing.push(id);
            });
            root.barTrailingComponents = combinedTrailing;
            root.save();
        }

        return changed;
    }

    function normalizedQuickSettingsComponents(raw) {
        const source = Array.isArray(raw) ? raw : root.defaultQuickSettingsComponents;
        const result = [];
        for (let index = 0; index < source.length; index += 1) {
            const componentId = String(source[index] || "");
            if (root.quickSettingsComponentIds.indexOf(componentId) === -1 || result.indexOf(componentId) !== -1)
                continue;

            result.push(componentId);
        }
        return result;
    }

    function moveQuickSettingsComponent(componentId, targetIndex) {
        const id = String(componentId || "");
        if (root.quickSettingsComponentIds.indexOf(id) === -1)
            return false;

        const components = root.normalizedQuickSettingsComponents(root.quickSettingsComponents).filter(value => {
            return value !== id;
        });
        const numericIndex = Number(targetIndex);
        const insertionIndex = isFinite(numericIndex) ? Math.max(0, Math.min(components.length, Math.round(numericIndex))) : components.length;
        components.splice(insertionIndex, 0, id);
        root.quickSettingsComponents = components;
        root.save();
        return true;
    }

    function removeQuickSettingsComponent(componentId) {
        const id = String(componentId || "");
        const components = root.quickSettingsComponents.filter(value => {
            return value !== id;
        });
        if (components.length === root.quickSettingsComponents.length)
            return false;

        root.quickSettingsComponents = root.normalizedQuickSettingsComponents(components);
        root.save();
        return true;
    }

    function toggleQuickSettingsComponent(componentId) {
        const id = String(componentId || "");
        if (root.quickSettingsComponents.indexOf(id) !== -1)
            return root.removeQuickSettingsComponent(id);

        return root.moveQuickSettingsComponent(id, root.quickSettingsComponents.length);
    }

    function setKeyboardIndicators(patch) {
        const allowed = {
            "showPopup": "keyboardShowPopup",
            "showPanel": "keyboardShowPanel",
            "popup.layout": "keyboardPopupLayout",
            "popup.caps": "keyboardPopupCaps",
            "popup.num": "keyboardPopupNum",
            "panel.layout": "keyboardPanelLayout",
            "panel.caps": "keyboardPanelCaps",
            "panel.num": "keyboardPanelNum"
        };
        for (const key in patch) {
            if (Object.prototype.hasOwnProperty.call(allowed, key))
                root[allowed[key]] = !!patch[key];
        }
        root.save();
    }

    function setKeyboardShowPopup(value) {
        root.setKeyboardIndicators({
            "showPopup": value
        });
    }

    function setKeyboardShowPanel(value) {
        root.setKeyboardIndicators({
            "showPanel": value
        });
    }

    function setKeyboardPopupLayout(value) {
        root.setKeyboardIndicators({
            "popup.layout": value
        });
    }

    function setKeyboardPopupCaps(value) {
        root.setKeyboardIndicators({
            "popup.caps": value
        });
    }

    function setKeyboardPopupNum(value) {
        root.setKeyboardIndicators({
            "popup.num": value
        });
    }

    function setKeyboardPanelLayout(value) {
        root.setKeyboardIndicators({
            "panel.layout": value
        });
    }

    function setKeyboardPanelCaps(value) {
        root.setKeyboardIndicators({
            "panel.caps": value
        });
    }

    function setKeyboardPanelNum(value) {
        root.setKeyboardIndicators({
            "panel.num": value
        });
    }

    function setBarShowNames(value) {
        setValue("barShowNames", !!value);
    }

    function setBarShowValues(value) {
        setValue("barShowValues", !!value);
    }

    function setIslandHideDate(value) {
        setValue("islandHideDate", !!value);
    }

    function setHorizontalClockFontSize(value, persist) {
        const next = root.normalizedBoundedInt(value, 22, 16, 28);
        if (root.horizontalClockFontSize === next) {
            if (persist !== false)
                root.save();

            return;
        }
        root.horizontalClockFontSize = next;
        if (persist !== false)
            root.save();
    }

    function setHorizontalClockAxis(axis, value, persist) {
        const name = String(axis || "");
        if (root.horizontalClockAxisDefaults[name] === undefined)
            return;

        const next = root.normalizedBoundedReal(value, root.horizontalClockAxisDefaults[name], root.horizontalClockAxisMinimums[name], root.horizontalClockAxisMaximums[name]);
        const current = root.horizontalClockAxes[name];
        if (current === next) {
            if (persist !== false)
                root.save();

            return;
        }
        const axes = root.cloneMap(root.horizontalClockAxes);
        axes[name] = next;
        root.horizontalClockAxes = root.normalizedHorizontalClockAxes(axes);
        if (persist !== false)
            root.save();
    }

    function setHorizontalClockDigitValue(id, field, value, persist) {
        const name = String(id || "");
        const propertyName = String(field || "");
        const fallback = root.horizontalClockDigitDefaults[name];
        if (!fallback || ["x", "y", "rotation"].indexOf(propertyName) === -1)
            return;

        const limits = propertyName === "x" ? [-8, 8] : propertyName === "y" ? [-6, 6] : [-12, 12];
        const current = root.horizontalClockDigit(name);
        const next = root.normalizedBoundedInt(value, fallback[propertyName], limits[0], limits[1]);
        if (current[propertyName] === next) {
            if (persist !== false)
                root.save();

            return;
        }
        const digits = root.normalizedHorizontalClockDigits(root.horizontalClockDigits);
        digits[name][propertyName] = next;
        root.horizontalClockDigits = digits;
        if (persist !== false)
            root.save();
    }

    function setHorizontalClockDigitColor(id, role, customColor, persist) {
        const name = String(id || "");
        const fallback = root.horizontalClockDigitDefaults[name];
        if (!fallback)
            return;

        const candidateRole = String(role || "");
        const normalizedColor = String(customColor || "").trim().toLowerCase();
        const customValid = /^#([0-9a-f]{6}|[0-9a-f]{8})$/.test(normalizedColor);
        const validRole = ["primary", "inversePrimary"].indexOf(candidateRole) !== -1;
        const useCandidate = validRole || (candidateRole === "custom" && customValid);
        const nextRole = useCandidate ? candidateRole : fallback.colorRole;

        const digits = root.normalizedHorizontalClockDigits(root.horizontalClockDigits);
        digits[name].colorRole = nextRole;
        digits[name].customColor = customValid ? normalizedColor : "";
        root.horizontalClockDigits = digits;
        if (persist !== false)
            root.save();
    }

    function toJson() {
        return {
            "wallpaper": {
                "bannerSource": root.bannerSource,
                "folder": root.wallpaperFolder,
                "path": root.wallpaperPath,
                "pathLight": root.wallpaperPathLight,
                "pathDark": root.wallpaperPathDark,
                "perMode": root.perModeWallpaper,
                "perMonitor": root.perMonitorWallpaper,
                "monitorWallpapers": root.monitorWallpapers,
                "monitorFillModes": root.monitorWallpaperFillModes,
                "recentColors": root.recentWallpaperColors,
                "fillMode": root.wallpaperFillMode,
                "desktopBackend": root.desktopWallpaperBackend,
                "autoCycle": {
                    "enabled": root.autoCycleEnabled,
                    "mode": root.autoCycleMode,
                    "interval": root.autoCycleInterval,
                    "time": root.autoCycleTime
                },
                "transition": {
                    "type": root.wallpaperTransitionType,
                    "included": root.includedTransitions,
                    "durationMs": root.transitionDurationMs,
                    "easingMode": root.transitionEasingMode,
                    "bezierCurve": root.transitionBezierCurve
                },
                "overview": {
                    "enabled": root.overviewEnabled,
                    "useDesktopWallpaper": root.overviewUseDesktopWallpaper,
                    "path": root.overviewWallpaperPath,
                    "fillMode": root.overviewWallpaperFillMode,
                    "perMonitor": root.overviewPerMonitorWallpaper,
                    "monitorWallpapers": root.overviewMonitorWallpapers,
                    "monitorFillModes": root.overviewMonitorFillModes,
                    "transitionType": root.overviewTransitionType,
                    "blurRadius": root.overviewBlurRadius,
                    "dim": root.overviewDim,
                    "saturation": root.overviewSaturation,
                    "contrast": root.overviewContrast
                },
                "parallax": {
                    "verticalEnabled": root.parallaxVerticalEnabled,
                    "followWorkspaces": root.parallaxFollowWorkspaces,
                    "followSidebars": root.parallaxFollowSidebars,
                    "followTiledColumns": root.parallaxFollowTiledColumns,
                    "preferredScale": root.parallaxPreferredScale,
                    "tiledColumnSpan": root.parallaxTiledColumnSpan
                }
            },
            "theme": {
                "matugenScheme": root.matugenScheme,
                "matugenTemplates": root.normalizedMatugenTemplates(root.matugenTemplates),
                "mode": root.themeMode,
                "superKeyStyle": root.superKeyStyle,
                "lockScreenStyle": root.lockScreenStyle,
                "settingsPanelStyle": root.settingsPanelStyle,
                "lyricSource": root.lyricSource,
                "lyricOffsetMs": root.lyricOffsetMs,
                "lyricFontSize": root.lyricFontSize,
                "lyricAlbumArtTint": root.lyricAlbumArtTint,
                "lyricShowTranslation": root.lyricShowTranslation,
                "cursorTheme": root.cursorTheme,
                "cursorSize": root.cursorSize,
                "cursorHideWhenTyping": root.cursorHideWhenTyping,
                "cursorHideAfterInactiveMs": root.cursorHideAfterInactiveMs,
                "iconTheme": root.iconTheme,
                "fonts": {
                    "ui": root.uiFontFamily,
                    "mono": root.monoFontFamily,
                    "numeric": root.numericFontFamily,
                    "expressive": root.expressiveFontFamily
                }
            },
            "effects": {
                "shellBackgroundOpacity": root.shellBackgroundOpacity,
                "shellBlurEnabled": root.shellBlurEnabled,
                "shellBlurXray": root.shellBlurXray
            },
            "keyboardIndicators": {
                "showPopup": root.keyboardShowPopup,
                "showPanel": root.keyboardShowPanel,
                "popup": {
                    "layout": root.keyboardPopupLayout,
                    "caps": root.keyboardPopupCaps,
                    "num": root.keyboardPopupNum
                },
                "panel": {
                    "layout": root.keyboardPanelLayout,
                    "caps": root.keyboardPanelCaps,
                    "num": root.keyboardPanelNum
                }
            },
            "island": {
                "satellite": root.islandSatellite,
                "layoutMigrated": root.islandLayoutMigrated,
                "hideDate": root.islandHideDate,
                "showAvatar": root.islandShowAvatar,
                "horizontalClock": {
                    "fontSize": root.horizontalClockFontSize,
                    "axes": root.cloneMap(root.horizontalClockAxes),
                    "digits": root.horizontalClockDigits
                }
            },
            "bar": {
                "position": root.barPosition,
                "autoHide": root.barAutoHide,
                "screenList": root.barScreenList.slice(),
                "showBackground": root.barShowBackground,
                "cornerStyle": root.barCornerStyle,
                "borderless": root.barBorderless,
                "groupColor": root.barGroupColor,
                "widgetStyles": root.barWidgetStyles.map(entry => Object.assign({}, entry)),
                "dividerStyle": root.barDividerStyle,
                "dividerSpacing": root.barDividerSpacing,
                "showAppIcons": root.barShowAppIcons,
                "alwaysShowNumbers": root.barAlwaysShowNumbers,
                "workspaceIndicatorStyle": root.barWorkspaceIndicatorStyle,
                "workspaceStyle": root.barWorkspaceStyle,
                "workspaceShown": root.barWorkspaceShown,
                "numberStyle": root.barWorkspaceNumberStyle,
                "utilButtons": {
                    "showScreenSnip": root.barShowScreenSnip,
                    "showColorPicker": root.barShowColorPicker,
                    "showKeyboardToggle": root.barShowKeyboardToggle,
                    "showMicToggle": root.barShowMicToggle,
                    "showWallpaperToggle": root.barShowWallpaperToggle,
                    "showDarkModeToggle": root.barShowDarkModeToggle,
                    "showPerformanceProfile": root.barShowPerformanceProfile
                },
                "resources": {
                    "alwaysShowCpu": root.barShowCpu,
                    "alwaysShowCpuTemp": root.barShowCpuTemp,
                    "alwaysShowRam": root.barShowRam,
                    "alwaysShowDisk": root.barShowDisk,
                    "alwaysShowSwap": root.barShowSwap,
                    "style": root.barResourceStyle,
                    "showValue": root.barResourceShowValue
                },
                "showValues": root.barShowValues,
                "showNames": root.barShowNames,
                "barLeadingComponents": root.barLeadingComponents.slice(),
                "barTrailingComponents": root.barTrailingComponents.slice(),
                "barLayoutLeft": root.barLayoutLeft.slice(),
                "barLayoutMiddle": root.barLayoutMiddle.slice(),
                "barLayoutRight": root.barLayoutRight.slice(),
                "barThickness": root.barThickness,
                "verticalThickness": root.barVerticalThickness,
                "edgeMargin": root.barEdgeMargin,
                "sideMargin": root.barSideMargin,
                "quickSettingsComponents": root.quickSettingsComponents.slice(),
                "tray": {
                    "pinnedItems": root.barTrayPinnedItems.slice(),
                    "filterPassive": root.barTrayFilterPassive,
                    "invertPinnedItems": root.barTrayInvertPinnedItems,
                    "showItemId": root.barTrayShowItemId,
                    "monochromeIcons": root.barTrayMonochromeIcons
                }
            },
            "sidebar": {
                "keepLoaded": root.keepSidebarsLoaded,
                "dashboardSide": root.dashboardSidebarSide,
                "quickSettingsSide": root.quickSettingsSidebarSide
            },
            "hotCorners": root.normalizedHotCornerActions(root.hotCornerActions),
            "desktopCards": {
                "gridSnapEnabled": root.desktopCardGridSnapEnabled,
                "gridVisibleWhileDragging": root.desktopCardGridVisibleWhileDragging
            }
        };
    }

    function configSection(value) {
        return value && typeof value === "object" && !Array.isArray(value) ? value : {};
    }

    // B9.3: pure layout resolution (one-shot seed + legacy island gate).
    // Kept side-effect free so scripts/dev/probe-bar.sh can prove the
    // migration keys without mutating the live store.
    function resolveBarLayouts(bar, island, legacyIslandEnabled) {
        const hasBarLayout = Array.isArray(bar.barLeadingComponents) || Array.isArray(bar.barTrailingComponents);
        const hasBarLayouts = "barLayoutLeft" in bar || "barLayoutMiddle" in bar || "barLayoutRight" in bar;
        const islandMigrated = island.layoutMigrated === true;
        let left;
        let middle;
        let right;
        if (hasBarLayouts) {
            left = root.normalizedBarLayoutIds(bar.barLayoutLeft);
            middle = root.normalizedBarLayoutIds(bar.barLayoutMiddle);
            right = root.normalizedBarLayoutIds(bar.barLayoutRight);
            // B3-1 one-shot seed: seed the island exactly once, then the user's
            // own choices win (B9.3 fixed the key this reads).
            if (!islandMigrated && middle.length === 0)
                middle = ["island"];
            const leading = root.normalizedBarLayoutIds(bar.barLeadingComponents);
            const trailing = root.normalizedBarLayoutIds(bar.barTrailingComponents);
            if (!root.arraysEqual(leading, left) && hasBarLayout) {
                left = leading;
                right = trailing;
            }
        } else {
            // Legacy configs only had leading/trailing zones; map them 1:1 so
            // an upgrade does not reshuffle the user's bar.
            left = root.normalizedBarLayoutIds(bar.barLeadingComponents);
            middle = root.defaultBarLayoutMiddle.slice();
            right = root.normalizedBarLayoutIds(bar.barTrailingComponents);
        }
        if (!legacyIslandEnabled) {
            left = left.filter(id => id !== "island");
            middle = middle.filter(id => id !== "island");
            right = right.filter(id => id !== "island");
        }
        return {
            "left": left,
            "middle": middle,
            "right": right,
            "migrated": islandMigrated || !legacyIslandEnabled
        };
    }

    function loadFromObject(parsed) {
        const source = configSection(parsed);
        const wallpaper = configSection(source.wallpaper);
        const theme = configSection(source.theme);
        const effects = configSection(source.effects);
        const island = configSection(source.island);
        const keyboard = configSection(source.keyboardIndicators);
        const keyboardPopup = configSection(keyboard.popup);
        const keyboardPanel = configSection(keyboard.panel);
        const bar = configSection(source.bar);
        const tray = configSection(bar.tray);
        const sidebar = configSection(source.sidebar);
        const desktopCards = configSection(source.desktopCards);
        const transition = configSection(wallpaper.transition);
        const overview = configSection(wallpaper.overview);
        const parallax = configSection(wallpaper.parallax);
        const autoCycle = configSection(wallpaper.autoCycle);
        const fonts = configSection(theme.fonts);
        const horizontalClock = configSection(island.horizontalClock);
        root.bannerSource = typeof wallpaper.bannerSource === "string" ? wallpaper.bannerSource : "";
        root.wallpaperFolder = typeof wallpaper.folder === "string" && wallpaper.folder !== "" ? wallpaper.folder : Paths.dataHome + "/wallpapers";
        const wallpaperPath = typeof wallpaper.path === "string" ? wallpaper.path : "";
        root.wallpaperPath = wallpaperPath === Paths.currentWallpaper ? "" : wallpaperPath;
        root.wallpaperPathLight = typeof wallpaper.pathLight === "string" ? wallpaper.pathLight : "";
        root.wallpaperPathDark = typeof wallpaper.pathDark === "string" ? wallpaper.pathDark : "";
        root.perModeWallpaper = !!wallpaper.perMode;
        root.perMonitorWallpaper = !!wallpaper.perMonitor;
        root.monitorWallpapers = normalizedStringMap(wallpaper.monitorWallpapers);
        root.monitorWallpaperFillModes = normalizedFillModeMap(wallpaper.monitorFillModes);
        root.recentWallpaperColors = normalizedRecentColors(wallpaper.recentColors);
        root.wallpaperFillMode = normalizedOption(root.desktopFillModes, wallpaper.fillMode, "Fill");
        root.desktopWallpaperBackend = "quickshell";
        root.autoCycleEnabled = !!autoCycle.enabled;
        root.autoCycleMode = autoCycle.mode === "time" ? "time" : "interval";
        root.autoCycleInterval = Math.max(5, Math.round(Number(autoCycle.interval) || 300));
        const validTime = /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/.test(autoCycle.time || "");
        root.autoCycleTime = validTime ? autoCycle.time : "06:00";

        root.wallpaperTransitionType = normalizedTransition(transition.type || "fade");
        root.includedTransitions = normalizedIncluded(transition.included);
        root.transitionDurationMs = normalizedDurationMs(transition.durationMs, 1000);
        root.transitionEasingMode = normalizedEasingMode(transition.easingMode || "customBezier");
        root.transitionBezierCurve = normalizedBezier(transition.bezierCurve);
        root.overviewEnabled = overview.enabled === undefined ? true : !!overview.enabled;
        root.overviewUseDesktopWallpaper = overview.useDesktopWallpaper === undefined ? true : !!overview.useDesktopWallpaper;
        root.overviewWallpaperPath = String(overview.path || "");
        root.overviewWallpaperFillMode = normalizedOption(root.fillModes, overview.fillMode, "Fill");
        root.overviewPerMonitorWallpaper = !!overview.perMonitor;
        root.overviewMonitorWallpapers = normalizedStringMap(overview.monitorWallpapers);
        root.overviewMonitorFillModes = normalizedFillModeMap(overview.monitorFillModes, root.fillModes);
        root.overviewTransitionType = normalizedTransition(overview.transitionType || "fade");
        root.overviewBlurRadius = normalizedBoundedReal(overview.blurRadius, 0, 0, 100);
        root.overviewDim = normalizedBoundedReal(overview.dim, 0, 0, 1);
        root.overviewSaturation = normalizedBoundedReal(overview.saturation, 1, 0, 2);
        root.overviewContrast = normalizedBoundedReal(overview.contrast, 1, 0.5, 2);
        root.parallaxVerticalEnabled = !!parallax.verticalEnabled;
        root.parallaxFollowWorkspaces = parallax.followWorkspaces === undefined ? true : !!parallax.followWorkspaces;
        root.parallaxFollowSidebars = !!parallax.followSidebars;
        root.parallaxFollowTiledColumns = !!parallax.followTiledColumns;
        root.parallaxPreferredScale = normalizedBoundedReal(parallax.preferredScale, 1.1, 1, 1.35);
        root.parallaxTiledColumnSpan = normalizedBoundedInt(parallax.tiledColumnSpan, 6, 2, 12);
        root.matugenScheme = normalizedOption(root.matugenSchemes, theme.matugenScheme, "scheme-tonal-spot");
        root.matugenTemplates = normalizedMatugenTemplates(theme.matugenTemplates);
        root.lockScreenStyle = normalizedOption(root.lockScreenStyles, theme.lockScreenStyle, "default");
        root.settingsPanelStyle = normalizedOption(root.settingsPanelStyles, theme.settingsPanelStyle, "default");
        root.lyricSource = normalizedOption(root.lyricSources, theme.lyricSource, "kugou");
        root.lyricOffsetMs = normalizedBoundedInt(theme.lyricOffsetMs, 0, root.lyricOffsetMinMs, root.lyricOffsetMaxMs);
        root.lyricFontSize = normalizedBoundedInt(theme.lyricFontSize, 26, root.lyricFontSizeMin, root.lyricFontSizeMax);
        root.lyricAlbumArtTint = theme.lyricAlbumArtTint === true;
        // Absent in older configs; default to on rather than mirroring the
        // `=== true` pattern used above, which would read a missing key as off.
        root.lyricShowTranslation = theme.lyricShowTranslation !== false;
        root.themeMode = theme.mode === "light" ? "light" : "dark";
        root.superKeyStyle = root.superKeyStyles.some(style => style.value === theme.superKeyStyle) ? theme.superKeyStyle : "text";
        root.cursorTheme = root.normalizedCursorTheme(theme.cursorTheme);
        root.cursorSize = root.normalizedBoundedInt(theme.cursorSize, 24, 12, 128);
        root.cursorHideWhenTyping = typeof theme.cursorHideWhenTyping === "boolean" ? theme.cursorHideWhenTyping : false;
        root.cursorHideAfterInactiveMs = root.normalizedBoundedInt(theme.cursorHideAfterInactiveMs, 0, 0, 5000);
        root.iconTheme = typeof theme.iconTheme === "string" ? theme.iconTheme : "";
        FontService.setConfiguredFamilies(fonts.ui, fonts.mono, fonts.numeric, fonts.expressive);
        root.shellBackgroundOpacity = normalizedBoundedReal(effects.shellBackgroundOpacity, 1, 0, 1);
        root.shellBlurEnabled = typeof effects.shellBlurEnabled === "boolean" ? effects.shellBlurEnabled : false;
        root.shellBlurXray = typeof effects.shellBlurXray === "boolean" ? effects.shellBlurXray : true;
        // B9.3 legacy read: `enabled=false` used to hide the island while the
        // layout still listed it. It is applied once after layout resolution;
        // membership is the only truth from then on.
        const legacyIslandEnabled = typeof island.enabled === "boolean" ? island.enabled : true;
        root.islandSatellite = normalizedOption(root.islandSatelliteOptions, island.satellite, "clock");
        root.islandLayoutMigrated = island.layoutMigrated === true;
        root.islandHideDate = typeof island.hideDate === "boolean" ? island.hideDate : false;
        root.islandShowAvatar = typeof island.showAvatar === "boolean" ? island.showAvatar : true;
        // iNiR keyboardIndicators block; the old island.capsLockOsd/numLockOsd
        // pair migrates to popup.caps/num so an existing choice is not lost.
        root.keyboardShowPopup = typeof keyboard.showPopup === "boolean" ? keyboard.showPopup : true;
        root.keyboardShowPanel = typeof keyboard.showPanel === "boolean" ? keyboard.showPanel : true;
        root.keyboardPopupLayout = typeof keyboardPopup.layout === "boolean" ? keyboardPopup.layout : true;
        root.keyboardPopupCaps = typeof keyboardPopup.caps === "boolean" ? keyboardPopup.caps : (typeof island.capsLockOsd === "boolean" ? island.capsLockOsd : true);
        root.keyboardPopupNum = typeof keyboardPopup.num === "boolean" ? keyboardPopup.num : (typeof island.numLockOsd === "boolean" ? island.numLockOsd : false);
        root.keyboardPanelLayout = typeof keyboardPanel.layout === "boolean" ? keyboardPanel.layout : true;
        root.keyboardPanelCaps = typeof keyboardPanel.caps === "boolean" ? keyboardPanel.caps : true;
        root.keyboardPanelNum = typeof keyboardPanel.num === "boolean" ? keyboardPanel.num : false;
        root.horizontalClockFontSize = root.normalizedBoundedInt(horizontalClock.fontSize, 22, 16, 28);
        root.horizontalClockAxes = root.normalizedHorizontalClockAxes(horizontalClock.axes);
        root.horizontalClockDigits = root.normalizedHorizontalClockDigits(horizontalClock.digits);
        root.barShowValues = typeof bar.showValues === "boolean" ? bar.showValues : typeof bar.showMonitorValues === "boolean" ? bar.showMonitorValues : true;
        root.barShowNames = typeof bar.showNames === "boolean" ? bar.showNames : false;
        root.barPosition = normalizedEdgePosition(bar.position);
        root.barAutoHide = bar.autoHide === true;
        root.barScreenList = root.normalizedScreenList(bar.screenList);
        root.barShowBackground = typeof bar.showBackground === "boolean" ? bar.showBackground : true;
        root.barCornerStyle = root.normalizedBoundedInt(bar.cornerStyle, 1, 0, 5);
        root.barBorderless = root.normalizedOption(root.barBorderlessModes, bar.borderless, "pills");
        root.barGroupColor = normalizedOption(root.barGroupColorOptions, bar.groupColor, "layer1");
        root.barWidgetStyles = root.normalizedBarWidgetStyles(bar.widgetStyles);
        root.barDividerStyle = root.normalizedOption(root.barDividerStyles, bar.dividerStyle, "rect");
        root.barDividerSpacing = typeof bar.dividerSpacing === "number" ? Math.max(4, Math.min(400, Math.round(bar.dividerSpacing / 2) * 2)) : 4;
        root.barShowAppIcons = typeof bar.showAppIcons === "boolean" ? bar.showAppIcons : false;
        root.barAlwaysShowNumbers = typeof bar.alwaysShowNumbers === "boolean" ? bar.alwaysShowNumbers : true;
        root.barWorkspaceIndicatorStyle = normalizedOption(root.barWorkspaceIndicatorStyles, bar.workspaceIndicatorStyle, "dot");
        root.barWorkspaceStyle = normalizedOption(root.barWorkspaceStyles, bar.workspaceStyle, "default");
        root.barWorkspaceShown = typeof bar.workspaceShown === "number" ? Math.max(1, Math.min(50, Math.round(bar.workspaceShown))) : 10;
        root.barWorkspaceNumberStyle = normalizedOption(root.barWorkspaceNumberStyles, bar.numberStyle, "normal");
        const utilButtons = configSection(bar.utilButtons);
        root.barShowScreenSnip = typeof utilButtons.showScreenSnip === "boolean" ? utilButtons.showScreenSnip : true;
        root.barShowColorPicker = typeof utilButtons.showColorPicker === "boolean" ? utilButtons.showColorPicker : true;
        root.barShowKeyboardToggle = utilButtons.showKeyboardToggle === true;
        root.barShowMicToggle = utilButtons.showMicToggle === true;
        root.barShowWallpaperToggle = utilButtons.showWallpaperToggle === true;
        root.barShowDarkModeToggle = typeof utilButtons.showDarkModeToggle === "boolean" ? utilButtons.showDarkModeToggle : true;
        root.barShowPerformanceProfile = utilButtons.showPerformanceProfile === true;
        const resources = configSection(bar.resources);
        root.barShowCpu = typeof resources.alwaysShowCpu === "boolean" ? resources.alwaysShowCpu : true;
        root.barShowCpuTemp = resources.alwaysShowCpuTemp === true;
        root.barShowRam = typeof resources.alwaysShowRam === "boolean" ? resources.alwaysShowRam : true;
        root.barShowDisk = resources.alwaysShowDisk === true;
        root.barShowSwap = resources.alwaysShowSwap === true;
        root.barResourceStyle = normalizedOption(root.barResourceStyles, resources.style, "outline");
        root.barResourceShowValue = resources.showValue === true;
        root.barThickness = typeof bar.barThickness === "number" ? Math.max(28, Math.min(64, Math.round(bar.barThickness))) : root.defaultBarThickness;
        root.barVerticalThickness = typeof bar.verticalThickness === "number" ? Math.max(28, Math.min(64, Math.round(bar.verticalThickness))) : root.defaultBarVerticalThickness;
        root.barEdgeMargin = typeof bar.edgeMargin === "number" ? Math.max(0, Math.min(48, Math.round(bar.edgeMargin))) : 0;
        root.barSideMargin = typeof bar.sideMargin === "number" ? Math.max(0, Math.min(96, Math.round(bar.sideMargin))) : 0;
        root.barTrayPinnedItems = root.normalizedTrayPinnedItems(tray.pinnedItems);
        root.barTrayFilterPassive = typeof tray.filterPassive === "boolean" ? tray.filterPassive : true;
        // Absent keys must keep the shipped defaults (on, not off): `=== true`
        // would read a fresh config as "do not pin" and "do not tint".
        root.barTrayInvertPinnedItems = typeof tray.invertPinnedItems === "boolean" ? tray.invertPinnedItems : true;
        root.barTrayShowItemId = tray.showItemId === true;
        root.barTrayMonochromeIcons = typeof tray.monochromeIcons === "boolean" ? tray.monochromeIcons : true;
        const hasBarLayout = Array.isArray(bar.barLeadingComponents) || Array.isArray(bar.barTrailingComponents);
        const barLayout = root.normalizedBarLayout(bar.barLeadingComponents, bar.barTrailingComponents, !hasBarLayout);
        root.barLeadingComponents = barLayout.leading;
        root.barTrailingComponents = barLayout.trailing;
        const barLayouts = root.resolveBarLayouts(bar, island, legacyIslandEnabled);
        root.barLayoutLeft = barLayouts.left;
        root.barLayoutMiddle = barLayouts.middle;
        root.barLayoutRight = barLayouts.right;
        // The one-shot marker keeps a deliberately empty middle lane empty; a
        // fresh/legacy config without the key arms it after this load.
        if (barLayouts.migrated || typeof island.layoutMigrated !== "boolean")
            root.islandLayoutMigrated = true;
        root.quickSettingsComponents = root.normalizedQuickSettingsComponents(bar.quickSettingsComponents);
        root.keepSidebarsLoaded = sidebar.keepLoaded === undefined ? true : !!sidebar.keepLoaded;
        root.sidebarPositions = SidebarPolicy.restoredPositions(sidebar);
        root.hotCornerActions = root.normalizedHotCornerActions(source.hotCorners);
        root.desktopCardGridSnapEnabled = desktopCards.gridSnapEnabled === undefined ? true : !!desktopCards.gridSnapEnabled;
        root.desktopCardGridVisibleWhileDragging = desktopCards.gridVisibleWhileDragging === undefined ? true : !!desktopCards.gridVisibleWhileDragging;
    }

    function needsScrollingMigration(parsed) {
        return !!(parsed && parsed.interactions !== undefined);
    }

    function needsWallpaperMigration(parsed) {
        const wallpaper = parsed && parsed.wallpaper;
        if (!wallpaper || typeof wallpaper !== "object")
            return true;

        return wallpaper.overview === undefined || wallpaper.parallax === undefined;
    }

    function needsEffectsMigration(parsed) {
        const effects = parsed && parsed.effects;
        if (!effects || typeof effects !== "object" || Array.isArray(effects))
            return true;

        return effects.shellBackgroundOpacity === undefined || effects.shellBlurEnabled === undefined || effects.shellBlurXray === undefined;
    }

    function needsThemeMigration(parsed) {
        const theme = parsed && parsed.theme;
        return !theme || typeof theme !== "object" || Array.isArray(theme) || theme.matugenTemplates === undefined || theme.fonts === undefined;
    }

    function needsEdgePositionMigration(parsed) {
        const bar = parsed && parsed.bar;
        const island = parsed && parsed.island;
        return !bar || typeof bar !== "object" || Array.isArray(bar) || bar.position !== root.normalizedEdgePosition(bar.position);
    }

    function commitPalette(scope, source) {
        if (!scope || ["desktop", "overview", "banner"].indexOf(scope.target) < 0 || ["path", "pathLight", "pathDark"].indexOf(scope.field) < 0 || !root.storeReady || root.loading || !WallpaperSource.decode(source))
            return false;
        const candidate = JSON.parse(JSON.stringify(root.toJson()));
        const section = scope.target === "overview" ? candidate.wallpaper.overview : candidate.wallpaper;
        if (scope.target === "banner")
            section.bannerSource = source;
        else if (scope.monitor)
            section.monitorWallpapers[scope.monitor] = source;
        else
            section[scope.field] = source;
        const seed = WallpaperSource.primary(source);
        candidate.wallpaper.recentColors = root.normalizedRecentColors([seed].concat(root.recentWallpaperColors));
        ConfigService.updateSections(candidate);
        ConfigService.saveNow();

        // Publish only after the atomic write succeeded. No normal setters,
        // extra writes, or theme generation are involved in this operation.
        if (scope.target === "banner") {
            root.bannerSource = source;
        } else if (scope.monitor) {
            const propertyName = scope.target === "overview" ? "overviewMonitorWallpapers" : "monitorWallpapers";
            const next = root.cloneMap(root[propertyName]);
            next[scope.monitor] = source;
            root[propertyName] = next;
        } else {
            const propertyName = scope.target === "overview" ? "overviewWallpaperPath" : scope.field === "pathLight" ? "wallpaperPathLight" : scope.field === "pathDark" ? "wallpaperPathDark" : "wallpaperPath";
            root[propertyName] = source;
        }
        root.recentWallpaperColors = candidate.wallpaper.recentColors;
        return true;
    }

    function save() {
        if (!root.storeReady || root.loading)
            return;

        ConfigService.updateSections(root.toJson());
    }

    Connections {
        target: ConfigService
        function onConfigLoaded() {
            root.loading = true;
            root.loadFromObject(ConfigService.rawConfig);
            root.loading = false;
            root.loaded = true;
            root.settingsLoaded();
        }
    }

    Component.onCompleted: {
        if (ConfigService.storeReady) {
            root.loading = true;
            root.loadFromObject(ConfigService.rawConfig);
            root.loading = false;
            root.loaded = true;
            root.settingsLoaded();
        }
    }
}
