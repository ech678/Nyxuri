import QtQuick
import QtQuick.Layouts
import qs.shared.theme

RowLayout {
    id: root

    property var model: []
    readonly property int pageSize: 5
    property int page: 0
    readonly property int count: model ? model.length : 0
    readonly property int pageCount: Math.max(1, Math.ceil(count / pageSize))
    readonly property int currentPage: Math.max(0, Math.min(page, pageCount - 1))
    readonly property var items: model ? model.slice(currentPage * pageSize, (currentPage + 1) * pageSize) :
                                         []

    onPageCountChanged: page = currentPage
    Layout.fillWidth: true
    visible: count > pageSize
    spacing: Metrics.spacingS

    IconButton {
        iconName: "chevron_left"
        accessibleName: qsTr("Previous page")
        enabled: root.currentPage > 0
        onClicked: root.page = root.currentPage - 1
    }
    Text {
        Layout.fillWidth: true
        horizontalAlignment: Text.AlignHCenter
        text: qsTr("%1–%2 of %3").arg(root.currentPage * root.pageSize + 1).arg(Math.min(root.count, (
                                                                                             root.currentPage
                                                                                             + 1) * root.pageSize)).arg(
                  root.count)
        color: Appearance.colors.colOnSurfaceVariant
        font.family: Fonts.ui
        font.pixelSize: 12
    }
    IconButton {
        iconName: "chevron_right"
        accessibleName: qsTr("Next page")
        enabled: root.currentPage + 1 < root.pageCount
        onClicked: root.page = root.currentPage + 1
    }
}
