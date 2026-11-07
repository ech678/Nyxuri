import QtQuick
import qs.commons
import qs.services
import "../../commons/WallpaperSource.js" as WallpaperSource
import qs.commons.i18n

Item {
    id: root
    property var parentModal: null
    readonly property string previewSource: ""
    readonly property string source: PersonalizationConfig.bannerSource || (ActionGateway.wallpaperHost ? ActionGateway.wallpaperHost.currentWallpaper : "")

    function chooseFile() {
        const parentFolder = root.source.substring(0, root.source.lastIndexOf("/"));
        filePicker.openAt(WallpaperSource.isImage(root.source) ? parentFolder : PersonalizationConfig.wallpaperFolder);
    }
    function chooseColor() {
        if (colorPickerLoader.item)
            colorPickerLoader.item.showFor("banner", "");
    }
    function clear() {
        PersonalizationConfig.setBannerSource("");
    }
    function close() {
        filePicker.dismiss();
        if (colorPickerLoader.item)
            colorPickerLoader.item.close();
    }
    FilePickerWindow {
        id: filePicker
        parentWindow: root.parentModal
        requiresParentWindow: true
        selectionMode: FilePickerWindow.Files
        dialogTitle: I18n.tr("Choose banner image", "AccountProfileHeader")
        description: ""
        selectionPrompt: dialogTitle
        onAccepted: (path, isDirectory) => {
            if (!isDirectory)
                PersonalizationConfig.setBannerSource(path);
        }
    }
    Loader {
        id: colorPickerLoader
        active: StateProjection.isEnabled("wallpaper")
        source: Qt.resolvedUrl("../wallpaper/WallpaperColorPicker.qml")
        onLoaded: {
            if (item)
                item.parentModal = root.parentModal;
        }
    }
}
