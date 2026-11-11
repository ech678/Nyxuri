import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import qs.commons
import qs.ui
import qs.commons.i18n

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
            title: I18n.tr("Dashboard", "HubContent")
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
                        duration: 200
                    }
                }
            }

            Text {
                text: parent.parent.title
                font.pixelSize: 13
                font.bold: parent.parent.active
                color: parent.parent.active ? Appearance.colors.colOnLayer0 : Appearance.applyAlpha(Appearance.colors.colOnLayer0, 0.5)
                anchors.horizontalCenter: parent.horizontalCenter

                Behavior on color {
                    ColorAnimation {
                        duration: 200
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
                    duration: 300
                    easing.type: Easing.OutBack
                }
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: 200
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
            // Use a file URL: Quickshell's Loader cannot resolve plugin-local
            // components through its intercepted relative URL scheme.
            source: Qt.resolvedUrl("../dashboard/DashboardContent.qml")
            onLoaded: {
                item.screen = Qt.binding(function () {
                    return root.screen;
                });
                item.active = Qt.binding(function () {
                    return root.visible && root.currentIndex === 0;
                });
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: 300
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
            // Keep weather out of the object tree until its tab is selected.
            source: Qt.resolvedUrl("../weather/WeatherContent.qml")
            onLoaded: item.active = Qt.binding(function () {
                return root.visible && root.currentIndex === 1;
            })

            Behavior on opacity {
                NumberAnimation {
                    duration: 300
                }
            }
        }

        Connections {
            target: dashboardLoader.item
            function onCloseRequested() {
                root.closeRequested();
            }
            function onAvatarEditRequested() {
                root.avatarEditRequested();
            }
        }
    }
}
