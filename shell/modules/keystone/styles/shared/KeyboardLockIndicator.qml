import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    property bool vertical: false
    property bool capsLock: true
    property bool lockEnabled: false
    readonly property string label: capsLock ? I18n.tr("Caps Lock") : I18n.tr("Num Lock")
    readonly property string stateLabel: lockEnabled ? I18n.tr("On") : I18n.tr("Off")

    Accessible.role: Accessible.StaticText
    Accessible.name: I18n.tr("%1: %2").arg(label).arg(stateLabel)

    GridLayout {
        anchors.centerIn: parent
        columns: root.vertical ? 1 : 3
        rowSpacing: 8
        columnSpacing: 14

        MaterialSymbol {
            Layout.alignment: Qt.AlignCenter
            text: root.capsLock ? "keyboard_capslock" : "pin"
            iconSize: 24
            color: root.lockEnabled ? Appearance.colors.colPrimary : Appearance.colors.colOnLayer0
        }

        Text {
            Layout.alignment: Qt.AlignCenter
            text: root.label
            font.family: Fonts.ui
            font.pixelSize: 14
            font.weight: Font.Medium
            color: Appearance.colors.colOnLayer0
        }

        Text {
            Layout.alignment: Qt.AlignCenter
            text: root.stateLabel
            font.family: Fonts.ui
            font.pixelSize: 14
            font.weight: Font.DemiBold
            color: root.lockEnabled ? Appearance.colors.colPrimary : Appearance.colors.colOnLayer0
        }
    }
}
