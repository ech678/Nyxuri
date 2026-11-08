import QtQuick
import Quickshell
import Quickshell.Io
import qs.services

Item {
    id: root

    property bool active: false
    property int sampleCount: 20
    property list<real> points: []
    property real normalizationCeiling: 100
    readonly property bool audioSignalActive: points.length > 0 && points.some(p => p > 0)

    onActiveChanged: {
        if (active) {
            IslandVisualizerService.acquire();
        } else {
            IslandVisualizerService.release();
            root.points = [];
        }
    }

    Connections {
        target: IslandVisualizerService
        function onPointsChanged() {
            if (root.active) {
                root.points = IslandVisualizerService.points;
            }
        }
    }

    Component.onDestruction: {
        if (active) {
            IslandVisualizerService.release();
        }
    }
}
