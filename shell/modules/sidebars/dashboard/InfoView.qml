import QtQuick
import QtQuick.Layouts
import qs.app.services
import qs.shared.controls
import "./notifications"
import "./infotools"

SidebarFlickable {
    id: root
    contentWidth: width
    contentHeight: infoContent.height + contentTopInset

    signal imageSelectionRequested(bool forAvatar)
    signal bannerColorRequested

    property string screenName: ""
    property bool foreground: false
    readonly property bool isForeground: root.foreground

    onIsForegroundChanged: {
        SystemIdentityService.setUptimeConsumer("left-sidebar-info:" + root.screenName, root.isForeground);
        if (isForeground) {
            NotificationService.hideAllPopups();
            NotificationService.markAllRead();
            TimeService.refreshNow();
        }
    }
    Component.onCompleted: SystemIdentityService.setUptimeConsumer("left-sidebar-info:" + root.screenName,
                                                                   root.isForeground)
    Component.onDestruction: SystemIdentityService.setUptimeConsumer("left-sidebar-info:" + root.screenName,
                                                                     false)

    ColumnLayout {
        id: infoContent
        y: root.contentTopInset
        width: root.width
        height: root.height + root.sectionExpansion * 2
        spacing: 12 + root.sectionExpansion

        ProfileHeaderCard {

            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            screenName: root.screenName
            onBannerColorRequested: root.bannerColorRequested()
            onImageSelectionRequested: forAvatar => root.imageSelectionRequested(forAvatar)
        }

        NotificationList {

            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        InfoToolDrawer {

            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            active: root.isForeground
        }
    }
}
