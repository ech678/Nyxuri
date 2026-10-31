pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.shared.controls
import qs.app.services
import qs.shared.i18n
import qs.units.settings
import qs.units.settings.controls

// Default applications page (T3 M4): NexusPageBase scaffold + M1 select
// atoms. The row shape mirrors Caelestia's DefaultRow (leading role icon +
// label + trailing selection pill); the pill replaces the upstream blob
// popup, which stays unported by the pure-QML red line.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("default-apps")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    Component.onCompleted: DefaultApplicationsService.refresh()

    component DefaultAppRow: PreferenceSelect {
        id: appRow

        required property string roleId
        required property string roleTitle
        required property string roleIcon

        readonly property var roleState: DefaultApplicationsService.stateFor(appRow.roleId)
        readonly property var candidates: appRow.roleState.candidates || []
        readonly property bool unavailable: !DefaultApplicationsService.loading && appRow.candidates.length
                                            === 0

        icon: appRow.roleIcon
        label: appRow.roleTitle
        subtext: appRow.unavailable ? I18n.tr("No available system applications were found") : ""
        model: appRow.candidates
        currentValue: appRow.roleState.currentId || ""
        fallbackText: DefaultApplicationsService.loading ? I18n.tr("Loading…") : appRow.roleId === "terminal"
                                                           && appRow.currentValue === "" ? I18n.tr(
                                                                                               "System default") :
                                                                                           I18n.tr("No available applications")
        enabled: !DefaultApplicationsService.loading && !DefaultApplicationsService.busy
                 && appRow.candidates.length > 0
        inputRegionService: PopupInputRegionService
        onSelected: value => DefaultApplicationsService.setRole(appRow.roleId, value)
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Internet
        PreferenceHeader {
            first: true
            text: I18n.tr("Internet")
        }

        DefaultAppRow {
            id: browserRow

            first: true
            roleId: "browser"
            roleTitle: I18n.tr("Web browser")
            roleIcon: "language"

            SettingsSearchAnchor {
                id: extraSearchAnchor0
                target: browserRow
                declaration:
                    '{"id":"default-apps.section.internet","route":"default-apps","title":"Internet","context":"DefaultAppsPage","icon":"settings","aliases":["general.default-apps.section.internet"]}'
            }
        }

        DefaultAppRow {
            last: true
            roleId: "mail"
            roleTitle: I18n.tr("Email")
            roleIcon: "mail"
        }

        // Utilities
        PreferenceHeader {
            text: I18n.tr("Utilities")
        }

        DefaultAppRow {
            id: fileManagerRow

            first: true
            roleId: "file-manager"
            roleTitle: I18n.tr("File manager")
            roleIcon: "folder"

            SettingsSearchAnchor {
                id: extraSearchAnchor1
                target: fileManagerRow
                declaration:
                    '{"id":"default-apps.section.utilities","route":"default-apps","title":"Utilities","context":"DefaultAppsPage","icon":"settings","aliases":["general.default-apps.section.utilities"]}'
            }
        }

        DefaultAppRow {
            last: true
            roleId: "terminal"
            roleTitle: I18n.tr("Terminal")
            roleIcon: "terminal"
        }

        // Documents
        PreferenceHeader {
            text: I18n.tr("Documents")
        }

        DefaultAppRow {
            id: textEditorRow

            first: true
            roleId: "text-editor"
            roleTitle: I18n.tr("Text editor")
            roleIcon: "edit_note"

            SettingsSearchAnchor {
                id: extraSearchAnchor2
                target: textEditorRow
                declaration:
                    '{"id":"default-apps.section.documents","route":"default-apps","title":"Documents","context":"DefaultAppsPage","icon":"settings","aliases":["general.default-apps.section.documents"]}'
            }
        }

        DefaultAppRow {
            last: true
            roleId: "pdf-reader"
            roleTitle: I18n.tr("PDF reader")
            roleIcon: "picture_as_pdf"
        }

        // Multimedia
        PreferenceHeader {
            text: I18n.tr("Multimedia")
        }

        DefaultAppRow {
            id: imageViewerRow

            first: true
            roleId: "image-viewer"
            roleTitle: I18n.tr("Image viewer")
            roleIcon: "image"

            SettingsSearchAnchor {
                id: extraSearchAnchor3
                target: imageViewerRow
                declaration:
                    '{"id":"default-apps.section.multimedia","route":"default-apps","title":"Multimedia","context":"DefaultAppsPage","icon":"settings","aliases":["general.default-apps.section.multimedia"]}'
            }
        }

        DefaultAppRow {
            roleId: "video-player"
            roleTitle: I18n.tr("Video player")
            roleIcon: "smart_display"
        }

        DefaultAppRow {
            last: true
            roleId: "music-player"
            roleTitle: I18n.tr("Music player")
            roleIcon: "music_note"
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DefaultApplicationsService.lastError !== ""
            tone: "error"
            message: DefaultApplicationsService.lastError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DefaultApplicationsService.lastMessage !== ""
            tone: "info"
            message: DefaultApplicationsService.lastMessage
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DefaultApplicationsService.loading
            iconName: "progress_activity"
            message: I18n.tr("Reading system default applications…")
        }
    }
}
