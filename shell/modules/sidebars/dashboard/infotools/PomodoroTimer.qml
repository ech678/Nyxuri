import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ToolCircularProgress {
            Layout.alignment: Qt.AlignHCenter
            implicitSize: 200
            lineWidth: 8
            value: TimerService.pomodoroLapDuration > 0 ? TimerService.pomodoroSecondsLeft / TimerService.pomodoroLapDuration : 0
            enableAnimation: true

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: {
                        const minutes = Math.floor(TimerService.pomodoroSecondsLeft / 60).toString().padStart(2, "0");
                        const seconds = Math.floor(TimerService.pomodoroSecondsLeft % 60).toString().padStart(2, "0");
                        return `${minutes}:${seconds}`;
                    }
                    color: Appearance.colors.colOnSurface
                    font.family: Fonts.numeric
                    font.pixelSize: Appearance.scaledFont(40)
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: TimerService.pomodoroLongBreak ? I18n.tr("Long break") : TimerService.pomodoroBreak ? I18n.tr("Break") : I18n.tr("Focus")
                    color: Appearance.colors.colSubtext
                    font.family: Fonts.ui
                    font.pixelSize: Appearance.scaledFont(14)
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                implicitWidth: 36
                implicitHeight: 36
                radius: Appearance.rounding.full
                color: BlurService.opaqueBackgroundColor(Appearance.m3colors.m3surfaceContainer)

                Text {
                    anchors.centerIn: parent
                    text: TimerService.pomodoroCycle + 1
                    color: Appearance.colors.colOnLayer2
                    font.family: Fonts.numeric
                    font.pixelSize: Appearance.scaledFont(14)
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10

            RippleButton {
                implicitWidth: 90
                implicitHeight: 35
                buttonRadius: Appearance.rounding.full
                containerColor: TimerService.pomodoroRunning ? Appearance.colors.colSecondaryContainer : Appearance.colors.colPrimary
                stateLayerColor: TimerService.pomodoroRunning ? Appearance.colors.colSecondaryContainerHover : Appearance.colors.colPrimaryHover
                pressedStateLayerColor: TimerService.pomodoroRunning ? Appearance.colors.colSecondaryContainerActive : Appearance.colors.colPrimaryActive
                rippleColor: TimerService.pomodoroRunning ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnPrimary
                Accessible.name: TimerService.pomodoroRunning ? I18n.tr("Pause Pomodoro") : I18n.tr("Start Pomodoro")
                onClicked: TimerService.togglePomodoro()

                contentItem: Text {
                    text: TimerService.pomodoroRunning ? I18n.tr("Pause") : TimerService.pomodoroSecondsLeft === TimerService.pomodoroLapDuration ? I18n.tr("Start") : I18n.tr("Resume")
                    color: TimerService.pomodoroRunning ? Appearance.colors.colOnSecondaryContainer : Appearance.colors.colOnPrimary
                    font.family: Fonts.ui
                    font.pixelSize: Appearance.scaledFont(14)
                    font.weight: Font.Medium
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            RippleButton {
                implicitWidth: 90
                implicitHeight: 35
                buttonRadius: Appearance.rounding.full
                enabled: TimerService.pomodoroSecondsLeft < TimerService.pomodoroLapDuration || TimerService.pomodoroCycle > 0 || TimerService.pomodoroBreak
                containerColor: Appearance.colors.colErrorContainer
                stateLayerColor: Appearance.colors.colErrorContainerHover
                pressedStateLayerColor: Appearance.colors.colErrorContainerActive
                rippleColor: Appearance.colors.colOnErrorContainer
                Accessible.name: I18n.tr("Reset Pomodoro")
                onClicked: TimerService.resetPomodoro()

                contentItem: Text {
                    text: I18n.tr("Reset")
                    color: Appearance.colors.colOnErrorContainer
                    font.family: Fonts.ui
                    font.pixelSize: Appearance.scaledFont(14)
                    font.weight: Font.Medium
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
