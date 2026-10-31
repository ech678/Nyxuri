pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import "./DisplayConfiguration.js" as Config
import qs.shared.i18n
import qs.units.settings
import qs.units.settings.controls

// Display configuration page (M3 row-level rebuild): the transaction flow
// (draft/apply/discard), the layout canvas, the advanced + hot-corner
// sections and the custom-scale dialog keep their machinery; the mechanical
// rows — enabled, resolution, scale, logical position, rotation, VRR and the
// navigation rows — are M1 atoms. Truth stays with DisplayConfigService.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("displays.configuration")

    readonly property Item searchLeaf: root.flickable

    readonly property var selected: DisplayConfigService.selected
    readonly property var settings: selected ? selected.settings : ({})
    readonly property bool rowsEnabled: root.selected && root.selected.editable && !DisplayConfigService.busy
    property bool advanced: false
    property var parentModal: null

    function closeChildWindows() {
        scaleDialog.dismiss();
    }

    readonly property string selectedKey: selected ? selected.key : ""
    onSelectedKeyChanged: scaleDialog.dismiss()
    onVisibleChanged: {
        if (!visible)
            scaleDialog.dismiss();
    }

    function revealAdvancedSearch() {
        if (SettingsBackend.searchTarget?.id === "displays.configuration.section.hot-corners"
                || SettingsBackend.searchTarget?.id === "general.displays.configuration.section.hot-corners")
            advanced = true;
    }

    Component.onCompleted: {
        DisplayConfigService.refresh();
        root.revealAdvancedSearch();
    }

    function edit(key, value) {
        if (selected)
            DisplayConfigService.edit(selected.key, key, value);
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Non-visual children live inside the content column (NexusPageBase
        // takes a single Item; page-root children are a type error that
        // kills the whole page — 2026-10-25 lesson). The canvas owns drag
        // gestures; the page scroll yields while a monitor is dragged.
        Binding {
            target: root.flickable
            property: "interactive"
            value: !layoutCanvas.dragging
        }

        Connections {
            target: SettingsBackend
            function onSearchTargetChanged() {
                root.revealAdvancedSearch();
            }
        }

        NiriSetupPrompt {
            Layout.fillWidth: true
            title: I18n.tr("Display configuration")
            description: ""
            integrationState: NiriConfigService.state("outputs")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "outputs"
            blocked: NiriConfigService.busy || DisplayConfigService.busy
            error: NiriConfigService.error
            onSetupRequested: NiriConfigService.setup("outputs")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DisplayConfigService.error !== ""
            tone: "error"
            message: DisplayConfigService.error
        }

        // Layout
        PreferenceHeader {
            text: I18n.tr("Layout")
        }

        ConnectedRect {
            id: layoutCard

            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: layoutCanvas.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: layoutCard
                declaration:
                    '{"id":"displays.configuration.section.layout","route":"displays.configuration","title":"Layout","context":"DisplayConfigurationPage","icon":"monitor","aliases":["general.displays.configuration.section.layout"]}'
            }

            DisplayLayoutCanvas {
                id: layoutCanvas

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                height: implicitHeight

                IconButton {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: NexusStyle.padding.small
                    z: 3
                    variant: "standard"
                    iconName: "id_card"
                    accessibleName: I18n.tr("Identify displays")
                    onClicked: DisplayConfigService.identifyDisplays()
                }
            }
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DisplayConfigService.validation !== ""
            message: DisplayConfigService.validation
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: root.selected && !root.selected.editable
            message: I18n.tr(
                         "This output is read-only. Resolve conflicting or unsupported settings in %1.").arg(
                         root.selected ? root.selected.source : "")
        }

        // Output settings
        PreferenceHeader {
            visible: root.selected !== null
            text: I18n.tr("Output settings")
        }

        PreferenceSelect {
            id: displaySelect

            first: true
            visible: root.selected !== null
            label: I18n.tr("Display")
            model: DisplayConfigService.draft.filter(r => !r.deleted).map(r => ({
                "value": r.key,
                "label": r.connected ? r.label : I18n.tr("%1 (disconnected)").arg(r.label)
            }))
            currentValue: DisplayConfigService.selection
            inputRegionService: PopupInputRegionService
            onSelected: value => DisplayConfigService.selection = value

            SettingsSearchAnchor {
                target: displaySelect
                declaration:
                    '{"id":"displays.configuration.section.output-settings","route":"displays.configuration","title":"Output settings","context":"DisplayConfigurationPage","icon":"monitor","aliases":["general.displays.configuration.section.output-settings"]}'
            }
        }

        // Editable rows share one enabled gate (busy / read-only outputs).
        ColumnLayout {
            visible: root.selected !== null
            enabled: root.rowsEnabled
            Layout.fillWidth: true
            spacing: NexusStyle.padding.extraSmall / 2

            PreferenceToggle {
                id: enabledToggle

                text: I18n.tr("Enabled")
                checked: root.settings.enabled !== false
                enabled: !root.selected || !root.selected.connected || !checked || DisplayConfigService.draft.filter(
                             r => r.connected && r.settings.enabled !== false).length > 1
                onToggled: root.edit("enabled", checked)
            }

            PreferenceSelect {
                visible: root.selected && root.selected.connected
                label: I18n.tr("Resolution and refresh rate")
                model: root.selected && root.selected.live ? root.selected.live.modes.map(m => ({
                    "value": Config.modeString(m),
                    "label": I18n.tr("%1 × %2 · %3 Hz").arg(m.width).arg(m.height).arg((m.refreshMilliHz
                                                                                        / 1000).toFixed(3))
                })) : []
                currentValue: root.settings.mode || ""
                inputRegionService: PopupInputRegionService
                onSelected: value => root.edit("mode", value)
            }

            PreferenceSelect {
                label: I18n.tr("Scale")
                model: {
                    const values = [1, 1.25, 1.5, 1.75, 2, 2.5, 3];
                    const result = values.map(v => ({
                        "value": String(v),
                        "label": Math.round(v * 100) + "%"
                    }));
                    const current = root.settings.scale || 1;
                    if (values.indexOf(current) < 0)
                        result.push({
                                        "value": String(current),
                                        "label": I18n.tr("%1% (Custom)").arg(Math.round(current * 1000000)
                                                                             / 10000)
                                    });
                    result.push({
                                    "value": "custom",
                                    "label": I18n.tr("Custom")
                                });
                    return result;
                }
                currentValue: String(root.settings.scale || 1)
                inputRegionService: PopupInputRegionService
                onSelected: value => {
                    if (value === "custom") {
                        scaleDialog.inputText = String(Math.round((root.settings.scale || 1) * 1000000)
                                                       / 10000);
                        scaleDialog.showWindow();
                    } else {
                        root.edit("scale", Number(value));
                    }
                }
            }

            PreferenceInput {
                id: logicalXInput

                label: I18n.tr("Logical X")
                value: String(root.settings.position ? root.settings.position.x : 0)
                smallField: true
                validate: text => /^-?\d+$/.test(text.trim())
                onEditingFinished: value => {
                    if (logicalXInput.valid)
                        root.edit("position", Object.assign({}, root.settings.position, {
                                                                "x": Number(value)
                                                            }));
                }
            }

            PreferenceInput {
                id: logicalYInput

                label: I18n.tr("Logical Y")
                value: String(root.settings.position ? root.settings.position.y : 0)
                smallField: true
                validate: text => /^-?\d+$/.test(text.trim())
                onEditingFinished: value => {
                    if (logicalYInput.valid)
                        root.edit("position", Object.assign({}, root.settings.position, {
                                                                "y": Number(value)
                                                            }));
                }
            }

            PreferenceSelect {
                label: I18n.tr("Rotation and reflection")
                model: [
                    {
                        "value": "normal",
                        "label": I18n.tr("Normal")
                    },
                    {
                        "value": "90",
                        "label": "90°"
                    },
                    {
                        "value": "180",
                        "label": "180°"
                    },
                    {
                        "value": "270",
                        "label": "270°"
                    },
                    {
                        "value": "flipped",
                        "label": I18n.tr("Flipped")
                    },
                    {
                        "value": "flipped-90",
                        "label": I18n.tr("Flipped · 90°")
                    },
                    {
                        "value": "flipped-180",
                        "label": I18n.tr("Flipped · 180°")
                    },
                    {
                        "value": "flipped-270",
                        "label": I18n.tr("Flipped · 270°")
                    }
                ]
                currentValue: root.settings.transform || "normal"
                inputRegionService: PopupInputRegionService
                onSelected: value => root.edit("transform", value)
            }

            PreferenceSelect {
                label: I18n.tr("Variable refresh rate")
                enabled: root.selected && (!root.selected.connected || root.selected.live.vrrSupported)
                model: [
                    {
                        "value": "off",
                        "label": I18n.tr("Off")
                    },
                    {
                        "value": "on",
                        "label": I18n.tr("On")
                    },
                    {
                        "value": "on-demand",
                        "label": I18n.tr("On-Demand")
                    }
                ]
                currentValue: root.settings.vrr || "off"
                inputRegionService: PopupInputRegionService
                onSelected: value => root.edit("vrr", value)
            }

            PreferenceAction {
                last: true
                icon: "tune"
                text: I18n.tr("Advanced settings")
                trailingIcon: root.advanced ? "expand_less" : "expand_more"
                onClicked: root.advanced = !root.advanced
            }

            DisplayAdvancedSettings {
                Layout.fillWidth: true
                visible: root.advanced
                row: root.selected
            }

            DisplayHotCornerSettings {
                id: hotCornerSettings

                Layout.fillWidth: true
                visible: root.advanced

                SettingsSearchAnchor {
                    target: hotCornerSettings
                    declaration:
                        '{"id":"displays.configuration.section.hot-corners","route":"displays.configuration","title":"Hot corners","context":"HotCornersPage","icon":"open_in_full","aliases":["corner actions", "screen corners", "general.displays.configuration.section.hot-corners"]}'
                }
            }
        }

        PreferenceAction {
            first: true
            last: true
            visible: root.selected && !root.selected.connected
            icon: "delete"
            text: I18n.tr("Delete saved display")
            trailingIcon: ""
            onClicked: DisplayConfigService.forget(root.selected.key)
        }

        // Transaction bar — discard/apply keeps its draft semantics.
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: NexusStyle.padding.medium
            spacing: NexusStyle.padding.small

            Item {
                Layout.fillWidth: true
                Layout.minimumWidth: NexusStyle.icon.medium + NexusStyle.padding.extraSmall
            }

            ActionButton {
                text: I18n.tr("Discard")
                enabled: DisplayConfigService.dirty && !DisplayConfigService.busy
                onClicked: DisplayConfigService.reload()

                InlineBusyIndicator {
                    anchors.right: parent.left
                    anchors.rightMargin: NexusStyle.padding.extraSmall
                    anchors.verticalCenter: parent.verticalCenter
                    busy: DisplayConfigService.busy
                }
            }

            ActionButton {
                text: I18n.tr("Apply")
                filled: true
                enabled: DisplayConfigService.dirty && !DisplayConfigService.busy &&
                         !DisplayConfigService.validation && NiriConfigService.ready("outputs")
                onClicked: DisplayConfigService.apply()
            }
        }

        // Custom-scale dialog (kept custom): FloatingWindow child of the
        // content column — a page-level child on the root is a type error
        // under NexusPageBase's single-Item default property.
        FloatingWindow {
            id: scaleDialog

            property string inputText: ""
            readonly property bool acceptable: percentInput.fieldItem.acceptableInput
            parentWindow: root.parentModal
            title: "nyxuri-control-center-display-scale"
            visible: false
            color: "transparent"
            implicitWidth: 380
            implicitHeight: dialogContent.implicitHeight + NexusStyle.padding.extraLargeIncreased * 2
            onClosed: dismiss()
            function showWindow() {
                visible = true;
                Qt.callLater(() => {
                    percentInput.fieldItem.forceActiveFocus();
                    percentInput.fieldItem.selectAll();
                });
            }
            function dismiss() {
                visible = false;
            }
            function applyScale() {
                if (!acceptable || DisplayConfigService.busy)
                    return;
                root.edit("scale", Number(inputText) / 100);
                dismiss();
            }

            Rectangle {
                id: scaleBackground

                anchors.fill: parent
                radius: NexusStyle.rounding.extraLarge
                color: BlurService.backgroundColor(Appearance.m3colors.m3surfaceContainerHigh)
                border.width: 1
                border.color: Appearance.colors.colOutlineVariant
            }

            CompositorBlurRegion {
                targetWindow: scaleDialog
                backgroundItem: scaleBackground
                radius: scaleBackground.radius
            }

            FocusScope {
                anchors.fill: parent
                focus: scaleDialog.visible
                Keys.onEscapePressed: scaleDialog.dismiss()

                ColumnLayout {
                    id: dialogContent

                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: NexusStyle.padding.extraLargeIncreased
                    }
                    spacing: NexusStyle.padding.medium

                    StyledText {
                        Layout.fillWidth: true
                        text: I18n.tr("Custom scale")
                        color: Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.headlineMedium
                        wrapMode: Text.Wrap
                    }

                    OutlinedTextField {
                        id: percentInput

                        Layout.fillWidth: true
                        labelText: I18n.tr("Scale (%)")
                        text: scaleDialog.inputText
                        validator: DoubleValidator {
                            bottom: 10
                            top: 1000
                            decimals: 4
                            notation: DoubleValidator.StandardNotation
                            locale: "C"
                        }
                        onTextChanged: scaleDialog.inputText = text
                        onAccepted: scaleDialog.applyScale()
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: NexusStyle.padding.small

                        Item {
                            Layout.fillWidth: true
                        }

                        ActionButton {
                            text: I18n.tr("Cancel")
                            onClicked: scaleDialog.dismiss()
                        }

                        ActionButton {
                            text: I18n.tr("Apply")
                            filled: true
                            enabled: scaleDialog.acceptable && !DisplayConfigService.busy
                            onClicked: scaleDialog.applyScale()
                        }
                    }
                }
            }
        }
    }
}
