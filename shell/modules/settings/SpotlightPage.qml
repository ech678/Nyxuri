import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

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
                    '{"id":"general.spotlight.section.applications","route":"general.spotlight","title":"Applications","context":"SpotlightPage","icon":"search","aliases":[]}'
            }
            iconName: "apps"

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Layout")
                iconName: "grid_view"

                trailing: SearchSelectMenuField {
                    id: appStylePicker

                    Layout.preferredWidth: 220
                    options: [
                        {
                            value: "list",
                            label: qsTr("List")
                        },
                        {
                            value: "grid",
                            label: qsTr("Grid")
                        }
                    ]
                    value: UiPreferences.spotlightAppStyle
                    closeOnAccept: true
                    Accessible.name: qsTr("Application layout")
                    onAccepted: value => UiPreferences.setSpotlightAppStyle(value)
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Application order")
                iconName: "sort"
                trailing: SearchSelectMenuField {
                    id: appOrderPicker
                    Layout.preferredWidth: 220
                    options: [
                        {
                            value: "smart",
                            label: qsTr("Smart")
                        },
                        {
                            value: "most-used",
                            label: qsTr("Most used")
                        },
                        {
                            value: "recently-used",
                            label: qsTr("Recently used")
                        },
                        {
                            value: "name",
                            label: qsTr("Name")
                        }
                    ]
                    value: UiPreferences.spotlightAppOrder
                    closeOnAccept: true
                    Accessible.name: qsTr("Application order")
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
                    '{"id":"general.spotlight.section.web-search","route":"general.spotlight","title":"Web search","context":"SpotlightPage","icon":"search","aliases":[]}'
            }
            iconName: "language"

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Search engine")
                iconName: "search"

                trailing: SearchSelectMenuField {
                    id: enginePicker

                    Layout.preferredWidth: 220
                    options: SpotlightSearchService.searchEngines
                    value: UiPreferences.spotlightSearchEngine
                    textRole: "label"
                    valueRole: "id"
                    closeOnAccept: true
                    leadingWidth: Metrics.iconM
                    Accessible.name: qsTr("Search engine")
                    onAccepted: value => {
                        return UiPreferences.setSpotlightSearchEngine(value);
                    }

                    leadingDelegate: Component {
                        Image {
                            property var optionData: null

                            source: optionData ? Qt.resolvedUrl("../../assets/icons/search-engines/"
                                                                + optionData.icon) : ""
                            sourceSize.width: Metrics.iconM * 2
                            sourceSize.height: Metrics.iconM * 2
                            fillMode: Image.PreserveAspectFit
                            smooth: true
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
                    '{"id":"general.spotlight.section.clipboard","route":"general.spotlight","title":"Clipboard","context":"SpotlightPage","icon":"search","aliases":[]}'
            }
            iconName: "content_paste"

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Layout")
                iconName: "view_sidebar"
                trailing: SearchSelectMenuField {
                    id: clipboardStylePicker
                    Layout.preferredWidth: 220
                    options: [
                        {
                            value: "default",
                            label: qsTr("Default")
                        },
                        {
                            value: "details",
                            label: qsTr("Details")
                        }
                    ]
                    value: UiPreferences.spotlightClipboardStyle
                    closeOnAccept: true
                    Accessible.name: qsTr("Clipboard layout")
                    onAccepted: value => UiPreferences.setSpotlightClipboardStyle(value)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("History limit")
                supportingText: qsTr("Oldest items are removed when new content is saved.")
                iconName: "history"

                trailing: MaterialStepper {
                    from: 50
                    to: 750
                    stepSize: 50
                    value: ClipboardService.historyLimit
                    enabled: ClipboardService.historyConfigLoaded
                    busy: ClipboardService.historyConfigBusy
                    Accessible.name: qsTr("History limit")
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
