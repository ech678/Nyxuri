import QtQuick
import qs.shared.theme
import qs.shared.controls

Item {
    id: root
    property url iconSource: ""
    implicitWidth: 24
    implicitHeight: 24

    ThemeIcon {
        id: appIcon
        anchors.fill: parent
        iconSource: root.iconSource
        fillMode: Image.PreserveAspectFit
        sourceSize: Qt.size(width * 2, height * 2)
        visible: status === Image.Ready
    }
    MaterialSymbol {
        anchors.centerIn: parent
        visible: appIcon.status !== Image.Ready
        text: "music_note"
        iconSize: Math.min(root.width, root.height)
        color: Appearance.colors.colPrimary
    }
}
