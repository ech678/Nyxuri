// Fork & Trim: end4-pC modules/ii/bar/BarGroup.qml (GPL-3, see
// shell/LICENSE appendix end-4-dots-hyprland-GPL-3.0.txt). B4 reskin promotes
// this component to plugins/bar/.
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services

Item {
    id: root

    property bool vertical: false
    property int currentIndex: 0
    property int totalCount: 0
    readonly property bool isMaterial: PersonalizationConfig.barCornerStyle === 3 || PersonalizationConfig.barCornerStyle === 4
    property bool paintMaterialPill: false
    property bool paintBackground: true
    property color bgColor: Appearance.colors.colPrimaryContainer
    property string widgetName: ""

    readonly property string borderlessMode: PersonalizationConfig.barBorderless ?? "pills"
    readonly property bool isSegmented: root.borderlessMode === "segmented"
    readonly property bool isPanel: PersonalizationConfig.barCornerStyle === 5
    readonly property real panelRadius: 14

    readonly property color resolvedGroupColor: Appearance.colors.colLayer1

    readonly property real fullRadius: root.isPanel ? root.panelRadius : (root.vertical ? (width / 2) : (height / 2))
    readonly property real midRadius: root.isPanel ? root.panelRadius : root.isSegmented ? 0 : (PersonalizationConfig.barCornerStyle === 2 ? 6 : 10)

    property real startRadius: {
        if (totalCount <= 1)
            return fullRadius;
        if (currentIndex === 0)
            return fullRadius;
        return midRadius;
    }
    property real endRadius: {
        if (totalCount <= 1)
            return fullRadius;
        if (currentIndex === totalCount - 1)
            return fullRadius;
        return midRadius;
    }

    property real padding: (root.isMaterial && !root.paintMaterialPill) ? 0 : 4

    implicitWidth: vertical && root.isMaterial ? 40 : (gridLayout.implicitWidth + padding * 2)
    implicitHeight: vertical ? (gridLayout.implicitHeight + padding * 2) : 32

    default property alias items: gridLayout.children

    readonly property Item loadedWidget: gridLayout.children.length > 0 ? (gridLayout.children[0]?.item ?? gridLayout.children[0]) : null

    Binding {
        target: root.loadedWidget && "backgroundVisible" in root.loadedWidget ? root.loadedWidget : null
        property: "backgroundVisible"
        value: false
    }

    Rectangle {
        id: background

        anchors {
            fill: parent
            topMargin: root.vertical ? 0 : 2
            bottomMargin: root.vertical ? 0 : 2
            leftMargin: root.vertical ? 2 : 0
            rightMargin: root.vertical ? 2 : 0
        }
        color: !root.paintBackground ? "transparent" : (root.isMaterial && !root.paintMaterialPill) ? "transparent" : (root.isMaterial && root.paintMaterialPill) ? root.bgColor : (root.borderlessMode === "transparent" ? "transparent" : PersonalizationConfig.barCornerStyle === 2 ? Appearance.colors.colLayer0 : root.resolvedGroupColor)

        border.width: (root.paintBackground && root.isSegmented && !root.isMaterial) ? 1 : 0
        border.color: Appearance.colors.colLayer0Border

        topLeftRadius: (root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.startRadius)
        bottomLeftRadius: (root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.vertical ? root.endRadius : root.startRadius)
        topRightRadius: (root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.vertical ? root.startRadius : root.endRadius)
        bottomRightRadius: (root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.endRadius)

        Behavior on color {
            NumberAnimation {
                duration: Appearance.animation.elementMoveFast.duration
            }
        }
    }

    GridLayout {
        id: gridLayout

        columns: root.vertical ? 1 : -1
        anchors.centerIn: parent
        columnSpacing: 0
        rowSpacing: 0
    }
}
