import QtQuick
import qs.Common

Column {
    id: root

    property int hour24: 0
    property int minute: 0
    property bool useTwelveHourClock: true
    property bool hourMarksEnabled: false
    property color color: "transparent"
    readonly property int hour12: ((root.hour24 + 11) % 12) + 1
    readonly property var values: root.useTwelveHourClock ? [String(root.hour12).padStart(2, "0"), String(root.minute).padStart(2, "0"), root.hour24 >= 12 ? "PM" : "AM"] : [String(root.hour24).padStart(2, "0"), String(root.minute).padStart(2, "0")]

    spacing: -16

    Repeater {
        model: root.values

        delegate: Text {
            required property int index
            required property var modelData
            readonly property bool period: index >= 2
            readonly property real targetSize: root.hourMarksEnabled ? (period ? 20 : 40) : (period ? 26 : 68)

            anchors.horizontalCenter: parent.horizontalCenter
            text: modelData
            color: root.color
            font.family: Fonts.expressive
            font.pixelSize: targetSize
            font.weight: Font.Bold

            Behavior on font.pixelSize {
                NumberAnimation {
                    duration: Appearance.animation.standardSmall.duration
                    easing.type: Appearance.animation.standardSmall.type
                    easing.bezierCurve: Appearance.animation.standardSmall.bezierCurve
                }

            }

        }

    }

}
