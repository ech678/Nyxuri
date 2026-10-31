import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

ColumnLayout {
    id: root
    property var row: null
    readonly property var settings: row ? row.settings : ({})
    spacing: Metrics.spacingM
    function edit(key, value) {
        if (row)
            DisplayConfigService.edit(row.key, key, value);
    }
    SettingsRow {
        Layout.fillWidth: true
        title: I18n.tr("Focus at Startup")
        trailing: StyledSwitch {
            checked: root.settings.focusAtStartup === true
            Accessible.name: I18n.tr("Focus at Startup")
            onToggled: root.edit("focusAtStartup", checked ? true : null)
        }
    }
    DisplayChoice {
        Layout.fillWidth: true
        title: I18n.tr("Overview corners")
        options: [
            {
                value: "inherit",
                label: I18n.tr("Inherit")
            },
            {
                value: "off",
                label: I18n.tr("Off")
            },
            {
                value: "custom",
                label: I18n.tr("Select corners")
            }
        ]
        value: !root.settings.hotCorners ? "inherit" : root.settings.hotCorners.indexOf("off") >= 0 ? "off" :
                                                                                                      "custom"

        onSelected: value => root.edit("hotCorners", value === "inherit" ? null : value === "off" ? ["off"] :
                                                                                                    ["top-left"])

    }
    GridLayout {
        Layout.fillWidth: true
        columns: width > 420 ? 2 : 1
        visible: Boolean(root.settings && root.settings.hotCorners && root.settings.hotCorners.indexOf("off")
                         < 0)
        Repeater {
            model: [
                {
                    key: "top-left",
                    label: I18n.tr("Top left")
                },
                {
                    key: "top-right",
                    label: I18n.tr("Top right")
                },
                {
                    key: "bottom-left",
                    label: I18n.tr("Bottom left")
                },
                {
                    key: "bottom-right",
                    label: I18n.tr("Bottom right")
                }
            ]
            SettingsRow {
                required property var modelData
                Layout.fillWidth: true
                title: modelData.label
                trailing: StyledSwitch {
                    checked: root.settings.hotCorners ? root.settings.hotCorners.indexOf(modelData.key) >= 0 :
                                                        false
                    Accessible.name: modelData.label
                    onToggled: {
                        const corners = root.settings.hotCorners || [];
                        const next = checked ? corners.concat([modelData.key]) : corners.filter(c => c
                                                                                                     !== modelData.key);
                        root.edit("hotCorners", next.length ? next : ["off"]);
                    }
                }
            }
        }
    }
    OutlinedTextField {
        Layout.fillWidth: true
        labelText: I18n.tr("Window gaps")
        placeholderText: I18n.tr("Inherit")
        text: root.settings.gaps === undefined ? "" : String(root.settings.gaps)
        validator: DoubleValidator {
            bottom: 0
            top: 65535
            locale: "C"
        }
        onEditingFinished: root.edit("gaps", text.trim() === "" ? null : Number(text))
    }
    DisplayChoice {
        Layout.fillWidth: true
        title: I18n.tr("Always center single column")
        options: [
            {
                value: "inherit",
                label: I18n.tr("Inherit")
            },
            {
                value: "on",
                label: I18n.tr("On")
            },
            {
                value: "off",
                label: I18n.tr("Off")
            }
        ]
        value: root.settings["always-center-single-column"] === undefined ? "inherit" :
                                                                            root.settings["always-center-single-column"]
                                                                            ? "on" : "off"
        onSelected: value => root.edit("always-center-single-column", value === "inherit" ? null : value
                                                                                            === "on")

    }
    DisplayColumnWidths {
        Layout.fillWidth: true
        title: I18n.tr("Default column width")
        single: true
        widths: root.settings["default-column-width"] || []
        onEdited: widths => root.edit("default-column-width", widths.length ? widths : null)
    }
    DisplayColumnWidths {
        Layout.fillWidth: true
        title: I18n.tr("Preset column widths")
        widths: root.settings["preset-column-widths"] || []
        onEdited: widths => root.edit("preset-column-widths", widths.length ? widths : null)
    }
}
