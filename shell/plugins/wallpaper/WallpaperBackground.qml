import QtQuick
import qs.services

Item {
    OverviewWallpaper {}
    DesktopWallpaper {}

    Component.onCompleted: {
        ActionGateway.wallpaperHost = WallpaperService;
        ActionGateway.sceneHost = WallpaperSceneService;
    }
    Component.onDestruction: {
        if (ActionGateway.wallpaperHost === WallpaperService)
            ActionGateway.wallpaperHost = null;
        if (ActionGateway.sceneHost === WallpaperSceneService)
            ActionGateway.sceneHost = null;
    }
}
