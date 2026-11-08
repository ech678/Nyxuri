import QtQuick
import qs.commons
import qs.services
import qs.ui
import "./ShortcutKeySymbols.js" as KeySymbols

Rectangle {
    id: root

    property string keyText: ""
    property string superStyle: PersonalizationConfig.superKeyStyle
    readonly property bool superKey: ["super", "win"].indexOf(keyText.toLowerCase()) !== -1
    readonly property string symbol: KeySymbols.forKey(keyText)

    implicitWidth: Math.max(30, symbol.length > 0 ? 32 : label.implicitWidth + 14)
    implicitHeight: 32
    radius: 5
    color: Appearance.colors.colOnSurface
    Accessible.role: Accessible.StaticText
    Accessible.name: superKey ? "Super" : keyText

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 1
        anchors.leftMargin: 1
        anchors.rightMargin: 1
        anchors.bottomMargin: 3
        radius: 4
        color: Appearance.m3colors.m3surfaceContainerLow

        Text {
            id: label
            anchors.centerIn: parent
            visible: root.symbol.length === 0
            text: root.superKey ? (root.superStyle === "command" ? "⌘" : "Super") : root.keyText
            font.family: Fonts.mono
            font.pixelSize: 16
            color: Appearance.colors.colOnSurface
        }

        MaterialSymbol {
            anchors.centerIn: parent
            visible: root.symbol.length > 0
            text: root.symbol
            iconSize: 20
            color: Appearance.colors.colOnSurface
        }
    }
}
