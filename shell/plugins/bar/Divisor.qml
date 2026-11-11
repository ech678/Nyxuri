// Fork & Trim: end4-pC modules/ii/bar/Divisor.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import qs.commons
import qs.ui
import qs.services

Item {
    id: root
    property bool vertical: Config.options.bar.vertical
    property real btnSize: 40
    property real btnSpacing: 2
    property bool isMaterial: Config.options.bar.m3.cornerStyle === 3
    property string style: PersonalizationConfig.barDividerStyle ?? Config.options.bar.m3.divider.style // "rect" - "dot" - "space"
    property int dividerSpacing: Config.options.bar.m3.divider.spacing

    width:  vertical ? btnSize : (root.style === "space" ? root.dividerSpacing : (1 + btnSpacing * 3))
    height: vertical ? (root.style === "space" ? root.dividerSpacing : (1 + btnSpacing * 3)) : btnSize

    Rectangle {
        visible: root.style === "rect"
        anchors.centerIn: parent
        width:  vertical ? Math.round(btnSize * 0.6) : 1
        height: vertical ? 1 : Math.round(btnSize * 0.6)
        color: isMaterial ? Appearance.colors.colPrimary : Appearance.colors.colOutlineVariant
    }

    StyledText {
        visible: root.style === "dot"
        anchors.centerIn: parent
        text: "•"
        color: isMaterial ? Appearance.colors.colPrimary : Appearance.colors.colOnLayer0
        font.pixelSize: Appearance.font.pixelSize.normal
    }
}
