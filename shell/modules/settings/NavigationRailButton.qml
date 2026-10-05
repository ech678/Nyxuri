import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

TabButton {
    id: root

    property bool active: false
    property bool toggled: root.active
    property string iconName: "settings"
    property string label: ""
    property string buttonIcon: root.iconName
    property real buttonIconRotation: 0
    property string buttonText: root.label
    property bool expanded: false
    property bool showToggledHighlight: true
    readonly property real visualWidth: root.expanded ? root.baseSize + 20 + itemText.implicitWidth : root.baseSize

    property real baseSize: 56
    property real baseHighlightHeight: 32
    property real iconSize: root.baseSize >= 50 ? 24 : (root.baseSize >= 40 ? 22 : 20)
    property real fontPixelSize: root.baseSize >= 50 ? 14 : (root.baseSize >= 40 ? 13 : 12)

    Layout.fillWidth: true
    implicitHeight: baseSize
    padding: 0
    background: null

    StyledToolTip {
        text: root.buttonText
        extraVisibleCondition: !root.expanded && root.hovered && root.buttonText.length > 0
    }

    contentItem: Item {
        id: buttonContent

        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        implicitWidth: root.visualWidth
        implicitHeight: root.baseSize

        Rectangle {
            id: itemBackground

            anchors.top: root.expanded ? buttonContent.top : itemIconBackground.top
            anchors.left: root.expanded ? buttonContent.left : itemIconBackground.left
            anchors.bottom: root.expanded ? buttonContent.bottom : itemIconBackground.bottom
            implicitWidth: root.visualWidth
            radius: Appearance.rounding.full
            color: root.toggled
                ? root.showToggledHighlight
                    ? (root.down ? Appearance.colors.colSecondaryContainerActive : root.hovered ? Appearance.colors.colSecondaryContainerHover : Appearance.colors.colSecondaryContainer)
                    : Appearance.transparentize(Appearance.colors.colSecondaryContainer, 1)
                : (root.down ? Appearance.colors.colLayer1Active : root.hovered ? Appearance.colors.colLayer1Hover : Appearance.transparentize(Appearance.colors.colLayer1Hover, 1))

            Behavior on implicitWidth {
                NumberAnimation {
                    duration: Appearance.animation.expressiveDefaultSpatial.duration
                    easing.type: Appearance.animation.expressiveDefaultSpatial.type
                    easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                }
            }

            Behavior on color {
                ColorAnimation {
                    duration: Appearance.animation.expressiveEffects.duration
                    easing.type: Appearance.animation.expressiveEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                }
            }
        }

        Item {
            id: itemIconBackground

            implicitWidth: root.baseSize
            implicitHeight: root.baseHighlightHeight
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter

            MaterialSymbol {
                anchors.centerIn: parent
                rotation: root.buttonIconRotation
                iconSize: root.iconSize
                fill: root.toggled ? 1 : 0
                text: root.buttonIcon
                color: root.toggled ? Appearance.m3colors.m3onSecondaryContainer : Appearance.colors.colOnLayer1

                Behavior on color {
                    ColorAnimation {
                        duration: Appearance.animation.expressiveEffects.duration
                        easing.type: Appearance.animation.expressiveEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                    }
                }
            }
        }

        Text {
            id: itemText

            anchors.left: itemIconBackground.right
            anchors.leftMargin: 8
            anchors.right: buttonContent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: itemIconBackground.verticalCenter
            visible: root.expanded
            opacity: root.expanded ? 1 : 0
            text: root.buttonText
            color: root.toggled ? Appearance.m3colors.m3onSecondaryContainer : Appearance.colors.colOnLayer1
            font.family: Fonts.ui
            font.pixelSize: root.fontPixelSize
            font.weight: root.toggled ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter

            Behavior on opacity {
                NumberAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                }
            }

            Behavior on color {
                ColorAnimation {
                    duration: Appearance.animation.expressiveEffects.duration
                    easing.type: Appearance.animation.expressiveEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                }
            }
        }
    }
}
