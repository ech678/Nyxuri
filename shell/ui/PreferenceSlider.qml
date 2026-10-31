import QtQuick
import QtQuick.Layouts
import QtQuick.Templates
import qs.commons
import qs.ui

// Slider row (Caelestia Nexus SliderRow): leading icon, label plus current
// value on the first line, one delicate full-width slider below. The slim
// track and the thin handle that grows while pressed are the Nexus look;
// wheel input on the strip fine-tunes the value by `wheelStep` instead of
// scrolling the page.
ConnectedRect {
    id: root

    property string icon: ""
    property alias label: titleLabel.text
    property alias valueLabel: valueLabel.text
    property real value: 0
    property real from: 0
    property real to: 1
    property real stepSize: 0
    property real wheelStep: stepSize > 0 ? stepSize : (to - from) / 20

    signal moved(real value)

    // Fired alongside the final `moved` of an interaction (drag release,
    // click, wheel step) — consumers with live-preview semantics (the
    // horizontal clock axes) persist on commit instead of on every tick.
    signal committed(real value)

    Layout.fillWidth: true
    implicitHeight: column.implicitHeight + NexusStyle.padding.medium * 2

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.largeIncreased
        anchors.rightMargin: NexusStyle.padding.largeIncreased
        spacing: NexusStyle.padding.small

        MaterialSymbol {
            visible: root.icon.length > 0
            Layout.preferredWidth: root.icon.length > 0 ? implicitWidth : 0
            text: root.icon
            iconSize: NexusStyle.icon.medium
            fill: 1
            color: Appearance.m3colors.m3onSurfaceVariant
        }

        ColumnLayout {
            id: column

            Layout.fillWidth: true
            spacing: NexusStyle.padding.extraSmall

            RowLayout {
                Layout.fillWidth: true
                spacing: NexusStyle.padding.small

                StyledText {
                    id: titleLabel

                    Layout.fillWidth: true
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    elide: Text.ElideRight
                }

                StyledText {
                    id: valueLabel

                    color: Appearance.m3colors.m3outline
                    font.pixelSize: NexusStyle.font.bodyMedium
                }
            }

            // Wheel strip wrapping the slider: wheel events the slider does
            // not accept bubble up here and adjust the value.
            MouseArea {
                id: wheelStrip

                Layout.fillWidth: true
                Layout.preferredHeight: NexusStyle.padding.large + NexusStyle.padding.medium

                function onWheel(event: WheelEvent): void {
                    if (event.angleDelta.y > 0) {
                        const next = Math.min(root.to, root.value + root.wheelStep);
                        root.moved(next);
                        root.committed(next);
                    } else if (event.angleDelta.y < 0) {
                        const next = Math.max(root.from, root.value - root.wheelStep);
                        root.moved(next);
                        root.committed(next);
                    }
                }

                // Unstyled Slider (QtQuick.Templates): behaviour only, all
                // visuals live in the contentItem below.
                Slider {
                    id: slider

                    // visualPosition tracks `value`; while dragging the
                    // Binding below overrides pos so the handle follows the
                    // finger before the consumer writes the value back.
                    property real pos: visualPosition

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    implicitHeight: NexusStyle.padding.medium

                    from: root.from
                    to: root.to
                    stepSize: root.stepSize
                    value: root.value
                    enabled: root.enabled

                    Binding {
                        target: slider
                        property: "pos"
                        value: Math.max(0, Math.min(1, dragArea.pressStartPos + dragArea.dragMovement))
                        when: dragArea.pressed
                    }

                    MouseArea {
                        id: dragArea

                        property real pressStartX
                        property real pressStartPos
                        property real dragMovement

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: NexusStyle.padding.large + NexusStyle.padding.medium
                        preventStealing: true

                        onPressed: event => {
                            dragArea.pressStartX = event.x;
                            dragArea.pressStartPos = slider.visualPosition;
                        }
                        onPositionChanged: event => {
                            dragArea.dragMovement = (event.x - dragArea.pressStartX) / width;
                            root.moved(slider.from + slider.pos * (slider.to - slider.from));
                        }
                        onReleased: event => {
                            const next = dragArea.dragMovement === 0 ? slider.from + Math.max(0, Math.min(1,
                                                                                                          event.x / width))
                                                                       * (slider.to - slider.from) :
                                                                       slider.from + slider.pos * (slider.to
                                                                                                   - slider.from);
                            root.moved(next);
                            root.committed(next);
                            dragArea.dragMovement = 0;
                        }
                    }

                    contentItem: Item {
                        // Remaining track past the handle; thins and fades
                        // as it collapses against the right edge dot.
                        Rectangle {
                            id: remaining

                            readonly property real fade: Math.min(width, 12) / 12

                            anchors.left: handle.right
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: NexusStyle.padding.extraSmall
                            height: slider.height * (slider.height <= 12 ? fade : Math.min(fade * 2, 1))
                            radius: NexusStyle.rounding.extraSmall / 2
                            topLeftRadius: NexusStyle.rounding.extraSmall / 2
                            bottomLeftRadius: NexusStyle.rounding.extraSmall / 2
                            color: slider.enabled ? Appearance.m3colors.m3secondaryContainer :
                                                    Appearance.applyAlpha(Appearance.m3colors.m3onSurface,
                                                                          0.1)
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.rightMargin: 4 * remaining.fade
                            width: 4 * remaining.fade
                            height: width
                            radius: NexusStyle.rounding.full
                            color: filled.color
                        }

                        Rectangle {
                            id: filled

                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - handle.width - NexusStyle.padding.extraSmall) * slider.pos
                            height: slider.height
                            radius: NexusStyle.rounding.extraSmall / 2
                            topRightRadius: NexusStyle.rounding.extraSmall / 2
                            bottomRightRadius: NexusStyle.rounding.extraSmall / 2
                            color: slider.enabled ? Appearance.m3colors.m3primary : Appearance.applyAlpha(
                                                        Appearance.m3colors.m3onSurface, 0.38)

                            Behavior on width {
                                enabled: !dragArea.pressed
                                NumberAnimation {
                                    duration: Appearance.animation.expressiveFastEffects.duration
                                    easing.type: Appearance.animation.expressiveFastEffects.type
                                    easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                                }
                            }
                        }

                        Rectangle {
                            id: handle

                            anchors.left: filled.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: NexusStyle.padding.extraSmall
                            width: 4
                            height: slider.height * (dragArea.pressed ? 1.6 : 1.25)
                            radius: NexusStyle.rounding.full
                            color: filled.color

                            Behavior on height {
                                NumberAnimation {
                                    duration: Appearance.animation.expressiveFastSpatial.duration
                                    easing.type: Appearance.animation.expressiveFastSpatial.type
                                    easing.bezierCurve: Appearance.animation.expressiveFastSpatial.bezierCurve
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
