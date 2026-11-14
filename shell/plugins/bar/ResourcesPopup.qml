import qs.services
import QtQuick
import Quickshell.Io
import qs.commons
import qs.ui

StyledPopup {
    id: root
    readonly property var memorySnapshot: SystemMonitorService.memory || ({})
    readonly property var cpuSnapshot: SystemMonitorService.cpu || ({})
    readonly property var rootDisk: SystemMonitorService.disks.length > 0 ? SystemMonitorService.disks[0] : ({})

    property QtObject resourceMonitor: ResourceUsageMonitor {
        active: root.active
        ownerId: "shell.bar.resources-popup"
        modules: ["cpu", "memory", "disk"]
    }

    function formatBytes(bytes) {
        return (Number(bytes || 0) / (1024 * 1024 * 1024)).toFixed(1) + " GB"
    }

    Row {
        spacing: 5

        Column {
            spacing: 5

            ResourceCard {
                label: "RAM"
                iconText: "memory"
                iconShape: MaterialShapeCanvas.Shape.Clover4Leaf
                value: Number(root.memorySnapshot.usagePercent || 0) / 100
                available: root.memorySnapshot.usagePercent !== undefined
                sublabel: root.formatBytes(root.memorySnapshot.usedBytes) + " / " + root.formatBytes(root.memorySnapshot.totalBytes)
            }

            ResourceCard {
                label: "CPU"
                iconText: "planner_review"
                iconShape: MaterialShapeCanvas.Shape.Gem
                value: Number(root.cpuSnapshot.usagePercent || 0) / 100
                available: root.cpuSnapshot.usagePercent !== undefined
                sublabel: `${Math.round(Number(root.cpuSnapshot.packageTemperatureCelsius
                                            ?? root.cpuSnapshot.temperatureCelsius ?? 0))}°C`
                sublabelColor: Number(root.cpuSnapshot.packageTemperatureCelsius
                                      ?? root.cpuSnapshot.temperatureCelsius ?? 0) > 80 ? Appearance.colors.colError
                    : Number(root.cpuSnapshot.packageTemperatureCelsius
                             ?? root.cpuSnapshot.temperatureCelsius ?? 0) > 60 ? Appearance.m3colors.m3tertiary
                    : Appearance.colors.colOnLayer1
            }
        }

        Column {
            spacing: 5

            ResourceCard {
                label: "Swap"
                iconText: "swap_horiz"
                iconShape: MaterialShapeCanvas.Shape.Bun
                value: SystemMonitorService.swapTotalBytes > 0
                       ? SystemMonitorService.swapUsedBytes / SystemMonitorService.swapTotalBytes : 0
                available: root.memorySnapshot.totalBytes !== undefined
                sublabel: root.formatBytes(SystemMonitorService.swapUsedBytes) + " / "
                          + root.formatBytes(SystemMonitorService.swapTotalBytes)
            }

            ResourceCard {
                label: "Disk"
                iconText: "hard_drive"
                iconShape: MaterialShapeCanvas.Shape.Circle
                value: Number(root.rootDisk.usagePercent || 0) / 100
                available: root.rootDisk.usagePercent !== undefined
                sublabel: root.formatBytes(root.rootDisk.usedBytes) + " / " + root.formatBytes(root.rootDisk.totalBytes)
            }
        }
    }
}
