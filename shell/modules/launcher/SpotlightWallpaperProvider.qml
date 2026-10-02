import QtQuick
import qs.Common
import qs.Services
import "../../Common/functions/SpotlightLocalSearch.js" as LocalSearch

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
        const title = WallpaperService.basename(path);
        return {
            provider: "wallpapers",
            id: path,
            title: title,
            subtitle: WallpaperService.parentFolder(path),
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
        const next = LocalSearch.wallpaperPaths(WallpaperService.wallpapers || [], query,
                                                WallpaperService.basename);
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
        if (active && !WallpaperService.scanning)
            WallpaperService.scan();
    }

    function execute(index) {
        const result = root.results[index];
        if (!result || WallpaperService.busy)
            return false;
        return WallpaperService.setWallpaper(result.path);
    }

    onQueryChanged: rebuild()
    Component.onCompleted: rebuild()

    ListModel {
        id: wallpaperResultModel
    }

    Connections {
        target: WallpaperService

        function onWallpapersChanged() {
            root.rebuild();
        }
    }
}
