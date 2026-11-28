// Fork & Trim: end4-pC modules/common/widgets/BarWidgetSwitcherArea.qml
// SPDX-License-Identifier: GPL-3.0-or-later
// Local baseline: pctrade/end4-pC b881970bfc25ff92b0f72b751c810a178c5fc677.

import qs.commons
import qs.services
import QtQuick
import QtQuick.Layouts
import "BarStyle.js" as BarStyle

MouseArea {
    id: root
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    property bool vertical: root.barAxes.position === "left" || root.barAxes.position === "right"
    property bool isMaterial: BarStyle.isTinted(root.barAxes)
    property real horizontalExtraPadding: 12

    property Component colDefault
    property Component colMaterial
    property Component rowDefault
    property Component rowMaterial

    implicitWidth: root.vertical ? PersonalizationConfig.resolvedVerticalBarWidth(root.barAxes) : (rowLoader.item?.implicitWidth ?? 0) + (root.isMaterial ? 0 : root.horizontalExtraPadding)
    implicitHeight: root.vertical ? (colLoader.item?.implicitHeight ?? 0) : PersonalizationConfig.resolvedBarHeight(root.barAxes)

    Loader {
        id: colLoader
        active: root.vertical
        visible: active
        anchors.centerIn: parent
        sourceComponent: root.isMaterial ? root.colMaterial : root.colDefault
    }

    Loader {
        id: rowLoader
        active: !root.vertical
        visible: active
        anchors.centerIn: parent
        sourceComponent: root.isMaterial ? root.rowMaterial : root.rowDefault
    }
}
