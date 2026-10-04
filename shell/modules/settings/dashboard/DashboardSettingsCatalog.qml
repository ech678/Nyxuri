pragma Singleton
import QtQuick
import Quickshell

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
            "title": qsTr("Interface"),
            "icon": "palette",
            "cards": [
                {
                    "type": "select",
                    "key": "interface:Settings panel style",
                    "title": qsTr("Settings panel style"),
                    "icon": "dashboard_customize",
                    "w": 4,
                    "kw": "settings panel style default minimal dashboard"
                },
                {
                    "type": "select",
                    "key": "interface:Theme mode",
                    "title": qsTr("Theme mode"),
                    "icon": "contrast"
                },
                {
                    "type": "combo",
                    "key": "interface:Matugen scheme",
                    "title": qsTr("Matugen scheme"),
                    "icon": "colors"
                },
                {
                    "type": "combo",
                    "key": "interface:Super key style",
                    "title": qsTr("Super key style"),
                    "icon": "keyboard_command_key"
                },
                {
                    "type": "select",
                    "key": "interface:Lock screen style",
                    "title": qsTr("Lock screen style"),
                    "icon": "lock"
                },
                {
                    "type": "slider",
                    "key": "interface:Shell background opacity",
                    "title": qsTr("Shell background opacity"),
                    "icon": "opacity"
                },
                {
                    "type": "toggle",
                    "key": "interface:Shell blur",
                    "title": qsTr("Shell blur"),
                    "icon": "blur_on"
                },
                {
                    "type": "toggle",
                    "key": "interface:Shell blur xray",
                    "title": qsTr("Shell blur xray"),
                    "icon": "blur_circular"
                },
                {
                    "type": "toggle",
                    "key": "interface:Keep sidebars loaded",
                    "title": qsTr("Keep sidebars loaded"),
                    "icon": "vertical_split"
                },
                {
                    "type": "toggle",
                    "key": "interface:Hide cursor while typing",
                    "title": qsTr("Hide cursor while typing"),
                    "icon": "mouse"
                },
                {
                    "type": "spin",
                    "key": "interface:Cursor size",
                    "title": qsTr("Cursor size"),
                    "icon": "arrow_selector_tool"
                },
                {
                    "type": "spin",
                    "key": "interface:Cursor idle timeout (ms)",
                    "title": qsTr("Cursor idle timeout"),
                    "icon": "timer"
                },
                {
                    "type": "text",
                    "key": "interface:Cursor theme",
                    "title": qsTr("Cursor theme"),
                    "icon": "mouse"
                },
                {
                    "type": "text",
                    "key": "interface:Icon theme",
                    "title": qsTr("Icon theme"),
                    "icon": "apps"
                }
            ]
        },
        {
            "title": qsTr("Bar"),
            "icon": "toolbar",
            "cards": [
                {
                    "type": "select",
                    "key": "bar:Position",
                    "title": qsTr("Position"),
                    "icon": "swap_horiz",
                    "w": 2
                },
                {
                    "type": "toggle",
                    "key": "bar:Show names",
                    "title": qsTr("Show names"),
                    "icon": "label"
                },
                {
                    "type": "toggle",
                    "key": "bar:Show values",
                    "title": qsTr("Show values"),
                    "icon": "123"
                },
                {
                    "type": "toggle",
                    "key": "bar:Overlay",
                    "title": qsTr("Overlay"),
                    "icon": "layers"
                }
            ]
        },
        {
            "title": qsTr("Keystone"),
            "icon": "toggle_off",
            "cards": [
                {
                    "type": "combo",
                    "key": "keystone:Style",
                    "title": qsTr("Style"),
                    "icon": "style",
                    "w": 2
                },
                {
                    "type": "select",
                    "key": "keystone:Position",
                    "title": qsTr("Position"),
                    "icon": "swap_horiz",
                    "w": 2
                },
                {
                    "type": "combo",
                    "key": "keystone:Hover action",
                    "title": qsTr("Hover action"),
                    "icon": "mouse"
                },
                {
                    "type": "combo",
                    "key": "keystone:Left click action",
                    "title": qsTr("Left click action"),
                    "icon": "ads_click"
                },
                {
                    "type": "combo",
                    "key": "keystone:Middle click action",
                    "title": qsTr("Middle click action"),
                    "icon": "ads_click"
                },
                {
                    "type": "combo",
                    "key": "keystone:Keyhole card",
                    "title": qsTr("Keyhole card"),
                    "icon": "door_front"
                },
                {
                    "type": "combo",
                    "key": "keystone:Media progress style",
                    "title": qsTr("Media progress style"),
                    "icon": "linear_scale"
                },
                {
                    "type": "combo",
                    "key": "keystone:Media cover style",
                    "title": qsTr("Media cover style"),
                    "icon": "album"
                },
                {
                    "type": "combo",
                    "key": "keystone:Media color style",
                    "title": qsTr("Media color style"),
                    "icon": "palette"
                },
                {
                    "type": "spin",
                    "key": "keystone:Hover open delay (ms)",
                    "title": qsTr("Hover open delay"),
                    "icon": "timer"
                },
                {
                    "type": "spin",
                    "key": "keystone:Hover close delay (ms)",
                    "title": qsTr("Hover close delay"),
                    "icon": "timer_off"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Overlay",
                    "title": qsTr("Overlay"),
                    "icon": "layers"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show date",
                    "title": qsTr("Show date"),
                    "icon": "calendar_today"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Caps lock OSD",
                    "title": qsTr("Caps lock OSD"),
                    "icon": "keyboard_capslock"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Num lock OSD",
                    "title": qsTr("Num lock OSD"),
                    "icon": "keyboard"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show names in long form",
                    "title": qsTr("Long form names"),
                    "icon": "short_text"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show values in long form",
                    "title": qsTr("Long form values"),
                    "icon": "numbers"
                },
                {
                    "type": "toggle",
                    "key": "keystone:Show monitor values in long form",
                    "title": qsTr("Long form monitor values"),
                    "icon": "monitor"
                }
            ]
        },
        {
            "title": qsTr("Wallpaper"),
            "icon": "wallpaper",
            "cards": [
                {
                    "type": "combo",
                    "key": "wallpaper:Fill mode",
                    "title": qsTr("Fill mode"),
                    "icon": "fit_screen"
                },
                {
                    "type": "select",
                    "key": "wallpaper:Desktop backend",
                    "title": qsTr("Desktop backend"),
                    "icon": "layers"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Auto cycle",
                    "title": qsTr("Auto cycle"),
                    "icon": "autorenew"
                },
                {
                    "type": "select",
                    "key": "wallpaper:Cycle mode",
                    "title": qsTr("Cycle mode"),
                    "icon": "schedule"
                },
                {
                    "type": "spin",
                    "key": "wallpaper:Cycle interval (min)",
                    "title": qsTr("Cycle interval"),
                    "icon": "timer"
                },
                {
                    "type": "combo",
                    "key": "wallpaper:Transition",
                    "title": qsTr("Transition"),
                    "icon": "animation"
                },
                {
                    "type": "spin",
                    "key": "wallpaper:Transition duration (ms)",
                    "title": qsTr("Transition duration"),
                    "icon": "speed"
                },
                {
                    "type": "combo",
                    "key": "wallpaper:Transition easing",
                    "title": qsTr("Transition easing"),
                    "icon": "show_chart"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Overview",
                    "title": qsTr("Overview"),
                    "icon": "grid_view"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview blur radius",
                    "title": qsTr("Overview blur radius"),
                    "icon": "blur_on"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview dim",
                    "title": qsTr("Overview dim"),
                    "icon": "brightness_4"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview saturation",
                    "title": qsTr("Overview saturation"),
                    "icon": "water_drop"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Overview contrast",
                    "title": qsTr("Overview contrast"),
                    "icon": "contrast"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Parallax",
                    "title": qsTr("Parallax"),
                    "icon": "3d_rotation"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Parallax follows workspaces",
                    "title": qsTr("Parallax follows workspaces"),
                    "icon": "space_dashboard"
                },
                {
                    "type": "toggle",
                    "key": "wallpaper:Parallax follows sidebars",
                    "title": qsTr("Parallax follows sidebars"),
                    "icon": "vertical_split"
                },
                {
                    "type": "slider",
                    "key": "wallpaper:Parallax preferred scale",
                    "title": qsTr("Parallax preferred scale"),
                    "icon": "zoom_in"
                }
            ]
        },
        {
            "title": qsTr("Desktop"),
            "icon": "desktop_windows",
            "cards": [
                {
                    "type": "toggle",
                    "key": "desktop:Grid snap",
                    "title": qsTr("Grid snap"),
                    "icon": "grid_on"
                },
                {
                    "type": "toggle",
                    "key": "desktop:Grid visible while dragging",
                    "title": qsTr("Grid visible while dragging"),
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
