import QtQuick
import qs.Common
import qs.Services

Item {
    id: root

    property int textFormat: Text.AutoText
    required property string text
    property bool shown: false
    property real horizontalPadding: 10
    property real verticalPadding: 5
    property alias font: tooltipText.font
    readonly property alias blurBackgroundItem: backgroundRectangle
    readonly property QtObject revealAnimation: Appearance.animation.expressiveEffects

    implicitWidth: tooltipText.implicitWidth + root.horizontalPadding * 2
    implicitHeight: tooltipText.implicitHeight + root.verticalPadding * 2
    width: implicitWidth
    height: implicitHeight

    readonly property bool isVisible: backgroundRectangle.height > 0

    Rectangle {
        id: backgroundRectangle

        anchors {
            bottom: root.bottom
            horizontalCenter: root.horizontalCenter
        }

        color: BlurService.backgroundColor(Appearance.colors.colTooltip)
        radius: 8
        opacity: root.shown ? 1 : 0
        width: root.shown ? root.implicitWidth : 0
        height: root.shown ? root.implicitHeight : 0
        clip: true

        Behavior on width {
            NumberAnimation {
                alwaysRunToEnd: true
                duration: root.revealAnimation.duration
                easing.type: root.revealAnimation.type
                easing.bezierCurve: root.revealAnimation.bezierCurve
            }
        }

        Behavior on height {
            NumberAnimation {
                alwaysRunToEnd: true
                duration: root.revealAnimation.duration
                easing.type: root.revealAnimation.type
                easing.bezierCurve: root.revealAnimation.bezierCurve
            }
        }

        Behavior on opacity {
            NumberAnimation {
                alwaysRunToEnd: true
                duration: root.revealAnimation.duration
                easing.type: root.revealAnimation.type
                easing.bezierCurve: root.revealAnimation.bezierCurve
            }
        }

        Text {
            id: tooltipText

            anchors.centerIn: parent
            text: root.text
            textFormat: root.textFormat
            color: Appearance.colors.colOnTooltip
            wrapMode: Text.Wrap
            font.family: Fonts.ui
            font.pixelSize: 12
            font.hintingPreference: Font.PreferNoHinting
        }
    }
}
