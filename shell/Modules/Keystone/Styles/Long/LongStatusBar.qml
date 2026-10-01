pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.Services
import qs.Modules.Keystone.ClockContent
import qs.Modules.Bar.Workspaces
import qs.Modules.Bar.Tray
import qs.Modules.Bar.Media
import qs.Modules.Bar.SysMonitor

Item {
    id: root

    required property var screen
    required property string edge
    readonly property string popupEdge: edge
    readonly property bool vertical: edge === "left" || edge === "right"
    readonly property bool clockHovered: clockHover.hovered
    readonly property bool hovered: mainHover.hovered
    readonly property alias clockItem: clock
    // Reserve equal space on both sides so changing module sizes never
    // pushes the clock away from the main island's geometric centre.
    readonly property real contentLength: 220 + 2 * (Math.max(leadingLane.contentExtent,
                                                              trailingLane.contentExtent) + 28)

    signal clockClicked(int button)
    signal mediaRequested

    HoverHandler {
        id: mainHover
    }

    ClockContent {
        id: clock
        anchors.centerIn: parent
        width: root.vertical ? 42 : 220
        height: root.vertical ? 220 : 42
        edge: root.edge
        player: MediaManager.active

        HoverHandler {
            id: clockHover
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.MiddleButton
            cursorShape: Qt.PointingHandCursor
            onClicked: mouse => root.clockClicked(mouse.button)
        }
    }

    StatusLane {
        id: leadingLane
        items: PersonalizationConfig.keystoneLongLeading
        x: root.vertical ? 0 : 16
        y: root.vertical ? 16 : 0
        width: root.vertical ? root.width : Math.max(0, clock.x - 28)
        height: root.vertical ? Math.max(0, clock.y - 28) : root.height
    }

    StatusLane {
        id: trailingLane
        items: PersonalizationConfig.keystoneLongTrailing
        x: root.vertical ? 0 : clock.x + clock.width + 12
        y: root.vertical ? clock.y + clock.height + 12 : 0
        width: root.vertical ? root.width : Math.max(0, root.width - x - 16)
        height: root.vertical ? Math.max(0, root.height - y - 16) : root.height
        trailing: true
    }

    component StatusLane: Item {
        id: lane
        required property var items
        property bool trailing: false
        readonly property real contentExtent: root.vertical ? itemsLayout.implicitHeight :
                                                              itemsLayout.implicitWidth

        GridLayout {
            id: itemsLayout
            x: root.vertical ? (lane.width - width) / 2 : lane.trailing ? Math.max(0, lane.width - width) : 0
            y: root.vertical ? (lane.trailing ? Math.max(0, lane.height - height) : 0) : (lane.height - height)
                               / 2
            columns: root.vertical ? 1 : Math.max(1, lane.items.length)
            rowSpacing: 8
            columnSpacing: 8

            Repeater {
                model: lane.items
                delegate: Loader {
                    id: statusLoader
                    required property string modelData
                    Layout.alignment: Qt.AlignCenter
                    Layout.preferredWidth: root.vertical ? root.width : implicitWidth
                    sourceComponent: modelData === "tray" ? tray : modelData === "workspaces" ? workspaces : modelData
                                                                                                === "media"
                                                                                                ? media : modelData
                                                                                                  === "systemMonitor"
                                                                                                  ? systemMonitor :
                                                                                                    status

                    Component {
                        id: workspaces
                        Workspaces {
                            screenName: root.screen ? root.screen.name : ""
                            vertical: root.vertical
                            backgroundVisible: false
                        }
                    }

                    Component {
                        id: tray
                        Tray {
                            screen: root.screen
                            edge: root.edge
                            vertical: root.vertical
                            barVisualItem: root
                            backgroundVisible: false
                        }
                    }

                    Component {
                        id: media
                        MediaBar {
                            vertical: root.vertical
                            edge: root.edge
                            maximumTitleWidth: root.vertical ? 120 : 180
                            backgroundVisible: false
                        }
                    }

                    Component {
                        id: systemMonitor
                        SysMonitor {
                            showValues: PersonalizationConfig.keystoneLongShowMonitorValues
                            vertical: root.vertical
                            ownerId: "keystone-long:" + String(root.screen ? root.screen.name : "default") + (
                                         lane.trailing ? ":trailing" : ":leading")
                            backgroundVisible: false
                        }
                    }

                    Component {
                        id: status
                        LongStatusItem {
                            maximumNameWidth: root.vertical ? 96 : 160
                            itemId: statusLoader.modelData
                            edge: root.edge
                            ownerId: "keystone-long:" + String(root.screen ? root.screen.name : "default") + (
                                         lane.trailing ? ":trailing" : ":leading")
                            screen: root.screen
                            onMediaRequested: root.mediaRequested()
                        }
                    }
                }
            }
        }
    }
}
