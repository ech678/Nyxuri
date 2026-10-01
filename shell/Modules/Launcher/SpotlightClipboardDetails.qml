pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.common
import "../../Common/functions/FileUtils.js" as FileUtils

ColumnLayout {
    id: root
    required property string entryId
    property bool canRestore: true
    property bool actionRunning: false
    property string actionError: ""
    property string requestedId: ""
    property bool waiting: false
    property string failure: ""
    readonly property var detail: {
        const revision = ClipboardService.detailsRevision;
        return ClipboardService.detail(entryId);
    }
    readonly property string kind: detail ? String(detail.payloadKind || "binary") : ""
    readonly property var files: detail && Array.isArray(detail.files) ? detail.files : []
    readonly property var singleFile: files.length === 1 ? files[0] : null
    readonly property string imageUrl: {
        if (waiting || failure !== "")
            return "";
        const candidate = kind === "image" ? String(detail.previewUrl || "") : singleFile
                                             && singleFile.readable && singleFile.local ? String(
                                                                                              singleFile.previewUrl
                                                                                              || "") : "";
        const mime = kind === "image" ? detail.mimeType : singleFile ? singleFile.mimeType : "";
        return ["image/png", "image/jpeg", "image/gif", "image/webp"].indexOf(mime) >= 0 && candidate.indexOf(
                    "file:///") === 0 ? candidate : "";
    }
    readonly property bool imageFailed: imagePreview.item ? imagePreview.item.loadFailed : false
    signal restoreRequested
    signal routedKey(var event)
    spacing: 10

    function selectEntry() {
        selectionDelay.stop();
        if (requestedId !== "")
            ClipboardService.releasePriorityInspect(requestedId);
        requestedId = "";
        failure = "";
        const cached = ClipboardService.detail(entryId);
        waiting = entryId !== "" && (!cached || cached.payloadKind === "file" || cached.payloadKind
                                     === "file-list");
        if (waiting)
            selectionDelay.restart();
    }
    onEntryIdChanged: selectEntry()
    Component.onCompleted: selectEntry()
    Component.onDestruction: {
        if (requestedId !== "")
            ClipboardService.releasePriorityInspect(requestedId);
    }
    Timer {
        id: selectionDelay
        interval: 70
        onTriggered: {
            root.requestedId = root.entryId;
            ClipboardService.inspect(root.entryId, true, true);
        }
    }
    Connections {
        target: ClipboardService
        function onInspected(id) {
            if (id !== root.entryId)
                return;
            root.waiting = false;
            root.failure = "";
        }
        function onInspectFailed(id, code, message) {
            if (id !== root.entryId)
                return;
            root.waiting = false;
            root.failure = message;
        }
    }

    function fileStatus(file) {
        if (!file.local)
            return qsTr("Remote location not read");
        if (file.metadataStatus === "missing" || (!file.metadataStatus && !file.exists))
            return qsTr("File no longer exists");
        if (file.metadataStatus === "unreadable" || !file.readable)
            return qsTr("Unable to read file");
        if (file.metadataStatus === "unavailable")
            return qsTr("Metadata unavailable");
        return "";
    }
    function fileDescription(file) {
        const parts = [file.directory ? qsTr("Folder") : (file.mimeType || qsTr("File"))];
        if (file.sizeKnown === true && !file.directory)
            parts.push(FileUtils.humanReadableSize(file.byteSize));
        const status = fileStatus(file);
        if (status !== "")
            parts.push(status);
        return parts.join(" · ");
    }
    function metadata() {
        if (!detail || waiting || failure !== "")
            return "";
        const parts = [];
        if (kind === "text") {
            if (typeof detail.characterCount === "number")
                parts.push(qsTr("Characters: %1").arg(detail.characterCount));
            if (typeof detail.textLineCount === "number")
                parts.push(qsTr("Lines: %1").arg(detail.textLineCount));
            if (typeof detail.byteSize === "number")
                parts.push(qsTr("Size: %1").arg(FileUtils.humanReadableSize(detail.byteSize)));
        } else if (singleFile) {
            parts.push(fileDescription(singleFile));
            parts.push(singleFile.parent || singleFile.uri);
            if (typeof singleFile.modifiedTime === "number") {
                const date = new Date(singleFile.modifiedTime * 1000);
                parts.push(qsTr("Modified: %1 %2").arg(date.toLocaleDateString(Qt.locale(),
                                                                               Locale.ShortFormat)).arg(
                               UiPreferences.shortTime(date)));
            }
        } else if (kind === "image" || kind === "binary") {
            parts.push(detail.mimeType || qsTr("Binary clipboard content"));
            if (detail.width > 0 && detail.height > 0)
                parts.push(qsTr("%1 × %2").arg(detail.width).arg(detail.height));
            if (typeof detail.byteSize === "number")
                parts.push(FileUtils.humanReadableSize(detail.byteSize));
        }
        return parts.join(" · ");
    }

    Item {
        id: previewArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        clip: true

        Text {
            anchors.centerIn: parent
            width: Math.max(0, parent.width - 20)
            visible: root.entryId === "" || root.waiting || root.failure !== "" || !root.detail || (root.kind
                                                                                                    === "binary")
                     || (root.kind === "image" && root.imageUrl === "")
            text: root.entryId === "" ? qsTr("Select an entry") : root.waiting ? qsTr("Reading…") :
                                                                                 root.failure !== ""
                                                                                 ? root.failure : qsTr(
                                                                                       "Preview unavailable")
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            horizontalAlignment: Text.AlignHCenter
            color: Appearance.colors.colOnSurfaceVariant
            font.family: Fonts.ui
        }
        Loader {
            anchors.fill: parent
            active: root.kind === "text" && !root.waiting && root.failure === ""
            sourceComponent: Flickable {
                id: textScroll
                clip: true
                contentWidth: width
                contentHeight: body.height
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: StyledScrollBar {}
                Connections {
                    target: root
                    function onEntryIdChanged() {
                        textScroll.contentY = 0;
                    }
                }
                TextEdit {
                    id: body
                    width: Math.max(0, textScroll.width - 16)
                    height: Math.max(textScroll.height, contentHeight)
                    text: root.detail ? String(root.detail.searchText !== undefined ? root.detail.searchText :
                                                                                      root.detail.preview
                                                                                      || "") : ""
                    textFormat: TextEdit.PlainText
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    color: Appearance.colors.colOnSurface
                    selectedTextColor: Appearance.m3colors.m3onPrimary
                    selectionColor: Appearance.m3colors.m3primary
                    font.family: Fonts.ui
                    font.pixelSize: 14
                    // Text selection/copy stays local. Navigation and mode keys
                    // propagate to the existing Spotlight focus router.
                    Keys.priority: Keys.BeforeItem
                    Keys.onPressed: event => {
                        if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
                            body.copy();
                            event.accepted = true;
                        } else {
                            root.routedKey(event);
                        }
                    }
                }
            }
        }
        Loader {
            id: imagePreview
            anchors.fill: parent
            active: root.imageUrl !== ""
            sourceComponent: Rectangle {
                readonly property bool loadFailed: picture.status === Image.Error
                visible: !loadFailed || !root.singleFile
                color: Appearance.colors.colLayer2
                radius: Appearance.rounding.normal
                Image {
                    id: picture
                    anchors.fill: parent
                    anchors.margins: 8
                    source: decodeReady ? root.imageUrl : ""
                    asynchronous: true
                    cache: false
                    currentFrame: 0
                    fillMode: Image.PreserveAspectFit
                    // Start only after layout settles, avoiding an initial decode
                    // at a placeholder size followed by another decode 250 ms later.
                    // Retain pixels only for resizing the same source, never when
                    // selection changes to a different clipboard image.
                    property bool decodeReady: false
                    property string loadedSource: ""
                    retainWhileLoading: source.toString() === loadedSource
                    onStatusChanged: {
                        if (status === Image.Ready)
                            loadedSource = source.toString();
                    }
                    // Quantize and settle the decode budget after resize animations.
                    property int decodeSize: Math.min(2048, Math.max(256, Math.ceil(Math.max(width, height)
                                                                                    * Screen.devicePixelRatio
                                                                                    / 256) * 256))
                    property int settledSize: 1024
                    onDecodeSizeChanged: resizeDelay.restart()
                    Component.onCompleted: resizeDelay.restart()
                    Timer {
                        id: resizeDelay
                        interval: 250
                        onTriggered: {
                            picture.settledSize = picture.decodeSize;
                            picture.decodeReady = true;
                        }
                    }
                    sourceSize: Qt.size(settledSize, settledSize)
                }
                Text {
                    anchors.centerIn: parent
                    visible: picture.status === Image.Error
                    text: qsTr("Preview unavailable")
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Fonts.ui
                }
            }
        }
        Column {
            anchors.centerIn: parent
            width: Math.max(0, Math.min(parent.width - 24, 360))
            spacing: 12
            visible: root.singleFile !== null && (root.imageUrl === "" || root.imageFailed) && !root.waiting
                     && root.failure === ""

            FileThemeIcon {
                active: parent.visible
                category: root.singleFile ? String(root.singleFile.category || "") : ""
                anchors.horizontalCenter: parent.horizontalCenter
                iconSize: Math.max(0, Math.min(112, previewArea.height - fileNameLabel.height - (
                                                   imageErrorLabel.visible ? imageErrorLabel.height : 0)
                                               - 24))
                width: iconSize
                height: iconSize
                entryKey: root.entryId
                themeIcon: root.singleFile ? String(root.singleFile.themeIcon || "") : ""
                mimeType: root.singleFile ? String(root.singleFile.mimeType || "") : ""
                directory: root.singleFile ? root.singleFile.directory === true : false
                fallbackSymbol: root.singleFile ? String(root.singleFile.icon || "draft") : "draft"
            }
            Text {
                id: fileNameLabel
                width: parent.width
                text: root.singleFile ? String(root.singleFile.name || root.singleFile.uri) : ""
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                maximumLineCount: 3
                elide: Text.ElideMiddle
                horizontalAlignment: Text.AlignHCenter
                color: Appearance.colors.colOnSurface
                font.family: Fonts.ui
                font.pixelSize: 16
                ToolTip.visible: truncated && fileNameHover.hovered
                ToolTip.text: text
                HoverHandler {
                    id: fileNameHover
                }
            }
            Text {
                id: imageErrorLabel
                width: parent.width
                visible: root.imageFailed
                text: qsTr("Preview unavailable")
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
            }
        }
        ListView {
            anchors.fill: parent
            visible: root.files.length > 1 && !root.waiting && root.failure === ""
            clip: true
            model: visible ? root.files : []
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: StyledScrollBar {}
            header: Text {
                width: ListView.view.width
                visible: root.files.length > 1
                height: visible ? implicitHeight + 12 : 0
                text: qsTr("%n file(s)", "", root.files.length)
                color: Appearance.colors.colOnSurface
                font.family: Fonts.ui
            }
            delegate: Column {
                required property var modelData
                width: ListView.view.width - 16
                spacing: 4
                Text {
                    width: parent.width
                    text: parent.modelData.name || parent.modelData.uri
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: Appearance.colors.colOnSurface
                    font.family: Fonts.ui
                }
                Text {
                    width: parent.width
                    visible: root.files.length > 1
                    text: root.fileDescription(parent.modelData)
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Fonts.ui
                }
                Item {
                    width: 1
                    height: 12
                }
            }
        }
    }
    Text {
        Layout.fillWidth: true
        visible: root.kind === "text" && !root.waiting && root.failure === "" && (!root.detail || root.detail.textTruncated
                                                                                  !== false)
        text: root.detail && root.detail.textTruncated === true ? qsTr(
                                                                      "Showing the first %1 of %2 characters. Restoring copies the full content.").arg(
                                                                      root.detail.detailTextLimit).arg(
                                                                      root.detail.characterCount) : qsTr(
                                                                      "Preview")
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
        color: Appearance.colors.colOnSurfaceVariant
        font.family: Fonts.ui
        font.pixelSize: 12
    }
    Text {
        Layout.fillWidth: true
        text: root.metadata()
        visible: text !== ""
        wrapMode: Text.WrapAnywhere
        maximumLineCount: 4
        elide: Text.ElideMiddle
        textFormat: Text.PlainText
        color: Appearance.colors.colOnSurfaceVariant
        font.family: Fonts.ui
        font.pixelSize: 12
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 10

        Text {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: root.actionError
            maximumLineCount: 1
            elide: Text.ElideRight
            textFormat: Text.PlainText
            color: Appearance.colors.colError
            font.family: Fonts.ui
            ToolTip.visible: truncated && errorHover.hovered
            ToolTip.text: text
            HoverHandler {
                id: errorHover
            }
        }
        ActionButton {
            text: qsTr("Restore to clipboard")
            iconName: "content_paste"
            enabled: root.entryId !== "" && root.canRestore && !root.actionRunning && (!root.detail
                                                                                       || root.detail.restorable
                                                                                       !== false)
            onClicked: root.restoreRequested()
        }
    }
}
