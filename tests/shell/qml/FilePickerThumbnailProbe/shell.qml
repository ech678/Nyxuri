import QtQuick
import Quickshell
import qs.commons
import qs.commons.i18n
import qs.services
import qs.ui

ShellRoot {
    id: probe

    property string imageDirectory: Quickshell.env("FILEPICKER_IMAGE_DIR") || ""
    property string expectedPath: imageDirectory + "/large-000.png"
    property int readyTicks: 0
    property bool selectionVerified: false

    function fail(reason) {
        console.error("FILEPICKER_THUMBNAIL_FAIL", reason)
        Qt.exit(1)
    }

    function collectImages(item, images) {
        if (item instanceof Image)
            images.push(item)
        for (const child of item.children || [])
            collectImages(child, images)
    }

    FilePickerWindow {
        id: picker
        width: 900
        height: 580
        visible: false

        onAccepted: (path, isDirectory) => {
            if (isDirectory || path !== probe.expectedPath)
                return probe.fail("selection callback mismatch: " + path)
            probe.selectionVerified = true
        }
    }

    Timer {
        interval: 100
        repeat: true
        running: picker.visible
        onTriggered: {
            let target = null
            for (let index = 0; index < picker.fileGridView.count; ++index) {
                const delegate = picker.fileGridView.itemAtIndex(index)
                if (delegate && delegate.filePath === probe.expectedPath) {
                    target = delegate
                    break
                }
            }
            if (!target)
                return

            const images = []
            probe.collectImages(target, images)
            const image = images.find(candidate => candidate.source !== "")
            if (!image || image.status !== Image.Ready)
                return

            const maxWidth = Math.ceil(image.width * Screen.devicePixelRatio)
            const maxHeight = Math.ceil(image.height * Screen.devicePixelRatio)
            if (Quickshell.env("FILEPICKER_EXPECT_BOUNDED") === "1"
                    && (image.sourceSize.width > maxWidth || image.sourceSize.height > maxHeight))
                return probe.fail("sourceSize bound exceeded: " + image.sourceSize
                                  + " viewport=" + image.width + "x" + image.height
                                  + " dpr=" + Screen.devicePixelRatio)

            probe.readyTicks += 1
            console.log("FILEPICKER_THUMBNAIL_IMAGE", "path=" + image.source,
                        "status=" + image.status,
                        "configured_source=" + image.sourceSize.width + "x" + image.sourceSize.height,
                        "decoded=" + image.implicitWidth + "x" + image.implicitHeight,
                        "viewport=" + image.width + "x" + image.height,
                        "dpr=" + Screen.devicePixelRatio)
            if (probe.readyTicks < 20)
                return

            picker.selectEntry(probe.expectedPath, "large-000.png", false)
            picker.acceptSelection()
            if (!probe.selectionVerified)
                return probe.fail("selection callback not observed")
            console.log("FILEPICKER_THUMBNAIL_PASS", "ready=" + image.status,
                        "selection=" + probe.expectedPath)
            Qt.quit()
        }
    }

    Component.onCompleted: {
        if (probe.imageDirectory === "")
            return probe.fail("FILEPICKER_IMAGE_DIR is required")
        picker.openAt(probe.imageDirectory)
    }
}
