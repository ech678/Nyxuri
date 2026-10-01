import QtQuick
import QtQuick.Controls
import Quickshell
import qs.Common
import qs.Widgets.common

Item {
    id: root

    property string text: ""
    property int textFormat: Text.AutoText
    property bool extraVisibleCondition: true
    property bool alternativeVisibleCondition: false
    property real horizontalPadding: 10
    property real verticalPadding: 5
    property real horizontalMargin: horizontalPadding
    property real verticalMargin: verticalPadding
    readonly property string contextualEdge: findContextEdge(root.parent)
    property var anchorEdges: edgeToAnchor(contextualEdge)
    property var anchorGravity: anchorEdges
    property font font

    font {
        family: Fonts.ui
        pixelSize: 12
        hintingPreference: Font.PreferNoHinting
    }

    function findContextEdge(item) {
        let current = item;
        while (current !== null && current !== undefined) {
            if (current.popupEdge !== undefined)
                return current.popupEdge;
            current = current.parent;
        }
        return "top";
    }

    function edgeToAnchor(edge) {
        switch (edge) {
        case "bottom":
            return Edges.Top;
        case "left":
            return Edges.Right;
        case "right":
            return Edges.Left;
        default:
            return Edges.Bottom;
        }
    }

    readonly property var anchorWindow: root.QsWindow.window
    readonly property bool anchorWindowReady: root.anchorWindow !== null && root.anchorWindow !== undefined
                                              && root.anchorWindow.backingWindowVisible
    readonly property bool usingFallback: fallbackTooltip.visible
    // Visibility is intentionally based on the direct anchor only. Walking
    // the QML parent hierarchy from a binding makes the tooltip's Loader and
    // its Controls/layout ancestors depend on one another.
    readonly property bool internalVisibleCondition: (extraVisibleCondition && (root.parent === null
                                                                                || root.parent.hovered
                                                                                === undefined
                                                                                || root.parent.hovered))
                                                     || alternativeVisibleCondition
    readonly property var popupWindow: tooltipLoader.item

    function updateAnchor() {
        if (tooltipLoader.item)
            tooltipLoader.item.anchor.updateAnchor();
    }

    Loader {
        id: tooltipLoader

        anchors.fill: parent
        active: root.internalVisibleCondition && root.anchorWindowReady

        sourceComponent: PopupWindow {
            id: tooltipWindow

            readonly property alias tooltipContentItem: tooltipContent

            visible: true
            color: "transparent"
            implicitWidth: tooltipContent.implicitWidth + root.horizontalMargin * 2
            implicitHeight: tooltipContent.implicitHeight + root.verticalMargin * 2

            Component.onCompleted: tooltipContent.shown = true

            anchor {
                window: root.anchorWindow
                item: root.parent
                edges: root.anchorEdges
                gravity: root.anchorGravity
            }

            mask: Region {
                item: null
            }

            StyledToolTipContent {
                id: tooltipContent

                x: root.horizontalMargin
                y: root.verticalMargin
                text: root.text
                textFormat: root.textFormat
                shown: false
                horizontalPadding: root.horizontalPadding
                verticalPadding: root.verticalPadding
                font: root.font
            }

            CompositorBlurRegion {
                targetWindow: tooltipWindow
                backgroundItem: tooltipContent.blurBackgroundItem
                blurEnabled: tooltipContent.shown
            }
        }
    }

    ToolTip {
        id: fallbackTooltip

        visible: root.internalVisibleCondition && (root.anchorWindow === null || root.anchorWindow
                                                   === undefined)
        delay: 0
        padding: 0
        background: null

        contentItem: StyledToolTipContent {
            text: root.text
            textFormat: root.textFormat
            shown: fallbackTooltip.visible
            horizontalPadding: root.horizontalPadding
            verticalPadding: root.verticalPadding
            font: root.font
        }
    }
}
