import QtQuick
import QtQuick.Effects
import qs.Common
import qs.Services

Item {
    id: root

    property color fillColor: BlurService.backgroundColor(
        Appearance.colors.colLayer0)
    property real cornerRadius: height / 2
    property real shadowPadding: Sizes.barShadowBuffer
    readonly property string contextualEdge: findContextEdge(root.parent)

    function findContextEdge(item) {
        let current = item;
        while (current !== null && current !== undefined) {
            if (current.popupEdge !== undefined)
                return current.popupEdge;
            current = current.parent;
        }
        return "top";
    }

    Rectangle {
        id: sourceItem

        anchors.fill: parent
        color: root.fillColor
        radius: root.cornerRadius
        visible: false
    }

    MultiEffect {
        anchors.fill: sourceItem
        source: sourceItem
        shadowEnabled: true
        shadowColor: Appearance.applyAlpha(
            Appearance.colors.colShadow, 0.4)
        shadowBlur: 0.8
        shadowVerticalOffset: root.contextualEdge === "top" ? 3
            : root.contextualEdge === "bottom" ? -3 : 0
        shadowHorizontalOffset: root.contextualEdge === "left" ? 3
            : root.contextualEdge === "right" ? -3 : 0

        // Let MultiEffect derive the source texture padding from its blur.
        // A manually expanded paddingRect caused the source itself to vanish
        // on the Qt version used by Clavis. The PanelWindow still reserves
        // shadowPadding below the visual bar for the resulting shadow.
        autoPaddingEnabled: true
    }
}
