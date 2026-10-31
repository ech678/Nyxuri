import QtQuick
import QtQuick.Layouts
import qs.app
import qs.commons
import qs.services
import qs.plugins.keystone.tools
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Shell control plane (T3 M4): NexusPageBase scaffold + M1 atom rows. Every
// row still binds straight to its owning service — the page mirrors no state.
// Monitoring keeps its real lifecycle: mounting this page arms the sampler
// only when the user opted in, unmounting disarms it unconditionally.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("shell")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    Component.onCompleted: ShellControlService.setPageMounted(true)
    Component.onDestruction: ShellControlService.setPageMounted(false)

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Modules & dependencies
        PreferenceHeader {
            first: true
            text: I18n.tr("Modules & dependencies", "ShellPage")
        }

        PreferenceInfo {
            id: startupRow

            first: true
            icon: "rocket_launch"
            label: I18n.tr("Startup stage")
            subtext: ShellStartupService.currentStage === ShellStartupService.stageFailed
                     ? ShellStartupService.failureReason : ShellStartupService.currentStage + " · " + (
                           Math.max(0, Date.now() - ShellStartupService.initTimestampMs) / 1000).toFixed(1)
                       + "s"

            SettingsSearchAnchor {
                id: modulesAnchor
                target: startupRow
                declaration:
                    '{"id":"shell.section.modules","route":"shell","title":"Modules & dependencies","context":"ShellPage","icon":"widgets","aliases":["control-plane","modules","dependencies","degraded","errors"]}'
            }
        }

        PreferenceAction {
            icon: "hub"
            text: I18n.tr("Niri integration")
            subtext: !NiriService.isNiri ? I18n.tr("Niri session not detected") : NiriService.connected
                                           ? I18n.tr("Connected") : NiriService.reconnecting ? I18n.tr(
                                                                                                   "Reconnecting") :
                                                                                               I18n.tr("Disconnected")
            trailingIcon: NiriService.isNiri && !NiriService.connected ? "restart_alt" : ""
            onClicked: {
                if (NiriService.isNiri && !NiriService.connected)
                    NiriService.reconnect();
            }
        }

        // The twelve Shell units, projected straight off the ledger
        // (unit-model.md §6). Flipping dispatches `nyxuri on/off shell.<domain>`
        // via UnitControlService; this page mirrors nothing.
        Repeater {
            model: UnitCatalog.units

            delegate: PreferenceToggle {
                id: unitToggle

                required property var modelData

                readonly property bool pending: UnitControlService.pendingUnitId === unitToggle.modelData.id

                text: I18n.tr(unitToggle.modelData.label)
                subtext: unitToggle.pending ? I18n.tr("Applying…") : ""
                checked: StateProjection.isEnabled(unitToggle.modelData.id)
                enabled: !unitToggle.pending && UnitControlService.canToggle(unitToggle.modelData.id)
                onToggled: UnitControlService.setUnit(unitToggle.modelData.id, checked)
            }
        }

        PreferenceToggle {
            text: I18n.tr("Overview wallpaper")
            checked: PersonalizationConfig.overviewEnabled
            onToggled: PersonalizationConfig.setOverviewEnabled(checked)
        }

        PreferenceInfo {
            icon: "wifi"
            label: I18n.tr("Network")
            subtext: NetworkService.available ? I18n.tr("Available") : I18n.tr(
                                                    "NetworkManager backend unavailable")
        }

        PreferenceInfo {
            icon: "bluetooth"
            label: I18n.tr("Bluetooth")
            subtext: BluetoothService.available ? I18n.tr("Available") : I18n.tr(
                                                      "No Bluetooth adapter detected")
        }

        PreferenceInfo {
            icon: "content_paste"
            label: I18n.tr("Clipboard history")
            subtext: {
                const deps = ClipboardService.dependencies || ({});
                const mark = value => value === true ? "✓" : "✗";
                return "cliphist " + mark(deps.cliphist) + " · wl-copy " + mark(deps.wlCopy) + " · wl-paste "
                        + mark(deps.wlPaste);
            }
        }

        PreferenceInfo {
            icon: "colorize"
            label: I18n.tr("Color picker")
            subtext: !ColorPickerService.probeFinished ? I18n.tr("Checking…") : ColorPickerService.available
                                                         ? "hyprpicker ✓" : I18n.tr("hyprpicker is missing")
        }

        PreferenceAction {
            last: true
            icon: "monitoring"
            text: I18n.tr("System monitor")
            subtext: SystemMonitorService.statusText
            trailingIcon: SystemMonitorService.error || SystemMonitorService.stale ? "restart_alt" : ""
            onClicked: {
                if (SystemMonitorService.error || SystemMonitorService.stale)
                    SystemMonitorService.retry();
            }
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: NiriService.configLoadFailed && NiriService.configError.length > 0
            tone: "error"
            message: NiriService.configError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DockService.configError.length > 0
            tone: "error"
            message: DockService.configError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: UnitControlService.lastError.length > 0
            tone: "error"
            message: UnitControlService.lastError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: StateProjection.degraded
            tone: "error"
            message: I18n.tr("The unit ledger is unreadable; every unit is shown as enabled.")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: SystemMonitorService.error && SystemMonitorService.errorDetails.length > 0
            tone: "error"
            message: SystemMonitorService.errorDetails
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: NexusStyle.padding.extraSmall
            Layout.rightMargin: NexusStyle.padding.extraSmall
            text: I18n.tr(
                      "notify-send availability cannot be probed; a missing notification daemon degrades at the environment level.")
            color: Appearance.m3colors.m3onSurfaceVariant
            font.pixelSize: NexusStyle.font.bodySmall
            wrapMode: Text.Wrap
        }

        // Session log
        PreferenceHeader {
            text: I18n.tr("Session log", "ShellPage")
        }

        ConnectedRect {
            id: logCard

            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: logColumn.implicitHeight + NexusStyle.padding.medium * 2

            ColumnLayout {
                id: logColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                StyledText {
                    Layout.fillWidth: true
                    text: I18n.tr(
                              "Last 40 entries of this session — theme generation, template renders and unit switches report here. The full log plus one previous session live under the state directory.")
                    color: Appearance.m3colors.m3onSurfaceVariant
                    font.pixelSize: NexusStyle.font.bodySmall
                    wrapMode: Text.Wrap
                }

                StyledText {
                    Layout.fillWidth: true
                    text: LogService.recentText(40)
                    color: Appearance.m3colors.m3onSurface
                    font.family: PersonalizationConfig.monoFontFamily
                    font.pixelSize: NexusStyle.font.bodySmall
                    wrapMode: Text.Wrap
                }

                StyledText {
                    Layout.fillWidth: true
                    text: I18n.tr("Log files: ") + LogService.logPath + "  ·  " + LogService.prevLogPath
                    color: Appearance.m3colors.m3onSurfaceVariant
                    font.family: PersonalizationConfig.monoFontFamily
                    font.pixelSize: NexusStyle.font.bodySmall
                    wrapMode: Text.Wrap
                }
            }

            SettingsSearchAnchor {
                id: logAnchor
                target: logCard
                declaration:
                    '{"id":"shell.section.log","route":"shell","title":"Session log","context":"ShellPage","icon":"receipt_long","aliases":["log","logs","debug","theme","取色"]}'
            }
        }

        // Resource sampling
        PreferenceHeader {
            text: I18n.tr("Resource sampling", "ShellPage")
        }

        PreferenceToggle {
            id: samplingToggle

            first: true
            last: !ShellControlService.samplingActive
            text: I18n.tr("Show resource usage")
            subtext: I18n.tr(
                         "Numbers describe this shell process only. Sampling runs solely while this page is open and the switch is on; closing the page leaves no timer behind.")
            checked: UiPreferences.controlPlaneResourceSampling
            onToggled: UiPreferences.setControlPlaneResourceSampling(checked)

            SettingsSearchAnchor {
                id: samplingAnchor
                target: samplingToggle
                declaration:
                    '{"id":"shell.section.sampling","route":"shell","title":"Resource sampling","context":"ShellPage","icon":"speed","aliases":["sampling","cpu","memory","resource","rss"]}'
            }
        }

        PreferenceInfo {
            visible: ShellControlService.samplingActive
            icon: "memory"
            label: I18n.tr("CPU")
            value: ShellControlService.cpuPercent >= 0 ? ShellControlService.cpuPercent.toFixed(1) + "%" : "—"
        }

        PreferenceInfo {
            visible: ShellControlService.samplingActive
            icon: "developer_board"
            label: I18n.tr("Memory (RSS)")
            value: ShellControlService.rssKb >= 0 ? (ShellControlService.rssKb / 1024).toFixed(1) + " MB" :
                                                    "—"

        }

        PreferenceInfo {
            visible: ShellControlService.samplingActive
            icon: "source"
            label: I18n.tr("Source")
            value: ShellControlService.samplingSource
        }

        PreferenceInfo {
            visible: ShellControlService.samplingActive
            last: true
            icon: "schedule"
            label: I18n.tr("Updated")
            value: ShellControlService.lastSampleMs > 0 ? Qt.formatDateTime(new Date(
                                                                                ShellControlService.lastSampleMs),
                                                                            "hh:mm:ss") : "—"
        }

        // Diagnostics & paths
        PreferenceHeader {
            text: I18n.tr("Diagnostics & paths", "ShellPage")
        }

        PreferenceAction {
            id: configPathRow

            icon: "folder"
            text: I18n.tr("Configuration")
            subtext: Paths.configHome
            trailingIcon: "open_in_new"
            onClicked: ApplicationService.openUrl(Paths.fileUrl(Paths.configHome))

            SettingsSearchAnchor {
                id: diagnosticsAnchor
                target: configPathRow
                declaration:
                    '{"id":"shell.section.diagnostics","route":"shell","title":"Diagnostics & paths","context":"ShellPage","icon":"bug_report","aliases":["diagnostics","export","paths","config folder","cache"]}'
            }
        }

        PreferenceAction {
            icon: "folder"
            text: I18n.tr("Data")
            subtext: Paths.dataHome
            trailingIcon: "open_in_new"
            onClicked: ApplicationService.openUrl(Paths.fileUrl(Paths.dataHome))
        }

        PreferenceAction {
            icon: "folder"
            text: I18n.tr("State")
            subtext: Paths.stateHome
            trailingIcon: "open_in_new"
            onClicked: ApplicationService.openUrl(Paths.fileUrl(Paths.stateHome))
        }

        PreferenceAction {
            icon: "folder"
            text: I18n.tr("Cache")
            subtext: Paths.cacheHome
            trailingIcon: "open_in_new"
            onClicked: ApplicationService.openUrl(Paths.fileUrl(Paths.cacheHome))
        }

        PreferenceAction {
            icon: "folder"
            text: I18n.tr("Diagnostics")
            subtext: ShellControlService.diagnosticsDir
            trailingIcon: "open_in_new"
            onClicked: ApplicationService.openUrl(Paths.fileUrl(ShellControlService.diagnosticsDir))
        }

        PreferenceAction {
            last: true
            icon: "download"
            text: I18n.tr("Export sanitized diagnostics")
            subtext: I18n.tr(
                         "Writes a filtered JSON file to the cache directory; no environment variables or configuration contents are included.")
            onClicked: ShellControlService.exportDiagnostics()
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: ShellControlService.lastExportError.length > 0
                     || ShellControlService.lastExportPath.length > 0
            tone: ShellControlService.lastExportError.length > 0 ? "error" : "info"
            message: ShellControlService.lastExportError.length > 0 ? ShellControlService.lastExportError :
                                                                      I18n.tr("Diagnostics exported") + ": "
                                                                      + ShellControlService.lastExportPath
        }
    }
}
