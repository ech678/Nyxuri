import QtQuick
import qs.shared.theme

ActionButton {
    id: root

    property bool vertical: false
    property bool expandedContent: true

    // Compact icon controls keep a 28px slot. Text and grouped content use
    // 10px of padding along the bar's main axis.
    leftPadding: !vertical && expandedContent ? (Metrics.spacingM - Metrics.spacingXXS) : 0
    rightPadding: leftPadding
    topPadding: vertical && expandedContent ? (Metrics.spacingM - Metrics.spacingXXS) : 0
    bottomPadding: topPadding
    implicitWidth: Math.max(Sizes.barControlCircleSize, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(Sizes.barControlCircleSize, implicitContentHeight + topPadding + bottomPadding)
}
