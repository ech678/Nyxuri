import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.modules.systemcards
import qs.shared.i18n

StyledFlickable {
    id: root

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
    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingXL

        SettingsSection {
            id: searchSection0
            Layout.fillWidth: true
            flat: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                target: searchSection0
                declaration:
                    '{"id":"sidebar.section.sidebars","route":"sidebar","title":"Sidebars","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.sidebars"]}'
            }
            iconName: "side_navigation"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Dashboard sidebar position")
                iconName: "dashboard"
                trailing: StyledButtonGroup {
                    model: [
                        {
                            value: "left",
                            label: I18n.tr("Left")
                        },
                        {
                            value: "right",
                            label: I18n.tr("Right")
                        }
                    ]
                    currentValue: PersonalizationConfig.dashboardSidebarSide
                    onValueSelected: value => PersonalizationConfig.setDashboardSidebarSide(value)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Quick settings sidebar position")
                iconName: "tune"
                trailing: StyledButtonGroup {
                    model: [
                        {
                            value: "left",
                            label: I18n.tr("Left")
                        },
                        {
                            value: "right",
                            label: I18n.tr("Right")
                        }
                    ]
                    currentValue: PersonalizationConfig.quickSettingsSidebarSide
                    onValueSelected: value => PersonalizationConfig.setQuickSettingsSidebarSide(value)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "side_navigation"
                title: I18n.tr("Keep sidebar loaded")
                supportingText: I18n.tr("Opens faster next time, but uses more memory")

                trailing: StyledSwitch {
                    checked: PersonalizationConfig.keepSidebarsLoaded
                    Accessible.name: I18n.tr("Keep sidebar loaded")
                    onToggled: PersonalizationConfig.setKeepSidebarsLoaded(checked)
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
                    '{"id":"sidebar.section.desktop-card-layout","route":"sidebar","title":"Desktop card layout","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.desktop-card-layout"]}'
            }
            iconName: "dashboard_customize"

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
                onValueSelected: value => {
                    return SystemCardService.setGlobalDesktopLayoutMode(value);
                }
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
                onValueSelected: value => {
                    return SystemCardService.setGlobalDesktopLayoutMode(value);
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "grid_4x4"
                title: I18n.tr("Snap desktop cards to grid")

                trailing: StyledSwitch {
                    checked: PersonalizationConfig.desktopCardGridSnapEnabled
                    Accessible.name: I18n.tr("Snap desktop cards to grid")
                    onToggled: PersonalizationConfig.setDesktopCardGridSnapEnabled(checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "grid_on"
                title: I18n.tr("Show desktop grid while dragging")

                trailing: StyledSwitch {
                    checked: PersonalizationConfig.desktopCardGridVisibleWhileDragging
                    Accessible.name: I18n.tr("Show desktop grid while dragging")
                    onToggled: PersonalizationConfig.setDesktopCardGridVisibleWhileDragging(checked)
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
                    '{"id":"sidebar.section.clock-style","route":"sidebar","title":"Clock style","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.clock-style"]}'
            }
            iconName: "schedule"

            StyledButtonGroup {
                Layout.fillWidth: true
                model: [
                    {
                        "value": "digital",
                        "label": I18n.tr("Digital"),
                        "icon": "timer_10"
                    },
                    {
                        "value": "cookie",
                        "label": I18n.tr("Cookie"),
                        "icon": "cookie"
                    }
                ]
                currentValue: UiPreferences.sidebarClockStyle
                buttonMinWidth: 120
                onValueSelected: value => {
                    return UiPreferences.setSidebarClockStyle(value);
                }
            }

            ColumnLayout {
                id: cookieSettings

                Layout.fillWidth: true
                Layout.topMargin: Metrics.spacingM
                spacing: Metrics.spacingS
                enabled: root.cookieClockActive
                opacity: root.cookieClockActive ? 1 : 0.42

                SettingsRow {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive
                    iconName: "add_triangle"
                    title: I18n.tr("Sides")
                    supportingText: I18n.tr("0 or 1 produces a circle; up to 40 sides")

                    trailing: MaterialStepper {
                        enabled: root.cookieClockActive
                        value: UiPreferences.sidebarCookieSides
                        from: 0
                        to: 40
                        stepSize: 1
                        onValueModified: value => {
                            return UiPreferences.setSidebarCookieSides(value);
                        }
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive
                    iconName: "autoplay"
                    title: I18n.tr("Constantly rotate")

                    trailing: StyledSwitch {
                        enabled: root.cookieClockActive
                        checked: UiPreferences.sidebarCookieConstantlyRotate
                        Accessible.name: I18n.tr("Constantly rotate")
                        onToggled: UiPreferences.setSidebarCookieConstantlyRotate(checked)
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive && (UiPreferences.sidebarCookieDialStyle === "dots"
                                                        || UiPreferences.sidebarCookieDialStyle === "full")
                    iconName: "brightness_7"
                    title: I18n.tr("Hour marks")
                    supportingText: I18n.tr("Available with Dots or Full dials")

                    trailing: StyledSwitch {
                        checked: UiPreferences.sidebarCookieHourMarks
                        Accessible.name: I18n.tr("Hour marks")
                        onToggled: UiPreferences.setSidebarCookieHourMarks(checked)
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive && UiPreferences.sidebarCookieDialStyle !== "numbers"
                    iconName: "timer_10"
                    title: I18n.tr("Digits in the middle")
                    supportingText: I18n.tr("Unavailable with the Numbers dial")

                    trailing: StyledSwitch {
                        checked: UiPreferences.sidebarCookieTimeIndicators
                        Accessible.name: I18n.tr("Digits in the middle")
                        onToggled: UiPreferences.setSidebarCookieTimeIndicators(checked)
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: Metrics.spacingXS
                    text: I18n.tr("Dial style")
                    color: Appearance.colors.colOnSurface
                    font.family: Typography.labelLarge.family
                    font.pixelSize: Typography.labelLarge.pixelSize
                    font.weight: Typography.labelLarge.weight
                }

                StyledButtonGroup {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive
                    model: [
                        {
                            "value": "none",
                            "label": I18n.tr("None"),
                            "icon": "block"
                        },
                        {
                            "value": "dots",
                            "label": I18n.tr("Dots"),
                            "icon": "graph_6"
                        },
                        {
                            "value": "full",
                            "label": I18n.tr("Full"),
                            "icon": "history_toggle_off"
                        },
                        {
                            "value": "numbers",
                            "label": I18n.tr("Digital"),
                            "icon": "counter_1"
                        }
                    ]
                    currentValue: UiPreferences.sidebarCookieDialStyle
                    horizontalPadding: Metrics.spacingXL
                    onValueSelected: value => {
                        return UiPreferences.setSidebarCookieDialStyle(value);
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: Metrics.spacingXS
                    text: I18n.tr("Hour hand")
                    color: Appearance.colors.colOnSurface
                    font.family: Typography.labelLarge.family
                    font.pixelSize: Typography.labelLarge.pixelSize
                    font.weight: Typography.labelLarge.weight
                }

                StyledButtonGroup {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive
                    model: [
                        {
                            "value": "hide",
                            "label": I18n.tr("None"),
                            "icon": "block"
                        },
                        {
                            "value": "classic",
                            "label": I18n.tr("Classic"),
                            "icon": "radio"
                        },
                        {
                            "value": "hollow",
                            "label": I18n.tr("Hollow"),
                            "icon": "circle"
                        },
                        {
                            "value": "fill",
                            "label": I18n.tr("Fill"),
                            "icon": "eraser_size_5"
                        }
                    ]
                    currentValue: UiPreferences.sidebarCookieHourHandStyle
                    horizontalPadding: Metrics.spacingXL
                    onValueSelected: value => {
                        return UiPreferences.setSidebarCookieHourHandStyle(value);
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: Metrics.spacingXS
                    text: I18n.tr("Minute hand")
                    color: Appearance.colors.colOnSurface
                    font.family: Typography.labelLarge.family
                    font.pixelSize: Typography.labelLarge.pixelSize
                    font.weight: Typography.labelLarge.weight
                }

                StyledButtonGroup {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive
                    model: [
                        {
                            "value": "hide",
                            "label": I18n.tr("None"),
                            "icon": "block"
                        },
                        {
                            "value": "classic",
                            "label": I18n.tr("Classic"),
                            "icon": "radio"
                        },
                        {
                            "value": "thin",
                            "label": I18n.tr("Thin"),
                            "icon": "line_end"
                        },
                        {
                            "value": "medium",
                            "label": I18n.tr("Medium"),
                            "icon": "eraser_size_2"
                        },
                        {
                            "value": "bold",
                            "label": I18n.tr("Bold"),
                            "icon": "eraser_size_4"
                        }
                    ]
                    currentValue: UiPreferences.sidebarCookieMinuteHandStyle
                    horizontalPadding: Metrics.spacingM * 2
                    contentSpacing: Metrics.spacingXS
                    onValueSelected: value => {
                        return UiPreferences.setSidebarCookieMinuteHandStyle(value);
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: Metrics.spacingXS
                    text: I18n.tr("Second hand")
                    color: Appearance.colors.colOnSurface
                    font.family: Typography.labelLarge.family
                    font.pixelSize: Typography.labelLarge.pixelSize
                    font.weight: Typography.labelLarge.weight
                }

                StyledButtonGroup {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive
                    model: [
                        {
                            "value": "hide",
                            "label": I18n.tr("None"),
                            "icon": "block"
                        },
                        {
                            "value": "classic",
                            "label": I18n.tr("Classic"),
                            "icon": "radio"
                        },
                        {
                            "value": "line",
                            "label": I18n.tr("Line"),
                            "icon": "line_end"
                        },
                        {
                            "value": "dot",
                            "label": I18n.tr("Dots"),
                            "icon": "adjust"
                        }
                    ]
                    currentValue: UiPreferences.sidebarCookieSecondHandStyle
                    horizontalPadding: Metrics.spacingXL
                    onValueSelected: value => {
                        return UiPreferences.setSidebarCookieSecondHandStyle(value);
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: Metrics.spacingXS
                    text: I18n.tr("Date style")
                    color: Appearance.colors.colOnSurface
                    font.family: Typography.labelLarge.family
                    font.pixelSize: Typography.labelLarge.pixelSize
                    font.weight: Typography.labelLarge.weight
                }

                StyledButtonGroup {
                    Layout.fillWidth: true
                    enabled: root.cookieClockActive
                    model: [
                        {
                            "value": "hide",
                            "label": I18n.tr("None"),
                            "icon": "block"
                        },
                        {
                            "value": "bubble",
                            "label": I18n.tr("Bubble"),
                            "icon": "bubble_chart"
                        },
                        {
                            "value": "border",
                            "label": I18n.tr("Border"),
                            "icon": "rotate_right"
                        },
                        {
                            "value": "rect",
                            "label": I18n.tr("Rect"),
                            "icon": "rectangle"
                        }
                    ]
                    currentValue: UiPreferences.sidebarCookieDateStyle
                    horizontalPadding: Metrics.spacingXL
                    onValueSelected: value => {
                        return UiPreferences.setSidebarCookieDateStyle(value);
                    }
                }
            }
        }

        SettingsSection {
            id: searchSection3
            Layout.fillWidth: true
            flat: true
            title: searchAnchor3.title
            SettingsSearchAnchor {
                id: searchAnchor3
                target: searchSection3
                declaration:
                    '{"id":"sidebar.section.system-cards","route":"sidebar","title":"System cards","context":"GeneralSidebarPage","icon":"side_navigation","aliases":["general.sidebar.section.system-cards"]}'
            }
            iconName: "widgets"

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Metrics.spacingS
                rowSpacing: Metrics.spacingS

                Repeater {
                    model: SystemCardService.cardIds

                    delegate: SettingsRow {
                        required property string modelData

                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        iconName: SystemCardService.cardIcon(modelData)
                        title: SystemCardService.cardName(modelData)
                        supportingText: {
                            const cards = SystemCardService.cards;
                            const state = cards ? cards[modelData] : null;
                            return state && state.container === "desktop" ? I18n.tr("Desktop") : I18n.tr(
                                                                                "Sidebar");
                        }

                        trailing: StyledSwitch {
                            checked: {
                                const cards = SystemCardService.cards;
                                const state = cards ? cards[modelData] : null;
                                return state ? state.enabled : true;
                            }
                            Accessible.name: SystemCardService.cardName(modelData)
                            onToggled: SystemCardService.setCardEnabled(modelData, checked)
                        }
                    }
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "developer_board"
                title: I18n.tr("GPU")
                supportingText: I18n.tr("Select the graphics device shown by the GPU card")

                trailing: SearchSelectMenuField {
                    Layout.preferredWidth: 220
                    options: root.gpuOptions
                    value: UiPreferences.systemMonitorGpuId
                    placeholder: I18n.tr("Auto")
                    closeOnAccept: true
                    onAccepted: value => {
                        return UiPreferences.setSystemMonitorGpuId(value);
                    }
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "speed"
                title: I18n.tr("System monitor snapshot interval")

                trailing: MaterialFilledTextField {
                    id: intervalField

                    Layout.preferredWidth: 150
                    labelText: I18n.tr("Interval")
                    text: String(UiPreferences.systemMonitorIntervalMs)
                    error: text.length === 0 || !acceptableInput
                    inputMethodHints: Qt.ImhDigitsOnly
                    trailingContentWidth: 40
                    onEditingFinished: {
                        UiPreferences.setSystemMonitorIntervalMs(text);
                        text = String(UiPreferences.systemMonitorIntervalMs);
                    }

                    validator: IntValidator {
                        bottom: 100
                        top: 60000
                    }

                    trailingContent: Component {
                        Text {
                            anchors.fill: parent
                            text: I18n.tr("ms")
                            color: Appearance.colors.colOnSurfaceVariant
                            font.family: Typography.bodyMedium.family
                            font.pixelSize: Typography.bodyMedium.pixelSize
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "data_usage"
                title: I18n.tr("Disk capacity")
                supportingText: I18n.tr("Select the physical disk shown by the capacity card")

                trailing: SearchSelectMenuField {
                    Layout.preferredWidth: 260
                    options: root.capacityDiskOptions
                    value: UiPreferences.storageCapacityDiskDevice
                    placeholder: I18n.tr("Follow Disk I/O card")
                    closeOnAccept: true
                    onAccepted: value => {
                        return UiPreferences.setStorageCapacityDiskDevice(value);
                    }
                }
            }
        }
    }
}
