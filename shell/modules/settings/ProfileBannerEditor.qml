import QtQuick
import qs.app.services
import qs.modules.wallpaper
import qs.modules.filepicker
import qs.shared.i18n

Item {
    id: root
    property var parentModal: null
    readonly property string previewSource: WallpaperPaletteSession.previewForScreen("banner", "")
    readonly property string source: PersonalizationConfig.bannerSource || WallpaperService.currentWallpaper

    function chooseFile() {
        filePicker.openAt(WallpaperService.isImagePath(root.source) ? WallpaperService.parentFolder(
                                                                          root.source) :
                                                                      PersonalizationConfig.wallpaperFolder);
    }
    function chooseColor() {
        colorPicker.showFor("banner", "");
    }
    function clear() {
        PersonalizationConfig.setBannerSource("");
    }
    function close() {
        filePicker.dismiss();
        colorPicker.close();
    }
    WallpaperFileBrowser {
        id: filePicker
        parentModal: root.parentModal
        selectionMode: FilePickerWindow.Files
        dialogTitle: I18n.tr("Choose banner image", "AccountProfileHeader")
        description: ""
        selectionPrompt: dialogTitle
        onFileSelected: path => PersonalizationConfig.setBannerSource(path)
    }
    WallpaperColorPicker {
        id: colorPicker
        parentModal: root.parentModal
    }
}
