import QtQuick
import "../../../commons/WallpaperSource.js" as WallpaperSource
import qs.commons
import qs.services
import qs.ui

AccountProfileHeader {
    id: root
    wallpaperIsImage: WallpaperSource.isImage(wallpaperPath)
    wallpaperComponent: Component {
        Item {
            id: pwRoot
            property string sourcePath: ""
            property string previewPath: ""
            Image {
                anchors.fill: parent
                source: WallpaperSource.isImage(pwRoot.sourcePath) ? Paths.fileUrl(pwRoot.sourcePath) : ""
                fillMode: Image.PreserveAspectCrop
                visible: source !== ""
            }
        }
    }

    signal imageSelectionRequested(bool forAvatar)
    signal bannerColorRequested

    property string screenName: ""
    coverHeight: Math.round(width / 2.5)
    profileAreaHeight: 112
    avatarSize: 96
    wallpaperPath: PersonalizationConfig.bannerSource || (ActionGateway.wallpaperHost ? ActionGateway.wallpaperHost.currentWallpaper : "")
    previewWallpaperPath: ""
    colorWallpaper: WallpaperSource.isSolid(wallpaperPath)
    avatarUrl: AvatarService.avatarUrl
    fallbackAvatarUrl: Paths.fileUrl(Paths.defaultAvatar)
    accountIdentity: SystemIdentityService.accountIdentity
    distroId: SystemIdentityService.distroId
    distroName: SystemIdentityService.distroName
    uptimeText: SystemIdentityService.uptimeText
    showNetworkStatus: false
    surfaceColor: BlurService.opaqueBackgroundColor(Appearance.m3colors.m3surfaceContainerHigh)

    onBannerFileActivated: root.imageSelectionRequested(false)
    onBannerColorActivated: root.bannerColorRequested()
    onBannerCleared: PersonalizationConfig.setBannerSource("")
    onAvatarActivated: root.imageSelectionRequested(true)
}
