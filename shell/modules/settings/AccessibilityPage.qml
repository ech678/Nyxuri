import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

StyledFlickable {
    id: root
    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2
    ColumnLayout {
        id: contentColumn
        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingL
        SettingsSection {
            id: searchSection0
            Layout.fillWidth: true
            flat: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                target: searchSection0
                declaration: '{"id":"general.accessibility.section.motion","route":"general.accessibility","title":"Motion and readability","context":"AccessibilityPage","icon":"accessibility_new","aliases":[]}'
            }
            iconName: "animation"
            SettingsRow {
                Layout.fillWidth: true
                iconName: "motion_photos_off"
                title: I18n.tr("Reduce motion")
                supportingText: I18n.tr("Shorten and simplify interface animations")
                trailing: StyledSwitch {
                    checked: UiPreferences.reduceMotion
                    Accessible.name: I18n.tr("Reduce motion")
                    onToggled: UiPreferences.setReduceMotion(checked)
                }
            }
            GeneralSliderSetting {
                title: I18n.tr("Text size")
                description: I18n.tr("Scale every interface label and value")
                from: 85
                to: 150
                stepSize: 5
                suffix: "%"
                value: Math.round(UiPreferences.fontScale * 100)
                onMoved: value => UiPreferences.setFontScale(value / 100)
            }
            SettingsRow {
                Layout.fillWidth: true
                iconName: "contrast"
                title: I18n.tr("High contrast")
                supportingText: I18n.tr("Raise text contrast against its background")
                trailing: StyledSwitch {
                    checked: UiPreferences.highContrast
                    Accessible.name: I18n.tr("High contrast")
                    onToggled: UiPreferences.setHighContrast(checked)
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                iconName: "opacity"
                title: I18n.tr("Reduce transparency")
                supportingText: I18n.tr("Draw surfaces fully opaque instead of blending them")
                trailing: StyledSwitch {
                    checked: UiPreferences.reduceTransparency
                    Accessible.name: I18n.tr("Reduce transparency")
                    onToggled: UiPreferences.setReduceTransparency(checked)
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                iconName: "battery_saver"
                title: I18n.tr("Low power mode")
                supportingText: I18n.tr("Turn off motion and transparency to save energy")
                trailing: StyledSwitch {
                    checked: UiPreferences.lowPowerMode
                    Accessible.name: I18n.tr("Low power mode")
                    onToggled: UiPreferences.setLowPowerMode(checked)
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                iconName: "wb_twilight"
                title: I18n.tr("Follow the sun")
                supportingText: ThemeService.solarScheduleAvailable ? I18n.tr("Switch between light and dark at sunrise and sunset") : I18n.tr("Waiting for today's sunrise and sunset")
                trailing: StyledSwitch {
                    checked: UiPreferences.followSun
                    enabled: ThemeService.solarScheduleAvailable
                    Accessible.name: I18n.tr("Follow the sun")
                    onToggled: UiPreferences.setFollowSun(checked)
                }
            }
        }
    }
}
