import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.i18n

ColumnLayout {
    id: root

    property string iconName: "inbox"
    property string title: ""
    property string description: ""
    property string actionText: ""
    signal actionTriggered

    spacing: Metrics.spacingS
    Layout.alignment: Qt.AlignHCenter
    Accessible.role: Accessible.StaticText
    Accessible.name: root.title

    Rectangle {
        Layout.alignment: Qt.AlignHCenter
        implicitWidth: 56
        implicitHeight: 56
        radius: Appearance.rounding.full
        color: Appearance.colors.colLayer2
        MaterialSymbol {
            anchors.centerIn: parent
            text: root.iconName
            iconSize: 26
            color: Appearance.colors.colOnSurfaceVariant
        }
    }
    Text {
        Layout.alignment: Qt.AlignHCenter
        Layout.maximumWidth: 320
        text: root.title
        color: Appearance.colors.colOnSurface
        font.family: Fonts.ui
        font.pixelSize: Appearance.scaledFont(14)
        font.weight: Font.Medium
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
    }
    Text {
        Layout.alignment: Qt.AlignHCenter
        Layout.maximumWidth: 320
        visible: root.description !== ""
        text: root.description
        color: Appearance.colors.colOnSurfaceVariant
        font.family: Fonts.ui
        font.pixelSize: Appearance.scaledFont(12)
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
    }
    Item {
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: actionButton.implicitWidth
        Layout.preferredHeight: actionButton.implicitHeight
        visible: root.actionText !== ""
        ActionButton {
            id: actionButton
            filled: false
            text: root.actionText
            onClicked: root.actionTriggered()
        }
    }
}
