pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import qs.shared.theme
import qs.shared.controls

// On/off tile. Ported from end4-pC's DashboardToggleCard; the control comes from
// SettingsControlCatalog instead of SettingsQuickControls.
DashboardCard {
    id: root

    property string controlKey: ""
    property string title: ""
    property string icon: "toggle_on"
    property var tileShape: MaterialShapeCanvas.Shape.Cookie6Sided
    property var override: null

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property bool checked: root.control ? !!root.control.get() : false

    tint: root.checked ? Appearance.colors.colPrimaryContainer : Appearance.colors.colLayer1

    Behavior on tint {
        ColorAnimation {
            duration: 200
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 0

        RowLayout {
            Layout.fillWidth: true

            MaterialShapeWrappedMaterialSymbol {
                wrappedShape: root.tileShape
                text: root.icon
                iconSize: 24
                fill: 1
                padding: 10
                color: root.checked ? Appearance.colors.colPrimary : Appearance.colors.colSecondaryContainer
                colSymbol: root.checked ? Appearance.colors.colOnPrimary :
                                          Appearance.colors.colOnSecondaryContainer
            }

            Item {
                Layout.fillWidth: true
            }

            Rectangle {
                id: track

                implicitWidth: 47
                implicitHeight: 27
                radius: height / 2
                color: root.checked ? Appearance.colors.colPrimary : Appearance.m3colors.m3surfaceBright

                Behavior on color {
                    ColorAnimation {
                        duration: 180
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    radius: parent.radius
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.06)
                }

                Rectangle {
                    id: thumb

                    width: 23
                    height: 23
                    radius: width / 2
                    anchors.verticalCenter: parent.verticalCenter
                    x: root.checked ? track.width - width - 2 : 2
                    color: root.checked ? Appearance.colors.colOnPrimary : Appearance.colors.colPrimary

                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: Qt.rgba(0, 0, 0, 0.55)
                        shadowVerticalOffset: 2
                        shadowHorizontalOffset: 0
                        shadowBlur: 0.4
                    }

                    Behavior on x {
                        NumberAnimation {
                            duration: 320
                            easing.type: Easing.BezierSpline
                            easing.bezierCurve: [0.42, 1.5, 0.28, 0.95, 1, 1]
                        }
                    }

                    Behavior on color {
                        ColorAnimation {
                            duration: 180
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }

        StyledText {
            Layout.fillWidth: true
            text: root.title
            font.pixelSize: Typography.titleLarge.pixelSize
            font.weight: Font.DemiBold
            color: root.checked ? Appearance.colors.colOnPrimaryContainer : Appearance.colors.colOnLayer1
            elide: Text.ElideRight
        }

        StyledText {
            text: root.checked ? qsTr("On") : qsTr("Off")
            font.pixelSize: Typography.bodySmall.pixelSize
            color: root.checked ? Appearance.colors.colOnPrimaryContainer : Appearance.colors.colSubtext
            opacity: 0.8
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            if (!root.control)
                return;
            const next = !root.checked;
            Qt.callLater(() => root.control.set(next));
        }
    }
}
