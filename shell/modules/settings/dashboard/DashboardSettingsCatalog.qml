pragma Singleton
import QtQuick
import Quickshell
import qs.shared.i18n

// Section layout for the dashboard settings grid. Mirrors end4-pC's
// DashboardSettingsCatalog structure (sections -> cards, each card naming a
// control key and a tile type) but the keys are nyxuri's own.
//
// end4-pC's catalog carries 307 keys over its own Config.options schema; none of
// them resolve here, so the sections are re-authored against nyxuri's
// PersonalizationConfig. The layout engine and card vocabulary are unchanged.
QtObject {
    id: root

    readonly property var sections: [
        {
            "title": I18n.tr("Interface"),
            "icon": "palette",
            "cards": [
                {
                    // Upstream keeps this one outside the sections as a "hero"
                    // tile; nyxuri has no hero row, so it stays the first card
                    // of Interface. Span comes from baseSpan("style").
                    "type": "style",
                    "key": "interface:Settings panel style",
                    "title": I18n.tr("Settings panel style"),
                    "icon": "dashboard_customize",
                    "kw": "settings panel style default minimal dashboard window overlay"
                },
                {
                    "type": "select",
                    "key": "interface:Theme mode",
                    "title": I18n.tr("Theme mode"),
                    "icon": "contrast"
                },
                {
                    // Rendered as the wide `palette` tile (span [4,1]) rather
                    // than a combo: nine schemes do not fit a dropdown and the
                    // grid has the room. Span comes from baseSpan("palette").
                    "type": "palette",
                    "key": "interface:Matugen scheme",
                    "title": I18n.tr("Palette style"),
                    "icon": "auto_awesome",
                    "kw": "palette style scheme auto content expressive fidelity fruit salad monochrome neutral rainbow tonal spot vibrant matugen"
                },
                {
                    "type": "combo",
                    "key": "interface:Super key style",
                    "title": I18n.tr("Super key style"),
                    "icon": "keyboard_command_key"
                },
                {
                    "type": "select",
                    "key": "interface:Lock screen style",
                    "title": I18n.tr("Lock screen style"),
                    "icon": "lock"
                },
                {
                    "type": "slider",
                    "key": "interface:Shell background opacity",
                    "title": I18n.tr("Shell background opacity"),
                    "icon": "opacity"
                },
                {
                    "type": "toggle",
                    "key": "interface:Shell blur",
                    "title": I18n.tr("Shell blur"),
                    "icon": "blur_on"
                },
                {
                    "type": "toggle",
                    "key": "interface:Shell blur xray",
                    "title": I18n.tr("Shell blur xray"),
                    "icon": "blur_circular"
                },
                {
                    "type": "toggle",
                    "key": "interface:Keep sidebars loaded",
                    "title": I18n.tr("Keep sidebars loaded"),
                    "icon": "vertical_split"
                },
                {
                    "type": "toggle",
                    "key": "interface:Hide cursor while typing",
                    "title": I18n.tr("Hide cursor while typing"),
                    "icon": "mouse"
                },
                {
                    "type": "spin",
                    "key": "interface:Cursor size",
                    "title": I18n.tr("Cursor size"),
                    "icon": "arrow_selector_tool"
                },
                {
                    "type": "spin",
                    "key": "interface:Cursor idle timeout (ms)",
                    "title": I18n.tr("Cursor idle timeout"),
                    "icon": "timer"
                },
                {
                    "type": "text",
                    "key": "interface:Cursor theme",
                    "title": I18n.tr("Cursor theme"),
                    "icon": "mouse"
                },
                {
                    "type": "text",
                    "key": "interface:Icon theme",
                    "title": I18n.tr("Icon theme"),
                    "icon": "apps"
                },
                {
                    // Two sidebars share one card shape; the options are left/right.
                    "type": "select",
                    "key": "interface:Dashboard sidebar side",
                    "title": I18n.tr("Dashboard sidebar side"),
                    "icon": "splitscreen_left"
                },
                {
                    "type": "select",
                    "key": "interface:Quick settings sidebar side",
                    "title": I18n.tr("Quick settings sidebar side"),
                    "icon": "splitscreen_right"
                },
                {
                    // Font pickers are searchable combos: the option set is every
                    // installed family, far too long for a flat select row.
                    "type": "combo",
                    "key": "font:UI family",
                    "title": I18n.tr("UI family"),
                    "icon": "text_fields",
                    "kw": "font ui interface text family"
                },
                {
                    "type": "combo",
                    "key": "font:Mono family",
                    "title": I18n.tr("Mono family"),
                    "icon": "code",
                    "kw": "font monospace mono terminal code family"
                },
                {
                    "type": "combo",
                    "key": "font:Numeric family",
                    "title": I18n.tr("Numeric family"),
                    "icon": "pin",
                    "kw": "font numeric numbers tabular digits family"
                },
                {
                    "type": "combo",
                    "key": "font:Expressive family",
                    "title": I18n.tr("Expressive family"),
                    "icon": "brand_family",
                    "kw": "font expressive display headline family"
                }
            ]
        },
        {
            "title": I18n.tr("Bar"),
            "icon": "toolbar",
            "cards": [
                {
                    "type": "select",
                    "key": "bar:Position",
                    "title": I18n.tr("Position"),
                    "icon": "swap_horiz",
                    "w": 2
                },
                {
                    "type": "toggle",
                    "key": "bar:Show names",
                    "title": I18n.tr("Show names"),
                    "icon": "label"
                },
                {
                    "type": "toggle",
                    "key": "bar:Show values",
                    "title": I18n.tr("Show values"),
                    "icon": "123"
                },
                {
                    "type": "toggle",
                    "key": "bar:Overlay",
                    "title": I18n.tr("Overlay"),
                    "icon": "layers"
                },
                {
                    "type": "barlayout",
                    "key": "bar:Layout",
                    "title": I18n.tr("Bar layout"),
                    "icon": "view_week",
                    "kw": "bar layout widgets order drag reorder lanes"
                }
            ]
        },
        {
            "title": I18n.tr("Keystone"),
            "icon": "toggle_off",
            "cards": [
                {
                    "type": "combo",
                    "key": "keystone:Style",
                    "title": I18n.tr("Style"),
                    "icon": "style",
                    "w": 2
                },
                {
                    "type": "select",
                    "key": "keystone:Position",
                    "title": I18n.tr("Position"),
                    "icon": "swap_horiz",
                    "w": 2
                },
                {
                    "type": "combo",
                    "key": "keystone:Hover action",
                    "title": I18n.tr("Hover action"),
                    "icon": "mouse"
                },
                {
                    "type": "combo",
                    "key": "keystone:Left click action",
                    "title": I18n.tr("Left click action"),
                    "icon": "ads_click"
                },
                {
                    "type": "combo",
                    "key": "keystone:Middle click action",
                    "title": I18n.tr("Middle click action"),
                    "icon": "ads_click"
                },
                {
                    "type": "combo",
                    "key": "keystone:Keyhole card",
                    "title": I18n.tr("Keyhole card"),
                    "icon": "door_front"
                },
                {
                    "type": "combo",
                    "key": "keystone:Media progress style",
                    "title": I18n.tr("Media progress style"),
                    "icon": "linear_scale"
                },
                {
                    "type": "combo",
                    "key": "keystone:Media cover style",
                    "title": I18n.tr("Media cover style"),
                    "icon": "album"
                },
                {
                    "type": "combo",
                    "key": "keystone:Media color style",
                    "title": I18n.tr("Media color style"),
                    "icon": "palette"
                },
                {
                    "type": "spin",
                    "key": "keystone:Hover open delay (ms)",
                    "title": I18n.tr("Hover open delay"),
                    "icon": "timer"
                },
                {
                    "type": "spin",
                    "key": "keystone:Hover close delay (ms)",
                    "title": I18n.tr("Hover close delay"),
                    "icon": "timer_off"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Overlay",
                    "title": I18n.tr("Overlay"),
                    "icon": "layers"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show date",
                    "title": I18n.tr("Show date"),
                    "icon": "calendar_today"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Caps lock OSD",
                    "title": I18n.tr("Caps lock OSD"),
                    "icon": "keyboard_capslock"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Num lock OSD",
                    "title": I18n.tr("Num lock OSD"),
                    "icon": "keyboard"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show names in long form",
                    "title": I18n.tr("Long form names"),
                    "icon": "short_text"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show values in long form",
                    "title": I18n.tr("Long form values"),
                    "icon": "numbers"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show monitor values in long form",
                    "title": I18n.tr("Long form monitor values"),
                    "icon": "monitor"
                }
            ]
        },
        {
            "title": I18n.tr("Media"),
            "icon": "lyrics",
            "cards": [
                {
                    "type": "select",
                    "key": "lyrics:Backend",
                    "title": I18n.tr("Lyric source"),
                    "icon": "cloud_download",
                    "w": 2,
                    "kw": "lyrics kugou lrclib source backend provider 歌词 来源"
                },
                {
                    "type": "spin",
                    "key": "lyrics:Timing offset (ms)",
                    "title": I18n.tr("Timing offset"),
                    "icon": "timer",
                    "kw": "lyrics offset delay timing sync 歌词 偏移 延迟"
                },
                {
                    "type": "spin",
                    "key": "lyrics:Font size",
                    "title": I18n.tr("Font size"),
                    "icon": "format_size",
                    "kw": "lyrics font size text 歌词 字号"
                },
                {
                    "type": "toggle",
                    "key": "lyrics:Tint from album art",
                    "title": I18n.tr("Tint from album art"),
                    "icon": "palette",
                    "kw": "lyrics album art colour color palette extract 歌词 封面 取色"
                }
            ]
        },
        {
            "title": I18n.tr("Wallpaper"),
            "icon": "wallpaper",
            "cards": [
                {
                    "type": "combo",
                    "key": "wallpaper:Fill mode",
                    "title": I18n.tr("Fill mode"),
                    "icon": "fit_screen"
                },

                {
                    "type": "toggle",
                    "key": "wallpaper:Auto cycle",
                    "title": I18n.tr("Auto cycle"),
                    "icon": "autorenew"
                },
                {
                    "type": "select",
                    "key": "wallpaper:Cycle mode",
                    "title": I18n.tr("Cycle mode"),
                    "icon": "schedule"
                },
                {
                    "type": "spin",
                    "key": "wallpaper:Cycle interval (min)",
                    "title": I18n.tr("Cycle interval"),
                    "icon": "timer"
                },
                {
                    "type": "combo",
                    "key": "wallpaper:Transition",
                    "title": I18n.tr("Transition"),
                    "icon": "animation"
                },
                {
                    "type": "spin",
                    "key": "wallpaper:Transition duration (ms)",
                    "title": I18n.tr("Transition duration"),
                    "icon": "speed"
                },
                {
                    "type": "combo",
                    "key": "wallpaper:Transition easing",
                    "title": I18n.tr("Transition easing"),
                    "icon": "show_chart"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Overview",
                    "title": I18n.tr("Overview"),
                    "icon": "grid_view"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview blur radius",
                    "title": I18n.tr("Overview blur radius"),
                    "icon": "blur_on"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview dim",
                    "title": I18n.tr("Overview dim"),
                    "icon": "brightness_4"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview saturation",
                    "title": I18n.tr("Overview saturation"),
                    "icon": "water_drop"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview contrast",
                    "title": I18n.tr("Overview contrast"),
                    "icon": "contrast"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Parallax",
                    "title": I18n.tr("Parallax"),
                    "icon": "3d_rotation"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Parallax follows workspaces",
                    "title": I18n.tr("Parallax follows workspaces"),
                    "icon": "space_dashboard"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Parallax follows sidebars",
                    "title": I18n.tr("Parallax follows sidebars"),
                    "icon": "vertical_split"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Parallax preferred scale",
                    "title": I18n.tr("Parallax preferred scale"),
                    "icon": "zoom_in"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Per-monitor wallpaper",
                    "title": I18n.tr("Per-monitor wallpaper"),
                    "icon": "wallpaper_slideshow",
                    "kw": "wallpaper per monitor screen independent"
                },
                {
                    "type": "combo",
                    "key": "wallpaper:Desktop transition",
                    "title": I18n.tr("Desktop transition"),
                    "icon": "transition_fade",
                    "kw": "wallpaper transition fade wipe"
                },
                {
                    "type": "combo",
                    "key": "wallpaper:Overview transition",
                    "title": I18n.tr("Overview transition"),
                    "icon": "grid_view",
                    "kw": "overview wallpaper transition"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Overview use desktop wallpaper",
                    "title": I18n.tr("Overview use desktop wallpaper"),
                    "icon": "wallpaper",
                    "kw": "overview wallpaper desktop reuse"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Parallax follow tiled columns",
                    "title": I18n.tr("Parallax follow tiled columns"),
                    "icon": "view_column",
                    "kw": "parallax columns wallpaper scroll"
                },
                {
                    "type": "spin",
                    "key": "wallpaper:Parallax tiled column span",
                    "title": I18n.tr("Parallax tiled column span"),
                    "icon": "width",
                    "kw": "parallax span columns wallpaper"
                }
            ]
        },
        {
            "title": I18n.tr("Desktop"),
            "icon": "desktop_windows",
            "cards": [
                {
                    "type": "toggle",
                    "key": "desktop:Grid snap",
                    "title": I18n.tr("Grid snap"),
                    "icon": "grid_on"
                },
                {
                    "type": "toggle",
                    "key": "desktop:Grid visible while dragging",
                    "title": I18n.tr("Grid visible while dragging"),
                    "icon": "grid_4x4"
                }
            ]
        }
    ]

    // Flat lookup so a page can reuse a control without restating its card.
    readonly property var cardIndex: {
        const index = {};
        root.sections.forEach(section => {
            section.cards.forEach(card => {
                index[card.key] = card;
            });
        });
        return index;
    }

    function controlFor(key) {
        return SettingsControlCatalog.controlFor(key);
    }
}
