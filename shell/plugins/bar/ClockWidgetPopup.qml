import qs.services
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import M3Shapes

StyledPopup {
    id: root
    property var today: new Date()

    function usageColor(value) {
        if (value > 0.9)
            return Appearance.colors.colError;
        if (value > 0.6)
            return Appearance.m3colors.m3tertiary;
        return Appearance.colors.colPrimary;
    }

    ColumnLayout {
        id: popupColumn
        spacing: Appearance.sizes.spacingSmall
        implicitWidth: Math.max(390, Math.round(410 * Appearance.fontSizeScale))

        RowLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: popupColumn.implicitWidth
            spacing: 4

            Repeater {
                model: 7
                delegate: Rectangle {
                    required property int index

                    readonly property var date: {
                        const today = root.today;
                        const dow = today.getDay();
                        const d = new Date(today);
                        d.setDate(today.getDate() - dow + index);
                        return d;
                    }
                    readonly property bool isToday: {
                        const t = root.today;
                        return date.getDate() === t.getDate() && date.getMonth() === t.getMonth() && date.getFullYear() === t.getFullYear();
                    }

                    Layout.fillWidth: true
                    height: Math.max(58, Math.round(60 * Appearance.fontSizeScale))
                    radius: Appearance.rounding.normal
                    color: isToday ? Appearance.colors.colPrimaryContainer : Appearance.colors.colSurfaceContainerHigh

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        StyledText {
                            Layout.alignment: Qt.AlignHCenter
                            text: Qt.locale().toString(date, "ddd").slice(0, 2)
                            font.pixelSize: Appearance.font.pixelSize.smaller
                            color: isToday ? Appearance.colors.colPrimary : Appearance.colors.colOnSurfaceVariant
                            font.weight: isToday ? Font.Bold : Font.Normal
                        }

                        StyledText {
                            Layout.alignment: Qt.AlignHCenter
                            text: date.getDate()
                            font.pixelSize: isToday ? Appearance.font.pixelSize.normal : Appearance.font.pixelSize.small
                            font.weight: isToday ? Font.Bold : Font.Normal
                            color: isToday ? Appearance.colors.colPrimary : Appearance.colors.colOnLayer1
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(20, Appearance.font.pixelSize.small + 6)
            spacing: 6

            MaterialSymbol {
                text: "timelapse"
                iconSize: Appearance.font.pixelSize.small
                color: Appearance.colors.colOnSurfaceVariant
            }

            StyledText {
                Layout.fillWidth: true
                text: Translation.tr("System Uptime") + "  •  " + DateTime.uptime
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                font.pixelSize: Appearance.font.pixelSize.smaller
                color: Appearance.colors.colOnSurfaceVariant
            }
        }
    }
}
