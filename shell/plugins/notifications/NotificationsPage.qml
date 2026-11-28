import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

NexusPageBase {
    id: root

    title: SpotlightCatalog.title("notifications")

    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    readonly property var positionOptions: [
        {
            "label": I18n.tr("Top right"),
            "value": "top-right"
        },
        {
            "label": I18n.tr("Top left"),
            "value": "top-left"
        },
        {
            "label": I18n.tr("Top center"),
            "value": "top-center"
        },
        {
            "label": I18n.tr("Bottom right"),
            "value": "bottom-right"
        },
        {
            "label": I18n.tr("Bottom left"),
            "value": "bottom-left"
        },
        {
            "label": I18n.tr("Bottom center"),
            "value": "bottom-center"
        }
    ]

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        PreferenceHeader {
            first: true
            text: I18n.tr("Popups")
        }

        PreferenceSelect {
            id: posSelect

            first: true
            label: I18n.tr("Screen position")
            model: root.positionOptions
            currentValue: PersonalizationConfig.notificationPosition
            inputRegionService: PopupInputRegionService
            modified: PersonalizationConfig.notificationPosition !== "top-right"
            onSelected: value => PersonalizationConfig.setNotificationPosition(String(value))
            onResetRequested: PersonalizationConfig.setNotificationPosition("top-right")

            SettingsSearchAnchor {
                target: posSelect
                anchorId: "notifications.section.popups"
            }
        }

        PreferenceSlider {
            label: I18n.tr("Popup width")
            valueLabel: Math.round(PersonalizationConfig.notificationWidth) + " px"
            value: PersonalizationConfig.notificationWidth
            from: 280
            to: 560
            stepSize: 10
            modified: PersonalizationConfig.notificationWidth !== 380
            onMoved: value => PersonalizationConfig.setNotificationWidth(Math.round(value))
            onResetRequested: PersonalizationConfig.setNotificationWidth(380)
        }

        PreferenceSlider {
            label: I18n.tr("Popup timeout")
            valueLabel: Math.round(PersonalizationConfig.notificationTimeoutMs / 1000) + " s"
            value: Math.round(PersonalizationConfig.notificationTimeoutMs / 1000)
            from: 1
            to: 30
            stepSize: 1
            modified: PersonalizationConfig.notificationTimeoutMs !== 5000
            onMoved: value => PersonalizationConfig.setNotificationTimeoutMs(Math.round(value) * 1000)
            onResetRequested: PersonalizationConfig.setNotificationTimeoutMs(5000)
        }

        PreferenceToggle {
            last: PersonalizationConfig.notificationOpacity < 0
            text: I18n.tr("Follow theme opacity")
            checked: PersonalizationConfig.notificationOpacity < 0
            modified: PersonalizationConfig.notificationOpacity >= 0
            onToggled: checked => PersonalizationConfig.setNotificationOpacity(checked ? -1 : PersonalizationConfig.shellBackgroundOpacity)
            onResetRequested: PersonalizationConfig.setNotificationOpacity(-1)
        }

        PreferenceSlider {
            visible: PersonalizationConfig.notificationOpacity >= 0
            last: true
            label: I18n.tr("Popup opacity")
            valueLabel: Math.round(Math.max(0, PersonalizationConfig.notificationOpacity) * 100) + " %"
            value: Math.round(Math.max(0, PersonalizationConfig.notificationOpacity) * 100)
            from: 0
            to: 100
            stepSize: 5
            modified: PersonalizationConfig.notificationOpacity >= 0
            onMoved: value => PersonalizationConfig.setNotificationOpacity(Math.round(value) / 100)
            onResetRequested: PersonalizationConfig.setNotificationOpacity(-1)
        }
    }
}
