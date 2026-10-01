import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Common
import qs.Components

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

    Layout.fillWidth: true
    implicitHeight: baseSize
    padding: 0
    background: null

    contentItem: Item {
        id: buttonContent

        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: parent.left

        implicitWidth: root.visualWidth
        implicitHeight: root.expanded ? itemIconBackground.implicitHeight : itemIconBackground.implicitHeight + itemText.implicitHeight

        Rectangle {
            id: itemBackground

            anchors.top: itemIconBackground.top
            anchors.left: itemIconBackground.left
            anchors.bottom: itemIconBackground.bottom
            implicitWidth: root.visualWidth
            radius: Appearance.rounding.full
            color: root.toggled
                ? root.showToggledHighlight
                    ? (root.down ? Appearance.colors.colSecondaryContainerActive : root.hovered ? Appearance.colors.colSecondaryContainerHover : Appearance.colors.colSecondaryContainer)
                    : Appearance.transparentize(Appearance.colors.colSecondaryContainer, 1)
                : (root.down ? Appearance.colors.colLayer1Active : root.hovered ? Appearance.colors.colLayer1Hover : Appearance.transparentize(Appearance.colors.colLayer1Hover, 1))

            states: State {
                name: "expanded"
                when: root.expanded

                AnchorChanges {
                    target: itemBackground
                    anchors.top: buttonContent.top
                    anchors.left: buttonContent.left
                    anchors.bottom: buttonContent.bottom
                }

                PropertyChanges {
                    target: itemBackground
                    implicitWidth: root.visualWidth
                }
            }

            transitions: Transition {
                AnchorAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                }

                NumberAnimation {
                    property: "implicitWidth"
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
                iconSize: 24
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

            anchors.top: itemIconBackground.bottom
            anchors.topMargin: 2
            anchors.horizontalCenter: itemIconBackground.horizontalCenter
            text: root.buttonText
            color: root.toggled ? Appearance.m3colors.m3onSecondaryContainer : Appearance.colors.colOnLayer1
            font.family: Fonts.ui
            font.pixelSize: 14
            verticalAlignment: Text.AlignVCenter

            states: State {
                name: "expanded"
                when: root.expanded

                AnchorChanges {
                    target: itemText
                    anchors.top: undefined
                    anchors.horizontalCenter: undefined
                    anchors.left: itemIconBackground.right
                    anchors.verticalCenter: itemIconBackground.verticalCenter
                }
            }

            transitions: Transition {
                AnchorAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
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
