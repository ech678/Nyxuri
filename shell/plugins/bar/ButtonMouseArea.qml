// Fork & Trim: end4-pC modules/common/widgets/ButtonMouseArea.qml
// SPDX-License-Identifier: GPL-3.0-or-later

pragma ComponentBehavior: Bound
import QtQuick

// MouseArea that contains good defaults for buttons
MouseArea {
    id: root
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
}
