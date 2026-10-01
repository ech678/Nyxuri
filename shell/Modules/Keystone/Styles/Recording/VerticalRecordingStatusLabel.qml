import QtQuick
import qs.Common

Item {
    id: root

    required property string label
    required property string edge
    readonly property bool hasCjk: /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]/.test(label)

    implicitWidth: 42
    implicitHeight: hasCjk ? uprightColumn.implicitHeight : latinLabel.implicitWidth

    Column {
        id: uprightColumn

        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 1
        visible: root.hasCjk

        Repeater {
            model: root.label.length

            delegate: Text {
                required property int index

                text: root.label.charAt(index)
                color: Appearance.colors.colOnLayer0
                font.family: Fonts.ui
                font.pixelSize: 14
                font.weight: Font.DemiBold
            }

        }

    }

    Text {
        id: latinLabel

        anchors.centerIn: parent
        visible: !root.hasCjk
        text: root.label
        color: Appearance.colors.colOnLayer0
        font.family: Fonts.ui
        font.pixelSize: 14
        font.weight: Font.DemiBold
        rotation: root.edge === "left" ? -90 : 90
    }

}
