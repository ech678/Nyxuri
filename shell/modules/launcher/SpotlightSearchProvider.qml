import QtQuick
import qs.Common
import qs.Services
import "../../Common/functions/SpotlightLocalSearch.js" as LocalSearch

Item {
    id: root
    property bool active: false
    property string query: ""
    property string filter: ""
    onFilterChanged: rebuild()
    property var results: []
    property var capacities: ({
                                  apps: 6,
                                  wallpapers: 4
                              })
    property string retainedResultId: ""
    property string error: ""
    readonly property string language: Qt.uiLanguage
    signal modeRequested(string mode, string query)
    signal deferredRequested(string provider, string sourceId, string query)
    signal closeRequested

    function rebuild() {
        if (!active || DockService.externalDragActive)
            return;
        if (filter === "settings" || filter === "actions") {
            const catalog = filter === "settings" ? SpotlightCatalog.settings : SpotlightCatalog.actions;
            const matches = filter === "actions" && !query.trim() ? catalog : LocalSearch.matchCatalog(catalog,
                                                                                                       query);
            results = matches.map(entry => ({
                id: filter + ":" + entry.id,
                sourceId: entry.id,
                provider: filter,
                query: query,
                title: entry.title,
                icon: entry.icon,
                symbol: entry.icon,
                subtitle: SpotlightCatalog.available(entry) ? (entry.breadcrumb || entry.description || "") : qsTr(
                                                                  "Currently unavailable")
            }));
            return;
        }
        if (!query.trim()) {
            results = [];
            return;
        }
        const apps = LocalSearch.appResults(ApplicationService.launcherApplications, query,
                                            UiPreferences.spotlightAppOrder, SpotlightAppUsage.records,
                                            Date.now()).map(entry => Object.assign({}, entry, {
                                                                                       iconKind: entry.symbol
                                                                                                 ? "symbol" :
                                                                                                   "app",
                                                                                       appIcon: entry.icon
                                                                                   }));
        const settings = LocalSearch.matchCatalog(SpotlightCatalog.settings.filter(SpotlightCatalog.available),
                                                  query).map(entry => ({
                                                      id: entry.id,
                                                      title: entry.title,
                                                      subtitle: qsTr("Settings · %1").arg(entry.breadcrumb),
                                                      iconKind: "symbol",
                                                      symbol: entry.icon
                                                  }));
        const actions = LocalSearch.matchCatalog(SpotlightCatalog.actions, query).map(entry => ({
            id: entry.id,
            title: entry.title,
            subtitle: SpotlightCatalog.available(entry) ? qsTr("Action · %1").arg(entry.description) : qsTr(
                                                              "Action · Currently unavailable"),
            iconKind: "symbol",
            symbol: entry.icon,
            available: SpotlightCatalog.available(entry)
        }));
        const wallpapers = LocalSearch.wallpaperPaths(WallpaperService.wallpapers, query,
                                                      WallpaperService.basename).map(path => ({
                                                          id: path,
                                                          title: WallpaperService.basename(path),
                                                          subtitle: WallpaperService.parentFolder(path),
                                                          iconKind: "wallpaper",
                                                          previewUrl: Paths.fileUrl(path),
                                                          symbol: "image"
                                                      }));
        results = LocalSearch.groupedResults({
                                                 apps: apps,
                                                 settings: settings,
                                                 actions: actions,
                                                 wallpapers: wallpapers
                                             }, query, {
                                                 apps: qsTr("Apps"),
                                                 settings: qsTr("Settings"),
                                                 actions: qsTr("Actions"),
                                                 wallpapers: qsTr("Wallpapers"),
                                                 files: qsTr("Search files for “%1”").arg(query),
                                                 web: qsTr("Search the web for “%1”").arg(query)
                                             }, capacities, retainedResultId);
    }
    function activate(id) {
        if (!active)
            return false;
        const request = LocalSearch.activation(results, id, query);
        if (!request)
            return false;
        error = "";
        switch (request.provider) {
        case "extension":
            if (request.sourceId === "files")
                modeRequested("files", request.query);
            else
                deferredRequested("web", "", request.query);
            return true;
        case "apps":
            if (ApplicationService.findById(request.sourceId)?.dragOnly)
                return false;
            if (SpotlightAppUsage.launch(request.sourceId)) {
                closeRequested();
                return true;
            }
            break;
        case "wallpapers":
            if (!WallpaperService.busy && WallpaperService.wallpapers.indexOf(request.sourceId) >= 0 && WallpaperService.setWallpaper(
                        request.sourceId)) {
                closeRequested();
                return true;
            }
            break;
        case "settings":
            if (SpotlightCatalog.available(SpotlightCatalog.setting(request.sourceId))) {
                deferredRequested("settings", request.sourceId, request.query);
                return true;
            }
            break;
        case "actions":
            const action = SpotlightCatalog.action(request.sourceId);
            if (!SpotlightCatalog.available(action))
                break;
            if (action.target === "spotlight") {
                const mode = action.method === "openMode" ? action.args[0] : action.method;
                modeRequested(mode, "");
            } else
                deferredRequested("actions", action.id, request.query);
            return true;
        }
        error = qsTr("This result is currently unavailable");
        return false;
    }
    onQueryChanged: {
        error = "";
        rebuild();
    }
    onActiveChanged: rebuild()
    onLanguageChanged: rebuild()
    onCapacitiesChanged: rebuild()
    Connections {
        target: DockService
        function onExternalDragActiveChanged() {
            if (!DockService.externalDragActive)
                root.rebuild();
        }
    }
    Connections {
        target: ApplicationService
        function onLauncherApplicationsChanged() {
            root.rebuild();
        }
    }
    Connections {
        target: WallpaperService
        function onWallpapersChanged() {
            root.rebuild();
        }
        function onBusyChanged() {
            root.rebuild();
        }
    }
    Connections {
        target: SpotlightCatalog
        function onAvailabilityChanged() {
            root.rebuild();
        }
        function onSettingsChanged() {
            root.rebuild();
        }
        function onActionsChanged() {
            root.rebuild();
        }
        function onKeystoneAvailableChanged() {
            root.rebuild();
        }
    }
    Connections {
        target: UiPreferences
        function onSpotlightAppOrderChanged() {
            root.rebuild();
        }
    }
    Connections {
        target: SpotlightAppUsage
        function onReadyChanged() {
            root.rebuild();
        }
    }
}
