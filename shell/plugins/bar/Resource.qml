import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services

Item {
    id: root
    property color contentColor: Appearance.colors.colOnSecondaryContainer
    property bool contentColorOverridden: false
    required property string iconName
    required property double percentage
    property bool vertical: false
    property bool available: true
    opacity: available ? 1 : 0.4
    property int warningThreshold: 100
    property bool shown: true
    // D4b: icon skin / percentage readout are entry axes injected by the
    // owning Resources widget (defaults mirror the entry defaults).
    property string iconStyle: "outline"
    property bool showValue: false
    readonly property color foregroundColor: root.contentColorOverridden ? root.contentColor : M3Palette.pillInk("resources")
    clip: !vertical
    visible: vertical ? true : width > 0 && height > 0
    implicitWidth: vertical ? Appearance.sizes.verticalBarWidth : (resourceRowLayout.x < 0 ? 0 : resourceRowLayout.implicitWidth)
    implicitHeight: vertical ? resourceProgress.implicitHeight : Appearance.sizes.barHeight
    property bool warning: percentage * 100 >= warningThreshold

    Component {
        id: outlineStyle
        ClippedOutlineCircularProgress {
            lineWidth: Appearance.rounding.unsharpen
            value: root.percentage
            implicitSize: 20
            colPrimary: root.warning ? Appearance.colors.colError : root.foregroundColor
            enableAnimation: false
            Item {
                anchors.centerIn: parent
                width: 20
                height: 20
                MaterialSymbol {
                    anchors.centerIn: parent
                    font.weight: Font.DemiBold
                    fill: 1
                    text: root.iconName
                    iconSize: NexusStyle.font.bodyLarge
                    color: root.foregroundColor
                }
            }
        }
    }

    Component {
        id: filledStyle
        ClippedFilledCircularProgress {
            lineWidth: Appearance.rounding.unsharpen
            value: root.percentage
            implicitSize: 20
            colPrimary: root.warning ? Appearance.colors.colError : root.foregroundColor
            accountForLightBleeding: !root.warning
            enableAnimation: false
            Item {
                anchors.centerIn: parent
                width: 20
                height: 20
                MaterialSymbol {
                    anchors.centerIn: parent
                    font.weight: vertical ? Font.Medium : Font.DemiBold
                    fill: 1
                    text: root.iconName
                    iconSize: NexusStyle.font.bodyLarge
                    color: root.foregroundColor
                }
            }
        }
    }

    Loader {
        id: resourceProgress
        active: root.vertical
        visible: active
        anchors.centerIn: parent
        sourceComponent: root.iconStyle === "filled" ? filledStyle : outlineStyle
    }

    RowLayout {
        id: resourceRowLayout
        visible: !root.vertical
        spacing: 2
        x: shown ? 0 : -resourceRowLayout.width
        anchors.verticalCenter: parent.verticalCenter

        Loader {
            Layout.alignment: Qt.AlignVCenter
            active: !root.vertical
            visible: active
            sourceComponent: root.iconStyle === "filled" ? filledStyle : outlineStyle
        }

        Item {
            Layout.alignment: Qt.AlignVCenter
            visible: root.showValue
            implicitWidth: visible ? fullPercentageTextMetrics.width : 0
            implicitHeight: percentageText.implicitHeight
            TextMetrics {
                id: fullPercentageTextMetrics
                text: "100"
                font.pixelSize: NexusStyle.font.bodyMedium
            }
            StyledText {
                id: percentageText
                anchors.centerIn: parent
                color: root.contentColorOverridden ? root.contentColor : Appearance.colors.colOnLayer1
                font.pixelSize: NexusStyle.font.bodyMedium
                text: root.available ? `${Math.round(root.percentage * 100).toString()}` : "—"
            }
        }

        Behavior on x {
            animation: Appearance.animation.elementMove.numberAnimation.createObject(this)
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        enabled: vertical ? root.visible : (resourceRowLayout.x >= 0 && root.width > 0 && root.visible)
    }

    Behavior on implicitWidth {
        enabled: false
    }
}
