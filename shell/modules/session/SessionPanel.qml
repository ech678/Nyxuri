import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.Common
import qs.shared.theme
import qs.shared.controls
import qs.shared.compositor

PanelWindow {
    id: root

    required property var targetScreen
    readonly property real buttonSize: Math.max(72, Math.min(128, (width - 112 - actionRow.spacing * 5) / 6))

    property int selectedIndex: 0
    property bool closing: false

    signal actionTriggered(string action)
    signal dismissRequested()
    signal dismissFinished()

    function requestDismiss() {
        if (root.closing)
            return;
        root.closing = true;
        exitAnimation.start();
    }

    function trigger(action) {
        root.actionTriggered(action);
        root.requestDismiss();
    }

    screen: targetScreen
    visible: true
    color: "transparent"
    exclusiveZone: 0
    WlrLayershell.namespace: "nyxuri-shell-session"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.exclusionMode: ExclusionMode.Ignore
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

    anchors {
        left: true
        right: true
        top: true
        bottom: true
    }

    Component.onCompleted: {
        root.selectedIndex = 0;
        interactionArea.forceActiveFocus(Qt.OtherFocusReason);
        enterAnimation.start();
    }

    ParallelAnimation {
        id: enterAnimation
        NumberAnimation {
            target: menuBackground
            property: "opacity"
            from: 0.0
            to: 1.0
            duration: Appearance.animation.expressiveFastEffects.duration
            easing.type: Appearance.animation.expressiveFastEffects.type
            easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
        }
        NumberAnimation {
            target: menuBackground
            property: "scale"
            from: 0.92
            to: 1.0
            duration: Appearance.animation.expressiveFastEffects.duration
            easing.type: Appearance.animation.expressiveFastEffects.type
            easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
        }
    }

    ParallelAnimation {
        id: exitAnimation
        NumberAnimation {
            target: menuBackground
            property: "opacity"
            from: 1.0
            to: 0.0
            duration: Appearance.animation.expressiveFastEffects.duration
            easing.type: Appearance.animation.expressiveFastEffects.type
            easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
        }
        NumberAnimation {
            target: menuBackground
            property: "scale"
            from: 1.0
            to: 0.95
            duration: Appearance.animation.expressiveFastEffects.duration
            easing.type: Appearance.animation.expressiveFastEffects.type
            easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
        }
        onFinished: {
            root.dismissFinished();
        }
    }

    Item {
        id: interactionArea

        anchors.fill: parent
        focus: true
        Keys.onPressed: event => {
            if (root.closing) {
                event.accepted = true;
                return;
            }

            switch (event.key) {
            case Qt.Key_Left:
            case Qt.Key_Up:
                root.selectedIndex = (root.selectedIndex + actionRepeater.count - 1) % actionRepeater.count;
                break;
            case Qt.Key_Right:
            case Qt.Key_Down:
                root.selectedIndex = (root.selectedIndex + 1) % actionRepeater.count;
                break;
            case Qt.Key_Return:
            case Qt.Key_Enter:
                if (!event.isAutoRepeat)
                    root.trigger(actionRepeater.itemAt(root.selectedIndex).modelData.action);
                break;
            case Qt.Key_Escape:
                root.requestDismiss();
                break;
            case Qt.Key_L:
                root.trigger("lock");
                break;
            case Qt.Key_E:
                root.trigger("logout");
                break;
            case Qt.Key_U:
                root.trigger("suspend");
                break;
            case Qt.Key_S:
                root.trigger("poweroff");
                break;
            case Qt.Key_H:
                root.trigger("hibernate");
                break;
            case Qt.Key_R:
                root.trigger("reboot");
                break;
            default:
                return;
            }
            event.accepted = true;
        }

        MouseArea {
            anchors.fill: parent
            onClicked: root.requestDismiss()
        }

        Rectangle {
            id: menuBackground

            anchors.centerIn: parent
            width: actionRow.implicitWidth + 56
            height: actionRow.implicitHeight + 56
            radius: Appearance.rounding.extraLarge
            color: Appearance.colors.colLayer0

            MouseArea {
                anchors.fill: parent
            }

            RowLayout {
                id: actionRow

                anchors.centerIn: parent
                spacing: 16

                Repeater {
                    id: actionRepeater
                    model: [
                        {
                            "action": "lock",
                            "icon": "lock",
                            "label": qsTr("Lock screen")
                        },
                        {
                            "action": "logout",
                            "icon": "logout",
                            "label": qsTr("Log out")
                        },
                        {
                            "action": "suspend",
                            "icon": "bedtime",
                            "label": qsTr("Suspend")
                        },
                        {
                            "action": "poweroff",
                            "icon": "power_settings_new",
                            "label": qsTr("Shut down")
                        },
                        {
                            "action": "hibernate",
                            "icon": "mode_night",
                            "label": qsTr("Hibernate")
                        },
                        {
                            "action": "reboot",
                            "icon": "restart_alt",
                            "label": qsTr("Restart")
                        }
                    ]

                    delegate: Rectangle {
                        id: actionButton

                        required property int index
                        required property var modelData
                        readonly property bool selected: root.selectedIndex === index

                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.label
                        Accessible.focused: selected && interactionArea.activeFocus
                        Accessible.onPressAction: root.trigger(modelData.action)

                        Layout.preferredWidth: root.buttonSize
                        Layout.preferredHeight: root.buttonSize
                        radius: Appearance.rounding.large
                        color: actionMouse.pressed ? Appearance.colors.colPrimaryActive : (
                                   actionButton.selected
                                   ? Appearance.colors.colPrimaryHover :
                                     Appearance.colors.colLayer1)

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 5

                            Item {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: 60
                                Layout.preferredHeight: 60

                                MaterialSymbol {
                                    id: actionIcon

                                    anchors.centerIn: parent
                                    text: actionButton.modelData.icon
                                    iconSize: 54
                                    fill: 0
                                    color: actionButton.selected ? Appearance.colors.colOnPrimary :
                                                                   Appearance.colors.colOnLayer1
                                    scale: actionMouse.pressed ? 50 / 54 : (actionButton.selected ? 1 : 44 / 54)
                                    transformOrigin: Item.Center
                                    smooth: true
                                    layer.enabled: true
                                    layer.smooth: true
                                    layer.mipmap: true

                                    Behavior on scale {
                                        NumberAnimation {
                                            duration: Appearance.animation.expressiveSlowEffects.duration
                                            easing.type: Appearance.animation.expressiveSlowEffects.type
                                            easing.bezierCurve: Appearance.animation.expressiveSlowEffects.bezierCurve
                                        }
                                    }

                                    Behavior on color {
                                        ColorAnimation {
                                            duration: Appearance.animation.expressiveFastEffects.duration
                                            easing.type: Appearance.animation.expressiveFastEffects.type
                                            easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                                        }
                                    }
                                }
                            }

                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: actionButton.modelData.label
                                color: actionButton.selected ? Appearance.colors.colOnPrimary :
                                                               Appearance.colors.colOnLayer1
                                font.family: Fonts.ui
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                            }
                        }

                        MouseArea {
                            id: actionMouse

                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: root.selectedIndex = actionButton.index
                            onClicked: root.trigger(actionButton.modelData.action)
                        }

                        Behavior on color {
                            ColorAnimation {
                                duration: Appearance.animation.expressiveFastEffects.duration
                                easing.type: Appearance.animation.expressiveFastEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                            }
                        }
                    }
                }
            }
        }

        CompositorBlurRegion {
            targetWindow: root
            backgroundItem: menuBackground
            radius: menuBackground.radius
        }
    }

    mask: Region {
        item: interactionArea
    }
}
