import QtQuick
import qs.Common
import qs.Services
import qs.Widgets.common

AccountProfileHeader {
    id: root

    signal imageSelectionRequested(bool forAvatar)
    signal bannerColorRequested

    property string screenName: ""
    coverHeight: Math.round(width / 2.5)
    profileAreaHeight: 112
    avatarSize: 96
    wallpaperPath: PersonalizationConfig.bannerSource || WallpaperService.currentWallpaper
    previewWallpaperPath: WallpaperPaletteSession.previewForScreen("banner", "")
    colorWallpaper: WallpaperService.isColorSource(wallpaperPath)
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
