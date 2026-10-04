pragma Singleton
import QtQuick
import Quickshell
import qs.app.services

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
                                                                             value => PersonalizationConfig.setThemeMode(
                                                                                          value), [
                                                                                 {
                                                                                     "value": "dark",
                                                                                     "label": qsTr("Dark"),
                                                                                     "icon": "dark_mode"
                                                                                 },
                                                                                 {
                                                                                     "value": "light",
                                                                                     "label": qsTr("Light"),
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
                                         "lyrics:Backend": root.select(()
                                                                       => PersonalizationConfig.lyricSource,
                                                                       value => PersonalizationConfig.setLyricSource(
                                                                                    value), PersonalizationConfig.lyricSources),
                                         "lyrics:Timing offset (ms)": root.spin(() => PersonalizationConfig.lyricOffsetMs,
                                                                                value => PersonalizationConfig.setLyricOffsetMs(
                                                                                             value),
                                                                                PersonalizationConfig.lyricOffsetMinMs,
                                                                                PersonalizationConfig.lyricOffsetMaxMs,
                                                                                50),
                                         "lyrics:Font size": root.spin(() => PersonalizationConfig.lyricFontSize,
                                                                       value => PersonalizationConfig.setLyricFontSize(
                                                                                    value),
                                                                       PersonalizationConfig.lyricFontSizeMin,
                                                                       PersonalizationConfig.lyricFontSizeMax, 2),
                                         "lyrics:Tint from album art": root.toggle(()
                                                                                   => PersonalizationConfig.lyricAlbumArtTint,
                                                                                   value => PersonalizationConfig.setLyricAlbumArtTint(
                                                                                                value)),
                                         "interface:Matugen scheme": root.select(()
                                                                                 => PersonalizationConfig.matugenScheme,
                                                                                 value => PersonalizationConfig.setMatugenScheme(
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
                                                                             value => PersonalizationConfig.setCursorTheme(
                                                                                          value)),
                                         "interface:Cursor size": root.spin(()
                                                                            => PersonalizationConfig.cursorSize,
                                                                            value => PersonalizationConfig.setCursorSize(
                                                                                         value), 12, 128, 1),
                                         "interface:Hide cursor while typing": root.toggle(()
                                                                                           => PersonalizationConfig.cursorHideWhenTyping,
                                                                                           value => PersonalizationConfig.setCursorHideWhenTyping(
                                                                                                        value)),
                                         "interface:Cursor idle timeout (ms)": root.spin(()
                                                                                         => PersonalizationConfig.cursorHideAfterInactiveMs,
                                                                                         value => PersonalizationConfig.setCursorHideAfterInactiveMs(
                                                                                                      value), 0,
                                                                                         5000, 100),
                                         "interface:Icon theme": root.text(()
                                                                           => PersonalizationConfig.iconTheme,
                                                                           value => PersonalizationConfig.setIconTheme(
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
                                                                            value => PersonalizationConfig.setWallpaperFillMode(
                                                                                         value), PersonalizationConfig.fillModes),
                                         "wallpaper:Desktop backend": root.select(()
                                                                                  => PersonalizationConfig.desktopWallpaperBackend,
                                                                                  value => PersonalizationConfig.setDesktopWallpaperBackend(
                                                                                               value), [
                                                                                      {
                                                                                          "value": "quickshell",
                                                                                          "label": qsTr(
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
                                                                                     "label": qsTr("Interval"),
                                                                                     "icon": "timer"
                                                                                 },
                                                                                 {
                                                                                     "value": "time",
                                                                                     "label": qsTr(
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
                                                                             value => PersonalizationConfig.setWallpaperTransitionType(
                                                                                          value), PersonalizationConfig.transitionTypes),
                                         "wallpaper:Transition duration (ms)": root.spin(()
                                                                                         => PersonalizationConfig.transitionDurationMs,
                                                                                         value => PersonalizationConfig.setTransitionDurationMs(
                                                                                                      value), 100,
                                                                                         5000, 100),
                                         "wallpaper:Transition easing": root.select(()
                                                                                    => PersonalizationConfig.transitionEasingMode,
                                                                                    value => PersonalizationConfig.setTransitionEasingMode(
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
                                                                                                         value))
                                     })

    function controlFor(key) {
        return root.controls[key] ?? null;
    }
}
