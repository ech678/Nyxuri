pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import Clavis.Files
import qs.shared.theme
import qs.shared.controls
import qs.app.services

Item {
    id: root
    required property string entryKey
    property real maximumWidth: 600
    property real maximumHeight: 600
    property bool contextMenu: false
    property string edge: "bottom"
    property real anchorOffset: width / 2
    property point sourceCenter: Qt.point(anchorOffset, height + 32)
    property real iconSize: 64
    property real maximumFanOutset: Infinity
    property bool labelsLeft: true
    readonly property var entry: {
        const revision = DockService.revision;
        return DockService.entryFor(entryKey);
    }
    property string browsingUrl: ""
    readonly property string currentUrl: browsingUrl || (entry && entry.url || "")
    property var history: []
    property bool confirmEmpty: false
    property var menuSurfaces: []
    readonly property bool fan: !contextMenu && !!entry && entry.view === "fan"
    readonly property bool list: !contextMenu && !!entry && entry.view === "list"
    readonly property bool hovered: fan ? fanView.hovered : list ? menuSurfaces.some(item => item
                                                                                             && item.menuHovered) :
                                                                   hover.hovered
    readonly property bool directoryAvailable: !!directory.item && directory.item.available
    readonly property int count: directory.item ? directory.item.count : 0
    property bool presented: false
    property bool closing: false
    readonly property int fanCount: fanView.geometry.count
    readonly property real fanIconInset: fanView.geometry.iconInset
    readonly property var fanItems: fanView.tiles
    readonly property var inputItems: !visible ? [] : list ? menuSurfaces : fan ? [fanView] : [root]
    readonly property var blurBackgroundItems: {
        if (!visible || fan)
            return [];
        if (!list)
            return bubble.blurItems;
        let items = [];
        for (const surface of menuSurfaces)
            if (surface)
                items = items.concat(surface.blurItems);
        return items;
    }
    readonly property var blurRegions: visible && fan ? fanView.blurRegions : []
    property real progress: 0
    readonly property int gridColumns: Math.max(1, Math.floor(grid.width / 106))
    readonly property int gridRows: Math.max(1, Math.min(4, Math.ceil((count + 1) / gridColumns)))
    signal dismissed
    width: fan ? fanView.implicitWidth : Math.min(maximumWidth, contextMenu ? 300 : 360)
    height: fan ? fanView.implicitHeight : list ? Math.min(480, maximumHeight, (Math.max(1, count) + 1) * 34
                                                           + 28 + (edge === "bottom" ? 10 : 0)) : contextMenu
                                                  ? Math.min(maximumHeight, menuColumn.height + 26) : Math.min(
                                                        maximumHeight, 20 + (edge === "bottom"
                                                                             ? bubble.tailSize : 0)
                                                        + header.implicitHeight + gridRows * grid.cellHeight)
    onEntryKeyChanged: {
        browsingUrl = "";
        history = [];
        confirmEmpty = false;
    }
    onVisibleChanged: {
        resetPresentation();
        if (!visible) {
            confirmEmpty = false;
            history = [];
            browsingUrl = "";
        }
    }
    onCurrentUrlChanged: resetPresentation()
    onFanChanged: resetPresentation()
    function resetPresentation() {
        closing = false;
        opening.stop();
        progress = 0;
        presented = false;
        Qt.callLater(root.presentContent);
    }
    function presentContent() {
        if (!root.visible || (root.list || root.contextMenu) || !directory.item || !directory.item.ready
                || presented)
            return;
        // Start once after a complete listing; live changes use ListView's
        // normal model updates and do not replay the opening animation.
        presented = true;
        opening.start();
    }
    function closePopup() {
        if (contextMenu)
            return false;
        if (closing)
            return true;
        if (list && nativeList.item && nativeList.item.visible) {
            closing = true;
            nativeList.item.close();
            return true;
        }
        if (!list && progress > 0) {
            closeContent();
            return true;
        }
        return false;
    }
    function closeContent() {
        if (closing)
            return;
        opening.stop();
        closing = true;
        opening.start();
    }
    function reopenPopup() {
        if (list && nativeList.item) {
            closing = false;
            nativeList.item.open();
            return;
        }
        opening.stop();
        closing = false;
        opening.start();
    }
    function presentList() {
        if (root.visible && root.list && !root.closing && directory.item && directory.item.ready
                && nativeList.item && !nativeList.item.visible)
            nativeList.item.open();
    }
    NumberAnimation {
        id: opening
        target: root
        property: "progress"
        to: root.closing ? 0 : 1
        duration: root.closing ? 180 : root.fan ? 260 : Appearance.animation.expressiveEffects.duration
        easing.type: root.fan ? Easing.OutCubic : Appearance.animation.expressiveEffects.type
        easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
        onFinished: {
            if (root.closing)
                root.dismissed();
        }
    }
    HoverHandler {
        id: hover
        enabled: !root.fan && !root.list
    }
    function open(info) {
        if (!DesktopFiles.info(info.url).available) {
            DockService.fileError = qsTranslate("DockService", "This file or folder is unavailable.");
            return;
        }
        if (info.isDirectory) {
            history = history.concat([currentUrl]);
            browsingUrl = String(info.url);
        } else {
            ApplicationService.openUrl(info.url);
            dismissed();
        }
    }
    Loader {
        id: directory
        active: root.visible && !root.contextMenu && !!root.entry && root.entry.kind === "folder"
        onLoaded: Qt.callLater(root.presentContent)
        sourceComponent: DockFolderModel {
            folder: root.currentUrl
            sort: root.entry.sort
        }
    }
    Connections {
        target: directory.item
        function onReadyChanged() {
            Qt.callLater(root.presentContent);
            Qt.callLater(root.presentList);
        }
        function onRevisionChanged() {
            Qt.callLater(root.presentContent);
        }
    }
    Loader {
        id: nativeList
        active: root.visible && root.list
        onLoaded: Qt.callLater(root.presentList)
        sourceComponent: DockFolderMenu {
            parent: root
            x: 0
            y: 0
            width: root.width
            edge: root.edge
            anchorOffset: root.anchorOffset
            sharedModel: directory.item
            folderUrl: root.currentUrl
            sort: root.entry.sort
            maximumHeight: root.maximumHeight
            onSurfacesChanged: root.menuSurfaces = surfaces()
            onAboutToHide: root.closing = true
            onClosed: {
                if (root.visible && root.list)
                    root.dismissed();
            }
            onFileActivated: info => {
                ApplicationService.openUrl(info.url);
                root.closePopup();
            }
        }
    }
    DockFolderFan {
        id: fanView
        anchors.fill: parent
        visible: root.fan && root.presented
        enabled: !root.closing
        model: root.presented && directory.item ? directory.item.model : null
        count: root.presented ? root.count : 0
        edge: root.edge
        labelsLeft: root.labelsLeft
        maximumWidth: root.maximumWidth
        maximumHeight: root.maximumHeight
        maximumOutset: root.maximumFanOutset
        iconSize: root.iconSize
        sourceCenter: root.sourceCenter
        progress: root.progress
        canOpen: root.directoryAvailable
        canGoBack: root.history.length > 0
        actionText: root.history.length && directory.item ? directory.item.info.name : !root.directoryAvailable
                                                            ? qsTr("Folder is unavailable") : root.count
                                                              ? qsTr("Open in File Manager") : qsTr(
                                                                    "Folder is empty")
        onActivated: info => root.open(info)
        onOpenRequested: {
            ApplicationService.openUrl(root.currentUrl);
            root.dismissed();
        }
        onBackRequested: {
            root.browsingUrl = root.history[root.history.length - 1];
            root.history = root.history.slice(0, -1);
        }
    }
    Item {
        id: card
        anchors.fill: parent
        visible: !root.fan && !root.list && (root.contextMenu || root.progress > 0)
        // Compositor blur has no opacity. Collapse paint, content and its blur
        // outline together, rather than fading away over a still-blurred card.
        // TransformWatcher observes Item.scaleChanged, not a separate Scale
        // object's xScale/yScale. Keep blur-region updates on the same frames.
        scale: root.contextMenu ? 1 : root.progress
        transformOrigin: root.edge === "left" ? Item.Left : root.edge === "right" ? Item.Right : Item.Bottom
        DockBubbleSurface {
            id: bubble
            anchors.fill: parent
            edge: root.edge
            anchorOffset: root.contextMenu ? root.anchorOffset : root.edge === "bottom" ? width / 2 : height
                                                                                          / 2
        }
        Item {
            visible: !root.contextMenu && !root.fan && !root.list
            x: bubble.bodyX + 10
            y: 10
            width: bubble.bodyWidth - 20
            height: bubble.bodyHeight - 20
            Item {
                id: header
                width: parent.width
                implicitHeight: 34
                height: implicitHeight
                Text {
                    anchors.centerIn: parent
                    width: parent.width - 72
                    text: directory.item ? directory.item.info.name || "" : ""
                    font.family: Fonts.ui
                    color: Appearance.colors.colOnSurface
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideMiddle
                }
                StyledMenuItem {
                    width: 34
                    height: 34
                    visible: root.history.length > 0
                    iconName: "arrow_back"
                    onTriggered: {
                        root.browsingUrl = root.history[root.history.length - 1];
                        root.history = root.history.slice(0, -1);
                    }
                }
            }
            GridView {
                id: grid
                anchors {
                    left: parent.left
                    right: parent.right
                    top: header.bottom
                    bottom: parent.bottom
                }
                clip: true
                cellWidth: width / root.gridColumns
                cellHeight: 112
                model: root.visible && !root.contextMenu && !root.fan && !root.list && directory.item ? root.count
                                                                                                        + 1 : 0
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: StyledScrollBar {}
                delegate: DockFileTile {
                    required property int index
                    readonly property bool openFolder: index === root.count
                    fileInfo: openFolder ? ({
                                                name: qsTr("Open in File Manager")
                                            }) : directory.item ? directory.item.get(index) : ({})
                    actionIcon: openFolder ? "open_in_new" : ""
                    enabled: !openFolder || root.directoryAvailable
                    width: grid.cellWidth
                    height: grid.cellHeight
                    onActivated: info => {
                        if (openFolder) {
                            ApplicationService.openUrl(root.currentUrl);
                            root.dismissed();
                        } else {
                            root.open(info);
                        }
                    }
                }
                InlineBusyIndicator {
                    anchors.centerIn: parent
                    busy: !!directory.item && directory.item.loading
                }
                Text {
                    x: grid.cellWidth
                    width: grid.width - grid.cellWidth
                    height: grid.cellHeight
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    visible: root.count === 0 && !(directory.item && directory.item.loading)
                    text: root.directoryAvailable ? qsTr("Folder is empty") : qsTr("Folder is unavailable")
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Fonts.ui
                }
            }
        }
    }
    readonly property var choices: {
        if (confirmEmpty)
            return [
                        {
                            heading: qsTr("Permanently delete all items in Trash?")
                        },
                        {
                            label: qsTr("Cancel"),
                            action: "cancel"
                        },
                        {
                            label: qsTr("Empty Trash"),
                            action: "empty",
                            destructive: true
                        }
                    ];
        let result = [];
        if (!entry)
            return result;
        if (entry.kind === "folder") {
            result.push({
                            heading: qsTr("Sort by")
                        });
            const sorts = [["name", qsTr("Name")], ["modified", qsTr("Date Modified")], ["created", qsTr(
                                                                                             "Date Created")],
                           ["kind", qsTr("Kind")], ["size", qsTr("Size")]];
            for (const option of sorts)
                result.push({
                                label: option[1],
                                option: "sort",
                                value: option[0]
                            });
            result.push({
                            heading: qsTr("Display as")
                        });
            result.push({
                            label: qsTr("Folder"),
                            option: "display",
                            value: "folder"
                        });
            result.push({
                            label: qsTr("Stack"),
                            option: "display",
                            value: "stack"
                        });
            result.push({
                            heading: qsTr("View content as")
                        });
            for (const option of [["fan", qsTr("Fan")], ["grid", qsTr("Grid")], ["list", qsTr("List")]])
                result.push({
                                label: option[1],
                                option: "view",
                                value: option[0]
                            });
        }
        result.push({
                        label: entry.kind === "trash" ? qsTr("Open Trash") : entry.kind === "file" ? qsTr(
                                                                                                         "Open") : qsTr(
                                                                                                         "Open in File Manager"),
                        action: "open"
                    });
        if (entry.kind === "trash")
            result.push({
                            label: qsTr("Empty Trash…"),
                            action: "confirm",
                            destructive: true
                        });
        else
            result.push({
                            label: qsTr("Remove from Dock"),
                            action: "remove"
                        });
        return result;
    }
    Flickable {
        visible: root.contextMenu
        x: bubble.bodyX + 8
        y: 8
        width: Math.max(0, bubble.bodyWidth - 16)
        height: Math.max(0, bubble.bodyHeight - 16)
        contentHeight: menuColumn.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: StyledScrollBar {}
        Column {
            id: menuColumn
            width: parent.width
            spacing: 2
            InlineStatusBanner {
                visible: DockService.fileError !== ""
                width: parent.width
                tone: "error"
                message: DockService.fileError
            }
            StyledMenuItem {
                visible: DockService.fileError !== ""
                width: parent.width
                implicitHeight: visible ? 30 : 0
                text: qsTr("Dismiss")
                onTriggered: DockService.fileError = ""
            }
            Text {
                visible: !!root.entry && root.entry.kind === "trash" && !DesktopFiles.trashAvailable
                width: parent.width - 16
                x: 8
                text: qsTr("Trash is unavailable. Install or enable GVfs.")
                wrapMode: Text.Wrap
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
                font.pixelSize: 12
            }
            Repeater {
                model: root.choices
                delegate: Column {
                    required property var modelData
                    required property int index
                    width: menuColumn.width
                    Rectangle {
                        visible: !!modelData.heading && parent.index > 0 || modelData.action === "open"
                                 && root.entry && root.entry.kind === "folder"
                        width: parent.width - 44
                        x: 32
                        height: 1
                        color: Appearance.applyAlpha(Appearance.colors.colOnSurface, 0.16)
                    }
                    Text {
                        visible: !!parent.modelData.heading
                        text: parent.modelData.heading || ""
                        width: parent.width - 44
                        x: 32
                        topPadding: 8
                        bottomPadding: 6
                        wrapMode: Text.Wrap
                        font.family: Fonts.ui
                        font.pixelSize: 12
                        color: Appearance.colors.colOnSurfaceVariant
                    }
                    StyledMenuItem {
                        id: choiceItem
                        readonly property var choice: parent.modelData
                        visible: !choice.heading
                        width: parent.width
                        implicitHeight: visible ? 30 : 0
                        text: choice.label || ""
                        checkable: !!choice.option
                        checked: !!root.entry && !!choice.option && root.entry[choice.option] === choice.value
                        leftPadding: 32
                        indicator: MaterialSymbol {
                            x: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: "check"
                            iconSize: 18
                            opacity: choiceItem.checked ? 1 : 0
                            color: choiceItem.foreground
                        }
                        contentItem: Text {
                            text: choiceItem.text
                            textFormat: Text.PlainText
                            font.family: Fonts.ui
                            font.pixelSize: Typography.labelLarge.pixelSize
                            font.weight: Typography.labelLarge.weight
                            color: choiceItem.foreground
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        background: Rectangle {
                            radius: 6
                            color: Appearance.applyAlpha(choiceItem.foreground, choiceItem.down
                                                         ? Appearance.interaction.pressedStateLayerOpacity :
                                                           choiceItem.highlighted || choiceItem.activeFocus
                                                           ? Appearance.interaction.focusStateLayerOpacity :
                                                             choiceItem.hovered
                                                             ? Appearance.interaction.hoverStateLayerOpacity :
                                                               0)
                        }
                        destructive: !!choice.destructive
                        enabled: choice.action !== "confirm" && choice.action !== "empty"
                                 || DesktopFiles.trashAvailable && DesktopFiles.trashCount > 0 &&
                                 !DesktopFiles.busy
                        onTriggered: {
                            if (choice.option) {
                                DockService.folderOption(root.entryKey, choice.option, choice.value);
                                root.dismissed();
                            } else if (choice.action === "confirm")
                                root.confirmEmpty = true;
                            else if (choice.action === "cancel")
                                root.confirmEmpty = false;
                            else {
                                if (choice.action === "empty")
                                    DesktopFiles.emptyTrash();
                                if (choice.action === "remove")
                                    DockService.unpin(root.entryKey);
                                if (choice.action === "open")
                                    DockService.activate(root.entryKey);
                                root.dismissed();
                            }
                        }
                    }
                }
            }
        }
    }
}
