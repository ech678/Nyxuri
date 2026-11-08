// Nyxuri Shell - Active Window Widget (M3 unified)
// GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.commons
import qs.commons.i18n
import qs.ui
import qs.services

Item {
    id: root

    property bool vertical: Config.options?.bar?.vertical ?? false
    readonly property bool isMaterial: (Config.options?.bar?.m3?.cornerStyle ?? 0) === 3
    readonly property var activeWindow: CompositorDriver.focusedWindow
    readonly property string activeTitle: activeWindow?.title || I18n.tr("Desktop")
    readonly property string activeIcon: activeWindow?.iconPath || ""
    readonly property string activeAppName: activeWindow?.appName || activeWindow?.appId || ""
    readonly property bool isDesktop: !activeWindow?.id

    implicitWidth: layout.implicitWidth
    implicitHeight: layout.implicitHeight

    RowLayout {
        id: layout
        anchors.centerIn: parent
        spacing: Appearance.sizes.spacingSmall

        Item {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            Layout.alignment: Qt.AlignVCenter
            visible: root.isDesktop || root.activeIcon !== "" || root.activeAppName !== ""

            Image {
                id: appIcon
                anchors.centerIn: parent
                width: 18
                height: 18
                source: root.activeIcon
                sourceSize.width: 36
                sourceSize.height: 36
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                smooth: true
                visible: root.activeIcon !== "" && status !== Image.Error
            }

            MaterialSymbol {
                anchors.fill: parent
                text: "desktop_windows"
                iconSize: 18
                color: root.isMaterial ? M3Palette.pillInk("activeWindow") : Appearance.colors.colPrimary
                visible: root.isDesktop
            }

            Text {
                anchors.centerIn: parent
                text: root.activeAppName.charAt(0).toUpperCase()
                color: root.isMaterial ? M3Palette.pillInk("activeWindow") : Appearance.colors.colPrimary
                font.pixelSize: 12
                font.bold: true
                visible: !root.isDesktop && !appIcon.visible
            }
        }

        Text {
            id: titleText
            Layout.alignment: Qt.AlignVCenter
            Layout.maximumWidth: 220
            text: root.activeTitle
            font.family: Appearance.font.main
            font.pixelSize: 12
            color: root.isMaterial ? M3Palette.pillInk("activeWindow") : Appearance.colors.colOnLayer0
            elide: Text.ElideRight
            visible: !root.vertical
        }
    }
}
