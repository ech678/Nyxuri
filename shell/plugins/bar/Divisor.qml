// Fork & Trim: end4-pC modules/ii/bar/Divisor.qml (GPL-3, see
// shell/LICENSE appendix end-4-dots-hyprland-GPL-3.0.txt). B4 reskin promotes
// this component to plugins/bar/.
import QtQuick
import qs.commons
import qs.services
import qs.ui

Item {
    id: root

    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool vertical: false
    property real btnSize: 32
    property real btnSpacing: 2
    readonly property bool isMaterial: PersonalizationConfig.barCornerStyle === 3 || PersonalizationConfig.barCornerStyle === 4
    property string style: PersonalizationConfig.barDividerStyle
    property int dividerSpacing: 10

    width: vertical ? btnSize : (root.style === "space" ? root.dividerSpacing : root.style === "dot" ? dotText.implicitWidth + 10 : (1 + btnSpacing * 3))
    height: vertical ? (root.style === "space" ? root.dividerSpacing : root.style === "dot" ? dotText.implicitHeight - 4 : (1 + btnSpacing * 3)) : btnSize

    Rectangle {
        visible: root.style === "rect"
        anchors.centerIn: parent
        width: root.vertical ? Math.round(root.btnSize * 0.6) : 1
        height: root.vertical ? 1 : Math.round(root.btnSize * 0.6)
        color: root.isMaterial ? Appearance.colors.colPrimary : (root.contentColorOverridden ? Appearance.applyAlpha(root.contentColor, 0.4) : Appearance.colors.colOutlineVariant)
    }

    StyledText {
        id: dotText

        visible: root.style === "dot"
        anchors.centerIn: parent
        text: "• "
        color: root.isMaterial ? Appearance.colors.colPrimary : root.contentColor
        font.pixelSize: 13
    }
}
