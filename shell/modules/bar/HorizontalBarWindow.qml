import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.app.services
import qs.shared.theme
import qs.shared.controls

PanelWindow {
    id: root

    required property string edge
    readonly property real visualThickness: Sizes.barVisualThickness
    readonly property real outerEdgeMargin: Sizes.barOuterEdgeMargin
    // Shadow pixels need surface space, but must not reserve desktop space.
    readonly property real surfaceThickness: outerEdgeMargin + visualThickness + Sizes.barShadowBuffer
    readonly property real exclusiveThickness: outerEdgeMargin + visualThickness

    implicitHeight: surfaceThickness
    color: "transparent"
    exclusiveZone: PersonalizationConfig.barOverlay ? 0 : exclusiveThickness
    // Floating changes desktop reservation, not stacking above fullscreen windows.
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.namespace: "nyxuri-shell-bar-horizontal"
    WlrLayershell.exclusionMode: PersonalizationConfig.barOverlay ? ExclusionMode.Ignore :
                                                                    ExclusionMode.Normal

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
        y: axis.isTop ? root.outerEdgeMargin : Sizes.barShadowBuffer
        width: parent.width
        height: root.visualThickness

        HorizontalBarContent {
            id: content

            anchors.fill: parent
            screen: root.screen
            axis: axis
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
