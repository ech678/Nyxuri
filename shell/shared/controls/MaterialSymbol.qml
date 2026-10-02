import QtQuick

Text {
    id: root

    property real iconSize: 22
    property real fill: 0
    property string symbolFamily: "Material Symbols Rounded"
    readonly property real roundedFill: Number(fill).toFixed(1)
    readonly property int renderedIconSize: Math.max(1, Math.round(root.iconSize))
    readonly property int opticalSize: {
        if (root.renderedIconSize <= 20)
            return 20;
        if (root.renderedIconSize <= 28)
            return 24;
        if (root.renderedIconSize <= 44)
            return 40;
        return 48;
    }

    width: root.renderedIconSize
    height: root.renderedIconSize
    clip: true

    renderType: Text.NativeRendering
    font {
        family: root.symbolFamily
        pixelSize: root.renderedIconSize
        weight: Font.Normal + (Font.DemiBold - Font.Normal) * root.roundedFill
        variableAxes: {
            "FILL": root.roundedFill,
            "opsz": root.opticalSize
        }
    }
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
}
