pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.Common
import qs.Services
import qs.Widgets.common
import "../../Common/functions/SpotlightLocalSearch.js" as LocalSearch

Item {
    id: root
    required property SpotlightStyle style
    required property var results
    required property int selectedIndex
    property string error: ""
    property real layoutWidth: width
    readonly property var capacities: ({
                                           apps: Math.max(2, Math.floor(layoutWidth
                                                                        / style.searchAppCellWidth)),
                                           wallpapers: Math.max(2, Math.floor(layoutWidth
                                                                              / style.searchWallpaperCellWidth))
                                       })
    readonly property var rows: LocalSearch.visualRows(results, capacities)
    readonly property int currentRow: LocalSearch.visualRowIndex(rows, selectedIndex)
    readonly property bool horizontalSelection: currentRow >= 0 && LocalSearch.horizontalGroup(
                                                    rows[currentRow].kind)
    readonly property real rowsHeight: rows.reduce((height, row) => height + rowHeight(row), 0) + (error ? 32 :
                                                                                                           0)
    signal selectionRequested(int index)
    signal activationRequested(string id)

    function contentHeight(row) {
        if (row.kind === "apps")
            return style.searchAppRowHeight;
        if (row.kind === "wallpapers")
            return Math.max(1, width / capacities.wallpapers - 20) / style.wallpaperPreviewAspectRatio + 44;
        return style.searchListRowHeight;
    }
    function rowHeight(row) {
        return contentHeight(row) + (row.groupTitle ? style.searchHeaderHeight : 0) + (row.separator ? 12 :
                                                                                                       0);
    }
    function navigationIndex(direction) {
        return LocalSearch.navigationIndex(rows, selectedIndex, direction);
    }

    Text {
        id: errorLabel
        width: parent.width
        height: visible ? 32 : 0
        visible: root.error !== ""
        text: root.error
        textFormat: Text.PlainText
        color: Appearance.colors.colError
        font.family: Fonts.ui
        font.pixelSize: 13
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
    }
    ListView {
        id: list
        anchors.top: errorLabel.bottom
        anchors.bottom: parent.bottom
        width: parent.width
        clip: true
        model: root.rows
        currentIndex: root.currentRow
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationEnabled: false
        interactive: !DockService.externalDragActive
        highlight: Item {}
        highlightMoveDuration: root.style.resultScrollDuration
        highlightMoveVelocity: -1
        cacheBuffer: 0
        ScrollBar.vertical: StyledScrollBar {}
        WheelScrollController {
            flickable: list
        }

        delegate: Item {
            id: row
            required property var modelData
            width: ListView.view.width
            height: root.rowHeight(modelData)
            Text {
                id: header
                x: 12
                width: parent.width - 24
                height: row.modelData.groupTitle ? root.style.searchHeaderHeight : 0
                visible: height > 0
                text: row.modelData.groupTitle
                textFormat: Text.PlainText
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            Item {
                id: separator
                y: header.height
                width: parent.width
                height: row.modelData.separator ? 12 : 0
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    x: 12
                    width: parent.width - 24
                    height: 1
                    color: Appearance.colors.colOutlineVariant
                    visible: parent.height > 0
                }
            }
            Row {
                y: header.height + separator.height
                width: parent.width
                height: root.contentHeight(row.modelData)
                Repeater {
                    model: row.modelData.cells
                    SpotlightSearchTile {
                        required property var modelData
                        width: row.width / (LocalSearch.horizontalGroup(row.modelData.kind)
                                            ? root.capacities[row.modelData.kind] : 1)
                        height: root.contentHeight(row.modelData)
                        style: root.style
                        result: modelData.result
                        kind: row.modelData.kind
                        selected: modelData.index === root.selectedIndex
                        onSelectionRequested: root.selectionRequested(modelData.index)
                        onActivationRequested: id => root.activationRequested(id)
                    }
                }
            }
        }
    }
}
