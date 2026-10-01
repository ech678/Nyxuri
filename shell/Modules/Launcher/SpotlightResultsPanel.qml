import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Effects
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.common

Item {
    id: root

    required property SpotlightStyle style
    required property string mode
    required property var results
    required property var wallpaperModel
    required property var clipboardModel
    required property int selectedIndex
    property string searchError: ""
    readonly property var searchCapacities: searchResults.capacities
    readonly property bool searchHorizontalSelection: searchResults.horizontalSelection
    signal searchActivationRequested(string id)
    property string query: ""
    property bool previewActive: false
    property string selectedClipboardId: ""
    property string clipboardLayout: UiPreferences.spotlightClipboardStyle
    property string appsLayout: UiPreferences.spotlightAppStyle
    readonly property bool commandList: ["commands", "settings", "actions", "slash"].includes(mode)
    readonly property bool clipboardDetails: mode === "clipboard" && clipboardLayout === "details"
    signal previewKey(var event)

    property bool controlHeld: false
    property string fileState: "idle"
    property var fileError: null
    readonly property bool fileMode: mode === "files"
    readonly property int fileHeaderHeight: fileMode && results.length > 0 ? 32 : 0
    signal revealRequested(int index)
    property bool expanded: mode !== "web"
    property bool loading: false
    property bool providerAvailable: true
    property bool canRestore: true
    property var providerError: null
    property string clipboardActionState: "idle"
    property string clipboardActionEntryId: ""
    property string clipboardActionError: ""
    property bool clipboardActionRunning: false
    property bool wallpaperHasMore: false
    property real availableHeight: 100000
    property real contentOpacity: 1
    property real targetWidth: width
    property bool animationsEnabled: true
    readonly property bool appGridActive: mode === "apps" && appsLayout === "grid"
    readonly property int modeIndex: mode === "wallpapers" ? 1 : (mode === "clipboard" ? 2 : 0)
    readonly property int clipboardHeaderHeight: mode === "clipboard" ? 46 : 0
    readonly property int wallpaperColumnCount: style.wallpaperColumnsForWidth(wallpaperGrid.width)
    readonly property real wallpaperCellWidth: wallpaperGrid.width / Math.max(1, wallpaperColumnCount)
    readonly property real wallpaperPreviewWidth: Math.max(1, wallpaperCellWidth - style.wallpaperGridGap)
    readonly property real wallpaperPreviewHeight: wallpaperPreviewWidth / style.wallpaperPreviewAspectRatio
    readonly property real wallpaperCellHeight: wallpaperPreviewHeight + style.wallpaperLabelGap
                                                + style.wallpaperLabelHeight + style.wallpaperGridGap
    readonly property Item blurRegionItem: panelBlurRegion
    readonly property Item modalBlurRegionItem: clearDialog.blurRegionItem
    property bool fileMenuActive: false
    readonly property bool modalActive: clearDialog.visible || fileMenuActive
    readonly property int targetHeight: {
        if (!expanded)
            return 0;
        if (mode === "search")
            return Math.min(availableHeight, searchResults.rowsHeight + style.resultPadding * 2);
        // Reserve the full clipboard viewport before history finishes loading.
        // Filtering, empty states and refreshes must not resize the panel.
        if (mode === "clipboard")
            return Math.min(clipboardDetails ? style.clipboardDetailsHeight : style.resultMaxHeight, Math.max(
                                0, availableHeight));
        if (loading || !providerAvailable || results.length === 0)
            return Math.min(availableHeight, style.emptyHeight + clipboardHeaderHeight + fileHeaderHeight);
        if (root.appGridActive)
            return Math.min(availableHeight, style.appGridMaxHeight, Math.ceil(results.length
                                                                               / appGrid.columns)
                            * style.appGridCellHeight + style.resultPadding * 2);
        if (mode === "wallpapers")
            return Math.min(style.wallpaperGridHeight, Math.max(0, availableHeight));
        return Math.min(availableHeight, style.resultMaxHeight, results.length * style.resultRowHeight
                        + style.resultPadding * 2 + clipboardHeaderHeight + fileHeaderHeight);
    }

    signal selectionRequested(int index)
    signal activationRequested(int index, bool keepOpen)
    signal deleteRequested(int index)
    signal clearRequested
    signal inspectionRequested(string id)
    signal inspectionReleased(string id)
    signal modalClosed
    signal wallpaperMoreRequested(int minimumCount)

    height: targetHeight
    opacity: expanded ? 1 : 0
    visible: height > 0.5 || opacity > 0.01

    Behavior on width {
        enabled: root.animationsEnabled
        NumberAnimation {
            duration: root.style.panelDuration
            easing.type: Easing.BezierSpline
            easing.bezierCurve: root.style.panelCurve
        }
    }

    Behavior on height {
        enabled: root.animationsEnabled
        NumberAnimation {
            duration: root.style.panelDuration
            easing.type: Easing.BezierSpline
            easing.bezierCurve: root.style.panelCurve
        }
    }

    Behavior on opacity {
        enabled: root.animationsEnabled
        NumberAnimation {
            duration: root.style.panelDuration
            easing.type: Easing.BezierSpline
            easing.bezierCurve: root.style.effectsCurve
        }
    }

    onModeChanged: {
        contentFade.stop();
        root.contentOpacity = root.animationsEnabled ? 0 : 1;
        if (root.animationsEnabled)
            contentFade.restart();
    }

    function clipboardActivationAreaAt(index) {
        const delegate = clipboardList.itemAtIndex(index);
        return delegate ? delegate.activationArea : null;
    }

    function clipboardLayoutAt(index) {
        const delegate = clipboardList.itemAtIndex(index);
        if (!delegate)
            return null;
        return {
            textRight: delegate.textArea.x + delegate.textArea.width,
            actionLeft: delegate.actionArea.x,
            titleMaximumLineCount: delegate.titleLabel.maximumLineCount,
            subtitleMaximumLineCount: delegate.subtitleLabel.maximumLineCount,
            titleWrapMode: delegate.titleLabel.wrapMode,
            subtitleWrapMode: delegate.subtitleLabel.wrapMode,
            titleFontFamily: delegate.titleLabel.font.family,
            titleClip: delegate.titleLabel.clip,
            subtitleClip: delegate.subtitleLabel.clip
        };
    }

    function gridColumns() {
        return root.wallpaperColumnCount;
    }

    function navigationStep(direction) {
        if (mode === "search")
            return searchResults.navigationIndex(direction < 0 ? "up" : "down") - selectedIndex;
        return mode === "wallpapers" ? direction * gridColumns() : (root.appGridActive ? direction
                                                                                         * appGrid.columns :
                                                                                         direction);
    }

    function searchNavigationIndex(direction) {
        return searchResults.navigationIndex(direction);
    }

    function requestMoreWallpapers() {
        if (root.mode !== "wallpapers" || !root.wallpaperHasMore)
            return;
        const remaining = wallpaperGrid.contentHeight - wallpaperGrid.contentY - wallpaperGrid.height;
        if (remaining > root.wallpaperCellHeight * 1.5)
            return;
        root.wallpaperMoreRequested(wallpaperGrid.count + root.wallpaperColumnCount * 4);
    }

    NumberAnimation {
        id: contentFade

        target: root
        property: "contentOpacity"
        from: 0
        to: 1
        duration: root.style.panelDuration
        easing.type: Easing.BezierSpline
        easing.bezierCurve: root.style.effectsCurve
    }

    Item {
        id: panelBlurRegion

        anchors.fill: parent
        anchors.margins: root.style.blurEdgeInset
        property real radius: Math.max(0, root.style.resultRadius - root.style.blurEdgeInset)
    }

    Rectangle {
        id: panelSurface

        anchors.fill: parent
        radius: root.style.resultRadius
        color: root.style.panelColor
        visible: false
    }

    MultiEffect {
        anchors.fill: panelSurface
        source: panelSurface
        autoPaddingEnabled: true
        shadowEnabled: true
        shadowColor: root.style.shadowColor
        shadowBlur: root.style.shadowBlur
        shadowVerticalOffset: root.style.shadowVerticalOffset
        shadowHorizontalOffset: 0
    }

    // Keep the grid centered on the panel itself while a newly shown
    // window settles its geometry; StackLayout updates its pages later.
    SpotlightAppGrid {
        id: appGrid

        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: root.style.resultPadding
        anchors.bottomMargin: root.style.resultPadding
        opacity: root.contentOpacity
        // Column count follows the destination size, not each frame
        // of the panel's width transition between launcher modes.
        readonly property real layoutWidth: Math.max(0, root.targetWidth - root.style.resultPadding * 2)

        width: Math.min(layoutWidth, Math.max(1, Math.floor(layoutWidth / root.style.appGridCellWidth))
                        * root.style.appGridCellWidth)
        visible: root.appGridActive
        style: root.style
        results: root.appGridActive ? root.results : []
        selectedIndex: root.selectedIndex
        searchActive: root.query.trim().length > 0
        onSelectionRequested: index => root.selectionRequested(index)
        onActivationRequested: index => root.activationRequested(index, false)
    }

    SpotlightSearchResults {
        id: searchResults
        anchors.fill: parent
        anchors.margins: root.style.resultPadding
        visible: root.mode === "search"
        layoutWidth: Math.max(0, root.targetWidth - root.style.resultPadding * 2)
        style: root.style
        results: root.mode === "search" ? root.results : []
        selectedIndex: root.selectedIndex
        error: root.searchError
        onSelectionRequested: index => root.selectionRequested(index)
        onActivationRequested: id => root.searchActivationRequested(id)
    }

    StackLayout {
        visible: root.mode !== "search"
        anchors.fill: parent
        anchors.topMargin: root.fileHeaderHeight + root.style.resultPadding
        anchors.margins: root.mode === "wallpapers" ? root.style.wallpaperPanelPadding :
                                                      root.style.resultPadding
        currentIndex: root.modeIndex
        opacity: root.contentOpacity

        Item {
            ListView {
                id: appList

                anchors.fill: parent
                visible: !root.appGridActive
                clip: true
                spacing: 0
                model: (root.mode === "apps" || root.fileMode || root.commandList) && !root.appGridActive ? root.results :
                                                                                                            []
                currentIndex: root.selectedIndex
                boundsBehavior: Flickable.StopAtBounds
                keyNavigationEnabled: false
                interactive: !DockService.externalDragActive
                highlight: Item {}
                highlightMoveDuration: root.style.resultScrollDuration
                highlightMoveVelocity: -1

                ScrollBar.vertical: StyledScrollBar {}

                delegate: Item {
                    id: appDelegate

                    required property int index
                    required property var modelData
                    width: ListView.view.width
                    height: root.style.resultRowHeight

                    Rectangle {
                        anchors.fill: parent
                        radius: Appearance.rounding.large
                        color: appDelegate.index === root.selectedIndex ? root.style.selectedColor : (
                                                                              appMouse.containsMouse
                                                                              ? root.style.hoverColor :
                                                                                "transparent")
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 16
                        spacing: 14

                        FileThemeIcon {
                            active: root.fileMode && !!appDelegate.modelData.file
                            visible: active
                            Layout.preferredWidth: root.style.resultIconSize
                            Layout.preferredHeight: root.style.resultIconSize
                            entryKey: root.fileMode ? appDelegate.modelData.id : ""
                            themeIcon: root.fileMode ? appDelegate.modelData.icon : ""
                            mimeType: active ? appDelegate.modelData.file.mimeType : ""
                            directory: active && appDelegate.modelData.file.isDirectory
                        }

                        ThemeIcon {
                            id: appListIcon

                            visible: !root.fileMode && !root.commandList && !appDelegate.modelData.symbol
                            Layout.preferredWidth: root.style.resultIconSize
                            Layout.preferredHeight: root.style.resultIconSize
                            iconSource: root.fileMode || root.commandList || appDelegate.modelData.symbol
                                        ? "" : ApplicationService.iconSource(appDelegate.modelData.icon)
                            sourceSize.width: root.style.resultIconSize * 2
                            sourceSize.height: root.style.resultIconSize * 2
                            asynchronous: true
                            fillMode: Image.PreserveAspectFit
                        }

                        MaterialSymbol {
                            id: appListSymbol

                            visible: root.commandList || (!root.fileMode && !!appDelegate.modelData.symbol)
                            text: appDelegate.modelData.symbol || appDelegate.modelData.icon || "terminal"
                            iconSize: root.style.resultIconSize
                            Layout.preferredWidth: root.style.resultIconSize
                            Layout.preferredHeight: root.style.resultIconSize
                            color: Appearance.colors.colOnSurfaceVariant
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            Text {
                                Layout.fillWidth: true
                                text: appDelegate.modelData.title
                                textFormat: Text.PlainText
                                maximumLineCount: 1
                                clip: true
                                color: appDelegate.index === root.selectedIndex
                                       ? root.style.selectedContentColor : Appearance.colors.colOnSurface
                                font.family: Fonts.ui
                                font.pixelSize: 17
                                font.weight: Font.Medium
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.fileMode && root.controlHeld && appDelegate.index
                                      === root.selectedIndex ? appDelegate.modelData.location :
                                                               appDelegate.modelData.subtitle
                                textFormat: Text.PlainText
                                maximumLineCount: 1
                                clip: true
                                color: appDelegate.index === root.selectedIndex
                                       ? root.style.selectedContentColor :
                                         Appearance.colors.colOnSurfaceVariant
                                font.family: Fonts.ui
                                font.pixelSize: 13
                                elide: root.fileMode && root.controlHeld && appDelegate.index
                                       === root.selectedIndex ? Text.ElideMiddle : Text.ElideRight
                            }
                        }

                        MaterialSymbol {
                            text: "keyboard_return"
                            iconSize: 19
                            color: root.style.selectedContentColor
                            opacity: appDelegate.index === root.selectedIndex ? 0.78 : 0
                        }
                    }

                    MouseArea {
                        id: appMouse

                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        Accessible.name: appDelegate.modelData.title
                        Accessible.role: Accessible.ListItem
                        acceptedButtons: root.fileMode ? Qt.LeftButton | Qt.RightButton : Qt.LeftButton
                        onPressed: appDrag.resetGesture()
                        onClicked: mouse => {
                            if (appDrag.dragged)
                                return;
                            root.selectionRequested(appDelegate.index);
                            if (root.fileMode && mouse.button === Qt.RightButton)
                                fileMenu.popup();
                            else
                                root.activationRequested(appDelegate.index, false);
                        }
                    }
                    SpotlightAppDrag {
                        id: appDrag

                        desktopId: root.mode === "apps" && appDelegate.modelData.appObject ? String(
                                                                                                 appDelegate.modelData.appObject.id) :
                                                                                             ""
                        iconItem: appDelegate.modelData.symbol ? appListSymbol : appListIcon
                    }
                    Menu {
                        id: fileMenu
                        onOpened: root.fileMenuActive = true
                        onClosed: {
                            root.fileMenuActive = false;
                            root.modalClosed();
                        }
                        MenuItem {
                            text: qsTr("Open")
                            onTriggered: root.activationRequested(appDelegate.index, false)
                        }
                        MenuItem {
                            text: qsTr("Show in file manager")
                            onTriggered: root.revealRequested(appDelegate.index)
                        }
                    }
                }
            }
        }

        GridView {
            id: wallpaperGrid

            clip: true
            model: root.mode === "wallpapers" ? root.wallpaperModel : null
            currentIndex: root.selectedIndex
            cellWidth: root.wallpaperCellWidth
            cellHeight: root.wallpaperCellHeight
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: false
            highlight: Item {}
            highlightMoveDuration: root.style.resultScrollDuration
            cacheBuffer: 0
            onContentYChanged: root.requestMoreWallpapers()
            onHeightChanged: Qt.callLater(root.requestMoreWallpapers)
            onCountChanged: Qt.callLater(root.requestMoreWallpapers)

            ScrollBar.vertical: StyledScrollBar {}

            delegate: Item {
                id: wallpaperDelegate

                required property int index
                required property string wallpaperPath
                readonly property var entry: root.results[wallpaperDelegate.index] || ({})
                readonly property bool isCurrentWallpaper: WallpaperService.normalizedPath(
                                                               wallpaperDelegate.entry.path)
                                                           === WallpaperService.normalizedPath(
                                                               WallpaperService.currentWallpaper
                                                               || WallpaperService.wallpaperForScreen(""))
                property bool appeared: false
                readonly property real initialX: ((index * 37) % 3 - 1) * 24
                readonly property real initialY: ((index * 53) % 5 - 2) * 10
                width: wallpaperGrid.cellWidth
                height: wallpaperGrid.cellHeight
                opacity: appeared ? 1 : 0
                scale: appeared ? 1 : 0.76
                rotation: appeared ? 0 : ((index % 3) - 1) * 3
                transform: Translate {
                    x: wallpaperDelegate.appeared ? 0 : wallpaperDelegate.initialX
                    y: wallpaperDelegate.appeared ? 0 : wallpaperDelegate.initialY
                }

                Behavior on opacity {
                    NumberAnimation {
                        duration: 190
                    }
                }

                Behavior on scale {
                    NumberAnimation {
                        duration: Appearance.animation.expressiveDefaultSpatial.duration
                        easing.type: Appearance.animation.expressiveDefaultSpatial.type
                        easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                    }
                }

                Behavior on rotation {
                    NumberAnimation {
                        duration: Appearance.animation.expressiveDefaultSpatial.duration
                        easing.type: Appearance.animation.expressiveDefaultSpatial.type
                        easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                    }
                }

                Timer {
                    interval: Math.min(260, (wallpaperDelegate.index % Math.max(1, root.wallpaperColumnCount
                                                                                * 3)) * 18) + ((
                                                                                                   wallpaperDelegate.index
                                                                                                   * 29) % 5)
                              * 8
                    running: root.mode === "wallpapers"
                    onTriggered: wallpaperDelegate.appeared = true
                }

                Rectangle {
                    id: wallpaperCard

                    anchors.fill: parent
                    anchors.margins: root.style.wallpaperGridGap / 2
                    radius: Appearance.rounding.large
                    color: wallpaperDelegate.index === root.selectedIndex ? root.style.selectedColor : (
                                                                                wallpaperMouse.containsMouse
                                                                                ? root.style.hoverColor :
                                                                                  "transparent")

                    Item {
                        id: previewFrame

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: width / root.style.wallpaperPreviewAspectRatio

                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: previewFrame.width
                                height: previewFrame.height
                                radius: Appearance.rounding.large
                            }
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: root.style.surfaceColor
                        }

                        MaterialSymbol {
                            anchors.centerIn: parent
                            text: "image"
                            iconSize: 34
                            fill: 1
                            color: Appearance.colors.colOutline
                        }

                        Image {
                            id: wallpaperImage

                            anchors.fill: parent
                            source: wallpaperDelegate.entry.preview
                            sourceSize.width: Math.ceil(previewFrame.width * 2)
                            sourceSize.height: Math.ceil(previewFrame.height * 2)
                            asynchronous: true
                            cache: true
                            smooth: true
                            fillMode: Image.PreserveAspectCrop
                            scale: wallpaperMouse.containsMouse ? root.style.wallpaperHoverScale : 1

                            Behavior on scale {
                                NumberAnimation {
                                    duration: root.style.wallpaperHoverDuration
                                    easing.type: Easing.BezierSpline
                                    easing.bezierCurve: root.style.wallpaperHoverCurve
                                }
                            }
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: Appearance.applyAlpha(Appearance.colors.colOnSurface,
                                                         wallpaperMouse.pressed
                                                         ? root.style.wallpaperPressedOverlayOpacity : (
                                                               wallpaperMouse.containsMouse
                                                               ? root.style.wallpaperHoverOverlayOpacity : 0))

                            Behavior on color {
                                ColorAnimation {
                                    duration: root.style.wallpaperHoverDuration
                                    easing.type: Easing.BezierSpline
                                    easing.bezierCurve: root.style.wallpaperHoverCurve
                                }
                            }
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 10
                            width: root.style.wallpaperCurrentMarkSize
                            height: width
                            radius: width / 2
                            color: Appearance.colors.colPrimaryContainer
                            visible: wallpaperDelegate.isCurrentWallpaper

                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: "check"
                                iconSize: 19
                                fill: 1
                                color: Appearance.colors.colOnPrimaryContainer
                            }
                        }
                    }

                    Text {
                        id: wallpaperLabel

                        anchors.top: previewFrame.bottom
                        anchors.topMargin: root.style.wallpaperLabelGap
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        height: root.style.wallpaperLabelHeight
                        text: wallpaperDelegate.entry.title
                        color: wallpaperDelegate.index === root.selectedIndex
                               ? root.style.selectedContentColor : Appearance.colors.colOnSurface
                        font.family: Fonts.ui
                        font.pixelSize: root.style.wallpaperLabelFontSize
                        font.weight: Font.Medium
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideMiddle
                        textFormat: Text.PlainText
                    }
                }

                MouseArea {
                    id: wallpaperMouse

                    anchors.fill: wallpaperCard
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.LeftButton
                    Accessible.name: wallpaperDelegate.entry.title
                    Accessible.role: Accessible.ListItem
                    onClicked: {
                        root.selectionRequested(wallpaperDelegate.index);
                        root.activationRequested(wallpaperDelegate.index, false);
                    }
                }
            }
        }

        ColumnLayout {
            spacing: 0

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 46

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.providerAvailable && !root.canRestore ? qsTr(
                                                                           "wl-copy is missing: restore is unavailable") :
                                                                       qsTr("Clipboard history")
                    color: root.providerAvailable && !root.canRestore ? Appearance.colors.colError :
                                                                        Appearance.colors.colOnSurfaceVariant
                    font.family: Fonts.ui
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }

                ActionButton {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    enabled: root.providerAvailable && !root.loading && !root.clipboardActionRunning
                             && root.results.length > 0
                    filled: false
                    iconName: "delete_sweep"
                    text: qsTr("Clear")
                    onClicked: clearDialog.open()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: root.clipboardDetails && width >= root.style.clipboardDetailsBreakpoint ? 2 : 1
                columnSpacing: root.style.resultPadding
                rowSpacing: root.style.resultPadding

                ListView {
                    id: clipboardList

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: root.clipboardDetails ? (parent.columns === 2 ? parent.width / 3 :
                                                                                           parent.width) :
                                                                   parent.width
                    Layout.preferredHeight: root.clipboardDetails && parent.columns === 1 ? parent.height
                                                                                            * 0.32 : parent.height
                    Layout.minimumWidth: 0
                    Layout.minimumHeight: 0
                    clip: true
                    spacing: 0
                    model: root.mode === "clipboard" ? root.clipboardModel : []
                    currentIndex: root.selectedIndex
                    boundsBehavior: Flickable.StopAtBounds
                    keyNavigationEnabled: false
                    highlight: Item {}
                    highlightMoveDuration: root.style.resultScrollDuration
                    highlightMoveVelocity: -1

                    ScrollBar.vertical: StyledScrollBar {}

                    delegate: Item {
                        id: clipboardDelegate

                        required property int index
                        required property string clipboardEntryId
                        readonly property int detailsRevision: ClipboardService.detailsRevision
                        readonly property var clipboardEntry: {
                            // The ListModel carries only the stable ID.  Keeping
                            // the result object in the provider's JS array avoids
                            // QVariant role type changes when a lightweight row
                            // is replaced by its inspected detail.
                            const currentResults = root.results;
                            const id = clipboardDelegate.clipboardEntryId;
                            for (let resultIndex = 0; resultIndex < currentResults.length; resultIndex += 1) {
                                const result = currentResults[resultIndex];
                                if (String(result.id || "") === id)
                                    return result;
                            }
                            return {};
                        }
                        readonly property bool detailsLayout: root.clipboardDetails
                        onDetailsLayoutChanged: {
                            if (!detailsLayout)
                                root.inspectionRequested(clipboardEntryId);
                            else
                                root.inspectionReleased(clipboardEntryId);
                        }
                        readonly property var displayData: {
                            if (root.clipboardDetails)
                                return clipboardDelegate.clipboardEntry;
                            // ClipboardService stores inspection results in a
                            // keyed object.  The revision is an explicit
                            // dependency because dynamic object keys do not
                            // produce QML notifications.
                            const ignoredRevision = clipboardDelegate.detailsRevision;
                            const detail = ClipboardService.detail(String(clipboardDelegate.clipboardEntry.id
                                                                          || ""));
                            if (!detail)
                                return clipboardDelegate.clipboardEntry;
                            return Object.assign({}, clipboardDelegate.clipboardEntry, detail);
                        }
                        readonly property bool actionForThis: String(clipboardEntry.id)
                                                              === root.clipboardActionEntryId
                        readonly property alias activationArea: clipboardMouse
                        readonly property alias textArea: clipboardTextColumn
                        readonly property alias actionArea: clipboardActionArea
                        readonly property alias titleLabel: clipboardTitle
                        readonly property alias subtitleLabel: clipboardSubtitle
                        width: ListView.view.width
                        height: root.clipboardDetails ? root.style.clipboardDetailsRowHeight :
                                                        root.style.resultRowHeight

                        Component.onCompleted: {
                            if (!root.clipboardDetails)
                                root.inspectionRequested(String(clipboardDelegate.clipboardEntry.id));
                        }
                        Component.onDestruction: root.inspectionReleased(String(
                                                                             clipboardDelegate.clipboardEntry.id))

                        Rectangle {
                            anchors.fill: parent
                            radius: Appearance.rounding.large
                            color: clipboardDelegate.index === root.selectedIndex ? root.style.selectedColor :
                                                                                    (clipboardMouse.containsMouse
                                                                                     ? root.style.hoverColor :
                                                                                       "transparent")
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 6
                            spacing: 13

                            Item {
                                visible: !root.clipboardDetails
                                Layout.preferredWidth: 42
                                Layout.minimumWidth: 42
                                Layout.maximumWidth: 42
                                Layout.preferredHeight: 42
                                Layout.minimumHeight: 42
                                Layout.maximumHeight: 42

                                Item {
                                    id: clipboardPreviewFrame

                                    anchors.fill: parent
                                    visible: String(clipboardDelegate.displayData.previewUrl || "") !== ""
                                    layer.enabled: visible
                                    layer.effect: OpacityMask {
                                        maskSource: Rectangle {
                                            width: clipboardPreviewFrame.width
                                            height: clipboardPreviewFrame.height
                                            radius: Appearance.rounding.large
                                        }
                                    }

                                    Rectangle {
                                        anchors.fill: parent
                                        color: root.style.hoverColor
                                    }

                                    Image {
                                        anchors.fill: parent
                                        source: root.clipboardDetails ? "" :
                                                                        clipboardDelegate.displayData.previewUrl
                                                                        || ""
                                        sourceSize.width: 96
                                        sourceSize.height: 96
                                        asynchronous: true
                                        cache: true
                                        smooth: true
                                        fillMode: Image.PreserveAspectCrop
                                    }
                                }

                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    visible: !clipboardPreviewFrame.visible
                                    text: clipboardDelegate.displayData.icon
                                    iconSize: 24
                                    color: clipboardDelegate.index === root.selectedIndex
                                           ? root.style.selectedContentColor : Appearance.colors.colPrimary
                                }
                            }

                            ColumnLayout {
                                id: clipboardTextColumn

                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                clip: true
                                spacing: 1

                                Text {
                                    id: clipboardTitle

                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    text: clipboardDelegate.displayData.title
                                    color: clipboardDelegate.index === root.selectedIndex
                                           ? root.style.selectedContentColor : Appearance.colors.colOnSurface
                                    font.family: Fonts.ui
                                    textFormat: Text.PlainText
                                    font.pixelSize: 16
                                    maximumLineCount: 1
                                    wrapMode: Text.NoWrap
                                    elide: Text.ElideRight
                                    clip: true
                                }

                                Text {
                                    id: clipboardSubtitle
                                    visible: !root.clipboardDetails

                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    text: clipboardDelegate.actionForThis && root.clipboardActionState
                                          === "error" && root.clipboardActionError !== ""
                                          ? root.clipboardActionError : clipboardDelegate.displayData.subtitle
                                    color: clipboardDelegate.index === root.selectedIndex
                                           ? root.style.selectedContentColor :
                                             Appearance.colors.colOnSurfaceVariant
                                    font.family: Fonts.ui
                                    textFormat: Text.PlainText
                                    font.pixelSize: 12
                                    maximumLineCount: 1
                                    wrapMode: Text.NoWrap
                                    elide: Text.ElideRight
                                    clip: true
                                }
                            }

                            Item {
                                id: clipboardActionArea

                                Layout.preferredWidth: 92
                                Layout.minimumWidth: 92
                                Layout.maximumWidth: 92
                                Layout.preferredHeight: 42
                                Layout.minimumHeight: 42
                                Layout.maximumHeight: 42

                                IconButton {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    controlSize: 42
                                    visible: !clipboardDelegate.actionForThis || root.clipboardActionState
                                             === "idle"
                                    enabled: !root.clipboardActionRunning
                                    iconName: "delete"
                                    iconSize: 20
                                    iconColor: Appearance.colors.colOnSurfaceVariant
                                    accessibleName: qsTr("Delete clipboard entry")
                                    onClicked: root.deleteRequested(clipboardDelegate.index)
                                }

                                BusyIndicator {
                                    anchors.centerIn: parent
                                    width: 24
                                    height: 24
                                    visible: clipboardDelegate.actionForThis && root.clipboardActionState
                                             === "copying"
                                    running: visible
                                    Material.accent: Appearance.colors.colPrimary
                                }

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 5
                                    visible: clipboardDelegate.actionForThis && (root.clipboardActionState
                                                                                 === "copied"
                                                                                 || root.clipboardActionState
                                                                                 === "error")

                                    MaterialSymbol {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: root.clipboardActionState === "copied" ? "check" : "error"
                                        iconSize: 18
                                        fill: 1
                                        color: root.clipboardActionState === "copied"
                                               ? Appearance.colors.colPrimary : Appearance.colors.colError
                                    }

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: root.clipboardActionState === "copied" ? qsTr("Copied") : qsTr(
                                                                                           "Copy failed")
                                        color: root.clipboardActionState === "copied"
                                               ? Appearance.colors.colPrimary : Appearance.colors.colError
                                        font.family: Fonts.ui
                                        font.pixelSize: 12
                                    }
                                }
                            }
                        }

                        MouseArea {
                            id: clipboardMouse

                            anchors.fill: parent
                            anchors.rightMargin: 96
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            acceptedButtons: Qt.LeftButton
                            Accessible.name: clipboardDelegate.displayData.title
                            Accessible.role: Accessible.ListItem
                            onClicked: mouse => {
                                root.selectionRequested(clipboardDelegate.index);
                                if (!root.clipboardDetails)
                                    root.activationRequested(clipboardDelegate.index, (mouse.modifiers
                                                                                       & Qt.ControlModifier)
                                                             !== 0);
                            }
                        }
                    }
                }
                Loader {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: parent.width * 2 / 3
                    Layout.preferredHeight: parent.height * 0.68
                    Layout.minimumWidth: 0
                    Layout.minimumHeight: 0
                    visible: root.clipboardDetails
                    active: root.clipboardDetails && root.previewActive && root.providerAvailable
                            && root.results.length > 0
                    sourceComponent: SpotlightClipboardDetails {
                        entryId: root.selectedClipboardId
                        canRestore: root.canRestore
                        actionRunning: root.clipboardActionRunning
                        actionError: root.clipboardActionError || (ClipboardService.lastActionError
                                                                   ? ClipboardService.lastActionError.message :
                                                                     "")
                        onRestoreRequested: root.activationRequested(root.selectedIndex, false)
                        onRoutedKey: event => root.previewKey(event)
                    }
                }
            }
        }
    }

    Text {
        visible: root.fileHeaderHeight > 0
        x: 20
        y: 8
        width: parent.width - 40
        text: root.fileError ? root.fileError.message : root.fileState === "limited" ? qsTr(
                                                                                           "Limited results — refine your search") :
                                                                                       qsTr("Enter — Open · Ctrl+Enter — Show in file manager")
        textFormat: Text.PlainText
        elide: Text.ElideRight
        font.family: Fonts.ui
        font.pixelSize: 12
        color: root.fileError ? Appearance.colors.colError : Appearance.colors.colOnSurfaceVariant
    }

    Item {
        anchors.fill: parent
        anchors.topMargin: root.clipboardHeaderHeight
        visible: root.mode !== "search" && ((root.loading && (!root.clipboardDetails || root.results.length === 0))
                                            || !root.providerAvailable || root.results.length === 0)
        opacity: root.contentOpacity

        Column {
            anchors.centerIn: parent
            spacing: 10

            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                running: root.loading
                visible: root.loading
                Material.accent: Appearance.colors.colPrimary
            }

            MaterialSymbol {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: !root.loading
                text: root.fileMode ? "folder_search" : !root.providerAvailable ? "content_paste_off" :
                                                                                  "search_off"
                iconSize: 32
                color: Appearance.colors.colOnSurfaceVariant
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(520, root.width - 48)
                text: root.fileMode ? (root.fileError ? root.fileError.message : root.loading ? qsTr(
                                                                                                    "Searching…") :
                                                                                                root.fileState
                                                                                                === "idle"
                                                                                                ? qsTr("Search files and folders") :
                                                                                                  root.fileState
                                                                                                  === "limited"
                                                                                                  ? qsTr("Search stopped before completion — refine your search") :
                                                                                                    qsTr("No matching results")) :
                                      root.loading ? qsTr("Reading…") : (!root.providerAvailable ? (
                                                                                                       root.providerError
                                                                                                       ? root.providerError.message :
                                                                                                         qsTr("Current provider is unavailable")) :
                                                                                                   qsTr("No matching results"))
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
                font.pixelSize: 15
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }
        }
    }

    MaterialDialog {
        id: clearDialog

        anchors.centerIn: Overlay.overlay
        width: 380
        dialogTitle: qsTr("Clear clipboard history?")
        messageText: qsTr("This clears all clipboard history in cliphist and cannot be undone.")

        actionsComponent: Component {
            RowLayout {
                spacing: Metrics.spacingS

                Item {
                    Layout.fillWidth: true
                }

                ActionButton {
                    id: cancelButton

                    text: qsTr("Cancel")
                    Component.onCompleted: clearDialog.initialFocusItem = cancelButton
                    onClicked: clearDialog.close()
                }

                ActionButton {
                    text: qsTr("Clear")
                    onClicked: {
                        root.clearRequested();
                        clearDialog.close();
                    }
                }
            }
        }
        onClosed: root.modalClosed()
    }
}
