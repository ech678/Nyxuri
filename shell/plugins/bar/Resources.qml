import qs.services
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

BarWidgetSwitcherArea {
    id: root
    property bool alwaysShowAllResources: false
    horizontalExtraPadding: 12

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
            resourcesPopup.active = !resourcesPopup.active
    }

    rowDefault: Component {
        RowLayout {
            spacing: 0
            Resource {
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowCpu
                percentage: root.cpuRatio
                Layout.leftMargin: shown ? 6 : 0
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowCpuTemp
                percentage: root.cpuTemperature / 100
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowDisk
                percentage: root.diskRatio
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowSwap
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
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowCpu
                percentage: root.cpuRatio
                Layout.leftMargin: shown ? 6 : 0
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowCpuTemp
                percentage: root.cpuTemperature / 100
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowDisk
                percentage: root.diskRatio
                Layout.leftMargin: shown ? 6 : 0
            }
            Resource {
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                shown: Config.options.bar.m3.resources.alwaysShowSwap
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
                Layout.alignment: Qt.AlignHCenter
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowCpu
                percentage: root.cpuRatio
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowCpuTemp
                percentage: root.cpuTemperature / 100
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowDisk
                percentage: root.diskRatio
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowSwap
                percentage: root.swapRatio
                warningThreshold: Config.options.bar.m3.resources.swapWarningThreshold
            }
        }
    }

    colMaterial: Component {
        ColumnLayout {
            spacing: 7
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "memory"
                available: root.memorySnapshot.usagePercent !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowRam
                percentage: root.memoryRatio
                warningThreshold: Config.options.bar.m3.resources.memoryWarningThreshold
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "planner_review"
                available: root.cpuSnapshot.usagePercent !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowCpu
                percentage: root.cpuRatio
                warningThreshold: Config.options.bar.m3.resources.cpuWarningThreshold
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "thermostat"
                available: root.cpuSnapshot.packageTemperatureCelsius !== undefined || root.cpuSnapshot.temperatureCelsius !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowCpuTemp
                percentage: root.cpuTemperature / 100
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "hard_drive"
                available: root.rootDisk.usagePercent !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowDisk
                percentage: root.diskRatio
            }
            Resource {
                Layout.alignment: Qt.AlignHCenter
                iconName: "swap_horiz"
                available: root.memorySnapshot.totalBytes !== undefined
                vertical: true
                visible: Config.options.bar.m3.resources.alwaysShowSwap
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
