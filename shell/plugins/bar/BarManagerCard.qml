import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// D4e multi-bar manager card (dux BarHubHeader pattern, Nexus ConnectedRect
// skin): lists every [[bar.configs]] entry with selection, enable switch,
// inline rename, add bar and guarded delete (default + last bar protected).
ColumnLayout {
    id: root

    property string editingBarId: ""
    property string renameDraft: ""

    readonly property var configs: Array.isArray(PersonalizationConfig.barConfigs) ? PersonalizationConfig.barConfigs : []
    readonly property var selectedConfig: PersonalizationConfig.activeBarConfig()
    readonly property bool allBarsDisabled: root.configs.length > 0 && !root.configs.some(cfg => cfg.enabled !== false)

    function edgeLabel(position): string {
        switch (position) {
        case "bottom":
            return I18n.tr("Bottom");
        case "left":
            return I18n.tr("Left");
        case "right":
            return I18n.tr("Right");
        default:
            return I18n.tr("Top");
        }
    }

    function barSummary(cfg): string {
        const parts = [root.edgeLabel(cfg?.axes?.position)];
        const screens = cfg?.axes?.screenList ?? [];
        if (screens.length === 0)
            parts.push(I18n.tr("All screens"));
        else
            parts.push(screens.length === 1 ? I18n.tr("1 screen") : I18n.tr("%1 screens").arg(screens.length));
        const hasIsland = ["left", "middle", "right"].some(zone => (cfg?.lanes?.[zone] ?? []).some(entry => entry.widgetId === "island"));
        if (hasIsland)
            parts.push(I18n.tr("Island"));
        return parts.join(" • ");
    }

    function beginRename(cfg): void {
        root.renameDraft = String(cfg?.name ?? "Bar");
        root.editingBarId = String(cfg?.id ?? "");
    }

    function commitRename(): void {
        const id = root.editingBarId;
        const name = root.renameDraft.trim();
        root.editingBarId = "";
        if (id && name.length > 0)
            PersonalizationConfig.renameBarConfig(id, name);
    }

    function createBar(): void {
        if (root.configs.length >= 4)
            return;
        const newId = PersonalizationConfig.addBarConfig();
        if (newId)
            PersonalizationConfig.selectBar(newId);
    }

    Layout.fillWidth: true
    spacing: NexusStyle.padding.extraSmall / 2

    PreferenceHeader {
        first: true
        text: I18n.tr("Bars")

        RippleButton {
            visible: root.configs.length < 4
            buttonText: I18n.tr("Add")
            buttonRadius: NexusStyle.rounding.full
            horizontalPadding: NexusStyle.padding.medium
            verticalPadding: NexusStyle.padding.extraSmall
            colBackground: Appearance.m3colors.m3secondaryContainer
            colBackgroundHover: Appearance.m3colors.m3secondaryContainer
            onClicked: root.createBar()

            contentItem: RowLayout {
                spacing: NexusStyle.padding.extraSmall

                MaterialSymbol {
                    text: "add"
                    iconSize: NexusStyle.icon.small
                    color: Appearance.m3colors.m3onSecondaryContainer
                }

                StyledText {
                    text: I18n.tr("Add")
                    color: Appearance.m3colors.m3onSecondaryContainer
                    font.pixelSize: NexusStyle.font.labelLarge
                    font.weight: NexusStyle.font.labelLargeWeight
                }
            }
        }
    }

    PreferenceGroup {
        Repeater {
            model: root.configs

            ConnectedRect {
                id: barRow

                required property var modelData
                required property int index

                readonly property bool isSelected: root.selectedConfig && root.selectedConfig.id === modelData.id
                readonly property bool isRenaming: root.editingBarId === modelData.id
                readonly property bool canDelete: modelData.id !== "default" && root.configs.length > 1

                Layout.fillWidth: true
                implicitHeight: rowContent.implicitHeight + NexusStyle.padding.medium * 2
                color: barRow.isSelected ? Appearance.m3colors.m3surfaceContainerHigh : Appearance.m3colors.m3surfaceContainer

                StateLayer {
                    anchors.fill: parent
                    layerRadius: (barRow.first || barRow.last) ? NexusStyle.rounding.extraLarge : NexusStyle.rounding.extraSmall
                    color: Appearance.m3colors.m3primary
                    hovered: rowMouse.containsMouse
                    pressed: rowMouse.pressed
                    selected: barRow.isSelected
                }

                MouseArea {
                    id: rowMouse

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.editingBarId && root.editingBarId !== barRow.modelData.id)
                            root.editingBarId = "";
                        PersonalizationConfig.selectBar(barRow.modelData.id);
                    }
                }

                ColumnLayout {
                    id: rowContent

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: NexusStyle.padding.largeIncreased
                    anchors.rightMargin: NexusStyle.padding.largeIncreased
                    spacing: NexusStyle.padding.small

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: NexusStyle.padding.small

                        MaterialSymbol {
                            text: barRow.isSelected ? "radio_button_checked" : "radio_button_unchecked"
                            iconSize: NexusStyle.icon.medium
                            fill: barRow.isSelected ? 1 : 0
                            color: barRow.isSelected ? Appearance.m3colors.m3primary : Appearance.m3colors.m3onSurfaceVariant
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            StyledText {
                                Layout.fillWidth: true
                                text: barRow.modelData.name || "Bar"
                                color: Appearance.m3colors.m3onSurface
                                font.pixelSize: NexusStyle.font.bodyMedium
                                font.weight: barRow.isSelected ? NexusStyle.font.titleWeight : Font.Normal
                                elide: Text.ElideRight
                            }

                            StyledText {
                                Layout.fillWidth: true
                                text: root.barSummary(barRow.modelData)
                                color: Appearance.m3colors.m3outline
                                font.pixelSize: NexusStyle.font.labelSmall
                                elide: Text.ElideRight
                            }
                        }

                        IconButton {
                            Layout.alignment: Qt.AlignVCenter
                            width: NexusStyle.icon.small + NexusStyle.padding.small
                            height: NexusStyle.icon.small + NexusStyle.padding.small
                            controlSize: NexusStyle.icon.small + NexusStyle.padding.small
                            iconSize: NexusStyle.icon.small
                            iconName: barRow.isRenaming ? "check" : "edit"
                            accessibleName: barRow.isRenaming ? I18n.tr("Save") : I18n.tr("Rename")
                            tooltipText: accessibleName
                            onClicked: {
                                if (barRow.isRenaming)
                                    root.commitRename();
                                else
                                    root.beginRename(barRow.modelData);
                            }
                        }

                        IconButton {
                            visible: barRow.isRenaming
                            Layout.alignment: Qt.AlignVCenter
                            width: NexusStyle.icon.small + NexusStyle.padding.small
                            height: NexusStyle.icon.small + NexusStyle.padding.small
                            controlSize: NexusStyle.icon.small + NexusStyle.padding.small
                            iconSize: NexusStyle.icon.small
                            iconName: "close"
                            accessibleName: I18n.tr("Cancel")
                            tooltipText: accessibleName
                            onClicked: root.editingBarId = ""
                        }

                        IconButton {
                            visible: barRow.canDelete && !barRow.isRenaming
                            Layout.alignment: Qt.AlignVCenter
                            width: NexusStyle.icon.small + NexusStyle.padding.small
                            height: NexusStyle.icon.small + NexusStyle.padding.small
                            controlSize: NexusStyle.icon.small + NexusStyle.padding.small
                            iconSize: NexusStyle.icon.small
                            iconName: "delete"
                            iconColor: Appearance.m3colors.m3error
                            accessibleName: I18n.tr("Delete bar")
                            tooltipText: accessibleName
                            onClicked: PersonalizationConfig.deleteBarConfig(barRow.modelData.id)
                        }

                        StyledSwitch {
                            id: barEnableSwitch

                            checked: barRow.modelData.enabled !== false
                            onToggled: {
                                PersonalizationConfig.selectBar(barRow.modelData.id);
                                PersonalizationConfig.setBarEnabled(barRow.modelData.id, barEnableSwitch.checked);
                            }
                        }
                    }

                    TextField {
                        id: renameField

                        visible: barRow.isRenaming
                        Layout.fillWidth: true
                        implicitHeight: NexusStyle.font.bodyMedium + NexusStyle.padding.small * 2 + NexusStyle.padding.extraSmall
                        text: root.renameDraft
                        color: Appearance.m3colors.m3onSurface
                        font.family: Fonts.ui
                        font.pixelSize: NexusStyle.font.bodyMedium
                        placeholderText: I18n.tr("Bar name")
                        selectByMouse: true
                        onTextEdited: root.renameDraft = text
                        onAccepted: root.commitRename()
                        Keys.onEscapePressed: root.editingBarId = ""
                        onVisibleChanged: {
                            if (visible) {
                                text = root.renameDraft;
                                forceActiveFocus();
                                selectAll();
                            }
                        }

                        background: Rectangle {
                            radius: NexusStyle.rounding.small
                            color: Appearance.m3colors.m3surfaceContainerLowest
                            border.width: renameField.activeFocus ? 2 : 1
                            border.color: renameField.activeFocus ? Appearance.m3colors.m3primary : Appearance.m3colors.m3outlineVariant
                        }
                    }
                }
            }
        }
    }

    InlineStatusBanner {
        Layout.fillWidth: true
        Layout.topMargin: NexusStyle.padding.extraSmall
        visible: root.allBarsDisabled
        tone: "warning"
        iconName: "visibility_off"
        message: I18n.tr("All bars are disabled. Use keybinds or the toggle above to show a bar again.")
    }
}
