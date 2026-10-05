import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.shared.theme
import qs.shared.controls
import qs.app.services

Variants {
    id: root

    model: Quickshell.screens

    delegate: PanelWindow {
        id: switcherWindow
        required property var modelData
        readonly property bool focused: WindowSwitcherService.visible
        property bool holding: false
        Connections {
            target: WindowSwitcherService
            function onVisibleChanged() {
                if (WindowSwitcherService.visible) {
                    switcherWindow.holding = true;
                    return;
                }
                if (!Appearance.animationsEnabled) {
                    switcherWindow.holding = false;
                    return;
                }
                switcherWindow.releaseTimer.restart();
            }
        }
        Timer {
            id: releaseTimer
            interval: Appearance.animation.expressiveFastSpatial.duration + 40
            onTriggered: switcherWindow.holding = false
        }
        screen: modelData
        visible: WindowSwitcherService.visible || holding
        color: "transparent"
        exclusiveZone: 0
        WlrLayershell.namespace: "nyxuri-shell-switcher"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.exclusionMode: ExclusionMode.Ignore
        WlrLayershell.keyboardFocus: focused ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
        anchors {
            left: true
            right: true
            top: true
            bottom: true
        }
        Item {
            id: overlay
            property real revealProgress: WindowSwitcherService.visible ? 1 : 0
            anchors.fill: parent
            focus: switcherWindow.focused
            Behavior on revealProgress {
                enabled: Appearance.animationsEnabled
                NumberAnimation {
                    duration: Appearance.animation.expressiveFastSpatial.duration
                    easing.type: Appearance.animation.expressiveFastSpatial.type
                    easing.bezierCurve: Appearance.animation.expressiveFastSpatial.bezierCurve
                }
            }
            Keys.onEscapePressed: WindowSwitcherService.close()
            Keys.onReturnPressed: WindowSwitcherService.activate()
            Keys.onEnterPressed: WindowSwitcherService.activate()
            Keys.onTabPressed: WindowSwitcherService.step(1)
            Keys.onBacktabPressed: WindowSwitcherService.step(-1)
            Keys.onLeftPressed: WindowSwitcherService.step(-1)
            Keys.onRightPressed: WindowSwitcherService.step(1)
            Component.onCompleted: {
                if (switcherWindow.focused)
                    overlay.forceActiveFocus(Qt.OtherFocusReason);
            }
            onVisibleChanged: {
                if (switcherWindow.focused)
                    overlay.forceActiveFocus(Qt.OtherFocusReason);
            }
            Rectangle {
                anchors.fill: parent
                color: Appearance.colors.colScrim
                opacity: overlay.revealProgress
            }
            Rectangle {
                id: card
                anchors.centerIn: parent
                width: Math.min(implicitWidth, parent.width - 64)
                height: Math.min(implicitHeight, parent.height - 64)
                implicitWidth: grid.implicitWidth + 40
                implicitHeight: grid.implicitHeight + 40
                radius: Appearance.rounding.large
                color: Appearance.applyAlpha(Appearance.colors.colLayer2, Appearance.backgroundOpacity)
                border.width: 1
                border.color: Appearance.colors.colOutline
                opacity: overlay.revealProgress
                scale: 0.94 + 0.06 * overlay.revealProgress
                transform: Translate {
                    y: Appearance.animationsEnabled ? (1 - overlay.revealProgress) * 14 : 0
                }
                GridLayout {
                    id: grid
                    anchors.centerIn: parent
                    columns: 4
                    rowSpacing: 12
                    columnSpacing: 12
                    Repeater {
                        model: WindowSwitcherService.entries
                        delegate: Rectangle {
                            id: tile
                            required property int index
                            required property var modelData
                            readonly property bool selected: WindowSwitcherService.selectedIndex === index
                            readonly property real tileReveal: !Appearance.animationsEnabled ? 1 : Math.max(0, Math.min(1, (overlay.revealProgress - Math.min(8, tile.index) * 0.05) / 0.45))
                            width: 176
                            height: 112
                            radius: Appearance.rounding.normal
                            opacity: tileReveal
                            scale: 0.96 + 0.04 * tileReveal
                            color: tile.selected ? Appearance.colors.colPrimaryContainer : Appearance.colors.colSurfaceContainerHigh
                            border.width: tile.selected ? 2 : 1
                            border.color: tile.selected ? Appearance.colors.colPrimary : Appearance.colors.colOutlineVariant
                            Behavior on color {
                                ColorAnimation {
                                    duration: Appearance.animation.expressiveFastEffects.duration
                                    easing.type: Appearance.animation.expressiveFastEffects.type
                                    easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                                }
                            }
                            Behavior on border.color {
                                ColorAnimation {
                                    duration: Appearance.animation.expressiveFastEffects.duration
                                    easing.type: Appearance.animation.expressiveFastEffects.type
                                    easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                                }
                            }
                            Behavior on border.width {
                                NumberAnimation {
                                    duration: Appearance.animation.expressiveFastEffects.duration
                                    easing.type: Appearance.animation.expressiveFastEffects.type
                                    easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                                }
                            }
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8
                                Image {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: 40
                                    Layout.preferredHeight: 40
                                    source: tile.modelData.iconPath || ""
                                    sourceSize.width: 80
                                    sourceSize.height: 80
                                    fillMode: Image.PreserveAspectFit
                                    visible: source.toString().length > 0
                                }
                                MaterialSymbol {
                                    Layout.alignment: Qt.AlignHCenter
                                    visible: !(tile.modelData.iconPath || "").length
                                    text: "window"
                                    iconSize: 32
                                    color: tile.selected ? Appearance.colors.colOnPrimaryContainer : Appearance.colors.colOnLayer2
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: tile.modelData.title || tile.modelData.appName || ""
                                    color: tile.selected ? Appearance.colors.colOnPrimaryContainer : Appearance.colors.colOnLayer2
                                    font.family: Fonts.ui
                                    font.pixelSize: Appearance.scaledFont(12)
                                    font.weight: Font.Medium
                                    elide: Text.ElideRight
                                    horizontalAlignment: Text.AlignHCenter
                                    maximumLineCount: 2
                                    wrapMode: Text.Wrap
                                }
                            }
                            Accessible.role: Accessible.Button
                            Accessible.name: tile.modelData.title || tile.modelData.appName || ""
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: WindowSwitcherService.activate(tile.index)
                            }
                        }
                    }
                }
            }
        }
    }
}
