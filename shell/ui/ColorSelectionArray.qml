// Fork & Trim: end4-pC modules/common/widgets/ColorSelectionArray.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

RowLayout {
    id: root
    Layout.fillWidth: true
    Layout.leftMargin: 8
    Layout.rightMargin: 8
    spacing: 10

    property string icon: "palette"
    property string text: "Color"
    property string currentValue: ""
    property var options: ["primary", "secondary", "tertiary", "primaryContainer", "secondaryContainer", "tertiaryContainer", "layer1", "layer0"]
    property bool showLabel: true
    property real itemSpacing: 10
    property bool showTooltip: false
    signal selected(string newValue)

    MaterialSymbol {
        visible: root.showLabel
        text: root.icon
        iconSize: Typography.bodyLarge.pixelSize + 5
        color: Appearance.colors.colOnLayer0
    }

    StyledText {
        visible: root.showLabel
        text: root.text
        color: Appearance.colors.colOnLayer0
    }

    Item {
        visible: root.showLabel
        Layout.fillWidth: true
    }

    Flow {
        Layout.fillWidth: !root.showLabel
        Layout.preferredWidth: root.showLabel ? implicitWidth : -1
        spacing: root.itemSpacing

        Repeater {
            model: root.options
            delegate: Item {
                id: slot
                required property string modelData
                readonly property bool isSelected: root.currentValue === modelData

                implicitWidth: 40
                implicitHeight: 40

                Rectangle {
                    id: ring
                    anchors.centerIn: parent
                    width: slot.isSelected ? parent.width : parent.width - 8
                    height: slot.isSelected ? parent.height : parent.height - 8
                    radius: slot.isSelected ? Appearance.rounding.normal : width / 2
                    color: "transparent"
                    border.width: slot.isSelected ? 2 : 0
                    border.color: Appearance.colors.colOnLayer0

                    Behavior on radius {
                        animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                    }
                    Behavior on width {
                        animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                    }
                    Behavior on height {
                        animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                    }
                }

                Rectangle {
                    id: swatch
                    anchors.centerIn: parent
                    width: slot.isSelected ? parent.width - 8 : parent.width - 8
                    height: slot.isSelected ? parent.height - 8 : parent.height - 8
                    radius: slot.isSelected ? Appearance.rounding.normal - 4 : width / 2
                    color: slot.modelData === "black" || slot.modelData === "transparent" ? slot.modelData : Appearance.colors["col" + slot.modelData.charAt(0).toUpperCase() + slot.modelData.slice(1)]
                    border.width: slot.modelData === "transparent" ? 1 : 0
                    border.color: Appearance.colors.colOutlineVariant

                    Behavior on radius {
                        animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                    }
                }

                MouseArea {
                    readonly property bool hovered: containsMouse
                    anchors.fill: parent
                    hoverEnabled: root.showTooltip
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selected(slot.modelData)

                    StyledToolTip {
                        extraVisibleCondition: root.showTooltip
                        text: slot.modelData
                    }
                }
            }
        }
    }
}
