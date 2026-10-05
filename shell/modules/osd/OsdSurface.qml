import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Variants {
    id: root

    model: Quickshell.screens

    delegate: PanelWindow {
        id: osdWindow
        required property var modelData
        readonly property bool targeted: NiriService.currentOutput === "" || NiriService.currentOutput === modelData.name
        readonly property string label: {
            if (OsdService.kind === "brightness")
                return I18n.tr("Brightness");
            if (OsdService.kind === "muted")
                return I18n.tr("Muted");
            return I18n.tr("Volume");
        }
        readonly property string icon: OsdService.kind === "brightness" ? "brightness_6" : OsdService.muted ? "volume_off" : "volume_up"
        readonly property real ratio: OsdService.muted ? 0 : OsdService.value
        property bool holding: false
        Connections {
            target: OsdService
            function onVisibleChanged() {
                if (OsdService.visible) {
                    if (osdWindow.targeted)
                        osdWindow.holding = true;
                    return;
                }
                if (!Appearance.animationsEnabled) {
                    osdWindow.holding = false;
                    return;
                }
                osdWindow.releaseTimer.restart();
            }
        }
        Timer {
            id: releaseTimer
            interval: Appearance.animation.expressiveFastSpatial.duration + 40
            onTriggered: osdWindow.holding = false
        }
        screen: modelData
        visible: (OsdService.visible || holding) && targeted
        color: "transparent"
        exclusiveZone: 0
        WlrLayershell.namespace: "nyxuri-shell-osd"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.exclusionMode: ExclusionMode.Ignore
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        anchors {
            bottom: true
        }
        margins {
            bottom: 96
        }
        implicitWidth: pill.width
        implicitHeight: pill.height
        Rectangle {
            id: pill
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: 240
            height: 56
            radius: Appearance.rounding.full
            color: Appearance.applyAlpha(Appearance.colors.colLayer2, Appearance.backgroundOpacity)
            border.width: 1
            border.color: Appearance.colors.colOutline
            property real revealProgress: OsdService.visible ? 1 : 0
            opacity: pill.revealProgress
            scale: 0.96 + 0.04 * pill.revealProgress
            transform: Translate {
                y: Appearance.animationsEnabled ? (1 - pill.revealProgress) * 14 : 0
            }
            Behavior on revealProgress {
                enabled: Appearance.animationsEnabled
                NumberAnimation {
                    duration: Appearance.animation.expressiveFastSpatial.duration
                    easing.type: Appearance.animation.expressiveFastSpatial.type
                    easing.bezierCurve: Appearance.animation.expressiveFastSpatial.bezierCurve
                }
            }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                spacing: 12
                MaterialSymbol {
                    text: osdWindow.icon
                    iconSize: 22
                    color: Appearance.colors.colOnLayer2
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text {
                        Layout.fillWidth: true
                        text: osdWindow.label
                        color: Appearance.colors.colOnLayer2
                        font.family: Fonts.ui
                        font.pixelSize: Appearance.scaledFont(12)
                        font.weight: Font.Medium
                        elide: Text.ElideRight
                    }
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 8
                        Rectangle {
                            anchors.fill: parent
                            radius: Appearance.rounding.full
                            color: Appearance.colors.colSurfaceContainerHighest
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(8, parent.width * osdWindow.ratio)
                            height: parent.height
                            radius: Appearance.rounding.full
                            color: Appearance.colors.colPrimary
                            Behavior on width {
                                enabled: Appearance.animationsEnabled
                                NumberAnimation {
                                    duration: Appearance.animation.expressiveFastEffects.duration
                                    easing.type: Appearance.animation.expressiveFastEffects.type
                                    easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                                }
                            }
                        }
                    }
                }
                Text {
                    text: Math.round(osdWindow.ratio * 100) + "%"
                    color: Appearance.colors.colOnLayer2
                    font.family: Fonts.numeric
                    font.pixelSize: Appearance.scaledFont(12)
                    font.weight: Font.Medium
                }
            }
            Accessible.role: Accessible.Alert
            Accessible.name: osdWindow.label
        }
    }
}
