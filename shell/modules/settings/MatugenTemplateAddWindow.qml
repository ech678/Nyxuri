pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.modules.filepicker
import qs.app
import qs.shared.i18n

FloatingWindow {
    id: root

    property var parentModal: null
    property string sourcePath: ""
    property bool advanced: false

    function showWindow() {
        root.sourcePath = "";
        idField.text = "";
        outputField.text = "";
        hookField.text = "";
        root.advanced = false;
        TemplateService.operationError = "";
        root.visible = true;
    }
    function dismiss() {
        picker.dismiss();
        root.visible = false;
    }

    visible: false
    parentWindow: root.parentModal
    // Stable compositor rule identity; visible headings remain localized.
    title: "clavis-control-center-template-add"
    implicitWidth: 580
    implicitHeight: 640
    minimumSize: Qt.size(460, 480)
    color: "transparent"
    onClosed: root.dismiss()

    Connections {
        target: TemplateService
        function onAdded(templateId) {
            if (root.visible)
                root.dismiss();
        }
    }

    Rectangle {
        id: background
        anchors.fill: parent
        radius: Appearance.rounding.extraLarge
        color: BlurService.backgroundColor(Appearance.m3colors.m3surfaceContainerHigh)
    }
    CompositorBlurRegion {
        targetWindow: root
        backgroundItem: background
        radius: background.radius
    }
    FocusScope {
        anchors.fill: parent
        focus: root.visible
        Keys.onEscapePressed: root.dismiss()

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Metrics.spacingXL
            spacing: Metrics.spacingM

            WizardHeader {
                Layout.fillWidth: true
                title: I18n.tr("Add Matugen template")
                onCloseRequested: root.dismiss()
            }
            StyledFlickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentHeight: form.implicitHeight
                contentWidth: width

                ColumnLayout {
                    id: form
                    width: parent.width
                    spacing: Metrics.spacingM
                    enabled: !TemplateService.busy

                    SettingsActionRow {
                        Layout.fillWidth: true
                        text: I18n.tr("Template file")
                        description: root.sourcePath
                        iconName: "description"
                        trailingIconName: "folder_open"
                        onClicked: picker.openAt(Paths.homeDir)
                    }
                    MaterialFilledTextField {
                        id: idField
                        Layout.fillWidth: true
                        labelText: I18n.tr("Template ID")
                        error: text !== "" && !/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$/.test(text)
                    }
                    MaterialFilledTextField {
                        id: outputField
                        Layout.fillWidth: true
                        labelText: I18n.tr("Output path")
                    }
                    SettingsActionRow {
                        Layout.fillWidth: true
                        text: I18n.tr("Advanced options")
                        trailingIconName: root.advanced ? "expand_less" : "expand_more"
                        onClicked: root.advanced = !root.advanced
                    }
                    MaterialFilledTextField {
                        id: hookField
                        Layout.fillWidth: true
                        visible: root.advanced
                        labelText: I18n.tr("Run command after generation")
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: root.advanced
                        text: I18n.tr(
                                  "This command runs every time Matugen regenerates the theme. Only enable trusted templates.")
                        color: Appearance.colors.colOnSurfaceVariant
                        font.family: Fonts.ui
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                    InlineStatusBanner {
                        Layout.fillWidth: true
                        visible: TemplateService.operationError !== ""
                        tone: "error"
                        message: TemplateService.operationError
                    }
                }
            }
            Item {
                Layout.fillWidth: true
                implicitHeight: addActions.implicitHeight

                InlineBusyIndicator {
                    anchors.right: addActions.left
                    anchors.rightMargin: Metrics.spacingXS
                    anchors.verticalCenter: parent.verticalCenter
                    width: implicitWidth
                    height: implicitHeight
                    busy: TemplateService.adding
                }

                RowLayout {
                    id: addActions

                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter

                    ActionButton {
                        text: I18n.tr("Cancel")
                        enabled: !TemplateService.adding
                        onClicked: root.dismiss()
                    }
                    ActionButton {
                        text: I18n.tr("Add")
                        filled: true
                        enabled: !TemplateService.busy && root.sourcePath !== "" && idField.text !== "" &&
                                 !idField.error && outputField.text.trim() !== ""
                        onClicked: TemplateService.add(idField.text, root.sourcePath, outputField.text,
                                                       hookField.text)
                    }
                }
            }
        }
    }
    FilePickerWindow {
        id: picker
        parentModal: root
        requiresParentWindow: true
        selectionMode: FilePickerWindow.Files
        nameFilters: ["*"]
        dialogTitle: I18n.tr("Choose template file")
        description: ""
        windowIconName: "description"
        emptyStateText: I18n.tr("No files available")
        selectionPrompt: I18n.tr("Choose template file")
        formatSummary: ""
        onAccepted: (path, isDirectory) => {
            if (!isDirectory)
                root.sourcePath = path;
        }
    }
}
