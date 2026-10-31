pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Horizontal clock style subpage (T3 M4): NexusPageBase subpage with its own
// back arrow. Font axes and digit offsets ride the slider atom (live `moved`
// plus commit-on-release `committed`); the digit picker stays a segmented
// semantic picker — its labels ARE the live clock digits a pill menu would
// hide — and the custom hex field stays the shared text field.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("keystone.horizontal-clock")
    isSubPage: true

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property string selectedDigit: "h0"
    property string customColorDraft: ""
    readonly property int currentHourTens: clockPreview.h0
    readonly property int currentHourOnes: clockPreview.h1
    readonly property int currentMinuteTens: clockPreview.m0
    readonly property int currentMinuteOnes: clockPreview.m1
    readonly property string currentPeriodLead: clockPreview.periodLead

    function selectedDigitData() {
        const defaults = PersonalizationConfig.horizontalClockDigitDefaults;
        const configured = PersonalizationConfig.horizontalClockDigits;
        return configured && configured[root.selectedDigit] ? configured[root.selectedDigit] :
                                                              defaults[root.selectedDigit];
    }

    function selectedDigitCustomColor() {
        const data = root.selectedDigitData();
        return String(data && data.customColor || "");
    }

    function updateCustomColorDraft() {
        root.customColorDraft = root.selectedDigitCustomColor();
        if (customColorField && !customColorField.activeFocus)
            customColorField.text = root.customColorDraft;
    }

    function selectedDigitThemeColor() {
        const data = root.selectedDigitData();
        return data && data.colorRole === "inversePrimary" ? Appearance.colors.colInversePrimary.toString() :
                                                             Appearance.colors.colPrimary.toString();
    }

    Component.onCompleted: root.updateCustomColorDraft()
    onSelectedDigitChanged: root.updateCustomColorDraft()

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        PreferenceHeader {
            first: true
            text: I18n.tr("Horizontal clock style")
        }

        ConnectedRect {
            id: previewCard

            first: true
            Layout.fillWidth: true
            implicitHeight: clockPreview.implicitHeight + NexusStyle.padding.medium * 2

            HorizontalClockPreview {
                id: clockPreview

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.small
                anchors.rightMargin: NexusStyle.padding.small
                implicitHeight: Math.max(42, width * 42 / 220)
            }

            SettingsSearchAnchor {
                id: searchAnchor0
                target: previewCard
                declaration:
                    '{"id":"keystone.horizontal-clock.section.horizontal-clock-style","route":"keystone.horizontal-clock","title":"Horizontal clock style","context":"HorizontalClockPage","icon":"schedule","aliases":[]}'
            }
        }

        PreferenceToggle {
            text: I18n.tr("Hide date")
            checked: PersonalizationConfig.keystoneHideDate
            onToggled: PersonalizationConfig.setKeystoneHideDate(checked)
        }

        PreferenceSlider {
            label: I18n.tr("Font size")
            valueLabel: "px  " + Math.round(PersonalizationConfig.horizontalClockFontSize)
            value: PersonalizationConfig.horizontalClockFontSize
            from: 16
            to: 28
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockFontSize(Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockFontSize(Math.round(value), true)
        }

        PreferenceSlider {
            label: I18n.tr("Weight")
            valueLabel: "wght  " + Math.round(PersonalizationConfig.horizontalClockAxes.wght)
            value: PersonalizationConfig.horizontalClockAxes.wght
            from: 1
            to: 1000
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockAxis("wght", Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockAxis("wght", Math.round(value),
                                                                               true)
        }

        PreferenceSlider {
            label: I18n.tr("Width")
            valueLabel: "wdth  " + Math.round(PersonalizationConfig.horizontalClockAxes.wdth)
            value: PersonalizationConfig.horizontalClockAxes.wdth
            from: 25
            to: 151
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockAxis("wdth", Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockAxis("wdth", Math.round(value),
                                                                               true)
        }

        PreferenceSlider {
            label: I18n.tr("Optical size")
            valueLabel: "opsz  " + Math.round(PersonalizationConfig.horizontalClockAxes.opsz)
            value: PersonalizationConfig.horizontalClockAxes.opsz
            from: 6
            to: 144
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockAxis("opsz", Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockAxis("opsz", Math.round(value),
                                                                               true)
        }

        PreferenceSlider {
            label: I18n.tr("Grade")
            valueLabel: "GRAD  " + Math.round(PersonalizationConfig.horizontalClockAxes.GRAD)
            value: PersonalizationConfig.horizontalClockAxes.GRAD
            from: 0
            to: 100
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockAxis("GRAD", Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockAxis("GRAD", Math.round(value),
                                                                               true)
        }

        PreferenceSlider {
            label: I18n.tr("Roundness")
            valueLabel: "ROND  " + Math.round(PersonalizationConfig.horizontalClockAxes.ROND)
            value: PersonalizationConfig.horizontalClockAxes.ROND
            from: 0
            to: 100
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockAxis("ROND", Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockAxis("ROND", Math.round(value),
                                                                               true)
        }

        PreferenceSlider {
            label: I18n.tr("Slant")
            valueLabel: "slnt  " + Math.round(PersonalizationConfig.horizontalClockAxes.slnt)
            value: PersonalizationConfig.horizontalClockAxes.slnt
            from: -10
            to: 0
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockAxis("slnt", Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockAxis("slnt", Math.round(value),
                                                                               true)
        }

        // The digit picker's labels are the live clock digits — a pill menu
        // would hide them, so this stays a segmented semantic picker.
        ConnectedRect {
            id: digitPickerCard

            Layout.fillWidth: true
            implicitHeight: digitPickerColumn.implicitHeight + NexusStyle.padding.medium * 2

            ColumnLayout {
                id: digitPickerColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                StyledText {
                    Layout.fillWidth: true
                    text: I18n.tr("Current digit")
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    elide: Text.ElideRight
                }

                StyledButtonGroup {
                    Layout.fillWidth: true
                    model: [
                        {
                            "value": "h0",
                            "label": String(root.currentHourTens)
                        },
                        {
                            "value": "h1",
                            "label": String(root.currentHourOnes)
                        },
                        {
                            "value": "separator",
                            "label": ":"
                        },
                        {
                            "value": "m0",
                            "label": String(root.currentMinuteTens)
                        },
                        {
                            "value": "m1",
                            "label": String(root.currentMinuteOnes)
                        },
                        {
                            "value": "ap",
                            "label": root.currentPeriodLead
                        },
                        {
                            "value": "periodM",
                            "label": "M"
                        }
                    ]
                    currentValue: root.selectedDigit
                    buttonMinWidth: 52
                    onValueSelected: value => {
                        root.selectedDigit = String(value);
                        root.updateCustomColorDraft();
                    }
                }
            }
        }

        PreferenceSelect {
            label: I18n.tr("Color")
            subtext: I18n.tr("Default theme colors follow the Matugen theme")
            model: [
                {
                    "label": I18n.tr("Primary"),
                    "value": "primary"
                },
                {
                    "label": I18n.tr("Inverse"),
                    "value": "inversePrimary"
                },
                {
                    "label": I18n.tr("Custom"),
                    "value": "custom"
                }
            ]
            currentValue: root.selectedDigitData().colorRole
            inputRegionService: PopupInputRegionService
            onSelected: value => {
                const role = String(value);
                const color = role === "custom" ? root.selectedDigitCustomColor()
                                                  || root.selectedDigitThemeColor() :
                                                  root.selectedDigitCustomColor();
                PersonalizationConfig.setHorizontalClockDigitColor(root.selectedDigit, role, color, true);
            }
        }

        ConnectedRect {
            visible: root.selectedDigitData().colorRole === "custom"
            Layout.fillWidth: true
            implicitHeight: customColorField.implicitHeight + NexusStyle.padding.medium * 2

            MaterialTextField {
                id: customColorField

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                text: root.customColorDraft
                placeholderText: I18n.tr("#RRGGBB or #RRGGBBAA")
                Accessible.name: I18n.tr("Custom color")
                onTextChanged: {
                    if (activeFocus)
                        root.customColorDraft = text;
                }
                onEditingFinished: PersonalizationConfig.setHorizontalClockDigitColor(root.selectedDigit,
                                                                                      "custom", text, true)
            }
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: NexusStyle.padding.extraSmall
            Layout.rightMargin: NexusStyle.padding.extraSmall
            Layout.topMargin: NexusStyle.padding.extraSmall
            text: I18n.tr("Position: %1").arg(root.selectedDigit.toUpperCase())
            color: Appearance.m3colors.m3onSurfaceVariant
            font.pixelSize: NexusStyle.font.labelMedium
            font.weight: NexusStyle.font.labelMediumWeight
            elide: Text.ElideRight
        }

        PreferenceSlider {
            label: I18n.tr("X offset")
            valueLabel: "x  " + Math.round(root.selectedDigitData().x)
            value: root.selectedDigitData().x
            from: -8
            to: 8
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockDigitValue(root.selectedDigit, "x",
                                                                                 Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockDigitValue(root.selectedDigit, "x",
                                                                                     Math.round(value), true)
        }

        PreferenceSlider {
            label: I18n.tr("Y offset")
            valueLabel: "y  " + Math.round(root.selectedDigitData().y)
            value: root.selectedDigitData().y
            from: -6
            to: 6
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockDigitValue(root.selectedDigit, "y",
                                                                                 Math.round(value), false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockDigitValue(root.selectedDigit, "y",
                                                                                     Math.round(value), true)
        }

        PreferenceSlider {
            last: true
            label: I18n.tr("Rotation")
            valueLabel: "°  " + Math.round(root.selectedDigitData().rotation) + "°"
            value: root.selectedDigitData().rotation
            from: -12
            to: 12
            stepSize: 1
            onMoved: value => PersonalizationConfig.setHorizontalClockDigitValue(root.selectedDigit,
                                                                                 "rotation", Math.round(value),
                                                                                 false)
            onCommitted: value => PersonalizationConfig.setHorizontalClockDigitValue(root.selectedDigit,
                                                                                     "rotation", Math.round(
                                                                                         value), true)
        }
    }

    Connections {
        function onHorizontalClockDigitsChanged() {
            if (!customColorField.activeFocus)
                root.updateCustomColorDraft();
        }

        target: PersonalizationConfig
    }
}
