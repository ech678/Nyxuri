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
    readonly property string assetsDir: shareRoot + "/assets"
    readonly property string builtinMatugenDir: assetsDir + "/matugen"
    readonly property string userMatugenDir: configHome + "/matugen"
    readonly property string iconsDir: assetsDir + "/icons"
    readonly property string weatherIconsDir: iconsDir + "/weather"
    readonly property string scriptsDir: shareRoot + "/scripts"
    readonly property string audioScriptsDir: scriptsDir + "/audio"
    readonly property string captureScriptsDir: scriptsDir + "/capture"
    readonly property string lyricsScriptsDir: scriptsDir + "/lyrics"
    readonly property string mediaScriptsDir: scriptsDir + "/media"
    readonly property string systemScriptsDir: scriptsDir + "/system"
    readonly property string themeScriptsDir: scriptsDir + "/theme"
    readonly property string weatherScriptsDir: scriptsDir + "/weather"
    readonly property string homeDir: root.absoluteEnvironment("HOME")
    readonly property string xdgConfigHome: root.absoluteEnvironment("XDG_CONFIG_HOME") || homeDir
                                            + "/.config"
    readonly property string xdgDataHome: root.absoluteEnvironment("XDG_DATA_HOME") || homeDir
                                          + "/.local/share"
    readonly property string binHome: root.absoluteEnvironment("NYXURI_BIN_HOME") || root.absoluteEnvironment(
                                          "CLAVIS_BIN_HOME") || homeDir + "/.local/bin"
    readonly property string stableKey: root.absoluteEnvironment("NYXURI_KEY") || root.absoluteEnvironment(
                                            "CLAVIS_KEY") || "key"
    readonly property string fallbackConfigHome: xdgConfigHome + "/nyxuri"
    readonly property string configHome: root.absoluteEnvironment("NYXURI_SHELL_CONFIG_HOME")
                                         || root.absoluteEnvironment("CLAVIS_CONFIG_HOME")
                                         || fallbackConfigHome
    readonly property string dataHome: root.absoluteEnvironment("NYXURI_SHELL_DATA_HOME")
                                       || root.absoluteEnvironment("CLAVIS_DATA_HOME") || xdgDataHome
                                       + "/nyxuri"
    readonly property string stateHome: root.absoluteEnvironment("NYXURI_SHELL_STATE_HOME")
                                        || root.absoluteEnvironment("CLAVIS_STATE_HOME") || (
                                            root.absoluteEnvironment("XDG_STATE_HOME") || homeDir
                                            + "/.local/state") + "/nyxuri"
    readonly property string cacheHome: root.absoluteEnvironment("NYXURI_SHELL_CACHE_HOME")
                                        || root.absoluteEnvironment("CLAVIS_CACHE_HOME") || (
                                            root.absoluteEnvironment("XDG_CACHE_HOME") || homeDir
                                            + "/.cache") + "/nyxuri"
    readonly property string runtimeHome: root.absoluteEnvironment("NYXURI_SHELL_RUNTIME_HOME")
                                          || root.absoluteEnvironment("CLAVIS_RUNTIME_HOME") || (
                                              root.absoluteEnvironment("XDG_RUNTIME_DIR") || cacheHome
                                              + "/runtime") + "/nyxuri"
    readonly property string requestedProfileName: Quickshell.env("NYXURI_SHELL_PROFILE") || Quickshell.env(
                                                       "CLAVIS_PROFILE") || "default"
    readonly property string profileName: root.validProfileName(requestedProfileName)
                                          ? requestedProfileName.trim() : "default"
    readonly property string profileConfigHome: root.absoluteEnvironment("NYXURI_SHELL_PROFILE_CONFIG_HOME")
                                                || root.absoluteEnvironment("CLAVIS_PROFILE_CONFIG_HOME")
                                                || configHome + "/profiles/" + profileName
    readonly property string profileHome: root.absoluteEnvironment("NYXURI_SHELL_PROFILE_HOME")
                                          || root.absoluteEnvironment("CLAVIS_PROFILE_HOME") || dataHome
                                          + "/profiles/" + profileName
    readonly property string generatedHome: root.absoluteEnvironment("NYXURI_SHELL_GENERATED_HOME")
                                            || root.absoluteEnvironment("CLAVIS_GENERATED_HOME")
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
        return value.startsWith("file://") ? value : "file://" + value;
    }

    function icon(name) {
        return fileUrl(iconsDir + "/" + name);
    }

    function scriptPath(group, name) {
        return scriptsDir + "/" + group + "/" + name;
    }
}
