import QtQuick
import M3Shapes
import qs.Common

Item {
    id: root

    property bool month: false
    property int day: 1
    property int monthNumber: 1
    property real targetSize: 64

    width: root.targetSize
    height: width

    MaterialShape {
        anchors.centerIn: parent
        implicitSize: root.targetSize
        shape: root.month ? MaterialShape.Pill : MaterialShape.Pentagon
        color: root.month ? Appearance.colors.colSecondaryContainer : Appearance.colors.colTertiaryContainer
    }

    Text {
        anchors.centerIn: parent
        text: root.month ? String(root.monthNumber).padStart(2, "0") : root.day
        color: root.month ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnTertiaryContainer
        font.family: Fonts.expressive
        font.pixelSize: 30
        font.weight: Font.Black
    }

}
