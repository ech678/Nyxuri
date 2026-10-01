import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components

MaterialSplitSlider {
    id: quickSlider

    property string materialSymbol: ""
    property string secondaryMaterialSymbol: ""
    property real secondaryIconLocation: 0
    property string percentText: `${Math.round(((value - from) / (to - from)) * 100)}%`

    configuration: MaterialSplitSlider.Configuration.M
    dividerValues: secondaryMaterialSymbol.length > 0 ? [secondaryIconLocation] : []
    Layout.fillWidth: true

    Text {
        id: percentLabel

        readonly property bool nearEmpty: quickSlider.visualPosition * quickSlider.effectiveDraggingWidth <= implicitWidth + 20

        anchors {
            verticalCenter: quickSlider.verticalCenter
            left: nearEmpty ? quickSlider.handle.left : quickSlider.left
            leftMargin: nearEmpty ? 14 : 8
        }
        text: quickSlider.percentText
        color: nearEmpty ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnPrimary
        font.family: Fonts.numeric
        font.pixelSize: 12
        font.weight: Font.Medium
        renderType: Text.NativeRendering
        z: 1

        Behavior on color {
            ColorAnimation {
                duration: quickSlider.fastAnimation.duration
                easing.type: quickSlider.fastAnimation.type
                easing.bezierCurve: quickSlider.fastAnimation.bezierCurve
            }
        }

        Behavior on anchors.leftMargin {
            NumberAnimation {
                alwaysRunToEnd: true
                duration: quickSlider.fastAnimation.duration
                easing.type: quickSlider.fastAnimation.type
                easing.bezierCurve: quickSlider.fastAnimation.bezierCurve
            }
        }
    }

    MaterialSymbol {
        id: icon

        property bool nearFull: quickSlider.value >= 0.9

        anchors {
            verticalCenter: quickSlider.verticalCenter
            right: nearFull ? quickSlider.handle.right : quickSlider.right
            rightMargin: nearFull ? 14 : 8
        }
        text: quickSlider.materialSymbol
        iconSize: 20
        fill: 0
        color: nearFull ? Appearance.colors.colOnPrimary : Appearance.colors.colOnSecondaryContainer

        Behavior on color {
            ColorAnimation {
                duration: quickSlider.fastAnimation.duration
                easing.type: quickSlider.fastAnimation.type
                easing.bezierCurve: quickSlider.fastAnimation.bezierCurve
            }
        }

        Behavior on anchors.rightMargin {
            NumberAnimation {
                alwaysRunToEnd: true
                duration: quickSlider.fastAnimation.duration
                easing.type: quickSlider.fastAnimation.type
                easing.bezierCurve: quickSlider.fastAnimation.bezierCurve
            }
        }
    }

    MaterialSymbol {
        id: secondaryIcon

        visible: quickSlider.secondaryMaterialSymbol.length > 0
        property bool nearIcon: quickSlider.secondaryIconLocation - quickSlider.value <= 0.1
            && quickSlider.secondaryIconLocation - quickSlider.value > (quickSlider.handleWidth + 8 - 14) / quickSlider.effectiveDraggingWidth

        anchors {
            verticalCenter: quickSlider.verticalCenter
            right: nearIcon ? quickSlider.handle.right : quickSlider.right
            rightMargin: nearIcon ? 14 : (1 - quickSlider.secondaryIconLocation) * quickSlider.effectiveDraggingWidth + quickSlider.rightPadding + 8
        }
        text: quickSlider.secondaryMaterialSymbol
        iconSize: 20
        fill: 0
        color: quickSlider.value >= quickSlider.secondaryIconLocation - 0.1 ? Appearance.colors.colOnPrimary : Appearance.colors.colOnSecondaryContainer

        Behavior on color {
            ColorAnimation {
                duration: quickSlider.fastAnimation.duration
                easing.type: quickSlider.fastAnimation.type
                easing.bezierCurve: quickSlider.fastAnimation.bezierCurve
            }
        }

        Behavior on anchors.rightMargin {
            NumberAnimation {
                alwaysRunToEnd: true
                duration: quickSlider.fastAnimation.duration
                easing.type: quickSlider.fastAnimation.type
                easing.bezierCurve: quickSlider.fastAnimation.bezierCurve
            }
        }
    }
}
