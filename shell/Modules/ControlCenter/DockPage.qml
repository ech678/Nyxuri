import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

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
            title: qsTr("First-time setup")
            description: qsTr("Set up window minimization animations.")
            integrationState: NiriConfigService.state("minimize-animation")
            busy: NiriConfigService.busy && NiriConfigService.activeFeature === "minimize-animation"
            blocked: NiriConfigService.busy
            error: NiriConfigService.errorFeature === "minimize-animation" ? NiriConfigService.error :
                                                                             NiriConfigService.readError
            onSetupRequested: NiriConfigService.setup("minimize-animation")
        }

        SettingsRow {
            Layout.fillWidth: true
            title: qsTr("Show Dock")
            iconName: "dock_to_bottom"

            trailing: StyledSwitch {
                checked: DockService.enabled
                Accessible.name: qsTr("Show Dock")
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
                    '{"id":"general.dock.section.appearance","route":"general.dock","title":"Appearance","context":"DockPage","icon":"dock_to_bottom","aliases":["size","position","magnification"]}'
            }

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Screen edge")

                trailing: StyledButtonGroup {
                    model: [
                        {
                            "value": "left",
                            "label": qsTr("Left"),
                            "icon": "dock_to_left",
                            "tooltip": qsTr("Left")
                        },
                        {
                            "value": "bottom",
                            "label": qsTr("Bottom"),
                            "icon": "dock_to_bottom",
                            "tooltip": qsTr("Bottom")
                        },
                        {
                            "value": "right",
                            "label": qsTr("Right"),
                            "icon": "dock_to_right",
                            "tooltip": qsTr("Right")
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
                title: qsTr("Icon size")
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
                title: qsTr("Magnify on hover")
                iconName: "zoom_in"

                trailing: StyledSwitch {
                    checked: DockService.magnification
                    Accessible.name: qsTr("Magnify on hover")
                    onToggled: DockService.setOption("magnification", checked)
                }
            }

            GeneralSliderSetting {
                title: qsTr("Magnification")
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
                    '{"id":"general.dock.section.behavior","route":"general.dock","title":"Behavior","context":"DockPage","icon":"touch_app","aliases":["auto hide","bounce","recent","indicators","pin","minimize","animation","genie","scale"]}'
            }

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Automatically hide")
                iconName: "visibility_off"

                trailing: StyledSwitch {
                    checked: DockService.autoHide
                    Accessible.name: qsTr("Automatically hide")
                    onToggled: DockService.setOption("autoHide", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Bounce when launching")
                iconName: "animation"

                trailing: StyledSwitch {
                    checked: DockService.launchBounce
                    Accessible.name: qsTr("Bounce when launching")
                    onToggled: DockService.setOption("launchBounce", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Show running indicators")
                iconName: "fiber_manual_record"

                trailing: StyledSwitch {
                    checked: DockService.showIndicators
                    Accessible.name: qsTr("Show running indicators")
                    onToggled: DockService.setOption("showIndicators", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                visible: !DockService.supportsMinimizeEffects || NiriConfigService.ready("minimize-animation")
                title: qsTr("Minimize animation")
                iconName: "animation"
                supportingText: !DockService.supportsMinimizeEffects ? qsTr(
                                                                           "Window animation selection is unavailable in this session") :
                                                                       NiriConfigService.minimizeAnimationsDisabled
                                                                       ? qsTr("Animations are disabled in your configuration") :
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
                                label: qsTr("Genie")
                            },
                            {
                                value: "scale",
                                label: qsTr("Scale")
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
                title: qsTr("Show recent applications")
                iconName: "history"

                trailing: StyledSwitch {
                    checked: DockService.showRecent
                    Accessible.name: qsTr("Show recent applications")
                    onToggled: DockService.setOption("showRecent", checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Pin applications from the menu")
                iconName: "keep"

                trailing: StyledSwitch {
                    checked: DockService.contextPinning
                    Accessible.name: qsTr("Pin applications from the menu")
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
                    '{"id":"general.dock.section.previews","route":"general.dock","title":"Window previews","context":"DockPage","icon":"preview","aliases":["thumbnails","hover"],"availability":"dock-previews"}'
            }
            SettingsRow {
                Layout.fillWidth: true
                title: qsTr("Show window thumbnails")
                iconName: "preview"
                trailing: StyledSwitch {
                    checked: DockService.showThumbnails
                    Accessible.name: qsTr("Show window thumbnails")
                    onToggled: DockService.setOption("showThumbnails", checked)
                }
            }
            GeneralSliderSetting {
                title: qsTr("Preview size")
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
