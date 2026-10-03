import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.shared.theme
import qs.app.services

Item {
    id: root

    property bool locked: false
    signal triggered(string action, string screenName)

    // The compositor owns its native corners until the user explicitly sets
    // up the managed integration. Never compete with its overview gesture.
    Variants {
        model: NiriConfigService.ready("hot-corners") ? Quickshell.screens : []

        Scope {
            id: output

            required property var modelData

            Variants {
                model: PersonalizationConfig.hotCornerIds

                PanelWindow {
                    id: corner

                    required property string modelData
                    readonly property string action: PersonalizationConfig.hotCornerActions[modelData]
                                                     || "disabled"
                    readonly property bool blocked: !NiriService.connected || root.locked

                    screen: output.modelData
                    implicitWidth: Metrics.hotCornerSize
                    implicitHeight: Metrics.hotCornerSize
                    color: "transparent"
                    visible: action !== "disabled"
                    exclusionMode: ExclusionMode.Ignore
                    WlrLayershell.layer: WlrLayer.Overlay
                    WlrLayershell.namespace: "clavis-shell-hot-corner"
                    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

                    anchors {
                        top: corner.modelData.startsWith("top-")
                        bottom: corner.modelData.startsWith("bottom-")
                        left: corner.modelData.endsWith("-left")
                        right: corner.modelData.endsWith("-right")
                    }

                    // Other shell surfaces exclude these corners from their
                    // input masks, so opening a sidebar cannot synthesize a
                    // leave/enter cycle or consume the next physical entry.
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                        onEntered: {
                            if (!corner.blocked)
                                root.triggered(corner.action, corner.screen.name);
                        }
                    }
                }
            }
        }
    }
}
