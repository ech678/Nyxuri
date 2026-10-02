import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls

TopBarPill {
    id: root

    property bool vertical: false

    implicitHeight: vertical ? layout.implicitHeight + 2 * Sizes.barPillHorizontalPadding : Sizes.barPillThickness
    implicitWidth: vertical ? Sizes.barPillThickness : layout.implicitWidth + 2 * Sizes.barPillHorizontalPadding

    readonly property string timeString: (Time.hours || "00") + ":" + (Time.minutes || "00")
    readonly property string dateString: (Time.month || "") + " " + (Time.day || "")

    RowLayout {
        id: layout
        anchors.centerIn: parent
        spacing: 6

        Text {
            text: root.timeString
            font.family: Fonts.numeric
            font.pixelSize: 13
            font.bold: true
            color: Appearance.colors.colOnSurface
            Layout.alignment: Qt.AlignCenter
        }
    }

    PopupToolTip {
        extraVisibleCondition: mouseArea.containsMouse
        text: root.dateString
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
    }
}
