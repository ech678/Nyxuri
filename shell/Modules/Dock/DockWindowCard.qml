pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import Clavis.WindowPreview
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.common

Button {
    id: root

    required property var windowData
    property string applicationName: ""
    property string applicationIcon: ""
    property bool showThumbnail: false
    property WindowCaptureProbe capture: null
    property WindowPreviewFrame previewFrame: null
    property var mediaPlayer: null
    readonly property string title: String(windowData && (windowData.title || windowData.appName
                                                          || windowData.appId) || applicationName)
    readonly property bool minimized: !!windowData && !!windowData.isMinimized
    readonly property bool hasFrame: !!previewFrame && previewFrame.hasFrame
    readonly property bool busy: !minimized && !!capture && !hasFrame && capture.error === ""
    // Below this width, shrink the entire card, including its controls. There
    // is deliberately no minimum width that could overflow the preview row.
    readonly property real detailScale: Math.min(1, width / 160)
    readonly property real logicalWidth: detailScale > 0 ? width / detailScale : 160

    signal activated
    signal closeRequested

    height: (showThumbnail ? 40 + (logicalWidth - 16) / 1.6 + 8 : 40) * detailScale
    padding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: title
    onClicked: activated()

    background: Rectangle {
        radius: Math.min(8, root.height / 4)
        color: Appearance.applyAlpha(Appearance.colors.colOnSurface, root.down ? 0.12 : root.hovered ? 0.07 :
                                                                                                       0)

        border.width: root.visualFocus ? 1 : 0
        border.color: Appearance.colors.colPrimary
    }

    contentItem: Item {
        clip: true
        Item {
            width: root.logicalWidth
            height: root.detailScale > 0 ? root.height / root.detailScale : 0
            scale: root.detailScale
            transformOrigin: Item.TopLeft

            ThemeIcon {
                x: 8
                y: 12
                width: 16
                height: 16
                iconSource: ApplicationService.iconSource(root.applicationIcon)
                sourceSize: Qt.size(32, 32)
                fillMode: Image.PreserveAspectFit
            }
            Text {
                id: headerTitle
                x: 30
                y: 0
                width: Math.max(0, parent.width - x - 36)
                height: 40
                text: root.title
                textFormat: Text.PlainText
                font.family: Fonts.ui
                font.pixelSize: 12
                color: Appearance.colors.colOnSurface
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            IconButton {
                id: closeButton
                x: parent.width - width - 4
                y: 6
                controlSize: 28
                iconSize: 16
                iconName: "close"
                buttonRadius: 5
                buttonRadiusPressed: 5
                normalHoverStateLayerColor: Appearance.applyAlpha(Appearance.m3colors.m3error, 0.2)
                accessibleName: qsTr("Close window")
                onClicked: root.closeRequested()
            }
            Rectangle {
                x: 8
                y: 40
                width: parent.width - 16
                height: width / 1.6
                visible: root.showThumbnail
                color: Appearance.applyAlpha(Appearance.colors.colOnSurface, 0.05)
                radius: 4
                clip: true
                CaptureImage {
                    anchors.fill: parent
                    frame: root.previewFrame
                    visible: root.hasFrame
                }
                Text {
                    anchors.fill: parent
                    anchors.margins: 4
                    visible: !root.hasFrame && !root.busy
                    text: root.minimized ? qsTr("Minimized") : qsTr("Preview unavailable")
                    textFormat: Text.PlainText
                    font.family: Fonts.ui
                    font.pixelSize: 11
                    color: Appearance.colors.colOnSurfaceVariant
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
                InlineBusyIndicator {
                    anchors.centerIn: parent
                    busy: root.busy
                }
                Rectangle {
                    id: mediaControls
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 4
                    width: mediaButtons.width + 8
                    height: 36
                    radius: 8
                    visible: !!root.mediaPlayer
                    color: Appearance.applyAlpha(Appearance.colors.colSurfaceContainer, 0.94)

                    // Consume the bar's gaps and disabled buttons as well, so
                    // no media click activates the window behind this overlay.
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.AllButtons
                    }
                    Row {
                        id: mediaButtons
                        anchors.centerIn: parent
                        IconButton {
                            controlSize: 32
                            iconSize: 20
                            iconName: "skip_previous"
                            accessibleName: qsTr("Previous track")
                            enabled: !!root.mediaPlayer && root.mediaPlayer.canControl
                                     && root.mediaPlayer.canGoPrevious
                            onClicked: root.mediaPlayer.previous()
                        }
                        IconButton {
                            controlSize: 32
                            iconSize: 22
                            iconName: root.mediaPlayer?.isPlaying ? "pause" : "play_arrow"
                            accessibleName: root.mediaPlayer?.isPlaying ? qsTr("Pause") : qsTr("Play")
                            enabled: !!root.mediaPlayer && root.mediaPlayer.canControl
                                     && root.mediaPlayer.canTogglePlaying
                            onClicked: root.mediaPlayer.togglePlaying()
                        }
                        IconButton {
                            controlSize: 32
                            iconSize: 20
                            iconName: "skip_next"
                            accessibleName: qsTr("Next track")
                            enabled: !!root.mediaPlayer && root.mediaPlayer.canControl
                                     && root.mediaPlayer.canGoNext
                            onClicked: root.mediaPlayer.next()
                        }
                    }
                }
            }
        }
    }

    StyledToolTip {
        text: root.title
        textFormat: Text.PlainText
        extraVisibleCondition: root.hovered && headerTitle.truncated && !closeButton.pointerHovered &&
                               !mediaHover.hovered
    }

    HoverHandler {
        id: mediaHover
        parent: mediaControls
    }
}
