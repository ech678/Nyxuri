import QtQuick
import QtQuick.Layouts
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Spotlight page (T3 M4): NexusPageBase scaffold + M1 select/stepper atoms.
// Caelestia has no Spotlight page — the layout follows the Nexus row language
// (label, optional subtext, trailing pill or stepper).
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("spotlight")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    function closeChildWindows() {
        appStylePicker.closeMenu();
        appOrderPicker.closeMenu();
        clipboardStylePicker.closeMenu();
        enginePicker.closeMenu();
    }

    Component.onCompleted: ClipboardService.loadHistoryConfig()

    readonly property var layoutOptions: [
        {
            "label": I18n.tr("List"),
            "value": "list"
        },
        {
            "label": I18n.tr("Grid"),
            "value": "grid"
        }
    ]
    readonly property var applicationOrderOptions: [
        {
            "label": I18n.tr("Smart"),
            "value": "smart"
        },
        {
            "label": I18n.tr("Most used"),
            "value": "most-used"
        },
        {
            "label": I18n.tr("Recently used"),
            "value": "recently-used"
        },
        {
            "label": I18n.tr("Name"),
            "value": "name"
        }
    ]
    readonly property var clipboardLayoutOptions: [
        {
            "label": I18n.tr("Default"),
            "value": "default"
        },
        {
            "label": I18n.tr("Details"),
            "value": "details"
        }
    ]
    readonly property var engineOptions: UiPreferences.searchEngines.map(engine => ({
        "label": engine.label,
        "value": engine.id
    }))

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Applications
        PreferenceHeader {
            first: true
            text: I18n.tr("Applications")
        }

        PreferenceSelect {
            id: appStylePicker

            first: true
            icon: "grid_view"
            label: I18n.tr("Layout")
            model: root.layoutOptions
            currentValue: UiPreferences.spotlightAppStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSpotlightAppStyle(value)

            SettingsSearchAnchor {
                id: searchAnchor0
                target: appStylePicker
                declaration:
                    '{"id":"spotlight.section.applications","route":"spotlight","title":"Applications","context":"SpotlightPage","icon":"search","aliases":["general.spotlight.section.applications"]}'
            }
        }

        PreferenceSelect {
            id: appOrderPicker

            last: true
            icon: "sort"
            label: I18n.tr("Application order")
            model: root.applicationOrderOptions
            currentValue: UiPreferences.spotlightAppOrder
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSpotlightAppOrder(value)
        }

        // Web search
        PreferenceHeader {
            text: I18n.tr("Web search")
        }

        PreferenceSelect {
            id: enginePicker

            first: true
            last: true
            icon: "language"
            label: I18n.tr("Search engine")
            model: root.engineOptions
            currentValue: UiPreferences.spotlightSearchEngine
            inputRegionService: PopupInputRegionService
            onSelected: value => {
                return UiPreferences.setSpotlightSearchEngine(value);
            }

            SettingsSearchAnchor {
                id: searchAnchor1
                target: enginePicker
                declaration:
                    '{"id":"spotlight.section.web-search","route":"spotlight","title":"Web search","context":"SpotlightPage","icon":"search","aliases":["general.spotlight.section.web-search"]}'
            }
        }

        // Clipboard
        PreferenceHeader {
            text: I18n.tr("Clipboard")
        }

        PreferenceSelect {
            id: clipboardStylePicker

            first: true
            icon: "view_sidebar"
            label: I18n.tr("Layout")
            model: root.clipboardLayoutOptions
            currentValue: UiPreferences.spotlightClipboardStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSpotlightClipboardStyle(value)

            SettingsSearchAnchor {
                id: searchAnchor2
                target: clipboardStylePicker
                declaration:
                    '{"id":"spotlight.section.clipboard","route":"spotlight","title":"Clipboard","context":"SpotlightPage","icon":"search","aliases":["general.spotlight.section.clipboard"]}'
            }
        }

        PreferenceStepper {
            id: historyLimitStepper

            last: true
            label: I18n.tr("History limit")
            subtext: I18n.tr("Oldest items are removed when new content is saved.")
            from: 50
            to: 750
            stepSize: 50
            value: ClipboardService.historyLimit
            enabled: ClipboardService.historyConfigLoaded
            busy: ClipboardService.historyConfigBusy
            onMoved: value => ClipboardService.setHistoryLimit(value)
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: ClipboardService.historyConfigError !== null
            tone: "error"
            message: ClipboardService.historyConfigError ? ClipboardService.historyConfigError.message : ""
        }
    }
}
