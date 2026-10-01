import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Material
import Quickshell
import Quickshell.Wayland
import Clavis.Keyboard
import qs.Common
import qs.Services
import qs.Widgets.common
import qs.Modules.ControlCenter
import "../../Common/functions/SpotlightCommands.js" as Commands

PanelWindow {
    id: root

    visible: false
    color: "transparent"

    anchors {
        top: true
        bottom: true
        left: true
        right: true
    }

    WlrLayershell.namespace: "clavis-shell-spotlight"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    WlrLayershell.exclusionMode: ExclusionMode.Ignore

    Material.theme: Appearance.m3colors.darkmode ? Material.Dark : Material.Light
    Material.accent: Appearance.colors.colPrimary

    property var pendingSearchActivation: null
    property bool queryUpdating: false
    property bool commandSelectionExplicit: false
    property int toolCandidateIndex: 0
    property string pendingWebUrl: ""
    property string windowPhase: "hidden"
    property bool closeAfterDrag: false
    readonly property string mode: session.viewMode
    // Keep the content query while the input is used for a slash command.
    property string contentQuery: ""
    readonly property bool toolMode: ["calculator", "currency", "time"].includes(mode)
    property bool modeRailExpanded: false
    property int modeFocusIndex: -1
    property alias query: session.query
    property bool controlHeld: false
    property int selectedResultIndex: -1
    property string selectedResultId: ""
    property string clipboardActionState: "idle"
    property string clipboardActionEntryId: ""
    property bool clipboardActionKeepOpen: false
    property string clipboardActionError: ""
    property bool clipboardSelectionRecoveryPending: false
    property string clipboardSelectionRecoveryTargetId: ""
    property string clipboardSelectionRecoveryId: ""

    property real windowProgress: 0
    property real railProgress: 0
    property real webProgress: 0
    property real _windowAnimationTarget: 0
    property real _railAnimationTarget: 0
    property real _webAnimationTarget: 0

    onWebProgressChanged: spotlightBlur.publish()

    readonly property var activeResults: mode === "commands" ? commandProvider.results : ["search", "settings",
                                                                                          "actions"].includes(
                                                                   mode) ? searchProvider.results : mode
                                                                           === "apps" ? appProvider.results : (
                                                                                            mode === "wallpapers"
                                                                                            ? wallpaperProvider.results :
                                                                                              (mode === "clipboard"
                                                                                               ? clipboardProvider.results :
                                                                                                 (mode === "files"
                                                                                                  ? fileProvider.results :
                                                                                                    [])))
    readonly property bool clipboardDetailsMode: mode === "clipboard" && session.clipboardLayout === "details"
    readonly property bool clipboardMode: mode === "clipboard"
    readonly property bool spotlightModalActive: resultsPanel.modalActive
    readonly property bool clipboardCanRestore: clipboardProvider.canRestore
    readonly property bool wallpaperMode: mode === "wallpapers"
    readonly property bool appGridMode: mode === "apps" && session.appsLayout === "grid"
    readonly property bool showing: windowPhase !== "hidden" && root.visible
    readonly property bool windowActive: searchBar.Window.active
    readonly property bool searchHasFocus: searchBar.inputActiveFocus
    readonly property real searchMainLeft: searchBar.mainLeft
    readonly property real searchMainRight: searchBar.mainRight
    readonly property real searchRequestedWidth: searchBar.requestedMainWidth
    readonly property real webPressDepth: searchBar.pressDepth
    readonly property real webPressScaleX: searchBar.pressScaleX
    readonly property real webPressScaleY: searchBar.pressScaleY
    readonly property real searchShadowBlur: searchBar.pressShadowBlur
    readonly property real searchShadowVerticalOffset: searchBar.pressShadowVerticalOffset
    readonly property real resultsPanelWidth: resultsPanel.width
    readonly property real resultsPanelHeight: resultsPanel.height
    readonly property int wallpaperGridColumns: resultsPanel.wallpaperColumnCount
    readonly property real wallpaperPreviewWidth: resultsPanel.wallpaperPreviewWidth
    readonly property int blurRegionCount: spotlightBlur.regionObjects.length

    // The source stays mapped during a platform drag; let the pointer reach
    // the Dock's separate layer surface outside the launcher card.
    mask: Region {
        x: DockService.externalDragActive ? spotlightRoot.x : 0
        y: DockService.externalDragActive ? spotlightRoot.y : 0
        width: DockService.externalDragActive ? spotlightRoot.width : root.width
        height: DockService.externalDragActive ? spotlightRoot.height : root.height
    }

    Connections {
        target: DockService
        function onExternalDragActiveChanged() {
            if (DockService.externalDragActive)
                return;
            if (root.closeAfterDrag) {
                root.closeAfterDrag = false;
                root.requestClose();
            } else {
                root.focusSpotlight();
            }
        }
    }

    Loader {
        id: locationPickerLoader
        active: false
        onLoaded: item.openWindow()
        sourceComponent: LocationPicker {
            visible: false
            active: false
        }
    }

    SpotlightSessionController {
        id: session
        onCommandRejected: searchBar.flashError()
        onBaseNavigationRequested: mode => {
            if (!root.showing || root.windowPhase === "closing")
                return;
            Qt.callLater(() => {
                if (root.mode !== mode || session.slashDraft)
                    return;
                if (mode === "clipboard")
                    clipboardProvider.refresh();
                if (mode === "wallpapers")
                    wallpaperProvider.refresh();
            });
        }
        onContextRestored: {
            root.focusSpotlight();
            if (root.mode === "clipboard")
                Qt.callLater(clipboardProvider.refresh);
        }
        onSelectionRestored: id => Qt.callLater(() => {
            root.selectedResultId = id;
            root.reconcileSelection();
        })
        onActionRequested: id => {
            if (id === "theme.light" || id === "theme.dark")
                ThemeService.setThemeMode(id === "theme.dark" ? "dark" : "light");
            else {
                const activation = {
                    provider: id === "location.open" ? "map" : "settings-open"
                };
                if (root.windowPhase === "hidden")
                    root.executeSearchActivation(activation);
                else {
                    root.pendingSearchActivation = activation;
                    root.requestClose();
                }
            }
        }
    }
    SpotlightCommandProvider {
        id: commandProvider
        active: root.showing && root.mode === "commands"
        query: root.contentQuery
        sessionState: ({
                           mode: session.baseMode,
                           tool: session.tool
                       })
    }
    Connections {
        target: SpotlightToolService
        function onResultChanged() {
            root.toolCandidateIndex = 0;
        }
    }
    Binding {
        target: SpotlightToolService
        property: "active"
        value: root.showing && root.windowPhase !== "closing" && root.toolMode
    }
    Binding {
        target: SpotlightToolService
        property: "tool"
        value: root.toolMode ? root.mode : ""
    }
    Binding {
        target: SpotlightToolService
        property: "query"
        value: root.mode === "currency" ? currency.expression : templates.active ? templates.expression :
                                                                                   root.toolMode ? root.query :
                                                                                                   ""
    }
    Binding {
        target: SpotlightToolService
        property: "instance"
        value: session.state.serial
    }

    SpotlightTemplateController {
        id: templates
        mode: root.mode
        onTemplateSelectionRequested: {
            root.query = "";
            root.focusSpotlight();
        }
    }
    SpotlightCurrencyController {
        id: currency
        active: root.showing && root.windowPhase !== "closing" && root.mode === "currency"
    }
    onModeChanged: Qt.callLater(() => {
        templates.reset();
        if (root.mode === "currency") {
            currency.reset(root.query);
            root.query = "";
        }
    })

    SpotlightStyle {
        id: style
    }

    SpotlightAppProvider {
        id: appProvider
        active: root.showing && root.windowPhase !== "closing" && root.mode === "apps"
        query: active ? root.contentQuery : ""
        order: session.appsOrder
        limit: session.appsLayout === "grid" ? 0 : 50
    }

    SpotlightWallpaperProvider {
        id: wallpaperProvider
        active: root.showing && root.windowPhase !== "closing" && root.mode === "wallpapers"

        query: active ? root.contentQuery : ""
    }

    SpotlightFileProvider {
        id: fileProvider
        active: root.showing && root.windowPhase !== "closing" && root.mode === "files"
        query: active ? root.contentQuery : ""
        onActivated: root.requestClose()
    }

    SpotlightSearchProvider {
        id: searchProvider
        active: root.showing && root.windowPhase !== "closing" && ["search", "settings", "actions"].includes(
                    root.mode)
        filter: ["settings", "actions"].includes(root.mode) ? root.mode : ""
        query: active ? root.contentQuery : ""
        capacities: resultsPanel.searchCapacities
        retainedResultId: root.mode === "search" && !root.queryUpdating ? root.selectedResultId : ""
        onModeRequested: (mode, query) => {
            root.query = query;
            if (mode === "web")
                root.enterWeb();
            else
                root.setLocalMode(mode);
            root.setRailExpanded(false);
        }
        onCloseRequested: root.requestClose()
        onDeferredRequested: (provider, sourceId, query) => {
            root.pendingSearchActivation = {
                provider: provider,
                sourceId: sourceId,
                query: query
            };
            root.requestClose();
        }
    }

    ShortcutRecorder {
        id: modifierSnapshot
        target: searchBar
        enabled: false
    }

    function syncControlHeld() {
        root.controlHeld = root.showing && root.windowActive && root.searchHasFocus &&
                !root.spotlightModalActive && (modifierSnapshot.currentModifiers() & Qt.ControlModifier)
                !== 0;
    }
    onWindowActiveChanged: Qt.callLater(root.syncControlHeld)
    onSearchHasFocusChanged: Qt.callLater(root.syncControlHeld)
    onSpotlightModalActiveChanged: Qt.callLater(root.syncControlHeld)
    onShowingChanged: Qt.callLater(root.syncControlHeld)

    function releaseControl(event) {
        root.controlHeld = event.key !== Qt.Key_Control && (event.modifiers & Qt.ControlModifier) !== 0;
    }

    SpotlightClipboardProvider {
        id: clipboardProvider
        active: root.showing && root.windowPhase !== "closing" && root.mode === "clipboard"

        query: active ? root.contentQuery : ""
        onRestored: id => root.finishClipboardRestore(id)
        onRestoreFailed: (id, code, message) => root.failClipboardRestore(id, code, message)
        onDeleteFailed: (id, code, message) => {
            root.clipboardSelectionRecoveryPending = false;
            root.clipboardSelectionRecoveryTargetId = "";
            root.clipboardSelectionRecoveryId = "";
        }
    }

    Timer {
        id: clipboardFeedbackTimer

        repeat: false
        onTriggered: {
            if (root.clipboardActionKeepOpen) {
                root.resetClipboardAction();
                return;
            }
            root.requestClose();
        }
    }

    function normalizedMode(value) {
        const requested = String(value || "").toLowerCase();
        return requested === "search" || requested === "apps" || requested === "wallpapers" || requested
                === "clipboard" || requested === "files" || requested === "commands" ? requested : "";
    }

    function modeIndex(value) {
        if (value === "files")
            return 3;
        if (value === "wallpapers")
            return 1;
        if (value === "clipboard")
            return 2;
        return value === "apps" ? 0 : -1;
    }

    function modeForIndex(index) {
        return ["apps", "wallpapers", "clipboard", "files"][Math.max(0, Math.min(style.modeButtonCount - 1,
                                                                                 index))];
    }

    function animateWindow(target) {
        root._windowAnimationTarget = target;
        windowAnimation.stop();
        windowAnimation.from = root.windowProgress;
        windowAnimation.to = target;
        windowAnimation.duration = Math.max(1, (target > root.windowProgress ? style.windowOpenDuration :
                                                                               style.windowCloseDuration)
                                            * Math.abs(target - root.windowProgress));
        windowAnimation.restart();
    }

    function animateRail(target) {
        root._railAnimationTarget = target;
        railAnimation.stop();
        railAnimation.from = root.railProgress;
        railAnimation.to = target;
        railAnimation.duration = Math.max(1, style.railDuration * Math.abs(target - root.railProgress));
        railAnimation.restart();
    }

    function animateWeb(target) {
        root._webAnimationTarget = target;
        webAnimation.stop();
        webAnimation.from = root.webProgress;
        webAnimation.to = target;
        webAnimation.duration = Math.max(1, style.webDuration * Math.abs(target - root.webProgress));
        webAnimation.restart();
    }

    function openSpotlight(requestedMode) {
        if (DockService.externalDragActive)
            return false;
        root.pendingWebUrl = "";
        root.pendingSearchActivation = null;
        SpotlightSearchService.cancelActivation();
        if (root.windowPhase === "hidden" || root.windowPhase === "closing")
            root.query = "";
        const localMode = normalizedMode(requestedMode || "search");
        if (localMode !== "")
            setLocalMode(localMode);
        else if (root.windowPhase === "hidden")
            setLocalMode("search");

        if (root.windowPhase === "open" || root.windowPhase === "opening") {
            root.focusSpotlight();
            return true;
        }

        if (!root.visible)
            root.visible = true;
        root.windowPhase = "opening";
        if (root.mode === "clipboard")
            clipboardProvider.refresh();
        if (root.mode === "wallpapers")
            wallpaperProvider.refresh();
        root.animateWindow(1);
        root.focusSpotlight();
        return true;
    }

    function focusSpotlight() {
        if (!root.showing || root.spotlightModalActive || DockService.externalDragActive)
            return;
        Qt.callLater(() => {
            if (root.showing && !root.spotlightModalActive && !DockService.externalDragActive)
                searchBar.focusInput();
        });
    }

    function requestClose() {
        if (DockService.externalDragActive) {
            root.closeAfterDrag = true;
            return true;
        }
        if (root.windowPhase === "hidden" || root.windowPhase === "closing")
            return false;
        root.controlHeld = false;
        root.windowPhase = "closing";
        root.modeRailExpanded = false;
        root.modeFocusIndex = -1;
        root.animateRail(0);
        root.animateWindow(0);
        return true;
    }

    function toggleWindow() {
        if (root.windowPhase === "hidden" || root.windowPhase === "closing")
            return root.openSpotlight();
        return root.requestClose();
    }

    function openWindow() {
        return root.openSpotlight();
    }

    function setRailExpanded(expanded) {
        if (root.modeRailExpanded === expanded && root._railAnimationTarget === (expanded ? 1 : 0))
            return;
        root.modeRailExpanded = expanded;
        if (!expanded)
            root.modeFocusIndex = -1;
        root.animateRail(expanded ? 1 : 0);
    }

    function setLocalMode(requestedMode) {
        if (DockService.externalDragActive)
            return false;
        const localMode = normalizedMode(requestedMode);
        if (!localMode)
            return false;
        if (root.mode === "clipboard")
            root.resetClipboardAction();
        session.switchMode(localMode, true);
        root.clipboardSelectionRecoveryPending = false;
        root.focusSpotlight();
        return true;
    }

    function runCommand(name) {
        if (DockService.externalDragActive)
            return "BUSY";
        const entry = Commands.exact(name);
        if (!entry || entry.kind === "override")
            return "INVALID_COMMAND";
        if (entry.kind === "mode") {
            root.openSpotlight(entry.value);
            return "OK";
        }
        if (entry.kind === "tool") {
            root.openSpotlight("search");
            session.activate(entry.id, "", false);
            root.setRailExpanded(false);
            root.focusSpotlight();
            return "OK";
        }
        return session.activate(entry.id, "", false) ? "OK" : "INVALID_COMMAND";
    }

    function executeSearchActivation(activation) {
        if (!activation)
            return;
        if (activation.provider === "map") {
            if (locationPickerLoader.item)
                locationPickerLoader.item.openWindow();
            else
                locationPickerLoader.active = true;
        } else if (activation.provider === "settings-open")
            ControlCenterService.openOrFocus();
        else if (activation.provider === "settings")
            ControlCenterService.openSearch(activation.sourceId);
        else if (activation.provider === "actions")
            SpotlightCatalog.execute(activation.sourceId);
        else if (activation.provider === "web")
            SpotlightSearchService.openUrl(SpotlightSearchService.searchUrl(activation.query, true));
    }

    function openWebMode() {
        if (!root.showing || root.windowPhase === "closing")
            root.openSpotlight("search");
        return root.enterWeb();
    }
    function enterWeb() {
        if (session.tool !== "web")
            session.enterTool("web", root.query, false);
        root.setRailExpanded(false);
        root.focusSpotlight();
        return true;
    }
    function exitWeb() {
        return session.tool === "web" && session.pop();
    }

    function moveModeFocus(delta) {
        if (!root.modeRailExpanded) {
            root.modeFocusIndex = Math.max(0, root.modeIndex(root.mode));
            root.setRailExpanded(true);
            return;
        }
        const current = root.modeFocusIndex < 0 ? 0 : root.modeFocusIndex;
        root.modeFocusIndex = (current + delta + style.modeButtonCount) % style.modeButtonCount;
    }

    function selectResult(index) {
        if (root.activeResults.length === 0 || index < 0) {
            root.selectedResultIndex = -1;
            root.selectedResultId = "";
            return false;
        }

        const bounded = Math.max(0, Math.min(root.activeResults.length - 1, index));
        const result = root.activeResults[bounded];
        root.selectedResultIndex = bounded;
        root.selectedResultId = result && result.id !== undefined ? String(result.id) : "";
        if (!session.applying && !session.slashDraft)
            session.rememberSelection(root.selectedResultId);
        return true;
    }

    function moveSelectionByOffset(offset) {
        if (root.mode === "currency" && currency.move(offset))
            return;
        if (templates.active && templates.move(offset))
            return;
        if (root.toolMode && SpotlightToolService.state === "ambiguous" && SpotlightToolService.result) {
            root.toolCandidateIndex = Math.max(0, Math.min(SpotlightToolService.result.candidates.length - 1,
                                                           root.toolCandidateIndex + offset));
            return;
        }
        if (session.slashDraft)
            root.commandSelectionExplicit = true;
        if (root.mode === "web" || root.activeResults.length === 0)
            return;
        const current = root.selectedResultIndex < 0 ? 0 : root.selectedResultIndex;
        if (root.mode === "wallpapers" && wallpaperProvider.hasMore && current + offset >= root.activeResults.length
                - 1) {
            wallpaperProvider.loadMore(current + Math.abs(offset) + root.wallpaperGridColumns * 2);
        }
        root.selectResult(Math.max(0, Math.min(root.activeResults.length - 1, current + offset)));
    }

    function moveSelection(direction) {
        root.moveSelectionByOffset(resultsPanel.navigationStep(direction));
    }

    function reconcileSelection() {
        if (session.slashDraft)
            return;
        if (root.activeResults.length === 0) {
            root.clipboardSelectionRecoveryPending = false;
            root.clipboardSelectionRecoveryTargetId = "";
            root.clipboardSelectionRecoveryId = "";
            root.selectResult(-1);
            return;
        }

        if (root.clipboardSelectionRecoveryPending) {
            const targetId = root.clipboardSelectionRecoveryTargetId;
            const targetStillPresent = root.activeResults.some(result => result && String(result.id || "")
                                                                         === targetId);
            if (targetStillPresent) {
                const targetIndex = root.activeResults.findIndex(result => result && String(result.id || "")
                                                                           === targetId);
                if (targetIndex >= 0)
                    root.selectResult(targetIndex);
                return;
            }

            const recoveryId = root.clipboardSelectionRecoveryId;
            root.clipboardSelectionRecoveryPending = false;
            root.clipboardSelectionRecoveryTargetId = "";
            root.clipboardSelectionRecoveryId = "";
            if (recoveryId !== "") {
                for (let index = 0; index < root.activeResults.length; index += 1) {
                    const result = root.activeResults[index];
                    if (result && String(result.id) === recoveryId) {
                        root.selectResult(index);
                        return;
                    }
                }
            }
        }

        let restoredIndex = -1;
        if (root.selectedResultId !== "") {
            for (let index = 0; index < root.activeResults.length; index += 1) {
                const result = root.activeResults[index];
                if (result && String(result.id) === root.selectedResultId) {
                    restoredIndex = index;
                    break;
                }
            }
        }
        root.selectResult(restoredIndex >= 0 ? restoredIndex : 0);
    }

    function openWebQuery() {
        const value = String(root.query || "").trim();
        if (value === "")
            return false;
        if (root.windowPhase === "closing" || root.windowPhase === "hidden")
            return false;
        root.pendingWebUrl = SpotlightSearchService.searchUrl(value);
        return root.requestClose();
    }

    function resetClipboardAction() {
        clipboardFeedbackTimer.stop();
        root.clipboardActionState = "idle";
        root.clipboardActionEntryId = "";
        root.clipboardActionKeepOpen = false;
        root.clipboardActionError = "";
    }

    function activateClipboard(keepOpen) {
        if (root.selectedResultIndex < 0)
            return false;
        const result = root.activeResults[root.selectedResultIndex];
        if (!result)
            return false;
        const id = String(result.id || "");
        if (root.clipboardActionState === "copying") {
            if (root.clipboardActionEntryId === id)
                return false;
            root.clipboardActionError = qsTr("A clipboard operation is already running");
            return false;
        }
        clipboardFeedbackTimer.stop();
        root.clipboardActionState = "copying";
        root.clipboardActionEntryId = id;
        root.clipboardActionKeepOpen = keepOpen === true;
        root.clipboardActionError = "";
        if (!clipboardProvider.execute(root.selectedResultIndex)) {
            if (root.clipboardActionState === "copying") {
                root.clipboardActionState = "error";
                root.clipboardActionError = qsTr("Copy failed");
            }
            return false;
        }
        return true;
    }

    function activateResult(index, keepClipboardOpen) {
        if (DockService.externalDragActive)
            return false;
        if (!root.selectResult(index))
            return false;
        if (session.slashDraft)
            return session.activate(root.selectedResultId, session.route.arguments, true);
        return root.activateSelected(keepClipboardOpen === true);
    }

    function finishClipboardRestore(id) {
        if (root.clipboardActionState !== "copying" || String(id) !== root.clipboardActionEntryId)
            return;
        root.clipboardActionState = "copied";
        root.clipboardActionError = "";
        clipboardFeedbackTimer.interval = root.clipboardActionKeepOpen ? 800 : 230;
        clipboardFeedbackTimer.restart();
    }

    function failClipboardRestore(id, code, message) {
        if (root.clipboardActionState === "copying" && root.clipboardActionEntryId !== "" && String(id)
                !== root.clipboardActionEntryId)
            return;
        root.clipboardActionEntryId = String(id);
        root.clipboardActionState = "error";
        root.clipboardActionError = String(message || qsTr("Copy failed"));
        root.clipboardActionKeepOpen = false;
        clipboardFeedbackTimer.stop();
    }

    function deleteClipboardEntry(index) {
        if (index < 0 || index >= root.activeResults.length)
            return false;
        const target = root.activeResults[index];
        if (!target)
            return false;

        root.clipboardSelectionRecoveryPending = root.selectedResultId === String(target.id || "");
        root.clipboardSelectionRecoveryTargetId = root.clipboardSelectionRecoveryPending ? String(target.id
                                                                                                  || "") : "";
        root.clipboardSelectionRecoveryId = "";
        if (root.clipboardSelectionRecoveryPending) {
            const successor = root.activeResults[index + 1] || root.activeResults[index - 1];
            root.clipboardSelectionRecoveryId = successor ? String(successor.id || "") : "";
        }

        const started = clipboardProvider.deleteEntry(index);
        if (!started) {
            root.clipboardSelectionRecoveryPending = false;
            root.clipboardSelectionRecoveryTargetId = "";
            root.clipboardSelectionRecoveryId = "";
        }
        return started;
    }

    function activateSelected(keepClipboardOpen) {
        if (root.windowPhase === "closing" || root.windowPhase === "hidden" || root.queryUpdating)
            return false;
        if (root.modeRailExpanded && root.modeFocusIndex >= 0) {
            root.setLocalMode(root.modeForIndex(root.modeFocusIndex));
            root.setRailExpanded(false);
            return true;
        }
        if (session.slashDraft)
            return session.executeSlash();
        if (root.mode === "commands")
            return session.activate(root.selectedResultId, "", false);
        if (root.toolMode) {
            if (root.mode === "currency") {
                if (currency.choosing)
                    return currency.choose(currency.selected);
                return currency.copyAnswer();
            }
            if (templates.active && templates.choices.length)
                return templates.choose(templates.selected);
            if (SpotlightToolService.state === "ambiguous" && SpotlightToolService.result) {
                const candidate = SpotlightToolService.result.candidates[root.toolCandidateIndex];
                if (candidate)
                    SpotlightToolService.confirmFold(candidate.fold);
                return !!candidate;
            }
            return SpotlightToolService.copy();
        }
        if (root.mode === "web")
            return root.openWebQuery();
        if (root.selectedResultIndex < 0)
            return false;

        if (["search", "settings", "actions"].includes(root.mode))
            return searchProvider.activate(root.selectedResultId);
        if (root.mode === "apps") {
            if (appProvider.execute(root.selectedResultIndex)) {
                root.requestClose();
                return true;
            }
            return false;
        }
        if (root.mode === "files")
            return fileProvider.execute(root.selectedResultIndex, false);
        if (root.mode === "wallpapers")
            return wallpaperProvider.execute(root.selectedResultIndex);
        if (root.mode === "clipboard")
            return root.activateClipboard(keepClipboardOpen === true);
        return false;
    }

    function modeButtonCenterX(index) {
        return searchBar.buttonCenterX(index);
    }

    function resultNavigationStep(direction) {
        return resultsPanel.navigationStep(direction);
    }

    function clipboardActivationAreaAt(index) {
        return resultsPanel.clipboardActivationAreaAt(index);
    }

    function clipboardLayoutAt(index) {
        return resultsPanel.clipboardLayoutAt(index);
    }

    function webPressDepthAt(progress) {
        return searchBar.pressDepthForProgress(progress);
    }

    function webPressScaleXAt(progress) {
        return searchBar.pressScaleXForProgress(progress);
    }

    function webPressScaleYAt(progress) {
        return searchBar.pressScaleYForProgress(progress);
    }

    function webShadowBlurAt(progress) {
        return searchBar.shadowBlurForProgress(progress);
    }

    function webShadowVerticalOffsetAt(progress) {
        return searchBar.shadowVerticalOffsetForProgress(progress);
    }

    function handleEscape() {
        if (root.spotlightModalActive)
            return;
        if (root.modeRailExpanded || root.railProgress > 0.001) {
            root.setRailExpanded(false);
        } else if (root.mode === "currency" && currency.dismiss()) {
            return;
        } else if (root.mode === "time" && templates.dismiss()) {
            return;
        } else if (session.tool || (root.mode === "commands" && session.state.parent)) {
            session.pop();
        } else if (root.query !== "") {
            root.query = "";
        } else {
            root.requestClose();
        }
    }

    function handleKey(event, fromSearch) {
        if (DockService.externalDragActive) {
            event.accepted = true;
            return;
        }
        if (root.spotlightModalActive)
            return;
        root.controlHeld = event.key === Qt.Key_Control || (event.modifiers & Qt.ControlModifier) !== 0;
        if (searchBar.inputComposing) {
            event.accepted = false;
            return;
        }
        const control = (event.modifiers & Qt.ControlModifier) !== 0;
        const shift = (event.modifiers & Qt.ShiftModifier) !== 0;

        if (!fromSearch && event.key === Qt.Key_Backspace) {
            event.accepted = false;
            return;
        }
        if (control && event.key === Qt.Key_0) {
            root.setLocalMode("search");
            root.setRailExpanded(false);
            event.accepted = true;
            return;
        }
        if (control && event.key === Qt.Key_1) {
            root.setLocalMode("apps");
            root.setRailExpanded(false);
            event.accepted = true;
            return;
        }
        if (control && event.key === Qt.Key_2) {
            root.setLocalMode("wallpapers");
            root.setRailExpanded(false);
            event.accepted = true;
            return;
        }
        if (control && event.key === Qt.Key_3) {
            root.setLocalMode("clipboard");
            root.setRailExpanded(false);
            event.accepted = true;
            return;
        }
        if (control && event.key === Qt.Key_4) {
            root.setLocalMode("files");
            root.setRailExpanded(false);
            event.accepted = true;
            return;
        }
        if (control && event.key === Qt.Key_K) {
            root.enterWeb();
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            root.moveModeFocus(event.key === Qt.Key_Backtab || shift ? -1 : 1);
            event.accepted = true;
            return;
        }
        if (root.mode !== "currency" && !templates.editing && fromSearch && !control && !shift && event.key
                === Qt.Key_Backspace && session.canBackspace({
                                                                 selection: searchBar.hasSelection,
                                                                 preedit: searchBar.inputComposing,
                                                                 modal: root.spotlightModalActive,
                                                                 repeat: event.isAutoRepeat,
                                                                 searchFocus: root.searchHasFocus
                                                             })) {
            session.pop();
            event.accepted = true;
            return;
        }
        if (fromSearch && root.modeRailExpanded && (event.key === Qt.Key_Left || event.key
                                                    === Qt.Key_Right)) {
            root.moveModeFocus(event.key === Qt.Key_Left ? -1 : 1);
            event.accepted = true;
            return;
        }
        if (fromSearch && root.modeRailExpanded && event.text && event.text.charCodeAt(0) >= 32 && !control)
            root.setRailExpanded(false);
        if (event.key === Qt.Key_Escape) {
            root.handleEscape();
            event.accepted = true;
            return;
        }
        if (session.slashDraft && event.key !== Qt.Key_Return && event.key !== Qt.Key_Enter) {
            event.accepted = false;
            return;
        }
        const plainArrow = event.modifiers === Qt.NoModifier || event.modifiers === Qt.KeypadModifier;
        if (event.key === Qt.Key_Up && plainArrow) {
            root.moveSelection(-1);
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_Down && plainArrow) {
            root.moveSelection(1);
            event.accepted = true;
            return;
        }
        if (root.mode === "search" && !root.modeRailExpanded && plainArrow
                && resultsPanel.searchHorizontalSelection && (event.key === Qt.Key_Left || event.key
                                                              === Qt.Key_Right)) {
            root.selectResult(resultsPanel.searchNavigationIndex(event.key === Qt.Key_Left ? "left" :
                                                                                             "right"));
            event.accepted = true;
            return;
        }
        const gridNavigation = (root.mode === "wallpapers" || resultsPanel.appGridActive) && !control &&
              !shift;
        if (gridNavigation && event.key === Qt.Key_Left) {
            root.moveSelectionByOffset(-1);
            event.accepted = true;
            return;
        }
        if (gridNavigation && event.key === Qt.Key_Right) {
            root.moveSelectionByOffset(1);
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            const modifiers = event.modifiers & ~Qt.KeypadModifier;
            if (root.mode === "files" && modifiers === Qt.ControlModifier && !root.modeRailExpanded) {
                if (!event.isAutoRepeat)
                    fileProvider.execute(root.selectedResultIndex, true);
            } else if (modifiers === Qt.NoModifier || (root.mode === "clipboard" && modifiers
                                                       === Qt.ShiftModifier)) {
                if (!event.isAutoRepeat)
                    root.activateSelected(root.mode === "clipboard" && shift);
            }
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_Delete && root.mode === "clipboard" && root.selectedResultIndex >= 0) {
            root.deleteClipboardEntry(root.selectedResultIndex);
            event.accepted = true;
        }
    }

    onQueryChanged: {
        root.commandSelectionExplicit = false;
        root.queryUpdating = true;
        // Let the session route settle before forwarding input to providers.
        Qt.callLater(() => {
            if (!session.slashDraft) {
                root.contentQuery = root.query;
                root.selectedResultId = "";
                root.selectedResultIndex = -1;
            }
            root.queryUpdating = false;
            root.reconcileSelection();
        });
    }
    onActiveResultsChanged: {
        if (!root.queryUpdating)
            root.reconcileSelection();
    }

    NumberAnimation {
        id: windowAnimation

        target: root
        property: "windowProgress"
        easing.type: Easing.BezierSpline
        easing.bezierCurve: root._windowAnimationTarget > root.windowProgress ? style.windowEnterCurve :
                                                                                style.windowExitCurve

        onFinished: {
            if (root._windowAnimationTarget >= 1) {
                root.windowProgress = 1;
                root.windowPhase = "open";
                root.focusSpotlight();
                return;
            }
            root.windowProgress = 0;
            root.windowPhase = "hidden";
            root.visible = false;
            if (root.pendingWebUrl !== "") {
                const url = root.pendingWebUrl;
                root.pendingWebUrl = "";
                SpotlightSearchService.openUrl(url);
            }
            const activation = root.pendingSearchActivation;
            root.pendingSearchActivation = null;
            root.query = "";
            session.reset("search");
            root.selectedResultIndex = -1;
            root.selectedResultId = "";
            root.clipboardSelectionRecoveryPending = false;
            root.clipboardSelectionRecoveryTargetId = "";
            root.clipboardSelectionRecoveryId = "";
            root.modeRailExpanded = false;
            root.modeFocusIndex = -1;
            root.railProgress = 0;
            root.webProgress = 0;
            root.resetClipboardAction();
            root.executeSearchActivation(activation);
        }
    }

    NumberAnimation {
        id: railAnimation

        target: root
        property: "railProgress"
        easing.type: Easing.Linear
    }

    NumberAnimation {
        id: webAnimation

        target: root
        property: "webProgress"
        easing.type: Easing.BezierSpline
        easing.bezierCurve: style.webCurve
        onFinished: {
            if (root._webAnimationTarget === 0 && session.visiblePills.length) {
                searchBar.commitPills();
                root.animateWeb(1);
            }
        }
    }

    CompositorBlurRegion {
        id: spotlightBlur

        targetWindow: root
        backgroundItem: searchBar.blurRegionItems[0]
        additionalBackgroundItems: searchBar.blurRegionItems.slice(1).concat([resultsPanel.blurRegionItem,
                                                                              resultsPanel.modalBlurRegionItem,
                                                                              toolPanel])
        blurEnabled: root.showing
    }

    MouseArea {
        anchors.fill: parent
        onPressed: root.syncControlHeld()
        onWheel: root.syncControlHeld()
        onClicked: root.requestClose()
    }

    FocusScope {
        id: spotlightRoot

        focus: true
        Keys.priority: Keys.BeforeItem
        Keys.onPressed: event => root.handleKey(event, root.searchHasFocus)
        Keys.onReleased: event => {
            Qt.callLater(root.syncControlHeld);
        }

        readonly property real baseY: Math.max(Metrics.popupMargin, Math.min(root.height * 0.22
                                                                             - searchBar.height / 2,
                                                                             root.height - searchBar.height
                                                                             - style.resultGap - Math.min(
                                                                                 root.appGridMode
                                                                                 ? style.appGridMaxHeight :
                                                                                   style.resultMaxHeight,
                                                                                 root.height * 0.55)
                                                                             - style.windowBottomMargin))

        width: Math.min(root.wallpaperMode ? style.wallpaperPanelWidth : style.canvasWidth, Math.max(0, root.width
                                                                                                     - Math.min(
                                                                                                         style.windowHorizontalMargin,
                                                                                                         Metrics.popupMargin)
                                                                                                     * 2))
        height: searchBar.height + style.resultGap + Math.max(resultsPanel.height, toolPanel.height)
        anchors.horizontalCenter: parent.horizontalCenter
        y: baseY + style.initialYOffset * (1 - root.windowProgress)
        opacity: root.windowProgress
        scale: style.initialScale + (1 - style.initialScale) * root.windowProgress
        transformOrigin: Item.Top

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
        }

        SpotlightSearchBar {
            id: searchBar

            width: parent.width
            anchors.top: parent.top
            style: style
            currencyController: currency
            templateController: templates
            onCurrencyExitRequested: session.pop()
            mode: root.mode
            modeRailExpanded: root.modeRailExpanded
            modeFocusIndex: root.modeFocusIndex
            railProgress: root.railProgress
            webProgress: root.webProgress
            requestedMainWidth: Math.min(Math.max(0, width - style.effectBleed * 2), Math.max(Math.min(420,
                                                                                                       width), Math.min(
                                                                                                  style.searchWidth,
                                                                                                  width - style.compactSideReserve)))
            text: root.query
            onTextChanged: root.query = text
            onRoutedKey: event => root.handleKey(event, true)
            onReleasedKey: event => root.releaseControl(event)
            onInputComposingChanged: {
                if (inputComposing) {
                    root.controlHeld = false;
                    root.setRailExpanded(false);
                }
            }
            pillEntries: session.visiblePills
            pillError: session.error
            onPillClosed: session.pop()
            onPillTransitionRequested: target => root.animateWeb(target)
            onSearchRequested: {
                root.setLocalMode("search");
                root.setRailExpanded(false);
            }
            onModeClicked: index => {
                root.modeFocusIndex = index;
                root.setLocalMode(root.modeForIndex(index));
                root.setRailExpanded(false);
            }
        }

        SpotlightToolPanel {
            id: toolPanel
            selectedCandidate: root.toolCandidateIndex
            templateController: templates
            currencyController: currency
            onInputFocusRequested: root.focusSpotlight()
            style: style
            visible: root.toolMode
            width: searchBar.requestedMainWidth
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: searchBar.bottom
            anchors.topMargin: style.resultGap
            availableHeight: Math.max(0, root.height - spotlightRoot.baseY - searchBar.height
                                      - style.resultGap - style.windowBottomMargin)
        }
        TapHandler {
            acceptedButtons: Qt.AllButtons
            onPressedChanged: {
                if (pressed)
                    root.controlHeld = false;
            }
        }
        WheelHandler {
            blocking: false
            onWheel: event => root.syncControlHeld()
        }

        SpotlightResultsPanel {
            id: resultsPanel

            onPreviewKey: event => root.handleKey(event, false)
            previewActive: root.windowPhase === "open" || root.windowPhase === "opening"
            selectedClipboardId: root.selectedResultId
            targetWidth: root.clipboardDetailsMode ? Math.min(style.clipboardDetailsWidth,
                                                              spotlightRoot.width) : root.wallpaperMode
                                                     ? Math.min(style.wallpaperPanelWidth,
                                                                spotlightRoot.width) : (root.appGridMode
                                                                                        ? Math.min(
                                                                                              style.appGridPanelWidth,
                                                                                              spotlightRoot.width) :
                                                                                          searchBar.requestedMainWidth)
            width: targetWidth
            // Opening already animates the whole surface. Apply restored
            // window geometry immediately before animating mode changes.
            animationsEnabled: root.windowPhase === "open"

            anchors.top: searchBar.bottom
            anchors.topMargin: style.resultGap
            anchors.horizontalCenter: parent.horizontalCenter
            style: style
            mode: root.mode
            enabled: !session.slashDraft
            appsLayout: session.appsLayout
            clipboardLayout: session.clipboardLayout
            expanded: !root.toolMode && root.mode !== "web" && (root.mode !== "search"
                                                                || root.contentQuery.trim() !== "")

            searchError: searchProvider.error
            results: root.activeResults
            query: root.contentQuery
            wallpaperModel: wallpaperProvider.resultModel
            clipboardModel: clipboardProvider.resultModel
            selectedIndex: session.slashDraft ? -1 : root.selectedResultIndex
            controlHeld: root.controlHeld
            fileState: fileProvider.searchState
            fileError: fileProvider.error
            onRevealRequested: index => fileProvider.execute(index, true)
            loading: root.mode === "files" ? fileProvider.searchState === "loading" : root.clipboardMode
                                             && clipboardProvider.loading
            providerAvailable: root.mode === "files" ? fileProvider.searchState !== "unavailable" :
                                                       !root.clipboardMode || clipboardProvider.available
            canRestore: !root.clipboardMode || clipboardProvider.canRestore
            providerError: root.mode === "files" ? fileProvider.error : root.clipboardMode
                                                   ? clipboardProvider.error : null
            clipboardActionState: root.clipboardActionState
            clipboardActionEntryId: root.clipboardActionEntryId
            clipboardActionError: root.clipboardActionError
            clipboardActionRunning: clipboardProvider.actionRunning || root.clipboardActionState
                                    === "copying" || root.clipboardActionState === "copied"
            wallpaperHasMore: wallpaperProvider.hasMore
            availableHeight: Math.max(0, root.height - spotlightRoot.baseY - searchBar.height
                                      - style.resultGap - style.windowBottomMargin)

            onSearchActivationRequested: id => {
                if (root.windowPhase !== "closing" && !root.queryUpdating)
                    searchProvider.activate(id);
            }
            onSelectionRequested: index => {
                root.selectResult(index);
            }
            onActivationRequested: (index, keepOpen) => {
                root.activateResult(index, keepOpen);
            }
            onDeleteRequested: index => root.deleteClipboardEntry(index)
            onClearRequested: clipboardProvider.clear()
            onInspectionRequested: id => clipboardProvider.requestDetails(id)
            onInspectionReleased: id => clipboardProvider.releaseDetails(id)
            onModalClosed: root.focusSpotlight()
            onWallpaperMoreRequested: minimumCount => wallpaperProvider.loadMore(minimumCount)
        }
    }
}
