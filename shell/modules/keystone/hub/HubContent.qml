import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import qs.shared.theme
import qs.shared.controls
import qs.modules.keystone.dashboard
import qs.modules.keystone.weather
import qs.shared.i18n

Item {
    id: root

    property var screen: null
    property int currentIndex: 0
    readonly property var dashboardKeyholeGlassItems: dashboardLoader.item ? dashboardLoader.item.keyholeGlassItems : []
    readonly property real dashboardKeyholeCenterOffset: dashboardLoader.item ? dashboardLoader.item.keyholeCenterOffset : 0

    signal closeRequested
    signal avatarEditRequested

    function cycleTab(step) {
        const count = tabBar.children.length;
        if (count > 0)
            root.currentIndex = ((root.currentIndex + step) % count + count) % count;
    }

    implicitWidth: currentIndex === 0 ? (dashboardLoader.item ? dashboardLoader.item.implicitWidth : 1040) : 960
    implicitHeight: 100 + (currentIndex === 0 ? 520 : (weatherLoader.item ? weatherLoader.item.height : 570))

    Shortcut {
        enabled: root.visible
        sequence: "Tab"
        onActivated: root.cycleTab(1)
    }

    Shortcut {
        enabled: root.visible
        sequence: "Shift+Tab"
        onActivated: root.cycleTab(-1)
    }

    RowLayout {
        id: tabBar

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 80
        anchors.margins: 10
        spacing: 15

        TabBtn {
            icon: "dashboard"
            title: I18n.tr("Dashboard")
            index: 0
        }

        TabBtn {
            icon: "sunny"
            title: I18n.tr("Weather")
            index: 1
        }
    }

    component TabBtn: Item {
        property string icon: ""
        property string title: ""
        property int index: 0
        property bool active: root.currentIndex === index

        Layout.fillWidth: true
        Layout.fillHeight: true

        Column {
            anchors.centerIn: parent
            spacing: 6

            MaterialSymbol {
                text: parent.parent.icon
                iconSize: 22
                fill: parent.parent.active ? 1 : 0
                color: parent.parent.active ? Appearance.colors.colOnLayer0 : Appearance.applyAlpha(Appearance.colors.colOnLayer0, 0.5)
                anchors.horizontalCenter: parent.horizontalCenter

                Behavior on color {
                    ColorAnimation {
                        duration: Appearance.motionDuration(200)
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: Appearance.animationCurves.standard
                    }
                }
            }

            Text {
                text: parent.parent.title
                font.pixelSize: Appearance.scaledFont(13)
                font.bold: parent.parent.active
                color: parent.parent.active ? Appearance.colors.colOnLayer0 : Appearance.applyAlpha(Appearance.colors.colOnLayer0, 0.5)
                anchors.horizontalCenter: parent.horizontalCenter

                Behavior on color {
                    ColorAnimation {
                        duration: Appearance.motionDuration(200)
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: Appearance.animationCurves.standard
                    }
                }
            }
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.active ? 40 : 0
            height: 3
            radius: 1.5
            color: Appearance.colors.colPrimary
            opacity: parent.active ? 1 : 0

            Behavior on width {
                NumberAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                }
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: Appearance.motionDuration(200)
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: Appearance.animationCurves.standard
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.currentIndex = parent.index
        }
    }

    Item {
        anchors.top: tabBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.topMargin: 10

        Loader {
            id: dashboardLoader

            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            active: root.visible && root.currentIndex === 0
            visible: active
            opacity: visible ? 1 : 0
            sourceComponent: DashboardContent {
                screen: root.screen
                active: root.visible && root.currentIndex === 0
                onCloseRequested: root.closeRequested()
                onAvatarEditRequested: root.avatarEditRequested()
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: Appearance.animation.expressiveEffects.duration
                    easing.type: Appearance.animation.expressiveEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                }
            }
        }

        Loader {
            id: weatherLoader

            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            active: root.visible && root.currentIndex === 1
            visible: active
            opacity: visible ? 1 : 0
            sourceComponent: WeatherContent {
                active: root.visible && root.currentIndex === 1
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
