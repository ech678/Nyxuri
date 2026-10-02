import QtQuick
import Quickshell.Io
import qs.shared.theme
import qs.app.services
import qs.modules.filepicker
import qs.modules.keystone.styles.bangs
import qs.modules.keystone.styles.long
import qs.modules.keystone.styles.pill
import qs.app

Item {
    id: root

    readonly property bool searchActionsAvailable: styleLoader.item !== null

    function invoke(methodName): string {
        if (!styleLoader.item || typeof styleLoader.item[methodName] !== "function")
            return "KEYSTONE_UNAVAILABLE";
        return styleLoader.item[methodName]();
    }

    function openAvatarPicker(screen) {
        avatarFilePicker.targetScreen = screen;
        Qt.callLater(() => avatarFilePicker.openAt(avatarFilePicker.picturesDir !== ""
                                                   ? avatarFilePicker.picturesDir : Paths.homeDir));
    }

    Loader {
        id: styleLoader
        active: PersonalizationConfig.keystoneEnabled

        sourceComponent: PersonalizationConfig.keystoneStyle === "long" ? longStyle :
                                                                          PersonalizationConfig.keystoneStyle
                                                                          === "pill" ? pillStyle : bangsStyle
    }

    FilePickerWindow {
        id: avatarFilePicker

        dialogTitle: qsTr("Choose user avatar")
        description: qsTr("The image will be copied to ~/.face and used by the Dashboard and lock screen")
        onAccepted: path => AvatarService.setAvatar(path)
    }

    IpcHandler {
        target: "keystone"

        function cancelRecord(): string {
            return root.invoke("cancelRecord");
        }
        function closeAllOthers(): string {
            return root.invoke("closeAllOthers");
        }
        function currentStyle(): string {
            return PersonalizationConfig.keystoneStyle;
        }
        function dashboard(): string {
            return root.invoke("dashboard");
        }
        function hub(): string {
            return root.invoke("hub");
        }
        function lyrics(): string {
            return root.invoke("lyrics");
        }
        function tools(): string {
            return root.invoke("tools");
        }
    }

    Component {
        id: bangsStyle

        Bangs {
            onAvatarEditRequested: screen => root.openAvatarPicker(screen)
        }
    }

    Component {
        id: pillStyle

        Pill {
            onAvatarEditRequested: screen => root.openAvatarPicker(screen)
        }
    }
    Component {
        id: longStyle

        Long {
            onAvatarEditRequested: screen => root.openAvatarPicker(screen)
        }
    }
}
