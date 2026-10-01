pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.common

GridView {
    id: root

    required property SpotlightStyle style
    required property var results
    required property int selectedIndex
    property bool searchActive: false
    readonly property int columns: Math.max(1, Math.floor(width / style.appGridCellWidth))

    signal selectionRequested(int index)
    signal activationRequested(int index)

    model: root.results
    currentIndex: root.selectedIndex
    cellWidth: Math.min(width, root.style.appGridCellWidth)
    cellHeight: root.style.appGridCellHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: false
    interactive: !DockService.externalDragActive
    // A nonvisual highlight lets the view animate scrolling to the current
    // item, including retargeting while an earlier movement is still running.
    highlight: Item {}
    highlightMoveDuration: root.style.resultScrollDuration

    ScrollBar.vertical: StyledScrollBar {}

    delegate: Item {
        id: tile

        required property int index
        required property var modelData
        readonly property bool selected: tile.index === root.selectedIndex
        width: root.cellWidth
        height: root.cellHeight

        Rectangle {
            id: tileSurface

            anchors.fill: parent
            anchors.margins: root.style.appGridGap / 2
            radius: Appearance.rounding.large
            color: !root.searchActive ? "transparent" : (tile.selected ? root.style.selectedColor : (
                                                                             tileMouse.containsMouse
                                                                             ? root.style.hoverColor :
                                                                               "transparent"))
            scale: tileMouse.pressed ? root.style.appGridPressedScale : 1

            Behavior on scale {
                NumberAnimation {
                    duration: root.style.panelDuration
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: root.style.effectsCurve
                }
            }

            ThemeIcon {
                id: appIcon

                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: 12
                width: root.style.appGridIconSize
                height: width
                visible: !tile.modelData.symbol
                iconSource: visible ? ApplicationService.iconSource(tile.modelData.icon) : ""
                sourceSize.width: root.style.appGridIconSize * 2
                sourceSize.height: root.style.appGridIconSize * 2
                asynchronous: true
                fillMode: Image.PreserveAspectFit
                scale: tile.selected || tileMouse.containsMouse ? root.style.appGridHoverScale : 1

                Behavior on scale {
                    NumberAnimation {
                        duration: root.style.panelDuration
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: root.style.effectsCurve
                    }
                }
            }

            Item {
                id: appSymbol
                anchors.centerIn: appIcon
                width: root.style.appGridIconSize
                height: width
                visible: !!tile.modelData.symbol
                scale: appIcon.scale
                MaterialSymbol {
                    anchors.centerIn: parent
                    text: tile.modelData.symbol || ""
                    iconSize: root.style.appGridIconSize
                    color: root.searchActive && tile.selected ? root.style.selectedContentColor :
                                                                tile.modelData.appObject?.dragOnly
                                                                ? Appearance.colors.colOnSurfaceVariant :
                                                                  Appearance.colors.colPrimary
                    transform: Scale {
                        origin.x: appSymbol.width / 2
                        xScale: tile.modelData.appObject?.id === ApplicationService.smallSpaceApplication.id
                                ? 0.5 : 1
                    }
                }
            }

            Text {
                id: appName

                anchors.top: appIcon.bottom
                anchors.topMargin: 10
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 8
                height: root.style.appGridLabelHeight
                text: tile.modelData.title
                textFormat: Text.PlainText
                font.family: Fonts.ui
                font.pixelSize: root.style.appGridLabelFontSize
                font.weight: Font.Medium
                color: root.searchActive && tile.selected ? root.style.selectedContentColor :
                                                            Appearance.colors.colOnSurface
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignTop
                maximumLineCount: 2
                wrapMode: Text.Wrap
                elide: Text.ElideRight
            }
        }

        MouseArea {
            id: tileMouse

            anchors.fill: tileSurface
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            acceptedButtons: Qt.LeftButton
            Accessible.description: tile.modelData.subtitle || ""
            Accessible.name: tile.modelData.title
            Accessible.role: Accessible.ListItem
            Accessible.selected: tile.selected
            Accessible.onPressAction: root.activationRequested(tile.index)
            onPositionChanged: {
                if (containsMouse)
                    root.selectionRequested(tile.index);
            }
            onPressed: appDrag.resetGesture()
            onClicked: {
                if (appDrag.dragged)
                    return;
                root.selectionRequested(tile.index);
                root.activationRequested(tile.index);
            }
        }

        SpotlightAppDrag {
            id: appDrag

            desktopId: tile.modelData.appObject ? String(tile.modelData.appObject.id) : ""
            iconItem: tile.modelData.symbol ? appSymbol : appIcon
        }

        ToolTip.visible: tileMouse.containsMouse && (appName.truncated || !!tile.modelData.appObject
                                                     ?.dragOnly) && !DockService.externalDragActive
        ToolTip.delay: 600
        ToolTip.text: tile.modelData.appObject?.dragOnly ? tile.modelData.subtitle : tile.modelData.title
    }
}
