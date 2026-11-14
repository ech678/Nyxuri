// Fork & Trim: iNiR modules/ii/bar/Workspaces.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri (B8.3):
//   - Niri only. The Hyprland monitor/branch/back-button paths and
//     HyprlandData are gone; the data plane is CompositorDriver's workspace
//     list and window list (the driver is the only compositor surface).
//   - Column mode (scrollBehaviour "column") is dropped: no Nyxuri config key
//     selects it and the compositor driver exposes no column-focus verbs.
//   - zzz / angel / aurora skin branches are gone; the end4 dots + numbers +
//     occupied-cell visuals remain, with Material tokens as the single skin.
//   - App icons resolve through ApplicationService.iconSource instead of the
//     upstream AppSearch singleton.

import qs.commons
import qs.services
import qs.ui
import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Wayland
import Quickshell.Widgets
import Qt5Compat.GraphicalEffects

Item {
    id: root
    property bool vertical: Config.options.bar.vertical

    readonly property bool showAppIcons: Config.options?.bar?.m3?.workspaces?.showAppIcons ?? true
    readonly property bool alwaysShowNumbers: Config.options?.bar?.m3?.workspaces?.alwaysShowNumbers ?? false
    readonly property bool monochromeIcons: Config.options?.bar?.m3?.workspaces?.monochromeIcons ?? true
    readonly property string indicatorStyle: Config.options?.bar?.m3?.workspaces?.indicatorStyle ?? "dot"
    readonly property var numberMap: Config.options?.bar?.m3?.workspaces?.numberMap ?? []
    readonly property bool perMonitor: true
    readonly property bool wrapAround: true
    readonly property bool invertScroll: false

    readonly property color workspacePrimary: Appearance.colors.colPrimary
    readonly property color workspaceOnPrimary: Appearance.colors.colOnPrimary
    readonly property color workspaceSecondaryContainer: Appearance.colors.colSecondaryContainer
    readonly property color workspaceOnSecondaryContainer: Appearance.colors.colOnSecondaryContainer
    readonly property color workspaceInactive: Appearance.colors.colOnLayer1Inactive
    readonly property color workspaceOnPrimaryReadable: ColorUtils.ensureReadable(root.workspaceOnPrimary, root.workspacePrimary, 4.5)
    readonly property color workspaceOnSecondaryReadable: ColorUtils.ensureReadable(root.workspaceOnSecondaryContainer, root.workspaceSecondaryContainer, 4.5)
    readonly property color workspaceInactiveReadable: ColorUtils.ensureReadable(root.workspaceInactive, Appearance.colors.colLayer1Base, 4.5)

    function _intOr(value, fallback: int): int {
        const parsed = Number(value);
        return isFinite(parsed) ? Math.round(parsed) : fallback;
    }

    function _stringOr(value, fallback: string): string {
        return typeof value === "string" ? value : fallback;
    }

    readonly property string screenName: root.QsWindow.window?.screen?.name ?? ""
    readonly property var outputWorkspaces: {
        const all = CompositorDriver.workspaceList ?? [];
        if (!root.perMonitor || root.screenName.length === 0)
            return all;
        const mine = all.filter(workspace => workspace.output === root.screenName);
        return mine.length > 0 ? mine : all;
    }
    readonly property int workspaceCount: root.outputWorkspaces.length
    readonly property int currentWorkspaceNumber: {
        const index = root.outputWorkspaces.findIndex(workspace => workspace.isActive);
        return index >= 0 ? index + 1 : 1;
    }
    readonly property int workspaceIndexInGroup: Math.max(0, root.currentWorkspaceNumber - 1)

    readonly property var occupiedWorkspaceIds: {
        const ids = new Set();
        const windows = CompositorDriver.windows ?? [];
        for (let i = 0; i < windows.length; i += 1) {
            const id = windows[i]?.workspaceId;
            if (id !== undefined && id !== null)
                ids.add(id);
        }
        return ids;
    }

    readonly property int workspaceButtonWidth: 26
    readonly property real activeWorkspaceMargin: 2
    readonly property real workspaceIconSize: root.workspaceButtonWidth * 0.69
    readonly property real workspaceIconSizeShrinked: root.workspaceButtonWidth * 0.55
    readonly property real workspaceIconOpacityShrinked: 1
    readonly property real workspaceIconMarginShrinked: -4

    property bool showNumbers: false
    Timer {
        id: showNumbersTimer
        interval: (Config?.options.bar.autoHide.showWhenPressingSuper.delay ?? 100)
        repeat: false
        onTriggered: root.showNumbers = true
    }
    Connections {
        target: GlobalStates
        function onSuperDownChanged() {
            if (!Config?.options.bar.autoHide.showWhenPressingSuper.enable)
                return;
            if (GlobalStates.superDown)
                showNumbersTimer.restart();
            else {
                showNumbersTimer.stop();
                root.showNumbers = false;
            }
        }
    }

    function workspaceForSlot(slotNumber): var {
        if (slotNumber < 1 || slotNumber > root.outputWorkspaces.length)
            return null;
        return root.outputWorkspaces[slotNumber - 1] ?? null;
    }

    function workspaceOccupiedFor(slotNumber): bool {
        const workspace = root.workspaceForSlot(slotNumber);
        return workspace ? root.occupiedWorkspaceIds.has(workspace.id) : false;
    }

    function workspaceLabel(slotNumber): string {
        const workspace = root.workspaceForSlot(slotNumber);
        if (workspace) {
            const name = root._stringOr(workspace.name, "");
            if (name.length > 0)
                return name;
        }
        const mapped = root.numberMap?.[slotNumber - 1];
        if (mapped !== undefined && mapped !== null)
            return String(mapped);
        return slotNumber > 0 ? String(slotNumber) : "";
    }

    function appIconForSlot(slotNumber): string {
        const workspace = root.workspaceForSlot(slotNumber);
        if (!workspace)
            return "";
        const windows = CompositorDriver.windowsForWorkspace(workspace.id) ?? [];
        if (windows.length === 0)
            return "";
        const focused = windows.find(entry => entry.isFocused) || windows[0];
        return ApplicationService.iconSource(focused?.appId ?? focused?.app_id ?? "");
    }

    function switchToSlot(slotNumber): void {
        const workspace = root.workspaceForSlot(slotNumber);
        if (workspace)
            CompositorDriver.focusWorkspaceById(workspace.id);
    }

    implicitWidth: root.vertical ? Appearance.sizes.verticalBarWidth : root.workspaceButtonWidth * Math.max(root.workspaceCount, 1)
    implicitHeight: root.vertical ? root.workspaceButtonWidth * Math.max(root.workspaceCount, 1) : Appearance.sizes.barHeight
    visible: root.workspaceCount > 0

    // Scroll handler overlay - captures wheel events above all content
    MouseArea {
        z: 10
        anchors.fill: parent

        onWheel: event => {
            const deltaX = event.angleDelta.x;
            const deltaY = event.angleDelta.y;
            let delta = deltaX !== 0 ? deltaX : -deltaY;
            if (delta === 0)
                return;
            if (root.invertScroll)
                delta = -delta;
            const direction = delta > 0 ? 1 : -1;

            const count = root.workspaceCount;
            const current = root.currentWorkspaceNumber;
            let target = current + direction;
            if (root.wrapAround) {
                if (target > count)
                    target = 1;
                if (target < 1)
                    target = count;
            }
            if (target < 1 || target > count)
                return;
            root.switchToSlot(target);
        }
    }

    // Workspaces - occupied background
    Grid {
        z: 1
        anchors.centerIn: parent

        rowSpacing: 0
        columnSpacing: 0
        columns: root.vertical ? 1 : Math.max(root.workspaceCount, 1)

        Repeater {
            model: root.workspaceCount

            Rectangle {
                id: occupiedCell
                z: 1
                implicitWidth: root.workspaceButtonWidth
                implicitHeight: root.workspaceButtonWidth

                readonly property bool occupied: root.workspaceOccupiedFor(index + 1)
                readonly property bool isCurrent: root.currentWorkspaceNumber === index + 1
                property bool previousOccupied: root.workspaceOccupiedFor(index) && !isCurrent
                property bool rightOccupied: root.workspaceOccupiedFor(index + 2) && !isCurrent
                property real radiusPrev: previousOccupied ? 0 : (width / 2)
                property real radiusNext: rightOccupied ? 0 : (width / 2)

                topLeftRadius: radiusPrev
                bottomLeftRadius: root.vertical ? radiusNext : radiusPrev
                topRightRadius: root.vertical ? radiusPrev : radiusNext
                bottomRightRadius: radiusNext

                color: ColorUtils.transparentize(root.workspaceSecondaryContainer, 0.4)
                opacity: occupied && !isCurrent ? 1 : 0

                Behavior on color {
                    animation: Appearance.animation.elementMoveFast.colorAnimation.createObject(this)
                }
                Behavior on opacity {
                    animation: NumberAnimation {
                        duration: Appearance.animation.elementMove.duration
                        easing.type: Appearance.animation.elementMove.type
                        easing.bezierCurve: Appearance.animation.elementMove.bezierCurve
                    }
                }
                Behavior on radiusPrev {
                    animation: NumberAnimation {
                        duration: Appearance.animation.elementMove.duration
                        easing.type: Appearance.animation.elementMove.type
                        easing.bezierCurve: Appearance.animation.elementMove.bezierCurve
                    }
                }
                Behavior on radiusNext {
                    animation: NumberAnimation {
                        duration: Appearance.animation.elementMove.duration
                        easing.type: Appearance.animation.elementMove.type
                        easing.bezierCurve: Appearance.animation.elementMove.bezierCurve
                    }
                }
            }
        }
    }

    // Active workspace indicator
    Rectangle {
        z: 2
        radius: Math.min(width, height) / 2
        color: root.workspacePrimary
        Behavior on radius {
            enabled: Appearance.animationsEnabled
            NumberAnimation {
                duration: Appearance.animation.elementMoveFast.duration
                easing.type: Appearance.animation.elementMoveFast.type
                easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
            }
        }
        Behavior on color {
            enabled: Appearance.animationsEnabled
            ColorAnimation {
                duration: Appearance.animation.elementMoveFast.duration
                easing.type: Appearance.animation.elementMoveFast.type
                easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
            }
        }

        anchors {
            verticalCenter: root.vertical ? undefined : parent.verticalCenter
            horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
        }

        AnimatedTabIndexPair {
            id: idxPair
            index: root.workspaceIndexInGroup
        }
        property real indicatorPosition: Math.min(idxPair.idx1, idxPair.idx2) * root.workspaceButtonWidth + root.activeWorkspaceMargin
        property real indicatorLength: Math.abs(idxPair.idx1 - idxPair.idx2) * root.workspaceButtonWidth + root.workspaceButtonWidth - root.activeWorkspaceMargin * 2
        property real indicatorThickness: root.workspaceButtonWidth - root.activeWorkspaceMargin * 2

        x: root.vertical ? null : indicatorPosition
        implicitWidth: root.vertical ? indicatorThickness : indicatorLength
        y: root.vertical ? indicatorPosition : null
        implicitHeight: root.vertical ? indicatorLength : indicatorThickness
    }

    // Workspaces - numbers, app icons and dot markers
    Grid {
        z: 3
        anchors.fill: parent
        columns: root.vertical ? 1 : Math.max(root.workspaceCount, 1)
        columnSpacing: 0
        rowSpacing: 0

        Repeater {
            model: root.workspaceCount

            Button {
                id: button
                readonly property int workspaceValue: index + 1
                readonly property bool isCurrent: root.currentWorkspaceNumber === workspaceValue
                readonly property bool isOccupied: root.workspaceOccupiedFor(workspaceValue)
                readonly property string iconSource: root.appIconForSlot(workspaceValue)
                readonly property bool hasIcon: root.showAppIcons && iconSource !== ""
                readonly property color markerColor: isCurrent ? root.workspaceOnPrimaryReadable : isOccupied ? root.workspaceOnSecondaryReadable : root.workspaceInactiveReadable

                implicitHeight: root.vertical ? Appearance.sizes.verticalBarWidth : Appearance.sizes.barHeight
                implicitWidth: root.vertical ? Appearance.sizes.verticalBarWidth : root.workspaceButtonWidth
                width: root.vertical ? undefined : root.workspaceButtonWidth
                height: root.vertical ? root.workspaceButtonWidth : undefined

                onPressed: root.switchToSlot(workspaceValue)

                background: Item {
                    id: workspaceButtonBackground
                    implicitWidth: root.workspaceButtonWidth
                    implicitHeight: root.workspaceButtonWidth

                    StyledText {
                        id: numberLabel
                        opacity: (root.showNumbers || (root.alwaysShowNumbers && (!button.hasIcon || root.showNumbers))) ? 1 : 0
                        z: 3

                        anchors.centerIn: parent
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: Appearance.font.pixelSize.small - ((text.length - 1) * (text !== "10") * 2)
                        text: root.workspaceLabel(button.workspaceValue)
                        elide: Text.ElideRight
                        color: button.markerColor

                        Behavior on opacity {
                            animation: NumberAnimation {
                                duration: Appearance.animation.elementMoveFast.duration
                                easing.type: Appearance.animation.elementMoveFast.type
                                easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                            }
                        }
                    }

                    Loader { // Compact workspace marker when no app icon/number is shown
                        id: wsMarker
                        opacity: (root.alwaysShowNumbers || root.showNumbers || button.hasIcon) ? 0 : 1
                        visible: opacity > 0
                        anchors.centerIn: parent
                        sourceComponent: root.indicatorStyle === "icon" ? workspaceIconMarker : workspaceDotMarker

                        Component {
                            id: workspaceDotMarker
                            Rectangle {
                                width: root.workspaceButtonWidth * 0.18
                                height: width
                                radius: width / 2
                                color: button.markerColor
                            }
                        }

                        Component {
                            id: workspaceIconMarker
                            MaterialSymbol {
                                iconSize: root.workspaceButtonWidth * 0.5
                                color: button.markerColor
                                text: {
                                    switch (button.workspaceValue) {
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

                        Behavior on opacity {
                            animation: NumberAnimation {
                                duration: Appearance.animation.elementMoveFast.duration
                                easing.type: Appearance.animation.elementMoveFast.type
                                easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                            }
                        }
                    }

                    Item { // Main app icon
                        anchors.centerIn: parent
                        width: root.workspaceButtonWidth
                        height: root.workspaceButtonWidth
                        opacity: !button.hasIcon ? 0 : (!root.showNumbers && !root.alwaysShowNumbers) ? 1 : root.workspaceIconOpacityShrinked
                        visible: opacity > 0

                        IconImage {
                            id: mainAppIcon
                            anchors.bottom: parent.bottom
                            anchors.right: parent.right
                            anchors.bottomMargin: (!root.showNumbers && !root.alwaysShowNumbers) ? (root.workspaceButtonWidth - root.workspaceIconSize) / 2 : root.workspaceIconMarginShrinked
                            anchors.rightMargin: (!root.showNumbers && !root.alwaysShowNumbers) ? (root.workspaceButtonWidth - root.workspaceIconSize) / 2 : root.workspaceIconMarginShrinked

                            source: button.iconSource
                            implicitSize: (!root.showNumbers && !root.alwaysShowNumbers) ? root.workspaceIconSize : root.workspaceIconSizeShrinked

                            Behavior on opacity {
                                animation: NumberAnimation {
                                    duration: Appearance.animation.elementMoveFast.duration
                                    easing.type: Appearance.animation.elementMoveFast.type
                                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                                }
                            }
                        }

                        Loader {
                            active: root.monochromeIcons
                            anchors.fill: mainAppIcon
                            sourceComponent: Item {
                                Desaturate {
                                    id: desaturatedIcon
                                    visible: false // There's already a color overlay
                                    anchors.fill: parent
                                    source: mainAppIcon
                                    desaturation: 0.8
                                }
                                ColorOverlay {
                                    anchors.fill: desaturatedIcon
                                    source: desaturatedIcon
                                    color: ColorUtils.transparentize(button.markerColor, 0.9)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
