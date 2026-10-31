pragma ComponentBehavior: Bound

import QtQuick
import qs.shared.theme

Item {
    id: root

    property url source
    property string route: ""
    property int navigationDepth: 0
    property bool presentationActive: false
    property bool animationsEnabled: true
    property Component headerComponent: null
    readonly property var item: currentLayer ? currentLayer.page : null
    readonly property bool ready: currentLayer !== null && currentLayer.pageSource === source && pendingLayer
                                  === null
    property var currentLayer: null
    property var pendingLayer: null

    signal loaded

    function loadPage() {
        if (pendingLayer) {
            pendingLayer.destroy();
            pendingLayer = null;
        }
        if (!source.toString().length || (currentLayer && currentLayer.pageSource === source))
            return;
        const next = pageComponent.createObject(root, {
                                                    route: root.route,
                                                    navigationDepth: root.navigationDepth,
                                                    header: root.headerComponent
                                                });
        if (!next)
            return;
        pendingLayer = next;
        next.load(source);
    }

    function present(nextLayer) {
        if (pendingLayer !== nextLayer || nextLayer.pageSource !== root.source)
            return;
        const previous = currentLayer;
        // Peers fade in place; deeper routes and back navigation share an axis.
        // With animationsEnabled false the host swaps instantly — an owning
        // window can drive its own container-level transition instead.
        const direction = previous ? Math.sign(nextLayer.navigationDepth - previous.navigationDepth) : 0;
        const readingDirection = root.LayoutMirroring.enabled ? -1 : 1;
        nextLayer.enterOffset = direction * readingDirection * Metrics.spacingL;
        nextLayer.animate = previous !== null && root.animationsEnabled;
        currentLayer = nextLayer;
        pendingLayer = null;
        loaded();
        nextLayer.active = true;
        if (previous) {
            previous.exitOffset = -direction * readingDirection * Metrics.spacingL;
            previous.animate = root.animationsEnabled;
            previous.retired = true;
            previous.active = false;
            if (!previous.visible)
                previous.destroy();
        }
    }

    onSourceChanged: {
        if (!root.animationsEnabled)
            root.loadPage();
        else
            Qt.callLater(root.loadPage);
    }
    clip: true

    Component {
        id: pageComponent

        Item {
            id: pageLayer

            required property string route
            required property int navigationDepth
            property bool active: false
            property bool animate: false
            property real enterOffset: 0
            property real exitOffset: 0
            property Component header
            property bool retired: false
            readonly property var page: loader.item
            readonly property url pageSource: loader.source

            function load(url) {
                loader.source = url;
            }

            // Animate visual properties only; page geometry stays fixed.
            width: root.width
            height: root.height
            enabled: active
            visible: active || opacity > 0
            opacity: active ? 1 : 0
            x: active ? 0 : (retired ? exitOffset : enterOffset)
            z: active ? 1 : 0

            Behavior on opacity {
                enabled: root.presentationActive && pageLayer.animate
                NumberAnimation {
                    duration: pageLayer.active ? Appearance.animation.expressiveDefaultEffects.duration :
                                                 Appearance.animation.expressiveFastEffects.duration
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: pageLayer.active ? Animations.curves.standardDecel :
                                                           Animations.curves.standardAccel
                }
            }

            Behavior on x {
                enabled: root.presentationActive && pageLayer.animate
                NumberAnimation {
                    duration: Appearance.animation.elementResize.duration
                    easing.type: Appearance.animation.elementResize.type
                    easing.bezierCurve: Appearance.animation.elementResize.bezierCurve
                }
            }
            onVisibleChanged: {
                if (retired && !visible)
                    destroy();
            }

            Loader {
                id: headerLoader

                readonly property string route: pageLayer.route
                width: parent.width
                sourceComponent: pageLayer.header
            }

            Loader {
                id: loader

                anchors.fill: parent
                anchors.topMargin: headerLoader.height
                asynchronous: root.animationsEnabled
                onLoaded: root.present(pageLayer)
            }
        }
    }
}
