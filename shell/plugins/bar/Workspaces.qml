// Fork & Trim: end4-pC modules/ii/bar/Workspaces.qml (+ WorkspaceModel Niri paths)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri (B9.6):
//   - Niri only. end4's WorkspaceModel Hyprland paths are replaced by an
//     inline projection on CompositorDriver; the model interface end4
//     consumers rely on (shownCount, occupied[], getWorkspaceIdAt,
//     fakeWorkspace, biggestWindow[]) is preserved so WorkspacesAlt.qml
//     stays a verbatim fork.
//   - Hyprland special workspaces have no Niri counterpart: the special
//     workspace pill and the specialBlur blur layers are dropped.
//   - AppIcon (Kirigami.Icon) is not available; app icons resolve through
//     Quickshell IconImage + ApplicationService.iconSource.
//   - WM.switchWorkspace/Relative map to CompositorDriver verbs; right-click
//     toggles the compositor overview via CompositorDriver.toggleOverview(),
//     right press-and-hold still opens the group style editor.
//   - Config keys live in PersonalizationConfig (shown/style/showAppIcons/
//     alwaysShowNumbers/indicatorStyle, and since B9.7 the numberMap preset);
//     monochromeIcons stays an internal bridge default.
//   - end4's useNerdFont number-font branch is dropped (no iconNerd token).

pragma ComponentBehavior: Bound
import qs.commons
import qs.services
import qs.ui
import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Quickshell
import Quickshell.Widgets

ButtonMouseArea {
    id: root
    property color contentColor: Appearance.colors.colOnLayer1
    property bool contentColorOverridden: false
    signal styleEditorRequested

    // ---- Data plane: end4 WorkspaceModel interface, Niri projection ----
    readonly property string monitorName: root.QsWindow.window?.screen?.name ?? ""

    // Fixed slot budget with group paging: pages stay stable (1-10,
    // 11-20, …) on the budget so the active workspace always lands inside
    // the visible group. The visible tail itself is dynamic — see shownCount.
    readonly property int shownBudget: Math.max(1, PersonalizationConfig.barWorkspaceShown)

    readonly property int activeNumber: {
        const ws = (CompositorDriver.workspaceList ?? []).find(w => w.output === root.monitorName && w.isActive);
        return ws?.idx ?? 1;
    }

    // Niri has no Hyprland-style "fake workspace": an active-but-empty
    // workspace is simply not occupied, so the sentinel never matches.
    readonly property int fakeWorkspace: -9999

    // Highest workspace index that exists on this output (niri keeps empty
    // workspaces around — live `niri msg -j workspaces` shows empty trailing
    // indices persisting — so the existing list already carries the tail).
    readonly property int existingMaxIdx: {
        let maxIdx = 0;
        const list = CompositorDriver.workspaceList ?? [];
        for (let i = 0; i < list.length; i += 1) {
            const ws = list[i];
            if (ws && ws.output === root.monitorName && typeof ws.idx === "number" && ws.idx > maxIdx)
                maxIdx = ws.idx;
        }
        return maxIdx;
    }

    readonly property int group: Math.floor((root.activeNumber - 1) / root.shownBudget)

    function getWorkspaceIdAt(index) {
        return root.group * root.shownBudget + index + 1;
    }

    // Slot count follows the iNiR original's dynamicCount semantics
    // (references/iNiR/modules/ii/bar/Workspaces.qml:176-183): on Niri the
    // bar shows exactly the workspaces that exist on this output, empty ones
    // included — niri persists them, so the tail is real and stable while
    // you move between workspaces. end4's fixed grid was Hyprland's
    // pre-created address space and grew seven fictional slots live; the
    // budget only caps the page (and drives paging) instead.
    readonly property int shownCount: Math.max(1, Math.min(root.shownBudget, root.existingMaxIdx - root.group * root.shownBudget))

    function workspaceForNumber(number): var {
        return (CompositorDriver.workspaceList ?? []).find(w => w.output === root.monitorName && w.idx === number) ?? null;
    }

    readonly property var occupied: {
        const winList = CompositorDriver.windows ?? [];
        const out = new Array(root.shownCount);
        for (let i = 0; i < root.shownCount; i++) {
            const ws = root.workspaceForNumber(root.getWorkspaceIdAt(i));
            out[i] = !!ws && winList.some(w => w.workspaceId === ws.id);
        }
        return out;
    }

    readonly property var biggestWindow: {
        const out = new Array(root.shownCount);
        for (let i = 0; i < root.shownCount; i++)
            out[i] = root.biggestWindowForNumber(root.getWorkspaceIdAt(i));
        return out;
    }

    function biggestWindowForNumber(number): var {
        const ws = root.workspaceForNumber(number);
        if (!ws)
            return null;
        const wins = (CompositorDriver.windows ?? []).filter(w => w.workspaceId === ws.id);
        if (wins.length === 0)
            return null;
        return wins.find(w => w.isFocused) ?? wins[0];
    }

    // ---- end4 visual skeleton ----
    property bool vertical: Config.options.bar.vertical
    property bool superPressAndHeld: false // Relevant modifications at bottom of file

    property real workspaceButtonWidth: PersonalizationConfig.barIsMaterial ? 30 : 26
    property real activeWorkspaceMargin: 2
    property real activeWorkspaceSize: workspaceButtonWidth - activeWorkspaceMargin * 2
    property real workspaceIconSize: workspaceButtonWidth * 0.69
    property real workspaceIconSizeShrinked: workspaceButtonWidth * 0.55
    property real workspaceIconOpacityShrinked: 1
    property real workspaceIconMarginShrinked: -4
    property int workspaceIndexInGroup: (root.activeNumber - 1) % root.shownBudget
    readonly property string style: PersonalizationConfig.barWorkspaceStyle
    readonly property bool altStyle: root.style !== "default"
    readonly property real slotLength: root.style === "gnome" ? 16 : root.style === "dots" ? 24 : root.style === "ticks" ? 16 : root.workspaceButtonWidth

    Layout.alignment: vertical ? Qt.AlignHCenter : Qt.AlignVCenter
    Layout.fillWidth: vertical
    Layout.fillHeight: !vertical
    readonly property real barThickness: vertical ? Appearance.sizes.verticalBarWidth : Appearance.sizes.barHeight
    implicitWidth: vertical ? root.barThickness : (altStyle ? (altLoader.item?.implicitWidth ?? 0) : occupiedIndicators.implicitWidth)
    implicitHeight: vertical ? (altStyle ? (altLoader.item?.implicitHeight ?? 0) : occupiedIndicators.implicitHeight) : root.barThickness

    // Interactions
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    hoverEnabled: true
    property int hoverIndex: {
        const position = root.vertical ? mouseY : mouseX;
        if (root.altStyle && altLoader.item)
            return altLoader.item.indexAt(position);
        return Math.floor(position / root.slotLength);
    }

    function switchWorkspaceToHovered() {
        const number = root.getWorkspaceIdAt(root.hoverIndex);
        const ws = root.workspaceForNumber(number);
        if (ws)
            CompositorDriver.focusWorkspaceById(ws.id);
        else
            CompositorDriver.focusWorkspaceOnOutput(root.monitorName, number);
    }
    function switchWorkspaceRelative(direction) {
        if (direction === "next")
            CompositorDriver.focusWorkspaceDown();
        else
            CompositorDriver.focusWorkspaceUp();
    }
    onPressed: mouse => {
        if (mouse.button == Qt.LeftButton)
            switchWorkspaceToHovered();
    }
    onClicked: mouse => {
        if (mouse.button == Qt.RightButton)
            CompositorDriver.toggleOverview();
    }
    onPressAndHold: mouse => {
        if (mouse.button == Qt.RightButton)
            root.styleEditorRequested();
    }
    onWheel: event => {
        if (event.angleDelta.y < 0)
            switchWorkspaceRelative("next");
        else if (event.angleDelta.y > 0)
            switchWorkspaceRelative("prev");
    }

    Loader {
        id: altLoader
        active: root.altStyle
        anchors.centerIn: parent
        sourceComponent: WorkspacesAlt {
            host: root
            model: root
        }
    }

    // Indications
    Item {
        id: regularWorkspaces
        anchors.fill: parent
        visible: !root.altStyle

        /////////////////// Occupied indicators ///////////////////
        StyledRectangle {
            id: occupiedIndicatorsBg
            anchors.fill: parent
            contentLayer: StyledRectangle.ContentLayer.Group
            color: ColorUtils.transparentize(Appearance.m3colors.m3secondaryContainer, 0.4)
            visible: false
        }

        WorkspaceLayout {
            id: occupiedIndicators
            anchors.centerIn: parent

            layer.enabled: true
            visible: false

            Repeater {
                model: root.shownCount
                delegate: Item {
                    id: wsBg
                    required property int index
                    readonly property int wsId: root.getWorkspaceIdAt(index)
                    property bool currentOccupied: root.occupied[index] && wsId != root.fakeWorkspace
                    property bool previousOccupied: index > 0 && root.occupied[index - 1] && (wsId - 1) != root.fakeWorkspace
                    property bool nextOccupied: index < root.shownCount - 1 && root.occupied[index + 1] && (wsId + 1) != root.fakeWorkspace
                    implicitWidth: root.workspaceButtonWidth
                    implicitHeight: root.workspaceButtonWidth

                    // The idea: over-stretch to occupied sides, animate this for a smooth transition.
                    //           masking already prevents weird overlaps
                    Pill {
                        property real undirectionalWidth: root.workspaceButtonWidth * wsBg.currentOccupied
                        property real undirectionalLength: root.workspaceButtonWidth * (1 + 0.5 * wsBg.previousOccupied + 0.5 * wsBg.nextOccupied) * currentOccupied
                        property real undirectionalOffset: (!wsBg.currentOccupied ? 0.5 : -0.5 * wsBg.previousOccupied) * root.workspaceButtonWidth
                        anchors.verticalCenter: root.vertical ? undefined : parent.verticalCenter
                        anchors.horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
                        x: root.vertical ? 0 : undirectionalOffset
                        y: root.vertical ? undirectionalOffset : 0
                        implicitWidth: root.vertical ? undirectionalWidth : undirectionalLength
                        implicitHeight: root.vertical ? undirectionalLength : undirectionalWidth

                        Behavior on undirectionalWidth {
                            animation: Appearance.animation.elementMoveSmall.numberAnimation.createObject(this)
                        }
                        Behavior on undirectionalLength {
                            animation: Appearance.animation.elementMoveSmall.numberAnimation.createObject(this)
                        }
                        Behavior on undirectionalOffset {
                            animation: Appearance.animation.elementMoveSmall.numberAnimation.createObject(this)
                        }
                    }
                }
            }
        }

        MaskMultiEffect {
            id: occupiedIndicatorsMultiEffect
            z: 1
            anchors.centerIn: parent
            implicitWidth: occupiedIndicators.implicitWidth
            implicitHeight: occupiedIndicators.implicitHeight
            source: occupiedIndicatorsBg
            maskSource: occupiedIndicators
        }

        /////////////////// Active indicator ///////////////////
        TrailingIndicator {
            id: activeIndicator
            anchors.fill: parent
            z: 2

            index: root.workspaceIndexInGroup
        }

        /////////////////// Hover ///////////////////
        TrailingIndicator {
            id: interactionIndicator
            z: 3
            index: root.containsMouse ? root.hoverIndex : root.workspaceIndexInGroup
            color: "transparent"
            StateOverlay {
                id: hoverOverlay
                anchors.fill: interactionIndicator.indicatorRectangle
                radius: root.activeWorkspaceSize / 2
                hover: root.containsMouse
                press: root.containsPress
                drag: true // There are too many layers so we need to force this to be a lil more opaque
                contentColor: Appearance.colors.colPrimary
            }
        }

        /////////////////// Numbers ///////////////////
        WorkspaceLayout {
            id: numbersGrid
            z: 4
            layer.enabled: true // For the masking

            Repeater {
                model: root.shownCount
                delegate: NumberWorkspaceItem {}
            }
        }
        Colorizer {
            z: 5
            anchors.fill: numbersGrid
            colorizationColor: Appearance.colors.colOnPrimary
            sourceColor: Appearance.colors.colOnSecondaryContainer

            source: activeIndicator
            maskEnabled: true
            maskSource: numbersGrid

            maskThresholdMin: 0.5
            maskSpreadAtMin: 1
        }

        /////////////////// App icons ///////////////////
        WorkspaceLayout {
            id: appsGrid
            z: 6

            Repeater {
                model: root.shownCount
                delegate: WorkspaceItem {
                    id: wsApp
                    property var biggestWindow: root.biggestWindow[index]
                    property string mainAppIconSource: ApplicationService.iconSource(wsApp.biggestWindow?.appId ?? wsApp.biggestWindow?.app_id ?? "")

                    IconImage {
                        id: appIcon
                        property real cornerMargin: (!root.superPressAndHeld && PersonalizationConfig.barShowAppIcons && wsApp.biggestWindow) ? (root.workspaceButtonWidth - root.workspaceIconSize) / 2 : root.workspaceIconMarginShrinked
                        anchors {
                            bottom: parent.bottom
                            right: parent.right
                            bottomMargin: (parent.implicitHeight - root.workspaceButtonWidth) / 2 + cornerMargin
                            rightMargin: (parent.implicitWidth - root.workspaceButtonWidth) / 2 + cornerMargin
                        }

                        visible: false // Prevent dupe: the colorizer already copies the icon

                        source: wsApp.mainAppIconSource
                        implicitSize: Math.round(root.workspaceIconSize / 2) * 2

                        Behavior on opacity {
                            animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                        }
                        Behavior on cornerMargin {
                            animation: Appearance.animation.elementMoveSmall.numberAnimation.createObject(this)
                        }
                    }

                    Circle {
                        id: iconMask
                        visible: false
                        layer.enabled: true
                        diameter: appIcon.implicitSize
                    }

                    Loader { // Somehow putting this multieffect in a loader prevents it from not showing up
                        id: colorizer
                        anchors.fill: appIcon
                        sourceComponent: Colorizer {
                            implicitWidth: appIcon.implicitWidth
                            implicitHeight: appIcon.implicitHeight
                            colorizationColor: Appearance.m3colors.darkmode ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnPrimary
                            colorization: Config.options?.bar?.m3?.workspaces?.monochromeIcons ? 0.8 : 0.5
                            brightness: 0
                            source: appIcon

                            opacity: !PersonalizationConfig.barShowAppIcons ? 0 : (wsApp.biggestWindow && !root.superPressAndHeld && PersonalizationConfig.barShowAppIcons) ? 1 : wsApp.biggestWindow ? root.workspaceIconOpacityShrinked : 0
                            visible: opacity > 0
                            scale: ((!root.superPressAndHeld && PersonalizationConfig.barShowAppIcons) ? root.workspaceIconSize : root.workspaceIconSizeShrinked) / root.workspaceIconSize

                            Behavior on opacity {
                                animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                            }
                            Behavior on scale {
                                animation: Appearance.animation.elementMoveSmall.numberAnimation.createObject(this)
                            }

                            maskEnabled: true
                            maskSource: iconMask
                            maskThresholdMin: 0.5
                            maskSpreadAtMin: 1
                        }
                    }
                }
            }
        }
    }

    /////////////////// Super key press handling ///////////////////
    Timer {
        id: superPressAndHeldTimer
        interval: (Config?.options.bar.autoHide.showWhenPressingSuper.delay ?? 100)
        repeat: false
        onTriggered: {
            root.superPressAndHeld = true;
        }
    }
    Connections {
        target: GlobalStates
        function onSuperDownChanged() {
            if (!Config?.options.bar.autoHide.showWhenPressingSuper.enable)
                return;
            if (GlobalStates.superDown)
                superPressAndHeldTimer.restart();
            else {
                superPressAndHeldTimer.stop();
                root.superPressAndHeld = false;
            }
        }
    }

    component WorkspaceLayout: Box {
        anchors {
            top: !root.vertical ? parent.top : undefined
            bottom: !root.vertical ? parent.bottom : undefined
            left: root.vertical ? parent.left : undefined
            right: root.vertical ? parent.right : undefined
        }

        rowSpacing: 0
        columnSpacing: 0
        vertical: root.vertical
    }

    component WorkspaceItem: Item {
        required property int index
        readonly property int wsId: root.getWorkspaceIdAt(index)
        implicitWidth: root.vertical ? root.barThickness : root.workspaceButtonWidth
        implicitHeight: root.vertical ? root.workspaceButtonWidth : root.barThickness
    }

    component NumberWorkspaceItem: WorkspaceItem {
        id: wsNum
        property bool hasBiggestWindow: !!root.biggestWindow[index]
        property int wsId: root.getWorkspaceIdAt(index)
        property color contentColor: (root.occupied[wsNum.index] && wsId !== root.fakeWorkspace) ? Appearance.colors.colOnSecondaryContainer : (root.contentColorOverridden ? Qt.alpha(root.contentColor, 0.5) : Appearance.colors.colOnLayer1Inactive)
        property bool showingNumbers: {
            if (root.superPressAndHeld)
                return true;
            if (GlobalStates.screenLocked)
                return false;
            if (PersonalizationConfig.barAlwaysShowNumbers && (!PersonalizationConfig.barShowAppIcons || !wsNum.hasBiggestWindow))
                return true;
            return false;
        }

        FadeLoader {
            shown: !wsNum.showingNumbers
            anchors.centerIn: parent
            Loader {
                anchors.centerIn: parent
                sourceComponent: (PersonalizationConfig.barWorkspaceIndicatorStyle ?? "dot") === "icon" ? iconComponent : dotComponent

                Component {
                    id: dotComponent
                    Circle {
                        anchors.centerIn: parent
                        diameter: root.workspaceButtonWidth * 0.18
                        color: wsNum.contentColor
                    }
                }

                Component {
                    id: iconComponent
                    MaterialSymbol {
                        anchors.centerIn: parent
                        iconSize: root.workspaceButtonWidth * 0.50
                        color: wsNum.contentColor
                        text: {
                            switch (wsNum.wsId) {
                            case 1:
                                return "code";
                            case 2:
                                return "public";
                            case 3:
                                return "music_note";
                            case 4:
                                return "edit_square";
                            case 5:
                                return "image";
                            case 6:
                                return "forum";
                            case 7:
                                return "browser_updated";
                            case 8:
                                return "finance_mode";
                            case 9:
                                return "monitor";
                            case 10:
                                return "analytics";
                            default:
                                return "circle";
                            }
                        }
                    }
                }
            }
        }
        FadeLoader {
            shown: wsNum.showingNumbers
            anchors.centerIn: parent
            StyledText {
                anchors.centerIn: parent
                font.pixelSize: Appearance.font.pixelSize.small - ((text.length - 1) * (text !== "10") * 2)
                color: wsNum.contentColor
                text: Config.options?.bar?.m3?.workspaces?.numberMap[wsNum.wsId - 1] || wsNum.wsId
            }
        }
    }

    component TrailingIndicator: Item {
        id: trailingIndicator
        anchors.fill: parent
        required property int index
        property alias indicatorRectangle: indicatorRect
        property alias color: indicatorRect.color

        property var indexPair: AnimatedTabIndexPair {
            id: idxPair
            index: trailingIndicator.index
        }

        StyledRectangle {
            id: indicatorRect

            anchors {
                verticalCenter: root.vertical ? undefined : parent.verticalCenter
                horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
            }

            property real indicatorPosition: Math.min(idxPair.idx1, idxPair.idx2) * root.workspaceButtonWidth + root.activeWorkspaceMargin
            property real indicatorLength: Math.abs(idxPair.idx1 - idxPair.idx2) * root.workspaceButtonWidth + root.activeWorkspaceSize
            property real indicatorThickness: root.activeWorkspaceSize

            contentLayer: StyledRectangle.ContentLayer.Group
            radius: indicatorThickness / 2
            color: Appearance.colors.colPrimary

            x: root.vertical ? null : indicatorPosition
            y: root.vertical ? indicatorPosition : null
            implicitWidth: root.vertical ? indicatorThickness : indicatorLength
            implicitHeight: root.vertical ? indicatorLength : indicatorThickness
        }
    }
}
