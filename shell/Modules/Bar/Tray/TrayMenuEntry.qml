import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Widgets
import qs.Common
import qs.Components
import qs.Widgets.common

RippleButton {
    id: root

    required property QsMenuEntry menuEntry
    property bool forceIconColumn: false
    property bool forceSpecialInteractionColumn: false
    readonly property bool entryAvailable: root.menuEntry !== null
    readonly property bool isSeparator: !root.entryAvailable || root.menuEntry.isSeparator === true
    readonly property string entryIcon: root.entryAvailable ? (root.menuEntry.icon || "") : ""
    readonly property bool hasIcon: entryIcon.length > 0
    readonly property int entryButtonType: root.entryAvailable && root.menuEntry.buttonType !== undefined ? root.menuEntry.buttonType : QsMenuButtonType.None
    readonly property bool hasSpecialInteraction: entryButtonType !== QsMenuButtonType.None
    readonly property int entryCheckState: root.entryAvailable ? root.menuEntry.checkState : Qt.Unchecked
    readonly property bool hasChildren: root.entryAvailable && root.menuEntry.hasChildren === true
    readonly property color entryForeground: root.pointerHovered ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnLayer0
    readonly property color entrySubtleForeground: root.pointerHovered ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnSurfaceVariant

    signal dismiss()
    signal openSubmenu(var handle)

    containerColor: isSeparator ? Appearance.m3colors.m3outlineVariant : "transparent"
    stateLayerColor: Appearance.colors.colSecondaryContainer
    pressedStateLayerColor: Appearance.colors.colSecondaryContainerActive
    rippleColor: Appearance.colors.colOnSecondaryContainer
    enabled: root.entryAvailable && !isSeparator && root.menuEntry.enabled !== false
    opacity: isSeparator ? 1 : (enabled ? 1 : 0.4)
    buttonRadius: 14
    implicitWidth: isSeparator ? 96 : contentRow.implicitWidth + 24
    implicitHeight: isSeparator ? 1 : 36
    Layout.topMargin: isSeparator ? 4 : 0
    Layout.bottomMargin: isSeparator ? 4 : 0
    Layout.fillWidth: true
    releaseAction: () => {
        if (!root.entryAvailable)
            return ;

        if (root.hasChildren) {
            root.openSubmenu(root.menuEntry);
            return ;
        }
        root.menuEntry.triggered();
        root.dismiss();
    }
    altAction: (event) => {
        event.accepted = false;
    }

    contentItem: RowLayout {
        id: contentRow

        spacing: 8
        visible: !root.isSeparator

        anchors {
            verticalCenter: parent.verticalCenter
            left: parent.left
            right: parent.right
            leftMargin: 12
            rightMargin: 12
        }

        Item {
            visible: root.hasSpecialInteraction || root.forceSpecialInteractionColumn
            implicitWidth: 20
            implicitHeight: 20
            Layout.alignment: Qt.AlignVCenter

            Loader {
                anchors.fill: parent
                active: root.entryButtonType === QsMenuButtonType.RadioButton

                sourceComponent: Item {
                    Rectangle {
                        anchors.centerIn: parent
                        width: 20
                        height: 20
                        radius: Appearance.rounding.full
                        color: "transparent"
                        border.width: 2
                        border.color: root.entryCheckState === Qt.Checked ? Appearance.colors.colPrimary : root.entrySubtleForeground

                        Rectangle {
                            anchors.centerIn: parent
                            width: root.entryCheckState === Qt.Checked ? 10 : 4
                            height: root.entryCheckState === Qt.Checked ? 10 : 4
                            radius: Appearance.rounding.full
                            color: Appearance.colors.colPrimary
                            opacity: root.entryCheckState === Qt.Checked ? 1 : 0

                            Behavior on width {
                                NumberAnimation {
                                    duration: Appearance.animation.expressiveDefaultSpatial.duration
                                    easing.type: Appearance.animation.expressiveDefaultSpatial.type
                                    easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                                }

                            }

                            Behavior on height {
                                NumberAnimation {
                                    duration: Appearance.animation.expressiveDefaultSpatial.duration
                                    easing.type: Appearance.animation.expressiveDefaultSpatial.type
                                    easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                                }

                            }

                            Behavior on opacity {
                                NumberAnimation {
                                    duration: Appearance.animation.expressiveEffects.duration
                                    easing.type: Appearance.animation.expressiveEffects.type
                                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                                }

                            }

                        }

                    }

                }

            }

            Loader {
                anchors.fill: parent
                active: root.entryButtonType === QsMenuButtonType.CheckBox && root.entryCheckState !== Qt.Unchecked

                sourceComponent: MaterialSymbol {
                    anchors.centerIn: parent
                    text: root.entryCheckState === Qt.PartiallyChecked ? "check_indeterminate_small" : "check"
                    iconSize: 20
                    color: root.entryForeground
                }

            }

        }

        Item {
            visible: root.hasIcon || root.forceIconColumn
            implicitWidth: 20
            implicitHeight: 20
            Layout.alignment: Qt.AlignVCenter

            Loader {
                anchors.centerIn: parent
                active: root.hasIcon

                sourceComponent: IconImage {
                    asynchronous: true
                    source: root.entryIcon
                    implicitSize: 20
                    width: 20
                    height: 20
                    mipmap: true
                }

            }

        }

        Text {
            text: root.entryAvailable ? (root.menuEntry.text || "") : ""
            color: root.entryForeground
            font.family: Fonts.ui
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            Layout.fillWidth: true
        }

        Loader {
            active: root.hasChildren
            Layout.alignment: Qt.AlignVCenter

            sourceComponent: MaterialSymbol {
                text: "chevron_right"
                iconSize: 20
                color: root.entryForeground
            }

        }

    }

}
