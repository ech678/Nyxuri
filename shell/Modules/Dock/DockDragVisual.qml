import QtQuick
import qs.Common
import qs.Components
import qs.Services
import "../../Common/functions/DockMotion.js" as DockMotion

// This snapshot outlives the model row. The pointer owns its position during
// a drag; only the short release/return transition interpolates that position.
Item {
    id: root

    property var entry: null
    property bool following: false
    property bool removalArmed: false
    property real fade: 1
    property real removalProgress: removalArmed ? 1 : 0
    property point destination
    property real destinationSize: 48
    readonly property bool active: entry !== null
    readonly property bool settling: landing.running

    visible: active
    height: width
    opacity: fade * (1 - removalProgress * 0.35)
    transformOrigin: Item.Center
    scale: DockMotion.iconScale(fade)

    function begin(value, center, size) {
        landing.stop();
        removal.stop();
        root.entry = value;
        root.width = size;
        root.fade = 1;
        root.removalArmed = false;
        root.following = true;
        root.follow(center);
    }
    function follow(center) {
        root.x = center.x - root.width / 2;
        root.y = center.y - root.height / 2;
    }
    function land(center, size) {
        root.destination = center;
        root.destinationSize = size;
        root.removalArmed = false;
        root.following = false;
        landing.restart();
    }
    function remove() {
        root.following = false;
        removal.restart();
    }
    function clear() {
        landing.stop();
        removal.stop();
        root.entry = null;
        root.following = false;
        root.removalArmed = false;
    }

    Behavior on removalProgress {
        NumberAnimation {
            duration: 100
            easing.type: Easing.OutCubic
        }
    }
    ParallelAnimation {
        id: landing
        NumberAnimation {
            target: root
            property: "x"
            to: root.destination.x - root.destinationSize / 2
            duration: DockMotion.reflowDuration
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: root
            property: "y"
            to: root.destination.y - root.destinationSize / 2
            duration: DockMotion.reflowDuration
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: root
            property: "width"
            to: root.destinationSize
            duration: DockMotion.reflowDuration
            easing.type: Easing.OutCubic
        }
        onFinished: root.clear()
    }
    SequentialAnimation {
        id: removal
        NumberAnimation {
            target: root
            property: "fade"
            to: 0
            duration: DockMotion.exitDuration
            easing.type: Easing.OutCubic
        }
        onFinished: root.clear()
    }

    ThemeIcon {
        anchors.fill: parent
        visible: !!root.entry && root.entry.kind === "app" && !root.entry.symbol
        iconSource: visible ? ApplicationService.iconSource(root.entry.icon) : ""
        sourceSize: Qt.size(160, 160)
        fillMode: Image.PreserveAspectFit
    }
    DockFileIcon {
        anchors.fill: parent
        visible: !!root.entry && (root.entry.kind === "file" || root.entry.kind === "folder")
        info: ({
                   url: root.entry ? root.entry.url : "",
                   icon: root.entry ? root.entry.icon : "",
                   isDirectory: !!root.entry && root.entry.kind === "folder"
               })
    }
    MaterialSymbol {
        anchors.centerIn: parent
        visible: !!root.entry && root.entry.kind === "app" && !!root.entry.symbol
        text: root.entry ? root.entry.symbol : ""
        iconSize: root.width * 0.82
        color: Appearance.colors.colPrimary
    }
    Rectangle {
        anchors.centerIn: parent
        width: parent.width * (root.entry && root.entry.kind === "small-spacer" ? 0.5 : 1)
        height: parent.height
        visible: !!root.entry && (root.entry.kind === "spacer" || root.entry.kind === "small-spacer")
        radius: width * 0.2
        color: "transparent"
        border.width: 1
        border.color: Appearance.applyAlpha(Appearance.colors.colOnSurface, 0.4)
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.bottom
        anchors.topMargin: 8
        width: label.implicitWidth + 16
        height: 26
        radius: 13
        opacity: root.following ? root.removalProgress : 0
        visible: opacity > 0
        color: Appearance.colors.colSurfaceContainerHigh
        Text {
            id: label
            anchors.centerIn: parent
            text: qsTranslate("DockSurface", "Remove from Dock")
            font.family: Fonts.ui
            font.pixelSize: 12
            color: Appearance.colors.colOnSurface
        }
    }
}
