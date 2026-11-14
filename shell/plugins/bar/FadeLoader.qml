// Fork & Trim: end4-pC modules/common/widgets/FadeLoader.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import qs.commons

Loader {
    id: root
    property bool shown: true
    property alias fade: opacityBehavior.enabled
    property alias animation: opacityBehavior.animation
    opacity: shown ? 1 : 0
    visible: opacity > 0
    active: opacity > 0
    z: item?.z ?? 0

    Behavior on opacity {
        id: opacityBehavior
        animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
    }
}
