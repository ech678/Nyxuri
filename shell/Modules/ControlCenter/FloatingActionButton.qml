import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components
import qs.Widgets.common

RippleButton {
    id: root

    property string iconText: "add"
    property bool expanded: false
    property real baseSize: 56
    property real elementSpacing: 5
    property color baseColor: Appearance.colors.colPrimaryContainer
    property color hoverStateColor: Appearance.colors.colPrimaryContainerHover
    property color pressedStateColor: Appearance.colors.colPrimaryContainerActive
    property color contentColor: Appearance.colors.colOnPrimaryContainer

    signal altClicked()

    Layout.alignment: Qt.AlignLeft
    implicitWidth: root.expanded ? Math.max(contentRow.implicitWidth + 20, root.baseSize) : root.baseSize
    implicitHeight: root.baseSize
    buttonRadius: root.baseSize / 14 * 4
    buttonRadiusPressed: root.buttonRadius
    containerColor: root.baseColor
    rippleColor: root.contentColor
    stateLayerColor: root.hoverStateColor
    hoverStateLayerColor: root.hoverStateColor
    focusStateLayerColor: root.hoverStateColor
    pressedStateLayerColor: root.pressedStateColor
    stateLayerOpacity: 1
    focusStateLayerOpacity: 1
    pressedStateLayerOpacity: 1
    altAction: () => {
        return root.altClicked();
    }

    Behavior on implicitWidth {
        NumberAnimation {
            duration: Appearance.animation.elementMoveFast.duration
            easing.type: Appearance.animation.elementMoveFast.type
            easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
        }

    }

    contentItem: Row {
        id: contentRow

        property real horizontalMargins: (root.baseSize - icon.width) / 2

        anchors.left: parent.left
        anchors.leftMargin: horizontalMargins
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0

        MaterialSymbol {
            id: icon

            anchors.verticalCenter: parent.verticalCenter
            iconSize: 26
            color: root.contentColor
            text: root.iconText
        }

        Item {
            anchors.verticalCenter: parent.verticalCenter
            width: root.expanded ? buttonText.implicitWidth + root.elementSpacing + contentRow.horizontalMargins : 0
            height: parent.height
            clip: true

            Text {
                id: buttonText

                anchors.left: parent.left
                anchors.leftMargin: root.elementSpacing
                anchors.verticalCenter: parent.verticalCenter
                text: root.buttonText
                color: root.contentColor
                font.family: Fonts.ui
                font.pixelSize: 14
                font.weight: Font.Medium
            }

            Behavior on width {
                NumberAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                }

            }

        }

    }

}
