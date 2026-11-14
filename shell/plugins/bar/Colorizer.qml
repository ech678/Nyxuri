// Fork & Trim: end4-pC modules/common/widgets/Colorizer.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Effects
import qs.commons

MultiEffect {
    property color sourceColor: "black"

    colorization: 1
    brightness: 1 - sourceColor.hslLightness

    Behavior on colorizationColor {
        animation: Appearance.animation.elementMoveFast.colorAnimation.createObject(this)
    }
}
