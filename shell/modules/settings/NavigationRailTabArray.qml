import QtQuick
import QtQuick.Layouts
import qs.Common

Item {
    id: root

    property int currentIndex: 0
    property bool expanded: false
    default property alias tabData: tabBarColumn.data

    implicitHeight: tabBarColumn.implicitHeight
    implicitWidth: tabBarColumn.implicitWidth
    Layout.topMargin: 25

    function tabItem(index) {
        if (index < 0 || index >= tabBarColumn.children.length)
            return null;
        return tabBarColumn.children[index];
    }

    Rectangle {
        id: activeIndicator

        property var firstItem: root.tabItem(0)
        property var currentItem: root.tabItem(root.currentIndex)
        property real itemHeight: firstItem && firstItem.baseSize !== undefined ? firstItem.baseSize : 56
        property real baseHighlightHeight: firstItem && firstItem.baseHighlightHeight !== undefined ? firstItem.baseHighlightHeight : 32

        anchors.top: tabBarColumn.top
        anchors.left: tabBarColumn.left
        anchors.topMargin: activeIndicator.itemHeight * root.currentIndex + (root.expanded ? 0 : ((activeIndicator.itemHeight - activeIndicator.baseHighlightHeight) / 2))
        radius: Appearance.rounding.full
        color: Appearance.colors.colSecondaryContainer
        implicitHeight: root.expanded ? activeIndicator.itemHeight : activeIndicator.baseHighlightHeight
        implicitWidth: currentItem && currentItem.visualWidth !== undefined ? currentItem.visualWidth : 56

        Behavior on anchors.topMargin {
            NumberAnimation {
                duration: Appearance.animation.expressiveFastSpatial.duration
                easing.type: Appearance.animation.expressiveFastSpatial.type
                easing.bezierCurve: Appearance.animation.expressiveFastSpatial.bezierCurve
            }
        }

        Behavior on implicitHeight {
            NumberAnimation {
                duration: Appearance.animation.elementMoveFast.duration
                easing.type: Appearance.animation.elementMoveFast.type
                easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
            }
        }

        Behavior on implicitWidth {
            NumberAnimation {
                duration: Appearance.animation.elementMoveFast.duration
                easing.type: Appearance.animation.elementMoveFast.type
                easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
            }
        }
    }

    ColumnLayout {
        id: tabBarColumn

        anchors.fill: parent
        spacing: 0
    }
}
