pragma ComponentBehavior: Bound
import QtQuick
import Clavis.Runtime
import qs.Services
import "../../Common/functions/DockLayout.js" as DockLayout

Item {
    id: root
    property var model: null
    property int count: 0
    property string edge: "bottom"
    property bool labelsLeft: true
    property real maximumWidth: 600
    property real maximumHeight: 800
    property real iconSize: 64
    property real maximumOutset: Infinity
    property point sourceCenter
    property real progress: 0
    property string actionText: ""
    property bool canOpen: true
    property bool canGoBack: false
    signal activated(var info)
    signal openRequested
    signal backRequested
    readonly property bool horizontal: edge !== "bottom"
    readonly property var geometry: DockLayout.folderFan(edge, count, maximumWidth, maximumHeight, labelsLeft,
                                                         iconSize, maximumOutset)
    readonly property bool hovered: hover.hovered
    readonly property var tiles: {
        const result = [openItem];
        for (const child of view.contentItem.children)
            if (child.fileTile && child.visible)
                result.push(child.fileTile);
        return result;
    }
    readonly property var blurRegions: {
        const result = [openBlur, actionBlur];
        for (const child of view.contentItem.children)
            if (child.blurRegion && child.visible)
                result.push(child.blurRegion);
        return result;
    }
    implicitWidth: geometry.width
    implicitHeight: geometry.height
    // Input includes the narrow gaps between rows, so traversing the curve
    // doesn't leave the popup or accidentally click the window underneath.
    HoverHandler {
        id: hover
    }
    HorizontalWheelArea {
        anchors.fill: parent
        z: 100
        enabled: root.horizontal && view.interactive && root.geometry.count > 0
        target: view
        reverseVertical: root.edge === "right"
    }
    ListView {
        id: view
        x: root.horizontal && root.edge === "right" ? root.width - width : 0
        y: root.horizontal ? 0 : root.geometry.header
        width: root.horizontal ? root.geometry.count * root.geometry.step : root.width
        height: root.horizontal ? root.height : root.geometry.count * root.geometry.step
        orientation: root.horizontal ? ListView.Horizontal : ListView.Vertical
        verticalLayoutDirection: ListView.BottomToTop
        layoutDirection: root.edge === "right" ? Qt.RightToLeft : Qt.LeftToRight
        model: root.model
        // Render the next few entries outside the normal scroll viewport;
        // their artwork folds back into the small overflow stack.
        displayMarginBeginning: root.geometry.step * 3
        displayMarginEnd: root.geometry.step * 3
        cacheBuffer: 0
        boundsBehavior: Flickable.StopAtBounds
        acceptedButtons: Qt.NoButton
        interactive: root.progress === 1 && !DockService.fileDragActive
        delegate: Item {
            id: row
            required property var fileInfo
            readonly property alias fileTile: tile
            readonly property var blurRegion: labelBlur
            width: root.horizontal ? root.geometry.step : view.width
            height: root.horizontal ? view.height : root.geometry.step
            readonly property real position: root.horizontal ? (root.edge === "left" ? x - view.contentX :
                                                                                       view.width - width - x
                                                                                       + view.contentX)
                                                               / width : (view.height - height - y
                                                                          + view.contentY) / height
            readonly property real stackDepth: Math.max(0, position - root.geometry.count + 1)
            readonly property var slot: DockLayout.folderFanSlot(root.edge, Math.min(position,
                                                                                     root.geometry.count - 1),
                                                                 root.geometry, root.labelsLeft)
            visible: root.geometry.count > 0 && position > -1 && stackDepth < 4
            z: -position
            DockFileTile {
                id: tile
                fileInfo: row.fileInfo
                fan: true
                verticalLabel: root.horizontal
                labelsLeft: root.labelsLeft
                tileIconSize: root.geometry.iconSize
                enabled: row.stackDepth < 0.001
                width: root.geometry.tileWidth
                height: root.geometry.tileHeight
                readonly property point center: Qt.point(iconItem.x + iconItem.width / 2, iconItem.y
                                                         + iconItem.height / 2)
                readonly property real finalX: row.slot.x + row.stackDepth * (root.horizontal ? (root.edge
                                                                                                 === "left"
                                                                                                 ? 7 : -7) : (
                                                                                                    root.labelsLeft
                                                                                                    ? 3 : -3))
                                               - view.x - row.x + view.contentX
                readonly property real finalY: row.slot.y - (root.horizontal ? 0 : row.stackDepth * 7) - view.y
                                               - row.y + view.contentY
                x: finalX + (root.sourceCenter.x - view.x - row.x + view.contentX - finalX - center.x) * (1
                                                                                                          - root.progress)
                y: finalY + (root.sourceCenter.y - view.y - row.y + view.contentY - finalY - center.y) * (1
                                                                                                          - root.progress)
                opacity: Math.min(1, root.progress * 2) * Math.min(1, row.position + 1) * (1 - row.stackDepth
                                                                                           / 4)
                labelReveal: Math.max(0, (root.progress - 0.4) / 0.6) * Math.pow(0.42, row.stackDepth)
                transform: [
                    Rotation {
                        origin.x: tile.center.x
                        origin.y: tile.center.y
                        angle: row.slot.rotation * root.progress
                    },
                    Scale {
                        origin.x: tile.center.x
                        origin.y: tile.center.y
                        xScale: (0.7 + 0.3 * root.progress) * Math.pow(0.94, row.stackDepth)
                        yScale: xScale
                    }
                ]
                onActivated: info => root.activated(info)
            }
            DockFanBlur {
                id: labelBlur
                sourceItem: tile.glassItem
                // A binary compositor blur mask cannot fade with the ghost
                // labels. Only the fully unfolded row supplies glass.
                enabled: row.visible && row.stackDepth < 0.001 && root.progress > 0
            }
        }
    }
    DockFileTile {
        id: openItem
        readonly property var slot: DockLayout.folderFanSlot(root.edge, root.geometry.count, root.geometry,
                                                             root.labelsLeft)
        fileInfo: ({
                       name: root.actionText
                   })
        actionIcon: root.canGoBack ? "arrow_back" : "open_in_new"
        fan: true
        verticalLabel: root.horizontal
        labelsLeft: root.labelsLeft
        tileIconSize: root.geometry.iconSize
        width: root.geometry.tileWidth
        height: root.geometry.tileHeight
        readonly property point center: Qt.point(iconItem.x + iconItem.width / 2, iconItem.y + iconItem.height
                                                 / 2)
        readonly property real finalX: slot.x
        readonly property real finalY: slot.y
        x: finalX + (root.sourceCenter.x - finalX - center.x) * (1 - root.progress)
        y: finalY + (root.sourceCenter.y - finalY - center.y) * (1 - root.progress)
        opacity: root.progress
        labelReveal: Math.max(0, (root.progress - 0.4) / 0.6)
        enabled: root.canGoBack || root.canOpen
        transform: Rotation {
            origin.x: openItem.center.x
            origin.y: openItem.center.y
            angle: openItem.slot.rotation * root.progress
        }
        onActivated: root.canGoBack ? root.backRequested() : root.openRequested()
    }
    DockFanBlur {
        id: openBlur
        sourceItem: openItem.glassItem
    }
    DockFanBlur {
        id: actionBlur
        sourceItem: openItem.actionGlassItem
        enabled: root.progress > 0
    }
}
