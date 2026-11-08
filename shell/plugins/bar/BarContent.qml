// Fork & Trim: end4-pC modules/ii/bar/BarContent.qml (GPL-3, see
// shell/LICENSE appendix end-4-dots-hyprland-GPL-3.0.txt). B4 reskin integrates
// end4 3-lane cornerStyle, BarGroup, and center-only semantics into Nyxuri bar.
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import "."

Item {
    id: root

    required property var screen
    required property var axis
    property bool vertical: false
    property string popupEdge: axis.edge

    readonly property int cornerStyle: PersonalizationConfig.barCornerStyle
    readonly property bool isMaterial: root.cornerStyle === 3 || root.cornerStyle === 4
    readonly property bool isMaterialHug: root.cornerStyle === 4
    readonly property bool isPanel: root.cornerStyle === 5
    readonly property color materialPillBgColor: Appearance.colors.colLayer0

    readonly property bool centerOnly: PersonalizationConfig.barLayoutLeft.length === 0 && PersonalizationConfig.barLayoutRight.length === 0

    readonly property Item leadingInputRegionItem: leftContainer
    readonly property Item centerInputRegionItem: centerContainer
    readonly property Item trailingInputRegionItem: rightContainer

    readonly property var backgroundItems: (() => {
            const items = [];
            if (barBackground && barBackground.visible && barBackground.color !== "transparent")
                items.push(barBackground);
            if (centerPill && centerPill.visible && centerPill.color !== "transparent")
                items.push(centerPill);
            if (leftMaterialPill && leftMaterialPill.visible)
                items.push(leftMaterialPill);
            if (centerMaterialPill && centerMaterialPill.visible)
                items.push(centerMaterialPill);
            if (rightMaterialPill && rightMaterialPill.visible)
                items.push(rightMaterialPill);
            return items;
        })()

    function shouldPaintMaterialPill(name) {
        if (!root.isMaterial)
            return false;
        const blacklist = ["workspaces", "divisor", "activeWindow", "island", "information"];
        return blacklist.indexOf(name) === -1;
    }

    function getMaterialPillColor(name) {
        if (!root.isMaterial)
            return Appearance.colors.colPrimaryContainer;
        switch (name) {
        case "media":
        case "tray":
            return Appearance.colors.colSecondaryContainer;
        case "systemMonitor":
            return Appearance.colors.colTertiaryContainer;
        case "quickSettings":
            return Appearance.colors.colPrimary;
        default:
            return Appearance.colors.colPrimaryContainer;
        }
    }

    // ── Full bar background (Floating / Hug / Panel) ─────────────────────
    Rectangle {
        id: barBackground

        anchors.fill: parent
        anchors.margins: root.cornerStyle === 1 ? (root.vertical ? 4 : 4) : 0
        visible: !root.centerOnly && root.cornerStyle !== 2 && !root.isMaterial
        color: visible ? Appearance.colors.colLayer0 : "transparent"
        radius: root.cornerStyle === 1 ? Appearance.rounding.windowRounding : 0
        border.width: root.cornerStyle === 1 ? 1 : 0
        border.color: Appearance.colors.colLayer0Border
    }

    // ── Center-only pill (when left & right lanes are empty) ─────────────
    Rectangle {
        id: centerPill

        visible: root.centerOnly && root.cornerStyle !== 2
        anchors.centerIn: parent
        width: root.vertical ? (parent.width - (root.cornerStyle === 1 ? 8 : 0)) : (middleContent.implicitWidth + 12)
        height: root.vertical ? (middleContent.implicitHeight + 12) : (parent.height - (root.cornerStyle === 1 ? 8 : 0))
        color: root.isMaterial ? "transparent" : Appearance.colors.colLayer0
        radius: (root.cornerStyle === 1 || root.isMaterial) ? Appearance.rounding.windowRounding : (root.cornerStyle === 0 ? 0 : 16)
        border.width: root.cornerStyle === 1 ? 1 : 0
        border.color: Appearance.colors.colLayer0Border

        bottomLeftRadius: (root.cornerStyle === 0 && !root.vertical && !root.axis.isBottom) ? Appearance.rounding.screenRounding : radius
        bottomRightRadius: (root.cornerStyle === 0 && !root.vertical && !root.axis.isBottom) ? Appearance.rounding.screenRounding : radius
        topLeftRadius: (root.cornerStyle === 0 && !root.vertical && root.axis.isBottom) ? Appearance.rounding.screenRounding : radius
        topRightRadius: (root.cornerStyle === 0 && !root.vertical && root.axis.isBottom) ? Appearance.rounding.screenRounding : radius
    }

    // Center-only screen fillets for Hug mode
    RoundCorner {
        id: leftPillCorner

        visible: root.centerOnly && root.cornerStyle === 0 && !root.vertical
        x: centerPill.x - implicitSize
        y: root.axis.isBottom ? (centerPill.y + centerPill.height - implicitSize) : centerPill.y
        implicitSize: Appearance.rounding.screenRounding
        color: Appearance.colors.colLayer0
        corner: root.axis.isBottom ? RoundCorner.CornerEnum.BottomRight : RoundCorner.CornerEnum.TopRight
    }

    RoundCorner {
        id: rightPillCorner

        visible: root.centerOnly && root.cornerStyle === 0 && !root.vertical
        x: centerPill.x + centerPill.width
        y: root.axis.isBottom ? (centerPill.y + centerPill.height - implicitSize) : centerPill.y
        implicitSize: Appearance.rounding.screenRounding
        color: Appearance.colors.colLayer0
        corner: root.axis.isBottom ? RoundCorner.CornerEnum.BottomLeft : RoundCorner.CornerEnum.TopLeft
    }

    // ── Content container (Left / Center / Right) ────────────────────────
    Item {
        id: contentContainer

        anchors.fill: parent

        // ── Left section ─────────────────────────────────────────────────
        Item {
            id: leftContainer

            anchors {
                left: root.vertical ? undefined : parent.left
                top: root.vertical ? parent.top : undefined
                leftMargin: root.vertical ? 0 : (root.isMaterialHug ? 0 : (root.cornerStyle === 1 ? 8 : 4))
                topMargin: root.vertical ? (root.isMaterialHug ? 0 : (root.cornerStyle === 1 ? 8 : 4)) : 0
                verticalCenter: root.vertical ? undefined : parent.verticalCenter
                horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
            }
            width: root.vertical ? parent.width : (root.isMaterial ? leftMaterialPill.width : leftRow.implicitWidth)
            height: root.vertical ? (root.isMaterial ? leftMaterialPill.height : leftRow.implicitHeight) : parent.height

            // Material pill wrapper (Left)
            Rectangle {
                id: leftMaterialPill

                visible: root.isMaterial && PersonalizationConfig.barLayoutLeft.length > 0
                anchors.centerIn: parent
                width: root.vertical ? (parent.width - (root.isMaterialHug ? 0 : 8)) : (leftRow.implicitWidth + 8)
                height: root.vertical ? (leftRow.implicitHeight + 8) : (parent.height - (root.isMaterialHug ? 0 : 8))
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor
            }

            GridLayout {
                id: leftRow

                anchors.centerIn: parent
                columns: root.vertical ? 1 : -1
                rows: root.vertical ? -1 : 1
                columnSpacing: 2
                rowSpacing: 2

                Repeater {
                    id: leftRepeater

                    model: PersonalizationConfig.barLayoutLeft

                    delegate: BarComponentLoader {
                        required property string modelData
                        required property int index

                        Layout.fillHeight: !root.vertical
                        Layout.fillWidth: root.vertical
                        componentId: modelData
                        screen: root.screen
                        axis: root.axis
                        barVisualItem: root
                        vertical: root.vertical
                        currentIndex: index
                        totalCount: leftRepeater.count
                    }
                }
            }
        }

        // ── Center section ────────────────────────────────────────────────
        Item {
            id: centerContainer

            anchors.centerIn: parent
            width: root.vertical ? parent.width : (root.isMaterial ? centerMaterialPill.width : middleContent.implicitWidth)
            height: root.vertical ? (root.isMaterial ? centerMaterialPill.height : middleContent.implicitHeight) : parent.height

            // Material pill wrapper (Center)
            Rectangle {
                id: centerMaterialPill

                visible: root.isMaterial && PersonalizationConfig.barLayoutMiddle.length > 0
                anchors.centerIn: parent
                width: root.vertical ? (parent.width - (root.isMaterialHug ? 0 : 8)) : (middleContent.implicitWidth + 8)
                height: root.vertical ? (middleContent.implicitHeight + 8) : (parent.height - (root.isMaterialHug ? 0 : 8))
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor
            }

            GridLayout {
                id: middleContent

                anchors.centerIn: parent
                columns: root.vertical ? 1 : -1
                rows: root.vertical ? -1 : 1
                columnSpacing: 2
                rowSpacing: 2

                Repeater {
                    id: centerRepeater

                    model: PersonalizationConfig.barLayoutMiddle

                    delegate: BarComponentLoader {
                        required property string modelData
                        required property int index

                        Layout.fillHeight: !root.vertical
                        Layout.fillWidth: root.vertical
                        componentId: modelData
                        screen: root.screen
                        axis: root.axis
                        barVisualItem: root
                        vertical: root.vertical
                        currentIndex: index
                        totalCount: centerRepeater.count
                    }
                }
            }
        }

        // ── Right section ─────────────────────────────────────────────────
        Item {
            id: rightContainer

            anchors {
                right: root.vertical ? undefined : parent.right
                bottom: root.vertical ? parent.bottom : undefined
                rightMargin: root.vertical ? 0 : (root.isMaterialHug ? 0 : (root.cornerStyle === 1 ? 8 : 4))
                bottomMargin: root.vertical ? (root.isMaterialHug ? 0 : (root.cornerStyle === 1 ? 8 : 4)) : 0
                verticalCenter: root.vertical ? undefined : parent.verticalCenter
                horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
            }
            width: root.vertical ? parent.width : (root.isMaterial ? rightMaterialPill.width : rightRow.implicitWidth)
            height: root.vertical ? (root.isMaterial ? rightMaterialPill.height : rightRow.implicitHeight) : parent.height

            // Material pill wrapper (Right)
            Rectangle {
                id: rightMaterialPill

                visible: root.isMaterial && PersonalizationConfig.barLayoutRight.length > 0
                anchors.centerIn: parent
                width: root.vertical ? (parent.width - (root.isMaterialHug ? 0 : 8)) : (rightRow.implicitWidth + 8)
                height: root.vertical ? (rightRow.implicitHeight + 8) : (parent.height - (root.isMaterialHug ? 0 : 8))
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor
            }

            GridLayout {
                id: rightRow

                anchors.centerIn: parent
                columns: root.vertical ? 1 : -1
                rows: root.vertical ? -1 : 1
                columnSpacing: 2
                rowSpacing: 2

                Repeater {
                    id: trailingRepeater

                    model: PersonalizationConfig.barLayoutRight

                    delegate: BarComponentLoader {
                        required property string modelData
                        required property int index

                        Layout.fillHeight: !root.vertical
                        Layout.fillWidth: root.vertical
                        componentId: modelData
                        screen: root.screen
                        axis: root.axis
                        barVisualItem: root
                        vertical: root.vertical
                        currentIndex: index
                        totalCount: trailingRepeater.count
                    }
                }
            }
        }
    }
}
