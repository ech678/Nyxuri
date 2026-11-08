// Fork & Trim: end4-pC modules/common/widgets/Visualizer.qml (GPL-3, see
// shell/LICENSE appendix end-4-dots-hyprland-GPL-3.0.txt). Trimmed for the
// tree: upstream pulled the player and cava points from its own singletons
// (`MprisController`, `GlobalStates`); here both are injected so the plain
// projection pool stays free of service reads. Sizes/colors go through
// Appearance instead of Config.options.
import QtQuick
import QtQuick.Layouts
import qs.commons

Item {
    id: root

    property bool vertical: false
    property bool isMaterial: false
    property bool mirrored: false
    property bool playing: false
    property list<real> points: []
    property int barCount: 20
    property real dotSize: 3
    property real dotSpacing: 3
    property real maxBarHeight: (vertical ? Sizes.verticalBarWidth : Sizes.barHeight) * 0.7
    property real maxVisualizerValue: 1000
    property color barColor: Appearance.colors.colPrimary

    implicitWidth: vertical ? Sizes.verticalBarWidth : (isMaterial ? barsRow.implicitWidth + 16 : barCount * (dotSize + dotSpacing))
    implicitHeight: vertical ? (isMaterial ? barsColumn.implicitHeight + 16 : barCount * (dotSize + dotSpacing)) : Sizes.barHeight

    transform: Scale {
        xScale: !root.vertical && root.mirrored ? -1 : 1
        origin.x: root.width / 2
    }

    Row {
        id: barsRow
        visible: !root.vertical
        anchors.centerIn: parent
        spacing: root.dotSpacing

        Repeater {
            model: root.barCount
            Rectangle {
                required property int index
                width: root.dotSize
                property real pointValue: {
                    if (!root.playing || root.points.length === 0)
                        return root.dotSize;
                    const idx = Math.floor(index * root.points.length / root.barCount);
                    const v = root.points[idx] ?? 0;
                    return Math.max(root.dotSize, (v / root.maxVisualizerValue) * root.maxBarHeight);
                }
                height: pointValue
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                color: root.barColor
                opacity: root.playing ? 0.85 : 0.3
                Behavior on height {
                    NumberAnimation {
                        duration: 80
                        easing.type: Easing.OutQuad
                    }
                }
                Behavior on opacity {
                    NumberAnimation {
                        duration: 300
                    }
                }
            }
        }
    }

    Column {
        id: barsColumn
        visible: root.vertical
        anchors.centerIn: parent
        spacing: root.dotSpacing

        Repeater {
            model: root.barCount
            Rectangle {
                required property int index
                height: root.dotSize
                property real pointValue: {
                    if (!root.playing || root.points.length === 0)
                        return root.dotSize;
                    const rawIndex = root.mirrored ? (root.barCount - 1 - index) : index;
                    const idx = Math.floor(rawIndex * root.points.length / root.barCount);
                    const v = root.points[idx] ?? 0;
                    return Math.max(root.dotSize, (v / root.maxVisualizerValue) * root.maxBarHeight);
                }
                width: pointValue
                radius: height / 2
                anchors.horizontalCenter: parent.horizontalCenter
                color: root.barColor
                opacity: root.playing ? 0.85 : 0.3
                Behavior on width {
                    NumberAnimation {
                        duration: 80
                        easing.type: Easing.OutQuad
                    }
                }
                Behavior on opacity {
                    NumberAnimation {
                        duration: 300
                    }
                }
            }
        }
    }
}
