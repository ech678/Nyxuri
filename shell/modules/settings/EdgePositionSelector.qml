import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

StyledButtonGroup {
    id: root

    property string position: "top"
    signal positionSelected(string position)

    model: PersonalizationConfig.edgePositions
    currentValue: root.position
    buttonMinWidth: 64
    horizontalPadding: Metrics.spacingL
    Layout.preferredWidth: implicitWidth
    onValueSelected: value => root.positionSelected(String(value))
}
