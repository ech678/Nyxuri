pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Widgets
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.modules.wallpaper
import qs.modules.settings

// Dashboard "Wallpapers" page. Layout ported from end4-pC's
// DashboardWallpapersPage: a strip of control tiles over a wallpaper grid with
// per-tile apply affordances.
//
// Not ported, because nyxuri has no counterpart:
//   - the "Use for both" toggle and the lock-screen badges/actions. end4-pC
//     models a separate lock wallpaper (`background.lockWall`); nyxuri has one
//     wallpaper per screen and no lock variant.
//   - pre-generated thumbnails (`Wallpapers.generateThumbnail`). nyxuri has no
//     thumbnail service, so tiles decode at the requested source size instead.
Item {
    id: root

    required property Item pager
    property int staggerMs: 45
    property int selectedIndex: 0

    readonly property string query: pager.searchQuery ?? ""
    readonly property var paths: {
        const all = WallpaperService.wallpapers;
        const needle = query.trim().toLowerCase();
        return needle === "" ? all : all.filter(path => String(path).toLowerCase().indexOf(needle) >= 0);
    }
    readonly property string desktopPath: WallpaperService.normalizedPath(PersonalizationConfig.wallpaperPath)
    readonly property int columns: Math.max(2, Math.round(width / 270))
    readonly property int tileWidth: Math.max(1, Math.floor(width / columns) - 12)
    readonly property int tileHeight: Math.max(1, Math.round(Math.floor(width / columns) * 0.64) - 12)

    property bool ready: false

    function applyTo(path) {
        if (!path)
            return;
        WallpaperService.setWallpaper(path, "");
    }

    function activate() {
        const path = root.paths[root.selectedIndex];
        if (path)
            root.applyTo(path);
    }

    function randomWallpaper() {
        WallpaperService.cycleRandom();
    }

    function moveSelection(dx, dy) {
        const next = root.selectedIndex + dx + dy * root.columns;
        if (next < 0 || next >= root.paths.length)
            return;
        root.selectedIndex = next;
        grid.positionViewAtIndex(next, GridView.Contain);
    }

    Timer {
        id: readyTimer

        interval: 60
        running: true
        onTriggered: root.ready = true
    }

    Component.onDestruction: readyTimer.stop()

    Component.onCompleted: WallpaperService.scan()

    onPathsChanged: root.selectedIndex = Math.min(root.selectedIndex, Math.max(0, root.paths.length - 1))

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 136
            Layout.minimumHeight: 136
            Layout.maximumHeight: 136
            spacing: 12

            DashboardWallpaperToolsCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 16
                Layout.fillHeight: true
                title: qsTr("Wallpaper tools")
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 0
                travelX: 0
                travelY: -120
                onRandomRequested: root.randomWallpaper()
                onFoldersRequested: wallpaperBrowser.openAt(PersonalizationConfig.wallpaperFolder)
            }

            DashboardSpinCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 10
                Layout.fillHeight: true
                controlKey: "wallpaper:Transition duration (ms)"
                title: qsTr("Transition (ms)")
                icon: "speed"
                tileShape: MaterialShapeCanvas.Shape.Gem
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 1
                travelX: 0
                travelY: -120
            }

            DashboardComboCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 16
                Layout.fillHeight: true
                controlKey: "wallpaper:Transition"
                title: qsTr("Transition")
                icon: "animation"
                tileShape: MaterialShapeCanvas.Shape.Puffy
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 2
                travelX: 200
                travelY: 0
            }

            DashboardToggleCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.horizontalStretchFactor: 10
                Layout.fillHeight: true
                controlKey: "wallpaper:Auto cycle"
                title: qsTr("Auto cycle")
                icon: "autorenew"
                tileShape: MaterialShapeCanvas.Shape.Cookie6Sided
                pager: root.pager
                staggerMs: root.staggerMs
                animIndex: 3
                travelX: 200
                travelY: 0
            }
        }

        GridView {
            id: grid

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            cellWidth: Math.floor(width / root.columns)
            cellHeight: Math.round(cellWidth * 0.64)
            model: root.ready ? root.paths : []
            cacheBuffer: 0
            ScrollBar.vertical: StyledScrollBar {}

            WheelScrollController {
                flickable: grid
            }

            // The default wheel step crawls through a full wallpaper library; use

            delegate: Item {
                id: cell

                required property int index
                required property var modelData

                readonly property bool selected: root.selectedIndex === cell.index
                readonly property bool isDesktop: WallpaperService.normalizedPath(cell.modelData)
                                                  === root.desktopPath

                width: grid.cellWidth
                height: grid.cellHeight

                DashboardCard {
                    id: tile

                    anchors.fill: parent
                    anchors.margins: 6
                    tint: Appearance.colors.colLayer1
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: cell.index % 8
                    travelX: 0
                    travelY: 80

                    // A plain Rectangle with clip only clips to the bounding box, so
                    // the thumbnail corners stay square. ClippingRectangle masks to
                    // the rounded border instead.
                    ClippingRectangle {
                        anchors.fill: parent
                        radius: tile.cardRadius
                        color: "transparent"

                        Image {
                            anchors.fill: parent
                            source: "file://" + cell.modelData
                            asynchronous: true
                            cache: false
                            fillMode: Image.PreserveAspectCrop
                            sourceSize.width: root.tileWidth
                            sourceSize.height: root.tileHeight
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: parent.height * 0.55
                            opacity: hover.containsMouse || cell.selected ? 1 : 0
                            gradient: Gradient {
                                GradientStop {
                                    position: 0
                                    color: "transparent"
                                }
                                GradientStop {
                                    position: 1
                                    color: Qt.rgba(0, 0, 0, 0.75)
                                }
                            }

                            Behavior on opacity {
                                NumberAnimation {
                                    duration: 150
                                }
                            }
                        }

                        Row {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: 8
                            spacing: 6

                            Rectangle {
                                visible: cell.isDesktop
                                width: 30
                                height: 30
                                radius: 15
                                color: Appearance.colors.colPrimary

                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    text: "desktop_windows"
                                    iconSize: 18
                                    fill: 1
                                    color: Appearance.colors.colOnPrimary
                                }
                            }
                        }

                        MouseArea {
                            id: hover

                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.selectedIndex = cell.index;
                                root.pager.forceActiveFocus();
                                root.applyTo(cell.modelData);
                            }
                        }

                        Row {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 10
                            spacing: 6
                            opacity: hover.containsMouse || cell.selected ? 1 : 0

                            Behavior on opacity {
                                NumberAnimation {
                                    duration: 150
                                }
                            }

                            RippleButton {
                                implicitHeight: 34
                                leftPadding: 14
                                rightPadding: 14
                                buttonRadius: 17
                                containerColor: Qt.rgba(0, 0, 0, 0.55)
                                rippleColor: "white"
                                stateLayerColor: Appearance.colors.colOnPrimary
                                stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                                downAction: () => {
                                    const path = cell.modelData;
                                    root.selectedIndex = cell.index;
                                    Qt.callLater(() => root.applyTo(path));
                                }

                                contentItem: Item {
                                    implicitWidth: contentRow.implicitWidth
                                    implicitHeight: contentRow.implicitHeight

                                    RowLayout {
                                        id: contentRow

                                        anchors.centerIn: parent
                                        spacing: 6

                                        MaterialSymbol {
                                            text: "wallpaper"
                                            iconSize: 16
                                            color: "white"
                                        }

                                        StyledText {
                                            text: qsTr("Apply")
                                            color: "white"
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        radius: tile.cardRadius
                        color: "transparent"
                        border.width: cell.selected ? 3 : 0
                        border.color: Appearance.colors.colPrimary
                    }
                }
            }
        }
    }

    WallpaperFileBrowser {
        id: wallpaperBrowser

        parentModal: root.pager
        startPath: PersonalizationConfig.wallpaperFolder
        onFolderSelected: path => WallpaperService.setWallpaperFolder(path)
        onFileSelected: path => WallpaperService.setWallpaperFromFile(path, "")
    }
}
