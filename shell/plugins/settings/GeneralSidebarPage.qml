pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Sidebars page (T3 M4): NexusPageBase scaffold + M1 atom rows. The desktop
// card layout block keeps its twin segmented pickers (mode + placement
// presets share one backing value — a semantic picker the atom suite has no
// shape for); the cookie clock sub-settings dim to 42% while the digital
// clock is active, exactly like the pre-M4 block did. GPU/disk sampling rows
// arm SystemMonitorService consumers for as long as this page is presented.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("sidebar")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    readonly property bool cookieClockActive: UiPreferences.sidebarClockStyle === "cookie"
    readonly property var gpuOptions: buildGpuOptions()
    readonly property var capacityDiskOptions: buildCapacityDiskOptions()

    function gpuPciLabel(gpu) {
        const pciId = String(gpu.pciId || "");
        if (pciId !== "")
            return pciId;

        const id = String(gpu.id || "");
        return id.indexOf("pci:") === 0 ? id.slice(4) : id;
    }

    function buildGpuOptions() {
        const options = [
                  {
                      "value": "auto",
                      "label": I18n.tr("Auto")
                  }
              ];
        const names = ({});
        for (let index = 0; index < SystemMonitorService.gpus.length; index += 1) {
            const name = String(SystemMonitorService.gpus[index].name || I18n.tr("Graphics device"));
            names[name] = Number(names[name] || 0) + 1;
        }
        for (let index = 0; index < SystemMonitorService.gpus.length; index += 1) {
            const gpu = SystemMonitorService.gpus[index];
            const id = String(gpu.id || "");
            if (id === "")
                continue;

            const name = String(gpu.name || I18n.tr("Graphics device"));
            options.push({
                             "value": id,
                             "label": names[name] > 1 ? name + " · " + root.gpuPciLabel(gpu) : name
                         });
        }
        const preferred = UiPreferences.systemMonitorGpuId;
        if (preferred !== "auto") {
            let found = false;
            for (let index = 1; index < options.length; index += 1) {
                if (options[index].value === preferred) {
                    found = true;
                    break;
                }
            }
            if (!found)
                options.push({
                                 "value": preferred,
                                 "label": preferred + " · " + I18n.tr("Currently unavailable")
                             });
        }
        return options;
    }

    function buildCapacityDiskOptions() {
        const language = I18nService.language;
        const options = [
                  {
                      "value": "follow-io",
                      "label": I18n.tr("Follow Disk I/O card")
                  }
              ];
        for (let index = 0; index < SystemMonitorService.disks.length; index += 1) {
            const device = String(SystemMonitorService.disks[index].device || "");
            if (device !== "")
                options.push({
                                 "value": device,
                                 "label": device
                             });
        }
        const preferred = UiPreferences.storageCapacityDiskDevice;
        if (preferred !== "follow-io") {
            let found = false;
            for (let index = 1; index < options.length; index += 1) {
                if (options[index].value === preferred) {
                    found = true;
                    break;
                }
            }
            if (!found)
                options.push({
                                 "value": preferred,
                                 "label": preferred + " · " + I18n.tr("Currently unavailable")
                             });
        }
        return options;
    }

    onPresentationActiveChanged: SystemMonitorService.setConsumerModules("general-sidebar-settings",
                                                                         root.presentationActive ? ["gpu",
                                                                                                    "disk"] : [])
    Component.onCompleted: SystemMonitorService.setConsumerModules("general-sidebar-settings",
                                                                   root.presentationActive ? ["gpu", "disk"] :
                                                                                             [])
    Component.onDestruction: SystemMonitorService.clearConsumer("general-sidebar-settings")

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Sidebars
        PreferenceHeader {
            first: true
            text: I18n.tr("Sidebars")
        }

        PreferenceSelect {
            id: dashboardSideSelect

            first: true
            label: I18n.tr("Dashboard sidebar position")
            model: [
                {
                    "label": I18n.tr("Left"),
                    "value": "left"
                },
                {
                    "label": I18n.tr("Right"),
                    "value": "right"
                }
            ]
            currentValue: PersonalizationConfig.dashboardSidebarSide
            inputRegionService: PopupInputRegionService
            onSelected: value => PersonalizationConfig.setDashboardSidebarSide(value)

            SettingsSearchAnchor {
                id: searchAnchor0
                target: dashboardSideSelect
                declaration:
                    '{"id":"sidebar.section.sidebars","route":"sidebar","title":"Sidebars","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.sidebars"]}'
            }
        }

        PreferenceSelect {
            label: I18n.tr("Quick settings sidebar position")
            model: [
                {
                    "label": I18n.tr("Left"),
                    "value": "left"
                },
                {
                    "label": I18n.tr("Right"),
                    "value": "right"
                }
            ]
            currentValue: PersonalizationConfig.quickSettingsSidebarSide
            inputRegionService: PopupInputRegionService
            onSelected: value => PersonalizationConfig.setQuickSettingsSidebarSide(value)
        }

        PreferenceToggle {
            last: true
            text: I18n.tr("Keep sidebar loaded")
            subtext: I18n.tr("Opens faster next time, but uses more memory")
            checked: PersonalizationConfig.keepSidebarsLoaded
            onToggled: PersonalizationConfig.setKeepSidebarsLoaded(checked)
        }

        // Desktop card layout
        PreferenceHeader {
            text: I18n.tr("Desktop card layout")
        }

        ConnectedRect {
            id: layoutBlock

            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: layoutColumn.implicitHeight + NexusStyle.padding.medium * 2

            ColumnLayout {
                id: layoutColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                StyledButtonGroup {
                    Layout.fillWidth: true
                    model: [
                        {
                            "value": "free",
                            "label": I18n.tr("Free drag")
                        },
                        {
                            "value": "leastBusy",
                            "label": I18n.tr("Least busy")
                        },
                        {
                            "value": "mostBusy",
                            "label": I18n.tr("Most busy")
                        }
                    ]
                    currentValue: SystemCardService.globalDesktopLayoutMode
                    onValueSelected: value => SystemCardService.setGlobalDesktopLayoutMode(value)
                }

                StyledButtonGroup {
                    Layout.fillWidth: true
                    model: [
                        {
                            "value": "screenTopLeft",
                            "label": I18n.tr("Top left")
                        },
                        {
                            "value": "screenTopRight",
                            "label": I18n.tr("Top right")
                        },
                        {
                            "value": "screenBottomLeft",
                            "label": I18n.tr("Bottom left")
                        },
                        {
                            "value": "screenBottomRight",
                            "label": I18n.tr("Bottom right")
                        },
                        {
                            "value": "screenCenter",
                            "label": I18n.tr("Center")
                        }
                    ]
                    currentValue: SystemCardService.globalDesktopLayoutMode
                    buttonMinWidth: 0
                    onValueSelected: value => SystemCardService.setGlobalDesktopLayoutMode(value)
                }
            }

            SettingsSearchAnchor {
                id: searchAnchor1
                target: layoutBlock
                declaration:
                    '{"id":"sidebar.section.desktop-card-layout","route":"sidebar","title":"Desktop card layout","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.desktop-card-layout"]}'
            }
        }

        PreferenceToggle {
            first: true
            text: I18n.tr("Snap desktop cards to grid")
            checked: PersonalizationConfig.desktopCardGridSnapEnabled
            onToggled: PersonalizationConfig.setDesktopCardGridSnapEnabled(checked)
        }

        PreferenceToggle {
            last: true
            text: I18n.tr("Show desktop grid while dragging")
            checked: PersonalizationConfig.desktopCardGridVisibleWhileDragging
            onToggled: PersonalizationConfig.setDesktopCardGridVisibleWhileDragging(checked)
        }

        // Clock style
        PreferenceHeader {
            text: I18n.tr("Clock style")
        }

        PreferenceSelect {
            id: clockStyleSelect

            first: true
            label: I18n.tr("Style")
            model: [
                {
                    "label": I18n.tr("Digital"),
                    "value": "digital"
                },
                {
                    "label": I18n.tr("Cookie"),
                    "value": "cookie"
                }
            ]
            currentValue: UiPreferences.sidebarClockStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSidebarClockStyle(value)

            SettingsSearchAnchor {
                id: searchAnchor2
                target: clockStyleSelect
                declaration:
                    '{"id":"sidebar.section.clock-style","route":"sidebar","title":"Clock style","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.clock-style"]}'
            }
        }

        // Cookie clock sub-settings — dimmed to 42% while digital is active.
        PreferenceStepper {
            label: I18n.tr("Sides")
            subtext: I18n.tr("0 or 1 produces a circle; up to 40 sides")
            enabled: root.cookieClockActive
            opacity: root.cookieClockActive ? 1 : 0.42
            value: UiPreferences.sidebarCookieSides
            from: 0
            to: 40
            stepSize: 1
            onMoved: value => UiPreferences.setSidebarCookieSides(value)
        }

        PreferenceToggle {
            text: I18n.tr("Constantly rotate")
            enabled: root.cookieClockActive
            opacity: root.cookieClockActive ? 1 : 0.42
            checked: UiPreferences.sidebarCookieConstantlyRotate
            onToggled: UiPreferences.setSidebarCookieConstantlyRotate(checked)
        }

        PreferenceToggle {
            text: I18n.tr("Hour marks")
            subtext: I18n.tr("Available with Dots or Full dials")
            enabled: root.cookieClockActive && (UiPreferences.sidebarCookieDialStyle === "dots"
                                                || UiPreferences.sidebarCookieDialStyle === "full")
            opacity: root.cookieClockActive ? 1 : 0.42
            checked: UiPreferences.sidebarCookieHourMarks
            onToggled: UiPreferences.setSidebarCookieHourMarks(checked)
        }

        PreferenceToggle {
            text: I18n.tr("Digits in the middle")
            subtext: I18n.tr("Unavailable with the Numbers dial")
            enabled: root.cookieClockActive && UiPreferences.sidebarCookieDialStyle !== "numbers"
            opacity: root.cookieClockActive ? 1 : 0.42
            checked: UiPreferences.sidebarCookieTimeIndicators
            onToggled: UiPreferences.setSidebarCookieTimeIndicators(checked)
        }

        PreferenceSelect {
            label: I18n.tr("Dial style")
            enabled: root.cookieClockActive
            opacity: root.cookieClockActive ? 1 : 0.42
            model: [
                {
                    "label": I18n.tr("None"),
                    "value": "none"
                },
                {
                    "label": I18n.tr("Dots"),
                    "value": "dots"
                },
                {
                    "label": I18n.tr("Full"),
                    "value": "full"
                },
                {
                    "label": I18n.tr("Digital"),
                    "value": "numbers"
                }
            ]
            currentValue: UiPreferences.sidebarCookieDialStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSidebarCookieDialStyle(value)
        }

        PreferenceSelect {
            label: I18n.tr("Hour hand")
            enabled: root.cookieClockActive
            opacity: root.cookieClockActive ? 1 : 0.42
            model: [
                {
                    "label": I18n.tr("None"),
                    "value": "hide"
                },
                {
                    "label": I18n.tr("Classic"),
                    "value": "classic"
                },
                {
                    "label": I18n.tr("Hollow"),
                    "value": "hollow"
                },
                {
                    "label": I18n.tr("Fill"),
                    "value": "fill"
                }
            ]
            currentValue: UiPreferences.sidebarCookieHourHandStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSidebarCookieHourHandStyle(value)
        }

        PreferenceSelect {
            label: I18n.tr("Minute hand")
            enabled: root.cookieClockActive
            opacity: root.cookieClockActive ? 1 : 0.42
            model: [
                {
                    "label": I18n.tr("None"),
                    "value": "hide"
                },
                {
                    "label": I18n.tr("Classic"),
                    "value": "classic"
                },
                {
                    "label": I18n.tr("Thin"),
                    "value": "thin"
                },
                {
                    "label": I18n.tr("Medium"),
                    "value": "medium"
                },
                {
                    "label": I18n.tr("Bold"),
                    "value": "bold"
                }
            ]
            currentValue: UiPreferences.sidebarCookieMinuteHandStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSidebarCookieMinuteHandStyle(value)
        }

        PreferenceSelect {
            label: I18n.tr("Second hand")
            enabled: root.cookieClockActive
            opacity: root.cookieClockActive ? 1 : 0.42
            model: [
                {
                    "label": I18n.tr("None"),
                    "value": "hide"
                },
                {
                    "label": I18n.tr("Classic"),
                    "value": "classic"
                },
                {
                    "label": I18n.tr("Line"),
                    "value": "line"
                },
                {
                    "label": I18n.tr("Dots"),
                    "value": "dot"
                }
            ]
            currentValue: UiPreferences.sidebarCookieSecondHandStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSidebarCookieSecondHandStyle(value)
        }

        PreferenceSelect {
            last: true
            label: I18n.tr("Date style")
            enabled: root.cookieClockActive
            opacity: root.cookieClockActive ? 1 : 0.42
            model: [
                {
                    "label": I18n.tr("None"),
                    "value": "hide"
                },
                {
                    "label": I18n.tr("Bubble"),
                    "value": "bubble"
                },
                {
                    "label": I18n.tr("Border"),
                    "value": "border"
                },
                {
                    "label": I18n.tr("Rect"),
                    "value": "rect"
                }
            ]
            currentValue: UiPreferences.sidebarCookieDateStyle
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSidebarCookieDateStyle(value)
        }

        // System cards
        PreferenceHeader {
            text: I18n.tr("System cards")
        }

        GridLayout {
            id: cardGrid

            Layout.fillWidth: true
            columns: 2
            columnSpacing: NexusStyle.padding.small
            rowSpacing: NexusStyle.padding.small

            SettingsSearchAnchor {
                id: searchAnchor3
                target: cardGrid
                declaration:
                    '{"id":"sidebar.section.system-cards","route":"sidebar","title":"System cards","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.system-cards"]}'
            }

            Repeater {
                model: SystemCardService.cardIds

                delegate: PreferenceToggle {
                    id: cardToggle

                    required property string modelData

                    first: true
                    last: true
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: SystemCardService.cardName(cardToggle.modelData)
                    subtext: {
                        const cards = SystemCardService.cards;
                        const state = cards ? cards[cardToggle.modelData] : null;
                        return state && state.container === "desktop" ? I18n.tr("Desktop") : I18n.tr(
                                                                            "Sidebar");
                    }
                    checked: {
                        const cards = SystemCardService.cards;
                        const state = cards ? cards[cardToggle.modelData] : null;
                        return state ? state.enabled : true;
                    }
                    onToggled: SystemCardService.setCardEnabled(cardToggle.modelData, checked)
                }
            }
        }

        PreferenceSelect {
            icon: "developer_board"
            label: I18n.tr("GPU")
            subtext: I18n.tr("Select the graphics device shown by the GPU card")
            model: root.gpuOptions
            currentValue: UiPreferences.systemMonitorGpuId
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setSystemMonitorGpuId(value)
        }

        PreferenceInput {
            id: intervalRow

            label: I18n.tr("System monitor snapshot interval")
            smallField: true
            value: String(UiPreferences.systemMonitorIntervalMs)
            validate: text => {
                const parsed = Number(text);
                return Number.isInteger(parsed) && parsed >= 100 && parsed <= 60000;
            }
            onEditingFinished: value => {
                UiPreferences.setSystemMonitorIntervalMs(Number(value));
                intervalRow.field.text = String(UiPreferences.systemMonitorIntervalMs);
            }
        }

        PreferenceSelect {
            last: true
            icon: "data_usage"
            label: I18n.tr("Disk capacity")
            subtext: I18n.tr("Select the physical disk shown by the capacity card")
            model: root.capacityDiskOptions
            currentValue: UiPreferences.storageCapacityDiskDevice
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setStorageCapacityDiskDevice(value)
        }
    }
}
