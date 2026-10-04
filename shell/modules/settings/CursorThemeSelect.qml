import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    property var cursorThemes: []
    property string currentCursorTheme: ""
    property int fieldWidth: 240

    signal accepted(string value)

    Layout.fillWidth: true
    Layout.preferredHeight: 58

    RowLayout {
        anchors.fill: parent
        spacing: 16

        Text {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            text: I18n.tr("Cursor theme")
            color: Appearance.colors.colOnSurface
            font.family: Fonts.ui
            font.pixelSize: 15
            font.weight: Font.Medium
            elide: Text.ElideRight
        }

        SearchSelectMenuField {
            closeOnAccept: false
            Layout.preferredWidth: root.fieldWidth
            Layout.preferredHeight: 40
            Layout.alignment: Qt.AlignVCenter
            options: root.cursorThemes
            value: root.currentCursorTheme
            placeholder: I18n.tr("Choose cursor theme")
            textRole: "label"
            valueRole: "value"
            onAccepted: value => root.accepted(value)
        }
    }
}
