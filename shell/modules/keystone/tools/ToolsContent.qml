import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import qs.shared.theme
import qs.shared.controls
import qs.app
import qs.app.services
import qs.shared.i18n

Item {
    id: toolsRoot

    property bool vertical: false
    property string edge: "top"
    property string popupEdge: edge
    property bool retainForRecording: false
    readonly property int buttonSize: 48
    readonly property int buttonSpacing: 40
    readonly property int buttonsExtent: toolsModel.length * buttonSize + Math.max(0, toolsModel.length - 1) * buttonSpacing
    readonly property int crossExtent: 72
    property var toolsModel: [
        {
            "action": "screenshot",
            "icon": "photo_camera",
            "tip": I18n.tr("Screenshot")
        },
        {
            "action": "color-picker",
            "icon": "colorize",
            "tip": I18n.tr("Color picker")
        },
        {
            "action": "record-video",
            "icon": "videocam",
            "tip": I18n.tr("Screen recording")
        },
        {
            "action": "record-gif",
            "icon": "gif",
            "tip": I18n.tr("Record GIF")
        },
        {
            "action": "audio-mic",
            "icon": "mic",
            "tip": I18n.tr("Record microphone")
        },
        {
            "action": "audio-system",
            "icon": "speaker",
            "tip": I18n.tr("Record system audio")
        }
    ]
    property int selectedIndex: 0

    signal requestHideKeystone
    signal recordingRequested

    function triggerSelected() {
        const tool = toolsModel[selectedIndex];
        if (!tool)
            return;

        const recordingTool = tool.action === "record-video" || tool.action === "record-gif" || tool.action === "audio-mic" || tool.action === "audio-system";
        if (recordingTool && retainForRecording)
            toolsRoot.recordingRequested();
        else
            toolsRoot.requestHideKeystone();
        switch (tool.action) {
        case "screenshot":
            ActionGateway.execute(["niri", "msg", "action", "screenshot"], "keystone");
            break;
        case "color-picker":
            ActionGateway.execute(["hyprpicker", "-a"], "keystone");
            break;
        case "record-video":
            RecordingService.start("video", {
                "audio": "none",
                "fps": 60,
                "output": UiPreferences.recordingVideoDirectory
            });
            break;
        case "record-gif":
            RecordingService.start("gif", {
                "audio": "none",
                "fps": 60,
                "output": UiPreferences.recordingGifDirectory
            });
            break;
        case "audio-mic":
            AudioRecordingService.start("mic", {
                "output": UiPreferences.recordingMicrophoneDirectory
            });
            break;
        case "audio-system":
            AudioRecordingService.start("system", {
                "output": UiPreferences.recordingSystemAudioDirectory
            });
            break;
        default:
            console.warn("[Tools] backend unavailable", tool.action);
        }
    }

    function stopRecording() {
        RecordingService.stop();
    }

    function stopAudio() {
        AudioRecordingService.stop();
    }

    implicitWidth: vertical ? crossExtent : buttonsExtent
    implicitHeight: vertical ? buttonsExtent : crossExtent
    property bool keyboardActive: visible
    enabled: keyboardActive
    focus: keyboardActive
    onKeyboardActiveChanged: {
        if (keyboardActive) {
            selectedIndex = 0;
            forceActiveFocus();
        }
    }
    Keys.onLeftPressed: {
        selectedIndex = (selectedIndex - 1 + toolsModel.length) % toolsModel.length;
    }
    Keys.onRightPressed: {
        selectedIndex = (selectedIndex + 1) % toolsModel.length;
    }
    Keys.onUpPressed: {
        if (toolsRoot.vertical)
            selectedIndex = (selectedIndex - 1 + toolsModel.length) % toolsModel.length;
    }
    Keys.onDownPressed: {
        if (toolsRoot.vertical)
            selectedIndex = (selectedIndex + 1) % toolsModel.length;
    }
    Keys.onReturnPressed: triggerSelected()
    Keys.onEnterPressed: triggerSelected()

    Grid {
        anchors.centerIn: parent
        spacing: toolsRoot.buttonSpacing
        columns: toolsRoot.vertical ? 1 : toolsRoot.toolsModel.length

        Repeater {
            model: toolsRoot.toolsModel

            IconButton {
                controlSize: toolsRoot.buttonSize
                iconName: modelData.icon
                iconSize: 22
                iconColor: Appearance.colors.colOnSurface
                selectedIconColor: Appearance.colors.colOnSurface
                accessibleName: modelData.tip
                selected: index === toolsRoot.selectedIndex
                selectedContainerColor: Appearance.colors.colLayer2Hover
                selectedHoverStateLayerColor: Appearance.colors.colLayer2Hover
                selectedPressedStateLayerColor: Appearance.colors.colLayer2Active
                hoverStateLayerColor: Appearance.colors.colLayer2Hover
                pressedStateLayerColor: Appearance.colors.colLayer2Active
                onPointerHoveredChanged: {
                    if (pointerHovered)
                        toolsRoot.selectedIndex = index;
                }
                onClicked: {
                    toolsRoot.selectedIndex = index;
                    toolsRoot.triggerSelected();
                }
            }
        }
    }
}
