import QtQuick
import Quickshell
import qs.Services
import "../../Common/functions/SpotlightLocalSearch.js" as LocalSearch

Item {
    id: root

    property string query: ""
    property var results: []
    property int limit: 50
    property string order: UiPreferences.spotlightAppOrder
    onOrderChanged: rebuild()

    function rebuild() {
        if (!active || DockService.externalDragActive)
            return;
        const ordered = LocalSearch.appResults(ApplicationService.launcherApplications, query, root.order,
                                               SpotlightAppUsage.records, Date.now());
        root.results = root.limit > 0 ? ordered.slice(0, root.limit) : ordered;
    }

    function execute(index) {
        const result = root.results[index];
        if (!result || !result.appObject || result.appObject.dragOnly)
            return false;
        return SpotlightAppUsage.launch(result.id);
    }

    property bool active: true
    onActiveChanged: rebuild()

    onQueryChanged: rebuild()
    onLimitChanged: rebuild()
    Component.onCompleted: rebuild()

    Connections {
        target: DockService
        function onExternalDragActiveChanged() {
            if (!DockService.externalDragActive)
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
            if (SpotlightAppUsage.ready)
                root.rebuild();
        }
    }

    Connections {
        target: ApplicationService

        function onLauncherApplicationsChanged() {
            root.rebuild();
        }
    }
}
