pragma Singleton
import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property string shellDir: Quickshell.shellDir
    // Quickshell chooses the user XDG shell directory before the system XDG
    // directory. Both installed and source shells therefore use the same
    // relative resource paths.
    readonly property string shareRoot: shellDir
    // Host-owned data directories (KM4.6: the assets/ junk drawer is dissolved —
    // unit-owned shaders live in plugins/<domain>/shaders/, host data lives in app/).
    readonly property string i18nDir: shareRoot + "/commons/i18n"
    readonly property string iconsDir: shareRoot + "/app/icons"
    readonly property string scriptsDir: shareRoot + "/scripts"
    readonly property string lyricsScriptsDir: scriptsDir + "/media"
    readonly property string mediaScriptsDir: scriptsDir + "/media"
    readonly property string systemScriptsDir: scriptsDir + "/system"
    readonly property string userMatugenDir: configHome + "/matugen"
    readonly property string homeDir: root.absoluteEnvironment("HOME")
    readonly property string xdgConfigHome: root.absoluteEnvironment("XDG_CONFIG_HOME") || homeDir
                                            + "/.config"
    readonly property string xdgDataHome: root.absoluteEnvironment("XDG_DATA_HOME") || homeDir
                                          + "/.local/share"
    readonly property string xdgCacheHome: {
        const orig = root.absoluteEnvironment("NYXURI_ORIGINAL_CACHE_HOME");
        if (orig)
            return orig;
        const raw = root.absoluteEnvironment("XDG_CACHE_HOME") || "";
        if (raw.endsWith("/nyxuri-shell"))
            return raw.substring(0, raw.length - "/nyxuri-shell".length);
        return raw || (homeDir + "/.cache");
    }
    readonly property string binHome: root.absoluteEnvironment("NYXURI_BIN_HOME") || homeDir + "/.local/bin"
    readonly property string stableKey: root.absoluteEnvironment("NYXURI_KEY") || "key"
    readonly property string fallbackConfigHome: xdgConfigHome + "/nyxuri"
    readonly property string configHome: root.absoluteEnvironment("NYXURI_SHELL_CONFIG_HOME")
                                          || fallbackConfigHome
    readonly property string dataHome: root.absoluteEnvironment("NYXURI_SHELL_DATA_HOME") || xdgDataHome
                                        + "/nyxuri"
    readonly property string stateHome: root.absoluteEnvironment("NYXURI_SHELL_STATE_HOME") || (
                                            root.absoluteEnvironment("XDG_STATE_HOME") || homeDir
                                            + "/.local/state") + "/nyxuri"
    readonly property string cacheHome: root.absoluteEnvironment("NYXURI_SHELL_CACHE_HOME") || (
                                            root.absoluteEnvironment("XDG_CACHE_HOME") || homeDir
                                            + "/.cache") + "/nyxuri"
    readonly property string runtimeHome: root.absoluteEnvironment("NYXURI_SHELL_RUNTIME_HOME")
                                           || (
                                               root.absoluteEnvironment("XDG_RUNTIME_DIR") || cacheHome
                                               + "/runtime") + "/nyxuri"
    readonly property string requestedProfileName: Quickshell.env("NYXURI_SHELL_PROFILE") || "default"
    readonly property string profileName: root.validProfileName(requestedProfileName)
                                          ? requestedProfileName.trim() : "default"
    readonly property string profileConfigHome: root.absoluteEnvironment("NYXURI_SHELL_PROFILE_CONFIG_HOME")
                                                 || configHome + "/profiles/" + profileName
    readonly property string profileHome: root.absoluteEnvironment("NYXURI_SHELL_PROFILE_HOME") || dataHome
                                           + "/profiles/" + profileName
    readonly property string generatedHome: root.absoluteEnvironment("NYXURI_SHELL_GENERATED_HOME")
                                             || profileHome + "/generated"
    readonly property string currentWallpaper: stateHome + "/wallpaper/current"
    readonly property string profileAvatar: homeDir + "/.face"
    readonly property string defaultAvatar: ""

    function absoluteEnvironment(name) {
        const value = String(Quickshell.env(name) || "").trim();
        return value.startsWith("/") ? value : "";
    }

    function validProfileName(value) {
        const name = String(value || "").trim();
        return name !== "" && name !== "." && name !== ".." && name.indexOf("/") < 0 && name.indexOf("\\")
                < 0;

    }

    function fileUrl(path) {
        if (!path || String(path).trim() === "")
            return "";
        const value = String(path);
        if (value.startsWith("file://"))
            return value;
        return "file://" + value.split("/").map(segment => encodeURIComponent(segment)).join("/");
    }

    function icon(name) {
        return fileUrl(iconsDir + "/" + name);
    }

    function scriptPath(group, name) {
        return scriptsDir + "/" + group + "/" + name;
    }
}
