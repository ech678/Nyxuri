import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services

MouseArea {
    id: root

    property bool vertical: false
    property real downloadBytesPerSecond: SystemMonitorService.network?.downloadBytesPerSecond ?? 0
    property real uploadBytesPerSecond: SystemMonitorService.network?.uploadBytesPerSecond ?? 0
    property real downloadedBytes: SystemMonitorService.network?.receivedBytes ?? 0
    property real uploadedBytes: SystemMonitorService.network?.transmittedBytes ?? 0

    Component.onCompleted: {
        SystemMonitorService.setConsumerModules("bar-network-speed", ["network"]);
    }

    Component.onDestruction: {
        SystemMonitorService.clearConsumer("bar-network-speed");
    }

    implicitWidth: vertical ? 36 : speedColumn.implicitWidth + 8
    implicitHeight: vertical ? speedColumn.implicitHeight + 6 : 32

    readonly property bool clickForDetails: Config.options?.bar?.m3?.tooltips?.clickToShow ?? false
    hoverEnabled: true

    onClicked: mouse => {
        if (mouse.button === Qt.LeftButton && root.clickForDetails)
            networkPopup.active = !networkPopup.active
    }

    function formatRate(rate, compact) {
        const units = compact
            ? ["B", "K", "M", "G"]
            : ["B/s", "KB/s", "MB/s", "GB/s"]
        let value = Math.max(0, Number(rate) || 0)
        let unitIndex = 0

        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024
            unitIndex++
        }

        const precision = unitIndex > 0 && value < 100 ? 1 : 0
        return `${value.toFixed(precision)}${compact ? "" : " "}${units[unitIndex]}`
    }

    TextMetrics {
        id: regularRateMetrics
        text: "999.9 MB/s"
        font.pixelSize: Appearance.font.pixelSize.smallest
        font.weight: Font.Medium
    }

    component SpeedLine: RowLayout {
        id: speedLine

        required property string iconName
        required property real rate
        required property color accentColor

        readonly property string rateText: root.formatRate(rate, root.vertical)

        spacing: root.vertical ? 1 : 3

        MaterialSymbol {
            text: speedLine.iconName
            iconSize: root.vertical
                ? Appearance.font.pixelSize.smallest
                : Appearance.font.pixelSize.smaller
            color: speedLine.accentColor
            opacity: speedLine.rate > 0 ? 1 : 0.45

            Behavior on opacity {
                animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
            }
        }

        StyledText {
            Layout.preferredWidth: root.vertical ? -1 : regularRateMetrics.width
            horizontalAlignment: Text.AlignRight
            text: speedLine.rateText
            color: Appearance.colors.colOnLayer1
            font.pixelSize: Appearance.font.pixelSize.smallest
            font.weight: Font.Medium
            font.features: { "tnum": 1 }
        }
    }

    ColumnLayout {
        id: speedColumn
        anchors.centerIn: parent
        spacing: -3

        SpeedLine {
            iconName: "arrow_upward"
            rate: root.uploadBytesPerSecond
            accentColor: Appearance.colors.colTertiary
        }

        SpeedLine {
            iconName: "arrow_downward"
            rate: root.downloadBytesPerSecond
            accentColor: Appearance.colors.colPrimary
        }
    }

    NetworkSpeedPopup {
        id: networkPopup
        hoverTarget: root
        hoverActivates: !root.clickForDetails
        closeOnOutsideClick: root.clickForDetails
        onRequestClose: active = false
        downloadSpeed: root.downloadBytesPerSecond
        uploadSpeed: root.uploadBytesPerSecond
        downloadedBytes: root.downloadedBytes
        uploadedBytes: root.uploadedBytes
    }
}
