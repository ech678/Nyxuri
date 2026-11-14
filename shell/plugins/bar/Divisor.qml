// Fork & Trim: end4-pC modules/ii/bar/Divisor.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// B9.6: contentColor/contentColorOverridden restored (BarGroup's style
// editor drives them) and the dot-style width branch back per end4.

import QtQuick
import qs.commons
import qs.services

Item {
    id: root
    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool vertical: Config.options.bar.vertical
    property real btnSize: 40
    property real btnSpacing: 2
    property bool isMaterial: PersonalizationConfig.barIsMaterial
    property string style: PersonalizationConfig.barDividerStyle ?? Config.options.bar.m3.divider.style // "rect" - "dot" - "space"
    property int dividerSpacing: Config.options.bar.m3.divider.spacing

    width: vertical ? btnSize : (root.style === "space" ? root.dividerSpacing : root.style === "dot" ? dotText.implicitWidth + 10 : (1 + btnSpacing * 3))
    height: vertical ? (root.style === "space" ? root.dividerSpacing : root.style === "dot" ? dotText.implicitHeight - 4 : (1 + btnSpacing * 3)) : btnSize

    Rectangle {
        visible: root.style === "rect"
        anchors.centerIn: parent
        width: vertical ? Math.round(btnSize * 0.6) : 1
        height: vertical ? 1 : Math.round(btnSize * 0.6)
        color: isMaterial ? Appearance.colors.colPrimary : (root.contentColorOverridden ? Qt.alpha(root.contentColor, 0.4) : Appearance.colors.colOutlineVariant)
    }

    StyledText {
        id: dotText
        visible: root.style === "dot"
        anchors.centerIn: parent
        text: "• "
        color: isMaterial ? Appearance.colors.colPrimary : root.contentColor
        font.pixelSize: Appearance.font.pixelSize.normal
    }
}
