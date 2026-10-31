import QtQuick
import QtQuick.Layouts
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Dock page (T3 M4): NexusPageBase scaffold + M1 atom rows. The first-run
// integration prompt and the config error banner stay above the groups; the
// minimize-animation row folds its busy state into the subtext.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("dock")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        NiriSetupPrompt {
            Layout.fillWidth: true
            visible: DockService.supportsMinimizeEffects && integrationState !== "ready" && (integrationState
                                                                                             !== "loading"
                                                                                             || error.length
                                                                                             > 0)
            title: I18n.tr("First-time setup")
            description: I18n.tr("Set up window minimization animations.")
            integrationState: NiriConfigService.state("minimize-animation")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "minimize-animation"
            blocked: NiriConfigService.busy
            error: NiriConfigService.errorFeature === "minimize-animation" ? NiriConfigService.error :
                                                                             NiriConfigService.readError
            onSetupRequested: NiriConfigService.setup("minimize-animation")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DockService.configError.length > 0
            tone: "error"
            message: DockService.configError
        }

        // Appearance
        PreferenceHeader {
            first: true
            text: I18n.tr("Appearance")
        }

        PreferenceSelect {
            id: edgeSelect

            first: true
            label: I18n.tr("Screen edge")
            model: [
                {
                    "label": I18n.tr("Left"),
                    "value": "left"
                },
                {
                    "label": I18n.tr("Bottom"),
                    "value": "bottom"
                },
                {
                    "label": I18n.tr("Right"),
                    "value": "right"
                }
            ]
            currentValue: DockService.position
            inputRegionService: PopupInputRegionService
            onSelected: value => DockService.setOption("position", String(value))

            SettingsSearchAnchor {
                id: appearanceAnchor
                target: edgeSelect
                declaration:
                    '{"id":"dock.section.appearance","route":"dock","title":"Appearance","context":"DockPage","icon":"dock_to_bottom","aliases":["general.dock.section.appearance","size","position","magnification","surface style","notch"]}'
            }
        }

        PreferenceSlider {
            label: I18n.tr("Icon size")
            valueLabel: Math.round(DockService.iconSize) + " px"
            value: DockService.iconSize
            from: 32
            to: 80
            stepSize: 2
            onMoved: value => DockService.setOption("iconSize", Math.round(value))
        }

        PreferenceToggle {
            text: I18n.tr("Magnify on hover")
            checked: DockService.magnification
            onToggled: DockService.setOption("magnification", checked)
        }

        PreferenceSlider {
            label: I18n.tr("Magnification")
            enabled: DockService.magnification
            valueLabel: Math.round(DockService.magnificationScale * 100) + "%"
            value: DockService.magnificationScale * 100
            from: 100
            to: 200
            stepSize: 5
            onMoved: value => DockService.setOption("magnificationScale", Math.round(value) / 100)
        }

        PreferenceSelect {
            last: true
            label: I18n.tr("Surface style")
            model: [
                {
                    "label": I18n.tr("Default"),
                    "value": "default"
                },
                {
                    "label": I18n.tr("Notch"),
                    "value": "notch"
                }
            ]
            currentValue: DockService.surfaceStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => DockService.setOption("surfaceStyle", String(value))
        }

        // Behavior
        PreferenceHeader {
            text: I18n.tr("Behavior")
        }

        PreferenceToggle {
            id: autoHideToggle

            first: true
            text: I18n.tr("Automatically hide")
            checked: DockService.autoHide
            onToggled: DockService.setOption("autoHide", checked)

            SettingsSearchAnchor {
                id: behaviorAnchor
                target: autoHideToggle
                declaration:
                    '{"id":"dock.section.behavior","route":"dock","title":"Behavior","context":"DockPage","icon":"touch_app","aliases":["general.dock.section.behavior","auto hide","bounce","recent","indicators","pin","minimize","animation","genie","scale"]}'
            }
        }

        PreferenceToggle {
            text: I18n.tr("Bounce when launching")
            checked: DockService.launchBounce
            onToggled: DockService.setOption("launchBounce", checked)
        }

        PreferenceToggle {
            text: I18n.tr("Show running indicators")
            checked: DockService.showIndicators
            onToggled: DockService.setOption("showIndicators", checked)
        }

        PreferenceSelect {
            visible: !DockService.supportsMinimizeEffects || NiriConfigService.ready("minimize-animation")
            label: I18n.tr("Minimize animation")
            subtext: !DockService.supportsMinimizeEffects ? I18n.tr(
                                                                "Window animation selection is unavailable in this session") :
                                                            NiriConfigService.minimizeAnimationsDisabled
                                                            ? I18n.tr(
                                                                  "Animations are disabled in your configuration") :
                                                              NiriConfigService.busy
                                                              && NiriConfigService.activeFeature
                                                              === "minimize-animation" ? I18n.tr("Checking…") :
                                                                                         ""
            enabled: DockService.supportsMinimizeEffects && NiriConfigService.ready("minimize-animation") &&
                     !NiriConfigService.busy
            model: [
                {
                    "label": I18n.tr("Genie"),
                    "value": "genie"
                },
                {
                    "label": I18n.tr("Scale"),
                    "value": "scale"
                }
            ]
            currentValue: NiriConfigService.minimizeEffect
            inputRegionService: PopupInputRegionService
            onSelected: value => NiriConfigService.setMinimizeEffect(String(value))
        }

        PreferenceToggle {
            text: I18n.tr("Show recent applications")
            checked: DockService.showRecent
            onToggled: DockService.setOption("showRecent", checked)
        }

        PreferenceToggle {
            last: true
            text: I18n.tr("Pin applications from the menu")
            checked: DockService.contextPinning
            onToggled: DockService.setOption("contextPinning", checked)
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: NiriConfigService.ready("minimize-animation") && NiriConfigService.errorFeature
                     === "minimize-animation" && NiriConfigService.error.length > 0
            tone: "error"
            message: NiriConfigService.error
        }

        // Window previews
        PreferenceHeader {
            visible: DockService.supportsThumbnails
            text: I18n.tr("Window previews")
        }

        PreferenceToggle {
            id: thumbnailsToggle

            visible: DockService.supportsThumbnails
            first: true
            text: I18n.tr("Show window thumbnails")
            checked: DockService.showThumbnails
            onToggled: DockService.setOption("showThumbnails", checked)

            SettingsSearchAnchor {
                id: previewsAnchor
                target: thumbnailsToggle
                declaration:
                    '{"id":"dock.section.previews","route":"dock","title":"Window previews","context":"DockPage","icon":"preview","aliases":["general.dock.section.previews","thumbnails","hover"],"availability":"dock-previews"}'
            }
        }

        PreferenceSlider {
            visible: DockService.supportsThumbnails
            last: true
            label: I18n.tr("Preview size")
            enabled: DockService.showThumbnails
            valueLabel: Math.round(DockService.previewSize) + " px"
            value: DockService.previewSize
            from: 96
            to: 240
            stepSize: 8
            onMoved: value => DockService.setOption("previewSize", Math.round(value))
        }
    }
}
