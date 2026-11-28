import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
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
                anchorId: "spotlight.section.applications"
            }
        }

        PreferenceSelect {
            id: appOrderPicker

            icon: "sort"
            label: I18n.tr("Application order")
            model: root.applicationOrderOptions
            currentValue: UiPreferences.spotlightAppOrder
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSpotlightAppOrder(value)
        }

        PreferenceSlider {
            visible: UiPreferences.spotlightAppStyle === "grid"
            label: I18n.tr("Grid icon size")
            valueLabel: Math.round(PersonalizationConfig.spotlightIconSize) + " px"
            value: PersonalizationConfig.spotlightIconSize
            from: 36
            to: 96
            stepSize: 4
            modified: PersonalizationConfig.spotlightIconSize !== 56
            onMoved: value => PersonalizationConfig.setSpotlightIconSize(Math.round(value))
            onResetRequested: PersonalizationConfig.setSpotlightIconSize(56)
        }

        PreferenceToggle {
            text: I18n.tr("Follow theme opacity")
            checked: PersonalizationConfig.spotlightOpacity < 0
            modified: PersonalizationConfig.spotlightOpacity >= 0
            onToggled: checked => PersonalizationConfig.setSpotlightOpacity(checked ? -1 : PersonalizationConfig.shellBackgroundOpacity)
            onResetRequested: PersonalizationConfig.setSpotlightOpacity(-1)
        }

        PreferenceSlider {
            visible: PersonalizationConfig.spotlightOpacity >= 0
            label: I18n.tr("Launcher opacity")
            valueLabel: Math.round(Math.max(0, PersonalizationConfig.spotlightOpacity) * 100) + " %"
            value: Math.round(Math.max(0, PersonalizationConfig.spotlightOpacity) * 100)
            from: 0
            to: 100
            stepSize: 5
            modified: PersonalizationConfig.spotlightOpacity >= 0
            onMoved: value => PersonalizationConfig.setSpotlightOpacity(Math.round(value) / 100)
            onResetRequested: PersonalizationConfig.setSpotlightOpacity(-1)
        }

        PreferenceToggle {
            last: true
            text: I18n.tr("Background blur")
            enabled: BlurService.enabled
            checked: PersonalizationConfig.spotlightBlurEnabled
            modified: !PersonalizationConfig.spotlightBlurEnabled
            onToggled: PersonalizationConfig.setSpotlightBlurEnabled(checked)
            onResetRequested: PersonalizationConfig.setSpotlightBlurEnabled(true)
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
                anchorId: "spotlight.section.web-search"
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
                anchorId: "spotlight.section.clipboard"
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
