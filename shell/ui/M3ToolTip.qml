pragma ComponentBehavior: Bound

import QtQuick
import qs.commons
import qs.ui

// Fork & Trim: iNiR modules/common/m3/M3ToolTip.qml
// Compact tooltip shape with subtle outline and small radius.
// B9.6: end4's PopupToolTip outer margins (= padding) restored — the zeroed
// margins made tooltips hug the bar edge.
PopupToolTip {
    id: root

    horizontalPadding: 10
    verticalPadding: 5
}
