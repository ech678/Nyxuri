pragma Singleton
import QtQuick
import qs.shared.theme

QtObject {
    readonly property string basePath: Resources.iconsRoot

    // 注册图标值
    property string previous: basePath + "previous.svg"
    property string play: basePath + "play.svg"
    property string pause: basePath + "pause.svg"
    property string next: basePath + "next.svg"
}
