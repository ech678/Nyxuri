import qs.services
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

BarWidgetSwitcherArea {
    id: root
    property color contentColor: Appearance.colors.colOnSecondaryContainer
    property bool contentColorOverridden: false
    property bool alwaysShowAllResources: false
    horizontalExtraPadding: 12
    // D4b entry axes: the five meters, icon skin and the percentage
    // readout ride the lane entry (flat [bar.resources] folded by the
    // v4 migration). Warning thresholds stay bridge literals (internal,
    // no settings surface).
    property var widgetEntry: null
    readonly property bool showRam: BarWidgetDefaults.option("systemMonitor", root.widgetEntry, "ram")
    readonly property bool showCpu: BarWidgetDefaults.option("systemMonitor", root.widgetEntry, "cpu")
    readonly property bool showCpuTemp: BarWidgetDefaults.option("systemMonitor", root.widgetEntry, "cpuTemp")
    readonly property bool showDisk: BarWidgetDefaults.option("systemMonitor", root.widgetEntry, "disk")
    readonly property bool showSwap: BarWidgetDefaults.option("systemMonitor", root.widgetEntry, "swap")
    readonly property string iconStyle: BarWidgetDefaults.option("systemMonitor", root.widgetEntry, "iconStyle")
    readonly property bool showValue: BarWidgetDefaults.option("systemMonitor", root.widgetEntry, "showValue")

    readonly property var cpuSnapshot: SystemMonitorService.cpu || ({})
    readonly property var memorySnapshot: SystemMonitorService.memory || ({})
    readonly property var rootDisk: diskForDevice(UiPreferences.systemMonitorDiskDevice, true)

    function diskForDevice(device, fallbackToFirst) {
        const wanted = String(device || "");
        for (let index = 0; index < SystemMonitorService.disks.length; index++) {
            const disk = SystemMonitorService.disks[index];
            if (String(disk.device || "") === wanted)
                return disk;
        }
        return fallbackToFirst && SystemMonitorService.disks.length > 0
            ? SystemMonitorService.disks[0] : ({ });
    }
    readonly property real cpuRatio: Math.max(0, Math.min(1, Number(root.cpuSnapshot.usagePercent || 0) / 100))
    readonly property real memoryRatio: Math.max(0, Math.min(1, Number(root.memorySnapshot.usagePercent || 0) / 100))
    readonly property real cpuTemperature: Number(root.cpuSnapshot.packageTemperatureCelsius
                                                  ?? root.cpuSnapshot.temperatureCelsius ?? 0)
    readonly property real diskRatio: Math.max(0, Math.min(1, Number(root.rootDisk.usagePercent || 0) / 100))
    readonly property real swapUsedBytes: Number(SystemMonitorService.swapUsedBytes || 0)
    readonly property real swapTotalBytes: Number(SystemMonitorService.swapTotalBytes || 0)
    readonly property real swapRatio: root.swapTotalBytes > 0
                                      ? Math.max(0, Math.min(1, root.swapUsedBytes / root.swapTotalBytes)) : 0
    property QtObject resourceMonitor: ResourceUsageMonitor {
        target: root
        ownerId: "shell.bar.resources"
        modules: ["cpu", "memory", "disk"]
    }

    readonly property bool clickForDetails: Config.options?.bar?.m3?.tooltips?.clickToShow ?? false
    hoverEnabled: true

    onClicked: mouse => {
        if (mouse.button === Qt.LeftButton && root.clickForDetails)
            resourcesPopup.active = !resourcesPopup.active;
    }

    rowDefault: Component {
        RowLayout {
            spacing: 0
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                shown: root.showRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                shown: root.showCpu
                percentage: root.cpuRatio
                Layout.leftMargin: shown ? 6 : 0
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                shown: root.showCpuTemp
                percentage: root.cpuTemperature / 100
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                shown: root.showDisk
                percentage: root.diskRatio
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                shown: root.showSwap
                percentage: root.swapRatio
                Layout.leftMargin: shown ? 6 : 0
                warningThreshold: Config.options.bar.m3.resources.swapWarningThreshold
            }
        }
    }

    rowMaterial: Component {
        RowLayout {
            spacing: 0
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                shown: root.showRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                shown: root.showCpu
                percentage: root.cpuRatio
                Layout.leftMargin: shown ? 6 : 0
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                shown: root.showCpuTemp
                percentage: root.cpuTemperature / 100
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                shown: root.showDisk
                percentage: root.diskRatio
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                shown: root.showSwap
                percentage: root.swapRatio
                Layout.leftMargin: shown ? 6 : 0
                warningThreshold: Config.options.bar.m3.resources.swapWarningThreshold
            }
        }
    }

    colDefault: Component {
        ColumnLayout {
            spacing: 7
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                vertical: true
                visible: root.showRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                vertical: true
                visible: root.showCpu
                percentage: root.cpuRatio
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                vertical: true
                visible: root.showCpuTemp
                percentage: root.cpuTemperature / 100
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                vertical: true
                visible: root.showDisk
                percentage: root.diskRatio
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                vertical: true
                visible: root.showSwap
                percentage: root.swapRatio
                warningThreshold: Config.options.bar.m3.resources.swapWarningThreshold
            }
        }
    }

    colMaterial: Component {
        ColumnLayout {
            spacing: 7
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                vertical: true
                visible: root.showRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                vertical: true
                visible: root.showCpu
                percentage: root.cpuRatio
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                vertical: true
                visible: root.showCpuTemp
                percentage: root.cpuTemperature / 100
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                vertical: true
                visible: root.showDisk
                percentage: root.diskRatio
            }
            Resource {
                contentColor: root.contentColor
                contentColorOverridden: root.contentColorOverridden
                iconStyle: root.iconStyle
                showValue: root.showValue
                Layout.alignment: Qt.AlignHCenter
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                vertical: true
                visible: root.showSwap
                percentage: root.swapRatio
                warningThreshold: Config.options.bar.m3.resources.swapWarningThreshold
            }
        }
    }

    ResourcesPopup {
        id: resourcesPopup
        hoverTarget: root
        hoverActivates: !root.clickForDetails
        closeOnOutsideClick: root.clickForDetails
        onRequestClose: active = false
    }
}
