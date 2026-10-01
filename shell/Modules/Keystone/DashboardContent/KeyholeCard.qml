import QtQuick
import qs.Common
import qs.Services

Item {
    id: root

    readonly property Item glassBackgroundItem: glassBackground
    readonly property real glassAlpha: BlurService.enabled ? Math.min(
                                                                 PersonalizationConfig.shellBackgroundOpacity,
                                                                 0.68) : 1

    Rectangle {
        id: glassBackground
        anchors.fill: parent
        anchors.margins: 10
        radius: 20
        color: Appearance.applyAlpha(Appearance.colors.colLayer0, root.glassAlpha)
    }

    Loader {
        anchors.fill: glassBackground
        sourceComponent: PersonalizationConfig.keystoneKeyholeCard === "pomodoro" ? pomodoroCard : weatherCard
    }

    Component {
        id: weatherCard
        DashboardWeatherCard {
            active: root.visible
        }
    }

    Component {
        id: pomodoroCard
        DashboardPomodoroCard {
            active: root.visible
        }
    }
}
