import QtQuick
import QtQuick.Layouts
import Quickshell.Services.UPower
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import "../../../shared/utils/SystemFormat.js" as Format
import qs.shared.i18n

Item {
    id: root

    property bool vertical: false
    readonly property bool valueAvailable: PowerService.present && Format.isNumber(PowerService.percentage)
    readonly property real percentage: root.valueAvailable ? Math.max(0, Math.min(100, PowerService.percentage * 100)) : NaN
    readonly property bool lowBattery: root.valueAvailable && root.percentage <= 15 && PowerService.discharging

    readonly property string displayText: root.valueAvailable ? String(Math.round(root.percentage)) : "—"
    readonly property bool showValue: PersonalizationConfig.barShowValues
    readonly property color foregroundColor: root.lowBattery ? Appearance.colors.colError : Appearance.colors.colOnSurface

    readonly property string tooltipText: root.buildTooltip()

    function stateAndTimeText() {
        if (PowerService.full)
            return I18n.tr("Status: Fully charged");

        if (PowerService.charging)
            return Format.isNumber(PowerService.timeToFull) ? I18n.tr("Status: Charging · Full in ") + Format.duration(PowerService.timeToFull) : I18n.tr("Status: Charging · Time to full unknown");

        if (PowerService.discharging)
            return Format.isNumber(PowerService.timeToEmpty) ? I18n.tr("Status: Discharging · ") + Format.duration(PowerService.timeToEmpty) : I18n.tr("Status: Discharging · Remaining time unknown");

        if (PowerService.state === UPowerDeviceState.Empty)
            return I18n.tr("Status: Empty");

        if (PowerService.state === UPowerDeviceState.PendingCharge)
            return I18n.tr("Status: Pending charge");

        if (PowerService.state === UPowerDeviceState.PendingDischarge)
            return I18n.tr("Status: Pending discharge");

        return PowerService.powerConnected ? I18n.tr("Status: Plugged in, not charging") : I18n.tr("Status: Unknown");
    }

    function powerText() {
        const label = PowerService.charging ? I18n.tr("Live charging power: ") : PowerService.discharging ? I18n.tr("Live discharging power: ") : I18n.tr("Live power: ");
        return label + (Format.isNumber(PowerService.changeRate) ? Format.watts(Math.abs(PowerService.changeRate)) : I18n.tr("Unknown"));
    }

    function buildTooltip() {
        if (!PowerService.ready)
            return [I18n.tr("Detecting battery"), I18n.tr("UPower has not provided battery data yet"), I18n.tr("Plug status, power, and health are temporarily unavailable")].join("\n");

        if (!PowerService.present)
            return [I18n.tr("No battery detected"), I18n.tr("This device may not have a built-in battery"), I18n.tr("Plugged in: ") + (PowerService.powerConnected ? I18n.tr("Yes") : I18n.tr("No")), I18n.tr("Charge state, power, and health are unavailable")].join("\n");

        return [I18n.tr("Battery level: ") + Format.percent(root.percentage, 0), I18n.tr("Plugged in: ") + (PowerService.powerConnected ? I18n.tr("Yes") : I18n.tr("No")), root.stateAndTimeText(), root.powerText(), I18n.tr("Health: ") + (Format.isNumber(PowerService.healthPercentage) ? Format.percent(PowerService.healthPercentage, 0) : I18n.tr("Unknown"))].join("\n");
    }

    implicitWidth: root.vertical ? Math.max(28, batteryContent.implicitWidth) : batteryContent.implicitWidth + 8
    implicitHeight: root.vertical ? Math.max(Sizes.barControlCircleSize, batteryContent.implicitHeight) : Sizes.barControlCircleSize
    Accessible.name: root.tooltipText
    Accessible.role: Accessible.StaticText

    GridLayout {
        id: batteryContent
        anchors.centerIn: parent
        columns: root.vertical ? 1 : 2
        rowSpacing: 4
        columnSpacing: Sizes.barLabelSpacing
        MaterialSymbol {
            Layout.preferredWidth: Sizes.barControlCircleSize
            Layout.preferredHeight: Sizes.barControlCircleSize
            Layout.alignment: Qt.AlignCenter
            text: !root.valueAvailable ? "battery_android_question" : PowerService.charging ? "battery_android_bolt" : root.percentage >= 95 ? "battery_android_full" : "battery_android_" + Math.max(0, Math.min(6, Math.floor(root.percentage * 7 / 100)))
            iconSize: Sizes.barIconSize
            fill: 1
            color: root.foregroundColor
        }
        Text {
            Layout.alignment: Qt.AlignCenter
            visible: root.showValue
            text: root.valueAvailable ? root.displayText + "%" : root.displayText
            font.family: Fonts.numeric
            font.pixelSize: Appearance.scaledFont(12)
            color: root.foregroundColor
        }
    }

    MouseArea {
        id: hoverArea

        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    PopupToolTip {
        extraVisibleCondition: hoverArea.containsMouse
        text: root.tooltipText
    }
}
