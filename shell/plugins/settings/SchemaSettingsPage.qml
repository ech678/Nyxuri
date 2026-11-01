pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services
import qs.commons.i18n

// SchemaSettingsPage — the generic renderer for manifest-declared settings
// controls (S0-3b). A route with `controls` instead of `source` has no page
// of its own: the host renders the descriptor list with the ui/ atom suite
// and persists values through the PluginSettings store ("<pluginId>.<key>").
// The page host injects `settingsRoute` (the route id) after load; without
// it the page stays empty rather than guessing.
NexusPageBase {
    id: root

    // Injected by the settings page host (SettingsPageHost's loader).
    property string settingsRoute: ""

    readonly property var route: settingsRoute ? SpotlightCatalog.route(settingsRoute) : null
    readonly property var controls: route && route.controls ? route.controls : []
    readonly property string pluginId: route ? route.pluginId : ""

    title: route ? I18n.tr(route.sourceTitle || route.title, route.context) : ""

    function controlTitle(control) {
        return I18n.tr(control.title, root.route ? root.route.context : "ControlCenterWindow");
    }

    function controlSubtext(control) {
        return control.description && root.route ? I18n.tr(control.description, root.route.context) : "";
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: 2

        Repeater {
            model: root.controls

            delegate: Loader {
                id: controlLoader

                required property var modelData
                required property int index

                Layout.fillWidth: true

                sourceComponent: {
                    switch (controlLoader.modelData.type) {
                    case "switch":
                        return switchRow;
                    case "select":
                        return selectRow;
                    case "slider":
                        return sliderRow;
                    case "spin":
                        return spinRow;
                    default:
                        return textRow;
                    }
                }
            }
        }

        // Row atoms weld into one connected group per page: first/last bend
        // the corners, everything between stays flush.
        Component {
            id: switchRow

            PreferenceToggle {
                first: controlLoader.index === 0
                last: controlLoader.index === root.controls.length - 1
                text: root.controlTitle(controlLoader.modelData)
                subtext: root.controlSubtext(controlLoader.modelData)
                icon: controlLoader.modelData.icon || ""
                checked: PluginSettings.value(root.pluginId, controlLoader.modelData.key,
                                              controlLoader.modelData.default === undefined ? false :
                                                                                              controlLoader.modelData.default)
                onToggled: PluginSettings.setValue(root.pluginId, controlLoader.modelData.key, checked)
            }
        }

        Component {
            id: selectRow

            PreferenceSelect {
                first: controlLoader.index === 0
                last: controlLoader.index === root.controls.length - 1
                label: root.controlTitle(controlLoader.modelData)
                subtext: root.controlSubtext(controlLoader.modelData)
                icon: controlLoader.modelData.icon || ""
                model: controlLoader.modelData.options
                currentValue: PluginSettings.value(root.pluginId, controlLoader.modelData.key,
                                                   controlLoader.modelData.default === undefined ? "" :
                                                                                                   controlLoader.modelData.default)
                onSelected: next => PluginSettings.setValue(root.pluginId, controlLoader.modelData.key, next)
            }
        }

        Component {
            id: sliderRow

            PreferenceSlider {
                first: controlLoader.index === 0
                last: controlLoader.index === root.controls.length - 1
                icon: controlLoader.modelData.icon || ""
                label: root.controlTitle(controlLoader.modelData)
                from: controlLoader.modelData.min
                to: controlLoader.modelData.max
                stepSize: controlLoader.modelData.step
                value: PluginSettings.value(root.pluginId, controlLoader.modelData.key,
                                            controlLoader.modelData.default === undefined
                                            ? controlLoader.modelData.min : controlLoader.modelData.default)
                valueLabel: Number(value).toLocaleString(Qt.locale(), "f", 0)
                onCommitted: next => PluginSettings.setValue(root.pluginId, controlLoader.modelData.key, next)
            }
        }

        Component {
            id: spinRow

            PreferenceStepper {
                first: controlLoader.index === 0
                last: controlLoader.index === root.controls.length - 1
                label: root.controlTitle(controlLoader.modelData)
                subtext: root.controlSubtext(controlLoader.modelData)
                from: controlLoader.modelData.min
                to: controlLoader.modelData.max
                stepSize: controlLoader.modelData.step
                value: PluginSettings.value(root.pluginId, controlLoader.modelData.key,
                                            controlLoader.modelData.default === undefined
                                            ? controlLoader.modelData.min : controlLoader.modelData.default)
                onValueChanged: PluginSettings.setValue(root.pluginId, controlLoader.modelData.key, value)
            }
        }

        Component {
            id: textRow

            PreferenceInput {
                first: controlLoader.index === 0
                last: controlLoader.index === root.controls.length - 1
                label: root.controlTitle(controlLoader.modelData)
                subtext: root.controlSubtext(controlLoader.modelData)
                value: PluginSettings.value(root.pluginId, controlLoader.modelData.key,
                                            controlLoader.modelData.default === undefined ? "" :
                                                                                            controlLoader.modelData.default)
                onEditingFinished: next => PluginSettings.setValue(root.pluginId, controlLoader.modelData.key,
                                                                   next)
            }
        }
    }
}
