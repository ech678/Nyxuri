import QtQuick
import qs.commons
import qs.ui
import qs.services

RippleButton {
    id: button

    required default property Item content
    property bool extraActiveCondition: false
    property alias colBackground: button.containerColor

    implicitHeight: Math.max(content.implicitHeight, 26, content.implicitHeight)
    implicitWidth: implicitHeight
    contentItem: content

}
