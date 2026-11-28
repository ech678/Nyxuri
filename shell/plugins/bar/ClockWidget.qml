import qs.services
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

BarWidgetSwitcher {
    id: root
    property color contentColor: Appearance.colors.colOnLayer1
    property bool contentColorOverridden: false
    // D4b entry axes: showDate/dateFormat replace the old verbose bridge
    // read and the global [time].dateFormat key; the long date formats
    // per instance now.
    property var widgetEntry: null
    // D4e: the owning bar (injected with the entry) — bar-level axes
    // resolve through it, never the settings-facing views.
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    readonly property bool showDate: BarWidgetDefaults.option("clock", root.widgetEntry, "showDate")
    readonly property string dateFormat: BarWidgetDefaults.option("clock", root.widgetEntry, "dateFormat")
    readonly property string longDate: root.dateFormat !== "" ? Qt.formatDateTime(root.today, root.dateFormat) : Qt.formatDateTime(root.today, "dddd, dd/MM")
    property var today: new Date()
    readonly property string dateTimeString: DateTime.time
    readonly property string _timeFontFamily: Config.options?.bar?.m3?.clock?.timeFontFamily ?? ""
    readonly property int _timePixelSize: Config.options?.bar?.m3?.clock?.timePixelSize ?? 0
    readonly property string _dateFontFamily: Config.options?.bar?.m3?.clock?.dateFontFamily ?? ""
    readonly property int _datePixelSize: Config.options?.bar?.m3?.clock?.datePixelSize ?? 0

    Timer {
        id: clockTicker
        interval: 60000
        running: true
        repeat: true
        onTriggered: root.today = new Date()
    }

    Component.onDestruction: {
        clockTicker.stop();
    }

    // D4g batch three rail face — Fork & Trim of caelestia
    // modules/bar/components/Clock.qml (stacked clock): date block
    // (weekday + day + divider, gated by the showDate axis), then HH / MM
    // lines whose sizes follow caelestia's fontFor() optical matching so
    // both lines read as one size. Two departures from the original,
    // both noted where they happen: the fit stage (caelestia fixes a
    // generous bar.innerWidth; our rail thickness is a 28–64 axis, so the
    // base shrinks to the widest line) and pixel-size scaling instead of
    // the variable-font width axis (our clock family is configurable and
    // not guaranteed variable).
    readonly property list<string> railTimeParts: root.dateTimeString.split(/[: ]/)
    readonly property string railAmPm: root.railTimeParts.find(part => /^(am|pm)$/i.test(part)) ?? ""
    readonly property string railHour: root.railTimeParts[0] ?? ""
    readonly property string railMinute: root.railTimeParts[1] ?? ""
    readonly property real railBaseSize: NexusStyle.font.titleLarge * BarScale.fontFor(root.widgetBar)
    readonly property real railAvailableWidth: PersonalizationConfig.resolvedVerticalBarWidth(root.barAxes) - 8

    function railFitScale(hourWidth, minuteWidth) {
        return Math.min(1, root.railAvailableWidth / Math.max(hourWidth, minuteWidth, 1));
    }

    // caelestia fontFor(): the narrower line widens up to +5% so HH and MM
    // optically match; "11" is visually narrow and gets a fixed boost.
    function railLineScale(text, metricWidth, widest) {
        if (text === "11")
            return 1.15;
        return Math.min(1.05, widest / Math.max(metricWidth, 1));
    }

    component RailClockFace: ColumnLayout {
        id: railFace

        property bool materialSkin: false

        anchors.centerIn: parent
        spacing: NexusStyle.padding.extraSmall

        readonly property real baseSize: root.railBaseSize
        readonly property color digitColor: railFace.materialSkin ? Appearance.colors.colPrimary : root.contentColor

        TextMetrics {
            id: hourMetrics

            font.family: root._timeFontFamily.length > 0 ? root._timeFontFamily : Appearance.font.main
            font.pixelSize: railFace.baseSize
            text: root.railHour
        }

        TextMetrics {
            id: minMetrics

            font.family: hourMetrics.font.family
            font.pixelSize: railFace.baseSize
            text: root.railMinute
        }

        readonly property real fitScale: root.railFitScale(hourMetrics.width, minMetrics.width)
        readonly property real widestMetric: Math.max(hourMetrics.width, minMetrics.width)

        // Date block (caelestia: weekday / day / divider).
        ColumnLayout {
            visible: root.showDate
            spacing: 0
            Layout.alignment: Qt.AlignHCenter

            StyledText {
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(root.today, "ddd")
                font.family: root._dateFontFamily.length > 0 ? root._dateFontFamily : Appearance.font.main
                font.pixelSize: NexusStyle.font.labelSmall * BarScale.fontFor(root.widgetBar)
                color: railFace.digitColor
                opacity: 0.85
            }

            StyledText {
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(root.today, "d")
                font.family: root._timeFontFamily.length > 0 ? root._timeFontFamily : Appearance.font.main
                font.pixelSize: railFace.baseSize * railFace.fitScale
                font.features: {
                    "tnum": 1
                }
                color: railFace.digitColor
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: -NexusStyle.padding.extraSmall
                Layout.rightMargin: -NexusStyle.padding.extraSmall
                Layout.topMargin: 4
                Layout.bottomMargin: NexusStyle.padding.extraSmall / 2
                implicitHeight: 1
                color: Appearance.m3colors.m3outlineVariant
            }
        }

        StyledText {
            Layout.alignment: Qt.AlignHCenter
            text: root.railHour
            font.family: hourMetrics.font.family
            font.pixelSize: railFace.baseSize * railFace.fitScale * root.railLineScale(text, hourMetrics.width, railFace.widestMetric)
            font.letterSpacing: -0.9
            font.features: {
                "tnum": 1
            }
            color: railFace.digitColor
        }

        StyledText {
            Layout.topMargin: -parent.spacing - 4
            Layout.alignment: Qt.AlignHCenter
            text: root.railMinute
            font.family: hourMetrics.font.family
            font.pixelSize: railFace.baseSize * railFace.fitScale * root.railLineScale(text, minMetrics.width, railFace.widestMetric)
            font.letterSpacing: -0.9
            font.features: {
                "tnum": 1
            }
            color: railFace.digitColor
        }

        StyledText {
            visible: root.railAmPm !== ""
            Layout.topMargin: -parent.spacing - 2
            Layout.alignment: Qt.AlignHCenter
            text: root.railAmPm.toLowerCase()
            font.family: hourMetrics.font.family
            font.pixelSize: NexusStyle.font.labelSmall * BarScale.fontFor(root.widgetBar)
            color: railFace.digitColor
            opacity: 0.8
        }
    }

    colDefault: Component {
        RailClockFace {
            materialSkin: false
        }
    }

    colMaterial: Component {
        RailClockFace {
            materialSkin: true
        }
    }

    rowDefault: Component {
        RowLayout {
            spacing: 4
            StyledText {
                visible: root.showDate
                font.family: root._dateFontFamily.length > 0 ? root._dateFontFamily : Appearance.font.main
                font.pixelSize: root._datePixelSize > 0 ? root._datePixelSize : NexusStyle.font.bodyMedium * BarScale.fontFor(root.widgetBar)
                color: root.contentColor
                text: root.longDate
            }
            StyledText {
                visible: root.showDate
                font.pixelSize: NexusStyle.font.bodyMedium * BarScale.fontFor(root.widgetBar)
                color: root.contentColor
                text: "•"
            }
            StyledText {
                font.family: root._timeFontFamily.length > 0 ? root._timeFontFamily : Appearance.font.main
                font.pixelSize: root._timePixelSize > 0 ? root._timePixelSize : NexusStyle.font.bodyLarge * BarScale.fontFor(root.widgetBar)
                color: root.contentColor
                text: DateTime.time ?? ""
                font.letterSpacing: -0.4
                font.features: {
                    "tnum": 1
                }
            }
        }
    }

    rowMaterial: Component {
        RowLayout {
            id: pill
            spacing: 4

            property var timeParts: DateTime.time.split(/[: ]/)
            property string ampm: timeParts.find(part => /^(am|pm)$/i.test(part)) ?? ""
            property string time: timeParts.filter(part => !/^(am|pm)$/i.test(part)).join(":")

            StyledText {
                visible: root.showDate
                font.family: root._dateFontFamily.length > 0 ? root._dateFontFamily : Appearance.font.main
                font.pixelSize: root._datePixelSize > 0 ? root._datePixelSize : NexusStyle.font.bodyMedium * BarScale.fontFor(root.widgetBar)
                color: M3Palette.pillInk("clockWidget")
                // The per-instance long form (dateFormat axis) keeps the
                // stacked-pill row identical across clock skins.
                text: root.longDate
                Layout.alignment: Qt.AlignVCenter
                leftPadding: 5
            }

            Rectangle {
                implicitWidth: timeText.implicitWidth + 16
                implicitHeight: Math.max(24, timeText.implicitHeight + 6)
                radius: Appearance.rounding.full
                color: M3Palette.primary

                StyledText {
                    id: timeText
                    anchors.centerIn: parent
                    font.family: root._timeFontFamily.length > 0 ? root._timeFontFamily : Appearance.font.main
                    font.pixelSize: root._timePixelSize > 0 ? root._timePixelSize : NexusStyle.font.bodySmall * BarScale.fontFor(root.widgetBar)
                    color: M3Palette.primaryForeground
                    font.weight: Font.Bold
                    text: pill.time
                    font.features: {
                        "tnum": 1
                    }
                    font.letterSpacing: -0.4
                }
            }

            Rectangle {
                visible: pill.ampm !== ""
                z: 1
                implicitWidth: ampmText.implicitWidth + 8
                implicitHeight: 24
                radius: Appearance.rounding.full
                color: M3Palette.tertiaryContainer
                Layout.alignment: Qt.AlignVCenter
                Layout.leftMargin: -10
                StyledText {
                    id: ampmText
                    anchors.centerIn: parent
                    font.family: root._timeFontFamily.length > 0 ? root._timeFontFamily : Appearance.font.main
                    font.pixelSize: NexusStyle.font.bodySmall * BarScale.fontFor(root.widgetBar)
                    color: M3Palette.primary
                    text: pill.ampm
                }
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        readonly property bool clickForDetails: !root.barAxes.hoverPopouts
        hoverEnabled: true
        // D4b click axes: a consumed dispatch ends here; "default"/"none"
        // fall through to the built-in popup behavior.
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        onClicked: mouse => {
            if (BarWidgetActions.dispatchMouse("clock", root.widgetEntry, mouse.button))
                mouse.accepted = true;
            else if (mouse.button === Qt.LeftButton && clickForDetails)
                clockPopup.active = !clockPopup.active;
        }

        ClockWidgetPopup {
            id: clockPopup
            widgetBar: root.widgetBar
            hoverTarget: mouseArea
            hoverActivates: !mouseArea.clickForDetails
            closeOnOutsideClick: mouseArea.clickForDetails
            onRequestClose: active = false
            today: root.today
        }
    }
}
