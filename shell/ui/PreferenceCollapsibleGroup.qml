import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Collapsible preference section (for Advanced / optional groups). Uses an
// explicit height-clipped host rather than flipping ColumnLayout child
// visibility directly, keeping width layout stable on expand.
ColumnLayout {
    id: root

    property string title: ""
    property string subtitle: ""
    property string icon: "tune"
    property bool expanded: false
    property bool first: false
    default property alias content: innerGroup.data

    Layout.fillWidth: true
    Layout.topMargin: root.first ? 0 : NexusStyle.padding.medium - ((parent as ColumnLayout)?.spacing ?? 0)
    spacing: NexusStyle.padding.extraSmall / 2

    ConnectedRect {
        id: headerCard

        Layout.fillWidth: true
        first: true
        last: !root.expanded && bodyHost.height === 0
        implicitHeight: headerRow.implicitHeight + NexusStyle.padding.medium * 2

        StateLayer {
            anchors.fill: parent
            layerRadius: NexusStyle.rounding.extraLarge
            color: Appearance.m3colors.m3onSurface
            hovered: headerMouse.containsMouse
            pressed: headerMouse.pressed
        }

        MouseArea {
            id: headerMouse

            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.expanded = !root.expanded
        }

        RowLayout {
            id: headerRow

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            MaterialSymbol {
                visible: root.icon.length > 0
                Layout.preferredWidth: root.icon.length > 0 ? implicitWidth : 0
                text: root.icon
                iconSize: NexusStyle.icon.medium
                fill: 1
                color: Appearance.m3colors.m3onSurfaceVariant
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                StyledText {
                    Layout.fillWidth: true
                    text: root.title
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    font.weight: NexusStyle.font.titleWeight
                    elide: Text.ElideRight
                }

                StyledText {
                    Layout.fillWidth: true
                    visible: root.subtitle.length > 0
                    text: root.subtitle
                    color: Appearance.m3colors.m3outline
                    font.pixelSize: NexusStyle.font.labelSmall
                    elide: Text.ElideRight
                }
            }

            MaterialSymbol {
                text: "expand_more"
                iconSize: NexusStyle.icon.medium
                color: Appearance.m3colors.m3onSurfaceVariant
                rotation: root.expanded ? 180 : 0

                Behavior on rotation {
                    NumberAnimation {
                        duration: Appearance.animation.expressiveFastEffects.duration
                        easing.type: Appearance.animation.expressiveFastEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                    }
                }
            }
        }
    }

    Item {
        id: bodyHost

        Layout.fillWidth: true
        implicitHeight: root.expanded ? innerGroup.implicitHeight : 0
        height: implicitHeight
        clip: true
        visible: height > 0 || root.expanded

        Behavior on implicitHeight {
            NumberAnimation {
                duration: Appearance.animation.expressiveDefaultSpatial.duration
                easing.type: Appearance.animation.expressiveDefaultSpatial.type
                easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
            }
        }

        PreferenceGroup {
            id: innerGroup

            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
        }
    }
}
