import QtQuick
import Quickshell.Io
import qs.commons
import qs.services
import "styles/bangs"
import "styles/long"
import "styles/pill"
import qs.commons.i18n

Item {
    id: root

    readonly property bool searchActionsAvailable: styleLoader.item !== null

    function invoke(methodName): string {
        if (!styleLoader.item || typeof styleLoader.item[methodName] !== "function")
            return "ISLAND_UNAVAILABLE";
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

    // Unit self-registration (unit-model.md §6): island owns its gateway
    // presence; search intents and availability read it through
    // ActionGateway, never around it. Style selection is the appearance
    // axis — the unit's existence is the ledger's alone.
    Component.onCompleted: ActionGateway.islandHost = root
    Component.onDestruction: {
        if (ActionGateway.islandHost === root)
            ActionGateway.islandHost = null;
    }

    Loader {
        id: styleLoader

        sourceComponent: PersonalizationConfig.islandStyle === "long" ? longStyle :
                                                                          PersonalizationConfig.islandStyle
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
        target: "island"

        function cancelRecord(): string {
            return root.invoke("cancelRecord");
        }
        function closeAllOthers(): string {
            return root.invoke("closeAllOthers");
        }
        function currentStyle(): string {
            return PersonalizationConfig.islandStyle;
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
