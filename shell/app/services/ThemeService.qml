pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.shared.theme
import qs.app.services
import qs.modules.wallpaper
import qs.app
import qs.shared.i18n

Singleton {
    id: root

    QtObject {
        id: iconThemeController
        readonly property string systemThemeName: "hicolor"
        property string themeName: ""
        property int revision: 0
        signal changed
        function setThemeName(name) {
            themeName = name;
            revision++;
            changed();
        }
    }

    readonly property string colorsPath: Paths.generatedHome + "/clavis/colors.json"
    property string paletteError: ""

    function snakeToM3(key) {
        const parts = key.split("_");
        let result = "m3" + parts[0];
        for (let i = 1; i < parts.length; i += 1)
            result += parts[i].charAt(0).toUpperCase() + parts[i].slice(1);
        return result;
    }

    function applyGeneratedColors(text) {
        const generatedColors = JSON.parse(text);
        if (!generatedColors || typeof generatedColors !== "object" || Array.isArray(generatedColors))
            throw new Error("Expected a palette object");
        const updates = [];
        for (let key in generatedColors) {
            const propertyName = root.snakeToM3(key);
            if (propertyName in Appearance.m3colors && propertyName !== "darkmode") {
                if (typeof generatedColors[key] !== "string" || !Qt.color(generatedColors[key]).valid)
                    throw new Error("Invalid palette color: " + key);
                updates.push([propertyName, Qt.color(generatedColors[key])]);
            }
        }
        for (const update of updates)
            Appearance.m3colors[update[0]] = update[1];
    }

    function reloadColors() {
        colorFile.reload();
    }

    FileView {
        id: colorFile
        path: root.colorsPath
        watchChanges: true
        onLoaded: {
            try {
                root.applyGeneratedColors(colorFile.text());
                root.paletteError = "";
            } catch (error) {
                root.paletteError = String(error);
                console.warn("Unable to apply palette:", error);
            }
        }
        onFileChanged: root.reloadColors()
        onLoadFailed: error => {
            root.paletteError = error === FileViewError.FileNotFound ? "" : FileViewError.toString(error);
        }
    }

    Binding {
        target: Appearance
        property: "backgroundOpacity"
        value: PersonalizationConfig.shellBackgroundOpacity
    }
    Binding {
        target: Resources
        property: "iconsRoot"
        value: Paths.fileUrl(Paths.iconsDir + "/")
    }
    Binding {
        target: Resources
        property: "iconThemeRevision"
        value: root.iconThemeRevision
    }

    function resolveIcon(name) {
        const revision = root.iconThemeRevision;
        if (!name)
            return "";
        return Quickshell.iconPath(name, "image-missing") || "image://icon/" + name;
    }

    function resolveFileIcons(candidates) {
        const revision = root.iconThemeRevision;
        const sources = [];
        for (const name of candidates) {
            if (!Quickshell.hasThemeIcon(name))
                continue;
            const source = Quickshell.iconPath(name, true);
            if (source && sources.indexOf(source) === -1)
                sources.push(source);
        }
        return sources;
    }

    function mediaIcon(player) {
        const revision = root.iconThemeRevision;
        if (!player)
            return "";
        const entry = DesktopEntries.heuristicLookup(player.desktopEntry || "")
              || DesktopEntries.heuristicLookup(player.identity || "");
        return entry && entry.icon ? Quickshell.iconPath(entry.icon, true) : "";
    }

    property string generationError: ""
    property string externalGenerationError: ""
    property string generationTemplateId: ""
    property string pendingGenerationTemplateId: ""
    property var pendingGeneration: null
    property bool coreReloaded: false
    property bool generating: false
    property string lastSource: ""
    readonly property bool cursorIntegrationReady: NiriConfigService.ready("cursor")
    readonly property string cursorLastError: NiriConfigService.error
    readonly property bool cursorSyncBusy: NiriConfigService.busy && NiriConfigService.activeFeature
                                           === "cursor"
    property var availableIconThemes: [({
                                            "label": I18n.tr("System default"),
                                            "value": ""
                                        })]
    property var availableCursorThemes: [({
                                              "label": I18n.tr("System default"),
                                              "value": ""
                                          })]
    readonly property string systemDefaultIconTheme: iconThemeController.systemThemeName
    readonly property int iconThemeRevision: iconThemeController.revision
    property string systemDefaultCursorTheme: ""

    readonly property bool isNiriSession: NiriConfigService.supported

    function applyConfigToAppearance() {
        Appearance.matugenScheme = PersonalizationConfig.matugenScheme;
        Appearance.matugenMode = PersonalizationConfig.themeMode;
    }

    function setMatugenScheme(value) {
        PersonalizationConfig.setMatugenScheme(value);
        root.applyConfigToAppearance();
        root.regenerateFromCurrentWallpaper();
    }

    function enabledMatugenTemplates() {
        const enabled = [];
        for (const template of MatugenTemplateService.templates) {
            if (template.valid && PersonalizationConfig.isMatugenTemplateEnabled(template.id)
                    && enabled.indexOf(template.id) === -1)
                enabled.push(template.id);
        }
        return enabled;
    }

    function setMatugenTemplateEnabled(id, enabled) {
        let changed = PersonalizationConfig.setMatugenTemplateEnabled(id, enabled);
        if (changed && enabled)
            root.regenerateFromCurrentWallpaper(id);
    }

    function setThemeMode(value) {
        PersonalizationConfig.setThemeMode(value);
        root.applyConfigToAppearance();
        UiPreferences.setDarkMode(PersonalizationConfig.themeMode === "dark");
        root.regenerateFromCurrentWallpaper();
    }

    function setCursorTheme(value) {
        PersonalizationConfig.setCursorTheme(value);
    }

    function setCursorSize(value) {
        PersonalizationConfig.setCursorSize(value);
    }

    function setCursorHideWhenTyping(value) {
        PersonalizationConfig.setCursorHideWhenTyping(value);
    }

    function setCursorHideAfterInactiveMs(value) {
        PersonalizationConfig.setCursorHideAfterInactiveMs(value);
    }

    function setIconTheme(value) {
        PersonalizationConfig.setIconTheme(value);
    }

    function applyIconTheme() {
        if (PersonalizationConfig.ready)
            iconThemeController.setThemeName(PersonalizationConfig.iconTheme);
    }

    function effectiveCursorTheme() {
        return PersonalizationConfig.cursorTheme !== "" ? PersonalizationConfig.cursorTheme :
                                                          root.systemDefaultCursorTheme;
    }

    function unique(values) {
        const result = [];
        const seen = {};
        for (let i = 0; i < values.length; i += 1) {
            const value = String(values[i] || "").trim();
            if (value === "" || seen[value])
                continue;
            seen[value] = true;
            result.push(value);
        }
        return result;
    }

    function dataDirs() {
        const raw = Quickshell.env("XDG_DATA_DIRS") || "";
        const base = raw.trim() !== "" ? raw.split(":") : ["/usr/local/share", "/usr/share"];
        return root.unique(base.concat([Paths.xdgDataHome, "/usr/local/share", "/usr/share"]));
    }

    function hasOption(options, value) {
        for (let i = 0; i < options.length; i += 1) {
            if (options[i].value === value)
                return true;
        }
        return false;
    }

    function defaultOption(label, systemDefault) {
        return {
            "label": systemDefault !== "" ? label + " · " + systemDefault : label,
            "value": ""
        };
    }

    function parseDetectedThemes(output, defaultLabel, currentValue, cursorThemes) {
        let systemDefault = cursorThemes ? "" : root.systemDefaultIconTheme;
        const names = [];
        const lines = String(output || "").split("\n");
        for (let i = 0; i < lines.length; i += 1) {
            const line = lines[i].trim();
            if (line === "")
                continue;
            if (line.indexOf("SYSDEFAULT:") === 0) {
                if (cursorThemes)
                    systemDefault = line.substring(11).trim();
                continue;
            }
            names.push(line);
        }

        if (cursorThemes)
            root.systemDefaultCursorTheme = systemDefault;

        const options = [root.defaultOption(defaultLabel, systemDefault)];
        const sorted = root.unique(names).sort((a, b) => a.localeCompare(b));
        for (let j = 0; j < sorted.length; j += 1)
            options.push({
                             "label": sorted[j],
                             "value": sorted[j]
                         });

        if (currentValue !== "" && !root.hasOption(options, currentValue))
            options.splice(1, 0, {
                               "label": currentValue,
                               "value": currentValue
                           });

        return options;
    }

    function detectAvailableThemes() {
        const paths = root.dataDirs().map(dir => dir + "/icons").concat([Paths.homeDir + "/.icons"]);
        const script = Paths.scriptPath("theme", "list-cursor-icon-themes.sh");
        detectIconThemesProcess.command = ["bash", script, "icon", ...paths];
        detectCursorThemesProcess.command = ["bash", script, "cursor", ...paths];
        detectIconThemesProcess.running = false;
        detectCursorThemesProcess.running = false;
        detectIconThemesProcess.running = true;
        detectCursorThemesProcess.running = true;
    }

    function applyCursorSettings() {
        if (!root.isNiriSession || !PersonalizationConfig.ready)
            return;
        root.generateNiriCursorConfig();
    }

    function generateNiriCursorConfig() {
        if (PersonalizationConfig.ready)
            NiriConfigService.update("cursor");
    }

    function generateFromWallpaper(path, templateId) {
        if (!path || path === "")
            return;

        root.applyConfigToAppearance();
        root.lastSource = path;
        const command = ["bash", Paths.scriptPath("theme", "generate-matugen-colors.sh"), "--image", path, "--scheme",
                         PersonalizationConfig.matugenScheme, "--mode", PersonalizationConfig.themeMode,
                         "--templates", root.enabledMatugenTemplates().join(",")];
        root.startGeneration(command, templateId);
    }

    function startGeneration(command, templateId) {
        if (generateColorsProcess.running || !MatugenTemplateService.ready || !PersonalizationConfig.ready) {
            root.pendingGenerationTemplateId = templateId || "";
            root.pendingGeneration = command;
            return;
        }
        root.generationTemplateId = templateId || "";
        root.pendingGenerationTemplateId = "";
        root.pendingGeneration = null;
        root.generationError = "";
        root.externalGenerationError = "";
        root.coreReloaded = false;
        generateColorsProcess.command = command;
        generateColorsProcess.running = true;
    }

    function resumeGeneration() {
        if (!root.pendingGeneration)
            return;
        const command = root.pendingGeneration.slice();
        command[command.indexOf("--templates") + 1] = root.enabledMatugenTemplates().join(",");
        command[command.indexOf("--scheme") + 1] = PersonalizationConfig.matugenScheme;
        command[command.indexOf("--mode") + 1] = PersonalizationConfig.themeMode;
        root.startGeneration(command, root.pendingGenerationTemplateId);
    }

    Connections {
        target: MatugenTemplateService
        function onReadyChanged() {
            if (MatugenTemplateService.ready && root.pendingGeneration)
                root.resumeGeneration();
        }
    }

    Connections {
        // startGeneration() also defers when PersonalizationConfig is still
        // loading its JSON. Without this listener a generation deferred for that
        // reason is only resumed if MatugenTemplateService happens to flip ready
        // afterwards — and when the template service was already ready, nothing
        // emits a change, so the palette is never generated at all.
        target: PersonalizationConfig
        function onReadyChanged() {
            if (PersonalizationConfig.ready && root.pendingGeneration)
                root.resumeGeneration();
        }
    }

    function opaqueHexFromColor(value) {
        const color = Qt.color(value);
        const r = Math.round(Math.max(0, Math.min(1, color.r)) * 255).toString(16).padStart(2, "0");
        const g = Math.round(Math.max(0, Math.min(1, color.g)) * 255).toString(16).padStart(2, "0");
        const b = Math.round(Math.max(0, Math.min(1, color.b)) * 255).toString(16).padStart(2, "0");
        return "#" + r + g + b;
    }

    function generateFromColor(value, templateId) {
        if (!value || value === "")
            return;

        const sourceColor = root.opaqueHexFromColor(value);
        root.applyConfigToAppearance();
        root.lastSource = value;
        const command = ["bash", Paths.scriptPath("theme", "generate-matugen-colors.sh"), "--color",
                         sourceColor, "--scheme", PersonalizationConfig.matugenScheme, "--mode",
                         PersonalizationConfig.themeMode, "--templates", root.enabledMatugenTemplates().join(
                             ",")];
        root.startGeneration(command, templateId);
    }

    function regenerateFromCurrentWallpaper(templateId) {
        const path = WallpaperService.currentWallpaper || PersonalizationConfig.wallpaperPath;
        if (path && path !== "" && WallpaperService.isImagePath(path))
            root.generateFromWallpaper(path, templateId);
        else if (WallpaperService.primaryColor(path))
            root.generateFromColor(WallpaperService.primaryColor(path), templateId);
    }

    Component.onCompleted: {
        root.applyIconTheme();
        root.applyConfigToAppearance();
        root.detectAvailableThemes();
        root.applyCursorSettings();
        // The palette is generated, not read from config. If config.json says
        // light while colors.json was last written for dark — or is missing on a
        // fresh install — the shell renders the stale palette and switching the
        // theme looks like it did nothing. Regenerate on startup so the two
        // cannot drift apart.
        root.regenerateFromCurrentWallpaper();
        // UiPreferences reads the system scheme on startup. The Matugen mode
        // is generation configuration, not a request to change the system theme.
    }

    Connections {
        target: PersonalizationConfig

        function onMatugenSchemeChanged() {
            root.applyConfigToAppearance();
        }

        function onThemeModeChanged() {
            root.applyConfigToAppearance();
        }

        function onSettingsLoaded() {
            root.applyIconTheme();
            if (root.pendingGeneration)
                root.resumeGeneration();
            root.applyCursorSettings();
        }

        function onIconThemeChanged() {
            root.applyIconTheme();
        }

        function onCursorThemeChanged() {
            root.applyCursorSettings();
        }

        function onCursorSizeChanged() {
            root.applyCursorSettings();
        }

        function onCursorHideWhenTypingChanged() {
            root.applyCursorSettings();
        }

        function onCursorHideAfterInactiveMsChanged() {
            root.applyCursorSettings();
        }
    }

    onSystemDefaultCursorThemeChanged: root.applyCursorSettings()

    Process {
        id: detectIconThemesProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.availableIconThemes = root.parseDetectedThemes(this.text, I18n.tr("System default"),
                                                                    PersonalizationConfig.iconTheme, false);
            }
        }
    }

    Process {
        id: detectCursorThemesProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.availableCursorThemes = root.parseDetectedThemes(this.text, I18n.tr("System default"),
                                                                      PersonalizationConfig.cursorTheme,
                                                                      true);
            }
        }
    }

    function refreshCursorIntegrationState() {
        NiriConfigService.refresh();
    }

    Process {
        id: generateColorsProcess
        onRunningChanged: if (running)
                              root.generating = true
        stderr: StdioCollector {
            id: generationStderr
        }
        stdout: SplitParser {
            onRead: data => {
                try {
                    const status = JSON.parse(data);
                    if (status.schemaVersion !== 1)
                        return;
                    if (status.event === "core-ready") {
                        root.coreReloaded = true;
                        root.reloadColors();
                    } else if (status.event === "external-error") {
                        root.externalGenerationError += (root.externalGenerationError ? "\n" : "")
                                + status.id + ": " + status.error;
                    } else if (status.event === "core-error") {
                        root.generationError = status.error;
                    }
                } catch (e) {
                    console.warn("Invalid Matugen generation status:", data);
                }
            }
        }
        onExited: exitCode => {
            root.generating = false;
            root.generationTemplateId = "";
            if ((exitCode === 0 || exitCode === 3) && !root.coreReloaded)
                root.reloadColors();
            if (exitCode !== 0 && exitCode !== 3)
                root.generationError = root.generationError || generationStderr.text.trim() || I18n.tr(
                            "Failed to generate Matugen colors");
            if (exitCode === 3 && !root.externalGenerationError)
                root.externalGenerationError = generationStderr.text.trim() || I18n.tr(
                            "Some Matugen templates failed to generate");
            if (root.pendingGeneration)
                Qt.callLater(root.resumeGeneration);
        }
    }

    Component.onDestruction: {
        if (detectIconThemesProcess)
            detectIconThemesProcess.running = false;
        if (detectCursorThemesProcess)
            detectCursorThemesProcess.running = false;
        if (generateColorsProcess)
            generateColorsProcess.running = false;
    }
}
