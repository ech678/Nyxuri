pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.common

StyledMenu {
    id: root
    required property url folderUrl
    property string edge: "bottom"
    property real anchorOffset: width / 2
    readonly property real tailSize: ownerMenu ? 0 : 10
    leftPadding: 8 + (edge === "left" ? tailSize : 0)
    rightPadding: 8 + (edge === "right" ? tailSize : 0)
    bottomPadding: 8 + (edge === "bottom" ? tailSize : 0)
    property string sort: "name"
    property DockFolderModel sharedModel: null
    readonly property DockFolderModel contents: sharedModel || directory.item
    property real maximumHeight: 600
    property var ancestorUrls: []
    property var ownerMenu: null
    property var childrenMenus: []
    signal surfacesChanged
    signal fileActivated(var info)
    width: 360
    height: Math.min(480, maximumHeight, 16 + ((root.contents ? Math.max(1, root.contents.count) : 1) + 1) * 34
                     + 12 + (edge === "bottom" ? tailSize : 0))

    cascade: true
    background: DockBubbleSurface {
        edge: root.edge
        tailSize: root.tailSize
        anchorOffset: root.anchorOffset
        readonly property bool menuHovered: menuHover.hovered
        HoverHandler {
            id: menuHover
        }
    }
    function surfaces() {
        let items = visible ? [background] : [];
        for (const menu of childrenMenus)
            items = items.concat(menu.surfaces());
        return items;
    }
    function changed() {
        if (ownerMenu && typeof ownerMenu.changed === "function")
            ownerMenu.changed();
        else
            surfacesChanged();
    }
    property bool loadedOnce: false
    property bool closing: false
    onAboutToShow: closing = false
    onAboutToHide: closing = true
    onVisibleChanged: {
        if (visible)
            loadedOnce = true;
        root.changed();
        if (visible)
            root.requestRebuild();
    }
    Loader {
        id: directory
        active: !root.sharedModel && (root.visible || DockService.fileDragActive && root.loadedOnce)
        onLoaded: root.requestRebuild()
        sourceComponent: DockFolderModel {
            folder: root.folderUrl
            sort: root.sort
        }
    }
    property var generatedItems: []
    function requestRebuild() {
        if (visible && !closing && !DockService.fileDragActive)
            Qt.callLater(root.rebuild);
    }
    function rebuild() {
        if (!visible || closing || !root.contents || root.contents.loading)
            return;
        const old = generatedItems;
        generatedItems = [];
        childrenMenus = [];
        for (const record of old) {
            if (record.directory)
                removeMenu(record.item);
            else
                removeItem(record.item);
            record.item.destroy();
        }
        const rows = [];
        const submenus = [];
        for (let i = 0; i < root.contents.count; ++i) {
            const info = root.contents.model.get(i);
            const nested = info.isDirectory && !info.isLink && ancestorUrls.indexOf(info.url) < 0;
            const item = nested ? createSubmenu(info) : fileItem.createObject(root.contentItem, {
                                                                                  info: info
                                                                              });
            if (nested) {
                insertMenu(i, item);
                submenus.push(item);
            } else
                insertItem(i, item);
            rows.push({
                          item: item,
                          directory: nested
                      });
        }
        generatedItems = rows;
        childrenMenus = submenus;
        changed();
    }
    Connections {
        target: root.contents
        function onLoadingChanged() {
            root.requestRebuild();
        }
    }
    Connections {
        target: root.contents ? root.contents.model : null
        function onModelReset() {
            root.requestRebuild();
        }
        function onRowsInserted() {
            root.requestRebuild();
        }
        function onRowsRemoved() {
            root.requestRebuild();
        }
        function onDataChanged() {
            root.requestRebuild();
        }
        function onLayoutChanged() {
            root.requestRebuild();
        }
    }
    function createSubmenu(info) {
        const component = Qt.createComponent(Qt.resolvedUrl("DockFolderMenu.qml"));
        const menu = component.createObject(root, {
                                                folderUrl: info.url,
                                                title: info.name,
                                                ownerMenu: root,
                                                sort: root.sort,
                                                maximumHeight: root.maximumHeight,
                                                ancestorUrls: root.ancestorUrls.concat([String(
                                                                                            root.folderUrl)])
                                            });
        if (menu)
            menu.fileActivated.connect(root.fileActivated);
        return menu;
    }
    Component {
        id: fileItem
        StyledMenuItem {
            required property var info
            text: info.name
            implicitHeight: 34
            leftPadding: 38
            DockFileIcon {
                id: artwork
                width: 22
                height: 22
                x: 8
                anchors.verticalCenter: parent.verticalCenter
                info: parent.info
            }
            onTriggered: root.fileActivated(info)
            DockFileDrag {
                fileUrl: String(parent.info.url)
                iconItem: artwork
            }
        }
    }
    delegate: StyledMenuItem {
        implicitHeight: 34
        leftPadding: 38
        DockFileIcon {
            width: 22
            height: 22
            x: 8
            anchors.verticalCenter: parent.verticalCenter
            info: ({
                       icon: "folder",
                       isDirectory: true
                   })
        }
        rightPadding: 30
        arrow: MaterialSymbol {
            x: parent.width - width - 8
            anchors.verticalCenter: parent.verticalCenter
            text: "chevron_right"
            iconSize: 18
            color: Appearance.colors.colOnSurface
        }
    }
    StyledMenuItem {
        visible: !!root.contents && root.contents.count === 0
        enabled: false
        text: root.contents && !root.contents.available ? qsTranslate("DockFilePopup",
                                                                      "Folder is unavailable") : qsTr(
                                                              "Folder is empty")
        implicitHeight: visible ? 34 : 0
    }
    MenuSeparator {}
    StyledMenuItem {
        text: qsTr("Open in File Manager")
        implicitHeight: 34
        enabled: !!root.contents && root.contents.available
        onTriggered: root.fileActivated({
                                            url: root.folderUrl,
                                            isDirectory: true
                                        })
    }
}
