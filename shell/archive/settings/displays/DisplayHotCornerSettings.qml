import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

ColumnLayout {
    id: root

    readonly property var nativeCornerStatus: NiriConfigService.snapshot.hotCorners || ({})
    readonly property var outputConflicts: nativeCornerStatus.outputConflicts || []
    readonly property var cornerOptions: [
        {
            value: "top-left",
            label: I18n.tr("Top left", "HotCornersPage")
        },
        {
            value: "top-right",
            label: I18n.tr("Top right", "HotCornersPage")
        },
        {
            value: "bottom-left",
            label: I18n.tr("Bottom left", "HotCornersPage")
        },
        {
            value: "bottom-right",
            label: I18n.tr("Bottom right", "HotCornersPage")
        }
    ]
    readonly property var actionOptions: [
        {
            value: "disabled",
            label: I18n.tr("Disabled", "HotCornersPage")
        },
        {
            value: "overview",
            label: I18n.tr("Niri Overview", "HotCornersPage")
        },
        {
            value: "dashboard:info",
            label: I18n.tr("Information", "HotCornersPage")
        },
        {
            value: "dashboard:drawer",
            label: I18n.tr("Drawer", "HotCornersPage")
        },
        {
            value: "dashboard:weather",
            label: I18n.tr("Weather", "HotCornersPage")
        },
        {
            value: "quicksettings:settings",
            label: I18n.tr("Quick settings", "HotCornersPage")
        },
        {
            value: "quicksettings:network",
            label: I18n.tr("Network", "HotCornersPage")
        },
        {
            value: "quicksettings:bluetooth",
            label: I18n.tr("Bluetooth", "HotCornersPage")
        },
        {
            value: "quicksettings:audio",
            label: I18n.tr("Audio output", "HotCornersPage")
        },
        {
            value: "quicksettings:microphone",
            label: I18n.tr("Microphone", "HotCornersPage")
        },
        {
            value: "quicksettings:idle",
            label: I18n.tr("Idle management", "HotCornersPage")
        },
        {
            value: "quicksettings:night",
            label: I18n.tr("Night light", "HotCornersPage")
        }
    ]

    spacing: Metrics.spacingL

    NiriSetupPrompt {
        Layout.fillWidth: true
        title: I18n.tr("Hot corners", "HotCornersPage")
        description: I18n.tr("Let Nyxuri manage corner actions instead of the compositor's overview gesture.",
                             "HotCornersPage")
        integrationState: NiriConfigService.state("hot-corners")
        busy: NiriConfigService.busy
        blocked: root.outputConflicts.length > 0
        error: NiriConfigService.errorFeature === "hot-corners" ? NiriConfigService.error :
                                                                  NiriConfigService.configurationMessage
        onSetupRequested: NiriConfigService.setup("hot-corners")
    }

    Repeater {
        model: root.outputConflicts

        InlineStatusBanner {
            required property var modelData

            Layout.fillWidth: true
            tone: "warning"
            message: I18n.tr("Disable the compositor's hot corners for %1 in %2.", "HotCornersPage").arg(
                         modelData.identifier).arg(modelData.source)
        }
    }

    InlineStatusBanner {
        Layout.fillWidth: true
        visible: NiriConfigService.state("hot-corners") === "conflict" && root.outputConflicts.length === 0
        tone: "warning"
        message: I18n.tr("Another compositor configuration enables hot corners: %1", "HotCornersPage").arg(
                     root.nativeCornerStatus.globalSource || "")
    }

    SettingsSection {
        id: cornerSection

        Layout.fillWidth: true
        title: I18n.tr("Hot corners", "HotCornersPage")
        supportingText: I18n.tr("Actions apply to all displays.")
        iconName: "open_in_full"
        enabled: NiriConfigService.ready("hot-corners")

        Repeater {
            model: root.cornerOptions

            DisplayChoice {
                required property var modelData

                Layout.fillWidth: true
                title: modelData.label
                options: root.actionOptions
                value: PersonalizationConfig.hotCornerActions[modelData.value]
                onSelected: value => PersonalizationConfig.setHotCornerAction(modelData.value, value)
            }
        }
    }

    InlineStatusBanner {
        Layout.fillWidth: true
        visible: NiriConfigService.ready("hot-corners") && NiriConfigService.errorFeature === "hot-corners"
                 && NiriConfigService.error !== ""
        tone: "error"
        message: NiriConfigService.error
    }
}
