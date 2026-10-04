import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.i18n

Item {
    id: root

    property bool active: true
    property string message: I18n.tr("Connecting to the system monitor service")

    implicitHeight: 240

    ColumnLayout {
        anchors.centerIn: parent
        spacing: Appearance.spacing.medium

        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: root.active && root.visible
            Material.accent: Appearance.colors.colPrimary
            Accessible.name: root.message
        }

        Text {
            text: root.message
            color: Appearance.colors.colOnSurface
            font.family: Fonts.ui
            font.pixelSize: Typography.bodyLarge.pixelSize
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            text: I18n.tr("Live metrics appear after the first valid snapshot arrives")
            color: Appearance.colors.colOnSurfaceVariant
            font.family: Fonts.ui
            font.pixelSize: Typography.bodySmall.pixelSize
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
