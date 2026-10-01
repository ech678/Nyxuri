import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Common
import qs.Services

Dialog {
    id: root

    // Material 3 Basic Dialog owns its title and message instead of relying
    // on the platform Dialog header. This keeps the visual hierarchy to one
    // title and makes the component independent of Qt Material styling.
    property string dialogTitle: ""
    property string messageText: ""
    property Component contentComponent
    property Component actionsComponent
    property Item initialFocusItem
    property real contentPadding: Metrics.spacingXL
    property real contentSpacing: Metrics.spacingM
    readonly property alias blurRegionItem: dialogSurface.blurRegionItem

    implicitWidth: 380
    implicitHeight: contentFrame.implicitHeight
    width: implicitWidth
    height: implicitHeight
    padding: 0
    modal: true
    dim: false
    focus: true
    closePolicy: Popup.CloseOnEscape
    Overlay.modal: Rectangle {
        color: "transparent"
    }

    background: Item {
        id: dialogSurface

        anchors.fill: parent

        readonly property alias blurRegionItem: surfaceFill

        Rectangle {
            id: surfaceFill

            anchors.fill: parent
            visible: root.visible
            radius: Appearance.rounding.extraLarge
            color: BlurService.backgroundColor(
                Appearance.m3colors.m3surfaceContainerHigh)
            antialiasing: true
        }
    }

    contentItem: Item {
        id: contentFrame

        implicitWidth: root.implicitWidth
        implicitHeight: contentColumn.implicitHeight
            + root.contentPadding * 2

        ColumnLayout {
            id: contentColumn

            anchors.fill: parent
            anchors.margins: root.contentPadding
            spacing: root.contentSpacing

            Text {
                Layout.fillWidth: true
                visible: root.dialogTitle.length > 0
                text: root.dialogTitle
                color: Appearance.colors.colOnSurface
                font.family: Typography.headlineSmall.family
                font.pixelSize: Typography.headlineSmall.pixelSize
                font.weight: Typography.headlineSmall.weight
                wrapMode: Text.Wrap
            }

            Text {
                Layout.fillWidth: true
                visible: root.messageText.length > 0
                text: root.messageText
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Typography.bodyMedium.family
                font.pixelSize: Typography.bodyMedium.pixelSize
                font.weight: Typography.bodyMedium.weight
                wrapMode: Text.Wrap
            }

            Loader {
                id: contentLoader

                Layout.fillWidth: true
                visible: root.contentComponent !== null
                active: root.contentComponent !== null
                sourceComponent: root.contentComponent
                Layout.preferredHeight: item ? item.implicitHeight : 0
            }

            Loader {
                id: actionsLoader

                Layout.fillWidth: true
                visible: root.actionsComponent !== null
                active: root.actionsComponent !== null
                sourceComponent: root.actionsComponent
                Layout.preferredHeight: item ? item.implicitHeight : 0
            }
        }
    }

    onOpened: {
        if (root.initialFocusItem)
            root.initialFocusItem.forceActiveFocus();
    }
}
