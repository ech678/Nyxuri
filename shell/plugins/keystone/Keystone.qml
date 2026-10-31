import QtQuick
import Quickshell.Io
import qs.commons
import qs.services
import qs.plugins.keystone.styles.bangs
import qs.plugins.keystone.styles.long
import qs.plugins.keystone.styles.pill
import qs.app
import qs.commons.i18n

Item {
    id: root

    readonly property bool searchActionsAvailable: styleLoader.item !== null

    function invoke(methodName): string {
        if (!styleLoader.item || typeof styleLoader.item[methodName] !== "function")
            return "KEYSTONE_UNAVAILABLE";
        return styleLoader.item[methodName]();
    }

    function openAvatarPicker(screen) {
        avatarFilePickerLoader.active = true;
        Qt.callLater(() => {
            if (avatarFilePickerLoader.item) {
                avatarFilePickerLoader.item.targetScreen = screen;
                avatarFilePickerLoader.item.openAt(avatarFilePickerLoader.item.picturesDir !== ""
                                                   ? avatarFilePickerLoader.item.picturesDir : Paths.homeDir);
            }
        });
    }

    // Unit self-registration (unit-model.md §6): keystone owns its gateway
    // presence; search intents and availability read it through
    // ActionGateway, never around it. Style selection is the appearance
    // axis — the unit's existence is the ledger's alone.
    Component.onCompleted: ActionGateway.keystoneHost = root
    Component.onDestruction: {
        if (ActionGateway.keystoneHost === root)
            ActionGateway.keystoneHost = null;
    }

    Loader {
        id: styleLoader

        sourceComponent: PersonalizationConfig.keystoneStyle === "long" ? longStyle :
                                                                          PersonalizationConfig.keystoneStyle
                                                                          === "pill" ? pillStyle : bangsStyle
    }

    Loader {
        id: avatarFilePickerLoader
        active: false

        sourceComponent: FilePickerWindow {
            dialogTitle: I18n.tr("Choose user avatar")
            description: I18n.tr(
                             "The image will be copied to ~/.face and used by the Dashboard and lock screen")
            onAccepted: path => AvatarService.setAvatar(path)
        }
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
