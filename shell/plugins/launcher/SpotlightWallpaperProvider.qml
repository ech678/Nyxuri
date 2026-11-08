import QtQuick
import qs.commons
import qs.services
import "./SpotlightLocalSearch.js" as LocalSearch

Item {
    id: root

    property bool active: false
    onActiveChanged: {
        if (active)
            rebuild();
    }
    property string query: ""
    property var results: []
    property var filteredPaths: []
    property int loadedCount: 0
    property int pageSize: 30
    readonly property var resultModel: wallpaperResultModel
    readonly property bool hasMore: root.loadedCount < root.filteredPaths.length

    function resultForPath(path, needle) {
        const wp = ActionGateway.wallpaperHost;
        const title = (wp && wp.basename) ? wp.basename(path) : path.split("/").pop();
        const subtitle = (wp && wp.parentFolder) ? wp.parentFolder(path) : path.substring(0, path.lastIndexOf("/"));
        return {
            provider: "wallpapers",
            id: path,
            title: title,
            subtitle: subtitle,
            icon: "",
            preview: Paths.fileUrl(path),
            score: needle === "" ? 0 : (title.toLocaleLowerCase().startsWith(needle) ? 2 : 1),
            actions: ["apply"],
            path: path
        };
    }

    function rebuild() {
        if (!active)
            return;
        const wp = ActionGateway.wallpaperHost;
        if (!wp || !StateProjection.isEnabled("wallpaper")) {
            root.filteredPaths = [];
            root.loadedCount = 0;
            root.results = [];
            wallpaperResultModel.clear();
            return;
        }
        const basenameFn = (wp && wp.basename) ? wp.basename : (p => p.split("/").pop());
        const next = LocalSearch.wallpaperPaths(wp.wallpapers || [], query, basenameFn);
        root.filteredPaths = next;
        root.loadedCount = 0;
        root.results = [];
        wallpaperResultModel.clear();
        root.loadMore(root.pageSize);
    }

    function loadMore(minimumCount) {
        if (!root.hasMore)
            return false;
        const needle = String(root.query || "").trim().toLocaleLowerCase();
        const requested = Math.max(root.loadedCount + root.pageSize, Number(minimumCount) || 0);
        const target = Math.min(root.filteredPaths.length, requested);
        const next = root.results.slice();
        const appendedPaths = [];
        for (let index = root.loadedCount; index < target; index += 1) {
            const result = root.resultForPath(String(root.filteredPaths[index]), needle);
            next.push(result);
            appendedPaths.push(result.path);
        }
        root.loadedCount = target;
        root.results = next;
        for (let index = 0; index < appendedPaths.length; index += 1) {
            wallpaperResultModel.append({
                                            "wallpaperPath": appendedPaths[index]
                                        });
        }
        return true;
    }

    function refresh() {
        const wp = ActionGateway.wallpaperHost;
        if (active && wp && !wp.scanning && wp.scan)
            wp.scan();
    }

    function execute(index) {
        const result = root.results[index];
        const wp = ActionGateway.wallpaperHost;
        if (!result || !wp || wp.busy)
            return false;
        return wp.setWallpaper(result.path);
    }

    onQueryChanged: rebuild()
    Component.onCompleted: rebuild()

    ListModel {
        id: wallpaperResultModel
    }

    Connections {
        target: ActionGateway.wallpaperHost

        function onWallpapersChanged() {
            root.rebuild();
        }
    }
}
