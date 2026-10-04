.import "../../shared/i18n/Translations.js" as I18n
// Names extracted from the bundled action catalog. IDs are language-independent.
function translated(name) {
    switch (name) {
    case "Weather sidebar: toggle": return I18n.tr("Weather sidebar: toggle", "NiriActions");
    case "Sidebar drawer: toggle": return I18n.tr("Sidebar drawer: toggle", "NiriActions");
    case "Spotlight: Commands": return I18n.tr("Spotlight: Commands", "NiriActions");
    case "Spotlight: Calculator": return I18n.tr("Spotlight: Calculator", "NiriActions");
    case "Spotlight: Currency": return I18n.tr("Spotlight: Currency", "NiriActions");
    case "Spotlight: Time zone": return I18n.tr("Spotlight: Time zone", "NiriActions");
    case "Spotlight: Light theme": return I18n.tr("Spotlight: Light theme", "NiriActions");
    case "Spotlight: Dark theme": return I18n.tr("Spotlight: Dark theme", "NiriActions");
    case "Spotlight: Search settings": return I18n.tr("Spotlight: Search settings", "NiriActions");
    case "Spotlight: Search IPC actions": return I18n.tr("Spotlight: Search IPC actions", "NiriActions");
    case "Spotlight: Location picker": return I18n.tr("Spotlight: Location picker", "NiriActions");

    case "Spotlight: Search": return I18n.tr("Spotlight: Search", "NiriActions");
    case "Spotlight: Find files": return I18n.tr("Spotlight: Find files", "NiriActions");
    case "Quit": return I18n.tr("Quit", "NiriActions");
    case "Suspend": return I18n.tr("Suspend", "NiriActions");
    case "Power off monitors": return I18n.tr("Power off monitors", "NiriActions");
    case "Power on monitors": return I18n.tr("Power on monitors", "NiriActions");
    case "Toggle debug tint": return I18n.tr("Toggle debug tint", "NiriActions");
    case "Debug toggle opaque regions": return I18n.tr("Debug toggle opaque regions", "NiriActions");
    case "Debug toggle damage": return I18n.tr("Debug toggle damage", "NiriActions");
    case "Do screen transition": return I18n.tr("Do screen transition", "NiriActions");
    case "Screenshot": return I18n.tr("Screenshot", "NiriActions");
    case "Screenshot screen": return I18n.tr("Screenshot screen", "NiriActions");
    case "Screenshot window": return I18n.tr("Screenshot window", "NiriActions");
    case "Toggle keyboard shortcuts inhibit": return I18n.tr("Toggle keyboard shortcuts inhibit", "NiriActions");
    case "Close window": return I18n.tr("Close window", "NiriActions");
    case "Fullscreen window": return I18n.tr("Fullscreen window", "NiriActions");
    case "Toggle windowed fullscreen": return I18n.tr("Toggle windowed fullscreen", "NiriActions");
    case "Focus window in column": return I18n.tr("Focus window in column", "NiriActions");
    case "Focus window previous": return I18n.tr("Focus window previous", "NiriActions");
    case "Focus column left": return I18n.tr("Focus column left", "NiriActions");
    case "Focus column right": return I18n.tr("Focus column right", "NiriActions");
    case "Focus column first": return I18n.tr("Focus column first", "NiriActions");
    case "Focus column last": return I18n.tr("Focus column last", "NiriActions");
    case "Focus column right or first": return I18n.tr("Focus column right or first", "NiriActions");
    case "Focus column left or last": return I18n.tr("Focus column left or last", "NiriActions");
    case "Focus column": return I18n.tr("Focus column", "NiriActions");
    case "Focus window or monitor up": return I18n.tr("Focus window or monitor up", "NiriActions");
    case "Focus window or monitor down": return I18n.tr("Focus window or monitor down", "NiriActions");
    case "Focus column or monitor left": return I18n.tr("Focus column or monitor left", "NiriActions");
    case "Focus column or monitor right": return I18n.tr("Focus column or monitor right", "NiriActions");
    case "Focus window down": return I18n.tr("Focus window down", "NiriActions");
    case "Focus window up": return I18n.tr("Focus window up", "NiriActions");
    case "Focus window down or column left": return I18n.tr("Focus window down or column left", "NiriActions");
    case "Focus window down or column right": return I18n.tr("Focus window down or column right", "NiriActions");
    case "Focus window up or column left": return I18n.tr("Focus window up or column left", "NiriActions");
    case "Focus window up or column right": return I18n.tr("Focus window up or column right", "NiriActions");
    case "Focus window or workspace down": return I18n.tr("Focus window or workspace down", "NiriActions");
    case "Focus window or workspace up": return I18n.tr("Focus window or workspace up", "NiriActions");
    case "Focus window top": return I18n.tr("Focus window top", "NiriActions");
    case "Focus window bottom": return I18n.tr("Focus window bottom", "NiriActions");
    case "Focus window down or top": return I18n.tr("Focus window down or top", "NiriActions");
    case "Focus window up or bottom": return I18n.tr("Focus window up or bottom", "NiriActions");
    case "Move column left": return I18n.tr("Move column left", "NiriActions");
    case "Move column right": return I18n.tr("Move column right", "NiriActions");
    case "Move column to first": return I18n.tr("Move column to first", "NiriActions");
    case "Move column to last": return I18n.tr("Move column to last", "NiriActions");
    case "Move column left or to monitor left": return I18n.tr("Move column left or to monitor left", "NiriActions");
    case "Move column right or to monitor right": return I18n.tr("Move column right or to monitor right", "NiriActions");
    case "Move column to index": return I18n.tr("Move column to index", "NiriActions");
    case "Move window down": return I18n.tr("Move window down", "NiriActions");
    case "Move window up": return I18n.tr("Move window up", "NiriActions");
    case "Move window down or to workspace down": return I18n.tr("Move window down or to workspace down", "NiriActions");
    case "Move window up or to workspace up": return I18n.tr("Move window up or to workspace up", "NiriActions");
    case "Consume or expel window left": return I18n.tr("Consume or expel window left", "NiriActions");
    case "Consume or expel window right": return I18n.tr("Consume or expel window right", "NiriActions");
    case "Consume window into column": return I18n.tr("Consume window into column", "NiriActions");
    case "Expel window from column": return I18n.tr("Expel window from column", "NiriActions");
    case "Swap window left": return I18n.tr("Swap window left", "NiriActions");
    case "Swap window right": return I18n.tr("Swap window right", "NiriActions");
    case "Toggle column tabbed display": return I18n.tr("Toggle column tabbed display", "NiriActions");
    case "Set column display": return I18n.tr("Set column display", "NiriActions");
    case "Center column": return I18n.tr("Center column", "NiriActions");
    case "Center window": return I18n.tr("Center window", "NiriActions");
    case "Center visible columns": return I18n.tr("Center visible columns", "NiriActions");
    case "Focus workspace down": return I18n.tr("Focus workspace down", "NiriActions");
    case "Focus workspace up": return I18n.tr("Focus workspace up", "NiriActions");
    case "Focus workspace": return I18n.tr("Focus workspace", "NiriActions");
    case "Focus workspace previous": return I18n.tr("Focus workspace previous", "NiriActions");
    case "Move window to workspace down": return I18n.tr("Move window to workspace down", "NiriActions");
    case "Move window to workspace up": return I18n.tr("Move window to workspace up", "NiriActions");
    case "Move window to workspace": return I18n.tr("Move window to workspace", "NiriActions");
    case "Move column to workspace down": return I18n.tr("Move column to workspace down", "NiriActions");
    case "Move column to workspace up": return I18n.tr("Move column to workspace up", "NiriActions");
    case "Move column to workspace": return I18n.tr("Move column to workspace", "NiriActions");
    case "Move workspace down": return I18n.tr("Move workspace down", "NiriActions");
    case "Move workspace up": return I18n.tr("Move workspace up", "NiriActions");
    case "Move workspace to index": return I18n.tr("Move workspace to index", "NiriActions");
    case "Move workspace to monitor": return I18n.tr("Move workspace to monitor", "NiriActions");
    case "Set workspace name": return I18n.tr("Set workspace name", "NiriActions");
    case "Unset workspace name": return I18n.tr("Unset workspace name", "NiriActions");
    case "Focus monitor left": return I18n.tr("Focus monitor left", "NiriActions");
    case "Focus monitor right": return I18n.tr("Focus monitor right", "NiriActions");
    case "Focus monitor down": return I18n.tr("Focus monitor down", "NiriActions");
    case "Focus monitor up": return I18n.tr("Focus monitor up", "NiriActions");
    case "Focus monitor previous": return I18n.tr("Focus monitor previous", "NiriActions");
    case "Focus monitor next": return I18n.tr("Focus monitor next", "NiriActions");
    case "Focus monitor": return I18n.tr("Focus monitor", "NiriActions");
    case "Move window to monitor left": return I18n.tr("Move window to monitor left", "NiriActions");
    case "Move window to monitor right": return I18n.tr("Move window to monitor right", "NiriActions");
    case "Move window to monitor down": return I18n.tr("Move window to monitor down", "NiriActions");
    case "Move window to monitor up": return I18n.tr("Move window to monitor up", "NiriActions");
    case "Move window to monitor previous": return I18n.tr("Move window to monitor previous", "NiriActions");
    case "Move window to monitor next": return I18n.tr("Move window to monitor next", "NiriActions");
    case "Move window to monitor": return I18n.tr("Move window to monitor", "NiriActions");
    case "Move column to monitor left": return I18n.tr("Move column to monitor left", "NiriActions");
    case "Move column to monitor right": return I18n.tr("Move column to monitor right", "NiriActions");
    case "Move column to monitor down": return I18n.tr("Move column to monitor down", "NiriActions");
    case "Move column to monitor up": return I18n.tr("Move column to monitor up", "NiriActions");
    case "Move column to monitor previous": return I18n.tr("Move column to monitor previous", "NiriActions");
    case "Move column to monitor next": return I18n.tr("Move column to monitor next", "NiriActions");
    case "Move column to monitor": return I18n.tr("Move column to monitor", "NiriActions");
    case "Set window width": return I18n.tr("Set window width", "NiriActions");
    case "Set window height": return I18n.tr("Set window height", "NiriActions");
    case "Reset window height": return I18n.tr("Reset window height", "NiriActions");
    case "Switch preset column width": return I18n.tr("Switch preset column width", "NiriActions");
    case "Switch preset column width back": return I18n.tr("Switch preset column width back", "NiriActions");
    case "Switch preset window width": return I18n.tr("Switch preset window width", "NiriActions");
    case "Switch preset window width back": return I18n.tr("Switch preset window width back", "NiriActions");
    case "Switch preset window height": return I18n.tr("Switch preset window height", "NiriActions");
    case "Switch preset window height back": return I18n.tr("Switch preset window height back", "NiriActions");
    case "Maximize column": return I18n.tr("Maximize column", "NiriActions");
    case "Maximize window to edges": return I18n.tr("Maximize window to edges", "NiriActions");
    case "Set column width": return I18n.tr("Set column width", "NiriActions");
    case "Expand column to available width": return I18n.tr("Expand column to available width", "NiriActions");
    case "Switch layout": return I18n.tr("Switch layout", "NiriActions");
    case "Show hotkey overlay": return I18n.tr("Show hotkey overlay", "NiriActions");
    case "Move workspace to monitor left": return I18n.tr("Move workspace to monitor left", "NiriActions");
    case "Move workspace to monitor right": return I18n.tr("Move workspace to monitor right", "NiriActions");
    case "Move workspace to monitor down": return I18n.tr("Move workspace to monitor down", "NiriActions");
    case "Move workspace to monitor up": return I18n.tr("Move workspace to monitor up", "NiriActions");
    case "Move workspace to monitor previous": return I18n.tr("Move workspace to monitor previous", "NiriActions");
    case "Move workspace to monitor next": return I18n.tr("Move workspace to monitor next", "NiriActions");
    case "Toggle window floating": return I18n.tr("Toggle window floating", "NiriActions");
    case "Move window to floating": return I18n.tr("Move window to floating", "NiriActions");
    case "Move window to tiling": return I18n.tr("Move window to tiling", "NiriActions");
    case "Focus floating": return I18n.tr("Focus floating", "NiriActions");
    case "Focus tiling": return I18n.tr("Focus tiling", "NiriActions");
    case "Switch focus between floating and tiling": return I18n.tr("Switch focus between floating and tiling", "NiriActions");
    case "Toggle window rule opacity": return I18n.tr("Toggle window rule opacity", "NiriActions");
    case "Set dynamic cast window": return I18n.tr("Set dynamic cast window", "NiriActions");
    case "Set dynamic cast monitor": return I18n.tr("Set dynamic cast monitor", "NiriActions");
    case "Clear dynamic cast target": return I18n.tr("Clear dynamic cast target", "NiriActions");
    case "Toggle overview": return I18n.tr("Toggle overview", "NiriActions");
    case "Open overview": return I18n.tr("Open overview", "NiriActions");
    case "Close overview": return I18n.tr("Close overview", "NiriActions");
    case "Lock: open": return I18n.tr("Lock: open", "NiriActions");
    case "Lock: is locked": return I18n.tr("Lock: is locked", "NiriActions");
    case "Spotlight: toggle": return I18n.tr("Spotlight: toggle", "NiriActions");
    case "Spotlight: open": return I18n.tr("Spotlight: open", "NiriActions");
    case "Spotlight: close": return I18n.tr("Spotlight: close", "NiriActions");
    case "Spotlight: web": return I18n.tr("Spotlight: web", "NiriActions");
    case "Spotlight: open mode": return I18n.tr("Spotlight: open mode", "NiriActions");
    case "Wallpaper: set": return I18n.tr("Wallpaper: set", "NiriActions");
    case "Wallpaper: set for screen": return I18n.tr("Wallpaper: set for screen", "NiriActions");
    case "Wallpaper: clear": return I18n.tr("Wallpaper: clear", "NiriActions");
    case "Wallpaper: clear for screen": return I18n.tr("Wallpaper: clear for screen", "NiriActions");
    case "Wallpaper: previous": return I18n.tr("Wallpaper: previous", "NiriActions");
    case "Wallpaper: next": return I18n.tr("Wallpaper: next", "NiriActions");
    case "Wallpaper: random": return I18n.tr("Wallpaper: random", "NiriActions");
    case "Wallpaper: set folder": return I18n.tr("Wallpaper: set folder", "NiriActions");
    case "Control center: open": return I18n.tr("Control center: open", "NiriActions");
    case "Control center: close": return I18n.tr("Control center: close", "NiriActions");
    case "Control center: toggle": return I18n.tr("Control center: toggle", "NiriActions");
    case "Keystone: cancel record": return I18n.tr("Keystone: cancel record", "NiriActions");
    case "Keystone: close all others": return I18n.tr("Keystone: close all others", "NiriActions");
    case "Keystone: current style": return I18n.tr("Keystone: current style", "NiriActions");
    case "Keystone: dashboard": return I18n.tr("Keystone: dashboard", "NiriActions");
    case "Keystone: hub": return I18n.tr("Keystone: hub", "NiriActions");
    case "Keystone: lyrics": return I18n.tr("Keystone: lyrics", "NiriActions");
    case "Keystone: tools": return I18n.tr("Keystone: tools", "NiriActions");
    case "Sidebar: open": return I18n.tr("Sidebar: open", "NiriActions");
    case "Sidebar: close": return I18n.tr("Sidebar: close", "NiriActions");
    case "Sidebar: toggle": return I18n.tr("Sidebar: toggle", "NiriActions");
    case "Run program": return I18n.tr("Run program", "NiriActions");
    case "Run shell command": return I18n.tr("Run shell command", "NiriActions");
    case "Spotlight: open applications": return I18n.tr("Spotlight: open applications", "NiriActions");
    case "Spotlight: open clipboard": return I18n.tr("Spotlight: open clipboard", "NiriActions");
    case "Spotlight: open wallpaper picker": return I18n.tr("Spotlight: open wallpaper picker", "NiriActions");
    case "Control center: open Account": return I18n.tr("Control center: open Account", "NiriActions");
    case "Control center: open General": return I18n.tr("Control center: open General", "NiriActions");
    case "Control center: open Wallpaper": return I18n.tr("Control center: open Wallpaper", "NiriActions");
    case "Control center: open Theme": return I18n.tr("Control center: open Theme", "NiriActions");
    case "Control center: open Keystone": return I18n.tr("Control center: open Keystone", "NiriActions");
    case "Control center: open Advanced": return I18n.tr("Control center: open Advanced", "NiriActions");
    case "Control center: open Language & region": return I18n.tr("Control center: open Language & region", "NiriActions");
    case "Control center: open current page": return I18n.tr("Control center: open current page", "NiriActions");
    case "Control center: toggle Account": return I18n.tr("Control center: toggle Account", "NiriActions");
    case "Control center: toggle General": return I18n.tr("Control center: toggle General", "NiriActions");
    case "Control center: toggle Wallpaper": return I18n.tr("Control center: toggle Wallpaper", "NiriActions");
    case "Control center: toggle Theme": return I18n.tr("Control center: toggle Theme", "NiriActions");
    case "Control center: toggle Keystone": return I18n.tr("Control center: toggle Keystone", "NiriActions");
    case "Control center: toggle Advanced": return I18n.tr("Control center: toggle Advanced", "NiriActions");
    case "Control center: toggle Language & region": return I18n.tr("Control center: toggle Language & region", "NiriActions");
    case "Control center: toggle current page": return I18n.tr("Control center: toggle current page", "NiriActions");
    case "Notifications: open": return I18n.tr("Notifications: open", "NiriActions");
    case "Quick settings: open": return I18n.tr("Quick settings: open", "NiriActions");
    case "Notifications: close": return I18n.tr("Notifications: close", "NiriActions");
    case "Quick settings: close": return I18n.tr("Quick settings: close", "NiriActions");
    case "Notifications: toggle": return I18n.tr("Notifications: toggle", "NiriActions");
    case "Quick settings: toggle": return I18n.tr("Quick settings: toggle", "NiriActions");
    case "Power menu: open": return I18n.tr("Power menu: open", "NiriActions");
    case "Power menu: close": return I18n.tr("Power menu: close", "NiriActions");
    case "Power menu: toggle": return I18n.tr("Power menu: toggle", "NiriActions");
    case "Shortcut map: open": return I18n.tr("Shortcut map: open", "NiriActions");
    case "Shortcut map: close": return I18n.tr("Shortcut map: close", "NiriActions");
    case "Shortcut map: toggle": return I18n.tr("Shortcut map: toggle", "NiriActions");
    default: return name;
    }
}

// Recognize only complete, known default commands; never infer an action from
// the bound key or a substring of an arbitrary shell script.
function commandName(expression) {
    const match = expression.trim().match(/^(spawn|spawn-sh)\s+((?:"(?:[^"\\]|\\.)*"\s*)+);?$/);
    if (!match)
        return "";
    let args;
    try {
        args = JSON.parse("[" + match[2].match(/"(?:[^"\\]|\\.)*"/g).join(",") + "]");
    } catch (error) {
        return "";
    }
    const commands = [
        { shell: "pkill orca || exec orca", argv: [], name: I18n.tr("Toggle screen reader", "NiriCommands") },
        { shell: "wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.1+ -l 1.0", argv: ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.1+", "-l", "1.0"], name: I18n.tr("Increase volume", "NiriCommands") },
        { shell: "wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.1-", argv: ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.1-"], name: I18n.tr("Decrease volume", "NiriCommands") },
        { shell: "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle", argv: ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], name: I18n.tr("Toggle audio mute", "NiriCommands") },
        { shell: "wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle", argv: ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"], name: I18n.tr("Toggle microphone mute", "NiriCommands") },
        { shell: "playerctl play-pause", argv: ["playerctl", "play-pause"], name: I18n.tr("Play/pause media", "NiriCommands") },
        { shell: "playerctl stop", argv: ["playerctl", "stop"], name: I18n.tr("Stop media", "NiriCommands") },
        { shell: "playerctl previous", argv: ["playerctl", "previous"], name: I18n.tr("Previous track", "NiriCommands") },
        { shell: "playerctl next", argv: ["playerctl", "next"], name: I18n.tr("Next track", "NiriCommands") },
        { shell: "brightnessctl --class=backlight set +10%", argv: ["brightnessctl", "--class=backlight", "set", "+10%"], name: I18n.tr("Increase screen brightness", "NiriCommands") },
        { shell: "brightnessctl --class=backlight set 10%-", argv: ["brightnessctl", "--class=backlight", "set", "10%-"], name: I18n.tr("Decrease screen brightness", "NiriCommands") },
    ];
    for (const command of commands) {
        if (match[1] === "spawn-sh" && args.length === 1 && args[0] === command.shell)
            return command.name;
        if (match[1] === "spawn" && command.argv.length && JSON.stringify(args) === JSON.stringify(command.argv))
            return command.name;
    }
    return "";
}
