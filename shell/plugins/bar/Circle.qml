// Fork & Trim: end4-pC modules/common/widgets/Circle.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick

Rectangle {
    property double diameter

    implicitWidth: diameter
    implicitHeight: diameter
    radius: diameter / 2
}
