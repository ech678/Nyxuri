import QtQuick
import Quickshell
import qs.Common
import qs.shared.controls

Item {
    id: root
    required property var player
    readonly property var desktopEntry: {
        if (!player)
            return null;
        return DesktopEntries.heuristicLookup(player.desktopEntry || "") || DesktopEntries.heuristicLookup(
                    player.identity || "");
    }
    implicitWidth: 24
    implicitHeight: 24

    ThemeIcon {
        id: appIcon
        anchors.fill: parent
        iconSource: root.desktopEntry && root.desktopEntry.icon ? Quickshell.iconPath(root.desktopEntry.icon,
                                                                                      true) : ""
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
