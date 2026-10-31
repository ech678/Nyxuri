pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Quickshell
import qs.commons
import qs.services
import qs.plugins.wallpaper
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Wallpaper page (M3 rebuild): NexusPageBase scaffold. The preview heroes,
// cycle/fill/transition button groups and the Bézier easing editor stay
// custom (visual assets); every standard row — per-monitor toggles, output
// selectors, parallax switches and sliders, overview image-effect sliders —
// is an M1 atom. Wallpaper truth stays with WallpaperService +
// PersonalizationConfig; nothing here writes config directly.
NexusPageBase {
    id: root

    title: I18n.tr("Wallpaper")

    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property string selectedDesktopOutput: ""
    property string selectedOverviewOutput: ""
    property real fillModeGroupRestingWidth: 0

    readonly property bool sharedTransitionParametersEnabled: PersonalizationConfig.wallpaperTransitionType
                                                              !== "none"
    readonly property var outputOptions: {
        const result = [({
                             "value": "",
                             "label": I18n.tr("Global")
                         })];
        for (let index = 0; index < Quickshell.screens.length; index += 1) {
            const name = String(Quickshell.screens[index].name);
            result.push({
                            "value": name,
                            "label": name
                        });
        }
        return result;
    }
    readonly property string currentWallpaperPath: WallpaperService.wallpaperForScreen(selectedDesktopOutput)
    readonly property string currentOverviewPath: WallpaperService.overviewWallpaperForScreen(
                                                      selectedOverviewOutput)
    readonly property bool currentWallpaperIsColor: WallpaperService.isColorSource(currentWallpaperPath)
    readonly property bool currentWallpaperIsImage: WallpaperService.isImagePath(currentWallpaperPath)
    readonly property string currentDesktopFillMode: selectedDesktopOutput !== ""
                                                     ? PersonalizationConfig.monitorFillMode(
                                                           selectedDesktopOutput) :
                                                       PersonalizationConfig.wallpaperFillMode
    readonly property bool panoramaSelected: currentDesktopFillMode === "panorama"
    readonly property real effectivePreferredScale: panoramaSelected ? 1 :
                                                                       PersonalizationConfig.parallaxPreferredScale
    readonly property bool preferredScaleControlEnabled: !panoramaSelected
    readonly property var desktopFillModeOptions: PersonalizationConfig.desktopFillModes.map(option => ({
        "value": option.value,
        "label": option.label,
        "enabled": true
    }))

    Component.onCompleted: WallpaperService.refreshOverviewBackdropRule()

    function chooseWallpaperFile() {
        const base = root.currentWallpaperIsImage ? WallpaperService.parentFolder(root.currentWallpaperPath) :
                                                    PersonalizationConfig.wallpaperFolder;
        wallpaperFileBrowser.openAt(base || PersonalizationConfig.wallpaperFolder);
    }

    function chooseWallpaperColor() {
        wallpaperColorPicker.showFor("desktop", root.selectedDesktopOutput);
    }

    function closeChildWindows() {
        wallpaperFileBrowser.dismiss();
        wallpaperColorPicker.close();
        overviewFileBrowser.dismiss();
        overviewColorPicker.close();
        bezierCurveLayerEditor.dismiss();
    }

    function chooseOverviewFile() {
        const source = root.currentOverviewPath;
        const base = WallpaperService.isImagePath(source) ? WallpaperService.parentFolder(source) :
                                                            PersonalizationConfig.wallpaperFolder;
        overviewFileBrowser.openAt(base || PersonalizationConfig.wallpaperFolder);
    }

    function chooseOverviewColor() {
        overviewColorPicker.showFor("overview", root.selectedOverviewOutput);
    }

    component WallpaperPreview: Item {
        id: preview

        property string sourcePath: ""
        property bool actionsEnabled: true
        property bool paletteEnabled: true
        property string previewSource: ""
        readonly property bool sourceIsColor: WallpaperService.isColorSource(sourcePath)
        readonly property bool sourceIsImage: WallpaperService.isImagePath(sourcePath)

        signal chooseFile
        signal chooseColor
        signal clearWallpaper

        implicitWidth: 340
        implicitHeight: 200

        Rectangle {
            anchors.fill: parent
            radius: Appearance.rounding.normal
            color: preview.sourceIsColor ? preview.sourcePath : Appearance.colors.colLayer2
        }

        WallpaperImageViewport {
            anchors.fill: parent
            anchors.margins: 1
            sourcePath: preview.previewSource || preview.sourcePath
            layer.enabled: true
            layer.effect: MultiEffect {
                maskEnabled: true
                maskSource: previewMask
                maskThresholdMin: 0.5
                maskSpreadAtMin: 1
            }
        }

        Rectangle {
            id: previewMask

            anchors.fill: parent
            anchors.margins: 1
            radius: Appearance.rounding.normal - 1
            color: Appearance.m3colors.m3scrim
            visible: false
            layer.enabled: true
        }

        MaterialSymbol {
            anchors.centerIn: parent
            text: "image"
            iconSize: 34
            color: Appearance.colors.colOnSurfaceVariant
            visible: preview.sourcePath === ""
        }

        WallpaperActions {
            anchors.fill: parent
            actionsEnabled: preview.actionsEnabled
            paletteEnabled: preview.paletteEnabled
            onChooseFile: preview.chooseFile()
            onChooseColor: preview.chooseColor()
            onClearWallpaper: preview.clearWallpaper()
        }
    }

    component EasingActionGroup: StyledButtonGroup {
        id: group

        property bool playing: false
        property bool flipEnabled: true

        signal playClicked
        signal replayClicked
        signal flipClicked

        iconOnly: true
        buttonHeight: 38
        buttonMinWidth: 44
        horizontalPadding: 23
        currentValue: group.playing ? "play" : ""
        model: [({
                     "value": "play",
                     "icon": group.playing ? "pause" : "play_arrow",
                     "tooltip": group.playing ? I18n.tr("Pause") : I18n.tr("Play")
                 }), ({
                          "value": "replay",
                          "icon": "keyboard_double_arrow_left",
                          "tooltip": I18n.tr("Reverse")
                      }), ({
                               "value": "flip",
                               "icon": "swap_vert",
                               "tooltip": I18n.tr("Flip"),
                               "enabled": group.flipEnabled
                           })]
        onValueSelected: value => {
            if (value === "play")
                group.playClicked();
            else if (value === "replay")
                group.replayClicked();
            else if (value === "flip")
                group.flipClicked();
        }
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        NiriSetupPrompt {
            Layout.fillWidth: true
            title: I18n.tr("Overview integration")
            description: I18n.tr(
                             "Create or connect backdrop rules and make the global workspace background transparent.")
            integrationState: NiriConfigService.state("layer-rules")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "layer-rules"
            blocked: NiriConfigService.busy
            error: NiriConfigService.error
            onSetupRequested: NiriConfigService.setup("layer-rules")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: NiriConfigService.snapshot.overviewSatisfied === true && !NiriConfigService.ready(
                         "layer-rules")
            message: I18n.tr("Overview is already configured outside Nyxuri")
        }

        // Current wallpaper
        PreferenceHeader {
            text: I18n.tr("Current wallpaper")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: WallpaperService.lastDesktopError !== ""
            tone: "error"
            message: WallpaperService.lastDesktopError
        }

        ConnectedRect {
            id: currentWallpaperCard

            first: true
            Layout.fillWidth: true
            implicitHeight: currentWallpaperColumn.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: currentWallpaperCard
                declaration:
                    '{"id":"wallpaper.section.current-wallpaper","route":"wallpaper","title":"Current wallpaper","context":"WallpaperPage","icon":"wallpaper","aliases":[]}'
            }

            ColumnLayout {
                id: currentWallpaperColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.medium

                RowLayout {
                    Layout.fillWidth: true
                    spacing: NexusStyle.padding.large

                    WallpaperPreview {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.preferredWidth: 340
                        Layout.preferredHeight: 200
                        sourcePath: root.currentWallpaperPath
                        paletteEnabled: true
                        previewSource: WallpaperPaletteSession.previewForScreen("desktop",
                                                                                root.selectedDesktopOutput)
                        onChooseFile: root.chooseWallpaperFile()
                        onChooseColor: root.chooseWallpaperColor()
                        onClearWallpaper: WallpaperService.clearWallpaper(root.selectedDesktopOutput)
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: NexusStyle.padding.medium

                        StyledText {
                            Layout.fillWidth: true
                            text: root.currentWallpaperPath !== "" ? WallpaperService.basename(
                                                                         root.currentWallpaperPath) : I18n.tr(
                                                                         "No wallpaper selected")
                            color: Appearance.m3colors.m3onSurface
                            font.pixelSize: NexusStyle.font.titleLarge
                            font.weight: NexusStyle.font.titleWeight
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideMiddle
                        }

                        StyledText {
                            Layout.fillWidth: true
                            text: WallpaperService.sourceKind(root.currentWallpaperPath) === "palette"
                                  ? WallpaperService.primaryColor(root.currentWallpaperPath) :
                                    root.currentWallpaperPath
                            color: Appearance.m3colors.m3outline
                            font.family: Fonts.mono
                            font.pixelSize: NexusStyle.font.bodyMedium
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideMiddle
                            visible: root.currentWallpaperPath !== ""
                        }

                        StyledButtonGroup {
                            Layout.alignment: Qt.AlignLeft
                            model: [({
                                         "value": "previous",
                                         "label": I18n.tr("Previous")
                                     }), ({
                                              "value": "random",
                                              "label": I18n.tr("Random")
                                          }), ({
                                                   "value": "next",
                                                   "label": I18n.tr("Next")
                                               })]
                            currentValue: ""
                            onValueSelected: value => {
                                if (value === "previous")
                                    WallpaperService.cyclePrevious();
                                else if (value === "random")
                                    WallpaperService.cycleRandom();
                                else
                                    WallpaperService.cycleNext();
                            }
                        }
                    }
                }

                StyledButtonGroup {
                    id: fillModeButtonGroup

                    Layout.alignment: Qt.AlignHCenter
                    model: root.desktopFillModeOptions
                    currentValue: root.currentDesktopFillMode
                    Component.onCompleted: root.fillModeGroupRestingWidth = implicitWidth
                    onValueSelected: value => WallpaperService.setWallpaperFillModeForScreen(
                                                  root.selectedDesktopOutput, value)
                }
            }
        }

        PreferenceToggle {
            text: I18n.tr("Per-monitor wallpapers")
            checked: PersonalizationConfig.perMonitorWallpaper
            onToggled: PersonalizationConfig.setPerMonitorWallpaper(checked)
        }

        PreferenceSelect {
            last: true
            label: I18n.tr("Output")
            model: root.outputOptions
            currentValue: root.selectedDesktopOutput
            inputRegionService: PopupInputRegionService
            onSelected: value => root.selectedDesktopOutput = value
        }

        // Transition
        PreferenceHeader {
            text: I18n.tr("Transition")
        }

        ConnectedRect {
            id: transitionTypeCard

            first: true
            Layout.fillWidth: true
            implicitHeight: transitionTypeColumn.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: transitionTypeCard
                declaration:
                    '{"id":"wallpaper.section.transition","route":"wallpaper","title":"Transition","context":"WallpaperPage","icon":"wallpaper","aliases":[]}'
            }

            ColumnLayout {
                id: transitionTypeColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                StyledText {
                    Layout.fillWidth: true
                    text: I18n.tr("Transition type")
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                }

                Item {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: root.fillModeGroupRestingWidth > 0
                                           ? root.fillModeGroupRestingWidth : implicitWidth
                    Layout.preferredHeight: transitionButtonColumn.implicitHeight

                    ColumnLayout {
                        id: transitionButtonColumn

                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: NexusStyle.padding.extraSmall

                        StyledButtonGroup {
                            Layout.alignment: Qt.AlignHCenter
                            model: PersonalizationConfig.transitionTypes.slice(0, 5)
                            currentValue: PersonalizationConfig.wallpaperTransitionType
                            horizontalPadding: 24
                            onValueSelected: value => WallpaperService.setWallpaperTransitionType(value)
                        }

                        StyledButtonGroup {
                            Layout.alignment: Qt.AlignHCenter
                            model: PersonalizationConfig.transitionTypes.slice(5)
                            currentValue: PersonalizationConfig.wallpaperTransitionType
                            horizontalPadding: 24
                            onValueSelected: value => WallpaperService.setWallpaperTransitionType(value)
                        }
                    }
                }
            }
        }

        PreferenceSlider {
            label: I18n.tr("Transition duration")
            valueLabel: Math.round(PersonalizationConfig.transitionDurationMs) + " ms"
            value: PersonalizationConfig.transitionDurationMs
            from: 0
            to: 5000
            stepSize: 50
            enabled: root.sharedTransitionParametersEnabled
            onMoved: value => WallpaperService.setTransitionDurationMs(Math.round(value))
        }

        ConnectedRect {
            id: easingCard

            last: true
            Layout.fillWidth: true
            implicitHeight: easingColumn.implicitHeight + NexusStyle.padding.medium * 2

            ColumnLayout {
                id: easingColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.medium

                StyledText {
                    Layout.fillWidth: true
                    text: I18n.tr("Easing curve")
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                }

                RowLayout {
                    id: bezierControls

                    Layout.fillWidth: true
                    spacing: NexusStyle.padding.large
                    enabled: root.sharedTransitionParametersEnabled

                    readonly property real controlsWidth: 172
                    readonly property real chartSide: Math.min(420, Math.max(240, root.cappedWidth
                                                                             - NexusStyle.padding.largeIncreased
                                                                             * 2 - controlsWidth - spacing))

                    BezierCurveEditor {
                        id: easingCurveEditor

                        Layout.preferredWidth: parent.chartSide
                        Layout.preferredHeight: implicitHeight
                        chartSize: parent.chartSide
                        curve: PersonalizationConfig.transitionBezierCurve
                        easingMode: PersonalizationConfig.transitionEasingMode
                        playDurationMs: Math.max(200, PersonalizationConfig.transitionDurationMs)
                        onControlsEdited: nextCurve => WallpaperService.setTransitionBezierCurve(nextCurve)
                        onEditRequested: bezierCurveLayerEditor.openWithCurve(
                                             PersonalizationConfig.transitionBezierCurve)
                    }

                    ColumnLayout {
                        Layout.preferredWidth: bezierControls.controlsWidth
                        Layout.alignment: Qt.AlignTop | Qt.AlignLeft
                        spacing: NexusStyle.padding.medium

                        EasingActionGroup {
                            Layout.alignment: Qt.AlignLeft
                            playing: easingCurveEditor.playing
                            flipEnabled: easingCurveEditor.editable
                            onPlayClicked: easingCurveEditor.togglePlayback()
                            onReplayClicked: easingCurveEditor.reversePlayback()
                            onFlipClicked: easingCurveEditor.flipCurve()
                        }

                        RippleButton {
                            id: editBezierButton

                            Layout.alignment: Qt.AlignLeft
                            Layout.preferredWidth: 154
                            Layout.preferredHeight: 44
                            enabled: easingCurveEditor.editable
                            opacity: enabled ? 1 : 0.45
                            buttonRadius: 13
                            containerColor: Appearance.colors.colPrimaryContainer
                            rippleColor: Appearance.colors.colOnPrimaryContainer
                            stateLayerColor: Appearance.colors.colPrimaryContainerHover
                            pressedStateLayerColor: Appearance.colors.colPrimaryContainerActive
                            Accessible.name: I18n.tr("Edit Bézier curve")
                            onClicked: easingCurveEditor.openCoordinateEditor()

                            contentItem: ButtonLabel {
                                iconName: "edit"
                                primaryText: I18n.tr("Edit Bézier curve")
                                spacing: 8
                                iconSize: 19
                                iconFill: 1
                                iconColor: Appearance.colors.colOnPrimaryContainer
                                primaryColor: Appearance.colors.colOnPrimaryContainer
                                primaryPixelSize: 14
                            }
                        }

                        SplitMenuButton {
                            Layout.alignment: Qt.AlignLeft
                            minimumWidth: 136
                            maximumWidth: 172
                            inputRegionService: PopupInputRegionService
                            model: PersonalizationConfig.transitionEasingModes
                            currentValue: PersonalizationConfig.transitionEasingMode
                            onValueSelected: value => WallpaperService.setTransitionEasingMode(value)
                        }
                    }
                }
            }
        }

        // Parallax effects
        PreferenceHeader {
            text: I18n.tr("Parallax effects")
        }

        PreferenceToggle {
            id: verticalParallaxToggle

            first: true
            text: I18n.tr("Vertical parallax")
            checked: PersonalizationConfig.parallaxVerticalEnabled
            onToggled: PersonalizationConfig.setParallaxVerticalEnabled(checked)

            SettingsSearchAnchor {
                target: verticalParallaxToggle
                declaration:
                    '{"id":"wallpaper.section.parallax-effects","route":"wallpaper","title":"Parallax effects","context":"WallpaperPage","icon":"wallpaper","aliases":[]}'
            }
        }

        PreferenceToggle {
            text: I18n.tr("Follow workspaces")
            enabled: PersonalizationConfig.parallaxVerticalEnabled
            checked: PersonalizationConfig.parallaxFollowWorkspaces
            onToggled: PersonalizationConfig.setParallaxFollowWorkspaces(checked)
        }

        PreferenceToggle {
            text: I18n.tr("Follow sidebars")
            checked: PersonalizationConfig.parallaxFollowSidebars
            onToggled: PersonalizationConfig.setParallaxFollowSidebars(checked)
        }

        PreferenceToggle {
            text: I18n.tr("Follow tiled-window focus")
            checked: PersonalizationConfig.parallaxFollowTiledColumns
            onToggled: PersonalizationConfig.setParallaxFollowTiledColumns(checked)
        }

        PreferenceSlider {
            enabled: root.preferredScaleControlEnabled
            label: I18n.tr("Wallpaper scale")
            valueLabel: Number(root.effectivePreferredScale).toFixed(2)
            value: root.effectivePreferredScale
            from: 1
            to: 1.35
            stepSize: 0.01
            onMoved: value => PersonalizationConfig.setParallaxPreferredScale(value)
        }

        PreferenceSlider {
            last: true
            label: I18n.tr("Horizontal travel columns")
            valueLabel: Math.round(PersonalizationConfig.parallaxTiledColumnSpan).toString()
            value: PersonalizationConfig.parallaxTiledColumnSpan
            from: 2
            to: 12
            stepSize: 1
            onMoved: value => PersonalizationConfig.setParallaxTiledColumnSpan(Math.round(value))
        }

        // Overview background
        PreferenceHeader {
            text: I18n.tr("Overview background")
        }

        ConnectedRect {
            id: overviewPreviewCard

            first: true
            Layout.fillWidth: true
            implicitHeight: overviewPreviewColumn.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: overviewPreviewCard
                declaration:
                    '{"id":"wallpaper.section.overview-background","route":"wallpaper","title":"Overview background","context":"WallpaperPage","icon":"wallpaper","aliases":[]}'
            }

            ColumnLayout {
                id: overviewPreviewColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.medium

                WallpaperPreview {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 300
                    Layout.preferredHeight: 176
                    sourcePath: root.currentOverviewPath
                    previewSource: WallpaperPaletteSession.previewForScreen("overview",
                                                                            root.selectedOverviewOutput)
                    actionsEnabled: !PersonalizationConfig.overviewUseDesktopWallpaper
                    onChooseFile: root.chooseOverviewFile()
                    onChooseColor: root.chooseOverviewColor()
                    onClearWallpaper: WallpaperService.clearOverviewWallpaper(root.selectedOverviewOutput)
                }

                StyledButtonGroup {
                    Layout.alignment: Qt.AlignHCenter
                    model: PersonalizationConfig.fillModes
                    currentValue: root.selectedOverviewOutput !== ""
                                  ? PersonalizationConfig.overviewMonitorFillMode(
                                        root.selectedOverviewOutput) :
                                    PersonalizationConfig.overviewWallpaperFillMode
                    onValueSelected: value => WallpaperService.setOverviewFillModeForScreen(
                                                  root.selectedOverviewOutput, value)
                }
            }
        }

        PreferenceToggle {
            text: I18n.tr("Enable background")
            checked: PersonalizationConfig.overviewEnabled
            onToggled: PersonalizationConfig.setOverviewEnabled(checked)
        }

        PreferenceToggle {
            text: I18n.tr("Use desktop wallpaper")
            checked: PersonalizationConfig.overviewUseDesktopWallpaper
            onToggled: PersonalizationConfig.setOverviewUseDesktopWallpaper(checked)
        }

        PreferenceToggle {
            text: I18n.tr("Per-monitor wallpapers")
            checked: PersonalizationConfig.overviewPerMonitorWallpaper
            onToggled: PersonalizationConfig.setOverviewPerMonitorWallpaper(checked)
        }

        PreferenceSelect {
            last: true
            label: I18n.tr("Output")
            model: root.outputOptions
            currentValue: root.selectedOverviewOutput
            inputRegionService: PopupInputRegionService
            onSelected: value => root.selectedOverviewOutput = value
        }

        PreferenceHeader {
            text: I18n.tr("Transition type")
        }

        ConnectedRect {
            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: overviewTransitionColumn.implicitHeight + NexusStyle.padding.medium * 2

            ColumnLayout {
                id: overviewTransitionColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.extraSmall

                StyledButtonGroup {
                    Layout.alignment: Qt.AlignHCenter
                    model: PersonalizationConfig.transitionTypes.slice(0, 5)
                    currentValue: PersonalizationConfig.overviewTransitionType
                    onValueSelected: value => PersonalizationConfig.setOverviewTransitionType(value)
                }

                StyledButtonGroup {
                    Layout.alignment: Qt.AlignHCenter
                    model: PersonalizationConfig.transitionTypes.slice(5, 9)
                    currentValue: PersonalizationConfig.overviewTransitionType
                    onValueSelected: value => PersonalizationConfig.setOverviewTransitionType(value)
                }
            }
        }

        PreferenceHeader {
            text: I18n.tr("Image effects")
        }

        PreferenceSlider {
            first: true
            enabled: PersonalizationConfig.overviewEnabled
            label: I18n.tr("Blur")
            valueLabel: Math.round(PersonalizationConfig.overviewBlurRadius) + "%"
            value: PersonalizationConfig.overviewBlurRadius
            from: 0
            to: 100
            stepSize: 1
            onMoved: value => PersonalizationConfig.setOverviewBlurRadius(value)
        }

        PreferenceSlider {
            enabled: PersonalizationConfig.overviewEnabled
            label: I18n.tr("Dim")
            valueLabel: Math.round(PersonalizationConfig.overviewDim * 100) + "%"
            value: PersonalizationConfig.overviewDim
            from: 0
            to: 1
            stepSize: 0.01
            onMoved: value => PersonalizationConfig.setOverviewDim(value)
        }

        PreferenceSlider {
            enabled: PersonalizationConfig.overviewEnabled
            label: I18n.tr("Saturation")
            valueLabel: Number(PersonalizationConfig.overviewSaturation).toFixed(2)
            value: PersonalizationConfig.overviewSaturation
            from: 0
            to: 2
            stepSize: 0.05
            onMoved: value => PersonalizationConfig.setOverviewSaturation(value)
        }

        PreferenceSlider {
            last: true
            enabled: PersonalizationConfig.overviewEnabled
            label: I18n.tr("Contrast")
            valueLabel: Number(PersonalizationConfig.overviewContrast).toFixed(2)
            value: PersonalizationConfig.overviewContrast
            from: 0.5
            to: 2
            stepSize: 0.05
            onMoved: value => PersonalizationConfig.setOverviewContrast(value)
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: WallpaperService.lastOverviewError !== ""
            tone: "error"
            message: WallpaperService.lastOverviewError
        }

        // Non-visual children live inside the content column (NexusPageBase
        // takes a single Item; children on the page root are a type error
        // that kills the whole page — 2026-10-25 lesson).
        WallpaperFileBrowser {
            id: wallpaperFileBrowser

            parentModal: root.parentModal
            startPath: PersonalizationConfig.wallpaperFolder
            onFolderSelected: path => {
                WallpaperService.setWallpaperFolder(path);
            }
            onFileSelected: path => {
                WallpaperService.setWallpaperFromFile(path, root.selectedDesktopOutput);
            }
        }

        WallpaperColorPicker {
            id: wallpaperColorPicker

            parentModal: root.parentModal
        }

        WallpaperFileBrowser {
            id: overviewFileBrowser

            parentModal: root.parentModal
            startPath: PersonalizationConfig.wallpaperFolder
            onFileSelected: path => WallpaperService.setOverviewWallpaper(path, root.selectedOverviewOutput)
        }

        WallpaperColorPicker {
            id: overviewColorPicker

            parentModal: root.parentModal
        }

        BezierCurveLayerEditor {
            id: bezierCurveLayerEditor

            parentModal: root.parentModal
            onCurveEdited: nextCurve => WallpaperService.setTransitionBezierCurve(nextCurve)
        }
    }
}
