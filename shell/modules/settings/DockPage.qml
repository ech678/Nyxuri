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

        NiriSetupPrompt {
            Layout.fillWidth: true
            visible: DockService.supportsMinimizeEffects && integrationState !== "ready" && (integrationState
                                                                                             !== "loading"
                                                                                             || error.length
                                                                                             > 0)
            title: I18n.tr("First-time setup")
            description: I18n.tr("Set up window minimization animations.")
            integrationState: NiriConfigService.state("minimize-animation")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "minimize-animation"
            blocked: NiriConfigService.busy
            error: NiriConfigService.errorFeature === "minimize-animation" ? NiriConfigService.error :
                                                                             NiriConfigService.readError
            onSetupRequested: NiriConfigService.setup("minimize-animation")
        }

        SettingsRow {
            Layout.fillWidth: true
            title: I18n.tr("Show Dock")
            iconName: "dock_to_bottom"

            trailing: StyledSwitch {
                checked: DockService.enabled
                Accessible.name: I18n.tr("Show Dock")
                onToggled: DockService.setOption("enabled", checked)
            }
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DockService.configError.length > 0
            tone: "error"
            message: DockService.configError
        }

        SettingsSection {
            id: appearanceSection

            Layout.fillWidth: true
            flat: true
            title: appearanceAnchor.title
            iconName: "dock_to_bottom"

            SettingsSearchAnchor {
                id: appearanceAnchor

                target: appearanceSection
                declaration:
                    '{"id":"dock.section.appearance","route":"dock","title":"Appearance","context":"DockPage","icon":"dock_to_bottom","aliases":["general.dock.section.appearance","size","position","magnification","surface style","notch"]}'
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Screen edge")

                trailing: StyledButtonGroup {
                    model: [
                        {
                            "value": "left",
                            "label": I18n.tr("Left"),
                            "icon": "dock_to_left",
                            "tooltip": I18n.tr("Left")
                        },
                        {
                            "value": "bottom",
                            "label": I18n.tr("Bottom"),
                            "icon": "dock_to_bottom",
                            "tooltip": I18n.tr("Bottom")
                        },
                        {
                            "value": "right",
                            "label": I18n.tr("Right"),
                            "icon": "dock_to_right",
                            "tooltip": I18n.tr("Right")
                        }
                    ]
                    currentValue: DockService.position
                    iconOnly: true
                    buttonMinWidth: 64
                    horizontalPadding: Metrics.spacingL
                    onValueSelected: value => {
                        return DockService.setOption("position", String(value));
                    }
                }
            }

            GeneralSliderSetting {
                title: I18n.tr("Icon size")
                from: 32
                to: 80
                stepSize: 2
                suffix: " px"
                value: DockService.iconSize
                onMoved: value => {
                    return DockService.setOption("iconSize", value);
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Magnify on hover")
                iconName: "zoom_in"

                trailing: StyledSwitch {
                    checked: DockService.magnification
                    Accessible.name: I18n.tr("Magnify on hover")
                    onToggled: DockService.setOption("magnification", checked)
                }
            }

            GeneralSliderSetting {
                title: I18n.tr("Magnification")
                enabled: DockService.magnification
                from: 100
                to: 200
                stepSize: 5
                suffix: "%"
                value: DockService.magnificationScale * 100
                onMoved: value => {
                    return DockService.setOption("magnificationScale", value / 100);
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Surface style")
                iconName: "rounded_corner"

                trailing: StyledButtonGroup {
                    model: [
                        {
                            "value": "default",
                            "label": I18n.tr("Default"),
                            "icon": "rounded_corner",
                            "tooltip": I18n.tr("Floating rounded tray")
                        },
                        {
                            "value": "notch",
                            "label": I18n.tr("Notch"),
                            "icon": "bottom_panel_close",
                            "tooltip": I18n.tr("Keystone notch, attached to the edge")
                        }
                    ]
                    currentValue: DockService.surfaceStyle
                    iconOnly: true
                    buttonMinWidth: 64
                    horizontalPadding: Metrics.spacingL
                    onValueSelected: value => {
                        return DockService.setOption("surfaceStyle", String(value));
                    }
                }
            }
        }

        SettingsSection {
            id: behaviorSection

            Layout.fillWidth: true
            flat: true
            title: behaviorAnchor.title
            iconName: "touch_app"

            SettingsSearchAnchor {
                id: behaviorAnchor

                target: behaviorSection
                declaration:
                    '{"id":"dock.section.behavior","route":"dock","title":"Behavior","context":"DockPage","icon":"touch_app","aliases":["general.dock.section.behavior","auto hide","bounce","recent","indicators","pin","minimize","animation","genie","scale"]}'
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Automatically hide")
                iconName: "visibility_off"

                trailing: StyledSwitch {
                    checked: DockService.autoHide
                    Accessible.name: I18n.tr("Automatically hide")
                    onToggled: DockService.setOption("autoHide", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Bounce when launching")
                iconName: "animation"

                trailing: StyledSwitch {
                    checked: DockService.launchBounce
                    Accessible.name: I18n.tr("Bounce when launching")
                    onToggled: DockService.setOption("launchBounce", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Show running indicators")
                iconName: "fiber_manual_record"

                trailing: StyledSwitch {
                    checked: DockService.showIndicators
                    Accessible.name: I18n.tr("Show running indicators")
                    onToggled: DockService.setOption("showIndicators", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                visible: !DockService.supportsMinimizeEffects || NiriConfigService.ready("minimize-animation")
                title: I18n.tr("Minimize animation")
                iconName: "animation"
                supportingText: !DockService.supportsMinimizeEffects ? I18n.tr(
                                                                           "Window animation selection is unavailable in this session") :
                                                                       NiriConfigService.minimizeAnimationsDisabled
                                                                       ? I18n.tr(
                                                                             "Animations are disabled in your configuration") :
                                                                         ""
                trailing: Item {
                    implicitWidth: effectButtons.implicitWidth
                    implicitHeight: effectButtons.implicitHeight
                    StyledButtonGroup {
                        id: effectButtons
                        anchors.fill: parent
                        enabled: DockService.supportsMinimizeEffects && NiriConfigService.ready(
                                     "minimize-animation") && !NiriConfigService.busy
                        model: [
                            {
                                value: "genie",
                                label: I18n.tr("Genie")
                            },
                            {
                                value: "scale",
                                label: I18n.tr("Scale")
                            }
                        ]
                        currentValue: NiriConfigService.minimizeEffect
                        onValueSelected: value => NiriConfigService.setMinimizeEffect(String(value))
                    }
                    InlineBusyIndicator {
                        anchors.right: effectButtons.left
                        anchors.rightMargin: Metrics.spacingS
                        anchors.verticalCenter: effectButtons.verticalCenter
                        busy: NiriConfigService.busy && NiriConfigService.activeFeature
                              === "minimize-animation"
                    }
                }
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: NiriConfigService.ready("minimize-animation") && NiriConfigService.errorFeature
                         === "minimize-animation" && NiriConfigService.error.length > 0
                tone: "error"
                message: NiriConfigService.error
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Show recent applications")
                iconName: "history"

                trailing: StyledSwitch {
                    checked: DockService.showRecent
                    Accessible.name: I18n.tr("Show recent applications")
                    onToggled: DockService.setOption("showRecent", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Pin applications from the menu")
                iconName: "keep"

                trailing: StyledSwitch {
                    checked: DockService.contextPinning
                    Accessible.name: I18n.tr("Pin applications from the menu")
                    onToggled: DockService.setOption("contextPinning", checked)
                }
            }
        }

        SettingsSection {
            id: previewsSection
            Layout.fillWidth: true
            flat: true
            visible: DockService.supportsThumbnails
            title: previewsAnchor.title
            iconName: "preview"

            SettingsSearchAnchor {
                id: previewsAnchor
                target: previewsSection
                declaration:
                    '{"id":"dock.section.previews","route":"dock","title":"Window previews","context":"DockPage","icon":"preview","aliases":["general.dock.section.previews","thumbnails","hover"],"availability":"dock-previews"}'
            }
            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Show window thumbnails")
                iconName: "preview"
                trailing: StyledSwitch {
                    checked: DockService.showThumbnails
                    Accessible.name: I18n.tr("Show window thumbnails")
                    onToggled: DockService.setOption("showThumbnails", checked)
                }
            }
            GeneralSliderSetting {
                title: I18n.tr("Preview size")
                enabled: DockService.showThumbnails
                from: 96
                to: 240
                stepSize: 8
                suffix: " px"
                value: DockService.previewSize
                onMoved: value => DockService.setOption("previewSize", value)
            }
        }
    }
}
