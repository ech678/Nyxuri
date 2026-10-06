import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.shared.theme

Item {
    id: root

    required property var targetWindow
    required property Item backgroundItem
    property var additionalBackgroundItems: []
    property var additionalRegions: []
    property var subtractedBackgroundItems: []
    property var postSubtractionBackgroundItems: []
    property Item postSubtractionClipItem: null
    property bool blurEnabled: true
    // Gate on the shell's blur setting. `Appearance` carries the value because
    // this layer may not read config or probe the compositor itself.
    property bool compositorEnabled: Appearance.compositorBlurEnabled
    property real radius: 0
    property Item clipItem: null

    property bool surfaceReady: false
    property bool publishPending: false
    property bool destroying: false
    property var _regionObjects: []
    property var _subtractionRegionObjects: []
    property var _postSubtractionRegionObjects: []
    property var _appliedBackgroundItems: []
    property var _appliedSubtractedItems: []
    property var _appliedPostSubtractionItems: []

    function _itemsMatch(a, b) {
        if (!a && !b)
            return true;
        if (!a || !b)
            return false;
        if (a.length !== b.length)
            return false;
        for (let i = 0; i < a.length; ++i) {
            if (a[i] !== b[i])
                return false;
        }
        return true;
    }

    readonly property int visibleBackgroundCount: {
        let count = 0;
        const items = root.allBackgroundItems().concat(root.allPostSubtractionBackgroundItems());
        for (let index = 0; index < items.length; ++index) {
            const item = items[index];
            if (item && item.visible && item.opacity > 0 && item.width > 0 && item.height > 0)
                ++count;
        }
        return count;
    }
    readonly property bool shouldSubmit: root.compositorEnabled && root.blurEnabled && root.surfaceReady
                                         && root.targetWindow && root.targetWindow.visible
                                         && root.visibleBackgroundCount > 0
    readonly property var submittedRegion: root.shouldSubmit ? combinedRegion : null
    readonly property alias region: combinedRegion
    readonly property alias regionObjects: root._regionObjects
    readonly property alias subtractionRegionObjects: root._subtractionRegionObjects
    readonly property alias postSubtractionRegionObjects: root._postSubtractionRegionObjects

    visible: false

    function allBackgroundItems() {
        const items = [];
        if (root.backgroundItem)
            items.push(root.backgroundItem);
        const additional = root.additionalBackgroundItems || [];
        for (let index = 0; index < additional.length; ++index) {
            const item = additional[index];
            if (item && items.indexOf(item) < 0)
                items.push(item);
        }
        return items;
    }

    function combinedRegionCount() {
        return combinedRegion.regions.length;
    }

    function allSubtractedBackgroundItems() {
        const items = [];
        const subtracted = root.subtractedBackgroundItems || [];
        for (let index = 0; index < subtracted.length; ++index) {
            const item = subtracted[index];
            if (item && items.indexOf(item) < 0)
                items.push(item);
        }
        return items;
    }

    function allPostSubtractionBackgroundItems() {
        const items = [];
        const postSubtraction = root.postSubtractionBackgroundItems || [];
        for (let index = 0; index < postSubtraction.length; ++index) {
            const item = postSubtraction[index];
            if (item && items.indexOf(item) < 0)
                items.push(item);
        }
        return items;
    }

    function rebuildRegions() {
        const items = root.allBackgroundItems();
        const subtractedItems = root.allSubtractedBackgroundItems();
        const postSubtractionItems = root.allPostSubtractionBackgroundItems();

        if (root._regionObjects.length > 0
                && root._itemsMatch(items, root._appliedBackgroundItems)
                && root._itemsMatch(subtractedItems, root._appliedSubtractedItems)
                && root._itemsMatch(postSubtractionItems, root._appliedPostSubtractionItems)) {
            return;
        }

        root._appliedBackgroundItems = items.slice();
        root._appliedSubtractedItems = subtractedItems.slice();
        root._appliedPostSubtractionItems = postSubtractionItems.slice();

        for (let index = 0; index < root._regionObjects.length; ++index)
            root._regionObjects[index].destroy();
        for (let index = 0; index < root._subtractionRegionObjects.length; ++index)
            root._subtractionRegionObjects[index].destroy();
        for (let index = 0; index < root._postSubtractionRegionObjects.length; ++index)
            root._postSubtractionRegionObjects[index].destroy();

        const regions = [];
        for (let index = 0; index < items.length; ++index) {
            const region = itemRegionComponent.createObject(combinedRegion, {
                "sourceItem": items[index]
            });
            if (region)
                regions.push(region);
        }
        root._regionObjects = regions;

        const subtractionRegions = [];
        for (let index = 0; index < subtractedItems.length; ++index) {
            const region = subtractionRegionComponent.createObject(combinedRegion, {
                "sourceItem": subtractedItems[index]
            });
            if (region)
                subtractionRegions.push(region);
        }
        root._subtractionRegionObjects = subtractionRegions;

        const postSubtractionRegions = [];
        for (let index = 0; index < postSubtractionItems.length; ++index) {
            const region = clippedItemRegionComponent.createObject(combinedRegion, {
                "sourceItem": postSubtractionItems[index]
            });
            if (region)
                postSubtractionRegions.push(region);
        }
        root._postSubtractionRegionObjects = postSubtractionRegions;

        const combinedRegions = regions.slice();
        for (const region of root.additionalRegions)
            combinedRegions.push(region);
        for (let index = 0; index < subtractionRegions.length; ++index)
            combinedRegions.push(subtractionRegions[index]);
        for (let index = 0; index < postSubtractionRegions.length; ++index)
            combinedRegions.push(postSubtractionRegions[index]);
        if (root.clipItem)
            combinedRegions.push(clipRegion);
        combinedRegion.regions = combinedRegions;
        root.publish();
    }

    function publish() {
        if (root.destroying || !root.targetWindow)
            return;
        if (!root.submittedRegion) {
            root.clear();
            return;
        }
        if (root.publishPending)
            return;
        root.publishPending = true;
        Qt.callLater(root._executeCommit);
    }

    function _executeCommit() {
        if (!root.destroying)
            root.commit();
    }

    function commit() {
        root.publishPending = false;
        if (!root.targetWindow)
            return;
        const targetRegion = root.submittedRegion || null;
        if (root.targetWindow.BackgroundEffect.blurRegion !== targetRegion)
            root.targetWindow.BackgroundEffect.blurRegion = targetRegion;
    }

    function clear() {
        if (root.targetWindow && root.targetWindow.BackgroundEffect.blurRegion !== null)
            root.targetWindow.BackgroundEffect.blurRegion = null;
    }

    onBackgroundItemChanged: rebuildRegions()
    onAdditionalBackgroundItemsChanged: rebuildRegions()
    onAdditionalRegionsChanged: rebuildRegions()
    onSubtractedBackgroundItemsChanged: rebuildRegions()
    onPostSubtractionBackgroundItemsChanged: rebuildRegions()
    onPostSubtractionClipItemChanged: publish()
    onClipItemChanged: rebuildRegions()
    onSubmittedRegionChanged: publish()

    Component.onCompleted: {
        root.surfaceReady = !!root.targetWindow && root.targetWindow.visible;
        root.rebuildRegions();
    }

    Component.onDestruction: {
        root.destroying = true;
        root.publishPending = false;
        if (root.targetWindow)
            root.targetWindow.BackgroundEffect.blurRegion = null;
    }

    Connections {
        target: root.targetWindow
        enabled: root.targetWindow !== null
        ignoreUnknownSignals: true

        function onResourcesLost() {
            root.surfaceReady = false;
            root.clear();
        }

        function onWindowConnected() {
            root.surfaceReady = root.targetWindow.visible;
            root.publish();
        }

        function onVisibleChanged() {
            root.surfaceReady = root.targetWindow.visible;
            if (root.surfaceReady)
                root.publish();
            else
                root.clear();
        }
    }

    Connections {
        target: clipRegion
        function onChanged() {
            root.publish();
        }
    }

    TransformWatcher {
        id: clipTransformWatcher
        a: root.targetWindow ? root.targetWindow.contentItem : null
        b: root.clipItem
        onTransformChanged: root.publish()
    }

    Region {
        id: combinedRegion
        onChanged: root.publish()
    }

    Region {
        id: clipRegion
        item: root.clipItem && root.clipItem.visible && root.clipItem.width > 0 && root.clipItem.height > 0
              ? root.clipItem : null
        intersection: Intersection.Intersect
    }

    Component {
        id: itemRegionComponent
        Region {
            required property Item sourceItem
            property TransformWatcher geometryWatcher: TransformWatcher {
                a: root.targetWindow ? root.targetWindow.contentItem : null
                b: sourceItem
                onTransformChanged: root.publish()
            }
            onChanged: root.publish()
            item: sourceItem && sourceItem.visible && sourceItem.opacity > 0 && sourceItem.width > 0
                  && sourceItem.height > 0 ? sourceItem : null
            radius: sourceItem && sourceItem.radius !== undefined ? Math.max(0, Math.round(sourceItem.radius)) : Math.max(0, Math.round(root.radius))
            intersection: Intersection.Combine
        }
    }

    Component {
        id: subtractionRegionComponent
        Region {
            required property Item sourceItem
            property TransformWatcher geometryWatcher: TransformWatcher {
                a: root.targetWindow ? root.targetWindow.contentItem : null
                b: sourceItem
                onTransformChanged: root.publish()
            }
            onChanged: root.publish()
            item: sourceItem && sourceItem.visible && sourceItem.width > 0 && sourceItem.height > 0
                  ? sourceItem : null
            radius: sourceItem && sourceItem.radius !== undefined ? Math.max(0, Math.round(sourceItem.radius)) : Math.max(0, Math.round(root.radius))
            intersection: Intersection.Subtract
        }
    }

    Component {
        id: clippedItemRegionComponent
        Region {
            required property Item sourceItem
            intersection: Intersection.Combine
            onChanged: root.publish()
            property TransformWatcher sourceWatcher: TransformWatcher {
                a: root.targetWindow ? root.targetWindow.contentItem : null
                b: sourceItem
                onTransformChanged: root.publish()
            }
            property TransformWatcher viewportWatcher: TransformWatcher {
                a: root.targetWindow ? root.targetWindow.contentItem : null
                b: root.postSubtractionClipItem
                onTransformChanged: root.publish()
            }
            Region {
                item: sourceItem && sourceItem.visible && sourceItem.opacity > 0 && sourceItem.width > 0
                      && sourceItem.height > 0 ? sourceItem : null
                radius: sourceItem && sourceItem.radius !== undefined ? sourceItem.radius : root.radius
                intersection: Intersection.Combine
                onChanged: root.publish()
            }
            Region {
                item: root.postSubtractionClipItem && root.postSubtractionClipItem.visible
                      && root.postSubtractionClipItem.width > 0 && root.postSubtractionClipItem.height > 0
                      ? root.postSubtractionClipItem : null
                radius: root.postSubtractionClipItem && root.postSubtractionClipItem.radius !== undefined
                        ? root.postSubtractionClipItem.radius : root.radius
                intersection: root.postSubtractionClipItem ? Intersection.Intersect : Intersection.Combine
                onChanged: root.publish()
            }
        }
    }
}
