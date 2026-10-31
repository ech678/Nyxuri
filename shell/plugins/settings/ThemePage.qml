pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Theme page (M3 rebuild): NexusPageBase scaffold + theme-mode preview cards,
// then panel style / color scheme / transparency / super key / lock screen /
// cursor / icon theme / fonts / matugen templates groups. Every standard row
// is an M1 atom; the preview pair, panel-style card, scheme button groups,
// keycap picker, cursor theme selector and the template list stay custom —
// they are semantic pickers the atom suite deliberately has no shape for.
NexusPageBase {
    id: root

    title: I18n.tr("Theme")

    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property var pendingDeleteTemplate: null

    function requestTemplateDeletion(template) {
        root.pendingDeleteTemplate = template;
        templateDialog.open();
    }

    function closeChildWindows() {
        templateAddWindow.dismiss();
        templateDialog.close();
    }

    Component.onCompleted: NiriConfigService.refresh()

    component PreviewSegmentGroup: Item {
        id: previewGroup

        property bool selected: false
        property bool darkPreview: false
        property color normalFill: darkPreview ? "#5f5961" : "#e1dee2"
        property color selectedFill: Appearance.colors.colPrimary
        property color checkColor: Appearance.colors.colOnPrimary

        implicitWidth: 260
        implicitHeight: 34

        readonly property real gap: 3
        readonly property real segmentHeight: height
        readonly property real firstWidth: Math.round(width * 0.315)
        readonly property real middleWidth: Math.round(width * 0.34)
        readonly property real lastWidth: width - firstWidth - middleWidth - gap * 2

        Rectangle {
            x: 0
            y: 0
            width: previewGroup.firstWidth
            height: previewGroup.segmentHeight
            radius: height / 2
            color: previewGroup.selected ? previewGroup.selectedFill : previewGroup.normalFill
            opacity: previewGroup.selected ? 1 : 0.82
            antialiasing: true

            MaterialSymbol {
                anchors.centerIn: parent
                text: "check"
                iconSize: 16
                fill: 1
                color: previewGroup.checkColor
                visible: previewGroup.selected
            }
        }

        Rectangle {
            x: previewGroup.firstWidth + previewGroup.gap
            y: 0
            width: previewGroup.middleWidth
            height: previewGroup.segmentHeight
            radius: 5
            color: previewGroup.normalFill
            opacity: 0.82
            antialiasing: true
        }

        Rectangle {
            x: previewGroup.firstWidth + previewGroup.middleWidth + previewGroup.gap * 2
            y: 0
            width: previewGroup.lastWidth
            height: previewGroup.segmentHeight
            topLeftRadius: 0
            bottomLeftRadius: 0
            topRightRadius: height / 2
            bottomRightRadius: height / 2
            color: previewGroup.normalFill
            opacity: 0.82
            antialiasing: true
        }
    }

    component ThemePreviewCard: Item {
        id: themeCard

        required property string mode
        required property string title
        property bool darkPreview: false
        readonly property bool active: PersonalizationConfig.themeMode === mode
        readonly property color selectedAccent: Appearance.colors.colPrimary
        readonly property color selectedOnAccent: Appearance.colors.colOnPrimary
        readonly property color outerFill: active ? selectedAccent : Appearance.colors.colLayer1
        readonly property color previewSurface: darkPreview ? "#302d32" : "#fbf7f8"
        readonly property color avatarFill: darkPreview ? "#8a838c" : "#dedde1"
        readonly property color placeholderFill: darkPreview ? "#948b92" : "#dedbdf"
        readonly property color placeholderAltFill: darkPreview ? "#776f75" : "#d3d0d5"
        readonly property color waveFill: active ? selectedAccent : (darkPreview ? "#8a858e" : "#ccc8cd")
        readonly property color trackFill: darkPreview ? "#6d6870" : "#d7d3d8"
        readonly property color labelText: active ? selectedOnAccent : Appearance.colors.colOnLayer1

        signal clicked

        Layout.preferredWidth: 288
        Layout.preferredHeight: 180
        Layout.fillWidth: true
        scale: cardMouse.pressed ? 0.985 : 1

        Behavior on scale {
            NumberAnimation {
                duration: 120
                easing.type: Easing.OutSine
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: 13
            color: themeCard.outerFill
            border.width: 0
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 33
            bottomLeftRadius: 13
            bottomRightRadius: 13
            color: "transparent"

            Text {
                anchors.centerIn: parent
                text: themeCard.title
                color: themeCard.labelText
                font.family: Fonts.ui
                font.pixelSize: 14
                font.weight: Font.Medium
            }
        }

        Rectangle {
            id: previewPane

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 10
            anchors.bottomMargin: 37
            radius: 8
            color: themeCard.previewSurface
            border.width: 0

            Rectangle {
                x: 15
                y: 12
                width: 46
                height: 46
                radius: width / 2
                color: themeCard.avatarFill
                opacity: themeCard.darkPreview ? 0.9 : 0.92
            }

            Column {
                x: 72
                y: 16
                spacing: 8

                Rectangle {
                    width: Math.min(154, previewPane.width - 92)
                    height: 18
                    radius: 5
                    color: themeCard.placeholderFill
                    opacity: themeCard.darkPreview ? 0.85 : 1
                }

                Rectangle {
                    width: Math.min(124, previewPane.width - 118)
                    height: 16
                    radius: 5
                    color: themeCard.placeholderAltFill
                    opacity: themeCard.darkPreview ? 0.95 : 1
                }
            }

            MiniMaterialWaveLine {
                x: 18
                y: 66
                width: previewPane.width - 36
                height: 18
                waveColor: themeCard.waveFill
                trackColor: themeCard.trackFill
                trackOpacity: themeCard.darkPreview ? 0.42 : 0.54
                wavePortion: 0.72
                phaseDuration: 1600
                flowing: themeCard.active
                endDotColor: themeCard.waveFill
            }

            PreviewSegmentGroup {
                x: 13
                y: previewPane.height - height - 8
                width: previewPane.width - 26
                height: 33
                selected: themeCard.active
                darkPreview: themeCard.darkPreview
                selectedFill: themeCard.selectedAccent
                checkColor: themeCard.selectedOnAccent
            }
        }

        MouseArea {
            id: cardMouse

            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: themeCard.clicked()
        }
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Cursor integration gate (Niri config setup).
        NiriSetupPrompt {
            Layout.fillWidth: true
            title: I18n.tr("Cursor integration")
            description: I18n.tr("Create or connect the Nyxuri cursor configuration.")
            integrationState: NiriConfigService.state("cursor")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "cursor"
            blocked: NiriConfigService.busy
            error: NiriConfigService.error
            onSetupRequested: NiriConfigService.setup("cursor")
        }

        // Theme mode preview pair — the page's visual anchor.
        RowLayout {
            Layout.topMargin: NexusStyle.padding.small
            Layout.fillWidth: true
            spacing: NexusStyle.padding.medium

            ThemePreviewCard {
                title: I18n.tr("Light")
                mode: "light"
                darkPreview: false
                onClicked: ThemeService.setThemeMode("light")
            }

            ThemePreviewCard {
                title: I18n.tr("Dark")
                mode: "dark"
                darkPreview: true
                onClicked: ThemeService.setThemeMode("dark")
            }
        }

        // Settings panel style
        PreferenceHeader {
            text: I18n.tr("Settings panel style")
        }

        SettingsPanelStyleCard {
            id: panelStyleCard

            Layout.fillWidth: true

            SettingsSearchAnchor {
                target: panelStyleCard
                declaration:
                    '{"id":"theme.section.settings-panel-style","route":"theme","title":"Settings panel style","context":"ThemePage","icon":"palette","aliases":[]}'
            }
        }

        // matugen color scheme
        PreferenceHeader {
            text: I18n.tr("Color scheme")
        }

        ConnectedRect {
            id: schemeRow

            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: schemeColumn.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: schemeRow
                declaration:
                    '{"id":"theme.section.matugen-color-scheme","route":"theme","title":"matugen color scheme","context":"ThemePage","icon":"palette","aliases":[]}'
            }

            ColumnLayout {
                id: schemeColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.extraSmall

                StyledButtonGroup {
                    Layout.alignment: Qt.AlignLeft
                    model: PersonalizationConfig.matugenSchemes.slice(0, 5)
                    currentValue: PersonalizationConfig.matugenScheme
                    horizontalPadding: 24
                    onValueSelected: value => ThemeService.setMatugenScheme(value)
                }

                StyledButtonGroup {
                    Layout.alignment: Qt.AlignLeft
                    model: PersonalizationConfig.matugenSchemes.slice(5, 9)
                    currentValue: PersonalizationConfig.matugenScheme
                    horizontalPadding: 24
                    onValueSelected: value => ThemeService.setMatugenScheme(value)
                }
            }
        }

        // Transparency and blur
        PreferenceHeader {
            text: I18n.tr("Transparency and blur")
        }

        NiriSetupPrompt {
            Layout.fillWidth: true
            title: I18n.tr("Background effects")
            description: I18n.tr("Create or connect the Nyxuri X-Ray rules.")
            integrationState: NiriConfigService.state("effects")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "effects"
            blocked: NiriConfigService.busy
            error: NiriConfigService.error
            onSetupRequested: NiriConfigService.setup("effects")
        }

        PreferenceSlider {
            id: opacitySlider

            first: true
            label: I18n.tr("Background opacity")
            valueLabel: Math.round(PersonalizationConfig.shellBackgroundOpacity * 100) + " %"
            value: PersonalizationConfig.shellBackgroundOpacity * 100
            from: 0
            to: 100
            stepSize: 1
            onMoved: value => PersonalizationConfig.setShellBackgroundOpacity(value / 100)

            SettingsSearchAnchor {
                target: opacitySlider
                declaration:
                    '{"id":"theme.section.transparency-and-blur","route":"theme","title":"Transparency and blur","context":"ThemePage","icon":"blur_on","aliases":["effects.section.background","general.effects.section.background","effects","general.effects"]}'
            }
        }

        PreferenceToggle {
            text: I18n.tr("Background blur")
            enabled: BlurService.available
            checked: PersonalizationConfig.shellBlurEnabled
            onToggled: PersonalizationConfig.setShellBlurEnabled(checked)
        }

        PreferenceToggle {
            last: true
            text: I18n.tr("Blur wallpaper only")
            subtext: BlurService.niriIntegrationReady ? I18n.tr(
                                                            "Turning this off also blurs windows and uses more resources") :
                                                        I18n.tr("Configure Niri blur integration first")
            enabled: BlurService.available && BlurService.niriIntegrationReady
            checked: PersonalizationConfig.shellBlurXray
            onToggled: PersonalizationConfig.setShellBlurXray(checked)
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: BlurService.lastError !== ""
            tone: "error"
            message: BlurService.lastError
        }

        // Super key appearance
        PreferenceHeader {
            text: I18n.tr("Super key appearance")
        }

        ConnectedRect {
            id: superKeyRow

            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: superKeyFlow.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: superKeyRow
                declaration:
                    '{"id":"theme.section.super-key-appearance","route":"theme","title":"Super key appearance","context":"ThemePage","icon":"palette","aliases":[]}'
            }

            Flow {
                id: superKeyFlow

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                Repeater {
                    model: PersonalizationConfig.superKeyStyles

                    delegate: RippleButton {
                        id: superChoice

                        required property var modelData

                        implicitWidth: 84
                        implicitHeight: 56
                        buttonRadius: NexusStyle.rounding.small
                        containerColor: PersonalizationConfig.superKeyStyle === modelData.value
                                        ? Appearance.m3colors.m3secondaryContainer :
                                          Appearance.m3colors.m3surfaceContainerHigh
                        hoverStateLayerOpacity: 0.08
                        pressedStateLayerOpacity: 0.12
                        focusStateLayerOpacity: 0.12
                        Accessible.name: modelData.label
                        Accessible.role: Accessible.RadioButton
                        Accessible.checked: PersonalizationConfig.superKeyStyle === modelData.value
                        onClicked: PersonalizationConfig.setValue("superKeyStyle", modelData.value)
                        contentItem: Item {
                            ShortcutKeycap {
                                anchors.centerIn: parent
                                keyText: "Super"
                                superStyle: superChoice.modelData.value
                            }
                        }
                        StyledToolTip {
                            text: parent.modelData.label
                            visible: parent.hovered
                        }
                    }
                }
            }
        }

        // Lock screen
        PreferenceHeader {
            text: I18n.tr("Lock screen")
        }

        PreferenceSelect {
            id: lockStyleSelect

            first: true
            last: true
            label: I18n.tr("Lock screen style")
            model: PersonalizationConfig.lockScreenStyles
            currentValue: PersonalizationConfig.lockScreenStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => PersonalizationConfig.setLockScreenStyle(value)

            SettingsSearchAnchor {
                target: lockStyleSelect
                declaration:
                    '{"id":"theme.section.lock-screen","route":"theme","title":"Lock screen","context":"ThemePage","icon":"palette","aliases":[]}'
            }
        }

        // Cursor
        PreferenceHeader {
            text: I18n.tr("Cursor theme")
        }

        ConnectedRect {
            id: cursorThemeRow

            first: true
            enabled: NiriConfigService.ready("cursor")
            Layout.fillWidth: true
            implicitHeight: cursorSelect.height + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: cursorThemeRow
                declaration:
                    '{"id":"theme.section.cursor-theme","route":"theme","title":"Cursor theme","context":"ThemePage","icon":"palette","aliases":[]}'
            }

            CursorThemeSelect {
                id: cursorSelect

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                height: 58
                cursorThemes: ThemeService.availableCursorThemes
                currentCursorTheme: PersonalizationConfig.cursorTheme
                onAccepted: value => ThemeService.setCursorTheme(value)
            }
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: ThemeService.cursorLastError !== ""
            tone: "error"
            message: ThemeService.cursorLastError
        }

        PreferenceSlider {
            enabled: NiriConfigService.ready("cursor")
            label: I18n.tr("Cursor size")
            valueLabel: Math.round(PersonalizationConfig.cursorSize) + " " + I18n.tr("pixels")
            value: PersonalizationConfig.cursorSize
            from: 12
            to: 128
            stepSize: 1
            onMoved: value => ThemeService.setCursorSize(Math.round(value))
        }

        PreferenceToggle {
            enabled: NiriConfigService.ready("cursor")
            text: I18n.tr("Hide while typing")
            checked: PersonalizationConfig.cursorHideWhenTyping
            onToggled: ThemeService.setCursorHideWhenTyping(checked)
        }

        PreferenceSlider {
            last: true
            enabled: NiriConfigService.ready("cursor")
            label: I18n.tr("Hide after timeout")
            valueLabel: PersonalizationConfig.cursorHideAfterInactiveMs === 0 ? I18n.tr("Off") : Math.round(
                                                                                    PersonalizationConfig.cursorHideAfterInactiveMs)
                                                                                + " " + I18n.tr(
                                                                                    "milliseconds")
            value: PersonalizationConfig.cursorHideAfterInactiveMs
            from: 0
            to: 5000
            stepSize: 100
            onMoved: value => ThemeService.setCursorHideAfterInactiveMs(Math.round(value))
        }

        // Icon theme
        PreferenceHeader {
            text: I18n.tr("Icon theme")
        }

        PreferenceSelect {
            id: iconThemeSelect

            first: true
            last: true
            label: I18n.tr("Icon theme")
            model: ThemeService.availableIconThemes
            currentValue: PersonalizationConfig.iconTheme
            inputRegionService: PopupInputRegionService
            onSelected: value => ThemeService.setIconTheme(value)

            SettingsSearchAnchor {
                target: iconThemeSelect
                declaration:
                    '{"id":"theme.section.icon-theme","route":"theme","title":"Icon theme","context":"ThemePage","icon":"palette","aliases":[]}'
            }
        }

        // Fonts
        PreferenceHeader {
            text: I18n.tr("Fonts")
        }

        PreferenceSelect {
            id: uiFontSelect

            first: true
            label: I18n.tr("UI font")
            subtext: I18n.tr("Regular headings, body text, and controls")
            model: FontService.fontOptions
            currentValue: PersonalizationConfig.uiFontFamily
            inputRegionService: PopupInputRegionService
            onSelected: value => PersonalizationConfig.setFontFamily("ui", value)

            SettingsSearchAnchor {
                target: uiFontSelect
                declaration:
                    '{"id":"theme.section.fonts","route":"theme","title":"Fonts","context":"ThemePage","icon":"palette","aliases":[]}'
            }
        }

        PreferenceSelect {
            label: I18n.tr("Monospace font")
            subtext: I18n.tr("Commands, paths, and technical information")
            model: FontService.fontOptions
            currentValue: PersonalizationConfig.monoFontFamily
            inputRegionService: PopupInputRegionService
            onSelected: value => PersonalizationConfig.setFontFamily("mono", value)
        }

        PreferenceSelect {
            label: I18n.tr("Numeric font")
            subtext: I18n.tr("Time, percentages, and system values")
            model: FontService.fontOptions
            currentValue: PersonalizationConfig.numericFontFamily
            inputRegionService: PopupInputRegionService
            onSelected: value => PersonalizationConfig.setFontFamily("numeric", value)
        }

        PreferenceSelect {
            last: true
            label: I18n.tr("Expressive font")
            subtext: I18n.tr("Expressive visual components such as weather")
            model: FontService.fontOptions
            currentValue: PersonalizationConfig.expressiveFontFamily
            inputRegionService: PopupInputRegionService
            onSelected: value => PersonalizationConfig.setFontFamily("expressive", value)
        }

        // Matugen template generation
        PreferenceHeader {
            text: I18n.tr("Matugen template generation")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: TemplateService.error !== ""
            tone: "error"
            message: TemplateService.error
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: !templateAddWindow.visible && TemplateService.operationError !== ""
            tone: "error"
            message: TemplateService.operationError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: ThemeService.generationError !== "" || TemplateService.mirrorError !== ""
            tone: "error"
            message: ThemeService.generationError !== "" ? I18n.tr("Failed to generate Matugen colors") :
                                                           I18n.tr("Failed to write the Noctalia palette mirror")
            StyledToolTip {
                extraVisibleCondition: errorHover.hovered
                text: ThemeService.generationError || TemplateService.mirrorError
            }
            HoverHandler {
                id: errorHover
            }
        }

        ConnectedRect {
            id: templateCard

            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: templateColumn.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: templateCard
                declaration:
                    '{"id":"theme.section.matugen-template-generation","route":"theme","title":"Matugen template generation","context":"ThemePage","icon":"tune","aliases":["advanced.section.matugen-template-generation"]}'
            }

            ColumnLayout {
                id: templateColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                Item {
                    Layout.fillWidth: true
                    implicitHeight: templateActions.implicitHeight

                    InlineBusyIndicator {
                        anchors.right: templateActions.left
                        anchors.rightMargin: NexusStyle.padding.extraSmall
                        anchors.verticalCenter: parent.verticalCenter
                        width: implicitWidth
                        height: implicitHeight
                        busy: ThemeService.generating && ThemeService.generationTemplateId === ""
                    }

                    RowLayout {
                        id: templateActions

                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter

                        IconButton {
                            iconName: "refresh"
                            tooltipText: I18n.tr("Refresh templates")
                            onClicked: TemplateService.refresh()
                        }

                        ActionButton {
                            text: I18n.tr("Add")
                            iconName: "add"
                            enabled: !TemplateService.busy && PersonalizationConfig.ready
                            onClicked: templateAddWindow.showWindow()
                        }
                    }
                }

                Repeater {
                    model: TemplateService.templates

                    SettingsRow {
                        id: templateRow

                        required property var modelData

                        Layout.fillWidth: true
                        iconName: modelData.valid ? modelData.icon : "error"
                        title: modelData.title
                        supportingText: !modelData.valid ? modelData.error : modelData.origin === "user" ? I18n.tr("User templates") :
                                                                                                           ""

                        trailing: Item {
                            implicitWidth: templateRowActions.implicitWidth
                            implicitHeight: templateRowActions.implicitHeight

                            InlineBusyIndicator {
                                anchors.right: templateRowActions.left
                                anchors.rightMargin: NexusStyle.padding.extraSmall
                                anchors.verticalCenter: parent.verticalCenter
                                width: implicitWidth
                                height: implicitHeight
                                busy: templateRow.modelData.valid && ThemeService.generating
                                      && ThemeService.generationTemplateId === templateRow.modelData.id
                            }

                            RowLayout {
                                id: templateRowActions

                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter

                                Item {
                                    visible: templateRow.modelData.hasPostHook
                                    implicitWidth: NexusStyle.icon.large
                                    implicitHeight: NexusStyle.icon.large
                                    Accessible.role: Accessible.StaticText
                                    Accessible.name: I18n.tr("Run after each generation: %1").arg(
                                                         templateRow.modelData.postHook)

                                    MaterialSymbol {
                                        anchors.centerIn: parent
                                        text: "terminal"
                                        iconSize: NexusStyle.icon.medium
                                        color: Appearance.m3colors.m3onSurfaceVariant
                                    }
                                    HoverHandler {
                                        id: hookHover
                                    }
                                    StyledToolTip {
                                        extraVisibleCondition: hookHover.hovered
                                        text: I18n.tr("Run after each generation:\n%1").arg(
                                                  templateRow.modelData.postHook)
                                    }
                                }

                                IconButton {
                                    visible: templateRow.modelData.origin === "user"
                                    iconName: "folder_open"
                                    tooltipText: I18n.tr("Open template location") + "\n"
                                                 + templateRow.modelData.inputPath + "\n" + I18n.tr(
                                                     "Output: %1").arg(templateRow.modelData.outputPath)
                                    onClicked: TemplateService.openLocation(templateRow.modelData)
                                }

                                IconButton {
                                    visible: templateRow.modelData.origin === "user"
                                    iconName: "delete"
                                    tooltipText: I18n.tr("Delete template")
                                    enabled: !TemplateService.busy && !ThemeService.generating
                                             && PersonalizationConfig.ready
                                    onClicked: root.requestTemplateDeletion(templateRow.modelData)
                                }

                                StyledSwitch {
                                    enabled: templateRow.modelData.valid && !ThemeService.generating &&
                                             !TemplateService.busy && PersonalizationConfig.ready
                                    checked: templateRow.modelData.valid
                                             && PersonalizationConfig.isMatugenTemplateEnabled(
                                                 templateRow.modelData.id)
                                    Accessible.name: I18n.tr("Enable the %1 Matugen template").arg(
                                                         templateRow.modelData.title)
                                    onToggled: ThemeService.setMatugenTemplateEnabled(templateRow.modelData.id,
                                                                                      checked)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Non-visual children live inside the content column (NexusPageBase
        // takes a single Item; children on the page root are a type error
        // that kills the whole page — 2026-10-25 lesson).
        MatugenTemplateAddWindow {
            id: templateAddWindow

            parentModal: root.parentModal
        }

        MaterialDialog {
            id: templateDialog

            anchors.centerIn: Overlay.overlay
            width: Math.min(480, root.width - 32)
            dialogTitle: root.pendingDeleteTemplate ? I18n.tr("Delete “%1”?").arg(
                                                          root.pendingDeleteTemplate.title) : ""
            messageText: I18n.tr("Delete the template and its registration. Keep generated output files.")
            onClosed: root.pendingDeleteTemplate = null
            actionsComponent: Component {
                RowLayout {
                    Item {
                        Layout.fillWidth: true
                    }

                    ActionButton {
                        text: I18n.tr("Cancel")
                        onClicked: templateDialog.close()
                    }

                    ActionButton {
                        text: I18n.tr("Delete")
                        enabled: !TemplateService.busy && !ThemeService.generating
                                 && PersonalizationConfig.ready
                        onClicked: {
                            if (root.pendingDeleteTemplate)
                                TemplateService.remove(root.pendingDeleteTemplate.id);
                            templateDialog.close();
                        }
                    }
                }
            }
        }
    }
}
