pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import Qt5Compat.GraphicalEffects
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.common

Item {
    id: root
    required property SpotlightStyle style
    required property var result
    required property string kind
    required property bool selected
    readonly property bool horizontal: kind === "apps" || kind === "wallpapers"
    readonly property bool wallpaper: kind === "wallpapers"
    signal selectionRequested
    signal activationRequested(string id)

    Rectangle {
        id: surface
        anchors.fill: parent
        anchors.margins: root.horizontal ? 4 : 0
        radius: Metrics.cornerM
        color: root.selected ? root.style.selectedColor : mouse.containsMouse ? root.style.hoverColor :
                                                                                "transparent"

        Item {
            id: artworkFrame
            x: root.horizontal ? (root.wallpaper ? 6 : (parent.width - width) / 2) : 12
            y: root.horizontal ? 6 : (parent.height - height) / 2
            width: root.wallpaper ? Math.max(1, parent.width - 12) : root.horizontal ? 40 : 28
            height: root.wallpaper ? width / root.style.wallpaperPreviewAspectRatio : width
            layer.enabled: root.wallpaper
            layer.effect: OpacityMask {
                maskSource: Rectangle {
                    width: artworkFrame.width
                    height: artworkFrame.height
                    radius: Metrics.cornerM
                }
            }
            Rectangle {
                anchors.fill: parent
                visible: root.wallpaper
                color: root.style.surfaceColor
            }
            ThemeIcon {
                id: artwork
                anchors.fill: parent
                iconSource: root.result.iconKind === "app" && !root.result.symbol ? ApplicationService.iconSource(
                                                                                        root.result.appIcon) :
                                                                                    root.result.iconKind
                                                                                    === "wallpaper"
                                                                                    ? root.result.previewUrl :
                                                                                      ""
                sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)
                asynchronous: true
                retainWhileLoading: false
                currentFrame: 0
                fillMode: root.wallpaper ? Image.PreserveAspectCrop : Image.PreserveAspectFit
                visible: status === Image.Ready
            }
            MaterialSymbol {
                anchors.centerIn: parent
                visible: !artwork.visible
                text: root.result.symbol || "apps"
                iconSize: root.horizontal ? 32 : 24
                transform: Scale {
                    origin.x: (root.horizontal ? 32 : 24) / 2
                    xScale: root.result.appObject?.id === ApplicationService.smallSpaceApplication.id ? 0.5 :
                                                                                                        1
                }
                color: root.selected ? root.style.selectedContentColor : Appearance.colors.colOnSurfaceVariant
            }
        }
        Column {
            id: labels
            x: root.horizontal ? 6 : artworkFrame.x + artworkFrame.width + 12
            y: root.horizontal ? artworkFrame.y + artworkFrame.height + 6 : (parent.height - height) / 2
            width: Math.max(0, parent.width - x - (root.horizontal ? 6 : 12))
            spacing: 2
            Text {
                id: title
                width: parent.width
                text: root.result.title
                textFormat: Text.PlainText
                font.family: Fonts.ui
                font.pixelSize: root.horizontal ? 13 : 15
                color: root.selected ? root.style.selectedContentColor : Appearance.colors.colOnSurface
                horizontalAlignment: root.horizontal ? Text.AlignHCenter : Text.AlignLeft
                maximumLineCount: 1
                wrapMode: Text.NoWrap
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                visible: !root.horizontal && text !== ""
                text: root.result.subtitle || ""
                textFormat: Text.PlainText
                font.family: Fonts.ui
                font.pixelSize: 12
                color: root.selected ? root.style.selectedContentColor : Appearance.colors.colOnSurfaceVariant
                elide: Text.ElideMiddle
            }
        }
        MouseArea {
            id: mouse
            property string pressedId: ""
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            acceptedButtons: Qt.LeftButton
            Accessible.role: Accessible.Button
            Accessible.selected: root.selected
            Accessible.name: root.result.title
            Accessible.description: root.result.subtitle || ""
            onPressed: {
                appDrag.resetGesture();
                pressedId = root.result.id;
                root.selectionRequested();
            }
            onClicked: {
                if (!appDrag.dragged && pressedId === root.result.id)
                    root.activationRequested(pressedId);
            }
            Accessible.onPressAction: root.activationRequested(root.result.id)
        }
        SpotlightAppDrag {
            id: appDrag

            desktopId: root.kind === "apps" && root.result.appObject ? String(root.result.appObject.id) : ""
            iconItem: artworkFrame
        }
        StyledToolTip {
            extraVisibleCondition: false
            alternativeVisibleCondition: mouse.containsMouse && (title.truncated || !!root.result.appObject
                                                                 ?.dragOnly) &&
                                         !DockService.externalDragActive
            text: root.result.appObject?.dragOnly ? root.result.subtitle : root.result.title
            textFormat: Text.PlainText
        }
    }
}
