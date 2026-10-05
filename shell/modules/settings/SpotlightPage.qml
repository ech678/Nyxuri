import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

StyledFlickable {
    id: root

    function closeChildWindows() {
        appStylePicker.closeMenu();
        appOrderPicker.closeMenu();
        clipboardStylePicker.closeMenu();
        enginePicker.closeMenu();
    }

    Component.onCompleted: ClipboardService.loadHistoryConfig()

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin

        SettingsSection {
            id: searchSection0
            Layout.fillWidth: true
            flat: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                target: searchSection0
                declaration:
                    '{"id":"spotlight.section.applications","route":"spotlight","title":"Applications","context":"SpotlightPage","icon":"search","aliases":["general.spotlight.section.applications"]}'
            }
            iconName: "apps"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Layout")
                iconName: "grid_view"

                trailing: SearchSelectMenuField {
                    id: appStylePicker

                    Layout.preferredWidth: 220
                    options: [
                        {
                            value: "list",
                            label: I18n.tr("List")
                        },
                        {
                            value: "grid",
                            label: I18n.tr("Grid")
                        }
                    ]
                    value: UiPreferences.spotlightAppStyle
                    closeOnAccept: true
                    Accessible.name: I18n.tr("Application layout")
                    onAccepted: value => UiPreferences.setSpotlightAppStyle(value)
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Application order")
                iconName: "sort"
                trailing: SearchSelectMenuField {
                    id: appOrderPicker
                    Layout.preferredWidth: 220
                    options: [
                        {
                            value: "smart",
                            label: I18n.tr("Smart")
                        },
                        {
                            value: "most-used",
                            label: I18n.tr("Most used")
                        },
                        {
                            value: "recently-used",
                            label: I18n.tr("Recently used")
                        },
                        {
                            value: "name",
                            label: I18n.tr("Name")
                        }
                    ]
                    value: UiPreferences.spotlightAppOrder
                    closeOnAccept: true
                    Accessible.name: I18n.tr("Application order")
                    onAccepted: value => UiPreferences.setSpotlightAppOrder(value)
                }
            }
        }

        SettingsSection {
            id: searchSection1
            Layout.fillWidth: true
            flat: true
            title: searchAnchor1.title
            SettingsSearchAnchor {
                id: searchAnchor1
                target: searchSection1
                declaration:
                    '{"id":"spotlight.section.web-search","route":"spotlight","title":"Web search","context":"SpotlightPage","icon":"search","aliases":["general.spotlight.section.web-search"]}'
            }
            iconName: "language"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Search engine")
                iconName: "search"

                trailing: SearchSelectMenuField {
                    id: enginePicker

                    Layout.preferredWidth: 220
                    options: UiPreferences.searchEngines
                    value: UiPreferences.spotlightSearchEngine
                    textRole: "label"
                    valueRole: "id"
                    closeOnAccept: true
                    leadingWidth: Metrics.iconM
                    Accessible.name: I18n.tr("Search engine")
                    onAccepted: value => {
                        return UiPreferences.setSpotlightSearchEngine(value);
                    }

                    leadingDelegate: Component {
                        MaterialSymbol {
                            text: "search"
                            iconSize: Metrics.iconM
                            color: Appearance.colors.colOnSurface
                        }
                    }
                }
            }
        }

        SettingsSection {
            id: searchSection2
            Layout.fillWidth: true
            flat: true
            title: searchAnchor2.title
            SettingsSearchAnchor {
                id: searchAnchor2
                target: searchSection2
                declaration:
                    '{"id":"spotlight.section.clipboard","route":"spotlight","title":"Clipboard","context":"SpotlightPage","icon":"search","aliases":["general.spotlight.section.clipboard"]}'
            }
            iconName: "content_paste"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Layout")
                iconName: "view_sidebar"
                trailing: SearchSelectMenuField {
                    id: clipboardStylePicker
                    Layout.preferredWidth: 220
                    options: [
                        {
                            value: "default",
                            label: I18n.tr("Default")
                        },
                        {
                            value: "details",
                            label: I18n.tr("Details")
                        }
                    ]
                    value: UiPreferences.spotlightClipboardStyle
                    closeOnAccept: true
                    Accessible.name: I18n.tr("Clipboard layout")
                    onAccepted: value => UiPreferences.setSpotlightClipboardStyle(value)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("History limit")
                supportingText: I18n.tr("Oldest items are removed when new content is saved.")
                iconName: "history"

                trailing: MaterialStepper {
                    from: 50
                    to: 750
                    stepSize: 50
                    value: ClipboardService.historyLimit
                    enabled: ClipboardService.historyConfigLoaded
                    busy: ClipboardService.historyConfigBusy
                    Accessible.name: I18n.tr("History limit")
                    onValueModified: value => ClipboardService.setHistoryLimit(value)
                }
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: ClipboardService.historyConfigError !== null
                tone: "error"
                message: ClipboardService.historyConfigError ? ClipboardService.historyConfigError.message :
                                                               ""
            }
        }
    }
}
