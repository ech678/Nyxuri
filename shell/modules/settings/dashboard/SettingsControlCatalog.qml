pragma Singleton
import QtQuick
import Quickshell
import qs.app.services
import qs.modules.wallpaper
import qs.shared.i18n

// Control registry for the dashboard settings grid. Plays the role end4-pC's
// SettingsQuickControls does: every card reads its control through
// `controlFor(key)` and never touches the config singleton directly.
//
// Difference from end4-pC: its registry walks a nested `Config.options` tree by
// dotted path, while nyxuri's PersonalizationConfig is a flat property bag with
// explicit setters. So each entry names its getter and setter outright. That is
// more verbose but keeps the normalisation inside PersonalizationConfig (which
// is where clamping and enum validation already live) instead of duplicating it
// here.
Singleton {
    id: root

    function toggle(get, set) {
        return {
            "type": "switch",
            "get": get,
            "set": set
        };
    }

    function select(get, set, options) {
        return {
            "type": "select",
            "get": get,
            "set": set,
            "options": options
        };
    }

    function slider(get, set, from, to, stepSize) {
        return {
            "type": "slider",
            "get": get,
            "set": set,
            "from": from,
            "to": to,
            "stepSize": stepSize ?? 0
        };
    }

    function spin(get, set, from, to, stepSize) {
        return {
            "type": "spin",
            "get": get,
            "set": set,
            "from": from,
            "to": to,
            "stepSize": stepSize ?? 1
        };
    }

    function text(get, set) {
        return {
            "type": "text",
            "get": get,
            "set": set
        };
    }

    readonly property var controls: ({
                                         // ── Interface ────────────────────────────────────────────────
                                         "interface:Theme mode": root.select(()
                                                                             => PersonalizationConfig.themeMode,
                                                                             value => ThemeService.setThemeMode(
                                                                                          value), [
                                                                                 {
                                                                                     "value": "dark",
                                                                                     "label": I18n.tr("Dark"),
                                                                                     "icon": "dark_mode"
                                                                                 },
                                                                                 {
                                                                                     "value": "light",
                                                                                     "label": I18n.tr("Light"),
                                                                                     "icon": "light_mode"
                                                                                 }
                                                                             ]),
                                         "interface:Settings panel style": root.select(()
                                                                                       => PersonalizationConfig.settingsPanelStyle,
                                                                                       value => PersonalizationConfig.setSettingsPanelStyle(
                                                                                                    value), PersonalizationConfig.settingsPanelStyles),

                                         // ── Lyrics ───────────────────────────────────────────────────
                                         // The source choice is the only lever for "Kugou matched
                                         // the wrong recording": lrclib matches on exact names, so
                                         // it is the honest fallback rather than a re-rank.
                                         "lyrics:Backend": root.select(() => PersonalizationConfig.lyricSource,
                                         value => PersonalizationConfig.setLyricSource(value),
                                         PersonalizationConfig.lyricSources),
                                         "lyrics:Timing offset (ms)": root.spin(()
                                                                                => PersonalizationConfig.lyricOffsetMs,
                                                                                value => PersonalizationConfig.setLyricOffsetMs(
                                                                                             value), PersonalizationConfig.lyricOffsetMinMs,
                                                                                PersonalizationConfig.lyricOffsetMaxMs,
                                                                                50),
                                         "lyrics:Font size": root.spin(()
                                                                       => PersonalizationConfig.lyricFontSize,
                                                                       value => PersonalizationConfig.setLyricFontSize(
                                                                                    value), PersonalizationConfig.lyricFontSizeMin,
                                                                       PersonalizationConfig.lyricFontSizeMax,
                                                                       2),
                                         "lyrics:Tint from album art": root.toggle(()
                                                                                   => PersonalizationConfig.lyricAlbumArtTint,
                                                                                   value => PersonalizationConfig.setLyricAlbumArtTint(
                                                                                                value)),
                                         "interface:Matugen scheme": root.select(()
                                                                                 => PersonalizationConfig.matugenScheme,
                                                                                 value => ThemeService.setMatugenScheme(
                                                                                              value), PersonalizationConfig.matugenSchemes),
                                         "interface:Lock screen style": root.select(()
                                                                                    => PersonalizationConfig.lockScreenStyle,
                                                                                    value => PersonalizationConfig.setLockScreenStyle(
                                                                                                 value), PersonalizationConfig.lockScreenStyles),
                                         "interface:Super key style": root.select(()
                                                                                  => PersonalizationConfig.superKeyStyle,
                                                                                  value => PersonalizationConfig.setValue(
                                                                                               "superKeyStyle",
                                                                                               value), PersonalizationConfig.superKeyStyles),
                                         "interface:Shell background opacity": root.slider(()
                                                                                           => PersonalizationConfig.shellBackgroundOpacity,
                                                                                           value => PersonalizationConfig.setShellBackgroundOpacity(
                                                                                                        value), 0,
                                                                                           1, 0.01),
                                         "interface:Dashboard sidebar side": root.select(()
                                                                                         => PersonalizationConfig.dashboardSidebarSide,
                                                                                         value => PersonalizationConfig.setDashboardSidebarSide(
                                                                                                      value), [
                                                                                             {
                                                                                                 "value": "left",
                                                                                                 "label": I18n.tr(
                                                                                                              "Left")
                                                                                             },
                                                                                             {
                                                                                                 "value": "right",
                                                                                                 "label": I18n.tr(
                                                                                                              "Right")
                                                                                             }
                                                                                         ]),
                                         "interface:Quick settings sidebar side": root.select(()
                                                                                              => PersonalizationConfig.quickSettingsSidebarSide,
                                                                                              value => PersonalizationConfig.setQuickSettingsSidebarSide(
                                                                                                           value), [
                                                                                                  {
                                                                                                      "value": "left",
                                                                                                      "label": I18n.tr(
                                                                                                                   "Left")
                                                                                                  },
                                                                                                  {
                                                                                                      "value": "right",
                                                                                                      "label": I18n.tr(
                                                                                                                   "Right")
                                                                                                  }
                                                                                              ]),
                                         "wallpaper:Per-monitor wallpaper": root.toggle(()
                                                                                        => PersonalizationConfig.perMonitorWallpaper,
                                                                                        value => PersonalizationConfig.setPerMonitorWallpaper(
                                                                                                     value)),
                                         "wallpaper:Overview per-monitor wallpaper": root.toggle(()
                                                                                                     => PersonalizationConfig.overviewPerMonitorWallpaper,
                                                                                                     value => PersonalizationConfig.setOverviewPerMonitorWallpaper(
                                                                                                                  value)),
                                         "wallpaper:Desktop transition": root.select(()
                                                                                     => PersonalizationConfig.awwwDesktopTransitionType,
                                                                                     value => PersonalizationConfig.setAwwwDesktopTransitionType(
                                                                                                  value), PersonalizationConfig.awwwTransitionTypes),
                                         "wallpaper:Transition fps": root.spin(()
                                                                               => PersonalizationConfig.awwwTransitionFps,
                                                                               value => PersonalizationConfig.setAwwwTransitionFps(
                                                                                            value), 10, 240,
                                                                               5),
                                         "wallpaper:Transition step": root.spin(()
                                                                                => PersonalizationConfig.awwwTransitionStep,
                                                                                value => PersonalizationConfig.setAwwwTransitionStep(
                                                                                             value), 0, 255,
                                                                                5),
                                         "wallpaper:Overview transition": root.select(()
                                                                                      => PersonalizationConfig.overviewTransitionType,
                                                                                      value => PersonalizationConfig.setOverviewTransitionType(
                                                                                                   value), PersonalizationConfig.transitionTypes),
                                         "wallpaper:Overview use desktop wallpaper": root.toggle(()
                                                                                                 => PersonalizationConfig.overviewUseDesktopWallpaper,
                                                                                                 value => PersonalizationConfig.setOverviewUseDesktopWallpaper(
                                                                                                              value)),
                                         "wallpaper:Parallax follow tiled columns": root.toggle(()
                                                                                                => PersonalizationConfig.parallaxFollowTiledColumns,
                                                                                                value => PersonalizationConfig.setParallaxFollowTiledColumns(
                                                                                                             value)),
                                         "wallpaper:Parallax tiled column span": root.spin(()
                                                                                           => PersonalizationConfig.parallaxTiledColumnSpan,
                                                                                           value => PersonalizationConfig.setParallaxTiledColumnSpan(
                                                                                                        value), 2,
                                                                                           12, 1),
                                         "font:UI family": root.select(()
                                                                       => PersonalizationConfig.uiFontFamily,
                                                                       value => PersonalizationConfig.setFontFamily(
                                                                                    "ui", value),
                                                                       FontService.fontOptions),
                                         "font:Mono family": root.select(()
                                                                         => PersonalizationConfig.monoFontFamily,
                                                                         value => PersonalizationConfig.setFontFamily(
                                                                                      "mono", value),
                                                                         FontService.fontOptions),
                                         "font:Numeric family": root.select(()
                                                                            => PersonalizationConfig.numericFontFamily,
                                                                            value => PersonalizationConfig.setFontFamily(
                                                                                         "numeric", value),
                                                                            FontService.fontOptions),
                                         "font:Expressive family": root.select(()
                                                                               => PersonalizationConfig.expressiveFontFamily,
                                                                               value => PersonalizationConfig.setFontFamily(
                                                                                            "expressive",
                                                                                            value), FontService.fontOptions),
                                         "interface:Shell blur": root.toggle(()
                                                                             => PersonalizationConfig.shellBlurEnabled,
                                                                             value => PersonalizationConfig.setShellBlurEnabled(
                                                                                          value)),
                                         "interface:Shell blur xray": root.toggle(()
                                                                                  => PersonalizationConfig.shellBlurXray,
                                                                                  value => PersonalizationConfig.setShellBlurXray(
                                                                                               value)),
                                         "interface:Keep sidebars loaded": root.toggle(()
                                                                                       => PersonalizationConfig.keepSidebarsLoaded,
                                                                                       value => PersonalizationConfig.setKeepSidebarsLoaded(
                                                                                                    value)),
                                         "interface:Cursor theme": root.text(()
                                                                             => PersonalizationConfig.cursorTheme,
                                                                             value => ThemeService.setCursorTheme(
                                                                                          value)),
                                         "interface:Cursor size": root.spin(()
                                                                            => PersonalizationConfig.cursorSize,
                                                                            value => ThemeService.setCursorSize(
                                                                                         value), 12, 128, 1),
                                         "interface:Hide cursor while typing": root.toggle(()
                                                                                           => PersonalizationConfig.cursorHideWhenTyping,
                                                                                           value => ThemeService.setCursorHideWhenTyping(
                                                                                                        value)),
                                         "interface:Cursor idle timeout (ms)": root.spin(()
                                                                                         => PersonalizationConfig.cursorHideAfterInactiveMs,
                                                                                         value => ThemeService.setCursorHideAfterInactiveMs(
                                                                                                      value), 0,
                                                                                         5000, 100),
                                         "interface:Icon theme": root.text(()
                                                                           => PersonalizationConfig.iconTheme,
                                                                           value => ThemeService.setIconTheme(
                                                                                        value)),

                                         // ── Bar ──────────────────────────────────────────────────────
                                         "bar:Position": root.select(() => PersonalizationConfig.barPosition,
                                         value => PersonalizationConfig.setBarPosition(value),
                                         PersonalizationConfig.edgePositions),
                                         "bar:Overlay": root.toggle(() => PersonalizationConfig.barOverlay,
                                         value => PersonalizationConfig.setValue("barOverlay", value)),
                                         "bar:Show names": root.toggle(()
                                                                       => PersonalizationConfig.barShowNames,
                                                                       value => PersonalizationConfig.setBarShowNames(
                                                                                    value)),
                                         "bar:Show values": root.toggle(()
                                                                        => PersonalizationConfig.barShowValues,
                                                                        value => PersonalizationConfig.setBarShowValues(
                                                                                     value)),

                                         // ── Keystone ─────────────────────────────────────────────────
                                         "keystone:Enabled": root.toggle(() => PersonalizationConfig.keystoneEnabled,
                                                                         value => PersonalizationConfig.setValue(
                                                                                      "keystoneEnabled", value)),
                                         "keystone:Style": root.select(()
                                                                       => PersonalizationConfig.keystoneStyle,
                                                                       value => PersonalizationConfig.setKeystoneStyle(
                                                                                    value), PersonalizationConfig.keystoneStyles),
                                         "keystone:Overlay": root.toggle(()
                                                                         => PersonalizationConfig.keystoneOverlay,
                                                                         value => PersonalizationConfig.setValue(
                                                                                      "keystoneOverlay",
                                                                                      value)),
                                         "keystone:Position": root.select(()
                                                                          => PersonalizationConfig.keystonePosition,
                                                                          value => PersonalizationConfig.setKeystonePosition(
                                                                                       value), PersonalizationConfig.edgePositions),
                                         "keystone:Hover action": root.select(()
                                                                              => PersonalizationConfig.keystoneHoverAction,
                                                                              value => PersonalizationConfig.setValue(
                                                                                           "keystoneHoverAction",
                                                                                           value), PersonalizationConfig.availableKeystoneHoverActionOptions),
                                         "keystone:Left click action": root.select(()
                                                                                   => PersonalizationConfig.keystoneLeftClickAction,
                                                                                   value => PersonalizationConfig.setKeystoneAction(
                                                                                                "leftClick",
                                                                                                value), PersonalizationConfig.keystoneActionOptions),
                                         "keystone:Middle click action": root.select(()
                                                                                     => PersonalizationConfig.keystoneMiddleClickAction,
                                                                                     value => PersonalizationConfig.setKeystoneAction(
                                                                                                  "middleClick",
                                                                                                  value), PersonalizationConfig.keystoneActionOptions),
                                         "keystone:Media progress style": root.select(()
                                                                                      => PersonalizationConfig.keystoneMediaProgressStyle,
                                                                                      value => PersonalizationConfig.setKeystoneMediaProgressStyle(
                                                                                                   value), PersonalizationConfig.keystoneMediaProgressOptions),
                                         "keystone:Media cover style": root.select(()
                                                                                   => PersonalizationConfig.keystoneMediaCoverStyle,
                                                                                   value => PersonalizationConfig.setKeystoneMediaCoverStyle(
                                                                                                value), PersonalizationConfig.keystoneMediaCoverOptions),
                                         "keystone:Media color style": root.select(()
                                                                                   => PersonalizationConfig.keystoneMediaColorStyle,
                                                                                   value => PersonalizationConfig.setKeystoneMediaColorStyle(
                                                                                                value), PersonalizationConfig.keystoneMediaColorOptions),
                                         "keystone:Hover open delay (ms)": root.spin(()
                                                                                     => PersonalizationConfig.keystoneHoverOpenDelay,
                                                                                     value => PersonalizationConfig.setKeystoneHoverOpenDelay(
                                                                                                  value), 0,
                                                                                     2000, 25),
                                         "keystone:Hover close delay (ms)": root.spin(()
                                                                                      => PersonalizationConfig.keystoneHoverCloseDelay,
                                                                                      value => PersonalizationConfig.setKeystoneHoverCloseDelay(
                                                                                                   value), 0,
                                                                                      2000, 25),
                                         "keystone:Show date": root.toggle(() =>
                                         !PersonalizationConfig.keystoneHideDate, value
                                         => PersonalizationConfig.setKeystoneHideDate(!value)),
                                         "keystone:Show names in long form": root.toggle(()
                                                                                         => PersonalizationConfig.keystoneLongShowNames,
                                                                                         value => PersonalizationConfig.setKeystoneLongShowNames(
                                                                                                      value)),
                                         "keystone:Show values in long form": root.toggle(()
                                                                                          => PersonalizationConfig.keystoneLongShowValues,
                                                                                          value => PersonalizationConfig.setKeystoneLongShowValues(
                                                                                                       value)),
                                         "keystone:Show monitor values in long form": root.toggle(()
                                                                                                  => PersonalizationConfig.keystoneLongShowMonitorValues,
                                                                                                  value => PersonalizationConfig.setKeystoneLongShowMonitorValues(
                                                                                                               value)),
                                         "keystone:Caps lock OSD": root.toggle(()
                                                                               => PersonalizationConfig.keystoneCapsLockOsd,
                                                                               value => PersonalizationConfig.setKeystoneCapsLockOsd(
                                                                                            value)),
                                         "keystone:Num lock OSD": root.toggle(()
                                                                              => PersonalizationConfig.keystoneNumLockOsd,
                                                                              value => PersonalizationConfig.setKeystoneNumLockOsd(
                                                                                           value)),
                                         "keystone:Keyhole card": root.select(()
                                                                              => PersonalizationConfig.keystoneKeyholeCard,
                                                                              value => PersonalizationConfig.setKeystoneKeyholeCard(
                                                                                           value), PersonalizationConfig.keystoneKeyholeCardOptions),

                                         // ── Wallpaper ────────────────────────────────────────────────
                                         "wallpaper:Fill mode": root.select(()
                                                                            => PersonalizationConfig.wallpaperFillMode,
                                                                            value => WallpaperService.setWallpaperFillMode(
                                                                                         value), PersonalizationConfig.fillModes),
                                         "wallpaper:Desktop backend": root.select(()
                                                                                  => PersonalizationConfig.desktopWallpaperBackend,
                                                                                  value => WallpaperService.setDesktopWallpaperBackend(
                                                                                               value), [
                                                                                      {
                                                                                          "value": "quickshell",
                                                                                          "label": I18n.tr(
                                                                                                       "Quickshell"),
                                                                                          "icon": "layers"
                                                                                      },
                                                                                      {
                                                                                          "value": "awww",
                                                                                          "label": "awww",
                                                                                          "icon": "animation"
                                                                                      }
                                                                                  ]),
                                         "wallpaper:Auto cycle": root.toggle(()
                                                                             => PersonalizationConfig.autoCycleEnabled,
                                                                             value => PersonalizationConfig.setAutoCycleEnabled(
                                                                                          value)),
                                         "wallpaper:Cycle mode": root.select(()
                                                                             => PersonalizationConfig.autoCycleMode,
                                                                             value => PersonalizationConfig.setAutoCycleMode(
                                                                                          value), [
                                                                                 {
                                                                                     "value": "interval",
                                                                                     "label": I18n.tr(
                                                                                                  "Interval"),
                                                                                     "icon": "timer"
                                                                                 },
                                                                                 {
                                                                                     "value": "time",
                                                                                     "label": I18n.tr(
                                                                                                  "Daily time"),
                                                                                     "icon": "schedule"
                                                                                 }
                                                                             ]),
                                         "wallpaper:Cycle interval (min)": root.spin(()
                                                                                     => PersonalizationConfig.autoCycleInterval,
                                                                                     value => PersonalizationConfig.setAutoCycleInterval(
                                                                                                  value), 5,
                                                                                     1440, 5),
                                         "wallpaper:Transition": root.select(()
                                                                             => PersonalizationConfig.wallpaperTransitionType,
                                                                             value => WallpaperService.setWallpaperTransitionType(
                                                                                          value), PersonalizationConfig.transitionTypes),
                                         "wallpaper:Transition duration (ms)": root.spin(()
                                                                                         => PersonalizationConfig.transitionDurationMs,
                                                                                         value => WallpaperService.setTransitionDurationMs(
                                                                                                      value), 100,
                                                                                         5000, 100),
                                         "wallpaper:Transition easing": root.select(()
                                                                                    => PersonalizationConfig.transitionEasingMode,
                                                                                    value => WallpaperService.setTransitionEasingMode(
                                                                                                 value), PersonalizationConfig.transitionEasingModes),
                                         "wallpaper:Overview": root.toggle(()
                                                                           => PersonalizationConfig.overviewEnabled,
                                                                           value => PersonalizationConfig.setOverviewEnabled(
                                                                                        value)),
                                         "wallpaper:Overview blur radius": root.slider(()
                                                                                       => PersonalizationConfig.overviewBlurRadius,
                                                                                       value => PersonalizationConfig.setOverviewBlurRadius(
                                                                                                    value), 0,
                                                                                       100, 1),
                                         "wallpaper:Overview dim": root.slider(()
                                                                               => PersonalizationConfig.overviewDim,
                                                                               value => PersonalizationConfig.setOverviewDim(
                                                                                            value), 0, 1,
                                                                               0.01),
                                         "wallpaper:Overview saturation": root.slider(()
                                                                                      => PersonalizationConfig.overviewSaturation,
                                                                                      value => PersonalizationConfig.setOverviewSaturation(
                                                                                                   value), 0,
                                                                                      2, 0.01),
                                         "wallpaper:Overview contrast": root.slider(()
                                                                                    => PersonalizationConfig.overviewContrast,
                                                                                    value => PersonalizationConfig.setOverviewContrast(
                                                                                                 value), 0.5,
                                                                                    2, 0.01),
                                         "wallpaper:Parallax": root.toggle(()
                                                                           => PersonalizationConfig.parallaxVerticalEnabled,
                                                                           value => PersonalizationConfig.setParallaxVerticalEnabled(
                                                                                        value)),
                                         "wallpaper:Parallax follows workspaces": root.toggle(()
                                                                                              => PersonalizationConfig.parallaxFollowWorkspaces,
                                                                                              value => PersonalizationConfig.setParallaxFollowWorkspaces(
                                                                                                           value)),
                                         "wallpaper:Parallax follows sidebars": root.toggle(()
                                                                                            => PersonalizationConfig.parallaxFollowSidebars,
                                                                                            value => PersonalizationConfig.setParallaxFollowSidebars(
                                                                                                         value)),
                                         "wallpaper:Parallax preferred scale": root.slider(()
                                                                                           => PersonalizationConfig.parallaxPreferredScale,
                                                                                           value => PersonalizationConfig.setParallaxPreferredScale(
                                                                                                        value), 1,
                                                                                           1.35, 0.01),

                                         // ── Desktop ──────────────────────────────────────────────────
                                         "desktop:Grid snap": root.toggle(()
                                                                          => PersonalizationConfig.desktopCardGridSnapEnabled,
                                                                          value => PersonalizationConfig.setDesktopCardGridSnapEnabled(
                                                                                       value)),
                                         "desktop:Grid visible while dragging": root.toggle(()
                                                                                            => PersonalizationConfig.desktopCardGridVisibleWhileDragging,
                                                                                            value => PersonalizationConfig.setDesktopCardGridVisibleWhileDragging(
                                                                                                         value)),

                                         // ── Spotlight ────────────────────────────────────────────────
                                         "spotlight:Application order": root.select(()
                                                                                    => UiPreferences.spotlightAppOrder,
                                                                                    value => UiPreferences.setSpotlightAppOrder(
                                                                                                 value), [
                                                                                        {
                                                                                            "value": "smart",
                                                                                            "label": I18n.tr("Smart")
                                                                                        },
                                                                                        {
                                                                                            "value": "most-used",
                                                                                            "label": I18n.tr("Most used")
                                                                                        },
                                                                                        {
                                                                                            "value": "recently-used",
                                                                                            "label": I18n.tr("Recently used")
                                                                                        },
                                                                                        {
                                                                                            "value": "name",
                                                                                            "label": I18n.tr("Name")
                                                                                        }
                                                                                    ]),
                                         "spotlight:Application layout": root.select(()
                                                                                     => UiPreferences.spotlightAppStyle,
                                                                                     value => UiPreferences.setSpotlightAppStyle(
                                                                                                  value), [
                                                                                         {
                                                                                             "value": "list",
                                                                                             "label": I18n.tr("List")
                                                                                         },
                                                                                         {
                                                                                             "value": "grid",
                                                                                             "label": I18n.tr("Grid")
                                                                                         }
                                                                                     ]),
                                         "spotlight:Search engine": root.select(()
                                                                                => UiPreferences.spotlightSearchEngine,
                                                                                value => UiPreferences.setSpotlightSearchEngine(
                                                                                             value), UiPreferences.searchEngines),
                                         "spotlight:Clipboard layout": root.select(()
                                                                                   => UiPreferences.spotlightClipboardStyle,
                                                                                   value => UiPreferences.setSpotlightClipboardStyle(
                                                                                                value), [
                                                                                       {
                                                                                           "value": "default",
                                                                                           "label": I18n.tr("Default")
                                                                                       },
                                                                                       {
                                                                                           "value": "details",
                                                                                           "label": I18n.tr("Details")
                                                                                       }
                                                                                   ]),

                                         // ── Language ─────────────────────────────────────────────────
                                         "language:Clock format": root.toggle(()
                                                                              => UiPreferences.useTwelveHourClock,
                                                                              value => UiPreferences.setUseTwelveHourClock(
                                                                                           value)),
                                         "language:Weather temperature": root.select(()
                                                                                      => UiPreferences.weatherTemperatureUnit,
                                                                                      value => UiPreferences.setWeatherTemperatureUnit(
                                                                                                   value), [
                                                                                          {
                                                                                              "value": "celsius",
                                                                                              "label": "°C"
                                                                                          },
                                                                                          {
                                                                                              "value": "fahrenheit",
                                                                                              "label": "°F"
                                                                                          }
                                                                                      ]),
                                         "language:Hardware temperature": root.select(()
                                                                                       => UiPreferences.systemTemperatureUnit,
                                                                                       value => UiPreferences.setSystemTemperatureUnit(
                                                                                                    value), [
                                                                                           {
                                                                                               "value": "celsius",
                                                                                               "label": "°C"
                                                                                           },
                                                                                           {
                                                                                               "value": "fahrenheit",
                                                                                               "label": "°F"
                                                                                           }
                                                                                       ]),

                                         // ── Sidebar clock ────────────────────────────────────────────
                                         "sidebar:Sides": root.spin(() => UiPreferences.sidebarCookieSides,                                                                    value => UiPreferences.setSidebarCookieSides(
                                                                                 value), 0, 40, 1),
                                         "sidebar:Constantly rotate": root.toggle(()
                                                                                  => UiPreferences.sidebarCookieConstantlyRotate,
                                                                                  value => UiPreferences.setSidebarCookieConstantlyRotate(
                                                                                               value)),
                                         "sidebar:Hour marks": root.toggle(()
                                                                           => UiPreferences.sidebarCookieHourMarks,
                                                                           value => UiPreferences.setSidebarCookieHourMarks(
                                                                                        value)),
                                         "sidebar:Digits in the middle": root.toggle(()
                                                                                     => UiPreferences.sidebarCookieTimeIndicators,
                                                                                     value => UiPreferences.setSidebarCookieTimeIndicators(
                                                                                                  value)),
                                         "sidebar:Snapshot interval (ms)": root.spin(()
                                                                                     => UiPreferences.systemMonitorIntervalMs,
                                                                                     value => UiPreferences.setSystemMonitorIntervalMs(
                                                                                                  value), 500,
                                                                                     60000, 100),

                                         // ── Horizontal clock ─────────────────────────────────────────
                                         "clock:Font size": root.spin(() => PersonalizationConfig.horizontalClockFontSize,
                                                                      value => PersonalizationConfig.setHorizontalClockFontSize(
                                                                                   value), 16, 28, 1),
                                         "clock:Weight": root.spin(()
                                                                   => PersonalizationConfig.horizontalClockAxes.wght,
                                                                   value => PersonalizationConfig.setHorizontalClockAxis(
                                                                                "wght", value), 1, 1000, 1),
                                         "clock:Width": root.spin(()
                                                                  => PersonalizationConfig.horizontalClockAxes.wdth,
                                                                  value => PersonalizationConfig.setHorizontalClockAxis(
                                                                               "wdth", value), 25, 151, 1),
                                         "clock:Optical size": root.spin(()
                                                                         => PersonalizationConfig.horizontalClockAxes.opsz,
                                                                         value => PersonalizationConfig.setHorizontalClockAxis(
                                                                                      "opsz", value), 6, 144, 1),
                                         "clock:Grade": root.spin(()
                                                                  => PersonalizationConfig.horizontalClockAxes.GRAD,
                                                                  value => PersonalizationConfig.setHorizontalClockAxis(
                                                                               "GRAD", value), 0, 100, 1),
                                         "clock:Roundness": root.spin(()
                                                                      => PersonalizationConfig.horizontalClockAxes.ROND,
                                                                      value => PersonalizationConfig.setHorizontalClockAxis(
                                                                                   "ROND", value), 0, 100, 1),
                                         "clock:Slant": root.spin(()
                                                                  => PersonalizationConfig.horizontalClockAxes.slnt,
                                                                  value => PersonalizationConfig.setHorizontalClockAxis(
                                                                               "slnt", value), -10, 0, 1),

                                         // ── Dock ─────────────────────────────────────────────────────
                                         "dock:Show dock": root.toggle(() => DockService.enabled,
                                                                       value => DockService.setOption("enabled", value)),
                                         "dock:Screen edge": root.select(() => DockService.position,
                                                                         value => DockService.setOption("position", value), [
                                                                             {
                                                                                 "value": "bottom",
                                                                                 "label": I18n.tr("Bottom")
                                                                             },
                                                                             {
                                                                                 "value": "left",
                                                                                 "label": I18n.tr("Left")
                                                                             },
                                                                             {
                                                                                 "value": "right",
                                                                                 "label": I18n.tr("Right")
                                                                             }
                                                                         ]),
                                         "dock:Surface style": root.select(() => DockService.surfaceStyle,
                                                                           value => DockService.setOption("surfaceStyle",
                                                                                                          value), [
                                                                               {
                                                                                   "value": "default",
                                                                                   "label": I18n.tr("Default")
                                                                               },
                                                                               {
                                                                                   "value": "notch",
                                                                                   "label": I18n.tr("Notch")
                                                                               }
                                                                           ]),
                                         "dock:Icon size": root.slider(() => DockService.iconSize,
                                                                       value => DockService.setOption("iconSize", value), 24,
                                                                       96, 1),
                                         "dock:Magnify on hover": root.toggle(() => DockService.magnification,
                                                                              value => DockService.setOption("magnification",
                                                                                                             value)),
                                         "dock:Magnification": root.slider(() => DockService.magnificationScale,
                                                                           value => DockService.setOption("magnificationScale",
                                                                                                          value), 1, 2.5,
                                                                           0.05),
                                         "dock:Automatically hide": root.toggle(() => DockService.autoHide,
                                                                                value => DockService.setOption("autoHide",
                                                                                                               value)),
                                         "dock:Bounce when launching": root.toggle(()
                                                                                   => DockService.launchBounce,
                                                                                   value => DockService.setOption("launchBounce",
                                                                                                                  value)),
                                         "dock:Show running indicators": root.toggle(()
                                                                                     => DockService.showIndicators,
                                                                                     value => DockService.setOption("showIndicators",
                                                                                                                    value)),
                                         "dock:Show recent applications": root.toggle(()
                                                                                      => DockService.showRecent,
                                                                                      value => DockService.setOption("showRecent",
                                                                                                                     value)),
                                         "dock:Show window thumbnails": root.toggle(()
                                                                                   => DockService.showThumbnails,
                                                                                   value => DockService.setOption("showThumbnails",
                                                                                                                  value)),
                                         "dock:Preview size": root.slider(() => DockService.previewSize,
                                                                          value => DockService.setOption("previewSize", value),
                                                                          80, 400, 10),
                                         "dock:Pin applications from the menu": root.toggle(()
                                                                                            => DockService.contextPinning,
                                                                                            value => DockService.setOption(
                                                                                                         "contextPinning",
                                                                                                         value))
                                     })

    function controlFor(key) {
        return root.controls[key] ?? null;
    }
}
