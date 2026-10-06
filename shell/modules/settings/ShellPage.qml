import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

// Shell control plane (R11): a user-understandable, actionable view of what
// the shell runs, what it is missing, and how to turn it off. Every row binds
// straight to its owning service — the page mirrors no state. Monitoring has
// a real lifecycle: mounting this page arms the sampler only when the user
// opted in, and unmounting disarms it unconditionally.
StyledFlickable {
    id: root

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

    Component.onCompleted: ShellControlService.setPageMounted(true)
    Component.onDestruction: ShellControlService.setPageMounted(false)

    component StateLabel: Text {
        color: Appearance.colors.colOnSurfaceVariant
        font.family: Typography.bodyMedium.family
        font.pixelSize: Typography.bodyMedium.pixelSize
    }

    component PathOpenButton: IconButton {
        iconName: "open_in_new"
        tooltipText: I18n.tr("Open folder")
        accessibleName: I18n.tr("Open folder")
        onClicked: ApplicationService.openUrl("file://" + folderPath)

        property string folderPath: ""
    }

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingL

        SettingsSection {
            id: modulesSection

            Layout.fillWidth: true
            flat: true
            title: modulesAnchor.title
            iconName: "widgets"

            SettingsSearchAnchor {
                id: modulesAnchor

                target: modulesSection
                declaration:
                    '{"id":"shell.section.modules","route":"shell","title":"Modules & dependencies","context":"ShellPage","icon":"widgets","aliases":["control-plane","modules","dependencies","degraded","errors"]}'
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Startup stage")
                iconName: "rocket_launch"
                supportingText: ShellStartupService.currentStage === ShellStartupService.stageFailed
                                ? ShellStartupService.failureReason : ShellStartupService.currentStage
                                  + " · " + (Math.max(0, Date.now() - ShellStartupService.initTimestampMs)
                                             / 1000).toFixed(1) + "s"
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Niri integration")
                iconName: "hub"
                supportingText: !NiriService.isNiri ? I18n.tr("Niri session not detected") :
                                                      NiriService.connected ? I18n.tr("Connected") :
                                                                              NiriService.reconnecting
                                                                              ? I18n.tr("Reconnecting") :
                                                                                I18n.tr("Disconnected")

                trailing: IconButton {
                    visible: NiriService.isNiri && !NiriService.connected
                    iconName: "restart_alt"
                    tooltipText: I18n.tr("Reconnect")
                    accessibleName: I18n.tr("Reconnect")
                    onClicked: NiriService.reconnect()
                }
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: NiriService.configLoadFailed && NiriService.configError.length > 0
                tone: "error"
                message: NiriService.configError
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Status bar")
                iconName: "dock_to_bottom"

                trailing: StyledSwitch {
                    checked: PersonalizationConfig.barEnabled
                    Accessible.name: I18n.tr("Status bar")
                    onToggled: PersonalizationConfig.setValue("barEnabled", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Dock")
                iconName: "dock_to_bottom"

                trailing: StyledSwitch {
                    checked: DockService.enabled
                    Accessible.name: I18n.tr("Dock")
                    onToggled: DockService.setOption("enabled", checked)
                }
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: DockService.configError.length > 0
                tone: "error"
                message: DockService.configError
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Keystone")
                iconName: "toggle_off"

                trailing: StyledSwitch {
                    checked: PersonalizationConfig.keystoneEnabled
                    Accessible.name: I18n.tr("Keystone")
                    onToggled: PersonalizationConfig.setValue("keystoneEnabled", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Overview wallpaper")
                iconName: "wallpaper"

                trailing: StyledSwitch {
                    checked: PersonalizationConfig.overviewEnabled
                    Accessible.name: I18n.tr("Overview wallpaper")
                    onToggled: PersonalizationConfig.setOverviewEnabled(checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Network")
                iconName: "wifi"
                supportingText: NetworkService.available ? I18n.tr("Available") : I18n.tr(
                                                               "NetworkManager backend unavailable")
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Bluetooth")
                iconName: "bluetooth"
                supportingText: BluetoothService.available ? I18n.tr("Available") : I18n.tr(
                                                                 "No Bluetooth adapter detected")
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Clipboard history")
                iconName: "content_paste"
                supportingText: {
                    const deps = ClipboardService.dependencies || ({});
                    const mark = value => value === true ? "✓" : "✗";
                    return "cliphist " + mark(deps.cliphist) + " · wl-copy " + mark(deps.wlCopy)
                            + " · wl-paste " + mark(deps.wlPaste);
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Color picker")
                iconName: "colorize"
                supportingText: !ColorPickerService.probeFinished ? I18n.tr("Checking…") :
                                                                    ColorPickerService.available
                                                                    ? "hyprpicker ✓" : I18n.tr(
                                                                          "hyprpicker is missing")
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("System monitor")
                iconName: "monitoring"
                supportingText: SystemMonitorService.statusText

                trailing: IconButton {
                    visible: SystemMonitorService.error || SystemMonitorService.stale
                    iconName: "restart_alt"
                    tooltipText: I18n.tr("Retry")
                    accessibleName: I18n.tr("Retry")
                    onClicked: SystemMonitorService.retry()
                }
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: SystemMonitorService.error && SystemMonitorService.errorDetails.length > 0
                tone: "error"
                message: SystemMonitorService.errorDetails
            }

            Text {
                Layout.fillWidth: true
                text: I18n.tr(
                          "notify-send availability cannot be probed; a missing notification daemon degrades at the environment level.")
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Typography.bodySmall.family
                font.pixelSize: Typography.bodySmall.pixelSize
                wrapMode: Text.Wrap
            }
        }

        SettingsSection {
            id: samplingSection

            Layout.fillWidth: true
            flat: true
            title: samplingAnchor.title
            iconName: "speed"

            SettingsSearchAnchor {
                id: samplingAnchor

                target: samplingSection
                declaration:
                    '{"id":"shell.section.sampling","route":"shell","title":"Resource sampling","context":"ShellPage","icon":"speed","aliases":["sampling","cpu","memory","resource","rss"]}'
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Show resource usage")
                supportingText: I18n.tr(
                                    "Numbers describe this shell process only. Sampling runs solely while this page is open and the switch is on; closing the page leaves no timer behind.")

                trailing: StyledSwitch {
                    checked: UiPreferences.controlPlaneResourceSampling
                    Accessible.name: I18n.tr("Show resource usage")
                    onToggled: UiPreferences.setControlPlaneResourceSampling(checked)
                }
            }

            Grid {
                Layout.fillWidth: true
                visible: ShellControlService.samplingActive
                columns: 2
                columnSpacing: Metrics.spacingL
                rowSpacing: Metrics.spacingS

                SampleLabel {
                    text: I18n.tr("CPU")
                }
                SampleValue {
                    text: ShellControlService.cpuPercent >= 0 ? ShellControlService.cpuPercent.toFixed(1)
                                                                + "%" : "—"
                }
                SampleLabel {
                    text: I18n.tr("Memory (RSS)")
                }
                SampleValue {
                    text: ShellControlService.rssKb >= 0 ? (ShellControlService.rssKb / 1024).toFixed(1) + " MB" :
                                                           "—"
                }
                SampleLabel {
                    text: I18n.tr("Source")
                }
                SampleValue {
                    text: ShellControlService.samplingSource
                }
                SampleLabel {
                    text: I18n.tr("Updated")
                }
                SampleValue {
                    text: ShellControlService.lastSampleMs > 0 ? Qt.formatDateTime(new Date(
                                                                                       ShellControlService.lastSampleMs),
                                                                                   "hh:mm:ss") : "—"
                }
            }
        }

        SettingsSection {
            id: diagnosticsSection

            Layout.fillWidth: true
            flat: true
            title: diagnosticsAnchor.title
            iconName: "bug_report"

            SettingsSearchAnchor {
                id: diagnosticsAnchor

                target: diagnosticsSection
                declaration:
                    '{"id":"shell.section.diagnostics","route":"shell","title":"Diagnostics & paths","context":"ShellPage","icon":"bug_report","aliases":["diagnostics","export","paths","config folder","cache"]}'
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Configuration")
                supportingText: Paths.configHome

                trailing: PathOpenButton {
                    folderPath: Paths.configHome
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Data")
                supportingText: Paths.dataHome

                trailing: PathOpenButton {
                    folderPath: Paths.dataHome
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("State")
                supportingText: Paths.stateHome

                trailing: PathOpenButton {
                    folderPath: Paths.stateHome
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Cache")
                supportingText: Paths.cacheHome

                trailing: PathOpenButton {
                    folderPath: Paths.cacheHome
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Diagnostics")
                supportingText: ShellControlService.diagnosticsDir

                trailing: PathOpenButton {
                    folderPath: ShellControlService.diagnosticsDir
                }
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "download"
                text: I18n.tr("Export sanitized diagnostics")
                description: I18n.tr(
                                 "Writes a filtered JSON file to the cache directory; no environment variables or configuration contents are included.")
                onClicked: ShellControlService.exportDiagnostics()
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: ShellControlService.lastExportError.length > 0
                         || ShellControlService.lastExportPath.length > 0
                tone: ShellControlService.lastExportError.length > 0 ? "error" : "info"
                message: ShellControlService.lastExportError.length > 0 ? ShellControlService.lastExportError :
                                                                          I18n.tr("Diagnostics exported")
                                                                          + ": " + ShellControlService.lastExportPath
            }
        }
    }

    component SampleLabel: Text {
        color: Appearance.colors.colOnSurfaceVariant
        font.family: Typography.bodyMedium.family
        font.pixelSize: Typography.bodyMedium.pixelSize
    }

    component SampleValue: Text {
        color: Appearance.colors.colOnSurface
        font.family: Typography.bodyMedium.family
        font.pixelSize: Typography.bodyMedium.pixelSize
    }
}
