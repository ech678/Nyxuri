import QtQuick
import qs.app.services
import qs.modules.filepicker

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
        dialogTitle: qsTranslate("AccountProfileHeader", "Choose banner image")
        description: ""
        selectionPrompt: dialogTitle
        onFileSelected: path => PersonalizationConfig.setBannerSource(path)
    }
    WallpaperColorPicker {
        id: colorPicker
        parentModal: root.parentModal
    }
}
