pragma Singleton
import QtQuick
import qs.Services
import Quickshell
import qs.Common
import "../Common/generated/SearchCatalog.js" as Catalog
import "../Common/functions/SpotlightCommands.js" as Commands

Singleton {
    id: root
    readonly property var routes: Catalog.catalog.routes
    property var settings: []
    property var actions: []
    readonly property string language: Qt.uiLanguage
    property var actionExecutor: null
    property bool keystoneAvailable: false
    readonly property bool keyboardLockAvailable: KeyboardLockService.available
    readonly property bool dockPreviewsAvailable: WindowPreviewService.supported

    readonly property var commands: Commands.entries
    function commandTitle(entry) {
        const currentLanguage = root.language;
        return Commands.title(entry);
    }
    function commandMatches(query, palette) {
        const currentLanguage = root.language;
        return Commands.match(query, palette, root.commandTitle);
    }

    signal availabilityChanged
    onKeyboardLockAvailableChanged: availabilityChanged()
    onDockPreviewsAvailableChanged: availabilityChanged()

    function title(id) {
        const currentLanguage = root.language;
        return Catalog.title(id);
    }
    function route(id) {
        return routes.find(entry => entry.id === id) || null;
    }
    function setting(id) {
        return settings.find(entry => entry.id === id) || null;
    }
    function action(id) {
        return actions.find(entry => entry.id === id) || null;
    }
    function rebuild() {
        settings = Catalog.catalog.settings.map(entry => Object.assign({}, entry, {
                                                                           title: Catalog.title(entry.id),
                                                                           sourceTitle: entry.title,
                                                                           breadcrumb: entry.path.map((part,
                                                                                                       i) => Catalog.title(
                                                                                                                 entry.path.slice(
                                                                                                                     0, i + 1).join(
                                                                                                                     "."))).join(
                                                                                           " → ")
                                                                       }));
        actions = Catalog.catalog.actions.map(entry => Object.assign({}, entry, {
                                                                         title: Catalog.title(entry.id),
                                                                         sourceTitle: entry.title,
                                                                         description: Catalog.description(
                                                                                          entry.id)
                                                                     }));
    }
    function available(entry) {
        if (!entry)
            return false;
        switch (entry.availability || "always") {
        case "always":
            return true;
        case "awww":
            return PersonalizationConfig.desktopWallpaperBackend === "awww";
        case "clavis-wallpaper":
            return PersonalizationConfig.desktopWallpaperBackend !== "awww";
        case "wallpaper-idle":
            return !WallpaperService.busy;
        case "keystone":
            return keystoneAvailable;
        case "keyboard-lock":
            return keyboardLockAvailable;
        case "dock-previews":
            return dockPreviewsAvailable;
        default:
            return false;
        }
    }
    function execute(id) {
        const entry = action(id);
        if (!entry)
            return false;
        const accepted = available(entry) && actionExecutor && actionExecutor(entry) === true;
        if (!accepted)
            Quickshell.execDetached(["notify-send", "-a", "Clavis Shell", qsTr("Action unavailable"),
                                     Catalog.title(id)]);
        return accepted;
    }
    onLanguageChanged: rebuild()
    Component.onCompleted: rebuild()
}
