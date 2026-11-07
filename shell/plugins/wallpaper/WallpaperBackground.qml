import QtQuick
import qs.services

Item {
    OverviewWallpaper {}
    DesktopWallpaper {}

    Component.onCompleted: ActionGateway.wallpaperHost = WallpaperService
    Component.onDestruction: {
        if (ActionGateway.wallpaperHost === WallpaperService)
            ActionGateway.wallpaperHost = null;
    }
}
