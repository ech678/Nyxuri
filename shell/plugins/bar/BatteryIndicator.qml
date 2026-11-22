import qs.services
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

MouseArea {
    id: root
    property color contentColor: Appearance.colors.colOnSecondaryContainer
    property bool contentColorOverridden: false
    property bool vertical: false
    property bool isMaterial: PersonalizationConfig.barIsMaterial
    // D4b entry axes: the percent readout and the wattage line (energyRate
    // from UPower) plus L/M/R click actions.
    property var widgetEntry: null
    readonly property bool showPercent: BarWidgetDefaults.option("battery", root.widgetEntry, "showPercent")
    readonly property bool showPower: BarWidgetDefaults.option("battery", root.widgetEntry, "showPower")
    readonly property var chargeState: Battery.chargeState
    readonly property bool isCharging: Battery.isCharging
    readonly property bool isPluggedIn: Battery.isPluggedIn
    readonly property real percentage: Battery.percentage
    readonly property bool isLow: percentage <= Config.options.battery.low / 100
    // Wattage line: UPower energyRate (W) while a cable is attached.
    readonly property string powerText: root.isPluggedIn ? Math.round(Battery.energyRate) + " W" : ""
    readonly property string displayText: (root.vertical && root.percentage > 99) || !root.showPercent ? "" : batteryProgress.text

    visible: Battery.available

    implicitWidth: !Battery.available ? 0 : vertical ? Appearance.sizes.verticalBarWidth : batteryProgress.valueBarWidth + 8 + (powerLabel.visible ? powerLabel.implicitWidth + 4 : 0)
    implicitHeight: !Battery.available ? 0 : vertical ? batteryProgress.valueBarWidth + 8 : Appearance.sizes.barHeight

    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    readonly property bool clickForDetails: !root.barAxes.hoverPopouts
    hoverEnabled: !root.clickForDetails

    // D4b click axes: a consumed dispatch ends here; "default"/"none" fall
    // through to the built-in popup behavior.
    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
    onClicked: mouse => {
        if (BarWidgetActions.dispatchMouse("battery", root.widgetEntry, mouse.button))
            mouse.accepted = true;
        else if (mouse.button === Qt.LeftButton && root.clickForDetails)
            batteryPopup.active = !batteryPopup.active;
    }

    ClippedProgressBar {
        id: batteryProgress
        anchors.centerIn: parent
        // With the wattage line attached, the pill+label group stays
        // optically centered (offset half the extra width).
        anchors.horizontalCenterOffset: powerLabel.visible ? -(powerLabel.implicitWidth + 4) / 2 : 0
        value: percentage
        rotation: root.vertical ? -90 : 0
        highlightColor: (isLow && !isCharging) ? M3Palette.error : (root.contentColorOverridden ? root.contentColor : M3Palette.pillInk("batteryIndicator"))
        Item {
            anchors.centerIn: parent
            width: batteryProgress.valueBarWidth
            height: batteryProgress.valueBarHeight
            // Horizontal
            Loader {
                id: rowLoader
                active: !root.vertical
                visible: active
                anchors.centerIn: parent
                sourceComponent: RowLayout {
                    spacing: 0
                    MaterialSymbol {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.topMargin: 2
                        Layout.leftMargin: -2
                        Layout.rightMargin: -2
                        fill: 1
                        text: "bolt"
                        iconSize: NexusStyle.font.bodySmall * BarScale.font
                        visible: root.isCharging && root.percentage < 1
                    }
                    StyledText {
                        Layout.alignment: Qt.AlignVCenter
                        Layout.topMargin: 2
                        font: batteryProgress.font
                        text: batteryProgress.text
                    }
                }
            }
            // Vertical
            Loader {
                id: colLoader
                active: root.vertical
                visible: active
                anchors.centerIn: parent
                sourceComponent: ColumnLayout {
                    rotation: 90
                    spacing: -7
                    MaterialSymbol {
                        Layout.alignment: Qt.AlignHCenter
                        fill: 1
                        text: "bolt"
                        Layout.topMargin: 4
                        iconSize: NexusStyle.font.bodySmall * BarScale.font
                        visible: root.isCharging && root.percentage < 1
                    }
                    StyledText {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: root.isCharging ? 2 : 4
                        font: batteryProgress.font
                        text: root.percentage * 100
                        visible: root.percentage < 1
                    }
                }
            }
        }
    }

    BatteryPopup {
        id: batteryPopup
        widgetBar: root.widgetBar
        hoverTarget: root
        hoverActivates: !root.clickForDetails
        closeOnOutsideClick: root.clickForDetails
        onRequestClose: active = false
    }

    // D4b showPower: the wattage line rides beside the pill while a cable
    // is attached (UPower energyRate).
    StyledText {
        id: powerLabel

        visible: !root.vertical && root.showPower && root.isPluggedIn && root.powerText !== ""
        anchors.left: batteryProgress.right
        anchors.leftMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        text: root.powerText
        color: root.contentColorOverridden ? root.contentColor : Appearance.colors.colOnLayer1
        font.pixelSize: NexusStyle.font.bodySmall * BarScale.font
        font.features: ({
            "tnum": 1
        })
    }
}
