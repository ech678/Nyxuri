import QtQuick
import QtQuick.Controls
import qs.Common

Slider {
    id: root

    from: 0
    to: 1
    enabled: false
    opacity: 1
    focusPolicy: Qt.NoFocus
    implicitHeight: 14

    background: Item {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        implicitWidth: 200
        implicitHeight: 8
        width: root.availableWidth
        height: implicitHeight
        readonly property real splitPosition:
            root.visualPosition * width
        readonly property real trackGap: 4
        readonly property real activeEnd: splitPosition <= 0
            ? 0
            : splitPosition >= width
              ? width
              : Math.max(2, splitPosition - trackGap / 2)
        readonly property real inactiveStart: splitPosition <= 0
            ? 0
            : splitPosition >= width
              ? width
              : Math.min(width - 2, splitPosition + trackGap / 2)

        Rectangle {
            x: parent.inactiveStart
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(0, parent.width - x)
            height: 2
            radius: Appearance.rounding.full
            color: Appearance.colors.colOutlineVariant
        }

        Rectangle {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: parent.activeEnd
            height: 4
            radius: Appearance.rounding.full
            color: Appearance.colors.colPrimary
        }
    }

    handle: Item {}
}
