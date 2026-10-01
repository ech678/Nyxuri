pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Quickshell
import qs.Common
import qs.Modules.Wallpaper
import qs.Services
import qs.Widgets.common
import "../../Common/functions/ZenPalette.js" as Zen

Item {
    id: root
    property var parentModal: null
    property bool requiresParentWindow: true
    property int sessionToken: 0
    property bool shouldBeVisible: false
    function showFor(target, output) {
        if (root.requiresParentWindow && !root.parentModal)
            return;
        root.sessionToken = WallpaperPaletteSession.begin(target, output);
        root.shouldBeVisible = root.sessionToken !== 0;
    }
    function close() {
        WallpaperPaletteSession.cancel(root.sessionToken);
        root.shouldBeVisible = false;
        root.sessionToken = 0;
    }
    Component.onDestruction: root.close()
    Connections {
        target: root.parentModal
        function onVisibleChanged() {
            if (!root.parentModal.visible)
                root.close();
        }
    }
    Connections {
        target: WallpaperPaletteSession
        function onInvalidated(token) {
            if (token === root.sessionToken)
                root.close();
        }
    }
    FloatingWindow {
        id: window
        parentWindow: root.parentModal
        title: "clavis-control-center-color-picker"
        visible: root.shouldBeVisible
        color: "transparent"
        implicitWidth: 470
        implicitHeight: 650
        minimumSize: Qt.size(430, 610)
        onClosed: root.close()
        Rectangle {
            id: background
            anchors.fill: parent
            radius: Appearance.rounding.large
            color: BlurService.backgroundColor(Appearance.m3colors.m3surfaceContainerLow)
            border.width: 1
            border.color: Appearance.colors.colOutlineVariant
        }
        CompositorBlurRegion {
            targetWindow: window
            backgroundItem: background
            radius: background.radius
        }
        FocusScope {
            anchors.fill: parent
            focus: true
            Keys.onEscapePressed: root.close()
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Wallpaper palette")
                        font.family: Fonts.ui
                        font.pixelSize: 20
                        color: Appearance.colors.colOnSurface
                    }
                    IconButton {
                        iconName: "close"
                        tooltipText: qsTr("Close")
                        onClicked: root.close()
                    }
                }
                RowLayout {
                    id: paletteBody
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 24

                    readonly property bool expanded: width >= 860

                    Item {
                        id: editorFrame
                        Layout.fillWidth: !paletteBody.expanded
                        Layout.preferredWidth: paletteBody.expanded ? Math.min(560, paletteBody.width * 0.4) :
                                                                      434
                        Layout.fillHeight: true

                        // Keep the compact editor's proportions, including its
                        // buttons, swatches and slider, at every window size.
                        ZenPaletteEditor {
                            id: editor
                            anchors.centerIn: parent
                            width: 434
                            height: 520
                            scale: Math.min(1.5, editorFrame.width / width, editorFrame.height / height)
                            paletteState: WallpaperPaletteSession.draft || Zen.initial()
                            onEdited: value => WallpaperPaletteSession.update(root.sessionToken, value)
                        }
                    }

                    Loader {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.maximumHeight: editor.height * editor.scale
                        Layout.alignment: Qt.AlignVCenter
                        visible: paletteBody.expanded
                        active: visible && root.shouldBeVisible
                        sourceComponent: Item {
                            ZenPaletteRenderer {
                                id: preview
                                anchors.fill: parent
                                paletteState: editor.paletteState
                                visible: false
                                layer.enabled: true
                            }
                            Rectangle {
                                id: previewMask
                                anchors.fill: parent
                                radius: Appearance.rounding.large
                                color: "black"
                                visible: false
                                layer.enabled: true
                            }
                            MultiEffect {
                                anchors.fill: parent
                                source: preview
                                maskEnabled: true
                                maskSource: previewMask
                                maskThresholdMin: 0.5
                                maskSpreadAtMin: 1
                            }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: WallpaperPaletteSession.error !== ""
                    text: WallpaperPaletteSession.error
                    color: Appearance.colors.colError
                    wrapMode: Text.Wrap
                    font.family: Fonts.ui
                }
                RowLayout {
                    Layout.fillWidth: true
                    Item {
                        Layout.fillWidth: true
                    }
                    ActionButton {
                        text: qsTr("Save")
                        onClicked: {
                            if (WallpaperPaletteSession.commit(root.sessionToken)) {
                                root.shouldBeVisible = false;
                                root.sessionToken = 0;
                            }
                        }
                    }
                }
            }
        }
    }
}
