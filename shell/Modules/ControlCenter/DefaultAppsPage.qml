import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.common

StyledFlickable {
    id: root

    clip: true
    contentWidth: width
    contentHeight: contentColumn.y + contentColumn.implicitHeight + Metrics.pageMargin

    readonly property real pageContentWidth: 640

    component DefaultAppSettingRow: Item {
        id: settingRow

        required property string roleId
        required property string title
        required property string iconName

        readonly property var roleState: DefaultApplicationsService.stateFor(settingRow.roleId)
        readonly property var selectedOption: {
            const options = settingRow.roleState.candidates || [];
            return options.find(option => option.value === settingRow.roleState.currentId) || null;
        }

        Layout.fillWidth: true
        Layout.preferredHeight: Metrics.controlHeightL

        RowLayout {
            id: rowColumn

            anchors.fill: parent
            spacing: Metrics.spacingS

            MaterialSymbol {
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: Metrics.iconM
                Layout.preferredHeight: Metrics.iconM
                text: settingRow.iconName
                iconSize: Metrics.iconM
                color: Appearance.colors.colOnSurfaceVariant

                // Keep the row icon as a glyph; only group headers use a
                // tonal icon container.
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: settingRow.title
                    color: Appearance.colors.colOnSurface
                    font.family: Typography.bodyLarge.family
                    font.pixelSize: Typography.bodyLarge.pixelSize
                    font.weight: Typography.bodyLarge.weight
                    elide: Text.ElideRight
                }
            }

            ThemeIcon {
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: Metrics.iconM
                Layout.preferredHeight: Metrics.iconM
                visible: settingRow.selectedOption !== null && settingRow.selectedOption.icon !== ""
                iconSource: settingRow.selectedOption ? ApplicationService.iconSource(
                                                            settingRow.selectedOption.icon) : ""
                sourceSize.width: Metrics.iconM * 2
                sourceSize.height: Metrics.iconM * 2
                fillMode: Image.PreserveAspectFit
            }

            SearchSelectMenuField {
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: 220
                Layout.preferredHeight: Metrics.controlHeightM
                options: settingRow.roleState.candidates || []
                value: settingRow.roleState.currentId || ""
                placeholder: DefaultApplicationsService.loading ? qsTr("Loading…") : settingRow.roleId
                                                                  === "terminal"
                                                                  && settingRow.roleState.currentId === ""
                                                                  ? qsTr("System default") : qsTr(
                                                                        "No available applications")
                closeOnAccept: true
                enabled: !DefaultApplicationsService.loading && !DefaultApplicationsService.busy && (
                             settingRow.roleState.candidates || []).length > 0
                Accessible.name: settingRow.title
                onAccepted: value => DefaultApplicationsService.setRole(settingRow.roleId, value)
            }
        }

        Text {
            anchors.left: rowColumn.left
            anchors.leftMargin: Metrics.controlHeightM + Metrics.spacingS
            anchors.right: rowColumn.right
            anchors.top: rowColumn.bottom
            visible: !DefaultApplicationsService.loading && (settingRow.roleState.candidates || []).length
                     === 0
            text: qsTr("No available system applications were found")
            color: Appearance.colors.colError
            font.family: Typography.bodySmall.family
            font.pixelSize: Typography.bodySmall.pixelSize
        }
    }

    component DefaultAppsGroup: SettingsSection {
        property string groupTitle: ""
        property string groupIcon: "apps"

        flat: true
        flatIconContainer: true
        title: groupTitle
        iconName: groupIcon

        default property alias rows: body.data

        ColumnLayout {
            id: body

            Layout.fillWidth: true
            spacing: Metrics.spacingXS
        }
    }

    Component.onCompleted: DefaultApplicationsService.refresh()

    ColumnLayout {
        id: contentColumn

        width: Math.min(root.pageContentWidth, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingXL

        DefaultAppsGroup {
            id: extraSearchSection0
            Layout.fillWidth: true
            groupTitle: extraSearchAnchor0.title
            SettingsSearchAnchor {
                id: extraSearchAnchor0
                target: extraSearchSection0
                declaration:
                    '{"id":"general.default-apps.section.internet","route":"general.default-apps","title":"Internet","context":"DefaultAppsPage","icon":"settings","aliases":[]}'
            }
            groupIcon: "public"

            DefaultAppSettingRow {
                roleId: "browser"
                title: qsTr("Web browser")
                iconName: "language"
            }

            DefaultAppSettingRow {
                roleId: "mail"
                title: qsTr("Email")
                iconName: "mail"
            }
        }

        DefaultAppsGroup {
            id: extraSearchSection1
            Layout.fillWidth: true
            groupTitle: extraSearchAnchor1.title
            SettingsSearchAnchor {
                id: extraSearchAnchor1
                target: extraSearchSection1
                declaration:
                    '{"id":"general.default-apps.section.utilities","route":"general.default-apps","title":"Utilities","context":"DefaultAppsPage","icon":"settings","aliases":[]}'
            }
            groupIcon: "terminal"

            DefaultAppSettingRow {
                roleId: "file-manager"
                title: qsTr("File manager")
                iconName: "folder"
            }

            DefaultAppSettingRow {
                roleId: "terminal"
                title: qsTr("Terminal")
                iconName: "terminal"
            }
        }

        DefaultAppsGroup {
            id: extraSearchSection2
            Layout.fillWidth: true
            groupTitle: extraSearchAnchor2.title
            SettingsSearchAnchor {
                id: extraSearchAnchor2
                target: extraSearchSection2
                declaration:
                    '{"id":"general.default-apps.section.documents","route":"general.default-apps","title":"Documents","context":"DefaultAppsPage","icon":"settings","aliases":[]}'
            }
            groupIcon: "description"

            DefaultAppSettingRow {
                roleId: "text-editor"
                title: qsTr("Text editor")
                iconName: "edit_note"
            }

            DefaultAppSettingRow {
                roleId: "pdf-reader"
                title: qsTr("PDF reader")
                iconName: "picture_as_pdf"
            }
        }

        DefaultAppsGroup {
            id: extraSearchSection3
            Layout.fillWidth: true
            groupTitle: extraSearchAnchor3.title
            SettingsSearchAnchor {
                id: extraSearchAnchor3
                target: extraSearchSection3
                declaration:
                    '{"id":"general.default-apps.section.multimedia","route":"general.default-apps","title":"Multimedia","context":"DefaultAppsPage","icon":"settings","aliases":[]}'
            }
            groupIcon: "movie"

            DefaultAppSettingRow {
                roleId: "image-viewer"
                title: qsTr("Image viewer")
                iconName: "image"
            }

            DefaultAppSettingRow {
                roleId: "video-player"
                title: qsTr("Video player")
                iconName: "smart_display"
            }

            DefaultAppSettingRow {
                roleId: "music-player"
                title: qsTr("Music player")
                iconName: "music_note"
            }
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
            message: qsTr("Reading system default applications…")
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Metrics.pageMargin
        }
    }
}
