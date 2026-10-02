import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

ColumnLayout {
    id: root

    readonly property var nativeCornerStatus: NiriConfigService.snapshot.hotCorners || ({})
    readonly property var outputConflicts: nativeCornerStatus.outputConflicts || []
    readonly property var cornerOptions: [
        {
            value: "top-left",
            label: qsTranslate("HotCornersPage", "Top left")
        },
        {
            value: "top-right",
            label: qsTranslate("HotCornersPage", "Top right")
        },
        {
            value: "bottom-left",
            label: qsTranslate("HotCornersPage", "Bottom left")
        },
        {
            value: "bottom-right",
            label: qsTranslate("HotCornersPage", "Bottom right")
        }
    ]
    readonly property var actionOptions: [
        {
            value: "disabled",
            label: qsTranslate("HotCornersPage", "Disabled")
        },
        {
            value: "overview",
            label: qsTranslate("HotCornersPage", "Niri Overview")
        },
        {
            value: "dashboard:info",
            label: qsTranslate("HotCornersPage", "Information")
        },
        {
            value: "dashboard:drawer",
            label: qsTranslate("HotCornersPage", "Drawer")
        },
        {
            value: "dashboard:weather",
            label: qsTranslate("HotCornersPage", "Weather")
        },
        {
            value: "quicksettings:settings",
            label: qsTranslate("HotCornersPage", "Quick settings")
        },
        {
            value: "quicksettings:network",
            label: qsTranslate("HotCornersPage", "Network")
        },
        {
            value: "quicksettings:bluetooth",
            label: qsTranslate("HotCornersPage", "Bluetooth")
        },
        {
            value: "quicksettings:audio",
            label: qsTranslate("HotCornersPage", "Audio output")
        },
        {
            value: "quicksettings:microphone",
            label: qsTranslate("HotCornersPage", "Microphone")
        },
        {
            value: "quicksettings:idle",
            label: qsTranslate("HotCornersPage", "Idle management")
        },
        {
            value: "quicksettings:night",
            label: qsTranslate("HotCornersPage", "Night light")
        }
    ]

    spacing: Metrics.spacingL

    NiriSetupPrompt {
        Layout.fillWidth: true
        title: qsTranslate("HotCornersPage", "Hot corners")
        description: qsTranslate("HotCornersPage",
                                 "Let Clavis manage corner actions instead of the compositor's overview gesture.")
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
            message: qsTranslate("HotCornersPage", "Disable the compositor's hot corners for %1 in %2.").arg(
                         modelData.identifier).arg(modelData.source)
        }
    }

    InlineStatusBanner {
        Layout.fillWidth: true
        visible: NiriConfigService.state("hot-corners") === "conflict" && root.outputConflicts.length === 0
        tone: "warning"
        message: qsTranslate("HotCornersPage", "Another compositor configuration enables hot corners: %1").arg(
                     root.nativeCornerStatus.globalSource || "")
    }

    SettingsSection {
        id: cornerSection

        Layout.fillWidth: true
        title: qsTranslate("HotCornersPage", "Hot corners")
        supportingText: qsTr("Actions apply to all displays.")
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
