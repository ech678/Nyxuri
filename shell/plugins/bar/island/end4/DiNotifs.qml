// Fork & Trim: end4-pC modules/ii/bar/DiNotifs.qml (GPL-3, see shell/LICENSE
// appendix end-4-dots-hyprland-GPL-3.0.txt). Trimmed per the B volume four
// classes: upstream singletons -> tree services (ThemeService/TimeService/
// NotificationService), Appearance tokens, dead upstream paths dropped,
// click/right-click actions preserved to prevent functional regression.
import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.commons
import qs.ui

Item {
    id: diNotifsRoot
    required property Item di
    anchors.fill: parent

    readonly property var notif: di.latestNotification

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => {
            if (!diNotifsRoot.notif)
                return;
            if (mouse.button === Qt.RightButton) {
                NotificationService.dismissPopup(diNotifsRoot.notif.notificationId);
            } else {
                NotificationService.invokeDefaultAction(diNotifsRoot.notif.notificationId);
            }
        }
    }

    Item {
        id: iconWrapper
        width: 20
        height: 20
        anchors {
            left: parent.left
            leftMargin: di.isMaterial ? 4 : 8
            verticalCenter: parent.verticalCenter
        }

        Image {
            id: notifIcon
            anchors.fill: parent
            source: ThemeService.resolveIcon(diNotifsRoot.notif?.appIcon ?? "")
            visible: (diNotifsRoot.notif?.appIcon ?? "") !== "" && status !== Image.Error
            fillMode: Image.PreserveAspectFit
            asynchronous: true
        }

        MaterialShapeWrappedMaterialSymbol {
            id: notifMaterialIcon
            anchors.fill: parent
            wrappedShape: MaterialShapeCanvas.Shape.Cookie12Sided
            color: Appearance.colors.colPrimary
            colSymbol: Appearance.colors.colOnPrimary
            text: "notifications"
            iconSize: di.isMaterial ? 20 : 14
            fill: 1
            padding: 2
            visible: !notifIcon.visible
        }
    }

    ColumnLayout {
        id: notifTextColumn
        anchors {
            left: iconWrapper.right
            leftMargin: di.isMaterial ? 10 : 8
            verticalCenter: parent.verticalCenter
            right: nowLabel.left
            rightMargin: 8
        }
        spacing: di.isMaterial ? -2 : -4

        StyledText {
            Layout.fillWidth: true
            text: (diNotifsRoot.notif?.summary ?? "").replace(/\n/g, " ")
            font.pixelSize: Appearance.font.pixelSize.smaller
            font.weight: Font.DemiBold
            color: Appearance.colors.colOnLayer0
            elide: Text.ElideRight
            wrapMode: Text.NoWrap
            maximumLineCount: 1
        }
        StyledText {
            Layout.fillWidth: true
            text: (diNotifsRoot.notif?.body ?? "").replace(/\n/g, " ")
            font.pixelSize: Appearance.font.pixelSize.smallest
            color: Appearance.colors.colOnLayer0
            opacity: 0.7
            elide: Text.ElideRight
            wrapMode: Text.NoWrap
            maximumLineCount: 1
        }
    }

    StyledText {
        id: nowLabel
        anchors {
            right: parent.right
            top: parent.top
            rightMargin: 10
            topMargin: 8
        }
        text: TimeService.hours + ":" + TimeService.minutes
        font.pixelSize: Appearance.font.pixelSize.small - 2
        color: Appearance.colors.colOnLayer0
        opacity: 0.8
    }
}
