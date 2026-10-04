import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.modules.sidebars.dashboard.infotools
import qs.shared.i18n

Item {
    id: root

    property bool active: false

    readonly property real progress: TimerService.pomodoroLapDuration > 0 ? TimerService.pomodoroSecondsLeft
                                                                            / TimerService.pomodoroLapDuration :
                                                                            0
    readonly property bool canReset: TimerService.pomodoroSecondsLeft < TimerService.pomodoroLapDuration
                                     || TimerService.pomodoroCycle > 0 || TimerService.pomodoroBreak
    readonly property color phaseColor: TimerService.pomodoroBreak ? Appearance.colors.colTertiary :
                                                                     Appearance.colors.colPrimary

    function timeText() {
        const minutes = Math.floor(TimerService.pomodoroSecondsLeft / 60).toString().padStart(2, "0");
        const seconds = Math.floor(TimerService.pomodoroSecondsLeft % 60).toString().padStart(2, "0");
        return `${minutes}:${seconds}`;
    }

    function phaseText() {
        if (TimerService.pomodoroLongBreak)
            return I18n.tr("Long break");
        if (TimerService.pomodoroBreak)
            return I18n.tr("Break");
        return I18n.tr("Focus");
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            MaterialSymbol {
                text: "search_activity"
                iconSize: 22
                fill: 1
                color: root.phaseColor
            }

            Text {
                Layout.fillWidth: true
                text: I18n.tr("Pomodoro")
                color: Appearance.colors.colOnLayer0
                font.family: Fonts.ui
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            Text {
                text: I18n.tr("Round %1 / %2").arg(TimerService.pomodoroCycle + 1).arg(
                          TimerService.cyclesBeforeLongBreak)
                color: Appearance.colors.colSubtext
                font.family: Fonts.ui
                font.pixelSize: 12
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ToolCircularProgress {
                id: progressRing

                anchors.centerIn: parent
                implicitSize: Math.min(parent.width, parent.height, 240)
                lineWidth: 10
                value: root.progress
                primaryColor: root.phaseColor
                trackColor: Appearance.applyAlpha(root.phaseColor, 0.2)
                enableAnimation: root.active
                animationDuration: Appearance.animation.expressiveSlowEffects.duration

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 2

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: root.timeText()
                        color: Appearance.colors.colOnLayer0
                        font.family: Fonts.numeric
                        font.pixelSize: 48
                        font.weight: Font.DemiBold
                    }

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: root.phaseText()
                        color: Appearance.colors.colSubtext
                        font.family: Fonts.ui
                        font.pixelSize: 15
                        font.weight: Font.Medium
                    }
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10

            Repeater {
                model: TimerService.cyclesBeforeLongBreak

                Rectangle {
                    id: cycleIndicator

                    required property int index

                    implicitWidth: cycleIndicator.index === TimerService.pomodoroCycle ? 24 : 8
                    implicitHeight: 8
                    radius: Appearance.rounding.full
                    color: cycleIndicator.index <= TimerService.pomodoroCycle ? root.phaseColor :
                                                                                Appearance.applyAlpha(
                                                                                    Appearance.colors.colOnLayer0,
                                                                                    0.18)

                    Behavior on implicitWidth {
                        NumberAnimation {
                            duration: Appearance.animation.expressiveDefaultEffects.duration
                            easing.type: Appearance.animation.expressiveDefaultEffects.type
                            easing.bezierCurve: Appearance.animation.expressiveDefaultEffects.bezierCurve
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            RippleButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                buttonRadius: Appearance.rounding.large
                containerColor: TimerService.pomodoroRunning ? Appearance.colors.colSecondaryContainer :
                                                               Appearance.colors.colPrimary
                stateLayerColor: TimerService.pomodoroRunning ? Appearance.colors.colSecondaryContainerHover :
                                                                Appearance.colors.colPrimaryHover
                pressedStateLayerColor: TimerService.pomodoroRunning
                                        ? Appearance.colors.colSecondaryContainerActive :
                                          Appearance.colors.colPrimaryActive
                rippleColor: TimerService.pomodoroRunning ? Appearance.colors.colOnSecondaryContainer :
                                                            Appearance.colors.colOnPrimary
                Accessible.name: TimerService.pomodoroRunning ? I18n.tr("Pause Pomodoro") : I18n.tr(
                                                                    "Start Pomodoro")
                onClicked: TimerService.togglePomodoro()

                contentItem: Item {
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6

                        MaterialSymbol {
                            text: TimerService.pomodoroRunning ? "pause" : "play_arrow"
                            iconSize: 20
                            fill: 1
                            color: TimerService.pomodoroRunning ? Appearance.colors.colOnSecondaryContainer :
                                                                  Appearance.colors.colOnPrimary
                        }

                        Text {
                            text: TimerService.pomodoroRunning ? I18n.tr("Pause") :
                                                                 TimerService.pomodoroSecondsLeft
                                                                 === TimerService.pomodoroLapDuration
                                                                 ? I18n.tr("Start") : I18n.tr("Resume")
                            color: TimerService.pomodoroRunning ? Appearance.colors.colOnSecondaryContainer :
                                                                  Appearance.colors.colOnPrimary
                            font.family: Fonts.ui
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }

            RippleButton {
                Layout.preferredWidth: 96
                Layout.preferredHeight: 44
                buttonRadius: Appearance.rounding.large
                enabled: root.canReset
                containerColor: Appearance.colors.colErrorContainer
                stateLayerColor: Appearance.colors.colErrorContainerHover
                pressedStateLayerColor: Appearance.colors.colErrorContainerActive
                rippleColor: Appearance.colors.colOnErrorContainer
                Accessible.name: I18n.tr("Reset Pomodoro")
                onClicked: TimerService.resetPomodoro()

                contentItem: Item {
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 5

                        MaterialSymbol {
                            text: "restart_alt"
                            iconSize: 19
                            color: Appearance.colors.colOnErrorContainer
                        }

                        Text {
                            text: I18n.tr("Reset")
                            color: Appearance.colors.colOnErrorContainer
                            font.family: Fonts.ui
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }
        }
    }
}
