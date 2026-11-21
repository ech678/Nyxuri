pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons
import "../commons/SidebarPolicy.js" as SidebarPolicy
import "../commons/WallpaperSource.js" as WallpaperSource
import "BarWidgetDefaults.js" as BarWidgetDefaults
import "BarDefaults.js" as BarDefaults
import "ConfigMigrations.js" as ConfigMigrations
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
    // Set when the version chain migrated the parsed file (D4a); the load
    // completion path saves once so the stamp and the reshaped keys land.
    property bool configVersionDirty: false
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
    // B-10: the island media face unfreezes the end4 control set — playback
    // buttons plus a visualizer style. end4 defaults: controls off, dots;
    // cava runs only while the media face is visible and playing.
    property bool islandShowMediaControls: false
    property string islandVisualizerStyle: "dots"
    readonly property var islandVisualizerStyleOptions: [
        {
            "value": "dots",
            "label": I18n.tr("Dots"),
            "icon": "more_horiz"
        },
        {
            "value": "wave",
            "label": I18n.tr("Wave"),
            "icon": "show_chart"
        },
        {
            "value": "none",
            "label": I18n.tr("None"),
            "icon": "block"
        }
    ]
    // B3-1 one-shot marker: seed the middle lane with the island exactly once.
    property bool islandLayoutMigrated: false
    // D4c: the bar-level axes live on the [[bar.configs]] entry
    // (normalizeBarAxes); the properties below are derived views so every
    // existing consumer (Config bridge, Bar window, popups) keeps its read
    // path. Setters write through withBarConfigs — nothing assigns these.
    readonly property string barPosition: root.activeBarConfig().axes.position
    // B9.7 settled keys. `barAutoHide` drives the slide-out window;
    // pushWindows / hoverRegionWidth / super-reveal stay internal bridge
    // defaults — consumed, but not user-visible surface.
    readonly property bool barAutoHide: root.activeBarConfig().axes.autoHide
    // Screen filter for the bar windows. Empty list = every screen (end4
    // semantics); names come from Quickshell.screens.
    readonly property var barScreenList: root.activeBarConfig().axes.screenList
    // end4 `bar.showBackground`: the frame/pill background of non-material
    // styles. Only Hug/Float expose it; other styles ignore it downstream.
    readonly property bool barShowBackground: root.activeBarConfig().axes.showBackground
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
    readonly property int barCornerStyle: root.activeBarConfig().axes.cornerStyle
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
        },
        {
            // D4c: bare widgets, no capsule geometry at all ("transparent"
            // keeps the capsule shape with a transparent fill).
            value: "flat",
            label: I18n.tr("Flat")
        }
    ]
    readonly property string barBorderless: root.activeBarConfig().axes.borderless
    readonly property string barGroupColor: root.activeBarConfig().axes.groupColor
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
    // Per-widget style overrides (right-click style editor) ride the lane
    // entries themselves since D4c (plain entry overrides: color /
    // borderColor / radius / borderWidth / padding). The pre-D4c
    // per-(mode, widget) barWidgetStyles array folded onto the entries in
    // the v5 migration; the per-mode dimension retired with it.
    // Tray contract (ROADMAP B9.1). Pinning is tray-domain shared STATE, not
    // a per-instance aesthetic: pinned ids keep a permanent slot, and
    // invertPinnedItems swaps the two groups (the stored list is the hidden
    // set). The per-instance tray axes (tintIcons/hidePassive/showItemId)
    // moved to lane-entry overrides (D4b, BarWidgetDefaults.tray).
    property var barTrayPinnedItems: []
    property bool barTrayInvertPinnedItems: true
    // Quickpanel data rows (B9.7): the utility buttons' hover popouts show
    // numeric values / device names. Global to the popouts (one data shape
    // across all buttons), so they stay flat [bar] keys — the UI entry
    // rides the utility buttons options page (D4b).
    property bool barShowValues: true
    property bool barShowNames: false
    // D4b: the resources/workspace/divider/tray per-instance axes (meters,
    // icon style, skins, indicator shape, divider style, tint...) moved to
    // lane-entry overrides — see BarWidgetDefaults.DEFAULTS and the
    // ConfigMigrations v4 step that folds the old flat [bar] keys onto the
    // entries. The option vocabularies live with their options pages
    // (plugins/bar/options/).
    // Only ids the bar can actually render. The whitelist lives in
    // BarWidgetDefaults.IDS (D4a registration point 1 of 3) and must match
    // shell/ui/BarWidgetCatalog.qml and shell/plugins/bar/BarWidgetFiles.js
    // — tests/shell/test_d4a_bar_config.py pins the equality. History:
    // `information` was never a widget (an iNiR bar style name), B8.2
    // re-added the end4 base widgets, B9.7 re-added `utilButtons`, D4a
    // renamed `divisor` -> `separator` (legacy alias kept) and added
    // `spacer`.
    readonly property var barComponentIds: BarWidgetDefaults.IDS
    // Labels/icons moved to shell/ui/BarWidgetCatalog.qml (D4a): the
    // settings cards consume the shared catalog instead of a services-side
    // option list.
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
    property var quickSettingsComponents: root.defaultQuickSettingsComponents.slice()
    readonly property int defaultBarThickness: BarDefaults.DEFAULTS.barThickness
    readonly property int barThickness: root.activeBarConfig().axes.barThickness
    onBarThicknessChanged: Appearance.barThickness = root.barThickness
    // B9.4: vertical thickness is a separate axis (ROADMAP B-2). It used to
    // reuse `barThickness`, which made the left/right edges impossible to tune
    // apart from the top/bottom one.
    readonly property int defaultBarVerticalThickness: BarDefaults.DEFAULTS.verticalThickness
    readonly property int barVerticalThickness: root.activeBarConfig().axes.verticalThickness
    onBarVerticalThicknessChanged: Appearance.verticalBarThickness = root.barVerticalThickness
    // B9.5 outer margins: distance from the screen edge (normal axis) and the
    // inset at both ends (along the bar). 0 keeps the end4 edge-flush baseline;
    // they are separate from the internal lane inset. sideMarginPercent
    // (D4c) is the each-side margin in percent of the screen: 0 keeps full
    // width, a nonzero value centers the bar on the remaining span.
    readonly property int barEdgeMargin: root.activeBarConfig().axes.edgeMargin
    readonly property int barSideMargin: root.activeBarConfig().axes.sideMargin
    // Full normalized axes view for the D4c consumers (Bar window geometry,
    // BarContent/BarGroup chrome resolve through BarDefaults).
    readonly property var barAxes: root.activeBarConfig().axes
    // D4c sentinel resolution (BarDefaults baselines). The context carries
    // the style booleans; gapsOut comes from Appearance so the baseline
    // stays in sync with the theme token. Bindings stay reactive: reading
    // barAxes/barStyleContext inside these functions tracks them.
    readonly property var barStyleContext: ({
        cornerStyle: root.barCornerStyle,
        borderless: root.barBorderless,
        material: root.barIsMaterial,
        materialHug: root.barIsMaterialHug,
        panel: root.barIsPanel,
        gapsOut: Appearance.sizes.hyprlandGapsOut
    })

    function resolvedBarSpacing(isVertical) {
        const context = Object.assign({}, root.barStyleContext, {
            vertical: isVertical === true
        });
        return BarDefaults.resolvedSpacing(root.barAxes, context);
    }

    function resolvedBarInnerPadding() {
        return BarDefaults.resolvedInnerPadding(root.barAxes, root.barStyleContext);
    }

    function resolvedBarWidgetPadding(paintMaterialPill) {
        return BarDefaults.resolvedWidgetPadding(root.barAxes, root.barStyleContext, paintMaterialPill === true);
    }

    // Bar shell corner radius: -1 keeps the style-derived value, an
    // explicit value wins, squareCorners flattens to 0 (dux semantics).
    function resolvedBarShellRadius(styleRadius) {
        return BarDefaults.resolvedRadius(root.barAxes, styleRadius);
    }

    // D4c color-axis resolution shared by the surface and widget layers:
    // "default" keeps the passed base, a #hex wins directly, anything else
    // resolves as an Appearance role name (col-prefixed). Explicit opacity
    // (0..1) bakes over the result; -1/-absent keeps the color untouched.
    function resolvedBarAxisColor(name, baseColor, opacity) {
        let color = baseColor;
        if (typeof name === "string" && BarDefaults.isCustomColor(name))
            color = name;
        else if (typeof name === "string" && name !== "" && name !== "default")
            color = Appearance.colors[`col${name.charAt(0).toUpperCase()}${name.slice(1)}`] ?? baseColor;
        if (typeof opacity === "number" && opacity >= 0 && opacity < 1)
            color = Appearance.transparentize(color, 1 - opacity);
        return color;
    }

    // The bar surface background (BarContent/VerticalBarContent
    // barBackground): the style's colLayer0 with the surfaceColor override
    // and surfaceTransparency applied (sentinels keep the theme pipeline,
    // which already bakes the global [effects] opacity into the palette).
    function resolvedBarSurfaceColor(baseColor) {
        return root.resolvedBarAxisColor(root.barAxes.surfaceColor, baseColor, root.barAxes.surfaceTransparency);
    }

    // The group-capsule layer: widgetTransparency < 1 transparentizes the
    // resolved capsule color (1.0 = untouched).
    function resolvedBarWidgetColor(color) {
        return root.resolvedBarAxisColor("default", color, root.barAxes.widgetTransparency);
    }

    // Group-capsule outline (D4c widgetOutline*): the segmented mode's
    // built-in 1px stays the baseline; enabled axes override it.
    function barWidgetOutlineWidth(baselineWidth) {
        return root.barAxes.widgetOutlineEnabled ? root.barAxes.widgetOutlineThickness : baselineWidth;
    }

    function barWidgetOutlineColor(baselineColor) {
        if (!root.barAxes.widgetOutlineEnabled)
            return baselineColor;
        return root.resolvedBarAxisColor(root.barAxes.widgetOutlineColor, baselineColor, root.barAxes.widgetOutlineOpacity);
    }

    // Bar surface border: borderEnabled=false keeps the style baseline
    // (Float's built-in 1px); enabled axes draw an explicit border
    // (thickness 0 turns every border off).
    function barSurfaceBorderWidth(baselineWidth) {
        return root.barAxes.borderEnabled ? root.barAxes.borderThickness : baselineWidth;
    }

    function barSurfaceBorderColor(baselineColor) {
        if (!root.barAxes.borderEnabled)
            return baselineColor;
        return root.resolvedBarAxisColor(root.barAxes.borderColor, baselineColor, root.barAxes.borderOpacity);
    }

    // D4a bar customization engine: the single truth is barConfigs (the
    // [[bar.configs]] array — one entry today, the schema is multi-bar
    // ready). Each lane holds entry objects {widgetId, uid, enabled,
    // overrides}; uid is unique across the whole bar so per-entry mutation
    // (enabled toggles, D4b per-instance axes) never touches siblings.
    // Everything else — barLayout* id views, the bridge's enabled-id views,
    // islandInLayout — derives from here; nothing writes those back.
    // A lane missing from storage reads as the default lane; an explicitly
    // empty lane stays empty (the minimal writer omits default-equal lanes
    // only).
    readonly property var defaultBarLayoutLeft: ["launcherButton", "workspaces", "activeWindow"]
    // B3-1: the island is a first-class middle widget, not a reserved gap.
    readonly property var defaultBarLayoutMiddle: ["island"]
    readonly property var defaultBarLayoutRight: ["tray", "quickSettings", "systemIcons", "powerButton"]
    property var barConfigs: root.defaultBarConfigs()

    // Lane entry views (hosts and the settings cards consume these).
    readonly property var barLayoutEntriesLeft: root.laneEntries("left")
    readonly property var barLayoutEntriesMiddle: root.laneEntries("middle")
    readonly property var barLayoutEntriesRight: root.laneEntries("right")

    // Widget-id views in lane order, disabled entries included. Kept for
    // the probe, the dashboard lane editor and other id-level consumers;
    // replacing a lane through setBarLayouts() resets disabled/override
    // state on the replaced entries by design.
    readonly property var barLayoutLeft: root.laneIds("left")
    readonly property var barLayoutMiddle: root.laneIds("middle")
    readonly property var barLayoutRight: root.laneIds("right")

    // B9.3 single truth: the island exists exactly when it is a member of any
    // bar lane. Notification-slot arbitration and the bar widget filter both
    // read this instead of a second config switch.
    readonly property bool islandInLayout: root.laneUsesWidget("island")

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
    // D1's `time.dateFormat` became the clock entry's `dateFormat` axis
    // (D4b): the Qt format pattern now lives on the lane entry and the
    // clock widget formats it per instance.

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

    function setIslandShowMediaControls(value) {
        setValue("islandShowMediaControls", value === true);
    }

    function setIslandVisualizerStyle(value) {
        setValue("islandVisualizerStyle", normalizedOption(root.islandVisualizerStyleOptions, value, "dots"));
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

    // D4c: bar-level axes write through the configs entry (clone-edit-
    // reassign + save, the D4a lane machinery). The normalize helpers are
    // the same ones normalizeBarAxes applies on load, so a write can never
    // smuggle an out-of-range value into storage.
    function setBarAxis(key, value) {
        return root.withBarConfigs(config => {
            if (config.axes[key] === value)
                return false;
            config.axes[key] = value;
            return true;
        });
    }

    function setBarPosition(value) {
        setBarAxis("position", normalizedEdgePosition(value));
    }

    function setBarCornerStyle(value) {
        setBarAxis("cornerStyle", normalizedBoundedInt(value, 1, 0, 5));
    }

    function setBarBorderless(value) {
        setBarAxis("borderless", BarDefaults.BORDERLESS_MODES.indexOf(String(value)) !== -1 ? String(value) : "pills");
    }

    function setBarGroupColor(value) {
        setBarAxis("groupColor", normalizedOption(root.barGroupColorOptions, value, "layer1"));
    }

    function setBarAutoHide(value) {
        setBarAxis("autoHide", value === true);
    }

    function setBarShowBackground(value) {
        setBarAxis("showBackground", value === true);
    }

    function setBarScreenList(value) {
        setBarAxis("screenList", root.normalizedScreenList(Array.isArray(value) ? value : []));
    }

    function setBarThickness(value) {
        setBarAxis("barThickness", root.clampedBarInt(value, 28, 64, root.defaultBarThickness));
    }

    function setBarVerticalThickness(value) {
        setBarAxis("verticalThickness", root.clampedBarInt(value, 28, 64, root.defaultBarVerticalThickness));
    }

    function setBarEdgeMargin(value) {
        setBarAxis("edgeMargin", root.normalizedBoundedInt(value, 0, 0, 48));
    }

    function setBarSideMargin(value) {
        setBarAxis("sideMargin", root.normalizedBoundedInt(value, 0, 0, 96));
    }

    // D4c named axis setters (the settings page calls these; every value
    // passes the same clamps as the load normalizer, so storage can never
    // hold an out-of-range value no matter which door wrote it).
    function setBarSideMarginPercent(value) {
        setBarAxis("sideMarginPercent", root.normalizedBoundedInt(value, 0, 0, 49));
    }

    function setBarSpacing(value) {
        setBarAxis("spacing", root.clampedBarSentinelInt(value, -1, 0, 64));
    }

    function setBarInnerPadding(value) {
        setBarAxis("innerPadding", root.clampedBarSentinelInt(value, -1, 0, 64));
    }

    function setBarWidgetPadding(value) {
        setBarAxis("widgetPadding", root.clampedBarSentinelInt(value, -1, 0, 32));
    }

    function setBarSquareCorners(value) {
        setBarAxis("squareCorners", value === true);
    }

    function setBarRadius(value) {
        setBarAxis("radius", root.clampedBarSentinelInt(value, -1, 0, 32));
    }

    function setBarFontScale(value) {
        const numeric = Number(value);
        setBarAxis("fontScale", isFinite(numeric) ? Math.max(0.8, Math.min(1.5, Math.round(numeric * 100) / 100)) : 1);
    }

    function setBarSurfaceColor(value) {
        setBarAxis("surfaceColor", typeof value === "string" && value.length > 0 && value.length <= 32 ? value : "default");
    }

    function setBarSurfaceTransparency(value) {
        const numeric = Number(value);
        setBarAxis("surfaceTransparency", !isFinite(numeric) || numeric >= 1 ? -1 : Math.max(0.3, Math.min(1, numeric)));
    }

    function setBarBorderEnabled(value) {
        setBarAxis("borderEnabled", value === true);
    }

    function setBarBorderColor(value) {
        setBarAxis("borderColor", typeof value === "string" && value !== "" ? value : "outlineVariant");
    }

    function setBarBorderOpacity(value) {
        const numeric = Number(value);
        setBarAxis("borderOpacity", isFinite(numeric) ? Math.max(0.1, Math.min(1, numeric)) : 1);
    }

    function setBarBorderThickness(value) {
        setBarAxis("borderThickness", root.clampedBarInt(value, 0, 4, 1));
    }

    function setBarWidgetTransparency(value) {
        const numeric = Number(value);
        setBarAxis("widgetTransparency", !isFinite(numeric) || numeric >= 1 ? 1 : Math.max(0.3, Math.min(1, numeric)));
    }

    function setBarWidgetOutlineEnabled(value) {
        setBarAxis("widgetOutlineEnabled", value === true);
    }

    function setBarWidgetOutlineColor(value) {
        setBarAxis("widgetOutlineColor", typeof value === "string" && value !== "" ? value : "outline");
    }

    function setBarWidgetOutlineOpacity(value) {
        const numeric = Number(value);
        setBarAxis("widgetOutlineOpacity", isFinite(numeric) ? Math.max(0.1, Math.min(1, numeric)) : 1);
    }

    function setBarWidgetOutlineThickness(value) {
        setBarAxis("widgetOutlineThickness", root.clampedBarInt(value, 0, 4, 1));
    }

    // Sentinel axes (-1 = follow the style baseline) or bounded ints; the
    // shared clamp for the D4c geometry axes.
    function clampedBarSentinelInt(value, fallback, min, max) {
        if (value === -1)
            return -1;
        return root.normalizedBoundedInt(value, fallback, min, max);
    }

    function clampedBarInt(value, min, max, fallback) {
        const numeric = Number(value);
        return isFinite(numeric) ? Math.max(min, Math.min(max, Math.round(numeric))) : fallback;
    }

    // Right-click style editor (BarGroupStylePopup) persistence, D4c
    // shape: the style keys are plain overrides on the lane entry (uid
    // addressed, so duplicate widgets style independently — dux per-widget
    // axis lineage). Writers search every zone; a uid only ever matches
    // one entry.
    function setBarEntryStyle(uid, key, value) {
        if (!uid || !key)
            return;
        root.withBarConfigs(config => {
            const zones = ["left", "middle", "right"];
            for (let z = 0; z < zones.length; z += 1) {
                const lane = config.lanes[zones[z]];
                for (let i = 0; i < lane.length; i += 1) {
                    if (lane[i].uid !== uid)
                        continue;
                    if (value === undefined || value === "") {
                        if (lane[i].overrides[key] !== undefined) {
                            delete lane[i].overrides[key];
                            return true;
                        }
                        return false;
                    }
                    if (lane[i].overrides[key] !== value) {
                        lane[i].overrides[key] = value;
                        return true;
                    }
                    return false;
                }
            }
            return false;
        });
    }

    function resetBarEntryStyle(uid) {
        if (!uid)
            return;
        const keys = ["color", "borderColor", "radius", "borderWidth", "padding"];
        root.withBarConfigs(config => {
            let changed = false;
            const zones = ["left", "middle", "right"];
            for (let z = 0; z < zones.length; z += 1) {
                const lane = config.lanes[zones[z]];
                for (let i = 0; i < lane.length; i += 1) {
                    if (lane[i].uid !== uid)
                        continue;
                    keys.forEach(key => {
                        if (lane[i].overrides[key] !== undefined) {
                            delete lane[i].overrides[key];
                            changed = true;
                        }
                    });
                }
            }
            return changed;
        });
    }

    // ---- D4a bar lane entry machinery -----------------------------------
    // barConfigs is the truth; every mutation clones, edits and reassigns
    // so the derived views (barLayout*, barLayoutEntries*) re-evaluate off a
    // single reference change. uids are session identity only — they are
    // never persisted (the minimal writer serializes entries without them),
    // so they only need to be unique within one bar, not stable across
    // restarts.

    function defaultBarConfigs() {
        return [
            {
                id: "default",
                name: "Bar",
                axes: root.normalizeBarAxes({}),
                lanes: root.normalizeConfigLanes({})
            }
        ];
    }

    // Normalizes a parsed [[bar.configs]] array. A lane missing from storage
    // reads as the DEFAULT lane; an explicitly empty lane stays empty (the
    // minimal writer omits default-equal lanes only). Single-bar first:
    // extra entries are dropped on the floor (D4e lifts this). The bar-level
    // axes are flat keys on the entry (everything except id/name/lanes),
    // normalized through the same clamp table the setters use.
    function normalizeBarConfigs(rawConfigs) {
        const source = Array.isArray(rawConfigs) && rawConfigs.length > 0 ? rawConfigs : [
            {}
        ];
        const bar = source[0] && typeof source[0] === "object" && !Array.isArray(source[0]) ? source[0] : {};
        const rawLanes = bar.lanes && typeof bar.lanes === "object" && !Array.isArray(bar.lanes) ? bar.lanes : {};
        return [
            {
                id: typeof bar.id === "string" && bar.id !== "" ? bar.id : "default",
                name: typeof bar.name === "string" && bar.name !== "" ? bar.name : "Bar",
                axes: root.normalizeBarAxes(bar),
                lanes: root.normalizeConfigLanes(rawLanes)
            }
        ];
    }

    // D4c bar-level axes, normalized against BarDefaults.DEFAULTS. Every
    // clamp mirrors the pre-D4c flat-key clamps (a migrated value can never
    // shift by normalization); the new axes use -1 sentinels ("follow the
    // style baseline") clamped to their adjustable ranges.
    function normalizeBarAxes(raw) {
        const d = BarDefaults.DEFAULTS;
        const scaled = (value, fallback) => {
            const numeric = Number(value);
            return isFinite(numeric) ? Math.max(0.8, Math.min(1.5, Math.round(numeric * 100) / 100)) : fallback;
        };
        const fraction = (value, fallback) => {
            const numeric = Number(value);
            return isFinite(numeric) ? Math.max(0, Math.min(1, numeric)) : fallback;
        };
        return {
            position: normalizedEdgePosition(raw.position),
            autoHide: raw.autoHide === true,
            screenList: root.normalizedScreenList(raw.screenList),
            showBackground: typeof raw.showBackground === "boolean" ? raw.showBackground : true,
            cornerStyle: root.normalizedBoundedInt(raw.cornerStyle, 1, 0, 5),
            borderless: BarDefaults.BORDERLESS_MODES.indexOf(raw.borderless) !== -1 ? raw.borderless : "pills",
            groupColor: normalizedOption(root.barGroupColorOptions, raw.groupColor, "layer1"),
            barThickness: root.clampedBarInt(raw.barThickness, 28, 64, d.barThickness),
            verticalThickness: root.clampedBarInt(raw.verticalThickness, 28, 64, d.verticalThickness),
            edgeMargin: root.normalizedBoundedInt(raw.edgeMargin, 0, 0, 48),
            sideMargin: root.normalizedBoundedInt(raw.sideMargin, 0, 0, 96),
            sideMarginPercent: root.normalizedBoundedInt(raw.sideMarginPercent, 0, 0, 49),
            spacing: root.clampedBarSentinelInt(raw.spacing, -1, 0, 64),
            innerPadding: root.clampedBarSentinelInt(raw.innerPadding, -1, 0, 64),
            widgetPadding: root.clampedBarSentinelInt(raw.widgetPadding, -1, 0, 32),
            squareCorners: raw.squareCorners === true,
            radius: root.clampedBarSentinelInt(raw.radius, -1, 0, 32),
            fontScale: scaled(raw.fontScale, 1),
            surfaceColor: typeof raw.surfaceColor === "string" && raw.surfaceColor.length <= 32 ? raw.surfaceColor : "default",
            surfaceTransparency: raw.surfaceTransparency === -1 ? -1 : fraction(raw.surfaceTransparency, -1),
            borderEnabled: raw.borderEnabled === true,
            borderColor: typeof raw.borderColor === "string" && raw.borderColor !== "" ? raw.borderColor : "outlineVariant",
            borderOpacity: fraction(raw.borderOpacity, 1),
            borderThickness: root.clampedBarInt(raw.borderThickness, 0, 4, 1),
            widgetTransparency: fraction(raw.widgetTransparency, 1),
            widgetOutlineEnabled: raw.widgetOutlineEnabled === true,
            widgetOutlineColor: typeof raw.widgetOutlineColor === "string" && raw.widgetOutlineColor !== "" ? raw.widgetOutlineColor : "outline",
            widgetOutlineOpacity: fraction(raw.widgetOutlineOpacity, 1),
            widgetOutlineThickness: root.clampedBarInt(raw.widgetOutlineThickness, 0, 4, 1)
        };
    }

    function normalizeConfigLanes(rawLanes) {
        const usedSingletons = [];
        const lanes = {};
        ["left", "middle", "right"].forEach(zone => {
            // Missing lane -> the default lane; explicit empty stays empty.
            const defaults = {
                left: root.defaultBarLayoutLeft,
                middle: root.defaultBarLayoutMiddle,
                right: root.defaultBarLayoutRight
            };
            const raw = rawLanes && Array.isArray(rawLanes[zone]) ? rawLanes[zone] : defaults[zone];
            lanes[zone] = root.normalizeLaneEntries(raw, zone, usedSingletons);
        });
        return lanes;
    }

    // Lane entries may be plain widget-id strings or {id, enabled,
    // ...overrides} objects (the persisted shape). Legacy ids alias to
    // canonical ones, unknown ids drop, singleton widgets (island) dedupe.
    function normalizeLaneEntries(rawLane, zone, usedSingletons) {
        const source = Array.isArray(rawLane) ? rawLane : [];
        const entries = [];
        for (let index = 0; index < source.length; index += 1) {
            const raw = source[index];
            let widgetId;
            let enabled = true;
            let overrides = {};
            if (raw && typeof raw === "object") {
                widgetId = raw.widgetId !== undefined ? raw.widgetId : raw.id;
                enabled = raw.enabled !== false;
                const flat = {};
                Object.keys(raw).forEach(key => {
                    if (key !== "id" && key !== "widgetId" && key !== "enabled" && key !== "overrides" && key !== "uid")
                        flat[key] = raw[key];
                });
                const enveloped = raw.overrides && typeof raw.overrides === "object" && !Array.isArray(raw.overrides) ? raw.overrides : {};
                Object.assign(overrides, flat, enveloped);
            } else {
                widgetId = raw;
            }
            const canonical = BarWidgetDefaults.canonicalId(widgetId);
            if (!BarWidgetDefaults.isKnownId(canonical))
                continue;
            if (BarWidgetDefaults.SINGLETON_IDS.indexOf(canonical) !== -1) {
                if (usedSingletons.indexOf(canonical) !== -1)
                    continue;
                usedSingletons.push(canonical);
            }
            entries.push({
                widgetId: canonical,
                uid: canonical + "@" + zone + index,
                enabled: enabled,
                overrides: overrides
            });
        }
        return entries;
    }

    // Minimal-write entry serialization: entries with no state beyond their
    // id collapse to plain strings; override keys equal to the widget
    // defaults drop. Keys are emitted sorted so equal content compares
    // equal regardless of construction order.
    function serializeBarEntry(entry) {
        const defaults = BarWidgetDefaults.DEFAULTS[entry.widgetId] || {};
        const keys = Object.keys(entry.overrides || {}).filter(key => entry.overrides[key] !== defaults[key]).sort();
        if (entry.enabled !== false && keys.length === 0)
            return entry.widgetId;
        const out = {
            id: entry.widgetId
        };
        if (entry.enabled === false)
            out.enabled = false;
        keys.forEach(key => {
            out[key] = entry.overrides[key];
        });
        return out;
    }

    function sparseBarConfigs() {
        const truth = root.activeBarConfig();
        const fallback = root.defaultBarConfigs()[0];
        const lanes = {};
        ["left", "middle", "right"].forEach(zone => {
            const mine = truth.lanes[zone].map(root.serializeBarEntry);
            const dflt = fallback.lanes[zone].map(root.serializeBarEntry);
            if (JSON.stringify(mine) !== JSON.stringify(dflt))
                lanes[zone] = mine;
        });
        // Bar-level axes ride the same sparse rule: only deviations from
        // BarDefaults.DEFAULTS persist (sorted for stable diffs); screenList
        // compares by content.
        const axes = {};
        Object.keys(BarDefaults.DEFAULTS).sort().forEach(key => {
            const mine = truth.axes[key];
            const dflt = fallback.axes[key];
            const same = Array.isArray(mine) ? JSON.stringify(mine) === JSON.stringify(dflt) : mine === dflt;
            if (!same)
                axes[key] = mine;
        });
        const out = {
            id: truth.id
        };
        if (truth.name !== fallback.name)
            out.name = truth.name;
        Object.assign(out, axes);
        if (Object.keys(lanes).length > 0)
            out.lanes = lanes;
        if (Object.keys(axes).length === 0 && Object.keys(lanes).length === 0)
            return null;
        return [out];
    }

    function activeBarConfig() {
        if (Array.isArray(root.barConfigs) && root.barConfigs.length > 0)
            return root.barConfigs[0];
        return root.defaultBarConfigs()[0];
    }

    function laneEntries(zone) {
        const config = root.activeBarConfig();
        return config.lanes[root.canonicalZone(zone)] || [];
    }

    function laneIds(zone) {
        return root.laneEntries(zone).map(entry => entry.widgetId);
    }

    // Enabled-only id view: what the bar actually instantiates. The Config
    // bridge serves this so vendor widgets asking "is X on this side" never
    // count a disabled entry.
    function barLayoutEnabledIds(zone) {
        return root.laneEntries(zone).filter(entry => entry.enabled !== false).map(entry => entry.widgetId);
    }

    function laneUsesWidget(widgetId) {
        return ["left", "middle", "right"].some(zone => root.laneEntries(zone).some(entry => entry.widgetId === widgetId));
    }

    // D4b: entry lookup by uid (the settings editor and the probe address
    // one instance — duplicate ids stay independent).
    function barEntryByUid(uid) {
        const zones = ["left", "middle", "right"];
        for (let z = 0; z < zones.length; z += 1) {
            const lane = root.laneEntries(zones[z]);
            for (let i = 0; i < lane.length; i += 1) {
                if (lane[i].uid === uid)
                    return lane[i];
            }
        }
        return null;
    }

    function canonicalZone(zone) {
        if (zone === "middle" || zone === "center")
            return "middle";
        if (zone === "right" || zone === "trailing")
            return "right";
        return "left";
    }

    // Clone-edit-reassign helper: mutator returns whether anything changed;
    // a change reassigns barConfigs (single notification) and saves.
    function withBarConfigs(mutator) {
        const next = JSON.parse(JSON.stringify(Array.isArray(root.barConfigs) && root.barConfigs.length > 0 ? root.barConfigs : [root.activeBarConfig()]));
        const changed = mutator(next[0]);
        if (changed) {
            root.barConfigs = next;
            root.save();
        }
        return changed;
    }

    function setBarLayouts(left, middle, right) {
        const zones = {
            left: left,
            middle: middle,
            right: right
        };
        return root.withBarConfigs(config => {
            const usedSingletons = [];
            let changed = false;
            ["left", "middle", "right"].forEach(zone => {
                const next = root.normalizeLaneEntries(Array.isArray(zones[zone]) ? zones[zone] : [], zone, usedSingletons);
                const mine = config.lanes[zone];
                const same = next.length === mine.length && next.every((entry, index) => entry.widgetId === mine[index].widgetId);
                if (!same) {
                    config.lanes[zone] = next;
                    changed = true;
                }
            });
            return changed;
        });
    }

    // Entry-level replacement (drag reorder): entries arrive verbatim from
    // the live views, so uids, enabled and overrides survive. Unknown ids
    // and duplicate singletons drop.
    function setBarLaneEntries(zone, entries) {
        const target = root.canonicalZone(zone);
        return root.withBarConfigs(config => {
            const usedSingletons = [];
            ["left", "middle", "right"].forEach(other => {
                if (other !== target)
                    config.lanes[other].forEach(entry => {
                        if (BarWidgetDefaults.SINGLETON_IDS.indexOf(entry.widgetId) !== -1)
                            usedSingletons.push(entry.widgetId);
                    });
            });
            const source = Array.isArray(entries) ? entries : [];
            const next = [];
            for (let index = 0; index < source.length; index += 1) {
                const entry = source[index];
                if (!entry || typeof entry !== "object")
                    continue;
                const canonical = BarWidgetDefaults.canonicalId(entry.widgetId);
                if (!BarWidgetDefaults.isKnownId(canonical))
                    continue;
                if (BarWidgetDefaults.SINGLETON_IDS.indexOf(canonical) !== -1) {
                    if (usedSingletons.indexOf(canonical) !== -1)
                        continue;
                    usedSingletons.push(canonical);
                }
                const overrides = entry.overrides && typeof entry.overrides === "object" && !Array.isArray(entry.overrides) ? entry.overrides : {};
                next.push({
                    widgetId: canonical,
                    uid: typeof entry.uid === "string" && entry.uid !== "" ? entry.uid : canonical + "@" + target + index + "+",
                    enabled: entry.enabled !== false,
                    overrides: overrides
                });
            }
            const mine = config.lanes[target];
            const same = JSON.stringify(next) === JSON.stringify(mine);
            if (!same)
                config.lanes[target] = next;
            return !same;
        });
    }

    function setBarEntryEnabled(uid, enabled) {
        return root.withBarConfigs(config => {
            let changed = false;
            ["left", "middle", "right"].forEach(zone => {
                config.lanes[zone].forEach(entry => {
                    if (entry.uid === uid && entry.enabled !== (enabled === true)) {
                        entry.enabled = enabled === true;
                        changed = true;
                    }
                });
            });
            return changed;
        });
    }

    // D4b write side of the injection protocol: an override equal to the
    // widget default removes itself, so the file only ever carries real
    // deviations.
    function setBarEntryOverride(uid, key, value) {
        return root.withBarConfigs(config => {
            let changed = false;
            ["left", "middle", "right"].forEach(zone => {
                config.lanes[zone].forEach(entry => {
                    if (entry.uid !== uid)
                        return;
                    const defaults = BarWidgetDefaults.DEFAULTS[entry.widgetId] || {};
                    const next = Object.assign({}, entry.overrides);
                    if (value === undefined || value === null || value === defaults[key])
                        delete next[key];
                    else
                        next[key] = value;
                    if (JSON.stringify(next) !== JSON.stringify(entry.overrides)) {
                        entry.overrides = next;
                        changed = true;
                    }
                });
            });
            return changed;
        });
    }

    function barZoneComponents(zone) {
        return root.laneIds(zone);
    }

    function moveBarComponent(componentId, targetZone, targetIndex) {
        const canonical = BarWidgetDefaults.canonicalId(componentId);
        if (!BarWidgetDefaults.isKnownId(canonical))
            return false;
        const zone = root.canonicalZone(targetZone);
        return root.withBarConfigs(config => {
            const moving = [];
            Object.keys(config.lanes).forEach(source => {
                config.lanes[source] = config.lanes[source].filter(entry => {
                    if (entry.widgetId === canonical) {
                        moving.push(entry);
                        return false;
                    }
                    return true;
                });
            });
            const numericIndex = Number(targetIndex);
            const insertionIndex = isFinite(numericIndex) ? Math.max(0, Math.min(config.lanes[zone].length, Math.round(numericIndex))) : config.lanes[zone].length;
            if (moving.length === 0) {
                // Not placed anywhere: move doubles as add — the island
                // re-entry path (setIslandInLayout(true)) relies on it.
                config.lanes[zone].splice(insertionIndex, 0, {
                    widgetId: canonical,
                    uid: canonical + "@" + zone + insertionIndex + "+" + Date.now(),
                    enabled: true,
                    overrides: {}
                });
                return true;
            }
            for (let index = 0; index < moving.length; index += 1)
                config.lanes[zone].splice(insertionIndex + index, 0, moving[index]);
            return true;
        });
    }

    function removeBarComponent(componentId) {
        const canonical = BarWidgetDefaults.canonicalId(componentId);
        if (!BarWidgetDefaults.isKnownId(canonical))
            return false;
        return root.withBarConfigs(config => {
            let removed = false;
            Object.keys(config.lanes).forEach(zone => {
                const next = config.lanes[zone].filter(entry => entry.widgetId !== canonical);
                if (next.length !== config.lanes[zone].length)
                    removed = true;
                config.lanes[zone] = next;
            });
            return removed;
        });
    }

    function toggleBarComponent(componentId, zone) {
        const canonical = BarWidgetDefaults.canonicalId(componentId);
        const target = root.canonicalZone(zone);
        if (root.laneEntries(target).some(entry => entry.widgetId === canonical))
            return root.removeBarComponent(canonical);
        return root.moveBarComponent(canonical, target, root.laneEntries(target).length);
    }

    // ---- entry-granular mutations (the settings card's chip operations) ---

    function addBarEntry(zone, widgetId, index) {
        const canonical = BarWidgetDefaults.canonicalId(widgetId);
        if (!BarWidgetDefaults.isKnownId(canonical))
            return false;
        const target = root.canonicalZone(zone);
        return root.withBarConfigs(config => {
            const usedSingletons = [];
            config.lanes[target].forEach(entry => {
                if (BarWidgetDefaults.SINGLETON_IDS.indexOf(entry.widgetId) !== -1)
                    usedSingletons.push(entry.widgetId);
            });
            if (BarWidgetDefaults.SINGLETON_IDS.indexOf(canonical) !== -1 && usedSingletons.indexOf(canonical) !== -1)
                return false;
            const numericIndex = Number(index);
            const insertionIndex = isFinite(numericIndex) ? Math.max(0, Math.min(config.lanes[target].length, Math.round(numericIndex))) : config.lanes[target].length;
            config.lanes[target].splice(insertionIndex, 0, {
                widgetId: canonical,
                uid: canonical + "@" + target + insertionIndex + "+" + Date.now(),
                enabled: true,
                overrides: {}
            });
            return true;
        });
    }

    function moveBarEntry(uid, zone, index) {
        const target = root.canonicalZone(zone);
        return root.withBarConfigs(config => {
            let moving = null;
            Object.keys(config.lanes).forEach(source => {
                if (moving)
                    return;
                const at = config.lanes[source].findIndex(entry => entry.uid === uid);
                if (at !== -1) {
                    moving = config.lanes[source][at];
                    config.lanes[source].splice(at, 1);
                }
            });
            if (!moving)
                return false;
            const numericIndex = Number(index);
            const insertionIndex = isFinite(numericIndex) ? Math.max(0, Math.min(config.lanes[target].length, Math.round(numericIndex))) : config.lanes[target].length;
            config.lanes[target].splice(insertionIndex, 0, moving);
            return true;
        });
    }

    function removeBarEntry(uid) {
        return root.withBarConfigs(config => {
            let removed = false;
            Object.keys(config.lanes).forEach(zone => {
                const next = config.lanes[zone].filter(entry => entry.uid !== uid);
                if (next.length !== config.lanes[zone].length)
                    removed = true;
                config.lanes[zone] = next;
            });
            return removed;
        });
    }

    function toggleBarEntryEnabled(uid) {
        return root.withBarConfigs(config => {
            let changed = false;
            Object.keys(config.lanes).forEach(zone => {
                config.lanes[zone].forEach(entry => {
                    if (entry.uid === uid) {
                        entry.enabled = entry.enabled === false;
                        changed = true;
                    }
                });
            });
            return changed;
        });
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

    // Legacy lane read (pre-v3 files and hand-written configs): canonicalize
    // aliases, drop unknown ids, dedupe. The v3 entry path
    // (normalizeLaneEntries) is the live one; this stays for
    // resolveBarLayouts and the migration seed.
    function normalizedBarLayoutIds(raw) {
        if (!Array.isArray(raw))
            return [];

        const seen = {};
        const out = [];
        raw.forEach(id => {
            const candidate = BarWidgetDefaults.canonicalId(id);
            if (!BarWidgetDefaults.isKnownId(candidate) || seen[candidate])
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
    // (D4c thickness/margin setters live with the bar-axis writers above.)
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

    function setIslandHideDate(value) {
        setValue("islandHideDate", !!value);
    }

    function setBarShowNames(value) {
        setValue("barShowNames", !!value);
    }

    function setBarShowValues(value) {
        setValue("barShowValues", !!value);
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
        const json = {
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
                "showMediaControls": root.islandShowMediaControls,
                "visualizerStyle": root.islandVisualizerStyle,
                "horizontalClock": {
                    "fontSize": root.horizontalClockFontSize,
                    "axes": root.cloneMap(root.horizontalClockAxes),
                    "digits": root.horizontalClockDigits
                }
            },
            "bar": root.barSectionJson(),
            "sidebar": {
                "keepLoaded": root.keepSidebarsLoaded,
                "dashboardSide": root.dashboardSidebarSide,
                "quickSettingsSide": root.quickSettingsSidebarSide
            },
            "hotCorners": root.normalizedHotCornerActions(root.hotCornerActions),
            "desktopCards": {
                "gridSnapEnabled": root.desktopCardGridSnapEnabled,
                "gridVisibleWhileDragging": root.desktopCardGridVisibleWhileDragging
            },
            "configVersion": ConfigMigrations.CURRENT_VERSION
        };
        // Minimal write: an all-default [bar] disappears entirely instead of
        // serializing as a bare empty table header.
        if (json.bar && Object.keys(json.bar).length === 0)
            delete json.bar;
        return json;
    }

    // ---- D4a [bar] minimal write -----------------------------------------
    // The section only carries deviations from the defaults table; a fresh
    // config writes no [bar] keys, one toggle writes exactly one key.
    // barSectionDefaults() mirrors barSectionRaw()'s shape with the pristine
    // property defaults — the fresh-boot empty-diff probe pins that the two
    // never disagree.

    function barSectionJson() {
        return root.diffSparseSection(root.barSectionRaw(), root.barSectionDefaults());
    }

    function barSectionRaw() {
        const sparseConfigs = root.sparseBarConfigs();
        const section = {
            "showValues": root.barShowValues,
            "showNames": root.barShowNames,
            "quickSettingsComponents": root.quickSettingsComponents.slice(),
            // Tray shared state only: the per-instance tray axes ride the
            // lane entries (D4b). The bar-level axes (position, styles,
            // thickness, margins...) live on the configs entry (D4c).
            "tray": {
                "pinnedItems": root.barTrayPinnedItems.slice(),
                "invertPinnedItems": root.barTrayInvertPinnedItems
            }
        };
        if (sparseConfigs)
            section.configs = sparseConfigs;
        return section;
    }

    function barSectionDefaults() {
        return {
            "showValues": true,
            "showNames": false,
            "quickSettingsComponents": root.defaultQuickSettingsComponents.slice(),
            "tray": {
                "pinnedItems": [],
                "invertPinnedItems": true
            }
        };
    }

    // Recursive default-diff: equal values drop, objects recurse, arrays
    // compare by content. An object that diffs down to nothing becomes an
    // empty object (the toJson wrapper deletes an all-empty [bar]).
    function diffSparseSection(value, defaults) {
        if (value === null || typeof value !== "object" || Array.isArray(value))
            return JSON.stringify(value) === JSON.stringify(defaults) ? {} : value;
        const out = {};
        Object.keys(value).forEach(key => {
            const diffed = root.diffSparseSection(value[key], defaults && typeof defaults === "object" ? defaults[key] : undefined);
            if (diffed === null || diffed === undefined)
                return;
            if (typeof diffed === "object" && !Array.isArray(diffed) && Object.keys(diffed).length === 0)
                return;
            out[key] = diffed;
        });
        return out;
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
        // D4a version chain: runs before any section read — the v3 step
        // reshapes the legacy [bar] layout keys into [[bar.configs]] lanes.
        // The seed inputs (one-shot island seed, legacy island gate) are the
        // same pure helpers the probe proves; the chain itself is idempotent
        // and stamps configVersion.
        const preSource = configSection(parsed);
        const preIsland = configSection(preSource.island);
        const migration = ConfigMigrations.migrateConfig(parsed, {
            lanes: root.resolveBarLayouts(configSection(preSource.bar), preIsland, typeof preIsland.enabled === "boolean" ? preIsland.enabled : true),
            defaults: BarWidgetDefaults.DEFAULTS,
            barDefaults: BarDefaults.DEFAULTS
        });
        root.configVersionDirty = root.configVersionDirty || migration.changed;

        const source = configSection(migration.config);
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
        // layout still listed it. The v3 migration applies it once (via
        // resolveBarLayouts); membership is the only truth from then on.
        root.islandSatellite = normalizedOption(root.islandSatelliteOptions, island.satellite, "clock");
        root.islandHideDate = typeof island.hideDate === "boolean" ? island.hideDate : false;
        root.islandShowAvatar = typeof island.showAvatar === "boolean" ? island.showAvatar : true;
        root.islandShowMediaControls = typeof island.showMediaControls === "boolean" ? island.showMediaControls : false;
        root.islandVisualizerStyle = normalizedOption(root.islandVisualizerStyleOptions, island.visualizerStyle, "dots");
        // D1: `time.dateFormat` (iNiR key shape) — a Qt format pattern for the
        // long date form; empty keeps the stock "dddd, dd/MM".
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
        // D4c: the bar-level axes (position/cornerStyle/borderless/thickness/
        // margins/widgetStyles...) arrive folded onto the [[bar.configs]]
        // entry by the v5 migration — the flat [bar] keys no longer exist
        // here. The derived views (barPosition etc.) re-evaluate off the
        // barConfigs assignment below.
        root.barTrayPinnedItems = root.normalizedTrayPinnedItems(tray.pinnedItems);
        // Absent keys must keep the shipped default (pin new items by
        // default); `=== true` would read a fresh config as "do not pin".
        root.barTrayInvertPinnedItems = typeof tray.invertPinnedItems === "boolean" ? tray.invertPinnedItems : true;
        // D4a truth: lanes live in [[bar.configs]] entries. A lane missing
        // from storage reads as the default lane; an explicitly empty lane
        // stays empty. The one-shot island seed spent itself in the v3
        // migration for pre-v3 files, so the marker is always armed after
        // this load.
        root.barConfigs = root.normalizeBarConfigs(bar.configs);
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
            // The version chain reshaped something: persist the migrated
            // shape (and the configVersion stamp) once, right after the
            // load that triggered it.
            if (root.configVersionDirty) {
                root.configVersionDirty = false;
                root.save();
            }
            root.settingsLoaded();
        }
    }

    Component.onCompleted: {
        if (ConfigService.storeReady) {
            root.loading = true;
            root.loadFromObject(ConfigService.rawConfig);
            root.loading = false;
            root.loaded = true;
            if (root.configVersionDirty) {
                root.configVersionDirty = false;
                root.save();
            }
            root.settingsLoaded();
        }
    }
}
