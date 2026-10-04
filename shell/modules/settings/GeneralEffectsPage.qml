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

    Component.onCompleted: NiriConfigService.refresh()

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin

        NiriSetupPrompt {
            Layout.fillWidth: true
            title: I18n.tr("Background effects")
            description: I18n.tr("Create or connect the Clavis X-Ray rules.")
            integrationState: NiriConfigService.state("effects")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "effects"
            blocked: NiriConfigService.busy
            error: NiriConfigService.error
            onSetupRequested: NiriConfigService.setup("effects")
        }

        SettingsSection {
            id: searchSection0
            Layout.fillWidth: true
            flat: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                target: searchSection0
                declaration:
                    '{"id":"general.effects.section.background","route":"general.effects","title":"Background","context":"GeneralEffectsPage","icon":"blur_on","aliases":[]}'
            }
            iconName: "wallpaper"

            GeneralSliderSetting {
                title: I18n.tr("Background opacity")
                from: 0
                to: 100
                stepSize: 1
                suffix: "%"
                value: PersonalizationConfig.shellBackgroundOpacity * 100
                onMoved: value => PersonalizationConfig.setShellBackgroundOpacity(value / 100)
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "blur_on"
                title: I18n.tr("Background blur")

                trailing: StyledSwitch {
                    enabled: BlurService.available
                    checked: PersonalizationConfig.shellBlurEnabled
                    Accessible.name: I18n.tr("Background blur")
                    onToggled: PersonalizationConfig.setShellBlurEnabled(checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "filter_center_focus"
                title: I18n.tr("Blur wallpaper only")
                supportingText: BlurService.niriIntegrationReady ? I18n.tr(
                                                                       "Turning this off also blurs windows and uses more resources") :
                                                                   I18n.tr("Configure Niri blur integration first")

                trailing: StyledSwitch {
                    enabled: BlurService.available && BlurService.niriIntegrationReady
                    checked: PersonalizationConfig.shellBlurXray
                    Accessible.name: I18n.tr("Blur wallpaper only")
                    onToggled: PersonalizationConfig.setShellBlurXray(checked)
                }
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: BlurService.lastError !== ""
                tone: "error"
                message: BlurService.lastError
            }
        }
    }
}
