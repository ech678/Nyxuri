import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.services
import qs.commons
import qs.ui

PanelWindow {
    id: root

    required property string edge
    readonly property real visualThickness: Sizes.barVisualThickness
    readonly property real outerEdgeMargin: Sizes.barOuterEdgeMargin
    readonly property int cornerStyle: PersonalizationConfig.barCornerStyle
    readonly property bool hasScreenCorners: (root.cornerStyle === 0 && !content.centerOnly) || root.cornerStyle === 4
    readonly property real decoratorBuffer: root.hasScreenCorners ? Appearance.rounding.screenRounding : 0

    readonly property real exclusiveThickness: {
        switch (root.cornerStyle) {
        case 0:
            return root.visualThickness;
        case 1:
            return root.outerEdgeMargin + root.visualThickness;
        case 2:
            return Math.max(0, root.visualThickness - 6);
        case 4:
        case 5:
            return root.visualThickness + 4;
        default:
            return root.visualThickness;
        }
    }
    // Shadow and decorator pixels need surface space, but must not reserve desktop space.
    readonly property real surfaceThickness: outerEdgeMargin + visualThickness + Sizes.barShadowBuffer + root.decoratorBuffer

    implicitHeight: surfaceThickness
    color: "transparent"
    exclusiveZone: PersonalizationConfig.barOverlay ? 0 : exclusiveThickness
    // Floating changes desktop reservation, not stacking above fullscreen windows.
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.namespace: "nyxuri-shell-bar-horizontal"
    WlrLayershell.exclusionMode: PersonalizationConfig.barOverlay ? ExclusionMode.Ignore : ExclusionMode.Normal

    BarAxis {
        id: axis

        edge: root.edge
    }

    anchors {
        left: true
        right: true
        top: axis.isTop
        bottom: axis.isBottom
    }

    Item {
        id: visualBand

        x: 0
        y: axis.isTop ? root.outerEdgeMargin : (Sizes.barShadowBuffer + root.decoratorBuffer)
        width: parent.width
        height: root.visualThickness

        HorizontalBarContent {
            id: content

            anchors.fill: parent
            screen: root.screen
            axis: axis
        }
    }

    Loader {
        id: roundDecorators

        anchors {
            left: parent.left
            right: parent.right
            top: axis.isTop ? visualBand.bottom : undefined
            bottom: axis.isBottom ? visualBand.top : undefined
        }
        height: Appearance.rounding.screenRounding
        active: root.hasScreenCorners

        sourceComponent: Item {
            implicitHeight: Appearance.rounding.screenRounding

            readonly property color decoratorColor: Appearance.colors.colLayer0

            RoundCorner {
                id: leftCorner

                anchors {
                    top: parent.top
                    bottom: parent.bottom
                    left: parent.left
                }
                implicitSize: Appearance.rounding.screenRounding
                color: parent.decoratorColor
                corner: axis.isBottom ? RoundCorner.CornerEnum.BottomLeft : RoundCorner.CornerEnum.TopLeft
            }

            RoundCorner {
                id: rightCorner

                anchors {
                    top: parent.top
                    bottom: parent.bottom
                    right: parent.right
                }
                implicitSize: Appearance.rounding.screenRounding
                color: parent.decoratorColor
                corner: axis.isBottom ? RoundCorner.CornerEnum.BottomRight : RoundCorner.CornerEnum.TopRight
            }
        }
    }

    CompositorBlurRegion {
        targetWindow: root
        backgroundItem: content.backgroundItems.length > 0 ? content.backgroundItems[0] : null
        additionalBackgroundItems: content.backgroundItems.slice(1)
        radius: 18
    }

    mask: Region {
        Region {
            item: content.leadingInputRegionItem
        }

        Region {
            item: content.centerInputRegionItem
        }

        Region {
            item: content.trailingInputRegionItem
        }

        Region {
            item: roundDecorators.item
        }

        HotCornerExclusionRegion {
            active: NiriConfigService.ready("hot-corners")
            cornerActions: PersonalizationConfig.hotCornerActions
            surfaceWidth: root.width
            surfaceHeight: root.height
            topEdge: axis.isTop
            bottomEdge: axis.isBottom
        }
    }
}
