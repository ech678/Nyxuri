pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

StyledFlickable {
    id: root

    property var parentModal: null
    readonly property real pageContentWidth: 600
    property var pendingDeleteTemplate: null

    function requestTemplateDeletion(template) {
        root.pendingDeleteTemplate = template;
        templateDialog.open();
    }

    function closeChildWindows() {
        templateAddWindow.dismiss();
        templateDialog.close();
    }

    clip: true
    contentWidth: width
    contentHeight: contentColumn.y + contentColumn.implicitHeight + 24

    ColumnLayout {
        id: contentColumn

        width: Math.min(root.pageContentWidth, Math.max(0, root.width - 48))
        x: Math.max(24, (root.width - width) / 2)
        y: 28
        spacing: Appearance.spacing.medium

        SettingsSection {
            id: searchSection2
            Layout.fillWidth: true
            title: searchAnchor2.title
            SettingsSearchAnchor {
                id: searchAnchor2
                target: searchSection2
                declaration:
                    '{"id":"advanced.section.matugen-template-generation","route":"advanced","title":"Matugen template generation","context":"AdvancedPage","icon":"tune","aliases":[]}'
            }

            Item {
                Layout.fillWidth: true
                implicitHeight: templateActions.implicitHeight

                InlineBusyIndicator {
                    anchors.right: templateActions.left
                    anchors.rightMargin: Metrics.spacingXS
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
                        onClicked: MatugenTemplateService.refresh()
                    }
                    ActionButton {
                        text: I18n.tr("Add")
                        iconName: "add"
                        enabled: !MatugenTemplateService.busy && PersonalizationConfig.ready
                        onClicked: templateAddWindow.showWindow()
                    }
                }
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: MatugenTemplateService.error !== ""
                tone: "error"
                message: MatugenTemplateService.error
            }
            InlineStatusBanner {
                Layout.fillWidth: true
                visible: !templateAddWindow.visible && MatugenTemplateService.operationError !== ""
                tone: "error"
                message: MatugenTemplateService.operationError
            }
            InlineStatusBanner {
                Layout.fillWidth: true
                visible: ThemeService.generationError !== "" || ThemeService.externalGenerationError !== ""
                tone: "error"
                message: ThemeService.generationError !== "" ? I18n.tr("Failed to generate Matugen colors") :
                                                               I18n.tr("Some Matugen templates failed to generate")
                StyledToolTip {
                    extraVisibleCondition: errorHover.hovered
                    text: ThemeService.generationError || ThemeService.externalGenerationError
                }
                HoverHandler {
                    id: errorHover
                }
            }

            Repeater {
                model: MatugenTemplateService.templates

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
                            anchors.rightMargin: Metrics.spacingXS
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
                                implicitWidth: Metrics.controlHeightM
                                implicitHeight: Metrics.controlHeightM
                                Accessible.role: Accessible.StaticText
                                Accessible.name: I18n.tr("Run after each generation: %1").arg(
                                                     templateRow.modelData.postHook)

                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    text: "terminal"
                                    iconSize: Metrics.iconM
                                    color: Appearance.colors.colOnSurfaceVariant
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
                                onClicked: MatugenTemplateService.openLocation(templateRow.modelData)
                            }
                            IconButton {
                                visible: templateRow.modelData.origin === "user"
                                iconName: "delete"
                                tooltipText: I18n.tr("Delete template")
                                enabled: !MatugenTemplateService.busy && !ThemeService.generating
                                         && PersonalizationConfig.ready
                                onClicked: root.requestTemplateDeletion(templateRow.modelData)
                            }
                            StyledSwitch {
                                enabled: templateRow.modelData.valid && !ThemeService.generating &&
                                         !MatugenTemplateService.busy && PersonalizationConfig.ready
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

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 24
        }
    }

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
                    enabled: !MatugenTemplateService.busy && !ThemeService.generating
                             && PersonalizationConfig.ready
                    onClicked: {
                        if (root.pendingDeleteTemplate)
                            MatugenTemplateService.remove(root.pendingDeleteTemplate.id);
                        templateDialog.close();
                    }
                }
            }
        }
    }
}
