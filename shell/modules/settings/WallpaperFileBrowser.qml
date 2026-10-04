import QtQuick
import qs.modules.filepicker
import qs.shared.i18n

FilePickerWindow {
    id: root

    requiresParentWindow: true
    selectionMode: FilePickerWindow.FilesAndFolders
    dialogTitle: I18n.tr("Select wallpaper or folder")
    description: I18n.tr("Select an image as wallpaper or a folder as the wallpaper directory")
    windowIconName: "wallpaper"
    emptyStateText: I18n.tr("This folder contains no selectable wallpapers")
    selectionPrompt: I18n.tr("Select a wallpaper or folder")
    acceptLabel: I18n.tr("Apply")
    formatSummary: "JPG · PNG · WebP\nBMP · GIF"

    signal fileSelected(string path)
    signal folderSelected(string path)

    onAccepted: (path, isDirectory) => {
        if (isDirectory)
            root.folderSelected(path);
        else
            root.fileSelected(path);
    }
}
