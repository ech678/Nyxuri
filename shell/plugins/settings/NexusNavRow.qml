import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.commons.i18n
import qs.ui

// Two-line navigation row (Caelestia Nexus NavLocations item): circular
// accent icon badge, body-medium label, label-small description. The active
// row fills with the secondary container and morphs into a full-height pill
// (extraLargeIncreased); pressing any row collapses its corners to `medium`
// for the MD3 shape response. Text keeps its resting colours in every state.
ConnectedRect {
    id: root

    property bool active: false
    property string title: ""
    property string description: ""
    property string icon: ""

    signal activated

    Layout.fillWidth: true
    implicitHeight: rowContent.implicitHeight + NexusStyle.padding.large * 2

    color: root.active ? Appearance.m3colors.m3secondaryContainer : Appearance.colors.colSurfaceContainerHigh
    uniformRadius: rowPress.pressed ? NexusStyle.rounding.medium : root.active
                                      ? NexusStyle.rounding.extraLargeIncreased : -1

    Behavior on color {
        ColorAnimation {
            duration: Appearance.animation.expressiveEffects.duration
            easing.type: Appearance.animation.expressiveEffects.type
            easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
        }
    }

    StateLayer {
        anchors.fill: parent
        layerRadius: root.uniformRadius >= 0 ? root.uniformRadius : (root.first || root.last)
                                               ? NexusStyle.rounding.extraLarge :
                                                 NexusStyle.rounding.extraSmall
        color: Appearance.m3colors.m3onSurface
        hovered: rowPress.containsMouse
        pressed: rowPress.pressed
    }

    MouseArea {
        id: rowPress

        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.activated()
    }

    RowLayout {
        id: rowContent

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.large
        anchors.rightMargin: NexusStyle.padding.large
        spacing: NexusStyle.spacing.medium

        Rectangle {
            id: badge

            Layout.fillHeight: true
            Layout.topMargin: -1
            Layout.bottomMargin: -1
            implicitWidth: height
            radius: NexusStyle.rounding.full
            color: root.active ? Appearance.m3colors.m3primary : Appearance.m3colors.m3secondaryContainer

            Behavior on color {
                ColorAnimation {
                    duration: Appearance.animation.expressiveEffects.duration
                    easing.type: Appearance.animation.expressiveEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                }
            }

            MaterialSymbol {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: 1
                iconSize: NexusStyle.icon.medium
                fill: 1
                grade: 25
                text: root.icon
                color: root.active ? Appearance.m3colors.m3onPrimary :
                                     Appearance.m3colors.m3onSecondaryContainer

                Behavior on color {
                    ColorAnimation {
                        duration: Appearance.animation.expressiveEffects.duration
                        easing.type: Appearance.animation.expressiveEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            StyledText {
                Layout.fillWidth: true
                text: root.title
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
                elide: Text.ElideRight
            }

            StyledText {
                Layout.fillWidth: true
                visible: text.length > 0
                text: root.description
                color: Appearance.m3colors.m3onSurfaceVariant
                font.pixelSize: NexusStyle.font.labelSmall
                elide: Text.ElideRight
            }
        }
    }
}
