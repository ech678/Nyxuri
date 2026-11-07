pragma Singleton
import QtQuick
import Quickshell
import qs.services
import "../plugins/wallpaper"
import qs.commons
import "../plugins/launcher/SpotlightCommands.js" as Commands
import qs.commons.i18n

// The spotlight search index over the runtime plugin registry (S0-2): routes,
// anchors and fixed actions are declared by plugins' manifest.toml and read
// through PluginRegistry — no generated catalog file, no hand-written mirror.
// Titles and descriptions are source strings; translation rides I18n.tr with
// the manifest context as the disambiguation key.
Singleton {
    id: root
    property var routes: []
    property var settings: []
    property var actions: []
    readonly property string language: Qt.uiLanguage
    property var actionExecutor: null
    property bool keystoneAvailable: false
    readonly property bool keyboardLockAvailable: KeyboardLockService.available
    readonly property bool dockPreviewsAvailable: false

    // id -> {title, description, context}: the translated lookup surface.
    property var _index: ({})

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
        const record = root._index[id];
        return record ? I18n.tr(record.title, record.context) : "";
    }
    function description(id) {
        const record = root._index[id];
        return record && record.description ? I18n.tr(record.description, record.context) : "";
    }
    function route(id) {
        return routes.find(entry => entry.id === id || (entry.aliases && entry.aliases.includes(id))) || null;
    }
    function setting(id) {
        return settings.find(entry => entry.id === id || (entry.aliases && entry.aliases.includes(id)))
                || null;
    }
    function action(id) {
        return actions.find(entry => entry.id === id) || null;
    }
    function rebuild() {
        const index = {};
        const nextRoutes = [];
        for (let i = 0; i < PluginRegistry.settingsRoutes.length; ++i) {
            const entry = PluginRegistry.settingsRoutes[i];
            const route = Object.assign({}, entry, {
                                            path: String(entry.id).split(".")
                                        });
            nextRoutes.push(route);
            index[entry.id] = {
                title: entry.title,
                description: entry.description || "",
                context: entry.context
            };
        }

        const routeById = {};
        nextRoutes.forEach(route => routeById[route.id] = route);
        const breadcrumb = path => path.map((part, i) => root.title(path.slice(0, i + 1).join("."))).join(
                                       " → ");
        const nextSettings = nextRoutes.map(route => Object.assign({}, route, {
                                                                       route: route.id,
                                                                       anchor: false,
                                                                       title: root.title(route.id),
                                                                       sourceTitle: route.title,
                                                                       breadcrumb: breadcrumb(route.path)
                                                                   }));
        for (let a = 0; a < PluginRegistry.settingsAnchors.length; ++a) {
            const anchor = PluginRegistry.settingsAnchors[a];
            const parent = routeById[anchor.route];
            if (!parent)
                continue;
            nextSettings.push(Object.assign({}, anchor, {
                                                anchor: true,
                                                path: parent.path,
                                                title: root.title(anchor.id),
                                                sourceTitle: anchor.title,
                                                breadcrumb: breadcrumb(parent.path)
                                            }));
            index[anchor.id] = {
                title: anchor.title,
                description: "",
                context: anchor.context
            };
        }

        const nextActions = [];
        for (let s = 0; s < PluginRegistry.actions.length; ++s) {
            const entry = PluginRegistry.actions[s];
            const search = entry.search;
            nextActions.push(Object.assign({}, entry, {
                                               title: I18n.tr(search.title, search.context),
                                               sourceTitle: search.title,
                                               description: I18n.tr(search.description, search.context),
                                               icon: search.icon,
                                               aliases: search.aliases || []
                                           }));
            index[entry.id] = {
                title: search.title,
                description: search.description,
                context: search.context
            };
        }

        root._index = index;
        root.routes = nextRoutes;
        root.settings = nextSettings;
        root.actions = nextActions;
    }
    function available(entry) {
        if (!entry)
            return false;
        switch (entry.availability || "always") {
        case "always":
            return true;
        case "awww":
            return PersonalizationConfig.desktopWallpaperBackend === "awww";
        case "nyxuri-wallpaper":
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
            ActionGateway.execute(["notify-send", "-a", "Nyxuri Shell", I18n.tr("Action unavailable"),
                                   root.title(id)], "spotlight:catalog-action");
        return accepted;
    }
    Connections {
        target: PluginRegistry
        function onReadyChanged() {
            root.rebuild();
        }
        // A third-party plugin landed, changed or left (inotify hot reload):
        // the views were re-derived, so the search index follows.
        function onPluginsChanged() {
            root.rebuild();
        }
    }
    onLanguageChanged: rebuild()
    Component.onCompleted: rebuild()
}
